#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export DATA_DIR="$PWD/data"
export CLOAKBROWSER_CACHE_DIR="$PWD/cloakbrowser-cache"
export TMPDIR="$PWD/tmp"
mkdir -p "$DATA_DIR" "$CLOAKBROWSER_CACHE_DIR" "$TMPDIR"

source .venv/bin/activate
exec uvicorn backend.main:app --reload --port 8080
