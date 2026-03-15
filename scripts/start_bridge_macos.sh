#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-$HOME/.codex/sillytavern-codex-bridge.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing bridge env file: $ENV_FILE" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/codex_openai_bridge.py" --env-file "$ENV_FILE"
