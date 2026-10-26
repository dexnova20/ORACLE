"""Generalization dataset and scenario specifications for ORACLE Implementation 017.

Provides 20 independently validated diagnostic scenarios covering Go, polyglot monorepos,
non-static runtime faults (database, API, contract, transform, config), multi-fault repositories,
evidence contradiction cases, and deliberate abstentions.
"""

from dataclasses import dataclass, field
import json
import os
import shutil
import sys
from typing import Any, Dict, List, Optional
import uuid

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from ml.taxonomy.fault_taxonomy import FaultCategory
from oracle.models.repository import Repository
from oracle.schemas.diagnostics import (
    DiagnosticEvidenceRecord,
    DiagnosticRunRequest,
    FaultHypothesis,
)


@dataclass
class GeneralizationScenario:
    """Specification of an empirical generalization test scenario."""

    scenario_id: str
    title: str
    ecosystem: str
    description: str
    dir_name: str
    expected_category: Optional[FaultCategory]
    is_healthy_control: bool = False
    is_abstention_case: bool = False
    is_multi_fault: bool = False
    symptom_description: Optional[str] = None
    runtime_traceback: Optional[str] = None
    files: Dict[str, str] = field(default_factory=dict)


GENERALIZATION_SCENARIOS: List[GeneralizationScenario] = [
    # 1-4: Go Scenarios
    GeneralizationScenario(
        scenario_id="GEN-001",
        title="Go HTTP Service (Clean Control)",
        ecosystem="go",
        description="Clean Go web server using net/http and declared gorilla/mux dependency.",
        dir_name="gen_001_go_clean",
        expected_category=None,
        is_healthy_control=True,
        files={
            "go.mod": "module example.com/clean\n\ngo 1.22.0\n\nrequire github.com/gorilla/mux v1.8.1\n",
            "main.go": """package main

import (
\t"fmt"
\t"net/http"
\t"github.com/gorilla/mux"
)

func main() {
\tr := mux.NewRouter()
\tr.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
\t\tfmt.Fprintf(w, "Healthy")
\t})
}
""",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-002",
        title="Go Service (Syntax Error)",
        ecosystem="go",
        description="Go server with unclosed brace syntax defect in handler.",
        dir_name="gen_002_go_syntax_error",
        expected_category=FaultCategory.RUNTIME_EXCEPTION,
        files={
            "go.mod": "module example.com/syntaxerr\n\ngo 1.22.0\n",
            "main.go": """package main

import "fmt"

func brokenHandler() {
\tfmt.Println("missing closing brace")
""",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-003",
        title="Go CLI (Undeclared External Dependency)",
        ecosystem="go",
        description="Go code imports external postgres driver 'github.com/lib/pq' missing from go.mod.",
        dir_name="gen_003_go_undeclared_dep",
        expected_category=FaultCategory.DEPENDENCY_IMPORT_FAILURE,
        files={
            "go.mod": "module example.com/cliapp\n\ngo 1.22.0\n",
            "main.go": """package main

import (
\t"database/sql"
\t_ "github.com/lib/pq"
)

func main() {
\tdb, _ := sql.Open("postgres", "postgres://localhost/test")
\t_ = db
}
""",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-004",
        title="Go Package (Unresolved Internal Module)",
        ecosystem="go",
        description="Go file imports an internal subpackage that does not exist in the repository.",
        dir_name="gen_004_go_unresolved_internal",
        expected_category=FaultCategory.DEPENDENCY_IMPORT_FAILURE,
        files={
            "go.mod": "module example.com/pkgapp\n\ngo 1.22.0\n",
            "main.go": """package main

import (
\t"example.com/pkgapp/missing/service"
)

func main() {
\tservice.Run()
}
""",
        },
    ),

    # 5-10: Non-Static Runtime / Telemetry Scenarios
    GeneralizationScenario(
        scenario_id="GEN-005",
        title="Database Socket Connection Refusal",
        ecosystem="python",
        description="Application fails at runtime because PostgreSQL socket on port 5432 is unreachable.",
        dir_name="gen_005_db_connection_refused",
        expected_category=FaultCategory.DATABASE_CONNECTIVITY_SCHEMA,
        runtime_traceback="""Traceback (most recent call last):
  File "app/main.py", line 18, in init_db
    conn = psycopg.connect("postgresql://user:pass@localhost:5432/testdb")
  File "psycopg/connection.py", line 112, in connect
    raise psycopg.OperationalError("connection to server at 'localhost', port 5432 failed: Connection refused")
psycopg.OperationalError: connection to server at 'localhost', port 5432 failed: Connection refused
""",
        files={
            "pyproject.toml": '[project]\nname = "db-app"\nversion = "0.1.0"\ndependencies = ["psycopg>=3.0"]\n',
            "app/main.py": "import psycopg\n\ndef init_db():\n    return psycopg.connect('postgresql://user:pass@localhost:5432/testdb')\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-006",
        title="Payment Gateway (API Connect Timeout)",
        ecosystem="python",
        description="Outbound HTTP client timeout communicating with upstream payment gateway.",
        dir_name="gen_006_api_connect_timeout",
        expected_category=FaultCategory.API_COMMUNICATION_FAILURE,
        runtime_traceback="""Traceback (most recent call last):
  File "app/payments.py", line 45, in charge
    res = httpx.post("https://api.payment-gateway.example/v1/charges", timeout=5.0)
httpx.ConnectTimeout: timed out while connecting to upstream payment gateway
""",
        files={
            "requirements.txt": "httpx>=0.27.0\n",
            "app/payments.py": "import httpx\n\ndef charge():\n    return httpx.post('https://api.payment-gateway.example/v1/charges')\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-007",
        title="User Registration (IO Contract Schema Mismatch)",
        ecosystem="python",
        description="Pydantic validation failure caused by missing required payload field 'email'.",
        dir_name="gen_007_contract_validation_error",
        expected_category=FaultCategory.IO_CONTRACT_VIOLATION,
        runtime_traceback="""Traceback (most recent call last):
  File "app/api.py", line 22, in create_user
    user = UserCreate(**payload)
pydantic.ValidationError: 1 validation error for UserCreate
email
  Field required [type=missing, input_value={'username': 'alice'}, input_type=dict]
""",
        files={
            "pyproject.toml": '[project]\nname = "user-api"\nversion = "1.0.0"\ndependencies = ["pydantic>=2.0"]\n',
            "app/api.py": "from pydantic import BaseModel\n\nclass UserCreate(BaseModel):\n    username: str\n    email: str\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-008",
        title="Data Processing (JSON Decode Error)",
        ecosystem="python",
        description="Pipeline crash parsing corrupt non-JSON binary data stream.",
        dir_name="gen_008_json_decode_error",
        expected_category=FaultCategory.DATA_VALIDATION_TRANSFORMATION,
        runtime_traceback="""Traceback (most recent call last):
  File "etl/parser.py", line 33, in parse_payload
    return json.loads(corrupt_stream)
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
""",
        files={
            "pyproject.toml": '[project]\nname = "etl-pipeline"\nversion = "0.1.0"\n',
            "etl/parser.py": "import json\n\ndef parse_payload(raw):\n    return json.loads(raw)\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-009",
        title="Authentication Service (Missing Environment Variable)",
        ecosystem="python",
        description="App bootstrap crash when mandatory JWT_SECRET_KEY is absent.",
        dir_name="gen_009_missing_env_key",
        expected_category=FaultCategory.CONFIG_MISSING_OR_INVALID,
        runtime_traceback="""Traceback (most recent call last):
  File "app/config.py", line 12, in <module>
    SECRET_KEY = os.environ['JWT_SECRET_KEY']
KeyError: 'JWT_SECRET_KEY'
""",
        files={
            ".env.example": "JWT_SECRET_KEY=replace_me\nPORT=8000\n",
            "app/config.py": "import os\nSECRET_KEY = os.environ['JWT_SECRET_KEY']\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-010",
        title="Go Worker (Runtime Panic)",
        ecosystem="go",
        description="Go background task crashes with slice index out of bounds panic.",
        dir_name="gen_010_go_panic",
        expected_category=FaultCategory.RUNTIME_EXCEPTION,
        runtime_traceback="""panic: runtime error: index out of range [10] with length 3
goroutine 1 [running]:
main.processBatch(0xc0000a6000, 0x3, 0x3)
\t/app/worker.go:28 +0x8a
main.main()
\t/app/worker.go:12 +0x24
""",
        files={
            "go.mod": "module example.com/worker\n\ngo 1.22.0\n",
            "worker.go": """package main

func processBatch(items []int) int {
\treturn items[10]
}

func main() {
\tprocessBatch([]int{1, 2, 3})
}
""",
        },
    ),

    # 11-16: Multi-Fault, Contradiction, and Ambiguous Scenarios
    GeneralizationScenario(
        scenario_id="GEN-011",
        title="Polyglot Monorepo (Simultaneous Python + TS Syntax Faults)",
        ecosystem="polyglot",
        description="Dual-language repository with independent syntax errors in backend and frontend.",
        dir_name="gen_011_polyglot_multifault",
        expected_category=FaultCategory.RUNTIME_EXCEPTION,
        is_multi_fault=True,
        files={
            "backend/main.py": "def broken():\n    return 42 +\n",
            "frontend/app.ts": "export function brokenUI() {\n    const x = (\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-012",
        title="Decoy Syntax Refuted vs Actual Config Error",
        ecosystem="python",
        description="App contains benign unexecuted scratch script, actual crash caused by missing DATABASE_URL.",
        dir_name="gen_012_decoy_syntax_refuted",
        expected_category=FaultCategory.CONFIG_MISSING_OR_INVALID,
        symptom_description="ConfigurationError: DATABASE_URL is not set in environment",
        runtime_traceback="""Traceback (most recent call last):
  File "app/server.py", line 15, in load_settings
    raise KeyError("DATABASE_URL")
KeyError: 'DATABASE_URL'
""",
        files={
            ".env.example": "DATABASE_URL=postgres://...\n",
            "app/server.py": "import os\nurl = os.environ['DATABASE_URL']\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-013",
        title="Gateway Service (Competing Hypotheses with Identical Signals)",
        ecosystem="python",
        description="Ambiguous network symptom: could be client timeout or server gateway 504.",
        dir_name="gen_013_competing_hypotheses",
        expected_category=FaultCategory.API_COMMUNICATION_FAILURE,
        symptom_description="HTTP 504 Gateway Timeout while proxying request to upstream service",
        files={
            "app/proxy.py": "def proxy():\n    pass\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-014",
        title="Circular Import Cycle",
        ecosystem="python",
        description="Two modules importing each other at top-level triggering AttributeError.",
        dir_name="gen_014_circular_import",
        expected_category=FaultCategory.DEPENDENCY_IMPORT_FAILURE,
        runtime_traceback="""Traceback (most recent call last):
  File "app/a.py", line 2, in <module>
    from app.b import b_func
  File "app/b.py", line 2, in <module>
    from app.a import a_func
ImportError: cannot import name 'a_func' from partially initialized module 'app.a'
""",
        files={
            "app/a.py": "from app.b import b_func\ndef a_func(): pass\n",
            "app/b.py": "from app.a import a_func\ndef b_func(): pass\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-015",
        title="Database Transaction Deadlock",
        ecosystem="python",
        description="Concurrent SQL transactions abort with DeadlockDetected exception.",
        dir_name="gen_015_db_deadlock",
        expected_category=FaultCategory.DATABASE_CONNECTIVITY_SCHEMA,
        runtime_traceback="""Traceback (most recent call last):
  File "app/repo.py", line 55, in transfer
    cursor.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
psycopg.errors.DeadlockDetected: deadlock detected
DETAIL: Process 12345 waits for ShareLock on transaction 67890.
""",
        files={
            "app/repo.py": "def transfer(): pass\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-016",
        title="Polyglot Clean Monorepo (Python + TS + Java + Go Clean Control)",
        ecosystem="polyglot",
        description="Four-language enterprise monorepo with 100% valid code and declared dependencies.",
        dir_name="gen_016_polyglot_clean",
        expected_category=None,
        is_healthy_control=True,
        files={
            "pyproject.toml": '[project]\nname = "py-svc"\nversion = "1.0.0"\n',
            "service.py": "def run():\n    return 'clean'\n",
            "package.json": '{"name": "ts-svc", "version": "1.0.0", "dependencies": {}}\n',
            "index.ts": "export const ok = true;\n",
            "pom.xml": '<project><modelVersion>4.0.0</modelVersion><groupId>com.app</groupId><artifactId>jvm-svc</artifactId><version>1.0</version></project>\n',
            "App.java": "public class App { public static void main(String[] args) {} }\n",
            "go.mod": "module example.com/go-svc\n\ngo 1.22.0\n",
            "main.go": "package main\nfunc main() {}\n",
        },
    ),

    # 17-20: Unseen Frameworks, OOD Abstention, and Monorepos
    GeneralizationScenario(
        scenario_id="GEN-017",
        title="Rust Service (Out-of-Distribution Explicit Abstention)",
        ecosystem="rust",
        description="Rust-only repository lacking Python/TS/Java/Go code. Engine must explicitly abstain.",
        dir_name="gen_017_rust_abstention",
        expected_category=FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE,
        is_abstention_case=True,
        files={
            "Cargo.toml": '[package]\nname = "rust-app"\nversion = "0.1.0"\nedition = "2021"\n',
            "src/main.rs": "fn main() {\n    println!(\"Hello, Rust!\");\n}\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-018",
        title="Configuration YAML Syntax Defect",
        ecosystem="config",
        description="Corrupt YAML configuration file with tab characters in indentation.",
        dir_name="gen_018_yaml_syntax_defect",
        expected_category=FaultCategory.CONFIG_MISSING_OR_INVALID,
        symptom_description="yaml.scanner.ScannerError: mapping values are not allowed here in config.yaml line 4",
        files={
            "config.yaml": "server:\n\tport: 8080\n  host: 0.0.0.0\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-019",
        title="Degraded External Service (Rate Limit 429)",
        ecosystem="python",
        description="External rate limit saturation returning HTTP 429 Too Many Requests.",
        dir_name="gen_019_rate_limit_429",
        expected_category=FaultCategory.API_COMMUNICATION_FAILURE,
        symptom_description="HTTP 429 Too Many Requests: Rate limit exceeded. Retry-After: 60",
        files={
            "client.py": "def fetch(): pass\n",
        },
    ),
    GeneralizationScenario(
        scenario_id="GEN-020",
        title="Modular Clean Architecture (Healthy Monorepo Control)",
        ecosystem="python",
        description="Multi-package Python architecture with proper absolute imports and zero defects.",
        dir_name="gen_020_modular_clean",
        expected_category=None,
        is_healthy_control=True,
        files={
            "pyproject.toml": '[project]\nname = "modular-app"\nversion = "2.0.0"\n',
            "core/__init__.py": "",
            "core/domain.py": "class Entity: pass\n",
            "api/__init__.py": "",
            "api/routes.py": "from core.domain import Entity\ndef get_entity(): return Entity()\n",
        },
    ),
]


def materialize_generalization_fixtures(base_dir: str) -> Dict[str, str]:
    """Materialize the 20 generalization scenarios as disk fixtures.

    Returns mapping of scenario_id -> directory absolute path.
    """
    os.makedirs(base_dir, exist_ok=True)
    paths: Dict[str, str] = {}

    for sc in GENERALIZATION_SCENARIOS:
        sc_dir = os.path.join(base_dir, sc.dir_name)
        os.makedirs(sc_dir, exist_ok=True)

        for rel_file, content in sc.files.items():
            full_file = os.path.join(sc_dir, rel_file.replace("/", os.sep))
            os.makedirs(os.path.dirname(full_file), exist_ok=True)
            with open(full_file, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)

        paths[sc.scenario_id] = sc_dir

    return paths
