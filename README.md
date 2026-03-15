# sillytavern-codex-bridge

Bridge `SillyTavern` to local `codex exec` through an OpenAI-compatible HTTP endpoint.

This project lets `SillyTavern` keep its normal UI while routing requests to a local `Codex` CLI bridge.

## What It Does

- installs or bootstraps `SillyTavern` on Windows or macOS
- starts a local OpenAI-compatible bridge
- configures `SillyTavern` to call that bridge as a `custom` chat-completions backend
- keeps `SillyTavern` interaction flow unchanged

## Repository Layout

- `SKILL.md`: Codex skill instructions
- `scripts/codex_openai_bridge.py`: local OpenAI-compatible bridge for `codex exec`
- `scripts/install_sillytavern_windows.ps1`: Windows bootstrap
- `scripts/install_sillytavern_macos.sh`: macOS bootstrap
- `scripts/start_bridge_windows.ps1`: Windows bridge launcher
- `scripts/start_bridge_macos.sh`: macOS bridge launcher
- `references/`: setup and behavior notes

## Quick Start

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_sillytavern_windows.ps1
powershell -ExecutionPolicy Bypass -File scripts/start_bridge_windows.ps1
```

### macOS

```bash
bash scripts/install_sillytavern_macos.sh
bash scripts/start_bridge_macos.sh
```

Then point `SillyTavern` to:

- Base URL: `http://127.0.0.1:8787/v1`
- API key: value from `~/.codex/sillytavern-codex-bridge.env`
- Model: `codex-cli`

## Verified Fixes

These fixes were added after real local testing on Windows:

- chat-completions settings must be restored through `settings.json -> oai_settings`
- `power_user.auto_connect` should be enabled for reliable UI reconnection
- inherited `HTTP_PROXY` and `HTTPS_PROXY` variables can break `codex exec`
- multilingual prompt delivery through stdin is unreliable with `codex.cmd` on Windows, so the bridge passes prompts as command arguments instead
- transcript formatting was tightened to reduce meta-task replies from `Codex`

## Current Limitation

This bridge is technically usable for assistant-style chat and workflow help.

It is not a reliable way to turn `Codex` into a strong long-form roleplay backend for `SillyTavern`.

Even with bridge-side fixes, `Codex` still behaves like a task-oriented agent more than a dedicated RP model. For immersive roleplay, use a chat model tuned for RP and keep this bridge for:

- setup
- writing assistance
- role card generation
- lorebook generation
- task-oriented chat inside the `SillyTavern` UI

## Related Repos

- `sillytavern-character-card`
- `sillytavern-practical-beautify`
