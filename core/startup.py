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
    
    # Only run schema if database is empty/new
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    has_users = cursor.fetchone() is not None
    conn.close()
    
    if not has_users:
        schema_path = Path(__file__).parent.parent / 'database' / 'schema.sql'
        if schema_path.exists():
            try:
                with open(schema_path) as f:
                    schema_sql = f.read()
                conn = db.get_connection()
                conn.executescript(schema_sql)
                conn.close()
                print("    Schema initialized")
            except Exception as e:
                print(f"    Schema init skipped: {e}")
        
        seed_path = Path(__file__).parent.parent / 'database' / 'seed.sql'
        if seed_path.exists():
            try:
                with open(seed_path) as f:
                    seed_sql = f.read()
                conn = db.get_connection()
                conn.executescript(seed_sql)
                conn.close()
                print("    Seed data loaded")
            except Exception as e:
                print(f"    Seed skipped: {e}")
    
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