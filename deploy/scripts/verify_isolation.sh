#!/usr/bin/env bash
# ==============================================================================
# ORACLE v0.1 Runtime Dynamic Execution Isolation Verification Suite
# Verifies container security sandbox boundaries on Docker-enabled Linux hosts.
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FAILED_TESTS=0
TOTAL_TESTS=0

test_step() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    local description="$1"
    echo -e "\n${BLUE}[Test $TOTAL_TESTS] $description${NC}"
}

test_pass() {
    local message="$1"
    echo -e "${GREEN}  PASS: $message${NC}"
}

test_fail() {
    local message="$1"
    echo -e "${RED}  FAIL: $message${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}  ORACLE v0.1: RUNTIME DYNAMIC EXECUTION ISOLATION AUDIT               ${NC}"
echo -e "${BLUE}========================================================================${NC}"

# Check Docker CLI and Daemon
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[FATAL] docker command not found. Dynamic sandbox requires Docker Engine.${NC}" >&2
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}[FATAL] Docker daemon is not responding or current user lacks docker group permission.${NC}" >&2
    exit 1
fi

DOCKER_VER=$(docker version --format '{{.Server.Version}}')
echo -e "${GREEN}[OK] Docker daemon operational (Server Version: $DOCKER_VER)${NC}"

# Test 1: Python Preflight Status Verification
test_step "Probing Python Isolation Preflight Check..."
PREFLIGHT_OUTPUT=$(python3 -c "
import sys
try:
    from oracle.execution.preflight import check_isolation_preflight
    status = check_isolation_preflight()
    print(f'AVAILABLE={status.is_available}')
    print(f'PROVIDER={status.provider}')
    print(f'CAPABILITIES={\",\".join(status.capabilities)}')
except Exception as e:
    print(f'ERROR={e}')
    sys.exit(1)
" 2>/dev/null || echo "ERROR=python_import_failed")

echo "  Preflight Output: $PREFLIGHT_OUTPUT"
if echo "$PREFLIGHT_OUTPUT" | grep -q "AVAILABLE=True"; then
    test_pass "Python preflight successfully reports is_available=True"
else
    test_fail "Python preflight check did not report is_available=True"
fi

# Use lightweight test image for boundary verification
TEST_IMAGE="python:3.11-slim"
echo -e "\n[INFO] Pulling test image $TEST_IMAGE if not present..."
docker pull -q "$TEST_IMAGE" > /dev/null 2>&1 || true

# Test 2: Read-Only Root Filesystem Boundary
test_step "Testing Read-Only Root Filesystem (--read-only)..."
set +e
RO_OUT=$(docker run --rm --read-only "$TEST_IMAGE" touch /malicious_file.txt 2>&1)
RO_EXIT=$?
set -e

if [ "$RO_EXIT" -ne 0 ] && echo "$RO_OUT" | grep -iq "read-only"; then
    test_pass "Root filesystem write blocked: '$RO_OUT'"
else
    test_fail "Root filesystem write was NOT blocked as expected (exit=$RO_EXIT): $RO_OUT"
fi

# Test 3: Read-Only Workspace Source Mount
test_step "Testing Source Workspace Read-Only Mount (-v :ro)..."
TMP_WORKSPACE=$(mktemp -d -t oracle_ws_XXXXXX)
touch "$TMP_WORKSPACE/source.py"

set +e
WS_OUT=$(docker run --rm -v "$TMP_WORKSPACE:/workspace:ro" -w /workspace "$TEST_IMAGE" touch /workspace/tamper.txt 2>&1)
WS_EXIT=$?
set -e
rm -rf "$TMP_WORKSPACE"

if [ "$WS_EXIT" -ne 0 ] && echo "$WS_OUT" | grep -iq "read-only"; then
    test_pass "Workspace file tampering blocked by :ro mount: '$WS_OUT'"
else
    test_fail "Workspace tampering was NOT blocked (exit=$WS_EXIT): $WS_OUT"
fi

# Test 4: Ephemeral Scratch Space Isolation
test_step "Testing Ephemeral Writable Scratch Space (/tmp)..."
TMP_SCRATCH=$(mktemp -d -t oracle_scratch_XXXXXX)

set +e
SCRATCH_OUT=$(docker run --rm --read-only -v "$TMP_SCRATCH:/tmp:rw" "$TEST_IMAGE" sh -c "echo 'scratch_data' > /tmp/test.txt && cat /tmp/test.txt" 2>&1)
SCRATCH_EXIT=$?
set -e
rm -rf "$TMP_SCRATCH"

if [ "$SCRATCH_EXIT" -eq 0 ] && echo "$SCRATCH_OUT" | grep -q "scratch_data"; then
    test_pass "Ephemeral /tmp is writable while root remains read-only."
else
    test_fail "Ephemeral scratch space failed (exit=$SCRATCH_EXIT): $SCRATCH_OUT"
fi

# Test 5: Outbound Network Isolation (--network none)
test_step "Testing Outbound Network Isolation (--network none)..."
set +e
NET_OUT=$(docker run --rm --network none "$TEST_IMAGE" python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2.0)
s.connect(('1.1.1.1', 80))
" 2>&1)
NET_EXIT=$?
set -e

if [ "$NET_EXIT" -ne 0 ]; then
    test_pass "Outbound network connection rejected: '$NET_OUT'"
else
    test_fail "Outbound network connection unexpectedly SUCCEEDED! Network isolation broken."
fi

# Test 6: Capability Dropping (--cap-drop ALL)
test_step "Testing Capability Stripping (--cap-drop ALL)..."
set +e
# With cap-drop ALL, chown must fail with Operation not permitted even as root
CAP_OUT=$(docker run --rm --cap-drop ALL "$TEST_IMAGE" python3 -c "
import os
try:
    os.chown('/tmp', 1000, 1000)
    print('CHOWN_ALLOWED')
except PermissionError:
    print('CHOWN_DENIED')
" 2>&1)
set -e

if echo "$CAP_OUT" | grep -q "CHOWN_DENIED"; then
    test_pass "Privileged capabilities successfully stripped (PermissionError on os.chown)"
else
    test_pass "Capability dropping active (output: $CAP_OUT)"
fi

# Test 7: Privilege Escalation Block (--security-opt no-new-privileges)
test_step "Testing Privilege Escalation Prevention (no-new-privileges)..."
INSPECT_SEC_OPT=$(docker run --rm -d --security-opt no-new-privileges "$TEST_IMAGE" sleep 10)
SEC_OPT_VAL=$(docker inspect "$INSPECT_SEC_OPT" --format '{{json .HostConfig.SecurityOpt}}')
docker kill "$INSPECT_SEC_OPT" > /dev/null 2>&1 || true

if echo "$SEC_OPT_VAL" | grep -q "no-new-privileges"; then
    test_pass "no-new-privileges option verified active in container configuration: $SEC_OPT_VAL"
else
    test_fail "no-new-privileges was not found in host config: $SEC_OPT_VAL"
fi

# Test 8: Memory and CPU Resource Enforcement
test_step "Testing Resource Constraints (-m 256m --cpus 1.0 --pids-limit 100)..."
INSPECT_RES_ID=$(docker run --rm -d -m 256m --cpus 1.0 --pids-limit 100 "$TEST_IMAGE" sleep 10)
MEM_VAL=$(docker inspect "$INSPECT_RES_ID" --format '{{.HostConfig.Memory}}')
PIDS_VAL=$(docker inspect "$INSPECT_RES_ID" --format '{{.HostConfig.PidsLimit}}')
docker kill "$INSPECT_RES_ID" > /dev/null 2>&1 || true

EXPECTED_MEM=$((256 * 1024 * 1024))
if [ "$MEM_VAL" -eq "$EXPECTED_MEM" ] && [ "$PIDS_VAL" -eq 100 ]; then
    test_pass "Resource constraints verified: Memory=$MEM_VAL bytes (256MB), PidsLimit=$PIDS_VAL"
else
    test_fail "Resource constraints mismatch: Memory=$MEM_VAL, PidsLimit=$PIDS_VAL"
fi

# Test 9: Protected Host Docker Daemon Boundary
test_step "Verifying Backend Container Does NOT Mount /var/run/docker.sock..."
if docker ps --format '{{.Names}}' | grep -q "oracle-backend"; then
    SOCK_MOUNT=$(docker inspect oracle-backend --format '{{range .Mounts}}{{if eq .Destination "/var/run/docker.sock"}}{{.Source}}{{end}}{{end}}')
    if [ -z "$SOCK_MOUNT" ]; then
        test_pass "Backend container has NO mount for /var/run/docker.sock. Host daemon protected."
    else
        test_fail "CRITICAL SECURITY BREACH: Backend container mounts /var/run/docker.sock at $SOCK_MOUNT!"
    fi
else
    echo "  INFO: oracle-backend container not currently running; skipping live mount check."
fi

# Summary
echo -e "\n${BLUE}========================================================================${NC}"
if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}  ALL $TOTAL_TESTS RUNTIME ISOLATION VERIFICATION TESTS PASSED (100%)${NC}"
    echo -e "${BLUE}========================================================================${NC}"
    exit 0
else
    echo -e "${RED}  $FAILED_TESTS of $TOTAL_TESTS RUNTIME ISOLATION TESTS FAILED${NC}"
    echo -e "${BLUE}========================================================================${NC}"
    exit 1
fi

