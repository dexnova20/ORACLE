"""Safe static Java AST analysis, dependency extraction, and manifest auditing without code execution.

Uses OpenJDK's official Compiler Tree API (via an in-process Java worker)
to parse source files, capture precise syntax diagnostics, and extract import/type
declarations without executing target repository code.
"""

from dataclasses import dataclass, field
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET

from oracle.inspection.ast_parser import FileSyntaxError, ImportRecord, ParsedFileSummary

# Supported Java file extensions
JAVA_EXTENSIONS: Set[str] = {".java"}

# Common Java source roots for package-to-path convention mapping
JAVA_SOURCE_ROOTS: List[str] = [
    "src/main/java",
    "src/test/java",
    "src",
]

# Standard library package prefixes in Java / JDK
JAVA_STDLIB_PREFIXES: Tuple[str, ...] = (
    "java.",
    "javax.",
    "org.w3c.dom",
    "org.xml.sax",
    "org.ietf.jgss",
    "sun.",
    "com.sun.",
    "jdk.",
)


def is_java_file(path: str) -> bool:
    """Check if the given relative or absolute file path is a Java source file."""
    _, ext = os.path.splitext(path)
    return ext.lower() in JAVA_EXTENSIONS


def is_java_stdlib_package(pkg_name: str) -> bool:
    """Determine whether an import target belongs to the Java standard runtime library."""
    if not pkg_name:
        return False
    clean = pkg_name.strip()
    return any(clean.startswith(prefix) for prefix in JAVA_STDLIB_PREFIXES)


KNOWN_JAVA_DEP_PREFIXES: Dict[str, List[str]] = {
    "com.google.guava": ["com.google.common", "com.google.thirdparty"],
    "guava": ["com.google.common", "com.google.thirdparty"],
    "com.google.guava:guava": ["com.google.common", "com.google.thirdparty"],
    "commons-lang3": ["org.apache.commons.lang3"],
    "commons-io": ["org.apache.commons.io"],
    "commons-collections4": ["org.apache.commons.collections4"],
    "jackson-databind": ["com.fasterxml.jackson.databind", "com.fasterxml.jackson"],
    "junit": ["org.junit", "junit"],
    "slf4j-api": ["org.slf4j"],
}


def is_java_package_declared(pkg_str: str, declared_deps: Set[str]) -> bool:
    """Check if an imported Java external package or class is covered by declared dependencies."""
    clean = pkg_str.replace("pkg:", "").strip().lower()
    if clean in declared_deps:
        return True
    for dep in declared_deps:
        dep_clean = dep.lower()
        if clean == dep_clean:
            return True
        if clean.startswith(dep_clean + ".") or clean.startswith(dep_clean + ":") or dep_clean.startswith(clean + "."):
            return True
        # Check if dep is prefix of dotted path
        parts = clean.split(".")
        for i in range(1, len(parts) + 1):
            sub = ".".join(parts[:i])
            if sub == dep_clean:
                return True
        # Check known package prefix mappings
        if dep_clean in KNOWN_JAVA_DEP_PREFIXES:
            for prefix in KNOWN_JAVA_DEP_PREFIXES[dep_clean]:
                if clean == prefix or clean.startswith(prefix + "."):
                    return True
    return False


def get_java_worker_path() -> str:
    """Return the absolute path to the JavaAstWorker.java file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "JavaAstWorker.java")


def check_java_parser_available() -> Tuple[bool, Optional[str]]:
    """Verify that Java runtime is installed and the Java AST worker is compiled or executable.

    Returns (is_available, error_reason).
    """
    java_bin = shutil.which("java")
    if not java_bin:
        return (False, "Java runtime executable ('java') was not found on system PATH.")

    javac_bin = shutil.which("javac")
    if not javac_bin:
        return (False, "Java compiler executable ('javac') was not found on system PATH.")

    worker_java = get_java_worker_path()
    if not os.path.exists(worker_java):
        return (False, f"Java AST worker source not found at {worker_java}.")

    worker_dir = os.path.dirname(worker_java)
    backend_root = os.path.abspath(os.path.join(worker_dir, "..", ".."))
    class_file = os.path.join(worker_dir, "JavaAstWorker.class")

    # If .class does not exist or source is newer, compile it
    if not os.path.exists(class_file) or os.path.getmtime(worker_java) > os.path.getmtime(class_file):
        try:
            compile_proc = subprocess.run(
                [javac_bin, "-d", backend_root, worker_java],
                capture_output=True,
                text=True,
                timeout=15.0,
            )
            if compile_proc.returncode != 0:
                return (False, f"Failed to compile JavaAstWorker: {compile_proc.stderr.strip()}")
        except Exception as ex:
            return (False, f"Compilation of JavaAstWorker raised error: {str(ex)}")

    # Quick smoke test probe with empty payload
    try:
        proc = subprocess.run(
            [java_bin, "-cp", backend_root, "oracle.inspection.JavaAstWorker"],
            input=json.dumps({"files": []}),
            text=True,
            capture_output=True,
            timeout=5.0,
        )
        if proc.returncode != 0:
            return (False, f"Java worker test execution failed: {proc.stderr.strip()}")
        data = json.loads(proc.stdout)
        if data.get("error"):
            return (False, f"Java worker error: {data['error']}")
        return (True, None)
    except subprocess.TimeoutExpired:
        return (False, "Java worker preflight check timed out.")
    except Exception as ex:
        return (False, f"Failed to probe Java AST worker: {str(ex)}")


@dataclass
class JavaTypeDeclaration:
    """Represents a class, interface, enum, or record declared in a Java file."""
    name: str
    fqn: str
    kind: str  # class, interface, enum, record, annotation
    is_nested: bool = False
    modifiers: List[str] = field(default_factory=list)
    line: int = 1
    column: int = 1
    offset: int = 0


@dataclass
class MavenDependency:
    """Represents a declared dependency extracted from pom.xml."""
    group_id: str
    artifact_id: str
    version: Optional[str] = None
    scope: str = "compile"
    version_status: str = "resolved"  # resolved, unresolved_property, inherited_unresolved
    is_managed: bool = False


@dataclass
class MavenPomSummary:
    """Structured inspection summary of a Maven pom.xml manifest."""
    path: str
    group_id: Optional[str] = None
    artifact_id: Optional[str] = None
    version: Optional[str] = None
    version_status: str = "resolved"
    properties: Dict[str, str] = field(default_factory=dict)
    parent: Optional[Dict[str, str]] = None
    modules: List[str] = field(default_factory=list)
    dependencies: List[MavenDependency] = field(default_factory=list)
    dependency_management: List[MavenDependency] = field(default_factory=list)
    is_malformed: bool = False
    parse_error: Optional[str] = None


@dataclass
class GradleDependency:
    """Represents a declared dependency extracted from build.gradle or build.gradle.kts."""
    group_id: str
    artifact_id: str
    version: Optional[str] = None
    scope: str = "implementation"
    version_status: str = "resolved"  # resolved, computed_unresolved, unresolved_metadata
    is_computed: bool = False
    raw_declaration: str = ""


@dataclass
class GradleBuildSummary:
    """Structured inspection summary of a Gradle build script."""
    path: str
    dependencies: List[GradleDependency] = field(default_factory=list)
    modules: List[str] = field(default_factory=list)
    unresolved_metadata: List[str] = field(default_factory=list)
    is_malformed: bool = False
    parse_error: Optional[str] = None


def parse_maven_pom(
    pom_path: str,
    available_properties: Optional[Dict[str, str]] = None,
) -> MavenPomSummary:
    """Inspect a Maven pom.xml file as XML data without executing Maven.

    Extracts groupId, artifactId, version, properties, parent, modules, and dependencies.
    Resolves simple property references (${property.name}) when available.
    """
    summary = MavenPomSummary(path=pom_path)
    if not os.path.exists(pom_path):
        summary.is_malformed = True
        summary.parse_error = f"File not found: {pom_path}"
        return summary

    try:
        with open(pom_path, "rb") as f:
            raw_content = f.read()

        if not raw_content.strip():
            summary.is_malformed = True
            summary.parse_error = "Empty pom.xml manifest"
            return summary

        root = ET.fromstring(raw_content)
        # Strip XML namespaces for uniform querying
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        # Properties
        props: Dict[str, str] = dict(available_properties or {})
        prop_elem = root.find("properties")
        if prop_elem is not None:
            for child in prop_elem:
                if child.text:
                    props[child.tag] = child.text.strip()
                    summary.properties[child.tag] = child.text.strip()

        # Coordinates
        summary.group_id = root.findtext("groupId", "").strip() or None
        summary.artifact_id = root.findtext("artifactId", "").strip() or None
        summary.version = root.findtext("version", "").strip() or None

        # Parent
        parent_elem = root.find("parent")
        if parent_elem is not None:
            parent_gid = parent_elem.findtext("groupId", "").strip()
            parent_aid = parent_elem.findtext("artifactId", "").strip()
            parent_ver = parent_elem.findtext("version", "").strip()
            summary.parent = {
                "groupId": parent_gid,
                "artifactId": parent_aid,
                "version": parent_ver,
            }
            if not summary.group_id:
                summary.group_id = parent_gid
            if not summary.version:
                summary.version = parent_ver

        # Multi-module declarations
        modules_elem = root.find("modules")
        if modules_elem is not None:
            for mod in modules_elem.findall("module"):
                if mod.text and mod.text.strip():
                    summary.modules.append(mod.text.strip())

        def _resolve_version(ver_raw: str) -> Tuple[Optional[str], str]:
            if not ver_raw:
                return (None, "inherited_unresolved")
            if ver_raw.startswith("${") and ver_raw.endswith("}"):
                prop_key = ver_raw[2:-1].strip()
                if prop_key in props:
                    return (props[prop_key], "resolved")
                return (ver_raw, "unresolved_property")
            return (ver_raw, "resolved")

        # Direct dependencies
        deps_elem = root.find("dependencies")
        if deps_elem is not None:
            for dep in deps_elem.findall("dependency"):
                gid = dep.findtext("groupId", "").strip()
                aid = dep.findtext("artifactId", "").strip()
                raw_v = dep.findtext("version", "").strip()
                scope = dep.findtext("scope", "compile").strip()
                res_v, v_status = _resolve_version(raw_v)
                if gid and aid:
                    summary.dependencies.append(
                        MavenDependency(
                            group_id=gid,
                            artifact_id=aid,
                            version=res_v,
                            scope=scope,
                            version_status=v_status,
                            is_managed=False,
                        )
                    )

        # Dependency management
        dep_mgmt_elem = root.find("dependencyManagement")
        if dep_mgmt_elem is not None:
            mg_deps = dep_mgmt_elem.find("dependencies")
            if mg_deps is not None:
                for dep in mg_deps.findall("dependency"):
                    gid = dep.findtext("groupId", "").strip()
                    aid = dep.findtext("artifactId", "").strip()
                    raw_v = dep.findtext("version", "").strip()
                    scope = dep.findtext("scope", "compile").strip()
                    res_v, v_status = _resolve_version(raw_v)
                    if gid and aid:
                        summary.dependency_management.append(
                            MavenDependency(
                                group_id=gid,
                                artifact_id=aid,
                                version=res_v,
                                scope=scope,
                                version_status=v_status,
                                is_managed=True,
                            )
                        )

    except ET.ParseError as pe:
        summary.is_malformed = True
        summary.parse_error = f"XML syntax error: {str(pe)}"
    except Exception as ex:
        summary.is_malformed = True
        summary.parse_error = f"Manifest extraction error: {str(ex)}"

    return summary


def parse_gradle_build(build_path: str) -> GradleBuildSummary:
    """Inspect a Gradle build script (build.gradle or build.gradle.kts) statically.

    Extracts declared dependencies without executing Gradle or plugins.
    Preserves uncertainty when versions or coordinates are computed dynamically.
    """
    summary = GradleBuildSummary(path=build_path)
    if not os.path.exists(build_path):
        summary.is_malformed = True
        summary.parse_error = f"File not found: {build_path}"
        return summary

    try:
        with open(build_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if not content.strip():
            return summary

        # 1. Standard string dependencies: e.g. implementation 'group:artifact:version' or implementation("group:artifact:version")
        # Handles scopes: implementation, testImplementation, api, compileOnly, runtimeOnly, classpath
        scope_pattern = r"\b(implementation|testImplementation|api|compileOnly|runtimeOnly|classpath)\s*[\(\s]\s*['\"]([^'\"]+)['\"]\s*[\)]?"
        for match in re.finditer(scope_pattern, content):
            scope = match.group(1)
            coord_str = match.group(2).strip()

            # Skip project references like project(':core')
            if coord_str.startswith("project(") or coord_str.startswith(":"):
                summary.unresolved_metadata.append(f"Subproject dependency reference: {coord_str}")
                continue

            parts = coord_str.split(":")
            if len(parts) >= 2:
                gid = parts[0].strip()
                aid = parts[1].strip()
                raw_ver = parts[2].strip() if len(parts) >= 3 else None
                is_computed = False
                v_status = "resolved"

                if raw_ver and ("$" in raw_ver or "{" in raw_ver):
                    is_computed = True
                    v_status = "computed_unresolved"

                summary.dependencies.append(
                    GradleDependency(
                        group_id=gid,
                        artifact_id=aid,
                        version=raw_ver,
                        scope=scope,
                        version_status=v_status,
                        is_computed=is_computed,
                        raw_declaration=match.group(0).strip(),
                    )
                )

        # 2. Map-style declarations: e.g. implementation group: 'org.slf4j', name: 'slf4j-api', version: '1.7.36'
        map_pattern = r"\b(implementation|testImplementation|api|compileOnly|runtimeOnly)\s+group:\s*['\"]([^'\"]+)['\"],\s*name:\s*['\"]([^'\"]+)['\"](?:,\s*version:\s*['\"]([^'\"]+)['\"])?"
        for match in re.finditer(map_pattern, content):
            scope = match.group(1)
            gid = match.group(2).strip()
            aid = match.group(3).strip()
            ver = match.group(4).strip() if match.group(4) else None
            is_computed = bool(ver and ("$" in ver or "{" in ver))
            summary.dependencies.append(
                GradleDependency(
                    group_id=gid,
                    artifact_id=aid,
                    version=ver,
                    scope=scope,
                    version_status="computed_unresolved" if is_computed else "resolved",
                    is_computed=is_computed,
                    raw_declaration=match.group(0).strip(),
                )
            )

        # 3. Detect settings.gradle / settings.gradle.kts modules if nearby
        root_dir = os.path.dirname(build_path)
        for settings_name in ("settings.gradle", "settings.gradle.kts"):
            settings_path = os.path.join(root_dir, settings_name)
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, "r", encoding="utf-8", errors="replace") as sf:
                        s_content = sf.read()
                    mod_matches = re.findall(r"include\s*\(?\s*['\"](?::)?([^'\"]+)['\"]", s_content)
                    for m in mod_matches:
                        clean_m = m.replace(":", "").strip()
                        if clean_m and clean_m not in summary.modules:
                            summary.modules.append(clean_m)
                except Exception:
                    pass

    except Exception as ex:
        summary.is_malformed = True
        summary.parse_error = f"Gradle parsing error: {str(ex)}"

    return summary


def extract_declared_java_dependencies(root_dir: str) -> Set[str]:
    """Scan repository root and subdirectories for declared Maven and Gradle dependencies.

    Returns normalized set of declared dependency identifiers (e.g. 'org.slf4j', 'commons-lang3').
    """
    declared: Set[str] = set()

    # 1. Maven pom.xml
    pom_path = os.path.join(root_dir, "pom.xml")
    if os.path.exists(pom_path):
        pom_summary = parse_maven_pom(pom_path)
        for dep in pom_summary.dependencies:
            declared.add(dep.group_id.lower())
            declared.add(dep.artifact_id.lower())
            declared.add(f"{dep.group_id.lower()}:{dep.artifact_id.lower()}")
            # Add package prefixes (e.g. 'org.apache.commons.lang3' from 'org.apache.commons:commons-lang3')
            declared.add(f"{dep.group_id.lower()}.{dep.artifact_id.lower().replace('-', '.')}")

        # Check submodules
        for mod in pom_summary.modules:
            sub_pom = os.path.join(root_dir, mod, "pom.xml")
            if os.path.exists(sub_pom):
                sub_summary = parse_maven_pom(sub_pom, available_properties=pom_summary.properties)
                for dep in sub_summary.dependencies:
                    declared.add(dep.group_id.lower())
                    declared.add(dep.artifact_id.lower())
                    declared.add(f"{dep.group_id.lower()}:{dep.artifact_id.lower()}")

    # 2. Gradle build files
    for build_name in ("build.gradle", "build.gradle.kts"):
        build_path = os.path.join(root_dir, build_name)
        if os.path.exists(build_path):
            gradle_summary = parse_gradle_build(build_path)
            for dep in gradle_summary.dependencies:
                declared.add(dep.group_id.lower())
                declared.add(dep.artifact_id.lower())
                declared.add(f"{dep.group_id.lower()}:{dep.artifact_id.lower()}")
                declared.add(f"{dep.group_id.lower()}.{dep.artifact_id.lower().replace('-', '.')}")

    return declared


def parse_java_files_batch(
    files: List[Dict[str, str]],
    all_known_files: Set[str],
    root_dir: str,
) -> List[ParsedFileSummary]:
    """Execute high-throughput batch AST parsing and module resolution for Java source files.

    Uses the isolated JavaAstWorker to extract AST diagnostics without executing target code.
    Performs deterministic cross-module type resolution across the snapshot.
    """
    if not files:
        return []

    is_avail, err_msg = check_java_parser_available()
    if not is_avail:
        return [
            ParsedFileSummary(
                file_path=f["path"],
                status="skipped_by_policy",
                line_count=0,
                imports=[],
                syntax_error=FileSyntaxError(
                    file_path=f["path"],
                    error_message=f"Java parser unavailable: {err_msg}",
                    line_number=None,
                    offset=None,
                ),
            )
            for f in files
        ]

    # Prepare file contents payload
    payload_files: List[Dict[str, str]] = []
    for item in files:
        rel_path = item["path"]
        content = item.get("content")
        if content is None:
            full_path = os.path.join(root_dir, rel_path.replace("/", os.sep))
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as ex:
                content = ""
        payload_files.append({"path": rel_path, "content": content})

    worker_java = get_java_worker_path()
    worker_dir = os.path.dirname(worker_java)
    backend_root = os.path.abspath(os.path.join(worker_dir, "..", ".."))
    java_bin = shutil.which("java") or "java"

    # Invoke worker over stdin/stdout
    try:
        proc = subprocess.run(
            [java_bin, "-cp", backend_root, "oracle.inspection.JavaAstWorker"],
            input=json.dumps({"files": payload_files}),
            text=True,
            capture_output=True,
            timeout=30.0,
        )
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            return [
                ParsedFileSummary(
                    file_path=pf["path"],
                    status="analysis_failed",
                    line_count=0,
                    imports=[],
                    syntax_error=FileSyntaxError(
                        file_path=pf["path"],
                        error_message=f"Java worker crash: {err}",
                        line_number=None,
                        offset=None,
                    ),
                )
                for pf in payload_files
            ]

        worker_output = json.loads(proc.stdout)
    except Exception as ex:
        return [
            ParsedFileSummary(
                file_path=pf["path"],
                status="analysis_failed",
                line_count=0,
                imports=[],
                syntax_error=FileSyntaxError(
                    file_path=pf["path"],
                    error_message=f"Java parser invocation error: {str(ex)}",
                    line_number=None,
                    offset=None,
                ),
            )
            for pf in payload_files
        ]

    raw_files = worker_output.get("files", [])
    raw_by_path = {rf["path"]: rf for rf in raw_files}

    # 1. Build global symbol tables across all inspected Java files
    # types_by_fqn: FQN -> (file_path, type_decl)
    # types_by_package: package_name -> list of (file_path, type_decl)
    # packages_in_repo: set of all packages declared
    types_by_fqn: Dict[str, Tuple[str, JavaTypeDeclaration]] = {}
    types_by_package: Dict[str, List[Tuple[str, JavaTypeDeclaration]]] = {}
    packages_in_repo: Set[str] = set()

    for pf in payload_files:
        rel_path = pf["path"]
        raw = raw_by_path.get(rel_path, {})
        pkg_name = raw.get("package_name") or ""
        if pkg_name:
            packages_in_repo.add(pkg_name)

        for td in raw.get("declared_types", []):
            name = td["name"]
            fqn = f"{pkg_name}.{name}" if pkg_name else name
            type_decl = JavaTypeDeclaration(
                name=name,
                fqn=fqn,
                kind=td.get("kind", "class"),
                is_nested=td.get("is_nested", False),
                modifiers=td.get("modifiers", []),
                line=td.get("line", 1),
                column=td.get("column", 1),
                offset=td.get("offset", 0),
            )
            types_by_fqn[fqn] = (rel_path, type_decl)
            types_by_package.setdefault(pkg_name, []).append((rel_path, type_decl))

    # 2. Extract declared dependencies from manifests (pom.xml, build.gradle)
    declared_manifest_deps = extract_declared_java_dependencies(root_dir)

    # 3. Build repository namespace prefixes (e.g. "com.example" for packages like "com.example.service")
    repo_namespaces: Set[str] = set(packages_in_repo)
    for p in packages_in_repo:
        parts = p.split(".")
        if len(parts) >= 2:
            repo_namespaces.add(".".join(parts[:2]))
        if len(parts) >= 3:
            repo_namespaces.add(".".join(parts[:3]))

    # 4. Process each file and resolve imports
    summaries: List[ParsedFileSummary] = []
    for pf in payload_files:
        rel_path = pf["path"]
        raw = raw_by_path.get(rel_path, {})
        pkg_name = raw.get("package_name") or ""
        line_count = raw.get("line_count", 0)

        # Check syntax errors
        raw_syntax_errors = raw.get("syntax_errors", [])
        syntax_err_obj: Optional[FileSyntaxError] = None
        status = "analyzed"
        if raw_syntax_errors:
            status = "syntax_error"
            first_err = raw_syntax_errors[0]
            syntax_err_obj = FileSyntaxError(
                file_path=rel_path,
                error_message=first_err.get("message", "Syntax error"),
                line_number=first_err.get("line"),
                offset=first_err.get("column"),
            )

        resolved_imports: List[ImportRecord] = []
        for imp in raw.get("imports", []):
            imp_name = imp.get("name", "").strip()
            is_static = imp.get("is_static", False)
            is_wildcard = imp.get("is_wildcard", False)
            line_no = imp.get("line", 1)
            raw_stmt = f"{'import static' if is_static else 'import'} {imp_name};"

            is_stdlib = False
            is_internal = False
            is_external = False
            res_status = "analyzed"
            target_module = imp_name
            imported_symbol: Optional[str] = None

            # Case A: Static import (e.g. import static com.example.util.MathUtils.clamp; or import static java.lang.Math.PI;)
            if is_static:
                if imp_name.endswith(".*"):
                    class_fqn = imp_name[:-2]
                    member = "*"
                elif "." in imp_name:
                    class_fqn, member = imp_name.rsplit(".", 1)
                else:
                    class_fqn = imp_name
                    member = None

                imported_symbol = member
                target_module = class_fqn

                if is_java_stdlib_package(class_fqn):
                    is_stdlib = True
                    res_status = "resolved_stdlib"
                elif class_fqn in types_by_fqn:
                    is_internal = True
                    res_status = "resolved_internal"
                    target_module = types_by_fqn[class_fqn][0]  # resolved file path
                else:
                    matches_repo_prefix = any(
                        class_fqn == p or class_fqn.startswith(p + ".")
                        for p in repo_namespaces
                    )
                    if matches_repo_prefix:
                        res_status = "unresolved_reference"
                    else:
                        is_external = True
                        res_status = "external_package"
                        target_module = f"pkg:{class_fqn}"

            # Case B: Wildcard import (e.g. import com.example.model.*; or import java.util.*;)
            elif is_wildcard:
                pkg_part = imp_name[:-2] if imp_name.endswith(".*") else imp_name
                if is_java_stdlib_package(pkg_part):
                    is_stdlib = True
                    res_status = "resolved_stdlib"
                elif pkg_part in packages_in_repo:
                    is_internal = True
                    res_status = "resolved_internal_package"
                    # Target module is mapped to package
                    target_module = pkg_part
                else:
                    # Unrecognized wildcard package
                    matches_repo_prefix = any(
                        pkg_part == p or pkg_part.startswith(p + ".") or p.startswith(pkg_part + ".")
                        for p in repo_namespaces
                    )
                    if matches_repo_prefix:
                        res_status = "unresolved_reference"
                    else:
                        is_external = True
                        res_status = "external_package"
                        target_module = f"pkg:{pkg_part}"

            # Case C: Standard library
            elif is_java_stdlib_package(imp_name):
                is_stdlib = True
                res_status = "resolved_stdlib"

            # Case D: Specific single-type import (e.g. import com.example.model.User;)
            else:
                if "." in imp_name:
                    _, sym_name = imp_name.rsplit(".", 1)
                    imported_symbol = sym_name

                if imp_name in types_by_fqn:
                    is_internal = True
                    res_status = "resolved_internal"
                    target_module = types_by_fqn[imp_name][0]  # Target file path
                else:
                    # Check if the prefix matches any project package namespace
                    matches_repo_prefix = any(
                        imp_name == p or imp_name.startswith(p + ".")
                        for p in repo_namespaces
                    )
                    if matches_repo_prefix:
                        res_status = "unresolved_reference"
                    else:
                        is_external = True
                        res_status = "external_package"
                        target_module = f"pkg:{imp_name}"

            resolved_imports.append(
                ImportRecord(
                    source_file=rel_path,
                    target_module=target_module,
                    imported_symbol=imported_symbol,
                    alias=None,
                    line_number=line_no,
                    is_relative=False,
                    level=0,
                    raw_statement=raw_stmt,
                    is_stdlib=is_stdlib,
                    is_internal=is_internal,
                    is_external=is_external,
                    resolution_status=res_status,
                )
            )

        summaries.append(
            ParsedFileSummary(
                file_path=rel_path,
                status=status,
                line_count=line_count,
                imports=resolved_imports,
                syntax_error=syntax_err_obj,
            )
        )

    return summaries


def parse_java_file(
    file_path: str,
    source_code: str,
    root_dir: str,
    all_known_files: Optional[Set[str]] = None,
) -> ParsedFileSummary:
    """Parse a single Java source file and return its inspection summary."""
    known = all_known_files or {file_path}
    summaries = parse_java_files_batch(
        files=[{"path": file_path, "content": source_code}],
        all_known_files=known,
        root_dir=root_dir,
    )
    if summaries:
        return summaries[0]
    return ParsedFileSummary(
        file_path=file_path,
        status="analysis_failed",
        line_count=0,
        imports=[],
        syntax_error=FileSyntaxError(
            file_path=file_path,
            error_message="Failed to parse Java file",
            line_number=None,
            offset=None,
        ),
    )
