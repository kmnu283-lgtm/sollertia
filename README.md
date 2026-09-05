# Sollertia

**Sollertia** (Latin: "skill, cleverness, resourceful diligence") is an open-source autonomous AI agent framework with a live browser, full takeover capabilities, and a modern mission-control interface.

## Features

- Multi-LLM Support (OpenRouter, Gemini)
- Live Browser Screen with real-time screenshots
- Take Control mode for manual browser driving
- Real-Time Event Stream (thoughts, actions, observations)
- Rich Tool Suite: browser, files, code execution, web search
- Parallel Sub-Agents for delegated research
- Cost Tracking (tokens and USD)
- Approval Mode for human oversight
- Session Recording and Export to markdown
- Plan Visualization with progress tracking
- Docker support for easy deployment

## Quick Start

### Local Development

1. Clone: git clone https://github.com/kmnu283-lgtm/sollertia.git
2. cd sollertia/backend
3. python -m venv venv and source venv/bin/activate
4. pip install -r requirements.txt
5. playwright install chromium
6. uvicorn main:app --reload
7. Open http://localhost:8000

### Docker

1. Clone the repo
2. cd sollertia
3. docker-compose up --build
4. Open http://localhost:8000

## Configuration

All via environment variables:
- SOLLERTIA_PROVIDER (default: openrouter)
- SOLLERTIA_MODEL (default: google/gemini-2.5-flash)
- SOLLERTIA_MAX_STEPS (default: 30)
- SOLLERTIA_TIMEOUT (default: 30)
- SOLLERTIA_APPROVAL (0 or 1, default: 0)

## License

MIT

Built with care by the Sollertia team.
