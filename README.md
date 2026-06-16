# SimpleLocalAI

SimpleLocalAI is a standalone terminal chat app for talking to local LLMs and switching between them during a session.

It ships with two local providers:

- **Apple Foundation Model** through Apple's official `FoundationModels` Swift framework.
- **Qwen 3.5 9B** through a local Ollama-compatible API, defaulting to `qwen3.5:9b` on `http://127.0.0.1:11434`.

No hosted model API keys are used.

## Quick Start

```bash
python3 -m simplelocalai doctor
python3 -m simplelocalai chat
```

Inside the chat:

```text
/model apple
/model qwen
/config
/config set qwen.options.temperature 0.4
/config set qwen.model qwen3.5:9b
/new
/save
/help
/quit
```

Regular text is sent to the currently active model. The conversation history is shared, so switching models lets the newly selected model continue from the same chat context.

## Manual Setup

### Qwen 3.5 9B

Install and run Ollama, then pull the model name you want to use:

```bash
ollama pull qwen3.5:9b
ollama serve
```

If Ollama publishes the model under a different local tag, set it in SimpleLocalAI:

```text
/config set qwen.model your-local-qwen-tag
```

The Qwen provider sends requests only to the configured local `base_url`.

### Apple Foundation Model

Apple's on-device model is exposed to third-party apps through the official `FoundationModels` framework on supported Apple Intelligence devices and OS versions. This project includes a small Swift command-line helper at `scripts/apple-foundation-helper.swift`.

Build it on a supported Mac with Xcode command-line tools:

```bash
mkdir -p build
swiftc scripts/apple-foundation-helper.swift -o build/apple-foundation-helper
```

Then either leave it at `build/apple-foundation-helper`, put it on your `PATH`, or point the app to it:

```text
/config set apple.helper_path /absolute/path/to/apple-foundation-helper
```

If your current SDK does not include `FoundationModels`, the helper builds as a diagnostic stub and the doctor command will tell you what is missing.

## Configuration

Config is stored at:

```text
~/.simplelocalai/config.json
```

You can edit it directly or use `/config set <path> <value>` in the TUI. Values are parsed as JSON when possible, so numbers, booleans, arrays, and objects work:

```text
/config set qwen.options.num_ctx 8192
/config set qwen.options.stop ["User:","Assistant:"]
/config set apple.options.maximum_response_tokens 512
```

The Ollama provider passes everything under `qwen.options` to Ollama's `options` object. The Apple helper accepts best-effort generation options supported by the local Foundation Models SDK.

## Commands

- `/model [apple|qwen]` shows or changes the active model.
- `/models` lists available configured models.
- `/config` prints current config.
- `/config set <model.path> <value>` updates config and saves it.
- `/new` clears the current transcript.
- `/save [path]` saves a Markdown transcript.
- `/doctor` runs local readiness checks.
- `/help` shows commands.
- `/quit` exits.

## Notes

- Apple model access depends on Apple Intelligence availability for the signed-in user, device, locale, and OS. SimpleLocalAI does not extract private Siri assets.
- Qwen model naming varies by local runtime. The default is easy to change.
- Streaming is supported for Ollama. The Apple helper returns a full response.

