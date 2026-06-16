from __future__ import annotations

import json
import os
import shlex
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import AppConfig, parse_config_value
from .models import Message, ModelError, create_client, find_apple_helper


HELP = """Commands:
  /model [apple|qwen]               show or switch active model
  /models                           list configured models
  /status                           show model/config readiness dashboard
  /settings                         guided settings menu
  /afm                              show Apple Foundation Model setup panel
  /config                           show current config
  /config set <path> <value>        set config, e.g. qwen.options.temperature 0.4
  /preset [normal|coding]           set Qwen context to 16k or 32k
  /context [16k|32k|number]         set Qwen context window
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
                raw = input(f"\n{self._prompt_label(active)} ").strip()
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
        active = self.config.data["active_model"]
        qwen = self.config.data["models"]["qwen"]
        apple = self.config.data["models"]["apple"]
        lines = [
            "SimpleLocalAI",
            "Local chat: Qwen now, Apple Foundation Model when macOS is ready",
            f"Active: {active}   Qwen ctx: {qwen['options'].get('num_ctx')}   AFM helper: {self._yes_no(find_apple_helper(apple) is not None)}",
            f"Config: {self.config.path}",
            "Try /settings, /status, /model, /preset coding, or /help.",
        ]
        print(self._box("READY", lines))

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
        if command == "/status":
            self._command_status()
            return False
        if command == "/settings":
            self._command_settings()
            return False
        if command == "/afm":
            self._command_afm()
            return False
        if command == "/config":
            self._command_config(parts, raw)
            return False
        if command == "/preset":
            self._command_preset(parts)
            return False
        if command == "/context":
            self._command_context(parts)
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
            self._command_models()
            return

        name = parts[1]
        if name not in self.config.data["models"]:
            print(f"Unknown model '{name}'. Try /models.")
            return

        self.config.data["active_model"] = name
        self.config.save()
        print(self._notice(f"Switched to {name}."))

    def _command_models(self) -> None:
        active = self.config.data["active_model"]
        rows = []
        for name, model in self.config.data["models"].items():
            marker = "*" if name == active else " "
            rows.append(f"{marker} {name:<5} {model.get('display_name', name):<25} {model.get('provider')}")
        print(self._box("MODELS", rows))

    def _command_status(self) -> None:
        qwen = self.config.data["models"]["qwen"]
        apple = self.config.data["models"]["apple"]
        qwen_lines = [
            f"model:      {qwen.get('model')}",
            f"base url:   {qwen.get('base_url')}",
            f"context:    {qwen.get('options', {}).get('num_ctx')} tokens",
            f"thinking:   {self._yes_no(bool(qwen.get('think')))}",
            f"ollama cli: {shutil.which('ollama') or 'not found'}",
        ]
        apple_lines = [
            f"helper:     {find_apple_helper(apple) or 'not built/found'}",
            f"timeout:    {apple.get('timeout_seconds')} sec",
            f"max tokens: {apple.get('options', {}).get('maximum_response_tokens')}",
            "note:       Sequoia will warn; retry after Tahoe upgrade.",
        ]
        transcript_lines = [
            f"messages:   {len(self.messages)} in memory",
            "history:    not persisted unless you run /save",
        ]
        print(self._box("QWEN", qwen_lines))
        print(self._box("APPLE FOUNDATION MODEL", apple_lines))
        print(self._box("SESSION", transcript_lines))

    def _command_afm(self) -> None:
        apple = self.config.data["models"]["apple"]
        helper = find_apple_helper(apple)
        lines = [
            f"helper:      {helper or 'not built/found'}",
            f"configured:  {apple.get('helper_path') or '(auto search)'}",
            f"temperature: {apple.get('options', {}).get('temperature')}",
            f"max tokens:  {apple.get('options', {}).get('maximum_response_tokens')}",
            "",
            "After upgrading macOS:",
            "1. make apple-helper",
            "2. python3 -m simplelocalai doctor",
            "3. /model apple",
            "",
            "Use /settings to change AFM helper path or max tokens.",
        ]
        print(self._box("APPLE FOUNDATION MODEL", lines))

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
            print(self._notice(f"Set {path} = {json.dumps(value)}"))
            return

        print("Usage: /config or /config set <path> <value>")

    def _command_preset(self, parts: list[str]) -> None:
        if len(parts) != 2 or parts[1] not in ("normal", "coding"):
            print("Usage: /preset normal  or  /preset coding")
            return
        tokens = 16384 if parts[1] == "normal" else 32768
        self._set_qwen_context(tokens)
        print(self._notice(f"Applied {parts[1]} preset: Qwen context = {tokens} tokens."))

    def _command_context(self, parts: list[str]) -> None:
        if len(parts) != 2:
            print("Usage: /context 16k, /context 32k, or /context 32768")
            return
        try:
            tokens = parse_context_tokens(parts[1])
        except ValueError as exc:
            print(f"Invalid context: {exc}")
            return
        self._set_qwen_context(tokens)
        print(self._notice(f"Qwen context = {tokens} tokens."))

    def _command_settings(self) -> None:
        while True:
            qwen = self.config.data["models"]["qwen"]
            apple = self.config.data["models"]["apple"]
            lines = [
                f"1  active model          {self.config.data['active_model']}",
                f"2  Qwen context normal   16384",
                f"3  Qwen context coding   32768",
                f"4  Qwen thinking         {self._yes_no(bool(qwen.get('think')))}",
                f"5  Qwen temperature      {qwen['options'].get('temperature')}",
                f"6  Qwen output tokens    {qwen['options'].get('num_predict')}",
                f"7  Qwen model tag        {qwen.get('model')}",
                f"8  Qwen base URL         {qwen.get('base_url')}",
                f"9  AFM helper path       {apple.get('helper_path') or '(auto)'}",
                f"10 AFM max tokens        {apple['options'].get('maximum_response_tokens')}",
                "0  done",
            ]
            print(self._box("SETTINGS", lines))
            choice = input("setting> ").strip()
            if choice in ("0", "q", "quit", "done", ""):
                return
            self._apply_settings_choice(choice)

    def _apply_settings_choice(self, choice: str) -> None:
        if choice == "1":
            value = input("active model [qwen/apple]> ").strip()
            if value in self.config.data["models"]:
                self.config.data["active_model"] = value
            else:
                print("Unknown model.")
                return
        elif choice == "2":
            self._set_qwen_context(16384)
        elif choice == "3":
            self._set_qwen_context(32768)
        elif choice == "4":
            qwen = self.config.data["models"]["qwen"]
            qwen["think"] = not bool(qwen.get("think"))
        elif choice == "5":
            self._prompt_set("qwen.options.temperature", "temperature")
        elif choice == "6":
            self._prompt_set("qwen.options.num_predict", "output tokens")
        elif choice == "7":
            self._prompt_set("qwen.model", "model tag")
        elif choice == "8":
            self._prompt_set("qwen.base_url", "base URL")
        elif choice == "9":
            self._prompt_set("apple.helper_path", "AFM helper path")
        elif choice == "10":
            self._prompt_set("apple.options.maximum_response_tokens", "AFM max tokens")
        else:
            print("Choose a number from the menu.")
            return

        self.config.save()
        print(self._notice("Settings saved."))

    def _prompt_set(self, dotted_path: str, label: str) -> None:
        value_text = input(f"{label}> ").strip()
        if not value_text:
            print("No change.")
            return
        self.config.set_dotted(dotted_path, parse_config_value(value_text))

    def _set_qwen_context(self, tokens: int) -> None:
        self.config.set_dotted("qwen.options.num_ctx", tokens)
        self.config.save()

    def _send_user_message(self, text: str) -> None:
        active = self.config.data["active_model"]
        model_config = self.config.data["models"][active]
        client = create_client(active, model_config)

        self.messages.append(Message(role="user", content=text))
        print(f"{self._assistant_label(active)} ", end="", flush=True)

        chunks: list[str] = []
        try:
            for chunk in client.chat(self.messages):
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            print()
        except ModelError as exc:
            self.messages.pop()
            print()
            print(self._box("MODEL ERROR", [str(exc)]))
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
        print(self._notice(f"Saved transcript to {path}"))

    def _prompt_label(self, active: str) -> str:
        return f"[{active}] you>"

    def _assistant_label(self, active: str) -> str:
        return f"[{active}] assistant>"

    def _notice(self, text: str) -> str:
        return self._box("OK", [text])

    def _box(self, title: str, lines: list[str]) -> str:
        width = min(max(58, max(len(line) for line in lines + [title]) + 6), terminal_width())
        top = "+" + "-" * (width - 2) + "+"
        title_line = f"| {title[: width - 4].ljust(width - 4)} |"
        body = [f"| {line[: width - 4].ljust(width - 4)} |" for line in lines]
        return "\n".join([top, title_line, top, *body, top])

    def _yes_no(self, value: bool) -> str:
        return "yes" if value else "no"


def terminal_width() -> int:
    return shutil.get_terminal_size((88, 24)).columns


def parse_context_tokens(value: str) -> int:
    normalized = value.strip().lower().replace("_", "")
    if normalized.endswith("k"):
        number = normalized[:-1]
        if not number.isdigit():
            raise ValueError("use values like 16k, 32k, or 32768")
        tokens = int(number) * 1024
    else:
        if not normalized.isdigit():
            raise ValueError("use values like 16k, 32k, or 32768")
        tokens = int(normalized)

    if tokens < 1024:
        raise ValueError("context must be at least 1024 tokens")
    return tokens
