# ERP AI Assistant Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI-powered ERP system where users interact via natural language. AI interprets instructions, generates SQL, and executes database operations. Test where AI breaks with complete database freedom.

**Architecture:** Layered approach - User Interface → Conversation Engine → AI Handler (LLM) → Operation Layer (SQL generation + execution) → SQLite Database. Dual LLM providers (Ollama + llama.cpp) with mid-session switching.

**Tech Stack:** Python 3.9+, Flask (lightweight HTTP), SQLite (embedded DB), Ollama API, llama.cpp API, ReportLab/FPDF2 (PDF generation), PyYAML (config)

---

## Chunk 1: Project Foundation

### Task 1: Project Setup

**Files:**
- Create: `config.yaml`
- Create: `requirements.txt`
- Create: `main.py`

- [ ] **Step 1: Write config.yaml**

```yaml
database:
  type: sqlite
  path: ./data/erp.db

ollama:
  host: localhost
  port: 11434
  model: mistral  # or llama3
  enabled: true

llama_cpp:
  host: localhost
  port: 8000
  enabled: true

system:
  retry_timeout: 5
  max_retries: 3
  auto_retry: true

invoice:
  prefix: "INV"
  payment_terms_days: 30
  default_tax_rate: 0.17
```

- [ ] **Step 2: Write requirements.txt**

```
flask>=2.3.0
requests>=2.31.0
pyyaml>=6.0
reportlab>=4.0.0
sqlite-utils>=3.35
```

- [ ] **Step 3: Write main.py**

```python
"""ERP AI Assistant - Main Entry Point"""
import sys
from core.startup import run_startup

def main():
    """Initialize and run the ERP AI system."""
    print("ERP AI Assistant starting...")
    
    # Run startup sequence
    config = run_startup()
    
    print("\n✓ System ready!")
    print(f"  Database: {config['database']['path']}")
    print(f"  LLM: Ollama + llama.cpp available")
    print("\nType your request or 'quit' to exit.")
    
    # Start chat loop (placeholder)
    while True:
        user_input = input("\n> ")
        if user_input.lower() in ('quit', 'exit'):
            break
        print(f"[AI] Processing: {user_input}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 5: Commit**

```bash
git add config.yaml requirements.txt main.py
git commit -m "feat: add project foundation - config, requirements, main entry"
```

---

### Task 2: Core Module Structure

**Files:**
- Create: `core/__init__.py`
- Create: `core/startup.py`
- Create: `core/config.py`
- Create: `core/database.py`

- [ ] **Step 1: Write core/__init__.py**

```python
"""Core modules for ERP AI Assistant."""
from .config import load_config
from .database import Database

__all__ = ['load_config', 'Database']
```

- [ ] **Step 2: Write core/config.py**

```python
"""Configuration loader."""
import yaml
from pathlib import Path

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    with open(path) as f:
        config = yaml.safe_load(f)
    
    return config
```

- [ ] **Step 3: Write core/startup.py**

```python
"""Startup sequence and validation."""
import requests
from .config import load_config
from .database import Database

def check_ollama(host: str, port: int) -> bool:
    """Check if Ollama is running."""
    try:
        resp = requests.get(f"http://{host}:{port}/api/tags", timeout=2)
        return resp.status_code == 200
    except:
        return False

def check_llama_cpp(host: str, port: int) -> bool:
    """Check if llama.cpp is running."""
    try:
        resp = requests.get(f"http://{host}:{port}/health", timeout=2)
        return resp.status_code == 200
    except:
        return False

def run_startup() -> dict:
    """Run startup sequence."""
    # Load config
    config = load_config()
    
    # Detect LLM providers
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
    
    return config
```

- [ ] **Step 4: Write core/database.py**

```python
"""Database connection and queries."""
import sqlite3
from pathlib import Path
from typing import Optional

class Database:
    """SQLite database wrapper."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self):
        """Create data directory if needed."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute(self, query: str, params: tuple = ()) -> list:
        """Execute query and return rows."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def execute_write(self, query: str, params: tuple = ()) -> int:
        """Execute write query, return rows affected."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
```

- [ ] **Step 5: Run startup to verify**

```bash
cd /home/fawad/ai/ERP-AI
python main.py
```

Expected output:
```
ERP AI Assistant starting...
[1] Database
    SQLite: ./data/erp.db
[2] LLM Providers
    Ollama:      ✓ or ✗
    llama.cpp:  ✓ or ✗
```

- [ ] **Step 6: Commit**

```bash
git add core/
git commit -m "feat: add core module structure - startup, config, database"
```

---

## Chunk 2: Database Schema

### Task 3: Create Schema and Seed Data

**Files:**
- Create: `database/schema.sql`
- Create: `database/seed.sql`
- Modify: `core/startup.py` (to initialize DB)

- [ ] **Step 1: Write database/schema.sql**

```sql
-- Core ERP Tables for SQLite

-- Users
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    full_name TEXT,
    role TEXT DEFAULT 'user',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    contact_name TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    credit_limit REAL DEFAULT 0,
    payment_terms_days INTEGER DEFAULT 30,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Warehouses
CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_code TEXT NOT NULL UNIQUE,
    warehouse_name TEXT NOT NULL,
    address TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Items (Products)
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_code TEXT NOT NULL UNIQUE,
    item_name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    unit_of_measure TEXT DEFAULT 'PCS',
    unit_price REAL DEFAULT 0,
    cost_price REAL DEFAULT 0,
    reorder_level INTEGER DEFAULT 10,
    current_stock INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Stock Balances (per warehouse)
CREATE TABLE IF NOT EXISTS stock_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 0,
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
    UNIQUE(item_id, warehouse_id)
);

-- Stock Movements (audit trail)
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL, -- IN, OUT, ADJUST
    quantity INTEGER NOT NULL,
    reference_type TEXT, -- invoice, po, production
    reference_id INTEGER,
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
);

-- Invoice Drafts
CREATE TABLE IF NOT EXISTS invoice_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    customer_id INTEGER NOT NULL,
    customer_name TEXT,
    invoice_date TEXT,
    due_date TEXT,
    warehouse_id INTEGER,
    items_data TEXT, -- JSON
    subtotal REAL DEFAULT 0,
    tax_rate REAL DEFAULT 0.17,
    tax_amount REAL DEFAULT 0,
    total REAL DEFAULT 0,
    notes TEXT,
    status TEXT DEFAULT 'draft',
    created_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Invoices (finalized)
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL,
    customer_name TEXT,
    invoice_date TEXT,
    due_date TEXT,
    status TEXT DEFAULT 'finalized',
    subtotal REAL DEFAULT 0,
    tax_rate REAL DEFAULT 0.17,
    tax_amount REAL DEFAULT 0,
    total_amount REAL DEFAULT 0,
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Invoice Items
CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    item_code TEXT,
    item_name TEXT,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    amount REAL NOT NULL,
    tax_rate REAL DEFAULT 0.17,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

-- Settings
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Activity Log
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    operation TEXT NOT NULL,
    details TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

- [ ] **Step 2: Write database/seed.sql**

```sql
-- Seed data for testing

-- Default warehouse
INSERT OR IGNORE INTO warehouses (warehouse_code, warehouse_name, address) 
VALUES ('WH01', 'Main Warehouse', '123 Industrial Ave');

-- Sample users
INSERT OR IGNORE INTO users (username, email, full_name, role) 
VALUES 
    ('admin', 'admin@erp.local', 'System Admin', 'admin'),
    ('user', 'user@erp.local', 'Default User', 'user');

-- Sample customers
INSERT OR IGNORE INTO customers (customer_code, customer_name, contact_name, email, credit_limit, payment_terms_days) 
VALUES 
    ('CUST001', 'ABC Corporation', 'John Smith', 'john@abc.com', 50000, 30),
    ('CUST002', 'XYZ Industries', 'Jane Doe', 'jane@xyz.com', 75000, 45),
    ('CUST003', 'Tech Solutions Ltd', 'Bob Wilson', 'bob@techsol.com', 25000, 30);

-- Sample items
INSERT OR OR REPLACE INTO items (item_code, item_name, description, category, unit_price, cost_price, reorder_level, current_stock) 
VALUES 
    ('PROD001', 'Widget A', 'Standard widget', 'Electronics', 1000, 600, 50, 100),
    ('PROD002', 'Widget B', 'Premium widget', 'Electronics', 1500, 900, 30, 50),
    ('PROD003', 'Gadget X', 'Basic gadget', 'Hardware', 500, 300, 100, 200),
    ('PROD004', 'Gadget Y', 'Advanced gadget', 'Hardware', 800, 480, 50, 75),
    ('PROD005', 'Component Z', 'Essential component', 'Parts', 250, 150, 200, 500);

-- Stock balances
INSERT OR IGNORE INTO stock_balances (item_id, warehouse_id, quantity)
SELECT id, 1, current_stock FROM items WHERE is_active = 1;

-- Settings
INSERT OR IGNORE INTO settings (setting_key, setting_value) 
VALUES 
    ('default_tax_rate', '0.17'),
    ('default_payment_terms', '30'),
    ('invoice_prefix', 'INV');
```

- [ ] **Step 3: Update core/startup.py to init DB**

```python
# Add to run_startup() after checking providers:

# Initialize database
db_path = config['database']['path']
db = Database(db_path)

# Create schema
schema_path = Path(__file__).parent.parent / 'database' / 'schema.sql'
if schema_path.exists():
    with open(schema_path) as f:
        schema_sql = f.read()
    conn = db.get_connection()
    conn.executescript(schema_sql)
    conn.close()

# Seed data
seed_path = Path(__file__).parent.parent / 'database' / 'seed.sql'
if seed_path.exists():
    with open(seed_path) as f:
        seed_sql = f.read()
    conn = db.get_connection()
    conn.executescript(seed_sql)
    conn.close()

print("\n[3] Database initialized")
```

- [ ] **Step 4: Run and verify schema**

```bash
python main.py
```

Expected: Schema tables created in SQLite

- [ ] **Step 5: Commit**

```bash
git add database/ core/startup.py
git commit -m "feat: add database schema and seed data"
```

---

## Chunk 3: AI Handler Layer

### Task 4: LLM Handler with Provider Abstraction

**Files:**
- Create: `core/llm_handler.py`

- [ ] **Step 1: Write core/llm_handler.py**

```python
"""LLM Provider Handler with abstraction."""
import requests
from typing import Optional

class LLMHandler:
    """Handles LLM providers (Ollama, llama.cpp)."""
    
    def __init__(self, config: dict):
        self.config = config
        self.current_provider = None
        self.current_model = None
    
    def chat(self, prompt: str, system_prompt: str = "") -> str:
        """Send chat request to current provider."""
        if self.current_provider == 'ollama':
            return self._call_ollama(prompt, system_prompt)
        elif self.current_provider == 'llama_cpp':
            return self._call_llama_cpp(prompt, system_prompt)
        else:
            raise ValueError("No provider selected")
    
    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Call Ollama API."""
        cfg = self.config.get('ollama', {})
        host = cfg.get('host', 'localhost')
        port = cfg.get('port', 11434)
        model = cfg.get('model', 'mistral')
        
        full_prompt = f"{system_prompt}\n\nUser: {prompt}" if system_prompt else prompt
        
        response = requests.post(
            f"http://{host}:{port}/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Ollama error: {response.text}")
        
        return response.json().get("response", "")
    
    def _call_llama_cpp(self, prompt: str, system_prompt: str) -> str:
        """Call llama.cpp API."""
        cfg = self.config.get('llama_cpp', {})
        host = cfg.get('host', 'localhost')
        port = cfg.get('port', 8000)
        
        full_prompt = f"{system_prompt}\n\nUser: {prompt}" if system_prompt else prompt
        
        response = requests.post(
            f"http://{host}:{port}/completion",
            json={
                "prompt": full_prompt,
                "n_predict": 500,
                "temperature": 0.7
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"llama.cpp error: {response.text}")
        
        return response.json().get("content", "")
    
    def set_provider(self, provider: str):
        """Switch LLM provider."""
        if provider not in ('ollama', 'llama_cpp'):
            raise ValueError(f"Unknown provider: {provider}")
        self.current_provider = provider
    
    def switch_provider(self, new_provider: str, conversation_history: list = None) -> str:
        """Switch provider and transfer context."""
        old_provider = self.current_provider
        self.set_provider(new_provider)
        
        # Context transfer message
        return f"Switched from {old_provider} to {new_provider}. Context transferred."
```

- [ ] **Step 2: Test LLM handler**

```python
# Add to main.py to test
from core.llm_handler import LLMHandler
from core.config import load_config

config = load_config()
llm = LLMHandler(config)

# Test Ollama if available
if check_ollama('localhost', 11434):
    llm.set_provider('ollama')
    response = llm.chat("Say 'hello' if you can hear me", "You are a helpful assistant.")
    print(f"Ollama response: {response}")
```

- [ ] **Step 3: Commit**

```bash
git add core/llm_handler.py
git commit -m "feat: add LLM handler with provider abstraction"
```

---

### Task 5: SQL Generator & Parser

**Files:**
- Create: `core/operations.py`

- [ ] **Step 1: Write core/operations.py**

```python
"""Operation layer - SQL generation and execution."""
import json
from typing import Optional
from .database import Database
from .llm_handler import LLMHandler

class Operation:
    """Business operations via AI-generated SQL."""
    
    def __init__(self, db: Database, llm: LLMHandler):
        self.db = db
        self.llm = llm
    
    def process(self, user_message: str, context: dict = None) -> str:
        """Process user message - interpret, generate SQL, execute."""
        # Build prompt with schema context
        prompt = self._build_prompt(user_message, context)
        
        # Get LLM response
        response = self.llm.chat(prompt, self._system_prompt())
        
        # Extract and execute SQL
        return self._handle_response(response)
    
    def _system_prompt(self) -> str:
        """System prompt for ERP operations."""
        return """You are an ERP AI Assistant. You help users manage invoices, inventory, customers, and sales.

Your job:
1. Understand the user's request in plain English
2. Generate the appropriate SQL query
3. Execute it on the SQLite database

Schema:
- customers(id, customer_code, customer_name, email, is_active)
- items(id, item_code, item_name, category, unit_price, current_stock)
- warehouses(id, warehouse_code, warehouse_name)
- stock_balances(item_id, warehouse_id, quantity)
- invoices(id, invoice_no, customer_id, total_amount, status)
- invoice_items(invoice_id, item_id, quantity, unit_price)
- invoice_drafts(id, customer_id, items_data, status)

Rules:
1. Always use parameterized queries to prevent SQL injection
2. Return results in a user-friendly format
3. If no data found, say so clearly
4. If error, explain what went wrong

Output format:
- SQL: <the SQL query to execute>
- Then execute and return results"""
    
    def _build_prompt(self, message: str, context: Optional[dict]) -> str:
        """Build prompt with context."""
        prompt = message
        if context:
            # Add relevant context
            if context.get('current_customer'):
                prompt = f"Current customer: {context['current_customer']}\n\n{prompt}"
            if context.get('current_draft'):
                prompt = f"Current draft invoice: {context['current_draft']}\n\n{prompt}"
        return prompt
    
    def _handle_response(self, response: str) -> str:
        """Parse LLM response and execute SQL if present."""
        # Simple extraction - look for SQL in response
        lines = response.strip().split('\n')
        sql = None
        
        for line in lines:
            if line.startswith('SQL:'):
                sql = line[4:].strip()
                break
        
        if not sql:
            # No SQL to execute, return response as-is
            return response
        
        # Execute SQL
        try:
            if sql.strip().upper().startswith('SELECT'):
                results = self.db.execute(sql)
                return self._format_results(results)
            else:
                rowid = self.db.execute_write(sql)
                return f"Operation completed. Rows affected: {rowid}"
        except Exception as e:
            return f"Error executing SQL: {e}\n\nOriginal response: {response}"
    
    def _format_results(self, rows: list) -> str:
        """Format query results."""
        if not rows:
            return "No results found."
        
        # Format as table
        if len(rows) == 1:
            row = rows[0]
            return "\n".join(f"{k}: {v}" for k, v in row.items())
        
        # Multiple rows
        headers = list(rows[0].keys())
        header_line = " | ".join(headers)
        separator = "-" * len(header_line)
        
        lines = [header_line, separator]
        for row in rows:
            lines.append(" | ".join(str(row.get(h, '')) for h in headers))
        
        return "\n".join(lines) + f"\n\n({len(rows)} rows)"
```

- [ ] **Step 2: Test operations**

```python
# Add to main.py after init
db = Database(config['database']['path'])
op = Operation(db, llm)

# Test query
result = op.process("Show me all customers", {})
print(f"Result: {result}")
```

- [ ] **Step 3: Commit**

```bash
git add core/operations.py
git commit -m "feat: add operations layer - SQL generation and execution"
```

---

## Chunk 4: Invoice Workflow

### Task 6: Invoice Creation Flow

**Files:**
- Modify: `core/operations.py` (add invoice-specific methods)

- [ ] **Step 1: Add invoice methods to operations.py**

```python
    def create_invoice_draft(self, customer_id: int, customer_name: str, warehouse_id: int = 1) -> dict:
        """Create draft invoice."""
        from datetime import datetime, timedelta
        
        invoice_date = datetime.now().strftime('%Y-%m-%d')
        due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        query = """
        INSERT INTO invoice_drafts 
        (customer_id, customer_name, invoice_date, due_date, warehouse_id, status)
        VALUES (?, ?, ?, ?, ?, 'draft')
        """
        
        draft_id = self.db.execute_write(query, (
            customer_id, customer_name, invoice_date, due_date, warehouse_id
        ))
        
        return {
            'draft_id': draft_id,
            'customer': customer_name,
            'invoice_date': invoice_date,
            'due_date': due_date
        }
    
    def get_customer_purchase_history(self, customer_id: int) -> list:
        """Get top products purchased by customer."""
        query = """
        SELECT i.id, i.item_code, i.item_name, COUNT(*) as purchase_count,
               SUM(ii.quantity) as total_qty
        FROM invoice_items ii
        JOIN invoices inv ON ii.invoice_id = inv.id
        JOIN items i ON ii.item_id = i.id
        WHERE inv.customer_id = ? AND inv.status = 'finalized'
        GROUP BY i.id
        ORDER BY purchase_count DESC
        LIMIT 5
        """
        return self.db.execute(query, (customer_id,))
    
    def add_item_to_draft(self, draft_id: int, item_id: int, quantity: int) -> dict:
        """Add item to draft invoice."""
        # Get item details
        item = self.db.execute("SELECT * FROM items WHERE id = ?", (item_id,))[0]
        
        # Get current draft
        draft = self.db.execute("SELECT * FROM invoice_drafts WHERE id = ?", (draft_id,))[0]
        
        # Parse existing items_data
        items_data = json.loads(draft['items_data'] or '["items": []]')
        if 'items' not in items_data:
            items_data = {'items': [], 'subtotal': 0, 'tax_rate': 0.17, 'tax_amount': 0, 'total': 0}
        
        # Add new item
        amount = item['unit_price'] * quantity
        items_data['items'].append({
            'item_id': item_id,
            'item_code': item['item_code'],
            'item_name': item['item_name'],
            'quantity': quantity,
            'unit_price': item['unit_price'],
            'amount': amount
        })
        
        # Recalculate totals
        subtotal = sum(i['amount'] for i in items_data['items'])
        tax_rate = items_data.get('tax_rate', 0.17)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        items_data['subtotal'] = subtotal
        items_data['tax_amount'] = tax_amount
        items_data['total'] = total
        
        # Update draft
        query = "UPDATE invoice_drafts SET items_data = ?, subtotal = ?, tax_amount = ?, total = ? WHERE id = ?"
        self.db.execute_write(query, (json.dumps(items_data), subtotal, tax_amount, total, draft_id))
        
        return items_data
    
    def finalize_invoice(self, draft_id: int, user_id: int = 1) -> dict:
        """Finalize draft invoice."""
        from datetime import datetime
        
        # Get draft
        draft = self.db.execute("SELECT * FROM invoice_drafts WHERE id = ?", (draft_id,))[0]
        
        items_data = json.loads(draft['items_data'] or '{"items": []}')
        
        if not items_data.get('items'):
            raise ValueError("Draft has no items")
        
        # Generate invoice number
        today = datetime.now().strftime('%Y%m%d')
        last_inv = self.db.execute(
            "SELECT MAX(CAST(RIGHT(invoice_no, 4) AS INTEGER)) as last_no FROM invoices WHERE invoice_no LIKE ?",
            (f"INV-{today}-%",)
        )
        next_num = (last_inv[0]['last_no'] or 0) + 1
        invoice_no = f"INV-{today}-{next_num:04d}"
        
        # Create invoice
        query = """
        INSERT INTO invoices 
        (invoice_no, customer_id, customer_name, invoice_date, due_date, status,
         subtotal, tax_rate, tax_amount, total_amount, created_by)
        VALUES (?, ?, ?, ?, ?, 'finalized', ?, ?, ?, ?, ?, ?)
        """
        invoice_id = self.db.execute_write(query, (
            invoice_no, draft['customer_id'], draft['customer_name'],
            draft['invoice_date'], draft['due_date'],
            items_data['subtotal'], items_data['tax_rate'],
            items_data['tax_amount'], items_data['total'], user_id
        ))
        
        # Create invoice items
        for item in items_data['items']:
            query = """
            INSERT INTO invoice_items 
            (invoice_id, item_id, item_code, item_name, quantity, unit_price, amount, tax_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db.execute_write(query, (
                invoice_id, item['item_id'], item['item_code'], item['item_name'],
                item['quantity'], item['unit_price'], item['amount'], items_data['tax_rate']
            ))
            
            # Deduct stock
            self._deduct_stock(item['item_id'], item['quantity'], draft['warehouse_id'])
        
        # Update draft status
        self.db.execute_write("UPDATE invoice_drafts SET status = 'finalized' WHERE id = ?", (draft_id,))
        
        return {
            'invoice_no': invoice_no,
            'invoice_id': invoice_id,
            'total': items_data['total']
        }
    
    def _deduct_stock(self, item_id: int, quantity: int, warehouse_id: int):
        """Deduct stock after invoice finalization."""
        query = """
        UPDATE stock_balances 
        SET quantity = quantity - ?
        WHERE item_id = ? AND warehouse_id = ?
        """
        self.db.execute_write(query, (quantity, item_id, warehouse_id))
        
        # Update items current_stock
        self.db.execute_write("""
        UPDATE items SET current_stock = (
            SELECT SUM(quantity) FROM stock_balances WHERE item_id = ?
        ) WHERE id = ?
        """, (item_id, item_id))
```

- [ ] **Step 2: Commit**

```bash
git add core/operations.py
git commit -m "feat: add invoice creation workflow - draft, items, finalize"
```

---

## Chunk 5: Conversation Engine

### Task 7: Session & Context Management

**Files:**
- Create: `core/conversation.py`

- [ ] **Step 1: Write core/conversation.py**

```python
"""Conversation engine - session and context management."""
import json
import uuid
from datetime import datetime
from typing import Optional

class ConversationEngine:
    """Manages conversation sessions and context."""
    
    def __init__(self, db: Database):
        self.db = db
        self.sessions = {}  # In-memory session cache
    
    def start_session(self) -> str:
        """Start new session."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'session_id': session_id,
            'current_customer_id': None,
            'current_customer_name': None,
            'current_draft_id': None,
            'current_invoice_no': None,
            'last_operation': None,
            'last_operation_id': None,
            'warehouse_id': 1,
            'user_id': 1,
            'conversation_history': []
        }
        return session_id
    
    def get_context(self, session_id: str) -> dict:
        """Get session context."""
        return self.sessions.get(session_id, {})
    
    def update_context(self, session_id: str, **kwargs):
        """Update session context."""
        if session_id in self.sessions:
            self.sessions[session_id].update(kwargs)
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add message to history."""
        if session_id in self.sessions:
            self.sessions[session_id]['conversation_history'].append({
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat()
            })
    
    def get_history(self, session_id: str, limit: int = 10) -> list:
        """Get conversation history."""
        ctx = self.sessions.get(session_id, {})
        hist = ctx.get('conversation_history', [])
        return hist[-limit:] if len(hist) > limit else hist
    
    def set_current_customer(self, session_id: str, customer_id: int, customer_name: str):
        """Set current customer."""
        self.update_context(
            session_id,
            current_customer_id=customer_id,
            current_customer_name=customer_name
        )
    
    def set_current_draft(self, session_id: str, draft_id: int):
        """Set current draft invoice."""
        self.update_context(session_id, current_draft_id=draft_id)
    
    def get_conversation_summary(self, session_id: str) -> str:
        """Get summary for LLM context."""
        ctx = self.get_context(session_id)
        parts = []
        
        if ctx.get('current_customer_name'):
            parts.append(f"Current customer: {ctx['current_customer_name']}")
        if ctx.get('current_invoice_no'):
            parts.append(f"Current invoice: {ctx['current_invoice_no']}")
        if ctx.get('last_operation'):
            parts.append(f"Last operation: {ctx['last_operation']}")
        
        return ", ".join(parts) if parts else "No active context"
```

- [ ] **Step 2: Modify main.py to use conversation**

```python
# Add to main.py
from core.conversation import ConversationEngine

# In main():
session_id = conv_engine.start_session()
print(f"Session: {session_id[:8]}...")
```

- [ ] **Step 3: Commit**

```bash
git add core/conversation.py
git commit -m "feat: add conversation engine - session and context"
```

---

## Chunk 6: Main Chat Interface

### Task 8: Chat Loop

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update main.py with full chat loop**

```python
"""ERP AI Assistant - Main Entry Point"""
import sys
from core.startup import run_startup, check_ollama, check_llama_cpp
from core.config import load_config
from core.database import Database
from core.llm_handler import LLMHandler
from core.operations import Operation
from core.conversation import ConversationEngine

def main():
    print("ERP AI Assistant starting...")
    
    # Startup
    config = run_startup()
    
    # Initialize components
    db = Database(config['database']['path'])
    llm = LLMHandler(config)
    op = Operation(db, llm)
    conv = ConversationEngine(db)
    
    # Start session
    session_id = conv.start_session()
    print(f"\n✓ System ready! Session: {session_id[:8]}")
    print("Type your request or 'quit' to exit.\n")
    
    # Select LLM provider
    ollama_ok = check_ollama(config['ollama']['host'], config['ollama']['port'])
    llamacpp_ok = check_llama_cpp(config['llama_cpp']['host'], config['llama_cpp']['port'])
    
    if ollama_ok:
        llm.set_provider('ollama')
        print(f"Using: Ollama ({config['ollama']['model']})")
    elif llamacpp_ok:
        llm.set_provider('llama_cpp')
        print("Using: llama.cpp")
    else:
        print("⚠ No LLM - running in query mode only")
    
    # Chat loop
    while True:
        user_input = input("\n> ").strip()
        if not user_input:
            continue
        if user_input.lower() in ('quit', 'exit'):
            break
        
        # Handle special commands
        if user_input.startswith('/'):
            cmd = user_input[1:].lower()
            if cmd == 'switch':
                # Switch provider
                new_provider = 'llama_cpp' if llm.current_provider == 'ollama' else 'ollama'
                msg = llm.switch_provider(new_provider)
                print(f"[AI] {msg}")
            elif cmd == 'customers':
                results = db.execute("SELECT * FROM customers LIMIT 10")
                print(format_results(results))
            elif cmd == 'items':
                results = db.execute("SELECT * FROM items LIMIT 10")
                print(format_results(results))
            else:
                print(f"Unknown command: {cmd}")
            continue
        
        # Add to conversation
        conv.add_message(session_id, 'user', user_input)
        
        # Process via AI
        try:
            context = conv.get_conversation_summary(session_id)
            result = op.process(user_input, {'context': context})
            print(f"\n{result}")
            
            # Add response to history
            conv.add_message(session_id, 'assistant', result)
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nGoodbye!")

def format_results(rows):
    if not rows:
        return "No results."
    if len(rows) == 1:
        return "\n".join(f"{k}: {v}" for k, v in rows[0].items())
    
    headers = list(rows[0].keys())
    lines = [" | ".join(headers), "-" * len(" | ".join(headers))]
    for row in rows:
        lines.append(" | ".join(str(row.get(h, '')) for h in headers)
    return "\n".join(lines)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test chat loop**

```bash
python main.py
# Try: /items
# Try: /customers
# Try: "Show me all items"
```

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add main chat loop interface"
```

---

## Chunk 7: PDF Generation

### Task 9: Invoice PDF Generator

**Files:**
- Create: `utils/invoice_generator.py`

- [ ] **Step 1: Write utils/invoice_generator.py**

```python
"""Invoice PDF generator."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

def generate_invoice_pdf(invoice_no: str, customer_name: str, items: list, 
                     subtotal: float, tax_rate: float, tax_amount: float, 
                     total: float, due_date: str, output_path: str):
    """Generate PDF invoice."""
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=30)
    story.append(Paragraph(f"Invoice #{invoice_no}", title))
    story.append(Spacer(1, 0.2*inch))
    
    # Customer & Date info
    info = f"""
    <b>Customer:</b> {customer_name}<br/>
    <b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}<br/>
    <b>Due Date:</b> {due_date}
    """
    story.append(Paragraph(info, styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Items table
    table_data = [['Item', 'Qty', 'Unit Price', 'Amount']]
    for item in items:
        table_data.append([
            item.get('item_name', ''),
            str(item.get('quantity', 0)),
            f"${item.get('unit_price', 0):.2f}",
            f"${item.get('amount', 0):.2f}"
        ])
    
    t = Table(table_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3*inch))
    
    # Totals
    totals = f"""
    <b>Subtotal:</b> ${subtotal:.2f}<br/>
    <b>Tax ({tax_rate*100}%):</b> ${tax_amount:.2f}<br/>
    <b>Total:</b> ${total:.2f}
    """
    story.append(Paragraph(totals, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    return output_path
```

- [ ] **Step 2: Integrate with finalize**

```python
# Add to Operation.finalize_invoice() after creating invoice:
# Generate PDF
from utils.invoice_generator import generate_invoice_pdf

pdf_path = f"invoices/{invoice_no}.pdf"
os.makedirs("invoices", exist_ok=True)
generate_invoice_pdf(
    invoice_no, draft['customer_name'],
    items_data['items'], items_data['subtotal'],
    items_data['tax_rate'], items_data['tax_amount'],
    items_data['total'], draft['due_date'],
    pdf_path
)
```

- [ ] **Step 3: Commit**

```bash
git add utils/invoice_generator.py
git commit -m "feat: add PDF invoice generator"
```

---

## Completion Criteria

- [ ] Project runs with `python main.py`
- [ ] Can query customers, items via natural language
- [ ] Can create and finalize invoices
- [ ] Stock deducted on finalization
- [ ] PDF invoices generated
- [ ] Can switch LLM providers with `/switch`
- [ ] Context maintained across messages

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-28-erp-ai-plan.md`. Ready to execute?**