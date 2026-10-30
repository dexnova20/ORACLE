# ORACLE v0.1 Cloud VM Deployment & Operational Guide

## 1. Overview and Architecture

This guide specifies the architecture, infrastructure requirements, automated provisioning, persistence verification, and isolation testing for deploying ORACLE v0.1 on a dedicated Linux cloud virtual machine.

### Topology

```
[ Internet / Deployer Workstation ]
               │
               │ HTTPS (Port 443) / HTTP (Port 3000)
               ▼
┌────────────────────────────────────────────────────────┐
│ Cloud VM (Ubuntu 22.04 / 24.04 LTS)                    │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ UFW Host Firewall                                │  │
│  │ (Allow: 22/SSH, 3000/UI, 8000/API; Deny: 5432)   │  │
│  └───────────┬──────────────────────────┬───────────┘  │
│              │                          │              │
│              ▼                          ▼              │
│   ┌────────────────────┐     ┌─────────────────────┐   │
│   │  oracle-frontend   │     │   oracle-backend    │   │
│   │  (Next.js 16)      │────▶│   (FastAPI Engine)  │   │
│   │  Port 3000         │HTTP │   Port 8000         │   │
│   └────────────────────┘     └──────────┬──────────┘   │
│                                         │              │
│                      oracle_internal    │ (SQLAlchemy) │
│                      Bridge Network     ▼              │
│                              ┌─────────────────────┐   │
│                              │      oracle-db      │   │
│                              │  (PostgreSQL 16)    │   │
│                              │  Port 5432 (Internal│   │
│                              └──────────┬──────────┘   │
│                                         │              │
│                                         ▼              │
│                              ┌─────────────────────┐   │
│                              │ Named Docker Volume │   │
│                              │    oracle_pgdata    │   │
│                              └─────────────────────┘   │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Dynamic Execution Sandboxing (Docker Engine)     │  │
│  │ Strict runtime isolation:                        │  │
│  │ --read-only, --cap-drop ALL, --network none,     │  │
│  │ --security-opt no-new-privileges, -m 256m        │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### Security Invariants
1. **Network Segregation**: The PostgreSQL database container is attached to `oracle_internal` (`internal: true`). The database port 5432 is bound strictly to `127.0.0.1:5432` on the host for maintenance; it is **never** exposed to the public internet (`0.0.0.0/0`).
2. **Unprivileged Container Execution**:
   - Backend runs as system user `oracle` (UID 10001, GID 10001).
   - Frontend runs as system user `nextjs` (UID 1001, GID 1001).
   - Database runs as standard `postgres` (UID 70).
3. **Protected Docker Boundary**: The backend container **never** mounts `/var/run/docker.sock`. Untrusted repository code is strictly isolated inside hardened, ephemeral containers when dynamic execution is invoked.
4. **Production Hardening**: In `ENVIRONMENT=production`, default development database credentials and `DEBUG=true` are strictly rejected at startup.

---

## 2. Infrastructure Sizing and Cost Analysis

### Sizing Specifications

| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **Operating System** | Ubuntu 22.04 LTS (x86_64) | Ubuntu 24.04 LTS (x86_64) |
| **vCPU** | 2 vCPUs | 2 to 4 vCPUs |
| **System Memory** | 4 GB RAM | 8 GB RAM |
| **Storage** | 30 GB SSD | 50 GB SSD (NVMe / gp3) |
| **Virtualization** | Hardware virtualization enabled | Hardware virtualization enabled |
| **Network** | Static public IPv4, 1 Gbps egress | Static public IPv4, 1 Gbps egress |

### Memory Budget Breakdown

- **Ubuntu OS + System Daemons + Docker Engine**: ~500 MB
- **PostgreSQL 16 Engine (`oracle-db`)**: ~256 MB (configurable `shared_buffers`)
- **FastAPI Backend + AST Analyzers (`oracle-backend`)**: ~512 MB to 1024 MB
- **Next.js 16 Standalone Runner (`oracle-frontend`)**: ~256 MB to 512 MB
- **Next.js Build Peak (during `docker compose build`)**: ~1.5 GB to 2.0 GB
- **Dynamic Sandbox Worker (ephemeral container)**: ~256 MB

> [!NOTE]
> A 4 GB VM can run the pre-built containers comfortably. However, 8 GB RAM is strongly recommended if building images directly on the VM to ensure Next.js standalone webpack compilation succeeds without triggering OOM-killer. Alternatively, configure a 2 GB swapfile if using a 4 GB VM.

### Cloud Provider Instance Comparison

| Provider | Recommended Instance | vCPU | RAM | Storage | Est. Monthly Cost (On-Demand) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AWS EC2** | `t3.large` | 2 | 8 GB | 40 GB gp3 | ~$60.74 / month (~$0.0832/hr) |
| **AWS EC2 (Minimal)**| `t3.medium` | 2 | 4 GB | 30 GB gp3 | ~$30.37 / month (~$0.0416/hr) |
| **Google Cloud (GCP)** | `e2-standard-2` | 2 | 8 GB | 40 GB Balanced PD | ~$48.91 / month (~$0.0670/hr) |
| **Google Cloud (Minimal)** | `e2-medium` | 2 | 4 GB | 30 GB Balanced PD | ~$24.46 / month (~$0.0335/hr) |
| **Microsoft Azure** | `Standard_B2ms` | 2 | 8 GB | 32 GB Premium SSD | ~$60.59 / month (~$0.0830/hr) |
| **DigitalOcean** | `Basic Droplet` | 2 | 4 GB | 50 GB NVMe SSD | $24.00 / month ($0.036/hr) |
| **DigitalOcean** | `Basic Droplet` | 4 | 8 GB | 160 GB NVMe SSD | $48.00 / month ($0.071/hr) |

> [!TIP]
> For temporary testing and verification, use Spot Instances (AWS) or Preemptible VMs (GCP) to reduce costs by 60%–80% (~$0.015 to $0.025/hr). Always shut down or terminate the VM when testing is complete.

---

## 3. Firewall and Network Security Rules

Before launching, configure the cloud provider's firewall / Security Group:

| Direction | Port / Protocol | Source | Purpose | Action |
| :--- | :--- | :--- | :--- | :--- |
| **Inbound** | `22 / TCP` (SSH) | `YOUR_CLIENT_IP/32` | Secure administrative shell access | **ALLOW** |
| **Inbound** | `3000 / TCP` (HTTP) | `YOUR_CLIENT_IP/32` or `0.0.0.0/0` | ORACLE Web UI | **ALLOW** |
| **Inbound** | `8000 / TCP` (HTTP) | `YOUR_CLIENT_IP/32` or `0.0.0.0/0` | ORACLE REST API | **ALLOW** |
| **Inbound** | `80 / TCP` (HTTP) | `0.0.0.0/0` | Optional reverse proxy / ACME challenge | ALLOW (if Nginx used) |
| **Inbound** | `443 / TCP` (HTTPS) | `0.0.0.0/0` | Optional TLS reverse proxy | ALLOW (if Nginx used) |
| **Inbound** | `5432 / TCP` (Postgres)| `0.0.0.0/0` | PostgreSQL Database Engine | **STRICTLY DENY / BLOCK** |
| **Outbound**| `All Traffic` | `0.0.0.0/0` | Package downloads, Docker Hub, updates | **ALLOW** |

> [!CAUTION]
> Never open port 5432 to `0.0.0.0/0`. The database is intended solely for internal container-to-container traffic over `oracle_internal`.

---

## 4. Automated Cloud VM Deployment

We provide an automated setup script that configures Docker, firewall rules, environment secrets, and launches the entire stack.

### One-Command Setup

On the fresh Ubuntu cloud VM, execute:

```bash
# Clone the repository
git clone https://github.com/your-org/ORACLE.git /opt/oracle
cd /opt/oracle

# Run the automated deployment script
bash deploy/scripts/setup_ubuntu_vm.sh
```

### What the Setup Script Performs:
1. Validates that the OS is Ubuntu 22.04 or 24.04 LTS.
2. Checks available RAM (minimum 4 GB; configures a 2 GB swapfile if RAM < 6 GB).
3. Installs prerequisites: `ca-certificates`, `curl`, `gnupg`, `git`, `jq`, `ufw`, `python3-venv`.
4. Installs official Docker Engine and Docker Compose v2 from Docker's official apt repository.
5. Adds current user to the `docker` group.
6. Configures UFW firewall rules (allows 22, 3000, 8000; blocks 5432).
7. Generates a secure, cryptographically random database password via `openssl rand -hex 24` and creates `deploy/.env`.
8. Builds and launches all services: `docker compose -f deploy/docker-compose.yml up -d --build`.
9. Polls health endpoints (`/api/v1/health` and `/api/v1/status`) until services report healthy.

---

## 5. Manual Step-by-Step Deployment Protocol

If running in a restricted or air-gapped environment without the setup script:

### Step 5.1: Install Docker Engine & Compose v2
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg ufw jq

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo usermod -aG docker $USER
```

### Step 5.2: Configure Firewall
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 3000/tcp comment 'ORACLE Frontend'
sudo ufw allow 8000/tcp comment 'ORACLE Backend API'
sudo ufw enable
```

### Step 5.3: Configure Production Environment
```bash
cp deploy/.env.example deploy/.env

# Generate secure password
DB_PASS=$(openssl rand -hex 24)
sed -i "s/replace_with_a_secure_random_production_password_2026/$DB_PASS/g" deploy/.env

# Detect VM public IP or set domain
VM_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
sed -i "s|HOST_BIND_IP=127.0.0.1|HOST_BIND_IP=0.0.0.0|g" deploy/.env
sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=[\"http://$VM_IP:3000\",\"http://localhost:3000\"]|g" deploy/.env
sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://$VM_IP:8000|g" deploy/.env
```

### Step 5.4: Build and Start Services
```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
```

### Step 5.5: Check Running Services
```bash
docker compose -f deploy/docker-compose.yml ps
```
Expected output:
```
NAME              IMAGE                  COMMAND                  SERVICE    STATUS
oracle-backend    oracle-backend:0.1.0   "/usr/local/bin/entr…"   backend    Up (healthy)
oracle-db         postgres:16-alpine     "docker-entrypoint.s…"   db         Up (healthy)
oracle-frontend   oracle-frontend:0.1.0  "node server.js"         frontend   Up (healthy)
```

---

## 6. Verification Protocols

### Protocol A: Health & Status Probes
```bash
# Liveness
curl -s http://localhost:8000/api/v1/health | jq .

# System Readiness and Persistence Mode
curl -s http://localhost:8000/api/v1/status | jq .
```
Verify that:
- `persistence_mode` is `"durable_postgresql"`.
- `database.connected` is `true`.
- `parsers.python`, `parsers.typescript`, `parsers.java` are operational.

### Protocol B: Durable Persistence Lifecycle Verification
Run the automated 11-step persistence verification suite:
```bash
python3 deploy/scripts/verify_persistence.py --backend-url http://localhost:8000
```
This script validates:
1. Initial persistence mode (`durable_postgresql`).
2. Current Alembic migration status (`002_create_diagnostic_runs`).
3. Repository registration and diagnostic run creation.
4. Record persistence across backend container restart (`docker compose restart backend`).
5. Record persistence across PostgreSQL container restart (`docker compose restart db`).
6. Record persistence across complete stack shutdown and recreation (`docker compose down` then `up -d`).
7. Idempotent Alembic migration execution on restart.

### Protocol C: Runtime Dynamic Execution Isolation Verification
Run the automated container isolation verification suite:
```bash
bash deploy/scripts/verify_isolation.sh
```
This script validates:
1. Docker daemon preflight check reports `is_available: true`.
2. Root filesystem read-only enforcement (`--read-only`).
3. Source workspace read-only mount enforcement (`-v :ro`).
4. Network disablement (`--network none`).
5. Capability dropping (`--cap-drop ALL`).
6. Privilege escalation prevention (`--security-opt no-new-privileges`).
7. Resource limits (memory, CPU, PID limit).
8. Absence of host Docker socket exposure.

### Protocol D: Full End-to-End Diagnostic Scenarios
Execute all 6 canonical diagnostic scenarios against the live deployed stack:
```bash
python3 testing/demonstration/test_e2e_scenarios.py --backend-url http://localhost:8000
```
All 6 scenarios must return `PASS`:
- Scenario 1: Healthy Input (zero false alarms).
- Scenario 2: Known Static-Analysis Fault (syntax defect detected).
- Scenario 3: Runtime Telemetry Fault (secret redacted 100%, DB error diagnosed).
- Scenario 4: Multiple Interacting Faults (multiple hypotheses and evidence).
- Scenario 5: Ambiguous Evidence (uncertainty preserved).
- Scenario 6: Unsupported / Blocked Input (Rust abstention, unapproved profile rejected).

---

## 7. Cloud VM Teardown and Cleanup

To stop and remove containers:
```bash
# Normal stop (preserves database records in named volume oracle_pgdata)
docker compose -f deploy/docker-compose.yml down

# Complete teardown including volumes (DESTRUCTIVE: wipes all database records)
docker compose -f deploy/docker-compose.yml down -v
```

To release cloud resources:
- Terminate or stop the cloud VM via your cloud provider console or CLI (`aws ec2 terminate-instances` / `gcloud compute instances delete`).
- Release any associated Elastic IPs / Static IPs.

