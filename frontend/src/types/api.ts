/**
 * TypeScript contract interfaces matching backend FastAPI schemas.
 * Reference: backend/oracle/schemas/diagnostics.py
 * Reference: backend/oracle/schemas/repository.py
 * Reference: backend/oracle/schemas/execution.py
 */

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
  environment: string;
}

export interface DatabaseStatus {
  connected: boolean;
  message: string;
  driver: string;
}

export interface SystemStatusResponse {
  app: HealthResponse;
  database: DatabaseStatus;
  persistence_mode?: "durable_postgresql" | "in_memory_transient" | string;
  docker_isolation_available?: boolean;
  supported_languages?: string[];
  supported_ecosystems?: string[];
}

export type SourceType = "git" | "local_directory";
export type RepositoryStatus = "registered" | "archived";

export interface Repository {
  id: string;
  name: string;
  url: string;
  source_type: SourceType;
  status: RepositoryStatus;
  created_at: string;
  updated_at: string;
}

export interface RepositoryCreateInput {
  name: string;
  url: string;
  source_type?: SourceType;
}

/**
 * Diagnostic workflow types and contracts.
 */
export type ComponentType =
  | "source_file"
  | "internal_module"
  | "external_package"
  | "stdlib_module"
  | "unresolved_reference";

export type ComponentStatus =
  | "analyzed"
  | "syntax_error"
  | "unresolved"
  | "unsupported"
  | "blocked";

export interface DiagnosticComponent {
  id: string;
  name: string;
  component_type: ComponentType;
  file_path?: string | null;
  status: ComponentStatus;
  metadata: Record<string, unknown>;
}

export interface DiagnosticDependencyEdge {
  source_component_id: string;
  target_component_id: string;
  dependency_type: "stdlib" | "internal" | "external" | "unresolved";
  line_number?: number | null;
  import_statement?: string | null;
  is_resolved: boolean;
  provenance: Record<string, unknown>;
}

export interface DiagnosticSystemMap {
  components: DiagnosticComponent[];
  edges: DiagnosticDependencyEdge[];
  total_components: number;
  total_dependencies: number;
  internal_dependency_count: number;
  external_dependency_count: number;
  stdlib_edge_count: number;
  unresolved_dependency_count: number;
  syntax_error_component_count: number;
}

export interface DiagnosticEvidenceRecord {
  evidence_id: string;
  evidence_type: string;
  source_component: string;
  extraction_method: string;
  location?: string | null;
  observed_data: Record<string, unknown>;
  reliability: "direct_observation" | "inferred_signal" | "limited_context";
  limitations: string[];
  timestamp: string;
}

export interface FaultHypothesis {
  hypothesis_id: string;
  category: string;
  category_title: string;
  affected_component: string;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  alternative_explanations: string[];
  confidence_level: "high" | "medium" | "low" | "uncertain";
  verification_status:
    | "verified"
    | "partially_verified"
    | "not_verified"
    | "blocked"
    | "unsupported";
  remediation_suggestion?: string | null;
  abstention_reason?: string | null;
  assumptions?: string[];
  relative_ranking_score?: number;
  score_rationale?: string | null;
  uncertainty_reason?: string | null;
}

export interface VerificationOutcome {
  hypothesis_id: string;
  method: string;
  status: "verified" | "partially_verified" | "not_verified" | "blocked" | "unsupported";
  workload_profile?: string | null;
  exit_code?: number | null;
  details: string;
  timestamp: string;
}

/**
 * Diagnostic Probe contracts (Adaptive Probe Planning).
 */
export interface DiagnosticProbe {
  probe_id: string;
  probe_type: string;
  target_component: string;
  prerequisites: string[];
  target_hypothesis_ids: string[];
  expected_outcomes: string[] | Record<string, string>;
  estimated_cost: number;
  cost_label: string;
  safety_classification: string;
  requires_dynamic: boolean;
  availability_status: string;
  selection_reason?: string | null;
  rejection_reason?: string | null;
}

export interface ProbeResult {
  probe_id: string;
  probe_type: string;
  run_id: string;
  target_component: string;
  outcome: string;
  generated_evidence_ids: string[];
  execution_status: string;
  duration_ms: number;
  unsupported_reason?: string | null;
  applied_safety_policy: string;
  ranking_changed: boolean;
  details: string | Record<string, unknown>;
  timestamp: string;
}

export interface DiagnosticDecisionRecord {
  iteration: number;
  decision_type: string;
  selected_probe_id?: string | null;
  rationale: string;
  candidates_considered_count: number;
  remaining_uncertainty?: string | null;
  stopping_reason?: string | null;
  timestamp: string;
}

export interface DiagnosticProbesResponse {
  run_id: string;
  candidate_probes: DiagnosticProbe[];
  executed_probes: ProbeResult[];
  stopping_reason?: string | null;
}

export interface DiagnosticDecisionsResponse {
  run_id: string;
  decisions?: DiagnosticDecisionRecord[];
  investigation_history?: DiagnosticDecisionRecord[];
  stopping_reason?: string | null;
}

export interface DiagnosticRunRequest {
  capabilities?: string[];
  allow_dynamic?: boolean;
  workload_profile?: string | null;
  timeout_seconds?: number | null;
  max_files?: number | null;
  max_iterations?: number;
  symptom_description?: string | null;
  runtime_traceback?: string | null;
}

export interface DiagnosticReport {
  run_id: string;
  repository_id: string;
  repository_name: string;
  repository_url: string;
  source_type: string;
  commit_hash?: string | null;
  status: "completed" | "partial" | "failed";
  completed_stages: string[];
  unsupported_stages: string[];
  system_map: DiagnosticSystemMap;
  evidence: DiagnosticEvidenceRecord[];
  hypotheses: FaultHypothesis[];
  verification: VerificationOutcome[];
  candidate_probes?: DiagnosticProbe[];
  executed_probes?: ProbeResult[];
  investigation_history?: DiagnosticDecisionRecord[];
  stopping_reason?: string | null;
  summary: string;
  recommendations: string[];
  abstention_reason?: string | null;
  error_message?: string | null;
  started_at: string;
  completed_at: string;
  duration_ms: number;
}

/**
 * Generic state representation for asynchronous remote operations.
 */
export type AsyncState<T> =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "success"; data: T; timestamp: string }
  | { state: "error"; error: string; timestamp: string };
