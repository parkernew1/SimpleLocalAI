from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "active_model": "qwen",
    "models": {
        "apple": {
            "provider": "apple_foundation",
            "display_name": "Apple Foundation Model",
            "helper_path": "",
            "system_prompt": "You are a concise, helpful local assistant.",
            "timeout_seconds": 120,
            "options": {
                "temperature": 0.7,
                "maximum_response_tokens": 768,
            },
        },
        "qwen": {
            "provider": "ollama",
            "display_name": "Qwen 3.5 9B",
            "base_url": "http://127.0.0.1:11434",
            "model": "qwen3.5:9b",
            "system_prompt": "You are a concise, helpful local assistant.",
            "timeout_seconds": 300,
            "stream": True,
            "think": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "repeat_penalty": 1.1,
                "num_ctx": 4096,
                "num_predict": 768,
            },
        },
    },
}


class AppConfig:
    def __init__(self, path: Path, data: dict[str, Any]) -> None:
        self.path = path
        self.data = data

    @classmethod
    def load(cls, path: str | None = None) -> "AppConfig":
        config_path = Path(path).expanduser() if path else default_config_path()
        if config_path.exists():
            data = merge_defaults(json.loads(config_path.read_text(encoding="utf-8")))
        else:
            data = deepcopy(DEFAULT_CONFIG)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return cls(config_path, data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")

    def set_dotted(self, dotted_path: str, value: Any) -> None:
        parts = dotted_path.split(".")
        if parts[0] in self.data.get("models", {}):
            parts = ["models", *parts]

        cursor: dict[str, Any] = self.data
        for part in parts[:-1]:
            existing = cursor.get(part)
            if not isinstance(existing, dict):
                existing = {}
                cursor[part] = existing
            cursor = existing
        cursor[parts[-1]] = value


def default_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base).expanduser() / "simplelocalai" / "config.json"
    return Path("~/.simplelocalai/config.json").expanduser()


def merge_defaults(user_data: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(DEFAULT_CONFIG)
    deep_update(merged, user_data)
    return merged


def deep_update(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = value


def parse_config_value(value_text: str) -> Any:
    try:
        return json.loads(value_text)
    except json.JSONDecodeError:
        return value_text
