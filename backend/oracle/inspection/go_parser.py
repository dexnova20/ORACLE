"""Safe static Go AST analysis, dependency extraction, and manifest auditing without code execution.

Analyzes Go source files (.go) and Go module manifests (go.mod) to capture
precise syntax diagnostics, import declarations, and package resolution
without compiling or executing target code.
"""

from dataclasses import dataclass, field
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from oracle.inspection.ast_parser import FileSyntaxError, ImportRecord, ParsedFileSummary

# Supported Go source file extensions
GO_EXTENSIONS: Set[str] = {".go"}

# Standard library packages in the Go runtime (major packages and prefixes)
GO_STDLIB_PACKAGES: Set[str] = {
    "archive/tar", "archive/zip", "bufio", "bytes", "compress/bzip2",
    "compress/flate", "compress/gzip", "compress/lzw", "compress/zlib",
    "container/heap", "container/list", "container/ring", "context",
    "crypto", "crypto/aes", "crypto/cipher", "crypto/des", "crypto/dsa",
    "crypto/ecdsa", "crypto/ed25519", "crypto/elliptic", "crypto/hmac",
    "crypto/md5", "crypto/rand", "crypto/rc4", "crypto/rsa", "crypto/sha1",
    "crypto/sha256", "crypto/sha512", "crypto/subtle", "crypto/tls",
    "crypto/x509", "database/sql", "database/sql/driver", "debug/buildinfo",
    "debug/dwarf", "debug/elf", "debug/gosym", "debug/macho", "debug/pe",
    "debug/plan9obj", "embed", "encoding", "encoding/ascii85", "encoding/asn1",
    "encoding/base32", "encoding/base64", "encoding/binary", "encoding/csv",
    "encoding/gob", "encoding/hex", "encoding/json", "encoding/pem",
    "encoding/xml", "errors", "expvar", "flag", "fmt", "go/ast",
    "go/build", "go/build/constraint", "go/constant", "go/doc", "go/format",
    "go/parser", "go/printer", "go/scanner", "go/token", "go/types",
    "hash", "hash/adler32", "hash/crc32", "hash/crc64", "hash/fnv",
    "hash/maphash", "html", "html/template", "image", "image/color",
    "image/draw", "image/gif", "image/jpeg", "image/png", "index/suffixarray",
    "io", "io/fs", "io/ioutil", "log", "log/slog", "log/syslog", "math",
    "math/big", "math/bits", "math/cmplx", "math/rand", "mime",
    "mime/multipart", "mime/quotedprintable", "net", "net/http",
    "net/http/cgi", "net/http/cookiejar", "net/http/fcgi", "net/http/httptest",
    "net/http/httptrace", "net/http/httputil", "net/http/pprof", "net/mail",
    "net/netip", "net/rpc", "net/rpc/jsonrpc", "net/smtp", "net/textproto",
    "net/url", "os", "os/exec", "os/signal", "os/user", "path",
    "path/filepath", "plugin", "reflect", "regexp", "regexp/syntax",
    "runtime", "runtime/cgo", "runtime/debug", "runtime/metrics",
    "runtime/pprof", "runtime/race", "runtime/trace", "sort", "strconv",
    "strings", "sync", "sync/atomic", "syscall", "testing", "testing/fstest",
    "testing/iotest", "testing/quick", "text/scanner", "text/tabwriter",
    "text/template", "text/template/parse", "time", "time/tzdata",
    "unicode", "unicode/utf16", "unicode/utf8", "unsafe",
}


def is_go_file(path: str) -> bool:
    """Check if the given relative or absolute file path is a Go source file."""
    _, ext = os.path.splitext(path)
    return ext.lower() in GO_EXTENSIONS


def is_go_stdlib_package(pkg_path: str) -> bool:
    """Determine whether an imported path belongs to the Go standard library."""
    clean = pkg_path.strip().strip('"').strip("'")
    if clean in GO_STDLIB_PACKAGES:
        return True
    parts = clean.split("/")
    if len(parts) == 1 and "." not in parts[0]:
        return True
    return False


@dataclass
class GoModuleManifest:
    """Structured representation of a parsed go.mod file."""

    module_name: str
    go_version: Optional[str] = None
    direct_dependencies: Set[str] = field(default_factory=set)
    indirect_dependencies: Set[str] = field(default_factory=set)
    replaces: Dict[str, str] = field(default_factory=dict)

    @property
    def all_declared_dependencies(self) -> Set[str]:
        """Union of direct and indirect dependencies."""
        return self.direct_dependencies | self.indirect_dependencies


def parse_go_mod(content: str) -> GoModuleManifest:
    """Parse a go.mod file content cleanly without executing external go tools."""
    lines = content.splitlines()
    module_name = ""
    go_version = None
    direct_deps: Set[str] = set()
    indirect_deps: Set[str] = set()
    replaces: Dict[str, str] = {}

    in_require_block = False
    in_replace_block = False

    for line in lines:
        stripped = line.strip()
        # Remove comments
        if "//" in stripped:
            comment_idx = stripped.index("//")
            comment_text = stripped[comment_idx:]
            code_text = stripped[:comment_idx].strip()
        else:
            comment_text = ""
            code_text = stripped

        if not code_text and not stripped.startswith("//"):
            continue

        # Module directive
        if code_text.startswith("module "):
            module_name = code_text[len("module "):].strip()
            continue

        # Go version directive
        if code_text.startswith("go "):
            go_version = code_text[len("go "):].strip()
            continue

        # Require block entry / exit
        if code_text == "require (":
            in_require_block = True
            continue
        if in_require_block:
            if code_text == ")":
                in_require_block = False
                continue
            parts = code_text.split()
            if parts:
                pkg = parts[0]
                if "// indirect" in stripped:
                    indirect_deps.add(pkg)
                else:
                    direct_deps.add(pkg)
            continue

        # Single-line require
        if code_text.startswith("require "):
            req_body = code_text[len("require "):].strip()
            parts = req_body.split()
            if parts:
                pkg = parts[0]
                if "// indirect" in stripped:
                    indirect_deps.add(pkg)
                else:
                    direct_deps.add(pkg)
            continue

        # Replace block entry / exit
        if code_text == "replace (":
            in_replace_block = True
            continue
        if in_replace_block:
            if code_text == ")":
                in_replace_block = False
                continue
            if "=>" in code_text:
                lhs, rhs = code_text.split("=>", 1)
                replaces[lhs.strip()] = rhs.strip()
            continue

        if code_text.startswith("replace "):
            rep_body = code_text[len("replace "):].strip()
            if "=>" in rep_body:
                lhs, rhs = rep_body.split("=>", 1)
                replaces[lhs.strip()] = rhs.strip()

    return GoModuleManifest(
        module_name=module_name or "unknown_module",
        go_version=go_version,
        direct_dependencies=direct_deps,
        indirect_dependencies=indirect_deps,
        replaces=replaces,
    )


def load_go_mod(root_dir: str) -> Optional[GoModuleManifest]:
    """Search for and parse go.mod at repository root or first-level subdirectories."""
    candidates = [
        os.path.join(root_dir, "go.mod"),
    ]
    try:
        for entry in os.scandir(root_dir):
            if entry.is_dir() and not entry.name.startswith("."):
                sub_mod = os.path.join(entry.path, "go.mod")
                candidates.append(sub_mod)
    except Exception:
        pass

    for path in candidates:
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return parse_go_mod(content)
            except Exception:
                pass
    return None


@dataclass
class _RawGoImport:
    specifier: str
    alias: Optional[str]
    line_number: int
    raw_statement: str


def _parse_go_import_line(text: str, line_no: int) -> Optional[_RawGoImport]:
    """Parse a single Go import clause (e.g. 'fmt', 'myalias \"net/http\"', '_ \"github.com/lib/pq\"')."""
    cleaned = text.strip().rstrip(";")
    if not cleaned:
        return None

    match = re.search(r'"([^"]+)"', cleaned)
    if not match:
        return None

    pkg_path = match.group(1)
    prefix = cleaned[:match.start()].strip()

    alias = None
    if prefix:
        alias = prefix

    return _RawGoImport(
        specifier=pkg_path,
        alias=alias,
        line_number=line_no,
        raw_statement=text.strip(),
    )


def is_go_package_declared(target_pkg: str, declared_deps: Set[str]) -> bool:
    """Check if an external Go import path is covered by declared dependencies in go.mod."""
    clean = target_pkg.strip().lower()
    if clean in declared_deps:
        return True
    for dep in declared_deps:
        dep_clean = dep.lower()
        if clean == dep_clean:
            return True
        if clean.startswith(dep_clean + "/"):
            return True
        if dep_clean.startswith(clean + "/"):
            return True
    return False


def parse_go_source(
    file_path: str,
    content: str,
    module_manifest: Optional[GoModuleManifest] = None,
    all_repo_files: Optional[Set[str]] = None,
    repo_root: Optional[str] = None,
) -> ParsedFileSummary:
    """Parse Go source text statically, extract package & imports, and capture syntax diagnostics.

    Performs rigorous zero-code-execution lexical scanning that accurately tracks:
    - Delimiter balancing ({}, (), []) strictly outside comments, string literals, and runes.
    - Raw multiline string literals (``...``) with unclosed literal detection.
    - Interpreted string literals ("...") with escape sequences (\", \\).
    - Rune literals ('...') with escape sequences.
    - Single-line comments (//...) and multiline comment blocks (/*...*/).
    """
    lines = content.splitlines()
    total_lines = len(lines)
    syntax_errors: List[FileSyntaxError] = []
    raw_imports: List[_RawGoImport] = []

    if not content.strip():
        return ParsedFileSummary(
            file_path=file_path,
            status="analyzed",
            line_count=0,
            imports=[],
            syntax_error=None,
        )

    # 1. Rigorous Lexical Scanner & Delimiter Balancer
    brace_stack: List[Tuple[str, int, int]] = []

    STATE_NORMAL = 0
    STATE_LINE_COMMENT = 1
    STATE_BLOCK_COMMENT = 2
    STATE_INTERPRETED_STR = 3
    STATE_RAW_STR = 4
    STATE_RUNE = 5

    state = STATE_NORMAL
    block_comment_start = (1, 1)
    raw_str_start = (1, 1)
    interp_str_start = (1, 1)

    cur_line = 1
    cur_col = 0
    n = len(content)
    idx = 0

    # Package & Import extraction state
    package_name = ""
    in_import_block = False
    import_block_start_line = 0

    while idx < n:
        ch = content[idx]
        cur_col += 1

        if ch == "\n":
            cur_line += 1
            cur_col = 0
            if state == STATE_LINE_COMMENT:
                state = STATE_NORMAL
            elif state == STATE_INTERPRETED_STR:
                # Go disallows unescaped newlines in interpreted string literals
                syntax_errors.append(
                    FileSyntaxError(
                        file_path=file_path,
                        error_message="SyntaxError: String literal not terminated before newline",
                        line_number=interp_str_start[0],
                        offset=interp_str_start[1],
                    )
                )
                state = STATE_NORMAL
            idx += 1
            continue

        if state == STATE_NORMAL:
            next_ch = content[idx + 1] if idx + 1 < n else ""
            if ch == "/" and next_ch == "/":
                state = STATE_LINE_COMMENT
                idx += 2
                cur_col += 1
                continue
            elif ch == "/" and next_ch == "*":
                state = STATE_BLOCK_COMMENT
                block_comment_start = (cur_line, cur_col)
                idx += 2
                cur_col += 1
                continue
            elif ch == '"':
                state = STATE_INTERPRETED_STR
                interp_str_start = (cur_line, cur_col)
                idx += 1
                continue
            elif ch == "`":
                state = STATE_RAW_STR
                raw_str_start = (cur_line, cur_col)
                idx += 1
                continue
            elif ch == "'":
                state = STATE_RUNE
                idx += 1
                continue
            elif ch in "{[(":
                brace_stack.append((ch, cur_line, cur_col))
                idx += 1
                continue
            elif ch in "}])":
                matching = {"}": "{", "]": "[", ")": "("}[ch]
                if brace_stack and brace_stack[-1][0] == matching:
                    brace_stack.pop()
                elif brace_stack:
                    unmatched, u_line, u_col = brace_stack.pop()
                    syntax_errors.append(
                        FileSyntaxError(
                            file_path=file_path,
                            error_message=f"SyntaxError: Unmatched closing token '{ch}'",
                            line_number=cur_line,
                            offset=cur_col,
                        )
                    )
                else:
                    syntax_errors.append(
                        FileSyntaxError(
                            file_path=file_path,
                            error_message=f"SyntaxError: Unmatched closing token '{ch}'",
                            line_number=cur_line,
                            offset=cur_col,
                        )
                    )
                idx += 1
                continue
            else:
                idx += 1
                continue

        elif state == STATE_LINE_COMMENT:
            idx += 1
            continue

        elif state == STATE_BLOCK_COMMENT:
            next_ch = content[idx + 1] if idx + 1 < n else ""
            if ch == "*" and next_ch == "/":
                state = STATE_NORMAL
                idx += 2
                cur_col += 1
                continue
            idx += 1
            continue

        elif state == STATE_INTERPRETED_STR:
            if ch == "\\":
                idx += 1
                cur_col += 1
                if idx < n:
                    if content[idx] == "\n":
                        cur_line += 1
                        cur_col = 0
                    idx += 1
                continue
            elif ch == '"':
                state = STATE_NORMAL
                idx += 1
                continue
            idx += 1
            continue

        elif state == STATE_RAW_STR:
            if ch == "`":
                state = STATE_NORMAL
                idx += 1
                continue
            idx += 1
            continue

        elif state == STATE_RUNE:
            if ch == "\\":
                idx += 1
                cur_col += 1
                if idx < n:
                    idx += 1
                continue
            elif ch == "'":
                state = STATE_NORMAL
                idx += 1
                continue
            idx += 1
            continue

    # Post-scan EOF validations
    if state == STATE_BLOCK_COMMENT:
        syntax_errors.append(
            FileSyntaxError(
                file_path=file_path,
                error_message="SyntaxError: Unclosed multi-line comment block '/*'",
                line_number=block_comment_start[0],
                offset=block_comment_start[1],
            )
        )
    elif state == STATE_RAW_STR:
        syntax_errors.append(
            FileSyntaxError(
                file_path=file_path,
                error_message="SyntaxError: Unclosed raw string literal '`'",
                line_number=raw_str_start[0],
                offset=raw_str_start[1],
            )
        )
    elif state == STATE_INTERPRETED_STR:
        syntax_errors.append(
            FileSyntaxError(
                file_path=file_path,
                error_message="SyntaxError: Unclosed string literal '\"'",
                line_number=interp_str_start[0],
                offset=interp_str_start[1],
            )
        )
    elif brace_stack:
        unclosed, u_line, u_col = brace_stack[-1]
        syntax_errors.append(
            FileSyntaxError(
                file_path=file_path,
                error_message=f"SyntaxError: Unclosed opening token '{unclosed}'",
                line_number=u_line,
                offset=u_col,
            )
        )

    # 2. Extract package and import declarations safely (ignoring comments)
    in_block_c = False
    in_import = False
    for line_idx, line in enumerate(lines, start=1):
        cleaned_line = ""
        c_idx = 0
        l_len = len(line)
        while c_idx < l_len:
            if in_block_c:
                if line[c_idx:c_idx + 2] == "*/":
                    in_block_c = False
                    c_idx += 2
                else:
                    c_idx += 1
                continue

            if line[c_idx:c_idx + 2] == "/*":
                if "*/" in line[c_idx + 2:]:
                    end_c = line.index("*/", c_idx + 2)
                    c_idx = end_c + 2
                    continue
                else:
                    in_block_c = True
                    break

            if line[c_idx:c_idx + 2] == "//":
                break

            cleaned_line += line[c_idx]
            c_idx += 1

        stripped = cleaned_line.strip()
        if not stripped:
            continue

        if stripped.startswith("package "):
            pkg_parts = stripped.split()
            if len(pkg_parts) >= 2:
                package_name = pkg_parts[1].rstrip(";")
            else:
                syntax_errors.append(
                    FileSyntaxError(
                        file_path=file_path,
                        error_message="SyntaxError: Expected package name after 'package' keyword",
                        line_number=line_idx,
                        offset=1,
                    )
                )
            continue

        if stripped == "import (" or stripped.startswith("import ("):
            in_import = True
            continue

        if in_import:
            if stripped == ")" or stripped.startswith(")"):
                in_import = False
                continue
            rec = _parse_go_import_line(stripped, line_idx)
            if rec:
                raw_imports.append(rec)
            continue

        if stripped.startswith("import "):
            import_tail = stripped[len("import "):].strip()
            rec = _parse_go_import_line(import_tail, line_idx)
            if rec:
                raw_imports.append(rec)
            continue

    # 2. Resolve imports and check against go.mod declarations
    resolved_imports: List[ImportRecord] = []
    module_name = module_manifest.module_name if module_manifest else ""
    declared_deps = module_manifest.all_declared_dependencies if module_manifest else set()

    for imp in raw_imports:
        raw_target = imp.specifier

        if is_go_stdlib_package(raw_target):
            resolved_imports.append(
                ImportRecord(
                    source_file=file_path,
                    target_module=raw_target,
                    imported_symbol=None,
                    alias=imp.alias,
                    line_number=imp.line_number,
                    is_relative=False,
                    level=0,
                    raw_statement=imp.raw_statement,
                    is_stdlib=True,
                    is_internal=False,
                    is_external=False,
                    resolution_status="resolved_stdlib",
                )
            )
        elif module_name and (raw_target == module_name or raw_target.startswith(module_name + "/")):
            sub_path = raw_target[len(module_name):].lstrip("/")
            resolved_path = None
            if all_repo_files:
                for f in all_repo_files:
                    if sub_path and (f.startswith(sub_path + "/") or f.startswith(sub_path + "\\") or f == sub_path):
                        resolved_path = f
                        break
            resolved_imports.append(
                ImportRecord(
                    source_file=file_path,
                    target_module=raw_target,
                    imported_symbol=None,
                    alias=imp.alias,
                    line_number=imp.line_number,
                    is_relative=False,
                    level=0,
                    raw_statement=imp.raw_statement,
                    is_stdlib=False,
                    is_internal=True,
                    is_external=False,
                    resolution_status="resolved_internal" if resolved_path else "unresolved_reference",
                )
            )
        elif raw_target.startswith("./") or raw_target.startswith("../"):
            base_dir = os.path.dirname(file_path)
            candidate_dir = os.path.normpath(os.path.join(base_dir, raw_target)).replace("\\", "/")
            resolved_path = None
            if all_repo_files:
                for f in all_repo_files:
                    if candidate_dir in f:
                        resolved_path = f
                        break
            resolved_imports.append(
                ImportRecord(
                    source_file=file_path,
                    target_module=raw_target,
                    imported_symbol=None,
                    alias=imp.alias,
                    line_number=imp.line_number,
                    is_relative=True,
                    level=raw_target.count("../") if raw_target.startswith("../") else 1,
                    raw_statement=imp.raw_statement,
                    is_stdlib=False,
                    is_internal=True,
                    is_external=False,
                    resolution_status="resolved_internal" if resolved_path else "unresolved_reference",
                )
            )
        else:
            # Third-party package (e.g. github.com/gin-gonic/gin)
            is_declared = is_go_package_declared(raw_target, declared_deps) if declared_deps else True
            resolved_imports.append(
                ImportRecord(
                    source_file=file_path,
                    target_module=raw_target,
                    imported_symbol=None,
                    alias=imp.alias,
                    line_number=imp.line_number,
                    is_relative=False,
                    level=0,
                    raw_statement=imp.raw_statement,
                    is_stdlib=False,
                    is_internal=False,
                    is_external=True,
                    resolution_status="external_package" if is_declared else "unresolved_reference",
                )
            )

    status = "syntax_error" if syntax_errors else "analyzed"

    return ParsedFileSummary(
        file_path=file_path,
        status=status,
        line_count=total_lines,
        imports=resolved_imports,
        syntax_error=syntax_errors[0] if syntax_errors else None,
    )
