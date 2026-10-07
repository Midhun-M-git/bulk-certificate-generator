#!/bin/bash
set -e

# Bulk Certificate Generator Startup Script
cd "$(dirname "$0")"

# Activate virtual environment if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Ensure storage directory exists
mkdir -p storage/certificates

# Run FastAPI app with Uvicorn
echo "Starting Bulk Certificate Generator on http://localhost:8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
