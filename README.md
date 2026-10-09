# Aunty.ai — Your Personal Coding Assistant

Aunty.ai is a desktop AI coding assistant built for working with real project folders in a focused, local workflow. It is designed for multi-step coding tasks, whole-repo context, chat history, attachments, and model switching across OpenRouter and local Ollama setups.

The app is built around the idea of having an always-available coding partner in your own workspace, rather than a single chat box with no project context.

## Highlights

- Desktop app for Windows/macOS-style local development workflows
- Connects to OpenRouter or local Ollama models
- Supports project workspace selection and full-project context injection
- Keeps chat history per session for ongoing coding work
- Includes image attachment support for UI and design references
- Optional voice output with text-to-speech
- Built with PySide6 for a native desktop interface

## Default model support

This project is configured to work with:

- 0x Alpha (stealth preview model on OpenRouter)
- Llama models via OpenRouter
- Local Ollama models

## What this project does

Aunty.ai helps you:

- ask questions about a codebase
- refactor or explain files inside an active project
- work across multi-step coding tasks with session memory
- include entire project context when needed for large codebases
- attach screenshots or design references to a prompt
- have a local, organized workspace for ongoing AI-assisted development

## Tech stack

- Python
- PySide6
- OpenAI-compatible API client
- SQLite-backed local session storage
- Optional TTS via pyttsx3

## Project structure

- `src/ui.py` — main desktop interface
- `src/config.py` — configuration and model setup
- `src/api_client.py` — API client logic for OpenRouter / Ollama
- `src/storage.py` — local chat and session storage
- `src/workspace.py` — workspace/project context builder
- `src/tts.py` — text-to-speech support

## Installation

1. Clone the repository
2. Create a virtual environment
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set your API key if using OpenRouter:

```bash
export OPENROUTER_API_KEY="your_key_here"
```

5. Run the app:

```bash
python src/ui.py
```

## Usage

- Open a project folder from the app
- Start a new chat session
- Choose your model/provider
- Ask for code changes, explanations, architecture help, or debugging
- Optionally include the whole project as context for larger tasks
- Attach images if you want visual input in the conversation

## Notes

This project is focused on practical coding assistance, not hype. The app is meant to make working with AI models feel more like a real coding environment than a generic chat interface.

## License

MIT
