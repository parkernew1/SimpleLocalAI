from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from .config import AppConfig
from .models import find_apple_helper


def run_doctor(config_path: str | None = None) -> int:
    config = AppConfig.load(config_path)
    ok = True

    print("SimpleLocalAI doctor")
    print(f"Config: {config.path}")

    qwen = config.data["models"]["qwen"]
    base_url = qwen["base_url"].rstrip("/")
    target = qwen["model"]
    print("\nQwen / Ollama")
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        ok = False
        print("  warn: ollama is not installed or is not on PATH.")
        print("  manual: install Ollama, then run:")
        print(f"          ollama pull {target}")
        print("          ollama serve")
    else:
        print(f"  ok: ollama CLI found at {ollama_bin}")

    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        names = sorted(model.get("name", "") for model in payload.get("models", []))
        if target in names:
            print(f"  ok: Ollama is running and {target} is installed.")
        else:
            ok = False
            print(f"  warn: Ollama is running, but {target} was not found.")
            print("  installed:", ", ".join(names) if names else "(none)")
            print(f"  manual: ollama pull {target}")
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        ok = False
        print(f"  warn: could not reach Ollama at {base_url}: {exc}")
        if ollama_bin:
            print("  manual: start Ollama with `ollama serve`, then rerun doctor.")

    print("\nApple Foundation Model")
    helper = find_apple_helper(config.data["models"]["apple"])
    if helper:
        result = subprocess.run(
            [str(helper), "--doctor"],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        output = (result.stdout or result.stderr).strip()
        message = _doctor_message(output)
        if result.returncode == 0:
            print(f"  ok: {message}")
        else:
            ok = False
            print(f"  warn: {message}")
    else:
        ok = False
        print("  warn: helper was not found.")
        print("  manual: build scripts/apple-foundation-helper.swift into build/apple-foundation-helper.")
        print("  note: this can wait if you only want Qwen on macOS Sequoia.")

    swiftc = shutil.which("swiftc")
    print("\nTooling")
    print(f"  swiftc: {swiftc or 'not found'}")

    return 0 if ok else 1


def _doctor_message(output: str) -> str:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return output
    return str(payload.get("message") or payload.get("error") or output)
