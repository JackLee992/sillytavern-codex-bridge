---
name: sillytavern-codex-bridge
description: Install SillyTavern on Windows or macOS and expose Codex CLI through a local OpenAI-compatible bridge so SillyTavern can keep its normal chat UI while sending requests with a base URL and API key. Use when Codex needs to set up SillyTavern, generate or rotate a local bridge key, start or troubleshoot the bridge, or explain how to point SillyTavern at Codex without changing SillyTavern's interaction model.
---

# SillyTavern Codex Bridge

Use this skill to set up a local `SillyTavern -> bridge -> codex exec` path.

Keep the workflow narrow:

1. Detect the platform.
2. Use the platform install script to install or update SillyTavern and create the bridge env file.
3. Use the platform start script to run the bridge.
4. Point SillyTavern at `http://127.0.0.1:<port>/v1` with the generated API key.

## Quick Start

For Windows, use `scripts/install_sillytavern_windows.ps1`, then `scripts/start_bridge_windows.ps1`.

For macOS, use `scripts/install_sillytavern_macos.sh`, then `scripts/start_bridge_macos.sh`.

If the user only wants configuration help, read `references/sillytavern-setup.md`.

If the user wants bridge behavior or endpoint details, read `references/bridge-behavior.md`.

## Standard Workflow

### 1. Install or update SillyTavern

Run the platform script.

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_sillytavern_windows.ps1
```

macOS:

```bash
bash scripts/install_sillytavern_macos.sh
```

The install scripts:

- check for `git`, `node`, `npm`, `python`, and `codex`
- clone `SillyTavern` if missing
- run `npm install`
- create `~/.codex/sillytavern-codex-bridge.env`
- create a dedicated bridge workspace under `~/.codex/tmp/sillytavern-bridge-workspace`
- preconfigure `SillyTavern` to use `chat_completion_source = custom`
- set `custom_url` to the local bridge and `custom_model` to `codex-cli`
- write `api_key_custom` into `SillyTavern`'s secret store file
- enable `power_user.auto_connect` so the UI connects automatically after reload

### 2. Start the bridge

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_bridge_windows.ps1
```

macOS:

```bash
bash scripts/start_bridge_macos.sh
```

The bridge is implemented in `scripts/codex_openai_bridge.py`.

### 3. Configure SillyTavern

Set:

- API type: OpenAI compatible
- Base URL: `http://127.0.0.1:8787/v1` unless the env file uses another port
- API key: value from `SILLYTAVERN_CODEX_API_KEY`
- Model: `codex-cli` unless the env file overrides it

Keep SillyTavern's own UI and chat flow. Only the backend target changes.

## Operational Rules

- Prefer the dedicated bridge workspace instead of the user's project folders.
- Keep Codex execution sandboxed. The bridge uses `codex exec --sandbox read-only`.
- Treat the bridge key like a local secret. Rotate it by editing the env file or re-running the install script with a new key.
- If the user asks for custom host, port, model, or working directory, update the env file instead of patching the Python bridge unless behavior must change.
- If the bridge must be debugged, check `/health`, `/v1/models`, then `/v1/chat/completions`.

## Files

- `scripts/codex_openai_bridge.py`: local OpenAI-compatible API bridge
- `scripts/install_sillytavern_windows.ps1`: Windows install/bootstrap
- `scripts/install_sillytavern_macos.sh`: macOS install/bootstrap
- `scripts/start_bridge_windows.ps1`: Windows bridge launcher
- `scripts/start_bridge_macos.sh`: macOS bridge launcher
- `references/sillytavern-setup.md`: SillyTavern-side settings
- `references/bridge-behavior.md`: bridge request and response behavior
