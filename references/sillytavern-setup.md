# SillyTavern setup

## Target

Use the bridge as an OpenAI-compatible endpoint so SillyTavern keeps its existing UI and message flow.

## Required SillyTavern values

- Base URL: `http://127.0.0.1:8787/v1`
- API key: the value from `~/.codex/sillytavern-codex-bridge.env`
- Model: `codex-cli`

If the env file changes the port or model, use those values instead.

## Recommended sequence

1. Start the bridge.
2. Open SillyTavern.
3. If the install script already ran, expect the UI to be preconfigured and auto-connect on refresh.
4. If manual setup is needed, choose the OpenAI-compatible provider option.
5. Set source to `custom`.
6. Paste the base URL.
7. Paste the API key.
8. Enter the model name.
9. Use the model list or test connection action if SillyTavern exposes one.

## Expected behavior

- SillyTavern still owns the chat UI.
- The bridge converts chat messages to a plain transcript for `codex exec`.
- The bridge returns standard OpenAI-style chat completion JSON.
- This is sufficient for assistant-like chat and workflow help.
- This is not sufficient to guarantee strong roleplay continuity or character immersion.

## Troubleshooting

- `401 Unauthorized`: wrong API key or missing `Bearer` header.
- Empty model list: bridge is not running or `GET /v1/models` is failing.
- Connection refused: wrong port or bridge process not started.
- Long wait then failure: local `codex` command cannot reach the OpenAI backend from the user's machine.
- `Not connected to API!` with working backend endpoints: refresh the page and verify `power_user.auto_connect` is enabled. The install script now enables it by default.
- Theme switches or manual settings saves can break the bridge if `settings.json -> oai_settings.chat_completion_source`, `custom_url`, or `custom_model` are overwritten. Restore those fields instead of only editing top-level duplicates.
- Replies look too tool-oriented: change the messages or system prompt on the SillyTavern side; the bridge does not rewrite persona logic beyond transcript formatting.
- If roleplay keeps stalling even though the bridge is technically working, the likely limit is the backend behavior of `Codex` itself, not the HTTP bridge. In that case keep `Codex` for setup/writing tasks and switch the actual roleplay backend to a chat model tuned for RP.
