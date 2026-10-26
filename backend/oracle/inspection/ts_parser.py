"""Safe static TypeScript and JavaScript AST analysis and dependency extraction without code execution.

Uses the official TypeScript Compiler API (via an in-process Node.js worker)
to parse source files, capture precise syntax diagnostics, and extract import/export
declarations without executing target repository code.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

from oracle.inspection.ast_parser import FileSyntaxError, ImportRecord, ParsedFileSummary

# Supported TypeScript and JavaScript file extensions
TS_JS_EXTENSIONS: Set[str] = {
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
}

# Resolution candidate file extensions in preference order
RESOLUTION_EXTENSIONS: List[str] = [
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mts",
    ".cts",
    ".mjs",
    ".cjs",
    ".json",
]

# Resolution index filename patterns in preference order
INDEX_FILENAMES: List[str] = [
    f"index{ext}" for ext in RESOLUTION_EXTENSIONS
]


def is_ts_js_file(path: str) -> bool:
    """Check if the given relative or absolute file path has a supported JS/TS extension."""
    _, ext = os.path.splitext(path)
    return ext.lower() in TS_JS_EXTENSIONS


def get_worker_script_path() -> str:
    """Return the absolute path to the ts_ast_worker.mjs script."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "ts_ast_worker.mjs")


def check_ts_parser_available() -> Tuple[bool, Optional[str]]:
    """Verify that Node.js is installed and the TypeScript compiler worker can be executed.

    Returns (is_available, error_reason).
    """
    node_bin = shutil.which("node")
    if not node_bin:
        return (False, "Node.js executable ('node') was not found on system PATH.")

    worker_script = get_worker_script_path()
    if not os.path.exists(worker_script):
        return (False, f"Worker script not found at {worker_script}.")

    # Quick probe with empty payload
    try:
        proc = subprocess.run(
            [node_bin, worker_script],
            input=json.dumps({"files": []}),
            text=True,
            capture_output=True,
            timeout=5.0,
        )
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            return (False, f"Node worker failed: {err}")
        data = json.loads(proc.stdout)
        if data.get("error"):
            return (False, f"Node worker error: {data['error']}")
        return (True, None)
    except subprocess.TimeoutExpired:
        return (False, "Node worker preflight check timed out.")
    except Exception as ex:
        return (False, f"Failed to probe TypeScript parser worker: {str(ex)}")


def strip_json_comments_and_trailing_commas(raw_text: str) -> str:
    """Safely strip single-line comments, multi-line comments, and trailing commas from JSON/JSONC."""
    # Strip multi-line comments: /* ... */
    no_block = re.sub(r"/\*.*?\*/", "", raw_text, flags=re.DOTALL)
    # Strip single-line comments: // ... (only outside quotes)
    no_line = re.sub(r"//.*?\n", "\n", no_block)
    # Strip trailing commas before } or ]
    clean = re.sub(r",\s*([\]}])", r"\1", no_line)
    return clean.strip()


def load_tsconfig(root_dir: str) -> Optional[Dict[str, Any]]:
    """Parse tsconfig.json or jsconfig.json located in the inspected repository root.

    Extracts compilerOptions.baseUrl and compilerOptions.paths.
    Returns None if neither exists or parsing fails.
    """
    for config_name in ("tsconfig.json", "jsconfig.json"):
        config_path = os.path.join(root_dir, config_name)
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                cleaned = strip_json_comments_and_trailing_commas(content)
                data = json.loads(cleaned)
                return data.get("compilerOptions", {})
            except Exception:
                pass
    return None


def load_package_json(root_dir: str) -> Dict[str, Any]:
    """Parse package.json to discover declared external dependencies and package metadata.

    Discovers package.json at root and in first-level subdirectories (e.g. polyglot/monorepo layouts).
    Returns a dict containing declared package names under 'declared_dependencies'.
    """
    candidate_paths = [os.path.join(root_dir, "package.json")]
    try:
        for entry in os.listdir(root_dir):
            sub = os.path.join(root_dir, entry)
            if os.path.isdir(sub) and not entry.startswith("."):
                candidate_paths.append(os.path.join(sub, "package.json"))
    except Exception:
        pass

    declared: Set[str] = set()
    root_data = {}
    root_name = None

    for pkg_path in candidate_paths:
        if not os.path.exists(pkg_path):
            continue
        try:
            with open(pkg_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            cleaned = strip_json_comments_and_trailing_commas(content)
            data = json.loads(cleaned)
            if not root_name and data.get("name"):
                root_name = data.get("name")
                root_data = data
            for dep_key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                deps = data.get(dep_key, {})
                if isinstance(deps, dict):
                    for pkg_name in deps.keys():
                        declared.add(pkg_name.lower())
        except Exception:
            continue

    return {
        "declared_dependencies": declared,
        "name": root_name,
        "data": root_data,
    }


def _match_path_alias(
    specifier: str,
    paths_config: Dict[str, List[str]],
    base_url: str,
    all_known_files: Set[str],
) -> Optional[Tuple[str, str]]:
    """Attempt to resolve a module specifier using tsconfig compilerOptions.paths.

    Returns (resolved_internal_file, matching_rule) if matched and found on disk,
    or (None, matching_rule) if matched pattern but target file is missing (unresolved internal),
    or None if no path alias patterns matched the specifier.
    """
    norm_known = {f.replace("\\", "/"): f for f in all_known_files}

    for pattern, targets in paths_config.items():
        if not isinstance(targets, list):
            continue

        # Exact match (e.g. "@utils": ["src/utils"])
        if "*" not in pattern:
            if specifier == pattern:
                for target in targets:
                    candidate_base = os.path.normpath(os.path.join(base_url, target)).replace("\\", "/")
                    if candidate_base.startswith(".."):
                        continue
                    # Check exact candidate, candidate with extensions, candidate/index
                    if candidate_base in norm_known:
                        return (norm_known[candidate_base], f"tsconfig_alias:{pattern}")
                    for ext in RESOLUTION_EXTENSIONS:
                        cand_ext = f"{candidate_base}{ext}"
                        if cand_ext in norm_known:
                            return (norm_known[cand_ext], f"tsconfig_alias:{pattern}")
                    for idx in INDEX_FILENAMES:
                        cand_idx = f"{candidate_base}/{idx}"
                        if cand_idx in norm_known:
                            return (norm_known[cand_idx], f"tsconfig_alias:{pattern}")
                return (None, f"tsconfig_alias:{pattern}")
            continue

        # Wildcard match (e.g. "@/*": ["src/*"] or "@components/*": ["src/components/*"])
        prefix, suffix = pattern.split("*", 1)
        if specifier.startswith(prefix) and (not suffix or specifier.endswith(suffix)):
            wildcard_part = specifier[len(prefix) : len(specifier) - len(suffix) if suffix else len(specifier)]

            for target in targets:
                target_substituted = target.replace("*", wildcard_part)
                candidate_base = os.path.normpath(os.path.join(base_url, target_substituted)).replace("\\", "/")

                # Repository containment check
                if candidate_base.startswith(".."):
                    continue

                if candidate_base in norm_known:
                    return (norm_known[candidate_base], f"tsconfig_alias:{pattern}")
                for ext in RESOLUTION_EXTENSIONS:
                    cand_ext = f"{candidate_base}{ext}"
                    if cand_ext in norm_known:
                        return (norm_known[cand_ext], f"tsconfig_alias:{pattern}")
                for idx in INDEX_FILENAMES:
                    cand_idx = f"{candidate_base}/{idx}"
                    if cand_idx in norm_known:
                        return (norm_known[cand_idx], f"tsconfig_alias:{pattern}")

            # Pattern matched, but no candidate file exists on disk
            return (None, f"tsconfig_alias:{pattern}")

    return None


def resolve_ts_module(
    source_file: str,
    specifier: str,
    is_computed: bool,
    all_known_files: Set[str],
    tsconfig: Optional[Dict[str, Any]] = None,
    declared_packages: Optional[Set[str]] = None,
) -> Tuple[str, Optional[str], Optional[str]]:
    """Determine the resolution status and concrete target for a TypeScript/JavaScript import.

    Returns (resolution_status, resolved_target_id, resolution_rule).
    Resolution statuses:
      - resolved_internal: Resolves deterministically to a file in all_known_files.
      - external_package: Bare package specifier (e.g. 'react', 'lodash').
      - unresolved_internal: Relative or path alias reference whose target file does not exist on disk.
      - unsupported_dynamic: Computed runtime expression (e.g. require(foo) or import('./' + bar)).
      - unsupported_resolution: Unsupported scheme, root escaping, or ambiguous target.
    """
    if is_computed:
        return ("unsupported_dynamic", None, "computed_runtime_expression")

    if not specifier or specifier.startswith(("#", "data:", "http:", "https:")):
        return ("unsupported_resolution", None, "unsupported_protocol_or_scheme")

    norm_known = {f.replace("\\", "/"): f for f in all_known_files}
    source_dir = os.path.dirname(source_file).replace("\\", "/")

    # 1. Relative import resolution (./ or ../)
    if specifier.startswith("./") or specifier.startswith("../"):
        candidate_raw = os.path.normpath(os.path.join(source_dir, specifier)).replace("\\", "/")

        # Security containment check: ensure candidate does not escape repository root
        if candidate_raw.startswith(".."):
            return ("unsupported_resolution", None, "escapes_repository_root")

        # 1a. Exact match
        if candidate_raw in norm_known:
            return ("resolved_internal", norm_known[candidate_raw], "relative_exact")

        # 1b. Common extensions
        for ext in RESOLUTION_EXTENSIONS:
            cand_ext = f"{candidate_raw}{ext}"
            if cand_ext in norm_known:
                return ("resolved_internal", norm_known[cand_ext], f"relative_extension:{ext}")

        # 1c. Directory index files
        for idx in INDEX_FILENAMES:
            cand_idx = f"{candidate_raw}/{idx}"
            if cand_idx in norm_known:
                return ("resolved_internal", norm_known[cand_idx], f"relative_index:{idx}")

        # Confirmed relative reference that cannot be found
        return ("unresolved_internal", None, "relative_missing_file")

    # 2. Path alias resolution (via tsconfig compilerOptions.paths)
    if tsconfig:
        paths = tsconfig.get("paths")
        base_url = tsconfig.get("baseUrl", ".") or "."
        if paths and isinstance(paths, dict):
            alias_match = _match_path_alias(specifier, paths, base_url, all_known_files)
            if alias_match is not None:
                matched_file, rule = alias_match
                if matched_file:
                    return ("resolved_internal", matched_file, rule)
                return ("unresolved_internal", None, f"{rule}_missing_target")

        # 3. BaseURL resolution without paths
        if base_url and base_url != ".":
            candidate_base = os.path.normpath(os.path.join(base_url, specifier)).replace("\\", "/")
            if not candidate_base.startswith(".."):
                if candidate_base in norm_known:
                    return ("resolved_internal", norm_known[candidate_base], "tsconfig_baseurl_exact")
                for ext in RESOLUTION_EXTENSIONS:
                    cand_ext = f"{candidate_base}{ext}"
                    if cand_ext in norm_known:
                        return ("resolved_internal", norm_known[cand_ext], f"tsconfig_baseurl_ext:{ext}")
                for idx in INDEX_FILENAMES:
                    cand_idx = f"{candidate_base}/{idx}"
                    if cand_idx in norm_known:
                        return ("resolved_internal", norm_known[cand_idx], f"tsconfig_baseurl_index:{idx}")

    # 4. Bare specifier -> External third-party package
    # Normalize scoped package (@scope/name) vs standard package (name/subpath)
    if specifier.startswith("@"):
        parts = specifier.split("/")
        top_pkg = "/".join(parts[:2]) if len(parts) >= 2 else specifier
    else:
        top_pkg = specifier.split("/")[0]

    return ("external_package", top_pkg, "external_package_specifier")


def parse_ts_files_batch(
    files: List[Dict[str, str]],
    all_known_files: Set[str],
    root_dir: Optional[str] = None,
    tsconfig: Optional[Dict[str, Any]] = None,
    package_json: Optional[Dict[str, Any]] = None,
) -> List[ParsedFileSummary]:
    """Parse a batch of TypeScript/JavaScript files in a single Node.js worker execution.

    Args:
        files: List of dicts, each with 'path' and optional 'content'. If 'content' is omitted,
               root_dir must be provided so the worker can read the file directly.
        all_known_files: Set of all discovered repository files (used for module resolution).
        root_dir: Optional absolute path to repository root.
        tsconfig: Optional parsed tsconfig compiler options.
        package_json: Optional parsed package.json metadata.
    """
    if not files:
        return []

    is_available, error_reason = check_ts_parser_available()
    if not is_available:
        # Gracefully report analysis_failed for all files without crashing
        summaries: List[ParsedFileSummary] = []
        for f in files:
            p = f["path"]
            summaries.append(
                ParsedFileSummary(
                    file_path=p,
                    status="analysis_failed",
                    line_count=0,
                    imports=[],
                    syntax_error=FileSyntaxError(
                        file_path=p,
                        error_message=f"TypeScript parser unavailable: {error_reason}",
                        line_number=1,
                        offset=1,
                    ),
                )
            )
        return summaries

    node_bin = shutil.which("node") or "node"
    worker_script = get_worker_script_path()

    payload = {
        "root_dir": root_dir or "",
        "files": files,
    }

    try:
        proc = subprocess.run(
            [node_bin, worker_script],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=30.0,
        )
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            raise RuntimeError(f"TypeScript worker exited with code {proc.returncode}: {err}")

        data = json.loads(proc.stdout)
        results = data.get("results", [])
    except Exception as ex:
        # Return analysis_failed summaries
        summaries = []
        for f in files:
            p = f["path"]
            summaries.append(
                ParsedFileSummary(
                    file_path=p,
                    status="analysis_failed",
                    line_count=0,
                    imports=[],
                    syntax_error=FileSyntaxError(
                        file_path=p,
                        error_message=f"Parser execution failed: {str(ex)}",
                        line_number=1,
                        offset=1,
                    ),
                )
            )
        return summaries

    declared_pkgs = package_json.get("declared_dependencies", set()) if package_json else set()

    summaries: List[ParsedFileSummary] = []
    for r in results:
        file_path = r["file_path"]
        status = r["status"]
        line_count = r.get("line_count", 0)
        raw_syntax = r.get("syntax_error")

        syntax_error = None
        if raw_syntax:
            syntax_error = FileSyntaxError(
                file_path=file_path,
                error_message=raw_syntax.get("error_message", "Syntax error"),
                line_number=raw_syntax.get("line_number"),
                offset=raw_syntax.get("offset"),
            )

        imports: List[ImportRecord] = []
        for imp in r.get("imports", []):
            specifier = imp["specifier"]
            is_computed = imp.get("is_computed", False)
            raw_statement = imp.get("raw_statement", f"import '{specifier}'")
            line_number = imp.get("line_number", 1)

            res_status, target_id, rule = resolve_ts_module(
                source_file=file_path,
                specifier=specifier,
                is_computed=is_computed,
                all_known_files=all_known_files,
                tsconfig=tsconfig,
                declared_packages=declared_pkgs,
            )

            is_internal = res_status == "resolved_internal"
            is_external = res_status == "external_package"

            # Derive imported symbol representation if present
            symbols = imp.get("symbols", [])
            primary_symbol = symbols[0]["name"] if symbols else None
            alias = symbols[0].get("imported") if symbols and symbols[0].get("imported") != primary_symbol else None

            # Determine target module display name
            if is_internal:
                target_module = target_id or specifier
            elif is_external:
                target_module = target_id or specifier
            else:
                target_module = specifier

            # Map internal resolution status into schema vocabulary
            if res_status == "resolved_internal":
                schema_status = "resolved_internal"
            elif res_status == "external_package":
                schema_status = "external_package"
            elif res_status == "unresolved_internal":
                schema_status = "unresolved_reference"
            elif res_status == "unsupported_dynamic":
                schema_status = "unsupported_dynamic"
            else:
                schema_status = "unsupported_resolution"

            imports.append(
                ImportRecord(
                    source_file=file_path,
                    target_module=target_module,
                    imported_symbol=primary_symbol,
                    alias=alias,
                    line_number=line_number,
                    is_relative=specifier.startswith("./") or specifier.startswith("../"),
                    level=specifier.count("../") if specifier.startswith("../") else (1 if specifier.startswith("./") else 0),
                    raw_statement=raw_statement,
                    is_stdlib=False,
                    is_internal=is_internal,
                    is_external=is_external,
                    resolution_status=schema_status,
                )
            )

        summaries.append(
            ParsedFileSummary(
                file_path=file_path,
                status=status,
                line_count=line_count,
                imports=imports,
                syntax_error=syntax_error,
            )
        )

    return summaries


def parse_ts_file(
    rel_path: str,
    source_code: str,
    all_known_files: Set[str],
    root_dir: Optional[str] = None,
    tsconfig: Optional[Dict[str, Any]] = None,
    package_json: Optional[Dict[str, Any]] = None,
) -> ParsedFileSummary:
    """Parse a single TypeScript/JavaScript source file and return its static analysis summary."""
    batch = parse_ts_files_batch(
        files=[{"path": rel_path, "content": source_code}],
        all_known_files=all_known_files,
        root_dir=root_dir,
        tsconfig=tsconfig,
        package_json=package_json,
    )
    if batch:
        return batch[0]
    return ParsedFileSummary(
        file_path=rel_path,
        status="analysis_failed",
        line_count=0,
        imports=[],
        syntax_error=FileSyntaxError(
            file_path=rel_path,
            error_message="Batch parser returned empty response",
            line_number=1,
            offset=1,
        ),
    )
