# Digital Infrastructure Newsletter

Automated weekly newsletter generation for digital infrastructure using a LangGraph multi-agent workflow.

## Features

- **Multi-Agent Workflow**: Manager → Research Agents → Reviewer → Editor → Assembly
- **Three Verticals**: Data Centers, Connectivity & Fibre, Towers & Wireless Infrastructure
- **Natural Language Input**: Describe your newsletter requirements in plain English
- **Evidence-Based**: Every claim is backed by cited sources
- **FastAPI Backend**: RESTful API for newsletter generation and retrieval

## Setup

1. **Install dependencies**:
   ```bash
   pip install -e .
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Run the server**:
   ```bash
   uvicorn src.main:app --reload
   ```

## API Endpoints

- `POST /newsletter/generate` - Generate a new newsletter issue
- `GET /newsletter/{id}` - Retrieve newsletter markdown
- `GET /newsletter/{id}/sections/{section_id}` - Retrieve section markdown
- `POST /newsletter/{id}/update-section` - Update a specific section

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `TAVILY_API_KEY` | Tavily search API key | Required |
| `MODEL_MANAGER` | LLM for input parsing | `gpt-4o` |
| `MODEL_RESEARCH` | LLM for research agents | `gpt-4o` |
| `MODEL_REVIEW` | LLM for reviewer | `gpt-4o` |
| `MODEL_EDIT` | LLM for editor | `gpt-4o` |
| `MAX_TOOL_CALLS_PER_AGENT` | Tool call budget | `12` |
| `ISSUES_DIR` | Output directory | `./issues` |

## License

MIT
