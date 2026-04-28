import requests
import sqlite3
from pathlib import Path
from .config import load_config
from .database import Database


def check_ollama(host: str, port: int) -> bool:
    try:
        resp = requests.get(f"http://{host}:{port}/api/tags", timeout=2)
        return resp.status_code == 200
    except:
        return False


def check_llama_cpp(host: str, port: int) -> bool:
    try:
        resp = requests.get(f"http://{host}:{port}/health", timeout=2)
        return resp.status_code == 200
    except:
        return False


def init_database(config: dict) -> Database:
    db_path = config['database']['path']
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db = Database(db_path)
    
    schema_path = Path(__file__).parent.parent / 'database' / 'schema.sql'
    if schema_path.exists():
        with open(schema_path) as f:
            schema_sql = f.read()
        conn = db.get_connection()
        conn.executescript(schema_sql)
        conn.close()
    
    seed_path = Path(__file__).parent.parent / 'database' / 'seed.sql'
    if seed_path.exists():
        with open(seed_path) as f:
            seed_sql = f.read()
        conn = db.get_connection()
        conn.executescript(seed_sql)
        conn.close()
    
    return db


def run_startup():
    config = load_config()
    
    ollama_cfg = config.get('ollama', {})
    llm_cfg = config.get('llama_cpp', {})
    
    ollama_available = check_ollama(ollama_cfg.get('host', 'localhost'), ollama_cfg.get('port', 11434))
    llamacpp_available = check_llama_cpp(llm_cfg.get('host', 'localhost'), llm_cfg.get('port', 8000))
    
    print("\n[1] Database")
    print(f"    SQLite: {config['database']['path']}")
    
    print("\n[2] LLM Providers")
    print(f"    Ollama:      {'✓' if ollama_available else '✗'}")
    print(f"    llama.cpp: {'✓' if llamacpp_available else '✗'}")
    
    if not ollama_available and not llamacpp_available:
        print("\n⚠ No LLM providers available. Running in wait mode...")
    
    db = init_database(config)
    print(f"\n[3] Database initialized")
    
    return config, db