#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/SillyTavern}"
BRIDGE_ENV="${BRIDGE_ENV:-$HOME/.codex/sillytavern-codex-bridge.env}"
BRIDGE_WORKSPACE="${BRIDGE_WORKSPACE:-$HOME/.codex/tmp/sillytavern-bridge-workspace}"
BRIDGE_PORT="${BRIDGE_PORT:-8787}"
API_KEY="${API_KEY:-}"

assert_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

assert_command git
assert_command node
assert_command npm
assert_command python3
assert_command codex

if [ ! -d "$INSTALL_DIR" ]; then
  git clone https://github.com/SillyTavern/SillyTavern.git "$INSTALL_DIR"
fi

npm install --prefix "$INSTALL_DIR"

mkdir -p "$BRIDGE_WORKSPACE"
mkdir -p "$(dirname "$BRIDGE_ENV")"

if [ -z "$API_KEY" ]; then
  API_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
)"
fi

cat >"$BRIDGE_ENV" <<EOF
SILLYTAVERN_CODEX_HOST=127.0.0.1
SILLYTAVERN_CODEX_PORT=$BRIDGE_PORT
SILLYTAVERN_CODEX_API_KEY=$API_KEY
SILLYTAVERN_CODEX_MODEL_ID=codex-cli
SILLYTAVERN_CODEX_BIN=codex
SILLYTAVERN_CODEX_CWD=$BRIDGE_WORKSPACE
SILLYTAVERN_CODEX_TIMEOUT=600
EOF

SETTINGS_PATH="$INSTALL_DIR/data/default-user/settings.json"
PRESET_PATH="$INSTALL_DIR/data/default-user/OpenAI Settings/Default.json"
SECRETS_PATH="$INSTALL_DIR/data/default-user/secrets.json"

if [ -f "$SETTINGS_PATH" ]; then
  python3 - "$SETTINGS_PATH" "$BRIDGE_PORT" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
port = sys.argv[2]
data = json.loads(path.read_text(encoding="utf-8"))
data["main_api"] = "openai"
data.setdefault("power_user", {})["auto_connect"] = True
oai = data.setdefault("oai_settings", {})
oai["chat_completion_source"] = "custom"
oai["custom_model"] = "codex-cli"
oai["custom_url"] = f"http://127.0.0.1:{port}/v1"
path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
PY
fi

if [ -f "$PRESET_PATH" ]; then
  python3 - "$PRESET_PATH" "$BRIDGE_PORT" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
port = sys.argv[2]
data = json.loads(path.read_text(encoding="utf-8"))
data["chat_completion_source"] = "custom"
data["custom_model"] = "codex-cli"
data["custom_url"] = f"http://127.0.0.1:{port}/v1"
path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
PY
fi

python3 - "$SECRETS_PATH" "$API_KEY" <<'PY'
import json
import sys
import uuid
from pathlib import Path

path = Path(sys.argv[1])
api_key = sys.argv[2]
payload = {
    "api_key_custom": [
        {
            "id": str(uuid.uuid4()),
            "value": api_key,
            "label": "Codex Bridge",
            "active": True,
        }
    ]
}
path.write_text(json.dumps(payload, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
PY

echo "SillyTavern is ready at $INSTALL_DIR"
echo "Bridge env file: $BRIDGE_ENV"
echo "API key: $API_KEY"
echo "Base URL: http://127.0.0.1:$BRIDGE_PORT/v1"
echo
echo "Next:"
echo "1. bash \"$SCRIPT_DIR/start_bridge_macos.sh\""
echo "2. npm start --prefix \"$INSTALL_DIR\""
