# ERP AI Assistant

An AI-powered ERP (Enterprise Resource Planning) assistant that uses local large language models (Ollama or llama.cpp) to handle business operations through natural language.

## Features

- **Natural Language Interface**: Interact with your ERP system using plain English
- **Local LLM Processing**: Runs entirely on your machine using Ollama or llama.cpp
- **Dual Interface**: Use as CLI or Web UI
- **Database Management**: SQLite-based storage for customers and inventory
- **Invoice Generation**: Generate PDF invoices with customizable tax rates
- **Provider Switching**: Seamlessly switch between Ollama and llama.cpp

## Requirements

- Python 3.8+
- [Ollama](https://ollama.ai/) or llama.cpp server
- SQLite

## Quick Start

```bash
# Clone and navigate to the project
cd ERP-AI

# Run the interactive setup script
./run.sh
```

The `run.sh` script will:
1. Create a virtual environment
2. Install dependencies
3. Prompt you to choose provider (Ollama/llama.cpp)
4. Prompt you to choose interface (CLI/Web)
5. Launch your selected mode

## Manual Setup

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 2. Configure LLM Provider

Edit `config.yaml` to set your preferred provider:

```yaml
ollama:
  enabled: true        # Set to true for Ollama
  host: localhost
  port: 11434
  model: gemma3:270m   # Or your preferred model

llama_cpp:
  enabled: false       # Set to true for llama.cpp
  host: localhost
  port: 8080
```

### 3. Run the Application

**CLI Mode:**
```bash
.venv/bin/python main.py
```

**Web UI Mode:**
```bash
.venv/bin/gunicorn -w 1 --timeout 300 --threads 4 -b 0.0.0.0:5000 'web:app'
```

Then open http://localhost:5000 in your browser.

## Usage

### CLI Commands

| Command | Description |
|---------|-------------|
| `/customers` | List customers |
| `/items` | List inventory items |
| `/model` | Show current model |
| `/switch` | Switch LLM provider |
| `/help` | Show help |
| `quit` | Exit |

### Web UI

The web interface provides:
- Chat-style interaction with the AI
- Model selection dropdown
- Customer and item management

## Project Structure

```
ERP-AI/
├── main.py           # CLI entry point
├── web.py            # Web UI entry point
├── config.yaml      # Configuration file
├── requirements.txt # Python dependencies
├── run.sh           # Setup script
├── core/            # Core logic
│   ├── database.py  # SQLite operations
│   ├── llm_handler.py  # LLM provider handling
│   ├── operations.py    # Business operations
│   └── conversation.py # Chat history
└── utils/
    └── invoice_generator.py  # PDF generation
```

## Configuration

All settings are in `config.yaml`:

- **database**: SQLite file path
- **invoice**: Default tax rate (17%), payment terms, invoice prefix
- **ollama**: Host, port, model selection
- **llama_cpp**: Host, port
- **system**: Auto-retry settings

## Examples

### Creating a Customer

```
You: Add a new customer called Acme Corp with contact john@acme.com
AI: Customer 'Acme Corp' created with ID: 1
```

### Checking Inventory

```
You: What items do we have?
AI: You have the following items:
    - Widget A (SKU: WID-A): $10.00
    - Gadget B (SKU: GAD-B): $25.00
```

### Generating Invoice

```
You: Generate invoice for Acme Corp with 5 Widget A
AI: Invoice INV-0001 generated successfully
```

## Troubleshooting

### "No providers available"

Ensure Ollama is running:
```bash
ollama serve
```

Or llama.cpp:
```bash
./server -c /path/to/model.gguf
```

### Web UI shows "Loading..."

The `/api/models` endpoint may not have initialized. Verify:
```bash
curl http://localhost:5000/api/models
```

### Database Issues

Delete the database to reset:
```bash
rm data/erp.db
# Restart the application to recreate
```

## Technology Stack

- **Runtime**: Python 3.8+
- **Web Framework**: Flask
- **Database**: SQLite (via sqlite-utils)
- **PDF Generation**: ReportLab
- **LLM Providers**: Ollama, llama.cpp

## License

MIT License