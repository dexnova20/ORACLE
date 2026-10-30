#!/usr/bin/env bash
# ==============================================================================
# ORACLE v0.1 Cloud VM Teardown and Resource Release Script
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_DIR="$REPO_ROOT/deploy"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}  ORACLE v0.1: Cloud VM Teardown                                       ${NC}"
echo -e "${BLUE}========================================================================${NC}"

WIPE_DATA=false
if [[ "${1:-}" == "--wipe-data" ]] || [[ "${1:-}" == "-v" ]]; then
    WIPE_DATA=true
fi

if [ "$WIPE_DATA" = true ]; then
    echo -e "${RED}[WARNING] --wipe-data flag provided. All persistent PostgreSQL records will be erased!${NC}"
    read -p "Are you sure you want to proceed with permanent data deletion? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborting teardown."
        exit 0
    fi
    echo -e "\nStopping services and deleting named volumes..."
    docker compose -f "$DEPLOY_DIR/docker-compose.yml" down -v
    echo -e "${GREEN}[OK] Stack and data volumes destroyed.${NC}"
else
    echo -e "\nStopping services while preserving database volume 'oracle_pgdata'..."
    docker compose -f "$DEPLOY_DIR/docker-compose.yml" down
    echo -e "${GREEN}[OK] Stack stopped. Persistent data preserved in named volume 'oracle_pgdata'.${NC}"
fi

echo -e "\n${YELLOW}Cloud Infrastructure Notice:${NC}"
echo -e "Remember to stop or terminate your Cloud VM instance via your cloud console"
echo -e "(AWS EC2, GCP Compute Engine, Azure Portal, or DigitalOcean) to stop incurring billing charges."

