"""Safe static Python AST analysis and dependency extraction without code execution."""

import ast
import os
import sys
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field


class ImportRecord(BaseModel):
    """Represents a single import statement extracted from Python source AST."""

    model_config = ConfigDict(frozen=True)

    source_file: str = Field(..., description="Relative path of the source file containing the import")
    target_module: str = Field(..., description="Imported target module name")
    imported_symbol: Optional[str] = Field(None, description="Specific symbol imported (from x import y)")
    alias: Optional[str] = Field(None, description="Local alias if renamed (as z)")
    line_number: int = Field(..., ge=1, description="Line number where the import occurs")
    is_relative: bool = Field(default=False, description="Whether this is a relative import (. or ..)")
    level: int = Field(default=0, ge=0, description="Relative import level (number of leading dots)")
    raw_statement: str = Field(..., description="Reconstructed source statement")

    # Resolution metadata (determined against repository file tree)
    is_stdlib: bool = Field(default=False, description="Whether target module belongs to Python standard library")
    is_internal: bool = Field(default=False, description="Whether target module resolves to a local repository file")
    is_external: bool = Field(default=False, description="Whether target is an external third-party package")
    resolution_status: str = Field(
        default="analyzed",
        description="Resolution status (resolved_stdlib, resolved_internal, external_package, unresolved_reference)",
    )


class FileSyntaxError(BaseModel):
    """File-level syntax error captured during static AST parsing."""

    model_config = ConfigDict(frozen=True)

    file_path: str = Field(..., description="Relative path of the source file with syntax errors")
    error_message: str = Field(..., description="SyntaxError description")
    line_number: Optional[int] = Field(None, description="Line number of syntax error")
    offset: Optional[int] = Field(None, description="Column offset of syntax error")


class ParsedFileSummary(BaseModel):
    """Static analysis summary for a single inspected Python source file."""

    model_config = ConfigDict(frozen=True)

    file_path: str = Field(..., description="Relative path of the analyzed source file")
    status: str = Field(..., description="Inspection status: analyzed, syntax_error, skipped_by_policy")
    line_count: int = Field(default=0, ge=0, description="Total lines of code")
    imports: List[ImportRecord] = Field(default_factory=list, description="All extracted import records")
    syntax_error: Optional[FileSyntaxError] = Field(None, description="Syntax error if parsing failed")


def _is_stdlib_module(module_name: str) -> bool:
    """Check if top-level module is part of Python's standard library."""
    if not module_name:
        return False
    top_module = module_name.split(".")[0]
    # Python 3.10+ provides sys.stdlib_module_names
    stdlib_names = getattr(sys, "stdlib_module_names", None)
    if stdlib_names:
        return top_module in stdlib_names
    # Fallback to sys.builtin_module_names
    return top_module in sys.builtin_module_names


def _resolve_relative_module(
    source_file: str,
    target_module: str,
    level: int,
    known_py_files: Set[str],
) -> Tuple[str, bool]:
    """Attempt to resolve a relative import against the known repository Python files.

    Returns (resolved_module_name, is_resolved_internally).
    """
    source_dir = os.path.dirname(source_file)
    dir_parts = [p for p in source_dir.replace("\\", "/").split("/") if p]

    # Level 1 = current dir, Level 2 = parent dir, etc.
    up_count = max(level - 1, 0)
    if up_count > len(dir_parts):
        # Escapes repository root
        return (target_module, False)

    base_parts = dir_parts[: len(dir_parts) - up_count] if up_count > 0 else dir_parts

    if target_module:
        target_parts = base_parts + target_module.split(".")
    else:
        target_parts = base_parts

    resolved_path_base = "/".join(target_parts)
    candidate_py = f"{resolved_path_base}.py"
    candidate_pkg = f"{resolved_path_base}/__init__.py"

    norm_py = os.path.normpath(candidate_py).replace("\\", "/")
    norm_pkg = os.path.normpath(candidate_pkg).replace("\\", "/")

    resolved_name = ".".join(target_parts)
    is_found = norm_py in known_py_files or norm_pkg in known_py_files
    return (resolved_name, is_found)


def parse_python_file(
    rel_path: str,
    source_code: str,
    all_known_py_files: Set[str],
) -> ParsedFileSummary:
    """Parse a single Python source file into an AST and extract all import statements.

    Zero code execution: uses ast.parse() exclusively.
    If a SyntaxError occurs, captures it cleanly and marks file as syntax_error without crashing.
    """
    line_count = len(source_code.splitlines())

    try:
        tree = ast.parse(source_code, filename=rel_path)
    except SyntaxError as e:
        syntax_err = FileSyntaxError(
            file_path=rel_path,
            error_message=str(e.msg) if hasattr(e, "msg") else str(e),
            line_number=e.lineno,
            offset=e.offset,
        )
        return ParsedFileSummary(
            file_path=rel_path,
            status="syntax_error",
            line_count=line_count,
            imports=[],
            syntax_error=syntax_err,
        )

    records: List[ImportRecord] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias_node in node.names:
                mod_name = alias_node.name
                alias = alias_node.asname
                raw = f"import {mod_name}" + (f" as {alias}" if alias else "")

                is_stdlib = _is_stdlib_module(mod_name)
                # Check if internal (e.g. oracle.core)
                mod_as_path = mod_name.replace(".", "/")
                is_internal = any(
                    f == f"{mod_as_path}.py" or f.startswith(f"{mod_as_path}/")
                    for f in all_known_py_files
                )

                if is_stdlib:
                    status = "resolved_stdlib"
                elif is_internal:
                    status = "resolved_internal"
                else:
                    status = "external_package"

                records.append(
                    ImportRecord(
                        source_file=rel_path,
                        target_module=mod_name,
                        imported_symbol=None,
                        alias=alias,
                        line_number=getattr(node, "lineno", 1),
                        is_relative=False,
                        level=0,
                        raw_statement=raw,
                        is_stdlib=is_stdlib,
                        is_internal=is_internal,
                        is_external=(not is_stdlib and not is_internal),
                        resolution_status=status,
                    )
                )

        elif isinstance(node, ast.ImportFrom):
            level = getattr(node, "level", 0) or 0
            base_module = node.module or ""

            for alias_node in node.names:
                symbol = alias_node.name
                alias = alias_node.asname

                leading_dots = "." * level
                full_mod = f"{leading_dots}{base_module}" if level > 0 else base_module
                raw = f"from {full_mod} import {symbol}" + (f" as {alias}" if alias else "")

                is_relative = level > 0
                if is_relative:
                    resolved_name, is_found = _resolve_relative_module(
                        rel_path, base_module, level, all_known_py_files
                    )
                    is_stdlib = False
                    is_internal = is_found
                    status = "resolved_internal" if is_found else "unresolved_reference"
                    target_name = resolved_name or full_mod
                else:
                    target_name = base_module
                    is_stdlib = _is_stdlib_module(base_module)
                    mod_as_path = base_module.replace(".", "/")
                    is_internal = any(
                        f == f"{mod_as_path}.py" or f.startswith(f"{mod_as_path}/")
                        for f in all_known_py_files
                    )
                    if is_stdlib:
                        status = "resolved_stdlib"
                    elif is_internal:
                        status = "resolved_internal"
                    else:
                        status = "external_package"

                records.append(
                    ImportRecord(
                        source_file=rel_path,
                        target_module=target_name,
                        imported_symbol=symbol,
                        alias=alias,
                        line_number=getattr(node, "lineno", 1),
                        is_relative=is_relative,
                        level=level,
                        raw_statement=raw,
                        is_stdlib=is_stdlib,
                        is_internal=is_internal,
                        is_external=(not is_stdlib and not is_internal and not is_relative),
                        resolution_status=status,
                    )
                )

    return ParsedFileSummary(
        file_path=rel_path,
        status="analyzed",
        line_count=line_count,
        imports=records,
        syntax_error=None,
    )
