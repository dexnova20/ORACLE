#!/bin/sh
set -e

echo "[ORACLE] Initializing backend container services..."

# If database URL is configured and WAIT_FOR_DB is set (default true), wait for PostgreSQL readiness
if [ "${WAIT_FOR_DB:-true}" = "true" ] && [ -n "$DATABASE_URL" ]; then
    echo "[ORACLE] Checking database connectivity..."
    python -c '
import os, sys, time
from sqlalchemy import create_engine, text

url = os.getenv("DATABASE_URL")
timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "30"))
deadline = time.time() + timeout
connected = False

while time.time() < deadline:
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        connected = True
        print("[ORACLE] Database connection verified successfully.")
        break
    except Exception as exc:
        print(f"[ORACLE] Database not ready yet ({exc}). Retrying in 2s...")
        time.sleep(2)

if not connected:
    print("[ORACLE] Warning: Database connection timed out or database is unreachable.")
    if os.getenv("ENVIRONMENT") == "production":
        print("[ORACLE] Fatal: Production environment requires database connectivity.")
        sys.exit(1)
'
fi

# Run database migrations if enabled (default true)
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "[ORACLE] Applying database migrations via Alembic..."
    alembic upgrade head || {
        echo "[ORACLE] Migration failed or database not reachable in non-fatal mode."
        if [ "$ENVIRONMENT" = "production" ]; then
            echo "[ORACLE] Fatal: Production migration failure."
            exit 1
        fi
    }
fi

echo "[ORACLE] Starting application: $@"
exec "$@"
