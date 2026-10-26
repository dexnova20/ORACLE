"""Telemetry, runtime traceback, and non-static fault analyzer.

Extracts structured diagnostic evidence from observed symptoms, execution logs,
runtime stack traces, and configuration files that static AST inspection alone cannot establish.
"""

from dataclasses import dataclass, field
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ml.taxonomy.fault_taxonomy import FAULT_TAXONOMY, FaultCategory
from oracle.inspection.policy import redact_secrets
from oracle.schemas.diagnostics import DiagnosticEvidenceRecord


@dataclass
class ParsedStackFrame:
    """A single frame extracted from a polyglot stack trace."""

    file_path: str
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    code_context: Optional[str] = None


@dataclass
class ParsedTraceback:
    """Structured representation of a polyglot runtime stack trace."""

    exception_class: str
    error_message: str
    frames: List[ParsedStackFrame] = field(default_factory=list)
    raw_text: str = ""
    chained_causes: List[str] = field(default_factory=list)

    @property
    def root_frame(self) -> Optional[ParsedStackFrame]:
        """The innermost (fault origin) stack frame."""
        return self.frames[-1] if self.frames else None


@dataclass
class TelemetryFinding:
    """Diagnostic signal derived from telemetry, traceback, or config inspection."""

    category: FaultCategory
    confidence: float
    component: str
    summary_message: str
    line_number: Optional[int] = None
    exception_class: Optional[str] = None
    observed_signals: Dict[str, Any] = field(default_factory=dict)
    reliability: str = "direct_observation"
    limitations: List[str] = field(default_factory=list)


def parse_runtime_traceback(traceback_text: str) -> Optional[ParsedTraceback]:
    """Parse Python, TypeScript/Node.js, Java, or Go tracebacks into structured frames and error details.

    Redacts credentials/passwords and captures chained causes across nested exception frames.
    """
    if not traceback_text or not traceback_text.strip():
        return None

    cleaned = redact_secrets(traceback_text.strip())
    frames: List[ParsedStackFrame] = []
    chained_causes: List[str] = []

    # 1. Python Traceback: File "...", line 123, in foo
    py_frame_pattern = re.compile(
        r'File\s+["\']([^"\']+)["\'],\s+line\s+(\d+)(?:,\s+in\s+([^\n\r]+))?'
    )
    for match in py_frame_pattern.finditer(cleaned):
        f_path = match.group(1).replace("\\", "/")
        l_num = int(match.group(2))
        fn_name = match.group(3).strip() if match.group(3) else None
        frames.append(ParsedStackFrame(file_path=f_path, line_number=l_num, function_name=fn_name))

    # Python Exception: ExceptionType: message (last non-empty line)
    if frames:
        if "The above exception was the direct cause" in cleaned or "During handling of the above exception" in cleaned:
            for cm in re.finditer(r"([a-zA-Z0-9_.]*(?:Error|Exception|Fault|Panic)):\s*([^\n\r]+)", cleaned):
                c_cls = cm.group(1).split(".")[-1]
                c_msg = redact_secrets(cm.group(2).strip())
                chained_causes.append(f"{c_cls}: {c_msg}")

        last_lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        last_line = last_lines[-1] if last_lines else ""
        if ":" in last_line:
            exc_class, exc_msg = last_line.split(":", 1)
            exc_class = exc_class.strip().split(".")[-1]
            exc_msg = redact_secrets(exc_msg.strip())
        else:
            exc_class = last_line or "RuntimeError"
            exc_msg = ""
        return ParsedTraceback(
            exception_class=exc_class,
            error_message=exc_msg,
            frames=frames,
            raw_text=cleaned,
            chained_causes=chained_causes,
        )

    # 2. Node.js / TypeScript Stack Trace: at func (path/file.ts:123:45) or at path/file.js:123:45
    ts_frame_pattern = re.compile(
        r"at\s+(?:([^\s(]+)\s+\()?([^\s():]+):(\d+)(?::(\d+))?\)?",
    )
    for match in ts_frame_pattern.finditer(cleaned):
        fn_name = match.group(1)
        f_path = match.group(2).replace("\\", "/")
        l_num = int(match.group(3))
        frames.append(ParsedStackFrame(file_path=f_path, line_number=l_num, function_name=fn_name))

    if frames:
        first_line = cleaned.splitlines()[0].strip()
        if ":" in first_line:
            exc_class, exc_msg = first_line.split(":", 1)
            exc_class = exc_class.strip()
            exc_msg = redact_secrets(exc_msg.strip())
        else:
            exc_class = first_line or "Error"
            exc_msg = ""
        return ParsedTraceback(
            exception_class=exc_class,
            error_message=exc_msg,
            frames=frames,
            raw_text=cleaned,
            chained_causes=chained_causes,
        )

    # 3. Java Stack Trace: at com.pkg.Class.method(File.java:123)
    java_frame_pattern = re.compile(
        r"at\s+([a-zA-Z0-9_$.]+)\(([^:)]+):(\d+)\)"
    )
    for match in java_frame_pattern.finditer(cleaned):
        full_method = match.group(1)
        f_path = match.group(2)
        l_num = int(match.group(3))
        frames.append(ParsedStackFrame(file_path=f_path, line_number=l_num, function_name=full_method))

    if frames:
        # Check for Caused by: in Java tracebacks
        java_caused_by = list(re.finditer(r"Caused by:\s*([a-zA-Z0-9_$.]+)(?::\s*([^\n\r]+))?", cleaned))
        if java_caused_by:
            for cb in java_caused_by:
                cb_cls = cb.group(1).split(".")[-1]
                cb_msg = redact_secrets(cb.group(2).strip()) if cb.group(2) else ""
                chained_causes.append(f"{cb_cls}: {cb_msg}".strip(": "))
            # Root cause is innermost Caused by:
            last_cb = java_caused_by[-1]
            exc_class = last_cb.group(1).split(".")[-1]
            exc_msg = redact_secrets(last_cb.group(2).strip()) if last_cb.group(2) else ""
        else:
            first_line = cleaned.splitlines()[0].strip()
            if ":" in first_line:
                exc_class, exc_msg = first_line.split(":", 1)
                exc_class = exc_class.strip().split(".")[-1]
                exc_msg = redact_secrets(exc_msg.strip())
            else:
                exc_class = first_line.split(".")[-1] or "Exception"
                exc_msg = ""

        return ParsedTraceback(
            exception_class=exc_class,
            error_message=exc_msg,
            frames=frames,
            raw_text=cleaned,
            chained_causes=chained_causes,
        )

    # 4. Go Panic: goroutine 1 [running]:\nmain.main()\n\t/path/main.go:12 +0x34
    go_frame_pattern = re.compile(
        r"\t([^\s:]+):(\d+)(?:\s+\+0x[0-9a-fA-F]+)?"
    )
    for match in go_frame_pattern.finditer(cleaned):
        f_path = match.group(1).replace("\\", "/")
        l_num = int(match.group(2))
        frames.append(ParsedStackFrame(file_path=f_path, line_number=l_num))

    if frames:
        first_line = cleaned.splitlines()[0].strip()
        exc_class = "Panic"
        exc_msg = first_line.replace("panic:", "").strip() if "panic:" in first_line else first_line
        exc_msg = redact_secrets(exc_msg)
        return ParsedTraceback(
            exception_class=exc_class,
            error_message=exc_msg,
            frames=frames,
            raw_text=cleaned,
            chained_causes=chained_causes,
        )

    # Fallback generic exception line extraction
    first_or_last = cleaned.splitlines()[-1].strip()
    return ParsedTraceback(
        exception_class="GenericError",
        error_message=redact_secrets(first_or_last),
        frames=[],
        raw_text=cleaned,
        chained_causes=[],
    )


# Taxonomy classification regex patterns
_DATABASE_PATTERNS = [
    r"psycopg(\.errors|\.OperationalError|\.ProgrammingError)?",
    r"OperationalError.*(?:connection|refused|timeout|could not connect)",
    r"(?:connection\s+refused|could\s+not\s+connect|connect.*refused).*(?:5432|3306|5433|27017|database|postgres|mysql|sqlite)",
    r"(?:5432|3306|5433|27017).*(?:refused|timeout|failed|connection)",
    r"relation\s+['\"][^'\"]+['\"]\s+does not exist",
    r"column\s+['\"][^'\"]+['\"]\s+does not exist",
    r"connection to server at.*failed",
    r"DeadlockDetected",
    r"QueuePool limit",
    r"Target database is not up to date",
    r"alembic.*revision mismatch",
    r"django\.db\.utils\.OperationalError",
    r"pg_hba\.conf rejection",
]

_API_NETWORK_PATTERNS = [
    r"ConnectTimeout",
    r"HTTP 502|HTTP 503|HTTP 504|Bad Gateway|Gateway Timeout|Service Unavailable",
    r"SSLError.*certificate verify failed",
    r"requests\.exceptions\.(ConnectionError|Timeout|ConnectTimeout)",
    r"httpx\.(ConnectTimeout|ConnectError)",
    r"socket\.gaierror.*getaddrinfo failed",
    r"ECONNREFUSED|ETIMEDOUT|ENOTFOUND",
    r"HTTP 429|Too Many Requests",
]

_IO_CONTRACT_PATTERNS = [
    r"pydantic(\.error_wrappers)?\.ValidationError",
    r"jsonschema\.exceptions\.ValidationError",
    r"HTTP 422|Unprocessable Entity",
    r"missing required field",
    r"Field required.*\[type=missing",
    r"Input should be a valid",
    r"response payload schema validation failed",
]

_DATA_TRANSFORM_PATTERNS = [
    r"json\.decoder\.JSONDecodeError",
    r"UnicodeDecodeError.*codec can't decode byte",
    r"UnicodeEncodeError.*codec can't encode",
    r"ValueError:\s*invalid literal for int\(\)",
    r"ZeroDivisionError",
    r"datetime timezone mismatch",
    r"NaN or Inf in numerical transformation",
    r"TypeError:\s*unsupported operand type",
]

_CONFIG_PATTERNS = [
    r"KeyError:\s*['\"][A-Z0-9_]+['\"]",
    r"Missing mandatory environment variable",
    r"ConfigurationError",
    r"SettingsError",
    r"yaml\.scanner\.ScannerError|yaml\.parser\.ParserError",
    r"tomllib\.TOMLDecodeError",
    r"Failed to load configuration file",
    r"\.env.*file not found",
]

_DEPENDENCY_PATTERNS = [
    r"ModuleNotFoundError:\s*No module named\s*['\"]([^'\"]+)['\"]",
    r"ImportError:\s*cannot import name",
    r"Cannot find module\s*['\"]([^'\"]+)['\"]",
    r"NoClassDefFoundError",
    r"ClassNotFoundException",
    r"package\s+([^\s]+)\s+is not in GOROOT",
]


def classify_symptom_category(
    text: str,
    exception_class: Optional[str] = None,
) -> Tuple[FaultCategory, float, str]:
    """Deterministically classify error symptoms into the ORACLE FaultTaxonomy."""
    combined = f"{exception_class or ''} {text}".strip()

    # 1. Database Connectivity & Schema
    for pat in _DATABASE_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return (FaultCategory.DATABASE_CONNECTIVITY_SCHEMA, 0.92, pat)

    # 2. API Communication Failure
    for pat in _API_NETWORK_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return (FaultCategory.API_COMMUNICATION_FAILURE, 0.90, pat)

    # 3. IO Contract Violation
    for pat in _IO_CONTRACT_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return (FaultCategory.IO_CONTRACT_VIOLATION, 0.88, pat)

    # 4. Data Validation and Transformation Error
    for pat in _DATA_TRANSFORM_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return (FaultCategory.DATA_VALIDATION_TRANSFORMATION, 0.87, pat)

    # 5. Configuration Missing or Invalid
    for pat in _CONFIG_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return (FaultCategory.CONFIG_MISSING_OR_INVALID, 0.89, pat)

    # 6. Dependency and Import Failure
    for pat in _DEPENDENCY_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return (FaultCategory.DEPENDENCY_IMPORT_FAILURE, 0.94, pat)

    # Default fallback
    if exception_class and any(err in exception_class for err in ("Error", "Exception", "Fault", "Panic")):
        return (FaultCategory.RUNTIME_EXCEPTION, 0.70, "generic_runtime_exception")

    return (FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE, 0.30, "unrecognized_symptom")


def audit_environment_configuration(root_dir: str) -> List[TelemetryFinding]:
    """Cross-reference example configuration manifests against local files or environment variables."""
    findings: List[TelemetryFinding] = []
    if not root_dir or not os.path.exists(root_dir):
        return findings

    # Look for .env.example or .env.template
    example_names = [".env.example", ".env.template", ".env.sample"]
    example_path = None
    for name in example_names:
        p = os.path.join(root_dir, name)
        if os.path.exists(p) and os.path.isfile(p):
            example_path = p
            break

    if not example_path:
        return findings

    # Extract required keys
    required_keys: Set[str] = set()
    try:
        with open(example_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    if key:
                        required_keys.add(key)
    except Exception:
        return findings

    # Check against .env in repo root
    env_path = os.path.join(root_dir, ".env")
    configured_keys: Set[str] = set()
    if os.path.exists(env_path) and os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        key = stripped.split("=", 1)[0].strip()
                        if key:
                            configured_keys.add(key)
        except Exception:
            pass

    # Missing mandatory keys
    missing = [k for k in sorted(required_keys) if k not in configured_keys and k not in os.environ]
    if missing:
        findings.append(
            TelemetryFinding(
                category=FaultCategory.CONFIG_MISSING_OR_INVALID,
                confidence=0.88,
                component=os.path.relpath(example_path, root_dir).replace("\\", "/"),
                summary_message=f"Mandatory environment keys declared in {os.path.basename(example_path)} missing from .env: {', '.join(missing[:5])}",
                observed_signals={
                    "declared_required_keys": sorted(list(required_keys)),
                    "missing_keys": missing,
                    "example_file": os.path.basename(example_path),
                },
                reliability="direct_observation",
                limitations=["Environment variables may be injected by container orchestrator at runtime"],
            )
        )

    return findings


def analyze_runtime_symptoms(
    symptom_text: Optional[str] = None,
    traceback_text: Optional[str] = None,
    root_dir: Optional[str] = None,
) -> List[TelemetryFinding]:
    """Analyze observed symptoms, runtime tracebacks, and configuration files into discrete findings."""
    findings: List[TelemetryFinding] = []

    # 1. Environment config audit if directory provided
    if root_dir:
        config_findings = audit_environment_configuration(root_dir)
        findings.extend(config_findings)

    # 2. Parse traceback if provided
    tb = parse_runtime_traceback(traceback_text) if traceback_text else None
    if tb and tb.raw_text:
        cat, conf, pattern = classify_symptom_category(tb.error_message or tb.raw_text, tb.exception_class)
        root_f = tb.root_frame
        comp = root_f.file_path if root_f else "runtime_traceback"
        line_num = root_f.line_number if root_f else None

        findings.append(
            TelemetryFinding(
                category=cat,
                confidence=conf,
                component=comp,
                line_number=line_num,
                exception_class=tb.exception_class,
                summary_message=f"{tb.exception_class}: {tb.error_message}" if tb.error_message else tb.exception_class,
                observed_signals={
                    "exception_class": tb.exception_class,
                    "error_message": tb.error_message,
                    "matched_pattern": pattern,
                    "total_frames": len(tb.frames),
                    "innermost_frame": {
                        "file": root_f.file_path,
                        "line": root_f.line_number,
                        "func": root_f.function_name,
                    } if root_f else None,
                },
                reliability="direct_observation",
                limitations=["Traceback represents runtime termination point, which may be downstream of root cause"],
            )
        )

    # 3. Analyze general symptom text if provided (and distinct from traceback)
    if symptom_text and symptom_text.strip() and symptom_text.strip() != (traceback_text or "").strip():
        sanitized_symptom = redact_secrets(symptom_text.strip())
        cat, conf, pattern = classify_symptom_category(sanitized_symptom)
        # Avoid duplicate if same category as traceback finding
        already_present = any(f.category == cat for f in findings)
        if not already_present or cat != FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
            findings.append(
                TelemetryFinding(
                    category=cat,
                    confidence=max(0.40, conf - 0.1),  # Slightly lower confidence without formal traceback
                    component="system_telemetry",
                    summary_message=sanitized_symptom.splitlines()[0][:120],
                    observed_signals={
                        "raw_symptom": sanitized_symptom,
                        "matched_pattern": pattern,
                    },
                    reliability="heuristic_inference",
                    limitations=["Symptom string matched via heuristic taxonomy patterns without full stack frame"],
                )
            )

    return findings


def telemetry_to_evidence(
    findings: List[TelemetryFinding],
    start_seq: int = 1,
    run_id: Optional[str] = None,
) -> List[DiagnosticEvidenceRecord]:
    """Convert structured telemetry findings into schema-compliant DiagnosticEvidenceRecord instances.

    Guarantees unique evidence IDs across runs via run_id scoping and enforces strict secret redaction.
    """
    records: List[DiagnosticEvidenceRecord] = []
    seq = start_seq

    for f in findings:
        clean_run = str(run_id).replace("diag-", "").replace("-", "")[:8] if run_id else None
        eid = f"EVID-TELEM-{clean_run}-{seq:03d}" if clean_run else f"EVID-TELEM-{seq:03d}"
        seq += 1
        loc = f"{f.component}:{f.line_number}" if f.line_number else f.component

        # Ensure all observed data strings and nested collections are sanitized
        safe_signals: Dict[str, Any] = {}
        for k, v in f.observed_signals.items():
            if isinstance(v, str):
                safe_signals[k] = redact_secrets(v)
            elif isinstance(v, list):
                safe_signals[k] = [redact_secrets(item) if isinstance(item, str) else item for item in v]
            elif isinstance(v, dict):
                safe_signals[k] = {
                    dk: redact_secrets(dv) if isinstance(dv, str) else dv
                    for dk, dv in v.items()
                }
            else:
                safe_signals[k] = v

        records.append(
            DiagnosticEvidenceRecord(
                evidence_id=eid,
                evidence_type="runtime_telemetry",
                source_component=f"file:{f.component}" if "/" in f.component or "\\" in f.component else f.component,
                extraction_method="telemetry_analyzer",
                location=loc,
                observed_data={
                    "fault_category": f.category.value,
                    "summary": redact_secrets(f.summary_message),
                    "confidence": f.confidence,
                    **safe_signals,
                },
                reliability=f.reliability,
                limitations=f.limitations or ["Observed runtime telemetry"],
            )
        )

    return records
