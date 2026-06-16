from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Protocol


@dataclass
class Message:
    role: str
    content: str
    model: str | None = None


class ModelError(RuntimeError):
    pass


class ChatClient(Protocol):
    def chat(self, messages: list[Message]) -> Iterator[str]:
        ...


def create_client(name: str, config: dict[str, Any]) -> ChatClient:
    provider = config.get("provider")
    if provider == "ollama":
        return OllamaClient(name, config)
    if provider == "apple_foundation":
        return AppleFoundationClient(name, config)
    raise ModelError(f"Unsupported provider '{provider}' for model '{name}'.")


class OllamaClient:
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config

    def chat(self, messages: list[Message]) -> Iterator[str]:
        url = self.config["base_url"].rstrip("/") + "/api/chat"
        payload = self._payload(messages)
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=float(self.config.get("timeout_seconds", 300)),
            ) as response:
                if payload["stream"]:
                    yield from self._iter_stream(response)
                else:
                    body = json.loads(response.read().decode("utf-8"))
                    yield body.get("message", {}).get("content", "")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ModelError(f"Ollama HTTP {exc.code}: {body}") from exc
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            raise ModelError(f"Could not reach local Ollama at {url}: {exc}") from exc

    def _payload(self, messages: list[Message]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config["model"],
            "messages": self._ollama_messages(messages),
            "stream": bool(self.config.get("stream", True)),
            "options": self.config.get("options", {}),
        }
        if "think" in self.config:
            payload["think"] = self.config["think"]
        return payload

    def _ollama_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        output = []
        system_prompt = self.config.get("system_prompt")
        if system_prompt:
            output.append({"role": "system", "content": system_prompt})
        for message in messages:
            output.append({"role": message.role, "content": message.content})
        return output

    def _iter_stream(self, response: Any) -> Iterator[str]:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            chunk = json.loads(line)
            if "error" in chunk:
                raise ModelError(chunk["error"])
            yield chunk.get("message", {}).get("content", "")
            if chunk.get("done"):
                return


class AppleFoundationClient:
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config

    def chat(self, messages: list[Message]) -> Iterator[str]:
        helper = find_apple_helper(self.config)
        if not helper:
            raise ModelError(
                "Apple helper not found. Build scripts/apple-foundation-helper.swift "
                "or set apple.helper_path."
            )

        payload = {
            "system_prompt": self.config.get("system_prompt", ""),
            "messages": [message.__dict__ for message in messages],
            "options": self.config.get("options", {}),
        }

        try:
            result = subprocess.run(
                [str(helper)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                timeout=float(self.config.get("timeout_seconds", 120)),
                check=False,
            )
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            raise ModelError(f"Could not run Apple helper: {exc}") from exc

        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise ModelError(detail or f"Apple helper exited with {result.returncode}")

        try:
            body = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ModelError(f"Apple helper returned invalid JSON: {result.stdout}") from exc

        if not body.get("ok"):
            raise ModelError(body.get("error", "Apple helper returned an unknown error."))

        yield body.get("content", "")


def find_apple_helper(config: dict[str, Any]) -> Path | None:
    candidates: list[Path] = []
    env_path = os.environ.get("SIMPLELOCALAI_APPLE_HELPER")
    configured = config.get("helper_path")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    if configured:
        candidates.append(Path(configured).expanduser())

    root = Path(__file__).resolve().parents[1]
    candidates.extend(
        [
            root / "build" / "apple-foundation-helper",
            root / "scripts" / "apple-foundation-helper",
        ]
    )

    which = shutil.which("apple-foundation-helper")
    if which:
        candidates.append(Path(which))

    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    return None
