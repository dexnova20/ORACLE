# ORACLE Deployment and Operational Runbook

## 1. Overview & Architecture

ORACLE is packaged into a hardened, three-tier containerized production architecture:

```
[ External User / Browser ]
           │
           │ HTTP (Port 3000)
           ▼
┌─────────────────────────────────┐
│     oracle-frontend             │  Next.js 16 Standalone Runner
│     (node:20-alpine, UID 1001)  │  Static & Client Rendered UI
└────────────────┬────────────────┘
                 │
                 │ HTTP (Port 8000 via oracle_external network)
                 ▼
┌─────────────────────────────────┐
│     oracle-backend              │  FastAPI Application +
│     (python:3.12-slim,UID 10001)│  Embedded Node.js (TS AST) +
│                                 │  Embedded OpenJDK 17 (Java AST)
└────────────────┬────────────────┘
                 │
                 │ PostgreSQL Protocol (Port 5432, oracle_internal network ONLY)
                 ▼
┌─────────────────────────────────┐
│     oracle-db                   │  PostgreSQL 16 Engine
│     (postgres:16-alpine)        │  Persistent Volume: oracle_pgdata
└─────────────────────────────────┘
```

### Key Security Invariants
1. **Network Segmentation**: The PostgreSQL database is attached exclusively to the private `oracle_internal` bridge network with `internal: true`. It is unreachable from the outside network.
2. **Unprivileged Execution**:
   - Backend runs as system user `oracle` (UID 10001, GID 10001).
   - Frontend runs as system user `nextjs` (UID 1001, GID 1001).
   - Database runs as standard unprivileged `postgres` user.
3. **Protected Docker Boundary**: The FastAPI backend container **never** mounts `/var/run/docker.sock`. Unrestricted daemon access from an internet-facing web service is strictly prohibited. Dynamic execution sandboxing is gated or performed via isolated workers.
4. **Configuration Hardening**: In `ENVIRONMENT=production`, ORACLE rejects default development database credentials, forbids `DEBUG=true`, and prohibits wildcard CORS (`*`).

---

## 2. Directory & Configuration Structure

All deployment assets reside in the `deploy/` subfolder:
```
deploy/
├── Dockerfile.backend      # Multi-runtime backend container definition
├── Dockerfile.frontend     # Multi-stage Next.js 16 standalone container
├── docker-compose.yml      # Service orchestration & internal networking
├── entrypoint-backend.sh   # DB readiness wait & automated Alembic migration runner
├── .env.example            # Environment configuration template
└── README.md               # Operational runbook (this document)
```

---

## 3. Quickstart Deployment

### Step 1: Prepare Environment File
Copy the deployment template and configure production secrets:
```bash
cp deploy/.env.example deploy/.env
# Edit deploy/.env and generate a strong, random database password:
# POSTGRES_PASSWORD=$(openssl rand -hex 24)
```

### Step 2: Build and Launch Services
```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
```

### Step 3: Verify Container Health
```bash
docker compose -f deploy/docker-compose.yml ps
```
All services should reach `healthy` status within 15–30 seconds.

---

## 4. Health & Status Probes

| Endpoint | Target | Purpose | Success Code |
| :--- | :--- | :--- | :--- |
| `GET /api/v1/health` | Backend | Liveness probe (Kubernetes / load balancer) | `200 OK` (`{"status":"healthy"}`) |
| `GET /api/v1/status` | Backend | Readiness probe (DB connectivity, AST parser availability) | `200 OK` (reports `persistence_mode`, `parsers`) |
| `GET /` | Frontend | Frontend web server availability | `200 OK` |

Example readiness probe output:
```json
{
  "app": {
    "status": "healthy",
    "app_name": "ORACLE",
    "version": "0.1.0",
    "environment": "production"
  },
  "database": {
    "connected": true,
    "message": "Database connection operational.",
    "driver": "postgresql+psycopg"
  },
  "persistence_mode": "durable_postgresql",
  "docker_isolation_available": false,
  "parsers": {
    "python": true,
    "typescript": true,
    "typescript_error": null,
    "java": true,
    "java_error": null
  },
  "supported_languages": ["python", "typescript", "javascript", "java"],
  "supported_ecosystems": ["python", "typescript", "javascript", "java"]
}
```

---

## 5. Database Migrations & Lifecycle

### Automated Migrations on Startup
The backend entrypoint (`deploy/entrypoint-backend.sh`) automatically performs:
1. Database connectivity polling (up to `DB_CONNECT_TIMEOUT=30` seconds).
2. Alembic migration execution: `alembic upgrade head`.

### Manual Migration Commands
To inspect current database revision:
```bash
docker compose -f deploy/docker-compose.yml exec backend alembic current
```

To manually apply pending migrations:
```bash
docker compose -f deploy/docker-compose.yml exec backend alembic upgrade head
```

To rollback the last migration:
```bash
docker compose -f deploy/docker-compose.yml exec backend alembic downgrade -1
```

---

## 6. Backup & Restore Procedures

### Automated Database Backup
Create a timestamped compressed SQL dump from the running PostgreSQL container:
```bash
BACKUP_FILE="backup_oracle_$(date +%Y%m%d_%H%M%S).sql.gz"
docker compose -f deploy/docker-compose.yml exec -T db pg_dump -U oracle_user oracle_db | gzip > "$BACKUP_FILE"
echo "Backup created: $BACKUP_FILE"
```

### Database Restore Procedure
1. Stop backend service to prevent write conflicts during restoration:
```bash
docker compose -f deploy/docker-compose.yml stop backend frontend
```

2. Restore database from compressed dump:
```bash
gunzip -c "$BACKUP_FILE" | docker compose -f deploy/docker-compose.yml exec -T db psql -U oracle_user -d oracle_db
```

3. Restart application services:
```bash
docker compose -f deploy/docker-compose.yml start backend frontend
```

4. Verify database connectivity and schema consistency:
```bash
curl -s http://localhost:8000/api/v1/status | jq .database
```

---

## 7. Disaster Recovery & Rollback

### Application Rollback
If a newly deployed image exhibits regressions:
1. Re-tag or revert to the previous container image version in `docker-compose.yml`.
2. Downgrade database schema if a schema migration was part of the release:
```bash
docker compose -f deploy/docker-compose.yml exec backend alembic downgrade <previous_revision_id>
```
3. Restart containers with previous image:
```bash
docker compose -f deploy/docker-compose.yml up -d
```

### Complete Environment Reset (Disaster Recovery)
> [!CAUTION]
> This destroys all persistent database records. Ensure a backup exists before running.
```bash
docker compose -f deploy/docker-compose.yml down -v
docker compose -f deploy/docker-compose.yml up -d --build
```

---

## 8. Environmental Verification & Known Status

In accordance with ORACLE's engineering standards, environmental status is transparently reported:
- **Development Workstation Environment**: Windows 11 host without Docker daemon or native PostgreSQL CLI installed.
- **Container Build & Composition**: Validated statically and structurally via syntax linters, schema validators, and mocked execution tests.
- **Offline & Mocked Lifecycle**: Verified in automated Python test suite (`testing/backend/test_deployment_config.py`).
- **Live Container Execution**: Awaiting target production host with active Docker Engine 24+ and Compose v2. Live execution is marked unverified on the Windows development workstation.
