# ERP AI Assistant - Agent Guidelines

## Essential Commands

**Start the system:**
```bash
./run.sh
```
- Handles provider selection (Ollama/llama.cpp), model selection, and app mode (CLI/Web)
- Creates virtual environment and installs dependencies if needed
- For Web UI: starts Gunicorn server on port 5000
- For CLI: runs main.py directly

**Direct CLI execution:**
```bash
.venv/bin/python main.py
```

**Direct Web UI execution:**
```bash
.venv/bin/gunicorn -w 1 --timeout 300 --threads 4 -b 0.0.0.0:5000 'web:app'
```

## Project Structure

- **Entry points:** `main.py` (CLI), `web.py` (Web UI)
- **Core logic:** `core/` directory (database, LLM handler, operations, conversation)
- **Configuration:** `config.yaml` (database, LLM providers, system settings)
- **Dependencies:** `requirements.txt`
- **Data:** SQLite database at `./data/erp.db`

## Key Files

- `config.yaml`: Configure database path, LLM providers (Ollama/llama.cpp), model selection
- `requirements.txt`: Flask, requests, pyyaml, reportlab, sqlite-utils, faster-whisper
- `run.sh`: Interactive setup script for provider/model/app mode selection

## Development Notes

- Uses SQLite database with automatic table creation on first run
- LLM provider must be available (Ollama on localhost:11434 or llama.cpp on localhost:8000)
- Virtual environment managed automatically by run.sh
- Conversation state maintained in memory during session
- No test suite present (testing mentioned in PRD but not implemented)
- Web UI uses Flask with CORS enabled
- PDF generation uses reportlab library
- Environment excludes `.venv/`, `__pycache__/`, `*.pyc`, `data/`, `*.db`, `*.pdf`, `.DS_Store`

## Troubleshooting

**Web UI model dropdown shows "Loading..."**
- Fix: Ensured `/api/models` endpoint properly initializes app state before accessing config
- Related files: `web.py` (api_models function and init_app call)
- Verified by: Checking that `curl http://localhost:5000/api/models` returns model list