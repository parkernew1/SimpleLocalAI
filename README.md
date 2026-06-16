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

On macOS Sequoia, use Qwen now and leave the Apple provider unbuilt or inactive until you update to a supported Apple Intelligence OS:

```text
/model qwen
```

Inside the chat:

```text
/model apple
/model qwen
/afm
/config
/config set qwen.options.temperature 0.4
/config set qwen.model qwen3.5:9b
/config set qwen.think true
/new
/save
/help
/quit
```

Regular text is sent to the currently active model. The conversation history is shared, so switching models lets the newly selected model continue from the same chat context.

## Manual Setup

### Qwen 3.5 9B

Qwen works on macOS Sequoia because it runs through Ollama, not Apple's Foundation Models framework.

Install Ollama:

```bash
brew install ollama
```

Then pull and run the local Qwen model:

```bash
ollama pull qwen3.5:9b
ollama serve
```

In another terminal, start the app:

```bash
python3 -m simplelocalai doctor
python3 -m simplelocalai chat
```

If Ollama publishes the model under a different local tag, set it in SimpleLocalAI:

```text
/config set qwen.model your-local-qwen-tag
```

The Qwen provider sends requests only to the configured local `base_url`.

The official Ollama library lists `qwen3.5:9b` as the 9B Qwen 3.5 tag. It is roughly a 6.6GB download and advertises a 256K context window. The app defaults to a smaller `num_ctx` of 4096 for memory friendliness; raise it as your machine allows:

```text
/config set qwen.options.num_ctx 8192
```

Qwen 3.5 supports thinking output through Ollama. SimpleLocalAI defaults `qwen.think` to `false` so chat feels like a regular assistant. Turn it on when you want visible reasoning output:

```text
/config set qwen.think true
```

### Apple Foundation Model

Apple's on-device model is exposed to third-party apps through the official `FoundationModels` framework on supported Apple Intelligence devices and OS versions. This project includes a small Swift command-line helper at `scripts/apple-foundation-helper.swift`.

macOS Sequoia is expected to report that Foundation Models are unavailable. That is okay if you only want to use Qwen for now.

After upgrading macOS, use this quick path:

```bash
make apple-helper
python3 -m simplelocalai doctor
python3 -m simplelocalai chat
```

Then in the TUI:

```text
/afm
/model apple
```

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
The Qwen provider also passes `qwen.think` to Ollama's top-level `think` field.

## Commands

- `/model [apple|qwen]` shows or changes the active model.
- `/models` lists available configured models.
- `/status` shows model and session status cards.
- `/settings` opens the guided settings menu.
- `/afm` shows Apple Foundation Model setup and readiness notes.
- `/config` prints current config.
- `/config set <model.path> <value>` updates config and saves it.
- `/preset normal` sets Qwen context to 16K.
- `/preset coding` sets Qwen context to 32K.
- `/context <tokens>` sets Qwen context directly, e.g. `/context 32k`.
- `/new` clears the current transcript.
- `/save [path]` saves a Markdown transcript.
- `/doctor` runs local readiness checks.
- `/help` shows commands.
- `/quit` exits.

## Notes

- Apple model access depends on Apple Intelligence availability for the signed-in user, device, locale, and OS. SimpleLocalAI does not extract private Siri assets.
- Qwen model naming varies by local runtime. The default is easy to change.
- Streaming is supported for Ollama. The Apple helper returns a full response.
