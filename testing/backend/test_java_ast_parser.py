"""Unit tests for safe Java AST analysis, module resolution, and manifest parsing (Implementation 014)."""

import os
import tempfile
import pytest

from oracle.inspection.java_parser import (
    check_java_parser_available,
    extract_declared_java_dependencies,
    is_java_file,
    is_java_package_declared,
    is_java_stdlib_package,
    parse_gradle_build,
    parse_java_file,
    parse_java_files_batch,
    parse_maven_pom,
)


def test_java_parser_availability():
    """Verify that Java runtime (OpenJDK 21) is available and the Java AST worker is functional."""
    is_avail, err_msg = check_java_parser_available()
    assert is_avail is True, f"Java parser worker should be available: {err_msg}"
    assert err_msg is None


def test_is_java_file():
    """Verify that file extension check correctly identifies .java files."""
    assert is_java_file("User.java") is True
    assert is_java_file("src/main/java/com/example/Service.java") is True
    assert is_java_file("Service.JAVA") is True
    assert is_java_file("script.py") is False
    assert is_java_file("Component.tsx") is False
    assert is_java_file("build.gradle") is False


def test_java_syntax_valid_record_and_interface():
    """Verify that Java 21 syntax (records, interfaces, enums, nested classes) parses accurately."""
    code = """package com.example.domain;

import java.util.List;

public record UserProfile(String id, String email) {
    public static class Preference {
        private boolean darkMode = true;
    }
}

interface Identifiable {
    String getId();
}

enum Status {
    ACTIVE,
    PENDING,
    SUSPENDED
}
"""
    with tempfile.TemporaryDirectory() as td:
        file_path = "src/main/java/com/example/domain/UserProfile.java"
        summary = parse_java_file(file_path, code, root_dir=td)

        assert summary.status == "analyzed"
        assert summary.syntax_error is None
        assert summary.line_count >= 15
        assert len(summary.imports) == 1
        assert summary.imports[0].is_stdlib is True


def test_java_syntax_error_exact_coordinates():
    """Verify that Java syntax errors are captured with exact line and column provenance."""
    code = """package com.example.service;

public class BrokenParser {
    public void execute() {
        int result = ;
    }
}
"""
    with tempfile.TemporaryDirectory() as td:
        file_path = "src/main/java/com/example/service/BrokenParser.java"
        summary = parse_java_file(file_path, code, root_dir=td)

        assert summary.status == "syntax_error"
        assert summary.syntax_error is not None
        assert summary.syntax_error.file_path == file_path
        assert summary.syntax_error.line_number == 5
        assert summary.syntax_error.offset is not None
        assert "illegal start of expression" in summary.syntax_error.error_message


def test_import_extraction_all_types():
    """Verify extraction of standard, wildcard, and static imports."""
    code = """package com.example.app;

import java.util.List;
import java.io.*;
import static org.junit.Assert.assertEquals;
import static java.lang.Math.PI;

public class App {}
"""
    with tempfile.TemporaryDirectory() as td:
        summary = parse_java_file("App.java", code, root_dir=td)
        assert summary.status == "analyzed"
        assert len(summary.imports) == 4

        # List
        imp_list = summary.imports[0]
        assert imp_list.target_module == "java.util.List"
        assert imp_list.is_stdlib is True
        assert imp_list.line_number == 3

        # Wildcard java.io.*
        imp_io = summary.imports[1]
        assert imp_io.target_module == "java.io.*"
        assert imp_io.is_stdlib is True

        # Static external import
        imp_junit = summary.imports[2]
        assert imp_junit.is_external is True
        assert imp_junit.imported_symbol == "assertEquals"

        # Static stdlib import
        imp_math = summary.imports[3]
        assert imp_math.is_stdlib is True
        assert imp_math.imported_symbol == "PI"


def test_stdlib_classification_zero_false_positives():
    """Verify that standard Java library packages are recognized without false positives."""
    assert is_java_stdlib_package("java.util.Map") is True
    assert is_java_stdlib_package("java.nio.file.Path") is True
    assert is_java_stdlib_package("javax.net.ssl.SSLSocket") is True
    assert is_java_stdlib_package("org.w3c.dom.Document") is True
    assert is_java_stdlib_package("org.xml.sax.SAXException") is True
    assert is_java_stdlib_package("com.sun.net.httpserver.HttpServer") is True

    # Non-stdlib packages must return False
    assert is_java_stdlib_package("org.apache.commons.lang3.StringUtils") is False
    assert is_java_stdlib_package("org.slf4j.Logger") is False
    assert is_java_stdlib_package("com.google.common.collect.Lists") is False
    assert is_java_stdlib_package("org.springframework.boot.SpringApplication") is False
    assert is_java_stdlib_package("com.example.service.UserService") is False


def test_module_resolution_internal_types():
    """Verify that project-local type imports resolve to their declaring files."""
    files = [
        {
            "path": "src/main/java/com/example/model/User.java",
            "content": "package com.example.model;\n\npublic class User {}\n",
        },
        {
            "path": "src/main/java/com/example/service/UserService.java",
            "content": "package com.example.service;\n\nimport com.example.model.User;\n\npublic class UserService {\n    private User u;\n}\n",
        },
    ]
    with tempfile.TemporaryDirectory() as td:
        summaries = parse_java_files_batch(files, set(), td)
        assert len(summaries) == 2

        service_summary = next(s for s in summaries if "UserService" in s.file_path)
        assert len(service_summary.imports) == 1
        imp = service_summary.imports[0]
        assert imp.is_internal is True
        assert imp.resolution_status == "resolved_internal"
        assert imp.target_module == "src/main/java/com/example/model/User.java"


def test_module_resolution_unresolved_internal():
    """Verify that an import referencing a missing class in a known project package is marked unresolved."""
    files = [
        {
            "path": "src/main/java/com/example/model/User.java",
            "content": "package com.example.model;\n\npublic class User {}\n",
        },
        {
            "path": "src/main/java/com/example/service/UserService.java",
            "content": "package com.example.service;\n\nimport com.example.model.MissingAccount;\n\npublic class UserService {}\n",
        },
    ]
    with tempfile.TemporaryDirectory() as td:
        summaries = parse_java_files_batch(files, set(), td)
        service_summary = next(s for s in summaries if "UserService" in s.file_path)
        assert len(service_summary.imports) == 1
        imp = service_summary.imports[0]
        assert imp.is_internal is False
        assert imp.resolution_status == "unresolved_reference"
        assert imp.target_module == "com.example.model.MissingAccount"


def test_static_import_internal_and_external():
    """Verify that static imports resolve internally when target class is present, or externally otherwise."""
    files = [
        {
            "path": "src/main/java/com/example/util/MathUtils.java",
            "content": "package com.example.util;\n\npublic class MathUtils {\n    public static int clamp(int v, int min, int max) { return v; }\n}\n",
        },
        {
            "path": "src/main/java/com/example/service/CalcService.java",
            "content": "package com.example.service;\n\nimport static com.example.util.MathUtils.clamp;\nimport static org.junit.Assert.assertEquals;\n\npublic class CalcService {}\n",
        },
    ]
    with tempfile.TemporaryDirectory() as td:
        summaries = parse_java_files_batch(files, set(), td)
        calc = next(s for s in summaries if "CalcService" in s.file_path)
        assert len(calc.imports) == 2

        clamp_imp = next(i for i in calc.imports if "clamp" in i.raw_statement)
        assert clamp_imp.is_internal is True
        assert clamp_imp.resolution_status == "resolved_internal"
        assert clamp_imp.target_module == "src/main/java/com/example/util/MathUtils.java"
        assert clamp_imp.imported_symbol == "clamp"

        assert_imp = next(i for i in calc.imports if "assertEquals" in i.raw_statement)
        assert assert_imp.is_external is True
        assert assert_imp.resolution_status == "external_package"
        assert assert_imp.imported_symbol == "assertEquals"


def test_maven_pom_parsing_and_property_resolution():
    """Verify that pom.xml extracts coordinates, dependencies, and resolves property placeholders."""
    pom_xml = """<project xmlns="http://maven.apache.org/POM/4.0.0">
    <groupId>com.example</groupId>
    <artifactId>order-service</artifactId>
    <version>1.0.0</version>
    <properties>
        <commons.version>3.12.0</commons.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.apache.commons</groupId>
            <artifactId>commons-lang3</artifactId>
            <version>${commons.version}</version>
            <scope>compile</scope>
        </dependency>
        <dependency>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-api</artifactId>
            <version>1.7.36</version>
            <scope>compile</scope>
        </dependency>
    </dependencies>
</project>"""

    with tempfile.TemporaryDirectory() as td:
        pom_path = os.path.join(td, "pom.xml")
        with open(pom_path, "w", encoding="utf-8") as f:
            f.write(pom_xml)

        summary = parse_maven_pom(pom_path)
        assert summary.is_malformed is False
        assert summary.group_id == "com.example"
        assert summary.artifact_id == "order-service"
        assert len(summary.dependencies) == 2

        commons_dep = next(d for d in summary.dependencies if d.artifact_id == "commons-lang3")
        assert commons_dep.version == "3.12.0"
        assert commons_dep.version_status == "resolved"


def test_maven_pom_unresolved_property_and_malformed():
    """Verify that unresolved Maven properties preserve uncertainty and malformed XML fails safely."""
    pom_unresolved = """<project>
    <groupId>com.example</groupId>
    <artifactId>app</artifactId>
    <dependencies>
        <dependency>
            <groupId>org.example</groupId>
            <artifactId>lib</artifactId>
            <version>${missing.property}</version>
        </dependency>
    </dependencies>
</project>"""

    with tempfile.TemporaryDirectory() as td:
        pom_path = os.path.join(td, "pom.xml")
        with open(pom_path, "w", encoding="utf-8") as f:
            f.write(pom_unresolved)

        summary = parse_maven_pom(pom_path)
        assert summary.is_malformed is False
        assert len(summary.dependencies) == 1
        assert summary.dependencies[0].version_status == "unresolved_property"
        assert summary.dependencies[0].version == "${missing.property}"

        # Malformed XML
        with open(pom_path, "w", encoding="utf-8") as f:
            f.write("<project><groupId>broken")
        broken_summary = parse_maven_pom(pom_path)
        assert broken_summary.is_malformed is True
        assert "XML syntax error" in broken_summary.parse_error


def test_gradle_build_parsing():
    """Verify that Gradle build scripts extract dependencies and flag computed versions."""
    gradle_content = """plugins {
    id 'java'
}

dependencies {
    implementation 'org.slf4j:slf4j-api:1.7.36'
    testImplementation "org.junit.jupiter:junit-jupiter:${junitVersion}"
    compileOnly group: 'org.projectlombok', name: 'lombok', version: '1.18.24'
}
"""
    with tempfile.TemporaryDirectory() as td:
        build_path = os.path.join(td, "build.gradle")
        with open(build_path, "w", encoding="utf-8") as f:
            f.write(gradle_content)

        summary = parse_gradle_build(build_path)
        assert summary.is_malformed is False
        assert len(summary.dependencies) == 3

        slf4j_dep = next(d for d in summary.dependencies if d.artifact_id == "slf4j-api")
        assert slf4j_dep.version == "1.7.36"
        assert slf4j_dep.version_status == "resolved"

        junit_dep = next(d for d in summary.dependencies if d.artifact_id == "junit-jupiter")
        assert junit_dep.is_computed is True
        assert junit_dep.version_status == "computed_unresolved"


def test_manifest_audit_declared_vs_undeclared():
    """Verify manifest auditing correctly distinguishes declared packages from undeclared packages."""
    pom_content = """<project>
    <groupId>com.example</groupId>
    <artifactId>app</artifactId>
    <dependencies>
        <dependency>
            <groupId>org.apache.commons</groupId>
            <artifactId>commons-lang3</artifactId>
            <version>3.12.0</version>
        </dependency>
    </dependencies>
</project>"""
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "pom.xml"), "w", encoding="utf-8") as f:
            f.write(pom_content)

        declared = extract_declared_java_dependencies(td)
        assert "org.apache.commons" in declared
        assert "commons-lang3" in declared

        assert is_java_package_declared("org.apache.commons.lang3.StringUtils", declared) is True
        assert is_java_package_declared("pkg:org.apache.commons.lang3.StringUtils", declared) is True
        assert is_java_package_declared("org.slf4j.Logger", declared) is False
        assert is_java_package_declared("pkg:org.slf4j.Logger", declared) is False
