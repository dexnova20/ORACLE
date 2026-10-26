"""Illustrative synthetic diagnostic cases used strictly for schema validation and testing.

All cases in this module are clearly designated with `is_synthetic = True`
and do not represent real-world incident telemetry.
"""

from ml.dataset.schema import (
    CaseFeatures,
    DiagnosticCase,
    ExpectedDiagnosticOutcome,
    GroundTruthLabel,
    ObservedSymptom,
    ProvenanceMetadata,
    TelemetryFeatures,
    TestResultFeature,
)
from ml.taxonomy.fault_taxonomy import FaultCategory

# Synthetic example 1: Database unreachable (simulated port closed)
SYNTHETIC_DATABASE_UNREACHABLE_CASE = DiagnosticCase(
    case_id="synth-case-db-001",
    project_id="oracle-mock-project",
    scenario_id="scenario-postgres-down",
    is_synthetic=True,
    provenance=ProvenanceMetadata(
        generator_info="ORACLE Test Fixture Generator",
        platform="win32/mock",
    ),
    features=CaseFeatures(
        symptoms=[
            ObservedSymptom(
                symptom_type="exception",
                source="oracle.db.session",
                message_pattern="psycopg.OperationalError: connection to server at 'localhost' (127.0.0.1), port 5432 failed: Connection refused",
                severity="error",
                timestamp_offset_ms=120.0,
            ),
            ObservedSymptom(
                symptom_type="http_status",
                source="api_gateway",
                message_pattern="GET /api/v1/status returned 200 with database.connected=false",
                severity="warning",
                timestamp_offset_ms=135.0,
            ),
        ],
        component_identifiers=["backend_api", "database_pool"],
        dependency_identifiers=["postgresql"],
        test_results=[
            TestResultFeature(
                test_id="test_check_db_connectivity_live_fast_timeout",
                passed=True,
                duration_ms=2100.0,
                error_type=None,
                error_message_snippet=None,
            )
        ],
        telemetry=TelemetryFeatures(
            latency_p50_ms=45.0,
            latency_p95_ms=2150.0,
            error_rate=0.5,
            cpu_utilization_pct=12.5,
            memory_rss_mb=95.0,
        ),
        missing_evidence_indicators=["postgresql_server_error_log"],
    ),
    ground_truth=GroundTruthLabel(
        root_cause_category=FaultCategory.DATABASE_CONNECTIVITY_SCHEMA,
        root_cause_component="postgresql_daemon",
        root_cause_detail="PostgreSQL daemon is not running on port 5432.",
        injection_method="service_stopped",
        verified=True,
    ),
    expected_outcome=ExpectedDiagnosticOutcome(
        primary_action="START_POSTGRES_SERVICE",
        recommended_probes=["check_port_5432", "inspect_pg_hba_conf"],
        urgency="high",
    ),
)

# Synthetic example 2: Missing environment configuration
SYNTHETIC_CONFIG_MISSING_CASE = DiagnosticCase(
    case_id="synth-case-cfg-002",
    project_id="oracle-mock-project",
    scenario_id="scenario-missing-secret-key",
    is_synthetic=True,
    provenance=ProvenanceMetadata(
        generator_info="ORACLE Test Fixture Generator",
        platform="linux/mock",
    ),
    features=CaseFeatures(
        symptoms=[
            ObservedSymptom(
                symptom_type="exception",
                source="oracle.core.config",
                message_pattern="pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings: SECRET_KEY Field required",
                severity="critical",
                timestamp_offset_ms=15.0,
            ),
            ObservedSymptom(
                symptom_type="exit_code",
                source="uvicorn",
                message_pattern="Process exited with code 1 during startup lifecycle",
                severity="critical",
                timestamp_offset_ms=22.0,
            ),
        ],
        component_identifiers=["backend_api", "config_loader"],
        dependency_identifiers=["pydantic_settings"],
        test_results=[
            TestResultFeature(
                test_id="test_config_settings_validation",
                passed=False,
                duration_ms=45.0,
                error_type="ValidationError",
                error_message_snippet="ValidationError: Field required [type=missing, input_value={}]",
            )
        ],
        telemetry=None,
        missing_evidence_indicators=[],
    ),
    ground_truth=GroundTruthLabel(
        root_cause_category=FaultCategory.CONFIG_MISSING_OR_INVALID,
        root_cause_component="env_configuration",
        root_cause_detail="Required environment variable SECRET_KEY was omitted from runtime environment.",
        injection_method="unset_env_var",
        verified=True,
    ),
    expected_outcome=ExpectedDiagnosticOutcome(
        primary_action="SET_ENVIRONMENT_VARIABLES",
        recommended_probes=["verify_env_file_presence"],
        urgency="critical",
    ),
)

# Synthetic example 3: Ambiguous case with insufficient telemetry (correct action is abstention)
SYNTHETIC_INSUFFICIENT_EVIDENCE_CASE = DiagnosticCase(
    case_id="synth-case-ambiguous-003",
    project_id="external-service-mock",
    scenario_id="scenario-intermittent-timeout",
    is_synthetic=True,
    provenance=ProvenanceMetadata(
        generator_info="ORACLE Test Fixture Generator",
        platform="generic/mock",
    ),
    features=CaseFeatures(
        symptoms=[
            ObservedSymptom(
                symptom_type="log_warning",
                source="upstream_client",
                message_pattern="Request to /process encountered transient socket delay",
                severity="warning",
                timestamp_offset_ms=5000.0,
            )
        ],
        component_identifiers=["network_gateway"],
        dependency_identifiers=[],
        test_results=[],
        telemetry=TelemetryFeatures(
            latency_p50_ms=None,
            latency_p95_ms=None,
            error_rate=0.05,
            cpu_utilization_pct=None,
            memory_rss_mb=None,
        ),
        missing_evidence_indicators=["server_logs", "tcpdump", "cpu_profile"],
    ),
    ground_truth=GroundTruthLabel(
        root_cause_category=FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE,
        root_cause_component="unknown",
        root_cause_detail="Signals are incomplete and missing server-side telemetry.",
        injection_method="telemetry_truncation",
        verified=True,
    ),
    expected_outcome=ExpectedDiagnosticOutcome(
        primary_action="ABSTAIN_INSUFFICIENT_EVIDENCE",
        recommended_probes=["request_server_logs", "enable_extended_telemetry"],
        urgency="medium",
    ),
)
