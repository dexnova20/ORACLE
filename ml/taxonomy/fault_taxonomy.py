"""Versioned taxonomy of observable software faults for ORACLE diagnostics."""

from enum import Enum
from typing import Dict, List
from pydantic import BaseModel, ConfigDict, Field

TAXONOMY_VERSION = "1.0.0"


class FaultCategory(str, Enum):
    """Canonical taxonomy categories for observable software faults."""

    CONFIG_MISSING_OR_INVALID = "config_missing_or_invalid"
    DEPENDENCY_IMPORT_FAILURE = "dependency_import_failure"
    IO_CONTRACT_VIOLATION = "io_contract_violation"
    RUNTIME_EXCEPTION = "runtime_exception"
    DATA_VALIDATION_TRANSFORMATION = "data_validation_transformation"
    API_COMMUNICATION_FAILURE = "api_communication_failure"
    DATABASE_CONNECTIVITY_SCHEMA = "database_connectivity_schema"
    MODEL_LOADING_INFERENCE_FAILURE = "model_loading_inference_failure"
    PERFORMANCE_ANOMALY = "performance_anomaly"
    UNKNOWN_INSUFFICIENT_EVIDENCE = "unknown_insufficient_evidence"


class TaxonomyEntry(BaseModel):
    """Detailed diagnostic metadata for a specific fault taxonomy category."""

    model_config = ConfigDict(frozen=True)

    category: FaultCategory = Field(..., description="Unique category enum identifier")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Detailed definition of the fault class")
    observable_evidence: List[str] = Field(
        ...,
        description="Empirical signals, logs, or metrics observed when this fault occurs",
    )
    confounding_causes: List[str] = Field(
        ...,
        description="Alternative root causes that can produce identical or similar symptoms",
    )
    safe_reproduction: str = Field(
        ...,
        description="Protocol for safely reproducing this fault in an isolated sandbox",
    )
    required_ground_truth_evidence: List[str] = Field(
        ...,
        description="Evidence required to definitively establish this category as ground truth",
    )
    unclassifiable_boundary_conditions: List[str] = Field(
        ...,
        description="Scenarios where available signals are insufficient for confident classification",
    )


FAULT_TAXONOMY: Dict[FaultCategory, TaxonomyEntry] = {
    FaultCategory.CONFIG_MISSING_OR_INVALID: TaxonomyEntry(
        category=FaultCategory.CONFIG_MISSING_OR_INVALID,
        title="Missing or Invalid Configuration",
        description=(
            "Application startup or runtime failure caused by absent environment variables, "
            "unreadable configuration files, malformed syntax (YAML/JSON/TOML), or out-of-range "
            "configuration values required by the system."
        ),
        observable_evidence=[
            "Pydantic ValidationError during settings instantiation",
            "KeyError on os.environ access during startup",
            "Non-zero process exit code during bootstrap phase before HTTP listener opens",
            "Log messages referencing missing .env keys or invalid type coercion",
        ],
        confounding_causes=[
            "Deployment script failed to decrypt or mount secret vault volumes",
            "Missing local directory permissions preventing read of config file",
            "Typo in environment variable name in CI/CD pipeline",
        ],
        safe_reproduction=(
            "Instantiate application factory with empty or malformed mock environment variables "
            "in an isolated container with no filesystem access to .env."
        ),
        required_ground_truth_evidence=[
            "Exact configuration key identified as missing or violating schema validator",
            "Process failure occurs deterministically at bootstrap before network listeners bind",
            "Diff of environment state against declared configuration schema",
        ],
        unclassifiable_boundary_conditions=[
            "Configuration value is syntactically valid but semantically points to an unreachable host (overlaps with connectivity faults)",
            "Dynamic configurations loaded over network where failure could be config or network transit",
        ],
    ),
    FaultCategory.DEPENDENCY_IMPORT_FAILURE: TaxonomyEntry(
        category=FaultCategory.DEPENDENCY_IMPORT_FAILURE,
        title="Dependency and Import Failure",
        description=(
            "Failure to resolve, load, or link required software dependencies, packages, "
            "shared libraries, native C-extensions, or circular import cycles within application modules."
        ),
        observable_evidence=[
            "ImportError or ModuleNotFoundError during module resolution",
            "OSError or ImportError mentioning missing shared object (.so / .dll / dylib)",
            "AttributeError: partially initialized module due to circular dependency",
            "Package version conflict warning from package manager or runtime loader",
        ],
        confounding_causes=[
            "Operating system architecture mismatch (e.g. x86_64 wheel on aarch64)",
            "Missing system-level C build tools or headers (gcc, libpq-dev)",
            "Virtual environment not activated or corrupted site-packages path",
        ],
        safe_reproduction=(
            "Execute Python interpreter import probe within an isolated container lacking "
            "the specific package or with an intentionally broken module cycle."
        ),
        required_ground_truth_evidence=[
            "Stack trace terminating in import statement or dynamic __import__ call",
            "Verification that package is absent from site-packages or has unresolvable circular reference",
        ],
        unclassifiable_boundary_conditions=[
            "Optional plugin import failure that is caught and gracefully handled (not a fault unless requested)",
            "Dynamic runtime imports triggered only under rare branch execution",
        ],
    ),
    FaultCategory.IO_CONTRACT_VIOLATION: TaxonomyEntry(
        category=FaultCategory.IO_CONTRACT_VIOLATION,
        title="Input/Output Contract Violation",
        description=(
            "Breach of explicit interface contracts between components, including unexpected nulls, "
            "missing required payload fields, type mismatches, or schema drift across service boundaries."
        ),
        observable_evidence=[
            "HTTP 422 Unprocessable Entity returned by API boundary",
            "JSONSchema or Pydantic validation failure in response serializer",
            "NullPointerException or AttributeError: 'NoneType' has no attribute on response parsing",
            "Missing mandatory header or unsupported content-type in HTTP exchange",
        ],
        confounding_causes=[
            "Client sending outdated payload version prior to scheduled migration",
            "API gateway or reverse proxy stripping or transforming request headers",
            "Concurrent deployment race condition between frontend and backend services",
        ],
        safe_reproduction=(
            "Transmit an HTTP request with omitted mandatory keys or corrupted payload types "
            "against the target API endpoint."
        ),
        required_ground_truth_evidence=[
            "Recorded request/response payload paired with the formal schema specification",
            "Discrepancy report highlighting the exact field path, expected type, and actual type received",
        ],
        unclassifiable_boundary_conditions=[
            "Malformed data originating from corrupted third-party webhook outside the system boundary",
            "Ambiguous error responses (HTTP 500) where the underlying cause was an unvalidated 400-level input",
        ],
    ),
    FaultCategory.RUNTIME_EXCEPTION: TaxonomyEntry(
        category=FaultCategory.RUNTIME_EXCEPTION,
        title="Unhandled Runtime Exception",
        description=(
            "Uncaught procedural or logic exceptions during code execution, including "
            "ZeroDivisionError, KeyError, IndexError, TypeError, recursion limits, or unhandled null references."
        ),
        observable_evidence=[
            "Unhandled exception stack trace logged at ERROR or CRITICAL level",
            "HTTP 500 Internal Server Error returned to consumer",
            "Abrupt process termination with traceback output in stderr",
            "Crash reports or core dumps generated by runtime interpreter",
        ],
        confounding_causes=[
            "Hardware memory corruption (bit flips) or host OS resource preemption",
            "Unexpected external API response shape triggering an unhandled parsing branch",
        ],
        safe_reproduction=(
            "Execute the specific function with edge-case input parameters (e.g. empty list, "
            "zero denominator, unexpected dictionary keys) in unit test harness."
        ),
        required_ground_truth_evidence=[
            "Complete stack trace with file paths, function names, and line numbers",
            "Input arguments that deterministically reproduce the exception in isolation",
        ],
        unclassifiable_boundary_conditions=[
            "Non-deterministic thread race conditions that only manifest under multi-core load",
            "Exceptions swallowed by broad 'except Exception:' handlers that corrupt downstream state silently",
        ],
    ),
    FaultCategory.DATA_VALIDATION_TRANSFORMATION: TaxonomyEntry(
        category=FaultCategory.DATA_VALIDATION_TRANSFORMATION,
        title="Data Validation and Transformation Error",
        description=(
            "Failures occurring during data parsing, serialization, deserialization, type coercion, "
            "character encoding (UTF-8/ASCII), datetime timezone shifts, or mathematical conversions."
        ),
        observable_evidence=[
            "UnicodeDecodeError / UnicodeEncodeError in log streams",
            "ValueError: invalid literal for int() with base 10",
            "Unexpected timezone shift altering calculated date boundaries or sorting order",
            "Truncated or NaN values propagating through calculation pipelines",
        ],
        confounding_causes=[
            "Corrupt binary data transmitted over network socket",
            "Host operating system locale or default encoding divergence",
        ],
        safe_reproduction=(
            "Pass non-UTF-8 byte sequences or naive/aware datetime strings through transformation pipeline."
        ),
        required_ground_truth_evidence=[
            "Input byte/string data paired with transformation function and failing assertion",
            "Identification of the lossy coercion step or missing encoding handler",
        ],
        unclassifiable_boundary_conditions=[
            "Silent floating-point rounding errors that do not raise exceptions but degrade calculation accuracy",
        ],
    ),
    FaultCategory.API_COMMUNICATION_FAILURE: TaxonomyEntry(
        category=FaultCategory.API_COMMUNICATION_FAILURE,
        title="API Communication Failure",
        description=(
            "Failures in network communication between services, including socket connection timeouts, "
            "DNS resolution failures, SSL/TLS handshake failures, HTTP 502/503/504 responses, and rate limits (429)."
        ),
        observable_evidence=[
            "HTTP 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout",
            "ConnectionRefusedError or ConnectTimeout raised by HTTP client library",
            "ssl.SSLError: certificate verify failed during TLS negotiation",
            "HTTP 429 Too Many Requests with Retry-After header",
        ],
        confounding_causes=[
            "Network routing partition or DNS server downtime",
            "Upstream service experiencing internal database lock contention",
            "Client-side connection pool saturation stalling requests before socket emission",
        ],
        safe_reproduction=(
            "Simulate downstream service unavailability by routing requests to closed port or mock proxy "
            "configured with artificial delay exceeding client timeout."
        ),
        required_ground_truth_evidence=[
            "Client-side outbound request logs with timestamps matching upstream access logs or timeouts",
            "Network packet capture or TCP socket status confirming termination (RST, timeout, or SSL alert)",
        ],
        unclassifiable_boundary_conditions=[
            "Intermittent packet drop over public internet where root cause cannot be isolated to either endpoint",
            "Upstream service returning valid HTTP 200 with error payload embedded in body",
        ],
    ),
    FaultCategory.DATABASE_CONNECTIVITY_SCHEMA: TaxonomyEntry(
        category=FaultCategory.DATABASE_CONNECTIVITY_SCHEMA,
        title="Database Connectivity and Schema Failure",
        description=(
            "Inability to establish or maintain database connections, pool exhaustion, authentication "
            "rejections, missing tables/columns, migration version mismatches, or transaction deadlocks."
        ),
        observable_evidence=[
            "psycopg.OperationalError: connection to server at port 5432 failed",
            "SQLAlchemy ProgrammingError: relation 'table_name' does not exist",
            "Alembic Target database is not up to date warning or revision mismatch",
            "psycopg.errors.DeadlockDetected or QueuePool limit exceeded",
        ],
        confounding_causes=[
            "Database server host rebooting or under maintenance window",
            "Firewall / security group rule dropping port 5432 traffic",
            "Application connecting with wrong credentials or to wrong database name",
        ],
        safe_reproduction=(
            "Execute database queries against a stopped database container or a database instance "
            "without applied migrations in an isolated test environment."
        ),
        required_ground_truth_evidence=[
            "Database error code (e.g. PostgreSQL SQLSTATE 42P01 for undefined table, 08006 for connection failure)",
            "Verification of database schema catalog (information_schema / alembic_version) confirming schema state",
        ],
        unclassifiable_boundary_conditions=[
            "Slow queries that look like network timeouts due to lock waits on unindexed columns",
            "Connection leaks that only fail after hours of continuous operation under high concurrency",
        ],
    ),
    FaultCategory.MODEL_LOADING_INFERENCE_FAILURE: TaxonomyEntry(
        category=FaultCategory.MODEL_LOADING_INFERENCE_FAILURE,
        title="Model Loading or Inference Failure",
        description=(
            "Failures specific to machine learning and statistical models, including missing model checkpoint files, "
            "tensor shape mismatches, CUDA out-of-memory errors, model architecture deserialization incompatibilities, "
            "or NaN output during forward inference."
        ),
        observable_evidence=[
            "FileNotFoundError when accessing model checkpoint weight file",
            "RuntimeError: shape mismatch or size mismatch in tensor operations",
            "torch.cuda.OutOfMemoryError or CUDA device unavailable",
            "Model output tensors containing NaN or Inf values",
        ],
        confounding_causes=[
            "GPU driver / CUDA version mismatch with installed ML framework",
            "Host running out of physical RAM during model weight loading",
            "Input feature preprocessing pipeline emitting wrong dimensionality",
        ],
        safe_reproduction=(
            "Attempt loading model checkpoint with missing weight file or pass tensor of mismatched dimension "
            "in test container without GPU access."
        ),
        required_ground_truth_evidence=[
            "Model artifact metadata confirming file absence, checksum mismatch, or framework version drift",
            "Input tensor dimension log contrasted with model layer definition",
        ],
        unclassifiable_boundary_conditions=[
            "Subtle concept drift or model performance degradation that does not throw an explicit exception",
            "GPU hardware throttling producing erratic inference latency without outright failure",
        ],
    ),
    FaultCategory.PERFORMANCE_ANOMALY: TaxonomyEntry(
        category=FaultCategory.PERFORMANCE_ANOMALY,
        title="Performance and Resource Anomaly",
        description=(
            "Degradation of system performance without immediate crash, including latency spikes (>3 sigma), "
            "CPU pegging (100%), unbounded memory growth (leaks), thread starvation, or disk I/O bottlenecks."
        ),
        observable_evidence=[
            "P95 or P99 response latency exceeding defined SLA thresholds by >300%",
            "System telemetry showing sustained CPU utilization >95% across all cores",
            "Memory resident set size (RSS) monotonically increasing under constant workload",
            "ThreadPoolExecutor or async event loop lag exceeding threshold",
        ],
        confounding_causes=[
            "External noisy neighbors on shared virtualization host",
            "JVM / Python garbage collection pause spikes",
            "Legitimate high traffic spike exceeding provisioned capacity",
        ],
        safe_reproduction=(
            "Execute synthetic benchmark harness simulating high concurrency or unoptimized recursive operations "
            "under resource-capped cgroup constraints."
        ),
        required_ground_truth_evidence=[
            "Time-series telemetry showing resource saturation correlated with latency degradation",
            "CPU/Memory profile (cProfile, py-spy, heap dump) identifying the hot path or uncollected references",
        ],
        unclassifiable_boundary_conditions=[
            "Transient micro-spikes lasting under 100ms with no corresponding log trace",
            "Performance degradation on external SaaS dependencies where no internal profiling data exists",
        ],
    ),
    FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE: TaxonomyEntry(
        category=FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE,
        title="Unknown or Insufficient Evidence",
        description=(
            "Failures or behavioral anomalies where observable telemetry, logs, and test results are "
            "missing, truncated, contradictory, or insufficient to establish a ground-truth root cause with confidence. "
            "The correct diagnostic action is deliberate abstention rather than hallucinating a false root cause."
        ),
        observable_evidence=[
            "Absence of diagnostic logs during reported incident window",
            "Generic error message without stack trace or error code (e.g. 'Operation failed')",
            "Contradictory signals (e.g. ping succeeds but higher-level health probe returns indeterminate)",
            "System state reset before forensic logs could be persisted",
        ],
        confounding_causes=[
            "Log shipping agent crashed or dropped log buffers under high volume",
            "Log retention policy truncated historical records prematurely",
            "Failure occurred in uninstrumented third-party binary or legacy system",
        ],
        safe_reproduction=(
            "Submit an empty or stripped telemetry payload with zero diagnostic signals to the diagnostic engine."
        ),
        required_ground_truth_evidence=[
            "Audit of available telemetry confirming that critical discriminators are absent",
            "Verification that diagnostic model confidence falls below the deliberate abstention threshold",
        ],
        unclassifiable_boundary_conditions=[
            "By definition, all cases assigned to this category represent ambiguous boundary conditions "
            "requiring further active probing or human escalation.",
        ],
    ),
}


def get_taxonomy_version() -> str:
    """Return the active taxonomy version string."""
    return TAXONOMY_VERSION


def get_taxonomy_entry(category: FaultCategory) -> TaxonomyEntry:
    """Retrieve full diagnostic entry for a specific fault category."""
    if category not in FAULT_TAXONOMY:
        raise KeyError(f"Fault category '{category}' is not defined in taxonomy v{TAXONOMY_VERSION}")
    return FAULT_TAXONOMY[category]


def list_taxonomy_categories() -> List[FaultCategory]:
    """Return all defined taxonomy categories in canonical order."""
    return list(FAULT_TAXONOMY.keys())
