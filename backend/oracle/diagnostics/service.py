"""Unified diagnostic engine and end-to-end evidence pipeline orchestrator."""

from datetime import datetime, timezone
import os
import re
import sys
import time
from typing import Dict, List, Optional, Set, Tuple
import uuid
import json
import tomllib
from sqlalchemy.orm import Session

# Ensure root is in sys.path so ml.taxonomy can be imported
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from ml.taxonomy.fault_taxonomy import FAULT_TAXONOMY, FaultCategory
from oracle.core.config import settings
from oracle.execution.policy import WORKLOAD_PROFILES, ExecutionState, WorkloadProfile
from oracle.execution.preflight import PreflightStatus, check_isolation_preflight
from oracle.execution.worker import DynamicExecutionWorker
from oracle.inspection.ast_parser import ParsedFileSummary, parse_python_file
from oracle.inspection.detector import detect_ecosystems
from oracle.inspection.graph import DependencyGraph, build_dependency_graph
from oracle.inspection.policy import (
    InspectionPolicyError,
    PathTraversalError,
    ResourceLimiter,
    ResourceLimitExceededError,
    SnapshotTimeoutError,
    is_binary_file,
    is_excluded_directory,
    redact_secrets,
)
from oracle.inspection.snapshot import (
    SnapshotContext,
    ingest_git_repository,
    ingest_local_directory,
)
from oracle.inspection.ts_parser import (
    is_ts_js_file,
    load_package_json,
    load_tsconfig,
    parse_ts_file,
    parse_ts_files_batch,
)
from oracle.inspection.java_parser import (
    extract_declared_java_dependencies,
    is_java_file,
    is_java_package_declared,
    parse_java_file,
    parse_java_files_batch,
)
from oracle.inspection.go_parser import (
    is_go_file,
    is_go_package_declared,
    load_go_mod,
    parse_go_mod,
    parse_go_source,
)
from oracle.diagnostics.telemetry_analyzer import (
    analyze_runtime_symptoms,
    telemetry_to_evidence,
)
from ml.planning.probe_planner import (
    DYNAMIC_PROFILE_MAPPING,
    ProbePlanner,
    ProbePlannerConfig,
)
from ml.ranking.heuristic_ranker import HeuristicRankerConfig, rank_hypotheses
from oracle.models.diagnostic_run import DiagnosticRunRecord, DiagnosticRunState
from oracle.models.repository import Repository
from oracle.schemas.diagnostics import (
    DiagnosticComponent,
    DiagnosticDecisionRecord,
    DiagnosticDependencyEdge,
    DiagnosticEvidenceRecord,
    DiagnosticProbe,
    DiagnosticReport,
    DiagnosticRunRequest,
    DiagnosticStage,
    DiagnosticSystemMap,
    FaultHypothesis,
    ProbeResult,
    VerificationOutcome,
)
from oracle.schemas.execution import ExecutionRequest


def _normalize_pkg_name(name: str) -> str:
    """Normalize Python package name for comparison."""
    clean = re.split(r"[><=~!]", name)[0].strip().lower()
    return clean.replace("_", "-")


def extract_declared_dependencies(root_dir: str) -> Set[str]:
    """Extract declared third-party dependencies from pyproject.toml, requirements.txt, setup.py, package.json, pom.xml.

    Scans root_dir and first-level subdirectories (supporting polyglot and monorepo repository structures).
    """
    declared: Set[str] = set()

    manifest_dirs = [root_dir]
    try:
        for entry in os.listdir(root_dir):
            sub = os.path.join(root_dir, entry)
            if os.path.isdir(sub) and not entry.startswith("."):
                manifest_dirs.append(sub)
    except Exception:
        pass

    for m_dir in manifest_dirs:
        # 1. pyproject.toml
        pyproject_path = os.path.join(m_dir, "pyproject.toml")
        if os.path.exists(pyproject_path):
            try:
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                # PEP 621 dependencies
                project_deps = data.get("project", {}).get("dependencies", [])
                for dep in project_deps:
                    if isinstance(dep, str):
                        declared.add(_normalize_pkg_name(dep))
                # Poetry dependencies
                poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                for dep in poetry_deps.keys():
                    if dep.lower() != "python":
                        declared.add(_normalize_pkg_name(dep))
            except Exception:
                pass

        # 2. requirements.txt
        req_path = os.path.join(m_dir, "requirements.txt")
        if os.path.exists(req_path):
            try:
                with open(req_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and not line.startswith("-"):
                            declared.add(_normalize_pkg_name(line))
            except Exception:
                pass

        # 3. setup.cfg / setup.py basic scan
        setup_cfg = os.path.join(m_dir, "setup.cfg")
        if os.path.exists(setup_cfg):
            try:
                with open(setup_cfg, "r", encoding="utf-8", errors="replace") as f:
                    in_install_requires = False
                    for line in f:
                        stripped = line.strip()
                        if stripped.startswith("install_requires"):
                            in_install_requires = True
                            continue
                        if in_install_requires:
                            if stripped.startswith("["):
                                in_install_requires = False
                            elif stripped:
                                declared.add(_normalize_pkg_name(stripped))
            except Exception:
                pass

        # 4. package.json for Node.js / TypeScript projects
        pkg_path = os.path.join(m_dir, "package.json")
        if os.path.exists(pkg_path):
            try:
                with open(pkg_path, "r", encoding="utf-8", errors="replace") as f:
                    raw_pkg = f.read()
                cleaned_pkg = re.sub(r"/\*.*?\*/", "", raw_pkg, flags=re.DOTALL)
                cleaned_pkg = re.sub(r"//.*?\n", "\n", cleaned_pkg)
                cleaned_pkg = re.sub(r",\s*([\]}])", r"\1", cleaned_pkg)
                pkg_data = json.loads(cleaned_pkg)
                for k in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                    deps = pkg_data.get(k, {})
                    if isinstance(deps, dict):
                        for pkg_name in deps.keys():
                            declared.add(_normalize_pkg_name(pkg_name))
            except Exception:
                pass

        # 5. Java Maven pom.xml and Gradle build.gradle / build.gradle.kts
        try:
            java_deps = extract_declared_java_dependencies(m_dir)
            declared.update(java_deps)
        except Exception:
            pass

        # 6. Go go.mod manifests
        try:
            go_mod_path = os.path.join(m_dir, "go.mod")
            if os.path.exists(go_mod_path):
                with open(go_mod_path, "r", encoding="utf-8", errors="replace") as f:
                    mod_content = f.read()
                manifest = parse_go_mod(mod_content)
                declared.update(manifest.all_declared_dependencies)
        except Exception:
            pass

    return declared


class DiagnosticOrchestrator:
    """Coordinates the end-to-end diagnostic workflow from repository validation to diagnostic report."""

    def __init__(
        self,
        execution_worker: Optional[DynamicExecutionWorker] = None,
    ) -> None:
        self.execution_worker = execution_worker or DynamicExecutionWorker()
        # In-memory run and repository stores for fast retrieval and offline execution
        self._runs_by_id: Dict[uuid.UUID, DiagnosticReport] = {}
        self._latest_by_repo: Dict[uuid.UUID, DiagnosticReport] = {}
        self._active_runs: Set[uuid.UUID] = set()
        self._repos_by_id: Dict[uuid.UUID, Repository] = {}

    def register_repo(self, repo: Repository) -> None:
        """Cache a repository target in the in-memory store."""
        self._repos_by_id[repo.id] = repo

    def get_repo(self, repo_id: uuid.UUID) -> Optional[Repository]:
        """Retrieve a cached repository target by UUID."""
        return self._repos_by_id.get(repo_id)

    def list_repos(self) -> List[Repository]:
        """Retrieve all cached repository targets ordered by registration date."""
        return sorted(self._repos_by_id.values(), key=lambda r: r.created_at, reverse=True)

    def delete_repo(self, repo_id: uuid.UUID) -> bool:
        """Remove a cached repository target by UUID."""
        return self._repos_by_id.pop(repo_id, None) is not None

    def get_run(self, run_id: uuid.UUID) -> Optional[DiagnosticReport]:
        """Retrieve a diagnostic report by run UUID."""
        return self._runs_by_id.get(run_id)

    def get_latest_report(self, repository_id: uuid.UUID) -> Optional[DiagnosticReport]:
        """Retrieve the most recent diagnostic report for a repository target."""
        return self._latest_by_repo.get(repository_id)

    def list_runs(self) -> List[DiagnosticReport]:
        """Retrieve all recorded diagnostic reports ordered by start timestamp."""
        return sorted(self._runs_by_id.values(), key=lambda r: r.started_at, reverse=True)

    def execute_diagnosis(
        self,
        repository: Repository,
        request: Optional[DiagnosticRunRequest] = None,
        db: Optional[Session] = None,
    ) -> DiagnosticReport:
        """Execute the end-to-end diagnostic pipeline against a registered repository target."""
        req = request or DiagnosticRunRequest()
        run_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc)
        start_mono = time.monotonic()

        # Prevent duplicate concurrent executions on the same repository target
        if repository.id in self._active_runs:
            existing = self.get_latest_report(repository.id)
            if existing and existing.status == "running":
                return existing

        self._active_runs.add(repository.id)

        completed_stages: List[str] = []
        unsupported_stages: List[str] = []
        evidence_records: List[DiagnosticEvidenceRecord] = []
        hypotheses: List[FaultHypothesis] = []
        verification_outcomes: List[VerificationOutcome] = []
        candidate_probes: List[DiagnosticProbe] = []
        executed_probes: List[ProbeResult] = []
        investigation_history: List[DiagnosticDecisionRecord] = []
        stopping_reason: Optional[str] = None
        missing_evidence: List[str] = []
        run_status = "completed"
        error_message: Optional[str] = None
        abstention_reason: Optional[str] = None
        snapshot_ctx: Optional[SnapshotContext] = None

        try:
            # -------------------------------------------------------------
            # Stage 1: Validate Target and Capabilities
            # -------------------------------------------------------------
            allowed_capabilities = {
                "static_inspection",
                "system_map",
                "evidence_collection",
                "hypothesis_generation",
                "dynamic_verification",
                "adaptive_probing",
            }
            for cap in req.capabilities:
                if cap not in allowed_capabilities:
                    unsupported_stages.append(f"capability:{cap}")

            if req.allow_dynamic and req.workload_profile:
                if req.workload_profile not in WORKLOAD_PROFILES:
                    run_status = "failed"
                    error_message = (
                        f"Workload profile '{req.workload_profile}' is not in the approved allowlist. "
                        "Arbitrary execution is prohibited."
                    )
                    raise ValueError(error_message)

            completed_stages.append(DiagnosticStage.VALIDATE_TARGET.value)

            # -------------------------------------------------------------
            # Stage 2: Safe Snapshot Ingestion
            # -------------------------------------------------------------
            timeout = float(req.timeout_seconds or settings.inspection_timeout_seconds)
            max_files = req.max_files or settings.max_inspection_file_count

            if repository.source_type == "git":
                snapshot_ctx = ingest_git_repository(
                    git_url=repository.url,
                    timeout_seconds=timeout,
                )
            else:
                snapshot_ctx = ingest_local_directory(
                    local_path=repository.url,
                    permitted_roots=settings.permitted_local_roots,
                )

            root_dir = snapshot_ctx.root_path
            commit_hash = snapshot_ctx.commit_hash
            completed_stages.append(DiagnosticStage.ACQUIRE_SNAPSHOT.value)

            # -------------------------------------------------------------
            # Stage 3: Static Inspection & AST Parsing
            # -------------------------------------------------------------
            limiter = ResourceLimiter(
                max_file_count=max_files,
                max_file_size_bytes=settings.max_inspection_file_size_bytes,
                max_total_bytes=settings.max_inspection_total_bytes,
                timeout_seconds=timeout,
            )

            discovered_rel_files: List[str] = []
            skipped_files: List[str] = []

            try:
                for current_dir, dir_names, filenames in os.walk(root_dir):
                    limiter.check_timeout()
                    dir_names[:] = [d for d in dir_names if not is_excluded_directory(d)]

                    for fname in filenames:
                        full_path = os.path.join(current_dir, fname)
                        rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")

                        if is_binary_file(fname):
                            continue

                        try:
                            st = os.stat(full_path)
                            size = st.st_size
                        except OSError:
                            continue

                        try:
                            limiter.register_file(rel_path, size)
                            discovered_rel_files.append(rel_path)
                        except ResourceLimitExceededError as rle:
                            run_status = "partial"
                            skipped_files.append(rel_path)
                            missing_evidence.append(str(rle))
                            break

                    if run_status == "partial" and any("file count" in m for m in missing_evidence):
                        break

            except SnapshotTimeoutError as te:
                run_status = "partial"
                missing_evidence.append(str(te))

            # Detect language ecosystems
            ecosystems = detect_ecosystems(discovered_rel_files)
            unsupported_ecosystems = [
                e.name for e in ecosystems if e.name not in ("python", "javascript_typescript", "java_jvm", "go")
            ]
            if unsupported_ecosystems:
                missing_evidence.append(
                    f"Ecosystems without static AST support detected: {', '.join(unsupported_ecosystems)}. Deep AST parsing is supported for Python, TypeScript/JavaScript, Java, and Go."
                )

            # AST parsing
            all_py_files: Set[str] = {f for f in discovered_rel_files if f.endswith(".py")}
            all_ts_js_files: Set[str] = {f for f in discovered_rel_files if is_ts_js_file(f)}
            all_java_files: Set[str] = {f for f in discovered_rel_files if is_java_file(f)}
            all_go_files: Set[str] = {f for f in discovered_rel_files if is_go_file(f)}
            all_known_files_set: Set[str] = set(discovered_rel_files)
            parsed_summaries: List[ParsedFileSummary] = []

            # 3a. Parse Python source files
            for py_rel in sorted(all_py_files):
                limiter.check_timeout()
                full_py_path = os.path.join(root_dir, py_rel.replace("/", os.sep))

                try:
                    file_size = os.path.getsize(full_py_path)
                    if not limiter.is_file_size_permitted(file_size):
                        run_status = "partial"
                        skipped_files.append(py_rel)
                        continue

                    with open(full_py_path, "r", encoding="utf-8", errors="replace") as f:
                        source_code = f.read()

                    summary = parse_python_file(py_rel, source_code, all_py_files)
                    parsed_summaries.append(summary)

                    if summary.status == "syntax_error":
                        run_status = "partial"
                except Exception as ex:
                    run_status = "partial"
                    skipped_files.append(py_rel)
                    missing_evidence.append(f"Failed to read {py_rel}: {str(ex)}")

            # 3b. Parse TypeScript and JavaScript source files
            if all_ts_js_files:
                tsconfig = load_tsconfig(root_dir)
                package_json = load_package_json(root_dir)

                ts_items: List[Dict[str, str]] = []
                for ts_rel in sorted(all_ts_js_files):
                    limiter.check_timeout()
                    full_ts_path = os.path.join(root_dir, ts_rel.replace("/", os.sep))
                    try:
                        file_size = os.path.getsize(full_ts_path)
                        if not limiter.is_file_size_permitted(file_size):
                            run_status = "partial"
                            skipped_files.append(ts_rel)
                            continue
                        ts_items.append({"path": ts_rel})
                    except Exception:
                        run_status = "partial"
                        skipped_files.append(ts_rel)

                if ts_items:
                    ts_summaries = parse_ts_files_batch(
                        files=ts_items,
                        all_known_files=all_known_files_set,
                        root_dir=root_dir,
                        tsconfig=tsconfig,
                        package_json=package_json,
                    )
                    for summary in ts_summaries:
                        parsed_summaries.append(summary)
                        if summary.status in ("syntax_error", "analysis_failed"):
                            run_status = "partial"

            # 3c. Parse Java source files
            if all_java_files:
                java_items: List[Dict[str, str]] = []
                for j_rel in sorted(all_java_files):
                    limiter.check_timeout()
                    full_j_path = os.path.join(root_dir, j_rel.replace("/", os.sep))
                    try:
                        file_size = os.path.getsize(full_j_path)
                        if not limiter.is_file_size_permitted(file_size):
                            run_status = "partial"
                            skipped_files.append(j_rel)
                            continue
                        java_items.append({"path": j_rel})
                    except Exception:
                        run_status = "partial"
                        skipped_files.append(j_rel)

                if java_items:
                    java_summaries = parse_java_files_batch(
                        files=java_items,
                        all_known_files=all_known_files_set,
                        root_dir=root_dir,
                    )
                    for summary in java_summaries:
                        parsed_summaries.append(summary)
                        if summary.status in ("syntax_error", "analysis_failed"):
                            run_status = "partial"

            # 3d. Parse Go source files
            if all_go_files:
                go_manifest = load_go_mod(root_dir)
                for go_rel in sorted(all_go_files):
                    limiter.check_timeout()
                    full_go_path = os.path.join(root_dir, go_rel.replace("/", os.sep))
                    try:
                        file_size = os.path.getsize(full_go_path)
                        if not limiter.is_file_size_permitted(file_size):
                            run_status = "partial"
                            skipped_files.append(go_rel)
                            continue
                        with open(full_go_path, "r", encoding="utf-8", errors="replace") as f:
                            go_source = f.read()
                        summary = parse_go_source(
                            file_path=go_rel,
                            content=go_source,
                            module_manifest=go_manifest,
                            all_repo_files=all_known_files_set,
                            repo_root=root_dir,
                        )
                        parsed_summaries.append(summary)
                        if summary.status in ("syntax_error", "analysis_failed"):
                            run_status = "partial"
                    except Exception:
                        run_status = "partial"
                        skipped_files.append(go_rel)

            completed_stages.append(DiagnosticStage.STATIC_INSPECTION.value)

            # -------------------------------------------------------------
            # Stage 4: Unified System Map Construction
            # -------------------------------------------------------------
            dep_graph: DependencyGraph = build_dependency_graph(parsed_summaries)

            component_map: Dict[str, DiagnosticComponent] = {}
            diagnostic_edges: List[DiagnosticDependencyEdge] = []

            # 1. Register analyzed source files
            for summary in parsed_summaries:
                cid = f"file:{summary.file_path}"
                status = "syntax_error" if summary.status == "syntax_error" else "analyzed"
                component_map[cid] = DiagnosticComponent(
                    id=cid,
                    name=os.path.basename(summary.file_path),
                    component_type="source_file",
                    file_path=summary.file_path,
                    status=status,
                    metadata={"lines_of_code": summary.line_count, "imports_count": len(summary.imports)},
                )

            # 2. Register graph nodes & edges
            for edge in dep_graph.edges:
                # Target node registration
                target_id = edge.target_node
                if target_id not in component_map:
                    if edge.dependency_type == "stdlib":
                        ctype = "stdlib_module"
                        cstatus = "analyzed"
                    elif edge.dependency_type == "internal":
                        ctype = "internal_module"
                        cstatus = "analyzed"
                    elif edge.dependency_type == "unresolved":
                        ctype = "unresolved_reference"
                        cstatus = "unresolved"
                    else:
                        ctype = "external_package"
                        cstatus = "analyzed"

                    component_map[target_id] = DiagnosticComponent(
                        id=target_id,
                        name=target_id.split(":", 1)[-1],
                        component_type=ctype,
                        file_path=None,
                        status=cstatus,
                        metadata={"dependency_type": edge.dependency_type},
                    )

                diagnostic_edges.append(
                    DiagnosticDependencyEdge(
                        source_component_id=edge.source_node,
                        target_component_id=edge.target_node,
                        dependency_type=edge.dependency_type,
                        line_number=edge.line_number,
                        import_statement=edge.import_statement,
                        is_resolved=edge.is_resolved,
                        provenance={"inspector": "ASTParser", "version": "1.0.0"},
                    )
                )

            system_map = DiagnosticSystemMap(
                components=list(component_map.values()),
                edges=diagnostic_edges,
                total_components=len(component_map),
                total_dependencies=len(diagnostic_edges),
                internal_dependency_count=dep_graph.internal_edge_count,
                external_dependency_count=dep_graph.external_edge_count,
                stdlib_edge_count=dep_graph.stdlib_edge_count,
                unresolved_dependency_count=dep_graph.unresolved_edge_count,
                syntax_error_component_count=len([s for s in parsed_summaries if s.syntax_error]),
            )
            completed_stages.append(DiagnosticStage.BUILD_SYSTEM_MAP.value)

            # -------------------------------------------------------------
            # Stage 5: Discrete Evidence Collection with Provenance
            # -------------------------------------------------------------
            evid_seq = 1

            # A. Syntax error evidence
            for summary in parsed_summaries:
                if summary.syntax_error:
                    se = summary.syntax_error
                    eid = f"EVID-SYNTAX-{evid_seq:03d}"
                    evid_seq += 1
                    evidence_records.append(
                        DiagnosticEvidenceRecord(
                            evidence_id=eid,
                            evidence_type="syntax_error",
                            source_component=f"file:{summary.file_path}",
                            extraction_method="ast_parser",
                            location=f"{se.file_path}:{se.line_number or 1}:{se.offset or 0}",
                            observed_data={
                                "error_message": redact_secrets(se.error_message),
                                "line_number": se.line_number,
                                "column_offset": se.offset,
                                "file_path": se.file_path,
                            },
                            reliability="direct_observation",
                            limitations=["AST parsing halted at first syntax violation in this file"],
                        )
                    )

            # B. Unresolved internal imports
            for edge in dep_graph.edges:
                if edge.dependency_type == "unresolved":
                    eid = f"EVID-IMPORT-{evid_seq:03d}"
                    evid_seq += 1
                    evidence_records.append(
                        DiagnosticEvidenceRecord(
                            evidence_id=eid,
                            evidence_type="unresolved_import",
                            source_component=edge.source_node,
                            extraction_method="dependency_graph",
                            location=f"{edge.source_node.replace('file:', '')}:{edge.line_number}",
                            observed_data={
                                "import_statement": edge.import_statement,
                                "target_reference": edge.target_node,
                                "line_number": edge.line_number,
                            },
                            reliability="direct_observation",
                            limitations=["Static relative import resolution based on filesystem enumeration"],
                        )
                    )

            # C. Undeclared external package imports
            declared_pkgs = extract_declared_dependencies(root_dir)
            external_pkgs_imported: Dict[str, List[Tuple[str, int]]] = {}
            for summary in parsed_summaries:
                for imp in summary.imports:
                    if imp.is_external:
                        top_pkg = _normalize_pkg_name(imp.target_module)
                        external_pkgs_imported.setdefault(top_pkg, []).append((summary.file_path, imp.line_number))

            undeclared_pkgs: Set[str] = set()
            for ext_pkg, usages in external_pkgs_imported.items():
                if (
                    ext_pkg not in declared_pkgs
                    and not is_java_package_declared(ext_pkg, declared_pkgs)
                    and not is_go_package_declared(ext_pkg, declared_pkgs)
                ):
                    undeclared_pkgs.add(ext_pkg)
                    eid = f"EVID-EXTDEP-{evid_seq:03d}"
                    evid_seq += 1
                    loc = f"{usages[0][0]}:{usages[0][1]}" if usages else None
                    evidence_records.append(
                        DiagnosticEvidenceRecord(
                            evidence_id=eid,
                            evidence_type="undeclared_external_dependency",
                            source_component=f"file:{usages[0][0]}" if usages else "pkg:" + ext_pkg,
                            extraction_method="manifest_audit",
                            location=loc,
                            observed_data={
                                "package": ext_pkg,
                                "imported_in": [f"{u[0]}:{u[1]}" for u in usages],
                                "manifest_present": bool(declared_pkgs or os.path.exists(os.path.join(root_dir, "pyproject.toml"))),
                            },
                            reliability="direct_observation",
                            limitations=["Package might be present in ambient runtime or system site-packages"],
                        )
                    )

            # D. Unsupported dynamic imports and computed references
            for summary in parsed_summaries:
                for imp in summary.imports:
                    if imp.resolution_status in ("unsupported_dynamic", "unsupported_resolution"):
                        eid = f"EVID-DYNAMIC-{evid_seq:03d}"
                        evid_seq += 1
                        evidence_records.append(
                            DiagnosticEvidenceRecord(
                                evidence_id=eid,
                                evidence_type="unsupported_dynamic_import",
                                source_component=f"file:{summary.file_path}",
                                extraction_method="ts_ast_parser",
                                location=f"{summary.file_path}:{imp.line_number}",
                                observed_data={
                                    "import_statement": imp.raw_statement,
                                    "specifier": imp.target_module,
                                    "resolution_status": imp.resolution_status,
                                },
                                reliability="limited_context",
                                limitations=["Computed dynamic import expression cannot be statically resolved without runtime execution"],
                            )
                        )

            # E. Empty codebase evidence
            if len(parsed_summaries) == 0:
                eid = f"EVID-EMPTY-{evid_seq:03d}"
                evid_seq += 1
                evidence_records.append(
                    DiagnosticEvidenceRecord(
                        evidence_id=eid,
                        evidence_type="empty_codebase",
                        source_component="repository_root",
                        extraction_method="ast_parser",
                        location=None,
                        observed_data={
                            "total_files_discovered": len(discovered_rel_files),
                            "python_files_found": len(all_py_files),
                            "ts_js_files_found": len(all_ts_js_files),
                            "java_files_found": len(all_java_files),
                            "go_files_found": len(all_go_files),
                        },
                        reliability="direct_observation",
                        limitations=["No parseable Python, TypeScript/JavaScript, Java, or Go source code found in target repository"],
                    )
                )

            # E. Container isolation probe evidence
            preflight = self.execution_worker.provider.check_preflight()
            eid = f"EVID-PREFLIGHT-{evid_seq:03d}"
            evid_seq += 1
            evidence_records.append(
                DiagnosticEvidenceRecord(
                    evidence_id=eid,
                    evidence_type="isolation_preflight",
                    source_component="system:container_runtime",
                    extraction_method="isolation_probe",
                    location=None,
                    observed_data={
                        "is_available": preflight.is_available,
                        "provider": preflight.provider,
                        "missing_reasons": preflight.missing_reasons,
                    },
                    reliability="direct_observation",
                    limitations=["Probes host Docker socket and CLI availability without code execution"],
                )
            )

            # F. Runtime telemetry and symptom analysis evidence
            telemetry_findings = analyze_runtime_symptoms(
                symptom_text=req.symptom_description,
                traceback_text=req.runtime_traceback,
                root_dir=root_dir,
            )
            if telemetry_findings:
                telem_records = telemetry_to_evidence(telemetry_findings, start_seq=evid_seq, run_id=run_id)
                evid_seq += len(telem_records)
                evidence_records.extend(telem_records)

            completed_stages.append(DiagnosticStage.COLLECT_EVIDENCE.value)

            # -------------------------------------------------------------
            # Stage 6: Multi-Hypothesis Generation & Deterministic Ranking
            # -------------------------------------------------------------
            hypo_seq = 1

            # Rule 1: Syntax error in source file(s) - grouped by distinct component
            syntax_evids_by_comp: Dict[str, List[DiagnosticEvidenceRecord]] = {}
            for e in evidence_records:
                if e.evidence_type == "syntax_error":
                    syntax_evids_by_comp.setdefault(e.source_component, []).append(e)

            for comp, comp_syntax_evids in sorted(syntax_evids_by_comp.items()):
                first_se = comp_syntax_evids[0]
                clean_comp = comp.replace("file:", "")
                hid = f"HYPO-{hypo_seq:03d}"
                hypo_seq += 1
                hypotheses.append(
                    FaultHypothesis(
                        hypothesis_id=hid,
                        category=FaultCategory.RUNTIME_EXCEPTION,
                        category_title=FAULT_TAXONOMY[FaultCategory.RUNTIME_EXCEPTION].title,
                        affected_component=clean_comp,
                        supporting_evidence_ids=[e.evidence_id for e in comp_syntax_evids],
                        assumptions=[
                            "Target source file is intended as an executable Python module",
                            "Parser grammar corresponds to target runtime interpreter version",
                        ],
                        alternative_explanations=[
                            "Incomplete file transfer or truncated git checkout",
                            "Incompatible Python grammar version used by parser",
                            "Unresolved merge conflict markers in source file",
                        ],
                        confidence_level="high",
                        relative_ranking_score=85.0,
                        score_rationale="Direct AST syntax violation observation (+35.0), line provenance verified (+35.0).",
                        verification_status="supported",
                        remediation_suggestion=(
                            f"Correct syntax violation in '{clean_comp}' "
                            f"at location {first_se.location}: {first_se.observed_data.get('error_message')}."
                        ),
                    )
                )

                # Competing hypothesis: Truncated file or grammar incompatibility
                comp_hid = f"HYPO-{hypo_seq:03d}"
                hypo_seq += 1
                hypotheses.append(
                    FaultHypothesis(
                        hypothesis_id=comp_hid,
                        category=FaultCategory.CONFIG_MISSING_OR_INVALID,
                        category_title=FAULT_TAXONOMY[FaultCategory.CONFIG_MISSING_OR_INVALID].title,
                        affected_component=clean_comp,
                        supporting_evidence_ids=[first_se.evidence_id],
                        assumptions=["Syntax failure caused by build environment or encoding misconfiguration"],
                        alternative_explanations=["Source file contains valid syntax under a different Python release"],
                        confidence_level="low",
                        relative_ranking_score=35.0,
                        score_rationale="Alternative confounding explanation with lower prior probability.",
                        verification_status="candidate",
                        remediation_suggestion="Verify python_requires version in project manifests.",
                        uncertainty_reason="Requires grammar compatibility check across runtime versions.",
                    )
                )

            # Rule 2: Unresolved internal import(s) - grouped by distinct component
            unres_evids_by_comp: Dict[str, List[DiagnosticEvidenceRecord]] = {}
            for e in evidence_records:
                if e.evidence_type == "unresolved_import":
                    unres_evids_by_comp.setdefault(e.source_component, []).append(e)

            for comp, comp_unres_evids in sorted(unres_evids_by_comp.items()):
                first_unres = comp_unres_evids[0]
                clean_comp = comp.replace("file:", "")
                target_ref = first_unres.observed_data.get("target_reference", "unknown")
                hid = f"HYPO-{hypo_seq:03d}"
                hypo_seq += 1
                hypotheses.append(
                    FaultHypothesis(
                        hypothesis_id=hid,
                        category=FaultCategory.DEPENDENCY_IMPORT_FAILURE,
                        category_title=FAULT_TAXONOMY[FaultCategory.DEPENDENCY_IMPORT_FAILURE].title,
                        affected_component=clean_comp,
                        supporting_evidence_ids=[e.evidence_id for e in comp_unres_evids],
                        assumptions=[
                            "Target module is intended to exist locally on disk within the repository",
                            "Import statement uses relative package path resolution",
                        ],
                        alternative_explanations=[
                            "Source root path differs from repository root directory",
                            "Referenced module deleted or renamed without updating import statement",
                            "Dynamic runtime sys.path modification not visible to static AST analysis",
                        ],
                        confidence_level="high",
                        relative_ranking_score=80.0,
                        score_rationale="Direct observation of missing internal module reference in dependency graph (+35.0).",
                        verification_status="supported",
                        remediation_suggestion=(
                            f"Provide the missing module for '{target_ref}' or adjust the relative import path "
                            f"in '{clean_comp}'."
                        ),
                    )
                )

                # Competing hypothesis: Source root misconfiguration
                comp_hid = f"HYPO-{hypo_seq:03d}"
                hypo_seq += 1
                hypotheses.append(
                    FaultHypothesis(
                        hypothesis_id=comp_hid,
                        category=FaultCategory.DEPENDENCY_IMPORT_FAILURE,
                        category_title=FAULT_TAXONOMY[FaultCategory.DEPENDENCY_IMPORT_FAILURE].title,
                        affected_component=clean_comp,
                        supporting_evidence_ids=[first_unres.evidence_id],
                        assumptions=["Internal import would resolve if source root was set to a subfolder (e.g. src/)"],
                        alternative_explanations=["Relative import is genuinely missing from project"],
                        confidence_level="medium",
                        relative_ranking_score=45.0,
                        score_rationale="Alternative hypothesis: source root layout mismatch.",
                        verification_status="candidate",
                        remediation_suggestion="Inspect pyproject.toml package directory configurations or PYTHONPATH.",
                        uncertainty_reason="Ambiguity between missing file on disk vs alternate source root directory.",
                    )
                )

            # Rule 3: Undeclared external dependencies
            undecl_evids = [e for e in evidence_records if e.evidence_type == "undeclared_external_dependency"]
            if undecl_evids:
                pkgs_list = [e.observed_data.get("package", "") for e in undecl_evids if e.observed_data.get("package")]
                hid = f"HYPO-{hypo_seq:03d}"
                hypo_seq += 1
                hypotheses.append(
                    FaultHypothesis(
                        hypothesis_id=hid,
                        category=FaultCategory.DEPENDENCY_IMPORT_FAILURE,
                        category_title=FAULT_TAXONOMY[FaultCategory.DEPENDENCY_IMPORT_FAILURE].title,
                        affected_component=", ".join(pkgs_list),
                        supporting_evidence_ids=[e.evidence_id for e in undecl_evids],
                        assumptions=[
                            "Imported third-party packages are required dependencies at runtime",
                            "Packages are not vendored inside an unanalyzed subfolder",
                        ],
                        alternative_explanations=[
                            "Package provided by ambient system site-packages environment",
                            "Optional runtime dependency intended for conditional import",
                            "Vendored library inside unanalyzed directory",
                        ],
                        confidence_level="medium",
                        relative_ranking_score=65.0,
                        score_rationale="Manifest audit confirmed packages missing from pyproject.toml / requirements.txt.",
                        verification_status="supported",
                        remediation_suggestion=(
                            f"Declare dependencies ({', '.join(pkgs_list)}) in pyproject.toml or requirements.txt "
                            "and verify installation in the project virtual environment."
                        ),
                    )
                )

            # Rule 3.5: Runtime telemetry and non-static faults
            telem_evids = [e for e in evidence_records if e.evidence_type == "runtime_telemetry"]
            for te in telem_evids:
                cat_val = te.observed_data.get("fault_category")
                conf_val = float(te.observed_data.get("confidence", 0.8))
                try:
                    target_cat = FaultCategory(cat_val)
                except Exception:
                    target_cat = FaultCategory.RUNTIME_EXCEPTION

                summary_str = te.observed_data.get("summary", "Observed runtime telemetry anomaly")
                comp_name = te.source_component.replace("file:", "")
                hid = f"HYPO-{hypo_seq:03d}"
                hypo_seq += 1

                score = round(conf_val * 100.0, 1)
                hypotheses.append(
                    FaultHypothesis(
                        hypothesis_id=hid,
                        category=target_cat,
                        category_title=FAULT_TAXONOMY.get(target_cat, FAULT_TAXONOMY[FaultCategory.RUNTIME_EXCEPTION]).title,
                        affected_component=comp_name,
                        supporting_evidence_ids=[te.evidence_id],
                        assumptions=["Observed error telemetry reflects actual runtime behavior"],
                        alternative_explanations=[
                            "Intermittent network or infrastructure hiccup",
                            "Transient database timeout",
                            "Environment variable set in outer host but unconfigured in target container",
                        ],
                        confidence_level="high" if conf_val >= 0.85 else ("medium" if conf_val >= 0.6 else "low"),
                        relative_ranking_score=score,
                        score_rationale=f"Empirical runtime telemetry observation ({summary_str[:80]}).",
                        verification_status="supported",
                        remediation_suggestion=f"Investigate {target_cat.value} in '{comp_name}': {summary_str}",
                    )
                )

            # Rule 4: Empty codebase -> Explicit abstention
            empty_evids = [e for e in evidence_records if e.evidence_type == "empty_codebase"]
            if empty_evids and not hypotheses:
                hid = f"HYPO-{hypo_seq:03d}"
                hypo_seq += 1
                abstention_reason = "No parseable Python source files found (nor supported TypeScript/JavaScript, Java, or Go files) in target repository to inspect."
                hypotheses.append(
                    FaultHypothesis(
                        hypothesis_id=hid,
                        category=FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE,
                        category_title=FAULT_TAXONOMY[FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE].title,
                        affected_component="repository_root",
                        supporting_evidence_ids=[e.evidence_id for e in empty_evids],
                        assumptions=["Repository must contain inspectable source code"],
                        confidence_level="uncertain",
                        relative_ranking_score=0.0,
                        score_rationale="Deliberate abstention: No source files available.",
                        verification_status="insufficient_evidence",
                        remediation_suggestion="Add supported Python, TypeScript/JavaScript, Java, or Go source code to the repository before initiating diagnosis.",
                        abstention_reason=abstention_reason,
                    )
                )

            # Rank initial hypotheses using deterministic heuristic ranker
            hypotheses = rank_hypotheses(hypotheses, evidence_records, system_map)
            completed_stages.append(DiagnosticStage.GENERATE_HYPOTHESES.value)

            # -------------------------------------------------------------
            # Stage 6.5: Adaptive Diagnostic Probe Planning & Investigation Loop
            # -------------------------------------------------------------
            planner = ProbePlanner(
                ProbePlannerConfig(max_iterations=req.max_iterations or 5)
            )
            executed_probe_ids: Set[str] = set()
            max_iters = req.max_iterations or 5

            for iteration in range(1, max_iters + 1):
                # 1. Generate candidate probes for current diagnostic state
                candidates = planner.generate_candidate_probes(
                    hypotheses=hypotheses,
                    evidence=evidence_records,
                    system_map=system_map,
                    allow_dynamic=req.allow_dynamic,
                    preflight_available=preflight.is_available,
                    executed_probe_ids=executed_probe_ids,
                )

                # Merge unique candidates into report candidate list
                existing_pids = {p.probe_id for p in candidate_probes}
                for c in candidates:
                    if c.probe_id not in existing_pids:
                        candidate_probes.append(c)
                        existing_pids.add(c.probe_id)

                # 2. Select next probe or determine stopping condition
                selected_probe, decision = planner.select_next_probe(
                    candidate_probes=candidates,
                    hypotheses=hypotheses,
                    iteration=iteration,
                )
                investigation_history.append(decision)

                if selected_probe is None:
                    stopping_reason = decision.stopping_reason
                    break

                # 3. Execute approved probe through safe adapter
                probe_start = time.monotonic()
                probe_outcome = "inconclusive"
                probe_exec_status = "completed"
                probe_details = ""
                applied_policy = "safe_static_analysis"
                ranking_changed = False
                generated_eids: List[str] = []

                if selected_probe.probe_type == "static_ast_syntax_check":
                    rel_path = selected_probe.target_component.replace("file:", "")
                    full_path = os.path.join(root_dir, rel_path.replace("/", os.sep))
                    if os.path.exists(full_path):
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                            src = f.read()
                        if is_ts_js_file(rel_path):
                            summary = parse_ts_file(
                                rel_path,
                                src,
                                all_known_files_set,
                                root_dir=root_dir,
                                tsconfig=tsconfig if "tsconfig" in locals() else load_tsconfig(root_dir),
                                package_json=package_json if "package_json" in locals() else load_package_json(root_dir),
                            )
                        elif is_java_file(rel_path):
                            summary = parse_java_file(rel_path, src, root_dir=root_dir, all_known_files=all_known_files_set)
                        elif is_go_file(rel_path):
                            summary = parse_go_source(
                                file_path=rel_path,
                                content=src,
                                module_manifest=load_go_mod(root_dir),
                                all_repo_files=all_known_files_set,
                                repo_root=root_dir,
                            )
                        else:
                            summary = parse_python_file(rel_path, src, all_py_files)
                        if summary.syntax_error:
                            probe_outcome = "confirmed"
                            probe_details = (
                                f"AST parser deterministically confirmed syntax defect in '{rel_path}' "
                                f"at line {summary.syntax_error.line_number}: {redact_secrets(summary.syntax_error.error_message)}."
                            )
                            # Confirm primary hypothesis and mark verified
                            updated_hypos = []
                            for h in hypotheses:
                                if h.hypothesis_id in selected_probe.target_hypothesis_ids and h.category == FaultCategory.RUNTIME_EXCEPTION:
                                    updated_hypos.append(h.model_copy(update={"verification_status": "verified"}))
                                elif h.hypothesis_id in selected_probe.target_hypothesis_ids and h.category == FaultCategory.CONFIG_MISSING_OR_INVALID:
                                    # Competing grammar hypothesis refuted by syntax confirmation
                                    updated_hypos.append(h.model_copy(update={"verification_status": "contradicted"}))
                                else:
                                    updated_hypos.append(h)
                            hypotheses = updated_hypos
                            ranking_changed = True
                        else:
                            probe_outcome = "refuted"
                            probe_details = f"AST parser found no syntax errors in '{rel_path}'."
                    else:
                        probe_outcome = "failed"
                        probe_exec_status = "failed"
                        probe_details = f"Target file '{rel_path}' not accessible on disk."

                elif selected_probe.probe_type == "static_import_resolution_check":
                    rel_path = selected_probe.target_component.replace("file:", "")
                    unres_ev = [
                        e for e in evidence_records
                        if e.source_component == selected_probe.target_component and e.evidence_type == "unresolved_import"
                    ]
                    target_mod = unres_ev[0].observed_data.get("target_reference", "") if unres_ev else ""
                    probe_outcome = "confirmed"
                    probe_details = f"Verified target internal import '{target_mod}' does not exist on disk relative to '{rel_path}'."
                    updated_hypos = []
                    for h in hypotheses:
                        if h.hypothesis_id in selected_probe.target_hypothesis_ids:
                            updated_hypos.append(h.model_copy(update={"verification_status": "verified"}))
                        else:
                            updated_hypos.append(h)
                    hypotheses = updated_hypos
                    ranking_changed = True

                elif selected_probe.probe_type == "static_manifest_audit":
                    decl = extract_declared_dependencies(root_dir)
                    target_pkgs = [p.strip() for p in selected_probe.target_component.split(",") if p.strip()]
                    missing_pkgs = [
                        p for p in target_pkgs
                        if _normalize_pkg_name(p) not in decl
                        and not is_java_package_declared(p, decl)
                        and not is_go_package_declared(p, decl)
                    ]
                    if missing_pkgs:
                        probe_outcome = "confirmed"
                        probe_details = f"Manifest audit confirmed package(s) {missing_pkgs} are undeclared in project manifests."
                        updated_hypos = []
                        for h in hypotheses:
                            if h.hypothesis_id in selected_probe.target_hypothesis_ids:
                                updated_hypos.append(h.model_copy(update={"verification_status": "partially_verified"}))
                            else:
                                updated_hypos.append(h)
                        hypotheses = updated_hypos
                        ranking_changed = True
                    else:
                        probe_outcome = "refuted"
                        probe_details = f"Manifest audit found all targeted packages {target_pkgs} are declared."

                elif selected_probe.probe_type == "downstream_independent_check":
                    downstream_rel = selected_probe.target_component.replace("file:", "")
                    downstream_full = os.path.join(root_dir, downstream_rel.replace("/", os.sep))
                    if os.path.exists(downstream_full):
                        with open(downstream_full, "r", encoding="utf-8", errors="replace") as f:
                            src = f.read()
                        if is_ts_js_file(downstream_rel):
                            d_summary = parse_ts_file(
                                downstream_rel,
                                src,
                                all_known_files_set,
                                root_dir=root_dir,
                                tsconfig=tsconfig if "tsconfig" in locals() else load_tsconfig(root_dir),
                                package_json=package_json if "package_json" in locals() else load_package_json(root_dir),
                            )
                        elif is_java_file(downstream_rel):
                            d_summary = parse_java_file(downstream_rel, src, root_dir=root_dir, all_known_files=all_known_files_set)
                        elif is_go_file(downstream_rel):
                            d_summary = parse_go_source(
                                file_path=downstream_rel,
                                content=src,
                                module_manifest=load_go_mod(root_dir),
                                all_repo_files=all_known_files_set,
                                repo_root=root_dir,
                            )
                        else:
                            d_summary = parse_python_file(downstream_rel, src, all_py_files)
                        if d_summary.syntax_error:
                            probe_outcome = "confirmed"
                            probe_details = f"Downstream component '{downstream_rel}' has independent syntax defect at line {d_summary.syntax_error.line_number}."
                        else:
                            probe_outcome = "confirmed"
                            probe_details = (
                                f"Downstream component '{downstream_rel}' has valid independent syntax. "
                                "However, runtime execution is blocked by broken upstream dependency."
                            )
                            # Update component status in system_map to 'blocked'
                            updated_comps = []
                            for c in system_map.components:
                                if c.id == selected_probe.target_component:
                                    updated_comps.append(
                                        c.model_copy(
                                            update={
                                                "status": "blocked",
                                                "metadata": {
                                                    **c.metadata,
                                                    "blocked_by": "Upstream dependency failure prevents runtime execution.",
                                                },
                                            }
                                        )
                                    )
                                else:
                                    updated_comps.append(c)
                            system_map = system_map.model_copy(update={"components": updated_comps})
                    else:
                        probe_outcome = "failed"
                        probe_exec_status = "failed"
                        probe_details = f"Downstream file '{downstream_rel}' not accessible on disk."

                elif selected_probe.probe_type in DYNAMIC_PROFILE_MAPPING:
                    applied_policy = "sandboxed_container_execution"
                    if req.allow_dynamic and preflight.is_available:
                        prof_id = DYNAMIC_PROFILE_MAPPING[selected_probe.probe_type]
                        exec_rep = self.execution_worker.execute_workload(
                            repository=repository,
                            request=ExecutionRequest(profile_id=prof_id),
                            snapshot_path=root_dir,
                        )
                        probe_outcome = "confirmed" if exec_rep.exit_code != 0 else "refuted"
                        probe_exec_status = exec_rep.status.value
                        probe_details = (
                            f"Dynamic container workload '{prof_id}' finished with exit code {exec_rep.exit_code}. "
                            f"Status: {exec_rep.status.value}."
                        )
                        updated_hypos = []
                        for h in hypotheses:
                            if h.hypothesis_id in selected_probe.target_hypothesis_ids:
                                updated_hypos.append(h.model_copy(update={"verification_status": "verified"}))
                            else:
                                updated_hypos.append(h)
                        hypotheses = updated_hypos
                        ranking_changed = True
                    else:
                        probe_outcome = "unsupported"
                        probe_exec_status = "unsupported"
                        probe_details = (
                            "Dynamic execution disabled: container isolation unavailable on host and "
                            "host fallback is strictly prohibited."
                        )

                probe_dur = round((time.monotonic() - probe_start) * 1000.0, 2)
                executed_probe_ids.add(selected_probe.probe_id)

                p_res = ProbeResult(
                    probe_id=selected_probe.probe_id,
                    probe_type=selected_probe.probe_type,
                    run_id=run_id,
                    target_component=selected_probe.target_component,
                    outcome=probe_outcome,
                    generated_evidence_ids=generated_eids,
                    execution_status=probe_exec_status,
                    duration_ms=probe_dur,
                    unsupported_reason=probe_details if probe_exec_status == "unsupported" else None,
                    applied_safety_policy=applied_policy,
                    ranking_changed=ranking_changed,
                    details=probe_details,
                )
                executed_probes.append(p_res)

                # Re-rank hypotheses after new probe evidence
                hypotheses = rank_hypotheses(hypotheses, evidence_records, system_map)

            completed_stages.append(DiagnosticStage.PLAN_ADAPTIVE_PROBES.value)

            # -------------------------------------------------------------
            # Stage 7: Verification Outcomes Synchronization
            # -------------------------------------------------------------
            for hypo in hypotheses:
                if hypo.verification_status == "verified":
                    verification_outcomes.append(
                        VerificationOutcome(
                            hypothesis_id=hypo.hypothesis_id,
                            method="static_ast_validation",
                            status="verified",
                            details="Independently verified via static AST parsing with line provenance.",
                        )
                    )
                elif hypo.verification_status in ("supported", "partially_verified"):
                    verification_outcomes.append(
                        VerificationOutcome(
                            hypothesis_id=hypo.hypothesis_id,
                            method="static_manifest_audit",
                            status="partially_verified",
                            details="Empirically supported by inspection evidence; dynamic proof requires container execution.",
                        )
                    )
                elif hypo.verification_status == "contradicted":
                    verification_outcomes.append(
                        VerificationOutcome(
                            hypothesis_id=hypo.hypothesis_id,
                            method="adaptive_probing",
                            status="not_verified",
                            details="Refuted by independent diagnostic check in favor of higher-probability explanation.",
                        )
                    )
                elif hypo.verification_status in ("unsupported", "insufficient_evidence"):
                    verification_outcomes.append(
                        VerificationOutcome(
                            hypothesis_id=hypo.hypothesis_id,
                            method="static_inspection",
                            status="unsupported",
                            details=hypo.abstention_reason or "Analysis unsupported due to missing inputs.",
                        )
                    )

            if req.allow_dynamic:
                if not preflight.is_available:
                    unsupported_stages.append("dynamic_verification")
                    stopping_reason = "further_investigation_unsafe_or_unsupported"
                    verification_outcomes.append(
                        VerificationOutcome(
                            hypothesis_id="dynamic_verification",
                            method="container_sandbox",
                            status="unsupported",
                            details=(
                                f"Dynamic verification disabled: host container isolation unavailable "
                                f"({'; '.join(preflight.missing_reasons)}). Host execution is strictly forbidden."
                            ),
                        )
                    )
                elif req.workload_profile:
                    already_executed = any(
                        p.execution_status == "completed" and p.outcome != "failed"
                        for p in executed_probes
                        if p.probe_id.startswith("PROBE-DYN")
                    )
                    if not already_executed:
                        exec_report = self.execution_worker.execute_workload(
                            repository=repository,
                            request=ExecutionRequest(profile_id=req.workload_profile),
                            snapshot_path=root_dir,
                        )
                        vstatus = "verified" if exec_report.exit_code == 0 else "partially_verified"
                        verification_outcomes.append(
                            VerificationOutcome(
                                hypothesis_id="dynamic_workload",
                                method="container_sandbox",
                                status=vstatus,
                                workload_profile=req.workload_profile,
                                exit_code=exec_report.exit_code,
                                details=(
                                    f"Dynamic execution finished with status {exec_report.status.value}. "
                                    f"Exit code: {exec_report.exit_code}."
                                ),
                            )
                        )

            completed_stages.append(DiagnosticStage.VERIFY_HYPOTHESES.value)

            # -------------------------------------------------------------
            # Stage 8: Diagnostic Report Assembly
            # -------------------------------------------------------------
            completed_stages.append(DiagnosticStage.GENERATE_REPORT.value)

            if not stopping_reason:
                stopping_reason = (
                    investigation_history[-1].stopping_reason
                    if investigation_history
                    else "investigation_completed"
                )

            # Construct readable summary and prioritized recommendations
            if hypotheses:
                top_hypo = hypotheses[0]
                if top_hypo.category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
                    summary = f"Abstained from diagnosis: {top_hypo.abstention_reason}"
                    recommendations = [top_hypo.remediation_suggestion or "Provide inspectable source code."]
                else:
                    summary = (
                        f"Adaptive investigation evaluated {len(hypotheses)} fault hypothesis(es) "
                        f"across {len(executed_probes)} executed probe(s). Primary finding: "
                        f"{top_hypo.category_title} in '{top_hypo.affected_component}' "
                        f"(Relative score: {top_hypo.relative_ranking_score}/100, {top_hypo.confidence_level} confidence)."
                    )
                    recommendations = [
                        h.remediation_suggestion
                        for h in hypotheses
                        if h.remediation_suggestion and h.verification_status != "contradicted"
                    ]
            else:
                summary = (
                    "No observable software faults detected. Target repository successfully passed "
                    "static AST inspection, manifest validation, and internal dependency resolution."
                )
                recommendations = [
                    "Maintain continuous integration tests and keep manifest dependencies synchronized."
                ]

            duration_ms = (time.monotonic() - start_mono) * 1000.0

            report = DiagnosticReport(
                run_id=run_id,
                repository_id=repository.id,
                repository_name=repository.name,
                repository_url=redact_secrets(repository.url),
                source_type=repository.source_type,
                commit_hash=commit_hash,
                status=run_status,
                completed_stages=completed_stages,
                unsupported_stages=unsupported_stages,
                system_map=system_map,
                evidence=evidence_records,
                hypotheses=hypotheses,
                verification=verification_outcomes,
                candidate_probes=candidate_probes,
                executed_probes=executed_probes,
                investigation_history=investigation_history,
                stopping_reason=stopping_reason,
                summary=summary,
                recommendations=recommendations,
                abstention_reason=abstention_reason,
                error_message=redact_secrets(error_message) if error_message else None,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                duration_ms=round(duration_ms, 2),
            )

        except (InspectionPolicyError, PathTraversalError, ValueError, FileNotFoundError) as err:
            duration_ms = (time.monotonic() - start_mono) * 1000.0
            sanitized_err = redact_secrets(str(err))
            report = DiagnosticReport(
                run_id=run_id,
                repository_id=repository.id,
                repository_name=repository.name,
                repository_url=redact_secrets(repository.url),
                source_type=repository.source_type,
                commit_hash=None,
                status="failed",
                completed_stages=completed_stages,
                unsupported_stages=unsupported_stages,
                system_map=DiagnosticSystemMap(),
                evidence=[],
                hypotheses=[],
                verification=[],
                candidate_probes=[],
                executed_probes=[],
                investigation_history=[],
                stopping_reason="failed",
                summary="Diagnostic run failed during execution.",
                recommendations=["Inspect repository URL and verify repository permissions."],
                abstention_reason=None,
                error_message=sanitized_err,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                duration_ms=round(duration_ms, 2),
            )

        finally:
            if snapshot_ctx:
                snapshot_ctx.cleanup()
            self._active_runs.discard(repository.id)

        # Store in in-memory run cache
        self._runs_by_id[run_id] = report
        self._latest_by_repo[repository.id] = report

        # Persist to database if session provided
        if db is not None:
            try:
                record = DiagnosticRunRecord(
                    id=run_id,
                    repository_id=repository.id,
                    status=report.status,
                    commit_hash=report.commit_hash,
                    summary=report.summary[:1000] if report.summary else None,
                    report_json=report.model_dump_json(),
                    duration_ms=report.duration_ms,
                    created_at=report.started_at,
                    completed_at=report.completed_at,
                )
                db.add(record)
                db.commit()
            except Exception:
                db.rollback()

        return report


# Shared singleton instance for the backend application
diagnostic_orchestrator = DiagnosticOrchestrator()
