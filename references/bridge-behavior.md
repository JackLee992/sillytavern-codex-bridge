# Bridge behavior

## Endpoints

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/completions`

## Authentication

Require `Authorization: Bearer <key>` and compare it with `SILLYTAVERN_CODEX_API_KEY`.

## Execution path

1. Receive OpenAI-style request.
2. Flatten message content into text.
3. Build a transcript prompt.
4. Run `codex exec` in a dedicated workspace.
5. Return the last assistant message as the OpenAI response.

## Defaults

- host: `127.0.0.1`
- port: `8787`
- model id: `codex-cli`
- sandbox: `read-only`
- workspace: `~/.codex/tmp/sillytavern-bridge-workspace`

## Streaming

Support both non-streaming JSON and text/event-stream output.

Streaming is synthetic: the bridge gets the full Codex response first, then emits it in chunks. This keeps compatibility with clients that expect stream events without requiring token-level Codex streaming support.

## Limits

- This bridge is optimized for chat completion calls, not tool calling.
- It does not preserve OpenAI token accounting; usage values are rough estimates.
- It depends on the local `codex` CLI already being logged in and working on the machine that runs the bridge.
- On Windows, inherited `HTTP_PROXY` or `HTTPS_PROXY` values from a sandboxed shell can break `codex exec`. Clear them before launching the child process.
- On Windows, feeding multilingual prompts through stdin may fail due to encoding issues in `codex.cmd`; passing the prompt as a direct command argument is more reliable.
