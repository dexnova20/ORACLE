"""Unit and integration tests for TypeScript/JavaScript AST parsing, import extraction, and module resolution."""

import os
import tempfile
import pytest

from oracle.inspection.ast_parser import ParsedFileSummary
from oracle.inspection.ts_parser import (
    TS_JS_EXTENSIONS,
    check_ts_parser_available,
    is_ts_js_file,
    load_package_json,
    load_tsconfig,
    parse_ts_file,
    parse_ts_files_batch,
    resolve_ts_module,
    strip_json_comments_and_trailing_commas,
)


def test_ts_parser_availability():
    """Verify that Node.js and TypeScript compiler worker are available in this environment."""
    is_avail, reason = check_ts_parser_available()
    assert is_avail is True, f"TypeScript worker should be available: {reason}"
    assert reason is None


def test_supported_extensions_recognition():
    """Verify that is_ts_js_file correctly recognizes all 8 supported file extensions."""
    for ext in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"):
        assert is_ts_js_file(f"src/module{ext}") is True
        assert is_ts_js_file(f"SRC/MODULE{ext.upper()}") is True

    for non_ext in (".py", ".json", ".rs", ".go", ".java", ".cpp", ".txt", ".md"):
        assert is_ts_js_file(f"src/module{non_ext}") is False


def test_strip_json_comments_and_trailing_commas():
    """Verify stripping of comments and trailing commas from tsconfig and package.json."""
    raw = """{
      // Single-line comment
      "compilerOptions": {
        /* Multi-line
           comment */
        "baseUrl": ".",
        "paths": {
          "@/*": ["src/*"],
        },
      },
    }"""
    cleaned = strip_json_comments_and_trailing_commas(raw)
    assert "// Single-line" not in cleaned
    assert "Multi-line" not in cleaned
    import json
    parsed = json.loads(cleaned)
    assert parsed["compilerOptions"]["baseUrl"] == "."
    assert parsed["compilerOptions"]["paths"]["@/*"] == ["src/*"]


def test_parse_ts_syntax_valid_tsx():
    """Verify parsing of valid modern TSX with types, interfaces, and components."""
    code = """
    import React, { useState } from "react";
    import type { FC } from "react";
    import { Button } from "./Button";

    export interface Props {
      title: string;
      count?: number;
    }

    export const App: FC<Props> = ({ title, count = 0 }) => {
      const [val, setVal] = useState<number>(count);
      return (
        <div className="container">
          <h1>{title}</h1>
          <Button onClick={() => setVal(v => v + 1)}>Count: {val}</Button>
        </div>
      );
    };
    """
    summary = parse_ts_file(
        rel_path="src/App.tsx",
        source_code=code,
        all_known_files={"src/App.tsx", "src/Button.tsx"},
    )
    assert summary.status == "analyzed"
    assert summary.syntax_error is None
    assert summary.line_count > 10
    assert len(summary.imports) == 3

    # Check imported symbols
    react_imp = summary.imports[0]
    assert react_imp.target_module == "react"
    assert react_imp.is_external is True

    type_imp = summary.imports[1]
    assert type_imp.target_module == "react"

    button_imp = summary.imports[2]
    assert button_imp.target_module == "src/Button.tsx"
    assert button_imp.is_internal is True
    assert button_imp.resolution_status == "resolved_internal"


def test_parse_ts_syntax_error_exact_coordinates():
    """Verify that syntax errors produce exact line numbers, column offsets, and error messages."""
    broken_code = """
    function compute() {
      const x = ;
      return x;
    }
    """
    summary = parse_ts_file(
        rel_path="src/broken.ts",
        source_code=broken_code,
        all_known_files={"src/broken.ts"},
    )
    assert summary.status == "syntax_error"
    assert summary.syntax_error is not None
    assert summary.syntax_error.file_path == "src/broken.ts"
    assert summary.syntax_error.line_number == 3
    assert summary.syntax_error.offset == 17
    assert "Expression expected" in summary.syntax_error.error_message


def test_comments_and_strings_immune_to_false_positives():
    """Verify that import-like tokens inside comments, string literals, and template literals are ignored."""
    code = """
    // import { broken } from "./missing_comment";
    /* import { fake } from "../unresolved_block"; */
    import { real } from "./real_module";

    export function test() {
      const s1 = "import { evil } from './nowhere';";
      const s2 = `import { evil2 } from "./nowhere2";`;
      return s1 + s2;
    }
    """
    summary = parse_ts_file(
        rel_path="src/immunity.ts",
        source_code=code,
        all_known_files={"src/immunity.ts", "src/real_module.ts"},
    )
    assert summary.status == "analyzed"
    assert summary.syntax_error is None
    assert len(summary.imports) == 1
    assert summary.imports[0].target_module == "src/real_module.ts"


def test_commonjs_require_and_dynamic_import():
    """Verify extraction of CommonJS require() calls and dynamic import() calls."""
    code = """
    const fs = require("fs");
    const local = require("./local_config.json");
    const computed = require(process.env.DYNAMIC_PATH);

    async function load() {
      const mod = await import("./dynamic_feature");
      const computedDynamic = await import("./plugins/" + name);
      return { mod, computedDynamic };
    }
    """
    summary = parse_ts_file(
        rel_path="src/commonjs.ts",
        source_code=code,
        all_known_files={"src/commonjs.ts", "src/local_config.json", "src/dynamic_feature.ts"},
    )
    assert summary.status == "analyzed"
    # Expected: fs, ./local_config.json, computed require, ./dynamic_feature, computed import
    assert len(summary.imports) == 5

    res_by_target = {i.raw_statement: i for i in summary.imports}
    # Static require to local JSON
    assert any("local_config" in k for k in res_by_target)
    # Computed require
    computed_req = [i for i in summary.imports if "DYNAMIC_PATH" in i.raw_statement][0]
    assert computed_req.resolution_status == "unsupported_dynamic"

    # Computed dynamic import
    computed_dyn = [i for i in summary.imports if "plugins" in i.raw_statement][0]
    assert computed_dyn.resolution_status == "unsupported_dynamic"


def test_re_export_declarations():
    """Verify extraction of barrel file re-export statements."""
    code = """
    export { Button } from "./Button";
    export * from "./types";
    export * as utils from "./utils";
    """
    summary = parse_ts_file(
        rel_path="src/index.ts",
        source_code=code,
        all_known_files={"src/index.ts", "src/Button.tsx", "src/types.ts", "src/utils.ts"},
    )
    assert summary.status == "analyzed"
    assert len(summary.imports) == 3
    assert all(i.is_internal for i in summary.imports)
    assert summary.imports[0].target_module == "src/Button.tsx"
    assert summary.imports[1].target_module == "src/types.ts"
    assert summary.imports[2].target_module == "src/utils.ts"


def test_tsconfig_path_alias_resolution():
    """Verify resolution of TypeScript path aliases configured in tsconfig compilerOptions.paths."""
    tsconfig = {
        "baseUrl": ".",
        "paths": {
            "@/*": ["src/*"],
            "@components/*": ["src/components/*"],
            "@utils": ["src/lib/utils"],
        },
    }
    known_files = {
        "src/app.ts",
        "src/components/Header.tsx",
        "src/lib/utils.ts",
        "src/services/auth.ts",
    }

    # 1. Alias matching @components/*
    st, target, rule = resolve_ts_module(
        source_file="src/app.ts",
        specifier="@components/Header",
        is_computed=False,
        all_known_files=known_files,
        tsconfig=tsconfig,
    )
    assert st == "resolved_internal"
    assert target == "src/components/Header.tsx"
    assert "tsconfig_alias" in rule

    # 2. Alias matching exact @utils
    st, target, rule = resolve_ts_module(
        source_file="src/app.ts",
        specifier="@utils",
        is_computed=False,
        all_known_files=known_files,
        tsconfig=tsconfig,
    )
    assert st == "resolved_internal"
    assert target == "src/lib/utils.ts"

    # 3. Alias matching @/* with wildcard
    st, target, rule = resolve_ts_module(
        source_file="src/app.ts",
        specifier="@/services/auth",
        is_computed=False,
        all_known_files=known_files,
        tsconfig=tsconfig,
    )
    assert st == "resolved_internal"
    assert target == "src/services/auth.ts"

    # 4. Alias matching pattern but target does NOT exist on disk -> unresolved_internal
    st, target, rule = resolve_ts_module(
        source_file="src/app.ts",
        specifier="@/services/nonexistent",
        is_computed=False,
        all_known_files=known_files,
        tsconfig=tsconfig,
    )
    assert st == "unresolved_internal"
    assert target is None


def test_directory_index_file_resolution():
    """Verify resolution of directory imports to index.ts, index.tsx, index.js."""
    known_files = {
        "src/main.ts",
        "src/utils/index.ts",
        "src/ui/index.tsx",
    }

    st, target, rule = resolve_ts_module(
        source_file="src/main.ts",
        specifier="./utils",
        is_computed=False,
        all_known_files=known_files,
    )
    assert st == "resolved_internal"
    assert target == "src/utils/index.ts"

    st, target, rule = resolve_ts_module(
        source_file="src/main.ts",
        specifier="./ui",
        is_computed=False,
        all_known_files=known_files,
    )
    assert st == "resolved_internal"
    assert target == "src/ui/index.tsx"


def test_repository_root_containment_escapes_prohibited():
    """Verify that path traversal attempts escaping the repository root are rejected."""
    st, target, rule = resolve_ts_module(
        source_file="src/main.ts",
        specifier="../../../../etc/passwd",
        is_computed=False,
        all_known_files={"src/main.ts"},
    )
    assert st == "unsupported_resolution"
    assert rule == "escapes_repository_root"


def test_package_json_declaration_audit():
    """Verify that external package references are cross-checked against package.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_json = os.path.join(tmpdir, "package.json")
        with open(pkg_json, "w", encoding="utf-8") as f:
            f.write('{\n  "dependencies": {\n    "lodash": "^4.17.21"\n  }\n}')

        parsed = load_package_json(tmpdir)
        declared = parsed["declared_dependencies"]
        assert "lodash" in declared
        assert "axios" not in declared

        # Declared package
        st, pkg, _ = resolve_ts_module(
            source_file="src/app.ts",
            specifier="lodash",
            is_computed=False,
            all_known_files={"src/app.ts"},
            declared_packages=declared,
        )
        assert st == "external_package"
        assert pkg == "lodash"
