# Aunty.ai — Your Personal Coding Assistant

Aunty.ai is a desktop AI coding assistant for developers who want a focused, workspace-aware environment for building and debugging software. Instead of treating AI like a generic chat box, it keeps the model grounded in your project, session history, and coding workflow.

The app is designed to help with multi-step software tasks: reading and explaining code, refactoring files, answering project-level questions, attaching screenshots, and working with large codebases through a local workspace.

## Features

- Desktop interface built with PySide6
- OpenRouter integration for remote model access
- Local Ollama support for self-hosted inference
- Workspace folder selection for project-aware prompts
- Session-based chat history
- Full-project context support for large codebases
- Image attachment support for visual references
- Optional voice output via text-to-speech
- Local storage for chats and project context

## Why Aunty.ai

A lot of AI coding tools feel like disconnected chat windows. Aunty.ai is designed to behave more like a real coding workspace:

- you open your project folder
- choose your model
- keep a conversation history for the task
- ask the assistant to work inside that codebase
- include large context when needed

This makes it useful for real development workflows, not just one-off Q&A.

## Supported models

The app is configured to work with:

- 0x Alpha via OpenRouter
- OpenRouter-hosted Llama models
- Local Ollama models

## Tech stack

- Python
- PySide6
- OpenAI-compatible API access
- SQLite for local session storage
- pyttsx3 for voice output

## Repository structure

- `src/ui.py` — main desktop application window
- `src/config.py` — app configuration and model settings
- `src/api_client.py` — OpenRouter and Ollama API logic
- `src/storage.py` — session and chat persistence
- `src/workspace.py` — workspace/project context handling
- `src/tts.py` — text-to-speech support
- `requirements.txt` — Python dependencies

## Installation

1. Clone the repository:

```bash
git clone https://github.com/23Q91A67F8-ai/Aunty-AI.git
cd Aunty-AI
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set your OpenRouter API key if you are using OpenRouter:

```bash
export OPENROUTER_API_KEY="your_api_key_here"
```

On Windows PowerShell:

```powershell
$env:OPENROUTER_API_KEY="your_api_key_here"
```

## Running the app

```bash
python src/ui.py
```

## Usage

- Open a project folder from the app
- Create a new chat session
- Select a model/provider
- Ask the assistant to explain, refactor, debug, or generate code
- Enable project context when you want the model to reason over your full codebase
- Attach images when you want visual inputs in the conversation
- Turn on voice if you want spoken responses

## Typical use cases

- codebase understanding and explanation
- bug fixing and debugging
- refactoring large files or modules
- generating new code based on project context
- asking architecture or implementation questions
- working with screenshots or UI references

## Notes

This project is intentionally focused on practical development workflows. The goal is to provide a local, project-aware assistant that feels more like a coding companion than a basic chatbot.

## License

MIT
