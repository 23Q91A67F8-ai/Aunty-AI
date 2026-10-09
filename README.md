# Aunty.ai

Your personal coding assistant for real project work.

Aunty.ai is a desktop AI coding companion built for developers who want to work inside their own codebase instead of chatting in a generic prompt box. It brings model access, workspace context, session history, and local project awareness into one focused desktop workflow.

## Why Aunty.ai

Most AI coding tools feel like disconnected chat interfaces. Aunty.ai is designed to feel more like a real coding workspace:

- open your project folder
- choose a model
- continue a chat session
- ask for explanations, refactors, and debugging help
- keep the project context relevant to the task

## Features

- Desktop app built with PySide6
- OpenRouter integration for managed model access
- Local Ollama support for self-hosted setups
- Workspace-aware coding assistant
- Session-based chat history
- Full-project context support for large codebases
- Image attachments for visual references
- Optional voice output
- Local storage for conversations and project context

## How it works

1. Open a project folder in the app.
2. Select a provider and model.
3. Start a chat session.
4. Ask for code explanations, refactors, architecture help, or debugging support.
5. Optionally include project context or attach images for visual input.

The goal is simple: make AI useful in a real software workflow, not just as a one-off chatbot.

## Supported models

Aunty.ai is configured to work with:

- 0x Alpha via OpenRouter
- OpenRouter-hosted Llama models
- Local Ollama models

## Use it on the web

Aunty.ai also runs in the browser at https://singular-croquembouche-9035e4.netlify.app. You don't need to install anything or set an API key.

- Choose Claude, GPT or Gemini (routed through Netlify AI Gateway)
- Click **Open folder** to load a project. Files are read in your browser and sent as context with your messages
- Attach or paste screenshots, and turn on **Voice** to hear replies read aloud
- Chats are saved per browser in Netlify Database, so you can come back to them later

The web app lives in `site/` (front end), `netlify/functions/` (chat and session APIs) and `db/` (database schema).

## Installation (desktop app)

### 1) Clone the repository

```bash
git clone https://github.com/23Q91A67F8-ai/Aunty-AI.git
cd Aunty-AI
```

### 2) Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Set your API key

If you are using OpenRouter:

```bash
export OPENROUTER_API_KEY="your_api_key_here"
```

On Windows PowerShell:

```powershell
$env:OPENROUTER_API_KEY="your_api_key_here"
```

### 5) Run the app

```bash
python src/ui.py
```

## Project structure

```text
Aunty-AI/
├── src/
│   ├── api_client.py
│   ├── config.py
│   ├── storage.py
│   ├── tts.py
│   ├── ui.py
│   └── workspace.py
├── requirements.txt
├── README.md
├── LICENSE
└── llms.txt
```

## Typical use cases

- understand an unfamiliar codebase
- debug failing logic
- refactor or rewrite files safely
- ask architecture and implementation questions
- generate code based on project context
- work with screenshots and UI references

## License

MIT
