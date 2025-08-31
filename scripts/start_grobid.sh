#!/usr/bin/env bash

# Simple helper to start a local GROBID service (Gradle or Docker).
#
# Usage:
#   scripts/start_grobid.sh /path/to/grobid
#   scripts/start_grobid.sh               # if GROBID_HOME is set
#
# It prefers a local Gradle run (recommended when you already cloned GROBID),
# falling back to Docker if available.

set -euo pipefail

G_HOME="${1:-${GROBID_HOME:-}}"
PORT="${GROBID_PORT:-8070}"

if [[ -n "$G_HOME" && -d "$G_HOME" ]]; then
  echo "[grobid] Using GROBID_HOME=$G_HOME"
  # Run via Gradle wrapper at repo root
  if [[ -x "$G_HOME/gradlew" ]]; then
    echo "[grobid] Starting via gradle wrapper from repo root..."
    (cd "$G_HOME" && ./gradlew ":grobid-service:run")
    exit $?
  fi
  # Or from grobid-service subfolder using parent wrapper
  if [[ -d "$G_HOME/grobid-service" && -x "$G_HOME/gradlew" ]]; then
    echo "[grobid] Starting via gradle wrapper from grobid-service..."
    (cd "$G_HOME/grobid-service" && ../gradlew run)
    exit $?
  fi
  # Or try system gradle if installed
  if command -v gradle >/dev/null 2>&1; then
    echo "[grobid] Starting via system gradle..."
    (cd "$G_HOME" && gradle :grobid-service:run)
    exit $?
  fi
  echo "[grobid] Could not find Gradle wrapper or system gradle at $G_HOME"
fi

echo "[grobid] Falling back to Docker (lfoppiano/grobid) on port $PORT..."
if ! command -v docker >/dev/null 2>&1; then
  echo "[grobid] Docker not found. Please install Docker or provide GROBID_HOME." >&2
  exit 1
fi
docker run -d --rm --name paperslicer-grobid -p "${PORT}:8070" lfoppiano/grobid:0.8.1
echo "[grobid] Started Docker container 'paperslicer-grobid' on http://localhost:${PORT}"
echo "[grobid] Health: curl http://localhost:${PORT}/api/isalive"

