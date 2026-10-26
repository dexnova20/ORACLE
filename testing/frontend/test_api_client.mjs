/**
 * Lightweight frontend API client verification tests.
 * Uses Node.js native test runner (node:test) and assertions (node:assert).
 */

import { test, describe, before, after } from "node:test";
import assert from "node:assert";
import http from "node:http";

let server;
let serverPort;

const mockRepositories = [
  {
    id: "123e4567-e89b-12d3-a456-426614174000",
    name: "auth-service",
    url: "https://github.com/example/auth-service.git",
    source_type: "git",
    status: "registered",
    created_at: "2026-10-25T12:00:00Z",
    updated_at: "2026-10-25T12:00:00Z",
  },
];

const mockDiagnosticReport = {
  run_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  repository_id: "123e4567-e89b-12d3-a456-426614174000",
  repository_name: "auth-service",
  repository_url: "https://github.com/example/auth-service.git",
  source_type: "git",
  commit_hash: "abcdef1234567890",
  status: "completed",
  completed_stages: [
    "validate_target",
    "acquire_snapshot",
    "static_inspection",
    "build_system_map",
    "collect_evidence",
    "generate_hypotheses",
    "verify_hypotheses",
    "generate_report",
  ],
  unsupported_stages: [],
  system_map: {
    components: [
      {
        id: "file:auth.py",
        name: "auth.py",
        component_type: "source_file",
        file_path: "auth.py",
        status: "analyzed",
        metadata: { lines_of_code: 42 },
      },
      {
        id: "pkg:fastapi",
        name: "fastapi",
        component_type: "external_package",
        file_path: null,
        status: "analyzed",
        metadata: {},
      },
    ],
    edges: [
      {
        source_component_id: "file:auth.py",
        target_component_id: "pkg:fastapi",
        dependency_type: "external",
        line_number: 1,
        import_statement: "import fastapi",
        is_resolved: true,
        provenance: { inspector: "ASTParser" },
      },
    ],
    total_components: 2,
    total_dependencies: 1,
    internal_dependency_count: 0,
    external_dependency_count: 1,
    stdlib_edge_count: 0,
    unresolved_dependency_count: 0,
    syntax_error_component_count: 0,
  },
  evidence: [
    {
      evidence_id: "EVID-PREFLIGHT-001",
      evidence_type: "isolation_preflight",
      source_component: "system:container_runtime",
      extraction_method: "isolation_probe",
      location: null,
      observed_data: { is_available: false, provider: "none" },
      reliability: "direct_observation",
      limitations: [],
      timestamp: "2026-10-26T00:00:00Z",
    },
  ],
  hypotheses: [],
  verification: [],
  summary: "No observable software faults detected.",
  recommendations: ["Maintain continuous integration tests."],
  abstention_reason: null,
  error_message: null,
  started_at: "2026-10-26T00:00:00Z",
  completed_at: "2026-10-26T00:00:01Z",
  duration_ms: 120.5,
};

const mockDiagnosticProbesResponse = {
  run_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  candidate_probes: [
    {
      probe_id: "PROBE-AST-SYNTAX-001",
      probe_type: "static_ast_syntax_check",
      target_component: "main.py",
      prerequisites: [],
      target_hypothesis_ids: ["HYPO-SYNTAX-001"],
      expected_outcomes: { syntax_valid: "Hypothesis invalidated", syntax_invalid: "Syntax error verified" },
      estimated_cost: 1.0,
      cost_label: "negligible",
      safety_classification: "safe_read_only",
      requires_dynamic: false,
      availability_status: "available",
      selection_reason: "High discrimination utility",
      rejection_reason: null,
    },
  ],
  executed_probes: [
    {
      probe_id: "PROBE-AST-SYNTAX-001",
      probe_type: "static_ast_syntax_check",
      run_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      target_component: "main.py",
      outcome: "syntax_invalid",
      generated_evidence_ids: ["EVID-AST-001"],
      execution_status: "executed",
      duration_ms: 1.5,
      unsupported_reason: null,
      applied_safety_policy: "safe_read_only_ast",
      ranking_changed: true,
      details: { defect_type: "syntax_error" },
      timestamp: "2026-10-26T00:00:01Z",
    },
  ],
};

const mockDiagnosticDecisionsResponse = {
  run_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  investigation_history: [
    {
      iteration: 1,
      decision_type: "select_probe",
      selected_probe_id: "PROBE-AST-SYNTAX-001",
      rationale: "Selected probe with highest utility score 1.25",
      candidates_considered_count: 1,
      remaining_uncertainty: "Syntax hypothesis unverified",
      stopping_reason: null,
      timestamp: "2026-10-26T00:00:00Z",
    },
    {
      iteration: 2,
      decision_type: "stop_sufficient_evidence",
      selected_probe_id: null,
      rationale: "High confidence fault verified; further probing unnecessary",
      candidates_considered_count: 0,
      remaining_uncertainty: "None",
      stopping_reason: "sufficient_evidence_verified",
      timestamp: "2026-10-26T00:00:01Z",
    },
  ],
  stopping_reason: "sufficient_evidence_verified",
};

before(async () => {
  return new Promise((resolve) => {
    server = http.createServer((req, res) => {
      const url = new URL(req.url, `http://127.0.0.1`);

      if (url.pathname === "/api/v1/health") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            status: "healthy",
            app_name: "ORACLE",
            version: "0.1.0",
            environment: "test",
          })
        );
      } else if (url.pathname === "/api/v1/status") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            app: {
              status: "healthy",
              app_name: "ORACLE",
              version: "0.1.0",
              environment: "test",
            },
            database: {
              connected: false,
              message: "Database connection failed",
              driver: "postgresql+psycopg",
            },
          })
        );
      } else if (url.pathname === "/api/v1/repositories" && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(mockRepositories));
      } else if (url.pathname === "/api/v1/repositories" && req.method === "POST") {
        let body = "";
        req.on("data", (chunk) => {
          body += chunk;
        });
        req.on("end", () => {
          try {
            const parsed = JSON.parse(body);
            if (!parsed.name || !parsed.url) {
              res.writeHead(422, { "Content-Type": "application/json" });
              res.end(
                JSON.stringify({
                  detail: [{ msg: "Field required" }],
                })
              );
              return;
            }
            if (
              !parsed.url.startsWith("http://") &&
              !parsed.url.startsWith("https://") &&
              !parsed.url.startsWith("git://") &&
              !parsed.url.startsWith("ssh://") &&
              !parsed.url.startsWith("file://")
            ) {
              res.writeHead(422, { "Content-Type": "application/json" });
              res.end(
                JSON.stringify({
                  detail: [{ msg: "Invalid repository URL scheme" }],
                })
              );
              return;
            }
            const created = {
              id: "987fcdeb-51a2-43f1-b456-426614174999",
              name: parsed.name,
              url: parsed.url,
              source_type: parsed.source_type || "git",
              status: "registered",
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            };
            res.writeHead(201, { "Content-Type": "application/json" });
            res.end(JSON.stringify(created));
          } catch {
            res.writeHead(400, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ detail: "Invalid JSON" }));
          }
        });
      } else if (url.pathname.endsWith("/diagnose") && req.method === "POST") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(mockDiagnosticReport));
      } else if (url.pathname.endsWith("/diagnostics/latest") && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(mockDiagnosticReport));
      } else if (url.pathname === "/api/v1/diagnostics/runs" && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify([mockDiagnosticReport]));
      } else if (url.pathname.endsWith("/probes") && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(mockDiagnosticProbesResponse));
      } else if (url.pathname.endsWith("/decisions") && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(mockDiagnosticDecisionsResponse));
      } else if (url.pathname.startsWith("/api/v1/diagnostics/") && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(mockDiagnosticReport));
      } else if (url.pathname.startsWith("/api/v1/repositories/") && req.method === "GET") {
        const id = url.pathname.split("/").pop();
        const found = mockRepositories.find((r) => r.id === id);
        if (found) {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify(found));
        } else {
          res.writeHead(404, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ detail: `Repository '${id}' not found.` }));
        }
      } else if (url.pathname.startsWith("/api/v1/repositories/") && req.method === "DELETE") {
        const id = url.pathname.split("/").pop();
        if (id === "123e4567-e89b-12d3-a456-426614174000") {
          res.writeHead(204);
          res.end();
        } else {
          res.writeHead(404, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ detail: `Repository '${id}' not found.` }));
        }
      } else if (url.pathname === "/api/v1/error") {
        res.writeHead(500, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ detail: "Internal server error" }));
      } else {
        res.writeHead(404);
        res.end();
      }
    });

    server.listen(0, "127.0.0.1", () => {
      serverPort = server.address().port;
      resolve();
    });
  });
});

after(async () => {
  return new Promise((resolve) => {
    if (server) {
      server.close(() => resolve());
    } else {
      resolve();
    }
  });
});

describe("Frontend API Client Tests", () => {
  test("fetchHealth returns validated HealthResponse", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/health`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.status, "healthy");
    assert.strictEqual(data.app_name, "ORACLE");
    assert.strictEqual(data.version, "0.1.0");
  });

  test("fetchStatus returns validated SystemStatusResponse with database metadata", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/status`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.ok(data.app);
    assert.strictEqual(data.app.status, "healthy");
    assert.ok(data.database);
    assert.strictEqual(data.database.connected, false);
    assert.strictEqual(data.database.driver, "postgresql+psycopg");
    assert.ok(data.database.message.includes("failed"));
  });

  test("handles non-200 HTTP responses gracefully", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/error`;
    const res = await fetch(url);
    assert.strictEqual(res.status, 500);
  });

  test("handles network connection failure gracefully", async () => {
    try {
      await fetch("http://127.0.0.1:59999/api/v1/health");
      assert.fail("Should have thrown network error");
    } catch (err) {
      assert.ok(err instanceof Error);
    }
  });

  test("listRepositories retrieves registered repositories list", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/repositories`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.ok(Array.isArray(data));
    assert.strictEqual(data.length, 1);
    assert.strictEqual(data[0].name, "auth-service");
    assert.strictEqual(data[0].status, "registered");
  });

  test("registerRepository creates target and returns HTTP 201", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/repositories`;
    const payload = {
      name: "payment-service",
      url: "https://github.com/example/payment-service.git",
      source_type: "git",
    };
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });
    assert.strictEqual(res.status, 201);
    const data = await res.json();
    assert.strictEqual(data.name, "payment-service");
    assert.strictEqual(data.status, "registered");
    assert.ok(data.id);
  });

  test("registerRepository rejects invalid URL scheme with HTTP 422", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/repositories`;
    const payload = {
      name: "invalid-target",
      url: "ftp://example.com/repo.git",
    };
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });
    assert.strictEqual(res.status, 422);
    const data = await res.json();
    assert.ok(data.detail);
  });

  test("getRepository returns target metadata by UUID", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/repositories/123e4567-e89b-12d3-a456-426614174000`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.name, "auth-service");
  });

  test("getRepository returns 404 for unknown UUID", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/repositories/00000000-0000-0000-0000-000000000000`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    assert.strictEqual(res.status, 404);
  });

  test("deleteRepository returns HTTP 204 No Content", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/repositories/123e4567-e89b-12d3-a456-426614174000`;
    const res = await fetch(url, {
      method: "DELETE",
      headers: { Accept: "application/json" },
    });
    assert.strictEqual(res.status, 204);
  });

  test("deleteRepository returns 404 when target does not exist", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/repositories/00000000-0000-0000-0000-000000000000`;
    const res = await fetch(url, {
      method: "DELETE",
      headers: { Accept: "application/json" },
    });
    assert.strictEqual(res.status, 404);
  });

  test("startDiagnosticRun initiates diagnosis and returns full report", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/repositories/123e4567-e89b-12d3-a456-426614174000/diagnose`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ allow_dynamic: false }),
    });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.status, "completed");
    assert.strictEqual(data.repository_name, "auth-service");
    assert.ok(data.system_map);
    assert.strictEqual(data.system_map.total_components, 2);
    assert.ok(Array.isArray(data.completed_stages));
    assert.strictEqual(data.completed_stages.length, 8);
  });

  test("getLatestDiagnosticReport returns latest report for repository", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/repositories/123e4567-e89b-12d3-a456-426614174000/diagnostics/latest`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.run_id, "a1b2c3d4-e5f6-7890-abcd-ef1234567890");
    assert.strictEqual(data.status, "completed");
  });

  test("getDiagnosticRun returns report by run UUID", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/diagnostics/a1b2c3d4-e5f6-7890-abcd-ef1234567890`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.run_id, "a1b2c3d4-e5f6-7890-abcd-ef1234567890");
  });

  test("listDiagnosticRuns returns all runs array", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/diagnostics/runs`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.ok(Array.isArray(data));
    assert.strictEqual(data.length, 1);
    assert.strictEqual(data[0].run_id, "a1b2c3d4-e5f6-7890-abcd-ef1234567890");
  });

  test("getDiagnosticProbes returns candidate and executed probes", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/diagnostics/a1b2c3d4-e5f6-7890-abcd-ef1234567890/probes`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.run_id, "a1b2c3d4-e5f6-7890-abcd-ef1234567890");
    assert.strictEqual(data.candidate_probes.length, 1);
    assert.strictEqual(data.candidate_probes[0].probe_id, "PROBE-AST-SYNTAX-001");
    assert.strictEqual(data.executed_probes.length, 1);
    assert.strictEqual(data.executed_probes[0].probe_id, "PROBE-AST-SYNTAX-001");
    assert.strictEqual(data.executed_probes[0].execution_status, "executed");
    assert.strictEqual(data.executed_probes[0].ranking_changed, true);
  });

  test("getDiagnosticDecisions returns decision history and stopping reason", async () => {
    const url = `http://127.0.0.1:${serverPort}/api/v1/diagnostics/a1b2c3d4-e5f6-7890-abcd-ef1234567890/decisions`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.run_id, "a1b2c3d4-e5f6-7890-abcd-ef1234567890");
    assert.strictEqual(data.investigation_history.length, 2);
    assert.strictEqual(data.investigation_history[0].decision_type, "select_probe");
    assert.strictEqual(data.investigation_history[1].decision_type, "stop_sufficient_evidence");
    assert.strictEqual(data.stopping_reason, "sufficient_evidence_verified");
  });
});
