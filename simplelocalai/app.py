from __future__ import annotations

import json
import os
import shlex
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import AppConfig, parse_config_value
from .models import Message, ModelError, create_client


HELP = """Commands:
  /model [apple|qwen]               show or switch active model
  /models                           list configured models
  /config                           show current config
  /config set <path> <value>        set config, e.g. qwen.options.temperature 0.4
  /new                              clear transcript
  /save [path]                      save transcript as Markdown
  /doctor                           run readiness checks
  /help                             show this help
  /quit                             exit
"""


class ChatApp:
    def __init__(self, config_path: str | None = None) -> None:
        self.config = AppConfig.load(config_path)
        self.messages: list[Message] = []

    def run(self) -> None:
        self._print_banner()
        while True:
            active = self.config.data["active_model"]
            try:
                raw = input(f"\n[{active}] you> ").strip()
            except EOFError:
                print()
                return

            if not raw:
                continue

            if raw.startswith("/"):
                if self._handle_command(raw):
                    return
                continue

            self._send_user_message(raw)

    def _print_banner(self) -> None:
        print("SimpleLocalAI")
        print("Local terminal chat: Apple Foundation Model <-> Qwen")
        print(f"Config: {self.config.path}")
        print("Type /help for commands.")

    def _handle_command(self, raw: str) -> bool:
        try:
            parts = shlex.split(raw)
        except ValueError as exc:
            print(f"Could not parse command: {exc}")
            return False

        command = parts[0]
        if command in ("/quit", "/exit", "/q"):
            return True
        if command == "/help":
            print(HELP)
            return False
        if command == "/model":
            self._command_model(parts)
            return False
        if command == "/models":
            self._command_models()
            return False
        if command == "/config":
            self._command_config(parts, raw)
            return False
        if command == "/new":
            self.messages.clear()
            print("Started a fresh transcript.")
            return False
        if command == "/save":
            path = Path(parts[1]).expanduser() if len(parts) > 1 else self._default_save_path()
            self._save_transcript(path)
            return False
        if command == "/doctor":
            from .doctor import run_doctor

            run_doctor(str(self.config.path))
            return False

        print(f"Unknown command: {command}")
        print("Type /help for commands.")
        return False

    def _command_model(self, parts: list[str]) -> None:
        if len(parts) == 1:
            print(f"Active model: {self.config.data['active_model']}")
            return

        name = parts[1]
        if name not in self.config.data["models"]:
            print(f"Unknown model '{name}'. Try /models.")
            return

        self.config.data["active_model"] = name
        self.config.save()
        print(f"Switched to {name}.")

    def _command_models(self) -> None:
        active = self.config.data["active_model"]
        for name, model in self.config.data["models"].items():
            marker = "*" if name == active else " "
            print(f"{marker} {name}: {model.get('display_name', name)} ({model.get('provider')})")

    def _command_config(self, parts: list[str], raw: str) -> None:
        if len(parts) == 1:
            print(json.dumps(self.config.data, indent=2, sort_keys=True))
            return

        if len(parts) >= 4 and parts[1] == "set":
            path = parts[2]
            value_text = raw.split(path, 1)[1].strip()
            value = parse_config_value(value_text)
            self.config.set_dotted(path, value)
            self.config.save()
            print(f"Set {path} = {json.dumps(value)}")
            return

        print("Usage: /config or /config set <path> <value>")

    def _send_user_message(self, text: str) -> None:
        active = self.config.data["active_model"]
        model_config = self.config.data["models"][active]
        client = create_client(active, model_config)

        self.messages.append(Message(role="user", content=text))
        print(f"[{active}] assistant> ", end="", flush=True)

        chunks: list[str] = []
        try:
            for chunk in client.chat(self.messages):
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            print()
        except ModelError as exc:
            self.messages.pop()
            print()
            print(f"Model error: {exc}")
            return

        self.messages.append(Message(role="assistant", content="".join(chunks), model=active))

    def _default_save_path(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        directory = Path(os.environ.get("SIMPLELOCALAI_TRANSCRIPTS", "~/.simplelocalai/transcripts")).expanduser()
        return directory / f"chat-{stamp}.md"

    def _save_transcript(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# SimpleLocalAI Transcript", ""]
        for message in self.messages:
            label = message.role
            if message.model:
                label += f" ({message.model})"
            lines.extend([f"## {label}", "", message.content, ""])
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Saved transcript to {path}")

