#!/usr/bin/env bash
# ==============================================================================
# ORACLE v0.1 Cloud VM Automated Setup & Deployment Script
# Target Platforms: Ubuntu 22.04 LTS (Jammy) / Ubuntu 24.04 LTS (Noble)
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}  ORACLE v0.1: Automated Cloud VM Provisioning & Deployment            ${NC}"
echo -e "${BLUE}========================================================================${NC}"

# 1. Operating System Validation
if [ ! -f /etc/os-release ]; then
    echo -e "${RED}[ERROR] Unsupported operating system. Expected Ubuntu Linux.${NC}" >&2
    exit 1
fi

. /etc/os-release
if [ "$ID" != "ubuntu" ]; then
    echo -e "${RED}[ERROR] Detected $ID, but Ubuntu 22.04 or 24.04 LTS is required.${NC}" >&2
    exit 1
fi

echo -e "${GREEN}[OK] Verified Operating System:${NC} $PRETTY_NAME ($VERSION_CODENAME)"

# 2. Hardware Resource Inspection
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
FREE_DISK_GB=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')

echo -e "[INFO] Detected Hardware Resources:"
echo -e "       - System RAM: ${TOTAL_RAM_MB} MB"
echo -e "       - Free Disk:  ${FREE_DISK_GB} GB"

if [ "$TOTAL_RAM_MB" -lt 3800 ]; then
    echo -e "${YELLOW}[WARN] Available RAM (${TOTAL_RAM_MB} MB) is below recommended 4096 MB.${NC}"
fi

# If RAM < 6000 MB and no swap exists, create a 2GB swap file to prevent OOM during Next.js build
SWAP_TOTAL=$(free -m | awk '/^Swap:/{print $2}')
if [ "$SWAP_TOTAL" -eq 0 ] && [ "$TOTAL_RAM_MB" -lt 6000 ]; then
    echo -e "${YELLOW}[INFO] Creating a 2GB emergency swapfile to support container builds...${NC}"
    sudo fallocate -l 2G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo -e "${GREEN}[OK] 2GB Swap activated.${NC}"
fi

# 3. Prerequisites Installation
echo -e "\n${BLUE}--- [Step 1/5] Updating Apt Repositories and Installing Core Tools ---${NC}"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    ca-certificates \
    curl \
    gnupg \
    git \
    jq \
    ufw \
    openssl \
    python3 \
    python3-venv \
    python3-pip

# 4. Official Docker Engine and Compose Plugin Installation
echo -e "\n${BLUE}--- [Step 2/5] Configuring Official Docker Engine & Compose v2 ---${NC}"
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    sudo install -m 0755 -d /etc/apt/keyrings
    if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
    fi

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $VERSION_CODENAME stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin

    sudo systemctl enable --now docker
    sudo usermod -aG docker "$USER"
    echo -e "${GREEN}[OK] Docker Engine installed successfully.${NC}"
else
    echo -e "${GREEN}[OK] Docker and Docker Compose already installed.${NC}"
fi

docker --version
docker compose version

# 5. Host Firewall Configuration (UFW)
echo -e "\n${BLUE}--- [Step 3/5] Configuring Host Firewall (UFW) ---${NC}"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH Administration'
sudo ufw allow 3000/tcp comment 'ORACLE Web UI'
sudo ufw allow 8000/tcp comment 'ORACLE API'
# Ensure PostgreSQL is NOT opened externally
sudo ufw deny 5432/tcp comment 'Block External Postgres' || true
sudo ufw --force enable
echo -e "${GREEN}[OK] UFW firewall active. Ports 22, 3000, 8000 open; 5432 strictly blocked.${NC}"

# 6. Production Environment Configuration
echo -e "\n${BLUE}--- [Step 4/5] Preparing Production Environment Secrets ---${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_DIR="$REPO_ROOT/deploy"

cd "$REPO_ROOT"

if [ ! -f "$DEPLOY_DIR/.env" ]; then
    echo -e "[INFO] Generating deploy/.env from template..."
    cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"

    # Generate secure random DB password
    SECURE_PASS=$(openssl rand -hex 24)
    sed -i "s/replace_with_a_secure_random_production_password_2026/$SECURE_PASS/g" "$DEPLOY_DIR/.env"

    # Detect public or external IP
    PUBLIC_IP=$(curl -s --connect-timeout 3 ifconfig.me || hostname -I | awk '{print $1}')
    echo -e "[INFO] Detected Server IP: $PUBLIC_IP"

    # Configure host bindings and CORS
    sed -i "s|HOST_BIND_IP=.*|HOST_BIND_IP=0.0.0.0|g" "$DEPLOY_DIR/.env"
    sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://$PUBLIC_IP:8000|g" "$DEPLOY_DIR/.env"
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=[\"http://$PUBLIC_IP:3000\",\"http://localhost:3000\"]|g" "$DEPLOY_DIR/.env"

    echo -e "${GREEN}[OK] deploy/.env generated with cryptographic database credentials.${NC}"
else
    echo -e "${GREEN}[OK] deploy/.env already exists, preserving configuration.${NC}"
fi

# 7. Container Stack Build & Startup
echo -e "\n${BLUE}--- [Step 5/5] Building and Launching Docker Compose Stack ---${NC}"
sudo docker compose -f "$DEPLOY_DIR/docker-compose.yml" --env-file "$DEPLOY_DIR/.env" up -d --build

echo -e "\n[INFO] Waiting for services to attain HEALTHY state..."
MAX_WAIT=90
ELAPSED=0
BACKEND_OK=0
DB_OK=0

while [ "$ELAPSED" -lt "$MAX_WAIT" ]; do
    BACKEND_STATUS=$(sudo docker inspect --format='{{json .State.Health.Status}}' oracle-backend 2>/dev/null || echo '"unknown"')
    DB_STATUS=$(sudo docker inspect --format='{{json .State.Health.Status}}' oracle-db 2>/dev/null || echo '"unknown"')

    if [ "$BACKEND_STATUS" = '"healthy"' ] && [ "$DB_STATUS" = '"healthy"' ]; then
        echo -e "${GREEN}[OK] All services are healthy (${ELAPSED}s).${NC}"
        BACKEND_OK=1
        DB_OK=1
        break
    fi

    echo -e "       ... db: $DB_STATUS, backend: $BACKEND_STATUS (${ELAPSED}s elapsed)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ "$BACKEND_OK" -ne 1 ]; then
    echo -e "${RED}[ERROR] Services failed to reach healthy status within ${MAX_WAIT}s.${NC}"
    sudo docker compose -f "$DEPLOY_DIR/docker-compose.yml" ps
    sudo docker compose -f "$DEPLOY_DIR/docker-compose.yml" logs --tail 30
    exit 1
fi

# 8. Final Deployment Verification
echo -e "\n${BLUE}========================================================================${NC}"
echo -e "${GREEN}  ORACLE v0.1 STACK SUCCESSFULLY DEPLOYED                              ${NC}"
echo -e "${BLUE}========================================================================${NC}"
sudo docker compose -f "$DEPLOY_DIR/docker-compose.yml" ps

echo -e "\nChecking API Readiness Probe:"
curl -s http://localhost:8000/api/v1/status | jq . || curl -s http://localhost:8000/api/v1/status

echo -e "\n${GREEN}Access Points:${NC}"
echo -e "  - Frontend UI:  http://${PUBLIC_IP}:3000"
echo -e "  - Backend API:  http://${PUBLIC_IP}:8000"
echo -e "  - API Status:   http://${PUBLIC_IP}:8000/api/v1/status"
echo -e "  - API Docs:     http://${PUBLIC_IP}:8000/docs"
echo -e "  - PostgreSQL:   127.0.0.1:5432 (Localhost/internal only)"

echo -e "\n${BLUE}Next Verification Steps:${NC}"
echo -e "  1. Verify Durable Persistence:  python3 deploy/scripts/verify_persistence.py"
echo -e "  2. Verify Runtime Isolation:    bash deploy/scripts/verify_isolation.sh"
echo -e "  3. Verify E2E Scenarios:        python3 testing/demonstration/test_e2e_scenarios.py"

