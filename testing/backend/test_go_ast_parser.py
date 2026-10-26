"""Unit and integration tests for Go AST parsing, go.mod manifests, and dependency extraction."""

import os
import tempfile
import uuid
import pytest

from oracle.inspection.ast_parser import ParsedFileSummary
from oracle.inspection.detector import detect_ecosystems
from oracle.inspection.go_parser import (
    GoModuleManifest,
    is_go_file,
    is_go_package_declared,
    is_go_stdlib_package,
    load_go_mod,
    parse_go_mod,
    parse_go_source,
)
from oracle.inspection.graph import build_dependency_graph
from oracle.inspection.service import inspection_service
from oracle.models.repository import Repository


def test_is_go_file():
    """Verify Go file extension checking."""
    assert is_go_file("main.go")
    assert is_go_file("pkg/server/handler.go")
    assert is_go_file("C:/projects/app/main.GO")
    assert not is_go_file("main.py")
    assert not is_go_file("index.ts")
    assert not is_go_file("go.mod")


def test_is_go_stdlib_package():
    """Verify identification of standard library packages."""
    assert is_go_stdlib_package("fmt")
    assert is_go_stdlib_package("net/http")
    assert is_go_stdlib_package("encoding/json")
    assert is_go_stdlib_package("crypto/sha256")
    assert is_go_stdlib_package("os")
    assert is_go_stdlib_package("context")
    assert not is_go_stdlib_package("github.com/gin-gonic/gin")
    assert not is_go_stdlib_package("golang.org/x/sync")


def test_parse_go_mod_complete():
    """Verify accurate extraction of go.mod directives."""
    content = """module example.com/my/project

go 1.22.0

require (
\tgithub.com/gin-gonic/gin v1.9.1
\tgithub.com/google/uuid v1.6.0 // indirect
\tgolang.org/x/crypto v0.21.0
)

require go.uber.org/zap v1.27.0

replace (
\tgolang.org/x/crypto => github.com/myfork/crypto v0.21.1
)
"""
    manifest = parse_go_mod(content)
    assert manifest.module_name == "example.com/my/project"
    assert manifest.go_version == "1.22.0"
    assert "github.com/gin-gonic/gin" in manifest.direct_dependencies
    assert "golang.org/x/crypto" in manifest.direct_dependencies
    assert "go.uber.org/zap" in manifest.direct_dependencies
    assert "github.com/google/uuid" in manifest.indirect_dependencies
    assert manifest.replaces.get("golang.org/x/crypto") == "github.com/myfork/crypto v0.21.1"
    assert "github.com/gin-gonic/gin" in manifest.all_declared_dependencies
    assert "github.com/google/uuid" in manifest.all_declared_dependencies


def test_is_go_package_declared():
    """Verify package declaration checking logic."""
    declared = {"github.com/gin-gonic/gin", "go.uber.org/zap"}
    assert is_go_package_declared("github.com/gin-gonic/gin", declared)
    assert is_go_package_declared("github.com/gin-gonic/gin/binding", declared)
    assert not is_go_package_declared("github.com/lib/pq", declared)


def test_parse_go_source_valid_imports():
    """Verify parsing of valid Go source code with standard, internal, and external imports."""
    content = """package main

import (
\t"fmt"
\t"net/http"
\talias "github.com/gin-gonic/gin"
\t"example.com/my/project/pkg/util"
)

func main() {
\tfmt.Println("Server started")
}
"""
    manifest = GoModuleManifest(
        module_name="example.com/my/project",
        direct_dependencies={"github.com/gin-gonic/gin"},
    )
    all_files = {"main.go", "pkg/util/helper.go"}
    summary = parse_go_source(
        file_path="main.go",
        content=content,
        module_manifest=manifest,
        all_repo_files=all_files,
    )

    assert summary.status == "analyzed"
    assert summary.syntax_error is None
    assert len(summary.imports) == 4

    # Check fmt
    imp_fmt = next(i for i in summary.imports if i.target_module == "fmt")
    assert imp_fmt.is_stdlib
    assert imp_fmt.resolution_status == "resolved_stdlib"

    # Check net/http
    imp_http = next(i for i in summary.imports if i.target_module == "net/http")
    assert imp_http.is_stdlib
    assert imp_http.resolution_status == "resolved_stdlib"

    # Check gin
    imp_gin = next(i for i in summary.imports if i.target_module == "github.com/gin-gonic/gin")
    assert imp_gin.is_external
    assert imp_gin.alias == "alias"
    assert imp_gin.resolution_status == "external_package"

    # Check internal util
    imp_util = next(i for i in summary.imports if "pkg/util" in i.target_module)
    assert imp_util.is_internal
    assert imp_util.resolution_status == "resolved_internal"


def test_parse_go_source_syntax_error_unclosed_brace():
    """Verify detection of unclosed opening token."""
    content = """package main

import "fmt"

func broken() {
\tfmt.Println("missing closing brace")
"""
    summary = parse_go_source("broken.go", content)
    assert summary.status == "syntax_error"
    assert summary.syntax_error is not None
    assert "Unclosed opening token '{'" in summary.syntax_error.error_message
    assert summary.syntax_error.line_number == 5


def test_parse_go_source_syntax_error_unmatched_brace():
    """Verify detection of unmatched closing token."""
    content = """package main

func broken() {
}
}
"""
    summary = parse_go_source("broken.go", content)
    assert summary.status == "syntax_error"
    assert summary.syntax_error is not None
    assert "Unmatched closing token '}'" in summary.syntax_error.error_message
    assert summary.syntax_error.line_number == 5


def test_parse_go_source_syntax_error_unclosed_comment():
    """Verify detection of unclosed multi-line comment."""
    content = """package main

/* This comment is never closed
func broken() {
}
"""
    summary = parse_go_source("broken.go", content)
    assert summary.status == "syntax_error"
    assert summary.syntax_error is not None
    assert "Unclosed multi-line comment" in summary.syntax_error.error_message


def test_go_ecosystem_detection():
    """Verify ecosystem detector recognizes Go projects from manifests and source files."""
    files = ["go.mod", "go.sum", "cmd/server/main.go", "pkg/api/router.go"]
    ecosystems = detect_ecosystems(files)
    go_eco = next((e for e in ecosystems if e.name == "go"), None)
    assert go_eco is not None
    assert go_eco.title == "Go Ecosystem"
    assert go_eco.confidence == "high"
    assert "go.mod" in go_eco.manifest_files
    assert go_eco.source_file_count == 2


def test_go_dependency_graph_integration():
    """Verify DependencyGraph generation from Go parsed summaries."""
    manifest = GoModuleManifest(
        module_name="example.com/demo",
        direct_dependencies={"github.com/gorilla/mux"},
    )
    main_code = """package main

import (
\t"fmt"
\t"github.com/gorilla/mux"
\t"example.com/demo/internal/service"
)

func main() {}
"""
    summary = parse_go_source(
        file_path="cmd/app/main.go",
        content=main_code,
        module_manifest=manifest,
        all_repo_files={"cmd/app/main.go", "internal/service/svc.go"},
    )

    graph = build_dependency_graph([summary])
    assert graph.total_nodes >= 3
    assert graph.stdlib_edge_count == 1
    assert graph.internal_edge_count == 1
    assert graph.external_edge_count == 1
    assert graph.unresolved_edge_count == 0


def test_inspection_service_with_go_repo(tmp_path):
    """Verify full InspectionService pipeline on a directory containing Go code and go.mod."""
    repo_dir = tmp_path / "go_repo"
    repo_dir.mkdir()

    mod_file = repo_dir / "go.mod"
    mod_file.write_text("module example.com/testgo\n\ngo 1.21.0\n", encoding="utf-8")

    src_file = repo_dir / "main.go"
    src_file.write_text("package main\n\nimport \"fmt\"\n\nfunc main() {\n\tfmt.Println(1)\n}\n", encoding="utf-8")

    repo = Repository(
        id=uuid.uuid4(),
        name="go-test-repo",
        source_type="local_directory",
        url=str(repo_dir),
    )

    report = inspection_service.inspect_repository(repo)
    assert report.status == "completed"
    assert report.total_files_analyzed >= 1
    assert len(report.syntax_errors) == 0
    assert any(e.name == "go" for e in report.ecosystems)


def test_parse_go_source_delimiters_inside_strings_ignored():
    """Verify that delimiter tokens inside interpreted strings do NOT cause false syntax errors."""
    code = """package main

import "fmt"

func main() {
\tfmt.Println("{")
\tfmt.Println("}")
\tfmt.Println("([)]")
\tfmt.Println("string with escaped \\" { \\" quote")
}
"""
    summary = parse_go_source("main.go", code)
    assert summary.status == "analyzed"
    assert summary.syntax_error is None


def test_parse_go_source_delimiters_inside_raw_strings_ignored():
    """Verify that delimiter tokens inside multiline raw string literals do NOT cause false syntax errors."""
    code = """package main

var tmpl = `
func mockTemplate() {
\tfor i := 0; i < 10; i++ {
\t\tif x > 0 {
\t\t\t// unmatched inside raw string: { { {
\t\t}
\t}
}
`

type User struct {
\tName string `json:"name" binding:"required"`
\tAge  int    `json:"age,omitempty"`
}

func main() {}
"""
    summary = parse_go_source("template.go", code)
    assert summary.status == "analyzed"
    assert summary.syntax_error is None


def test_parse_go_source_delimiters_inside_comments_ignored():
    """Verify that delimiter tokens inside single-line and multiline comments are ignored."""
    code = """package main

// Unclosed brace in single-line comment: {
// Unclosed paren in single-line comment: (
/*
   Unclosed brace in block comment: {
   Unmatched closing bracket in block comment: ]
*/

func validFunc() {
\t// { inside function body
\t/* } inside function body */
}
"""
    summary = parse_go_source("comments.go", code)
    assert summary.status == "analyzed"
    assert summary.syntax_error is None


def test_parse_go_source_rune_literals_ignored():
    """Verify that rune literals with delimiters and escapes do not corrupt the delimiter stack."""
    code = """package main

func processRunes() {
\tr1 := '{'
\tr2 := '}'
\tr3 := '('
\tr4 := ')'
\tr5 := '['
\tr6 := ']'
\tr7 := '\\''
\tr8 := '\\\\'
}
"""
    summary = parse_go_source("runes.go", code)
    assert summary.status == "analyzed"
    assert summary.syntax_error is None


def test_parse_go_source_detects_unclosed_raw_string():
    """Verify detection of unclosed raw string literal."""
    code = """package main

var s = `unclosed raw string without terminating backtick
func foo() {}
"""
    summary = parse_go_source("bad_raw.go", code)
    assert summary.status == "syntax_error"
    assert summary.syntax_error is not None
    assert "Unclosed raw string literal" in summary.syntax_error.error_message
    assert summary.syntax_error.line_number == 3


def test_parse_go_source_detects_unclosed_interpreted_string():
    """Verify detection of unclosed interpreted string broken by newline."""
    code = """package main

func foo() {
\ts := "unclosed string before newline
}
"""
    summary = parse_go_source("bad_str.go", code)
    assert summary.status == "syntax_error"
    assert summary.syntax_error is not None
    assert "String literal not terminated" in summary.syntax_error.error_message


def test_parse_go_source_genuine_error_with_strings_present():
    """Verify genuine syntax error is detected even when strings with delimiters exist in the same file."""
    code = """package main

import "fmt"

func main() {
\tfmt.Println("{ this string has a brace }")
\t// Real missing closing brace below
\tif true {
\t\tfmt.Println("ok")
"""
    summary = parse_go_source("real_defect.go", code)
    assert summary.status == "syntax_error"
    assert summary.syntax_error is not None
    assert "Unclosed opening token '{'" in summary.syntax_error.error_message
    # Should point to the unclosed if or func, not the string line
    assert summary.syntax_error.line_number in (5, 8)
