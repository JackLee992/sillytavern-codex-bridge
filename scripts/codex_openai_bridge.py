#!/usr/bin/env python3
import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


DEFAULT_ENV_FILE = Path.home() / ".codex" / "sillytavern-codex-bridge.env"
DEFAULT_WORKDIR = Path.home() / ".codex" / "tmp" / "sillytavern-bridge-workspace"


@dataclass
class BridgeConfig:
    host: str
    port: int
    api_key: str
    model_id: str
    codex_bin: str
    codex_model: str | None
    codex_cwd: Path
    env_file: Path
    request_timeout: int


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_setting(name: str, env_values: dict[str, str], default: str | None = None) -> str | None:
    return os.environ.get(name) or env_values.get(name) or default


def resolve_codex_bin(raw_value: str) -> str:
    direct = Path(raw_value).expanduser()
    if direct.exists():
        return str(direct.resolve())
    found = shutil.which(raw_value)
    if found:
        return found
    if os.name == "nt":
        npm_bin = Path.home() / "AppData" / "Roaming" / "npm"
        for candidate in (
            npm_bin / f"{raw_value}.cmd",
            npm_bin / f"{raw_value}.exe",
            npm_bin / f"{raw_value}.bat",
            npm_bin / raw_value,
        ):
            if candidate.exists():
                return str(candidate.resolve())
    return raw_value


def build_config(env_file: Path, args: argparse.Namespace) -> BridgeConfig:
    env_values = load_env_file(env_file)
    host = args.host or get_setting("SILLYTAVERN_CODEX_HOST", env_values, "127.0.0.1")
    port = int(args.port or get_setting("SILLYTAVERN_CODEX_PORT", env_values, "8787"))
    api_key = args.api_key or get_setting("SILLYTAVERN_CODEX_API_KEY", env_values)
    if not api_key:
        raise SystemExit(
            f"Missing SILLYTAVERN_CODEX_API_KEY. Create {env_file} first or pass --api-key."
        )
    model_id = args.model_id or get_setting("SILLYTAVERN_CODEX_MODEL_ID", env_values, "codex-cli")
    codex_bin = resolve_codex_bin(
        args.codex_bin or get_setting("SILLYTAVERN_CODEX_BIN", env_values, "codex")
    )
    codex_model = args.codex_model or get_setting("SILLYTAVERN_CODEX_MODEL", env_values)
    codex_cwd_raw = args.codex_cwd or get_setting(
        "SILLYTAVERN_CODEX_CWD", env_values, str(DEFAULT_WORKDIR)
    )
    timeout = int(args.request_timeout or get_setting("SILLYTAVERN_CODEX_TIMEOUT", env_values, "600"))
    codex_cwd = Path(codex_cwd_raw).expanduser().resolve()
    codex_cwd.mkdir(parents=True, exist_ok=True)
    return BridgeConfig(
        host=host,
        port=port,
        api_key=api_key,
        model_id=model_id,
        codex_bin=codex_bin,
        codex_model=codex_model,
        codex_cwd=codex_cwd,
        env_file=env_file,
        request_timeout=timeout,
    )


def flatten_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "text":
                text = item.get("text")
                if text:
                    parts.append(str(text))
            elif item_type == "input_text":
                text = item.get("text")
                if text:
                    parts.append(str(text))
            elif item_type in {"image_url", "input_image"}:
                parts.append("[image omitted]")
        return "\n".join(part for part in parts if part).strip()
    return str(content)


def transcript_from_messages(messages: list[dict[str, Any]]) -> str:
    lines = [
        "Respond to the final user turn as the assistant.",
        "Use the conversation transcript below as the full context.",
        "",
        "Conversation:",
    ]
    for message in messages:
        role = str(message.get("role", "user")).upper()
        content = flatten_content(message.get("content", ""))
        if not content:
            continue
        lines.append(f"[{role}]")
        lines.append(content)
        lines.append("")
    return "\n".join(lines).strip()


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def run_codex(prompt: str, config: BridgeConfig) -> tuple[str, str]:
    with tempfile.NamedTemporaryFile(prefix="codex-bridge-", suffix=".txt", delete=False) as handle:
        output_path = Path(handle.name)
    command = [
        config.codex_bin,
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "-C",
        str(config.codex_cwd),
        "-o",
        str(output_path),
    ]
    if config.codex_model:
        command.extend(["--model", config.codex_model])
    command.append(prompt)
    child_env = os.environ.copy()
    # Clear inherited proxy/sandbox overrides so a local bridge can reach Codex normally.
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "GIT_HTTP_PROXY",
        "GIT_HTTPS_PROXY",
        "CODEX_SANDBOX_NETWORK_DISABLED",
    ):
        child_env.pop(key, None)
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=config.request_timeout,
            check=False,
            env=child_env,
        )
        reply = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        if result.returncode != 0:
            detail = stderr or stdout or f"codex exited with code {result.returncode}"
            raise RuntimeError(detail)
        if not reply.strip():
            detail = stderr or stdout or "codex produced no assistant message"
            raise RuntimeError(detail)
        return reply.strip(), stderr
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            pass


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "SillyTavernCodexBridge/0.1"

    @property
    def config(self) -> BridgeConfig:
        return self.server.bridge_config  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok", "model": self.config.model_id})
            return
        if self.path == "/v1/models":
            self._send_json(
                HTTPStatus.OK,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": self.config.model_id,
                            "object": "model",
                            "owned_by": "local-codex-bridge",
                        }
                    ],
                },
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": {"message": "Not found"}})

    def do_POST(self) -> None:
        if self.path not in {"/v1/chat/completions", "/v1/completions"}:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": {"message": "Not found"}})
            return
        if not self._authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": {"message": "Unauthorized"}})
            return
        try:
            body = self._read_json()
            response = self._handle_completion(body)
            if body.get("stream"):
                self._send_stream(response)
            else:
                self._send_json(HTTPStatus.OK, response)
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                HTTPStatus.BAD_GATEWAY,
                {"error": {"message": f"Bridge error: {exc}"}},
            )

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        return header.startswith(prefix) and secrets.compare_digest(
            header[len(prefix) :],
            self.config.api_key,
        )

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        data = json.loads(payload or "{}")
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        return data

    def _handle_completion(self, body: dict[str, Any]) -> dict[str, Any]:
        if self.path == "/v1/completions":
            prompt = str(body.get("prompt", ""))
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = body.get("messages", [])
            if not isinstance(messages, list):
                raise ValueError("messages must be a list")
            prompt = transcript_from_messages(messages)
        answer, stderr = run_codex(prompt, self.config)
        created = int(time.time())
        completion_id = f"chatcmpl-{created}"
        usage = {
            "prompt_tokens": estimate_tokens(prompt),
            "completion_tokens": estimate_tokens(answer),
            "total_tokens": estimate_tokens(prompt) + estimate_tokens(answer),
        }
        response = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": self.config.model_id,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "finish_reason": "stop",
                }
            ],
            "usage": usage,
        }
        if stderr:
            response["system_fingerprint"] = "codex-cli"
        return response

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_stream(self, response: dict[str, Any]) -> None:
        content = response["choices"][0]["message"]["content"]
        created = response["created"]
        completion_id = response["id"]
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        first_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": self.config.model_id,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
        self.wfile.write(f"data: {json.dumps(first_chunk)}\n\n".encode("utf-8"))
        self.wfile.flush()

        for start in range(0, len(content), 96):
            piece = content[start : start + 96]
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": self.config.model_id,
                "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
            }
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
            self.wfile.flush()

        final_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": self.config.model_id,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        self.wfile.write(f"data: {json.dumps(final_chunk)}\n\n".encode("utf-8"))
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expose codex exec as a local OpenAI-compatible API.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Path to the bridge env file.")
    parser.add_argument("--host", help="Listen host override.")
    parser.add_argument("--port", type=int, help="Listen port override.")
    parser.add_argument("--api-key", help="API key override.")
    parser.add_argument("--model-id", help="Model id shown to clients.")
    parser.add_argument("--codex-bin", help="Path to codex executable.")
    parser.add_argument("--codex-model", help="Optional codex model override.")
    parser.add_argument("--codex-cwd", help="Working directory for codex exec.")
    parser.add_argument("--request-timeout", type=int, help="Per-request timeout in seconds.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    env_file = Path(args.env_file).expanduser().resolve()
    config = build_config(env_file, args)
    server = ThreadingHTTPServer((config.host, config.port), BridgeHandler)
    server.bridge_config = config  # type: ignore[attr-defined]
    print(f"SillyTavern Codex bridge listening on http://{config.host}:{config.port}/v1")
    print(f"Model id: {config.model_id}")
    print(f"Env file: {config.env_file}")
    print(f"Codex cwd: {config.codex_cwd}")
    server.serve_forever()


if __name__ == "__main__":
    main()
