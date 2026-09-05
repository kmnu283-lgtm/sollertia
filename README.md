# Sollertia

Sollertia (Latin: "skill, cleverness, resourceful diligence") is an open-source autonomous AI agent framework with a live browser, full takeover capabilities, and a modern mission-control interface.

## Features

- Multi-LLM Support (OpenRouter, Gemini)
- Live Browser Screen
- Take Control mode
- Real-Time Event Stream
- Rich Tool Suite
- Approval Mode
- Mission-Control UI

## Quick Start

1. Clone: git clone https://github.com/kmnu283-lgtm/sollertia.git
2. cd sollertia/backend
3. python -m venv venv && source venv/bin/activate
4. pip install -r requirements.txt
5. playwright install chromium
6. uvicorn main:app --reload
7. Open http://localhost:8000

## Usage

1. Select LLM provider (OpenRouter or Gemini)
2. Enter API key
3. Specify model (e.g., google/gemini-2.5-flash)
4. Give Sollertia a mission
5. Click Run!

## Manual Takeover

- goto <url>
- click <selector>
- type <selector> <text>
- shot
- back

## Roadmap

- Memory & planning scratchpad
- File system access
- Python code execution
- Web search integration
- Parallel sub-agents
- Artifact export

---

Built with care by the Sollertia team.
