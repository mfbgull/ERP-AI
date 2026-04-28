# ERP AI Assistant System - Product Requirements Document

## 1. Executive Summary

An AI-powered ERP system where users interact with the system entirely through natural language conversations. The AI assistant interprets instructions in plain English, executes database operations, generates documents (invoices, reports), and maintains context throughout conversations. The system uses local LLMs (Ollama or llama.cpp) for complete privacy and offline capability.

**Challenge Objective:** Discover where AI breaks when given complete database freedom with complex multi-step operations and context-dependent workflows.

---

## 2. System Overview

### 2.1 Core Components

1. **LLM Provider Layer** — Ollama and llama.cpp with mid-session switching
2. **Database Layer** — MySQL with 40+ tables for full ERP functionality
3. **AI Handler** — Interprets natural language and generates SQL/operations
4. **Conversation Engine** — Maintains session context and chat history
5. **Document Generator** — Creates PDFs for invoices and reports
6. **Validation Layer** — Catches errors before/after execution

### 2.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                           │
│            (CLI Chat / Web UI - Text-based)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 CONVERSATION LAYER                          │
│  • Session Management                                       │
│  • Chat History                                             │
│  • Context Window Management                                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    AI HANDLER LAYER                         │
│  • LLM Provider Abstraction (Ollama/llama.cpp)             │
│  • Prompt Engineering                                       │
│  • Mid-session Provider Switching                           │
│  • Response Parsing                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 OPERATION LAYER                             │
│  • SQL Generation                                           │
│  • Query Execution                                          │
│  • Data Validation                                          │
│  • Error Recovery                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 DATABASE LAYER                              │
│                  MySQL Database                             │
│        40+ Tables (Inventory, Sales, Purchases, etc)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Startup & Connection Management

### 3.1 Application Startup Flow

```
START
  ↓
[1] Connect to MySQL Database
    • Validate credentials
    • Test connection
    • Verify schema integrity
    ↓ (failure) → ERROR: Show setup instructions, exit
    ↓ (success)
[2] Detect LLM Providers
    • Scan localhost:11434 (Ollama)
    • Scan localhost:8000 (llama.cpp)
    • Check for custom IPs on local network (if configured)
    ↓
[3] Display Available Providers
    • List detected providers
    • Show available models (Ollama only)
    ↓
[4] User Selects Provider
    • If both running: user chooses
    • If only one: auto-select
    • If none: "Waiting for LLM" mode with retry (5 sec intervals)
    ↓
[5] Model Selection (Ollama only)
    • List available models
    • User selects (e.g., mistral, llama2)
    ↓
[6] Initialize LLM Handler
    • Test connection to selected provider
    • Verify model responsiveness
    ↓ (failure) → "LLM not responding" message + retry loop
    ↓ (success)
[7] Start Application UI
    • Load chat interface
    • Display system ready message
    • Ready for user input
```

### 3.2 LLM Provider Configuration

**Default Ports:**
- Ollama: `http://localhost:11434`
- llama.cpp: `http://localhost:8000`

**Configuration File (config.yaml):**
```yaml
database:
  host: localhost
  port: 3306
  user: root
  password: password
  database: erp_system

ollama:
  host: localhost
  port: 11434
  model: null  # Selected at startup
  enabled: true

llama_cpp:
  host: localhost
  port: 8000
  enabled: true

system:
  retry_timeout: 5  # seconds
  max_retries: 0    # 0 = infinite
  auto_retry: true
```

### 3.3 Mid-Session Provider Switching

**User can switch providers anytime during conversation:**

```
Current Provider: Ollama (Mistral)

User: "/switch llama.cpp"

AI:
  1. Save current session state
  2. Switch to llama.cpp
  3. Load full conversation history
  4. Continue with same context
  5. Respond: "Switched to llama.cpp. Ready to continue."
```

**Context Transfer:**
- Full conversation history transferred to new provider
- Current draft invoice (if any) preserved
- Session variables maintained
- LLM inherits all previous context

---

## 4. Database Schema

### 4.1 Core Tables

**Master Data:**
- `customers` — Customer information, credit limits, payment terms
- `suppliers` — Supplier details, payment terms, contact info
- `items` — Products/inventory, pricing, stock levels
- `warehouses` — Physical storage locations
- `users` — System users, roles, permissions
- `roles` — User roles and access levels
- `permissions` — Fine-grained permissions

**Inventory Management:**
- `stock_balances` — Per-warehouse stock levels (detail)
- `stock_movements` — All inventory movements with traceability
- `item_locations` — Item placement in warehouse racks

**Sales:**
- `quotations` — Customer quotations before conversion
- `quotation_items` — Line items in quotations
- `sales_orders` — Customer orders
- `sales_order_items` — Line items in sales orders
- `invoices` — Customer invoices
- `invoice_items` — Line items in invoices
- `invoice_drafts` — Draft invoices during creation
- `sales` — Simple sales transactions

**Purchasing:**
- `purchase_orders` — Supplier purchase orders
- `purchase_order_items` — Line items in POs
- `goods_receipts` — Receipt of goods from suppliers
- `goods_receipt_items` — Line items in receipts
- `purchases` — Simple purchase transactions

**Payments:**
- `payments` — Customer/supplier payments
- `payment_allocations` — Payment allocation to invoices
- `customer_ledger` — Customer transaction history
- `supplier_ledger` — Supplier transaction history

**Manufacturing:**
- `boms` — Bill of Materials
- `bom_items` — Raw materials in BOMs
- `work_orders` — Manufacturing orders
- `productions` — Production records
- `production_inputs` — Materials used in production
- `material_consumption` — Detailed consumption tracking

**Reports & Analytics:**
- `demand_forecasts` — AI-generated demand predictions
- `activity_log` — Audit trail of all operations

**Configuration:**
- `settings` — System-wide settings
- `tax_rates` — Tax rate definitions
- `payment_terms` — Payment term templates
- `expense_categories` — Expense categorization

### 4.2 Key Relationships

```
CUSTOMERS ──┬─→ INVOICES ──┬─→ INVOICE_ITEMS ──→ ITEMS
            │              │
            ├─→ SALES_ORDERS
            │
            ├─→ QUOTATIONS
            │
            ├─→ PAYMENTS
            │
            └─→ CUSTOMER_LEDGER

SUPPLIERS ──┬─→ PURCHASE_ORDERS ──→ PURCHASE_ORDER_ITEMS ──→ ITEMS
            │
            ├─→ GOODS_RECEIPTS ──→ GOODS_RECEIPT_ITEMS
            │
            ├─→ PAYMENTS
            │
            └─→ SUPPLIER_LEDGER

ITEMS ──────┬─→ STOCK_BALANCES ──→ WAREHOUSES
            │
            ├─→ STOCK_MOVEMENTS
            │
            ├─→ BOM_ITEMS
            │
            ├─→ PRODUCTION_INPUTS
            │
            └─→ INVOICE_ITEMS / PURCHASE_ORDER_ITEMS / SALES_ORDER_ITEMS
```

---

## 5. Core Features

### 5.1 Invoice Management

**Use Case: Creating an Invoice**

**Input:**
```
User: "Create an invoice for customer ABC"
```

**Process:**

1. **Customer Lookup**
   - Query: SELECT * FROM customers WHERE customer_name = 'ABC' OR customer_code = 'ABC'
   - Validate: Customer exists and is active

2. **Purchase History Analysis**
   - Query: Top 5 products by frequency from past invoices
   ```sql
   SELECT i.id, i.item_code, i.item_name, COUNT(*) as purchase_count
   FROM invoice_items ii
   JOIN invoices inv ON ii.invoice_id = inv.id
   JOIN items i ON ii.item_id = i.id
   WHERE inv.customer_id = ? AND inv.status != 'draft'
   GROUP BY i.id
   ORDER BY purchase_count DESC
   LIMIT 5;
   ```

3. **Stock Availability Check**
   - For each suggested product, query STOCK_BALANCES
   - Show available quantity for primary warehouse

4. **Draft Creation**
   ```sql
   INSERT INTO invoice_drafts 
   (session_id, customer_id, customer_name, invoice_date, due_date, warehouse_id, status)
   VALUES (?, ?, ?, TODAY(), TODAY()+payment_terms_days, ?, 'draft')
   ```

5. **AI Suggests Products**
   ```
   AI: "I found customer ABC Inc. Here's what they usually buy:
       • Product X (purchased 3 times, 50 units available)
       • Product Y (purchased 2 times, 25 units available)
       • Product Z (purchased 1 time, 40 units available)
       
       Would you like to add any of these to the invoice?"
   ```

**User Edits:**

```
User: "Add 5 units of X, 10 of Y, 3 of Z, remove 1 of Y"
```

**Process:**
1. Parse quantities
2. Validate stock availability
3. Update invoice_drafts.items_data (JSON)
4. Recalculate: subtotal, tax, total
5. Show updated preview

**Items Data Structure (JSON):**
```json
{
  "items": [
    {
      "item_id": 5,
      "item_code": "PROD-001",
      "item_name": "Product X",
      "quantity": 5,
      "unit_price": 1000.00,
      "amount": 5000.00
    },
    {
      "item_id": 8,
      "item_code": "PROD-002",
      "item_name": "Product Y",
      "quantity": 9,
      "unit_price": 500.00,
      "amount": 4500.00
    },
    {
      "item_id": 12,
      "item_code": "PROD-003",
      "item_name": "Product Z",
      "quantity": 3,
      "unit_price": 800.00,
      "amount": 2400.00
    }
  ],
  "subtotal": 11900.00,
  "tax_rate": 0.17,
  "tax_amount": 2023.00,
  "total": 13923.00,
  "discount": 0,
  "notes": ""
}
```

**Finalization:**

```
User: "Finalize this invoice"
```

**Process:**

1. **Final Validation**
   - Customer exists and active
   - All items exist
   - Stock available: `SUM(quantity) <= stock_balance FOR EACH item`
   - Total > 0

2. **Generate Invoice Number**
   - Format: INV-YYYYMMDD-XXXX
   - Query: `SELECT MAX(CAST(RIGHT(invoice_no, 4) AS UNSIGNED)) FROM invoices WHERE DATE(invoice_date) = TODAY()`
   - Increment and pad: INV-20260428-0001

3. **Create INVOICES Record**
   ```sql
   INSERT INTO invoices 
   (invoice_no, customer_id, invoice_date, due_date, status, total_amount, created_by, created_at)
   VALUES (?, ?, ?, ?, 'finalized', ?, ?, NOW())
   ```

4. **Create INVOICE_ITEMS Records**
   ```sql
   INSERT INTO invoice_items (invoice_id, item_id, quantity, unit_price, amount, tax_rate)
   VALUES (?, ?, ?, ?, ?, ?) -- repeat for each item
   ```

5. **Deduct Stock Immediately**
   ```sql
   UPDATE stock_balances 
   SET quantity = quantity - ? 
   WHERE item_id = ? AND warehouse_id = ?
   -- repeat for each item
   ```

6. **Recalculate ITEMS.current_stock**
   ```sql
   UPDATE items 
   SET current_stock = (SELECT SUM(quantity) FROM stock_balances WHERE item_id = ?)
   WHERE id = ?
   -- repeat for each modified item
   ```

7. **Generate PDF Invoice**
   - ReportLab or FPDF2
   - Include: invoice number, date, customer, items, total, due date, terms
   - Save to filesystem or database

8. **Archive Draft**
   ```sql
   UPDATE invoice_drafts SET status = 'archived' WHERE id = ?
   ```

9. **Confirm to User**
   ```
   AI: "✓ Invoice INV-20260428-0001 created
       Customer: ABC Inc
       Items: 3 products
       Total: 13,923
       Due Date: 2026-05-28
       PDF generated and ready for download"
   ```

**Undo/Rollback:**

```
User: "Undo the last action"

AI:
1. Track last operation in session
2. If draft: Can undo edits (just revert items_data)
3. If finalized: Cannot undo (would need credit note)
4. Show what was undone
```

---

### 5.2 Other ERP Operations

The AI can handle:

**Inventory Management:**
- "Add 100 units of product X to warehouse Y"
- "Show me low stock items" (items where current_stock < reorder_level)
- "What's the total value of inventory?"

**Purchasing:**
- "Create a purchase order from supplier ABC for product X (50 units)"
- "Show pending purchase orders"
- "Receive goods for PO-001"

**Sales:**
- "Show me sales for customer ABC in the last 30 days"
- "What's the revenue by product category?"

**Payments:**
- "Record a payment of $5,000 from customer ABC"
- "Show outstanding payments"

**Reports:**
- "Show me sales by customer this month"
- "What are my top 5 selling products?"
- "Generate a profit/loss report"

**Manufacturing:**
- "Create a production order for 50 units of finished product"
- "Record raw material consumption"

---

## 6. AI Interaction Model

### 6.1 Prompt Structure

**System Prompt:**
```
You are an ERP AI Assistant. You help users manage inventory, sales, purchases, invoices, and reports.

Your capabilities:
- Create/update/delete records in the database
- Generate SQL queries and execute them
- Create and finalize invoices
- Generate reports and PDFs
- Maintain conversation context about current operations

Rules:
1. Always validate data before operations
2. If stock insufficient, report and ask for confirmation
3. Maintain context: remember current customer, current draft, etc.
4. For ambiguous requests, ask clarifying questions
5. Show clear confirmations after operations
6. Use table schema knowledge to generate correct SQL
7. For multi-step operations, break them into sequential steps
8. If an operation fails, explain why and suggest solutions
```

### 6.2 Conversation Context

**Session Variables (maintained throughout conversation):**
```
{
  "session_id": "unique_session_key",
  "current_customer_id": null,
  "current_customer_name": null,
  "current_draft_id": null,
  "current_invoice_no": null,
  "last_operation": "create_invoice",
  "last_operation_id": 12345,
  "warehouse_id": 1,  # primary warehouse
  "user_id": 1,
  "provider": "ollama",  # current LLM provider
  "model": "mistral",
  "conversation_history": []
}
```

**Context Transfer When Switching Providers:**
- Save current session state
- Send full conversation history to new provider
- New provider inherits all context
- Continue seamlessly

### 6.3 Error Handling

**AI-Generated SQL Errors:**
```
User: "Show me customer with ID 99999"

AI attempts: SELECT * FROM customers WHERE id = 99999
Result: No rows

AI responds: "No customer found with ID 99999. 
            Would you like me to show all customers, 
            or search by name instead?"
```

**Stock Validation Errors:**
```
User: "Add 100 units of product X"

Stock check: Only 50 available

AI responds: "Product X has only 50 units available, 
            but you requested 100.
            Options:
            1. Add 50 units instead
            2. Add to purchase order for more stock
            3. Cancel this operation"
```

**Ambiguous Input:**
```
User: "Add product X"

AI: "I found 3 products with 'X' in the name:
    1. Product X-100
    2. Product X-200
    3. Product X-300
    
    Which one did you mean?"
```

---

## 7. Technical Architecture

### 7.1 Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.9+ |
| Backend Framework | Flask (lightweight) |
| Database | MySQL 5.7+ |
| LLM Integration | Ollama API, llama.cpp API |
| HTTP Requests | requests library |
| PDF Generation | ReportLab or FPDF2 |
| Config Management | PyYAML |
| Database Driver | mysql-connector-python or SQLAlchemy |

### 7.2 Project Structure

```
erp-ai-challenge/
├── config.yaml                 # Configuration file
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
│
├── core/
│   ├── startup.py             # Startup sequence & validation
│   ├── config.py              # Config loading & LLM detection
│   ├── database.py            # MySQL connection & queries
│   ├── llm_handler.py         # LLM provider abstraction
│   ├── conversation.py        # Session & context management
│   ├── operations.py          # Business logic (invoice, etc)
│   └── validator.py           # Data validation
│
├── llm/
│   ├── prompts.py             # System prompts & templates
│   ├── parser.py              # Parse LLM responses
│   └── context_builder.py     # Build context for LLM
│
├── database/
│   ├── schema.sql             # Create tables script
│   ├── migrations/            # Database migrations
│   └── queries.py             # Reusable SQL queries
│
├── utils/
│   ├── invoice_generator.py   # PDF invoice creation
│   ├── report_generator.py    # PDF report creation
│   ├── logger.py              # Logging setup
│   └── helpers.py             # Utility functions
│
├── templates/
│   └── index.html             # Web UI (optional)
│
└── tests/
    ├── test_invoice.py
    ├── test_llm.py
    └── test_database.py
```

### 7.3 Request Flow

```
USER INPUT (plain English)
    ↓
┌─ CONVERSATION LAYER ─────────────────────────────┐
│ 1. Extract message                               │
│ 2. Load session context (customer, draft, etc)   │
│ 3. Build message history                         │
└──────────────────┬────────────────────────────────┘
                   ↓
        ┌─ LLM HANDLER LAYER ──────────────┐
        │ 1. Build system prompt           │
        │ 2. Add conversation history      │
        │ 3. Add context variables         │
        │ 4. Send to LLM (Ollama/llama.cpp)│
        │ 5. Parse response                │
        └──────────────┬────────────────────┘
                       ↓
          ┌─ OPERATION LAYER ────────────────┐
          │ 1. Extract SQL/operations        │
          │ 2. Validate syntax               │
          │ 3. Validate permissions          │
          │ 4. Execute on database           │
          │ 5. Handle errors gracefully      │
          │ 6. Return results                │
          └──────────────┬────────────────────┘
                         ↓
            ┌─ RESPONSE LAYER ──────────────┐
            │ 1. Format results              │
            │ 2. Update session context      │
            │ 3. Log operation               │
            │ 4. Return to user              │
            └────────────────────────────────┘
                         ↓
                  USER RESPONSE
```

### 7.4 Database Connection

**MySQL Connection:**
```python
import mysql.connector

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password",
    database="erp_system",
    autocommit=False  # Use transactions
)
```

**Transaction Handling:**
```python
try:
    cursor.execute(sql1)
    cursor.execute(sql2)
    cursor.execute(sql3)
    connection.commit()  # All succeed or all fail
except Exception as e:
    connection.rollback()  # Undo all changes
    raise
```

### 7.5 LLM Integration

**Ollama:**
```python
def call_ollama(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        },
        timeout=60
    )
    return response.json()["response"]
```

**llama.cpp:**
```python
def call_llama_cpp(prompt):
    response = requests.post(
        "http://localhost:8000/completion",
        json={
            "prompt": prompt,
            "n_predict": 500,
            "temperature": 0.7
        },
        timeout=60
    )
    return response.json()["content"]
```

---

## 8. Testing Strategy

### 8.1 Phased Testing

**Phase 1: Basic Operations (Week 1)**
- [x] LLM detection and connection
- [x] Database connection validation
- [x] Simple queries: "Show all customers"
- [x] Customer lookup: "Find customer ABC"
- [x] Product search: "Search for product X"

**Phase 2: Invoice Creation (Week 2)**
- [ ] Create draft invoice
- [ ] Add items to draft
- [ ] Modify quantities
- [ ] Calculate totals correctly
- [ ] Finalize and generate PDF
- [ ] Stock deduction verification

**Phase 3: Complex Operations (Week 3)**
- [ ] Multi-step workflows
- [ ] Provider switching mid-session
- [ ] Error recovery
- [ ] Undo/rollback
- [ ] Context maintenance

**Phase 4: Edge Cases & Breaking Points (Week 4)**
- [ ] Large data sets
- [ ] Concurrent operations
- [ ] Ambiguous instructions
- [ ] Invalid data
- [ ] Provider timeout/failure

### 8.2 Failure Scenarios to Test

1. **SQL Generation Quality**
   - Does AI generate syntactically correct SQL?
   - Does it handle complex joins?
   - Does it use correct WHERE conditions?

2. **Arithmetic Accuracy**
   - Invoice totals calculated correctly?
   - Tax amounts correct?
   - Stock quantities accurate?

3. **Context Maintenance**
   - Does AI remember current customer across messages?
   - Does AI maintain draft state during edits?
   - Does full history transfer when switching providers?

4. **Stock Management**
   - Stock deducted only after finalization?
   - Correct warehouse deducted from?
   - current_stock field updated correctly?

5. **Error Handling**
   - Graceful errors for invalid customers?
   - Clear feedback for insufficient stock?
   - Proper rollback on failures?

6. **Provider Switching**
   - Context preserved when switching?
   - Conversation history transferred?
   - Same accuracy with different providers?

---

## 9. Success Criteria

### 9.1 Functional Success

- [x] System starts successfully with auto-detection
- [x] User can create complete invoices through conversation
- [x] Invoices are properly created in database
- [x] Stock is correctly deducted
- [x] PDF invoices generated
- [x] User can switch providers mid-session
- [x] Context maintained across provider switches

### 9.2 Testing Success

- [x] Identified where AI struggles
- [x] Documented error patterns
- [x] Found edge cases that break
- [x] Identified improvements needed

### 9.3 Performance Targets

- LLM response time: < 10 seconds per operation
- Database operations: < 100ms
- PDF generation: < 5 seconds
- Context transfer on switch: < 2 seconds

---

## 10. Known Risks & Challenges

### 10.1 LLM Reliability

**Risk:** Local LLMs (Mistral 7B) may generate incorrect SQL for complex queries

**Mitigation:**
- Validate SQL syntax before execution
- Use prepared statements
- Comprehensive error logging
- Prompt engineering to improve accuracy

### 10.2 Transaction Integrity

**Risk:** Multi-step operations (create invoice, deduct stock, update summary) could partially fail

**Mitigation:**
- Use MySQL transactions (BEGIN/COMMIT/ROLLBACK)
- All-or-nothing operations
- Clear error messaging to user

### 10.3 Context Window Limitations

**Risk:** Long conversations exceed LLM context window

**Mitigation:**
- Summarize old messages
- Keep context variables in session (don't send full history)
- Reset context periodically

### 10.4 Stock Overselling

**Risk:** Race conditions with concurrent operations

**Mitigation:**
- Check stock immediately before finalization
- Use database locks if needed
- Clear error message if stock insufficient

### 10.5 JSON Data Corruption

**Risk:** AI incorrectly modifies invoice_drafts.items_data JSON

**Mitigation:**
- Validate JSON syntax after modification
- Use JSON schema validation
- Fallback to previous version if invalid

---

## 11. Future Enhancements (Post-Challenge)

1. **Multi-provider comparison** — Test same task on different LLMs simultaneously
2. **Automated testing** — Generate test scenarios and measure accuracy
3. **Fine-tuned models** — Train models specifically for ERP tasks
4. **Guardrails** — Add safety rails to prevent dangerous operations
5. **API layer** — Build REST API for external integrations
6. **Web UI** — Professional interface instead of CLI
7. **Mobile app** — Mobile access to ERP
8. **Analytics** — Track AI accuracy, common failures, performance metrics
9. **Real-time collaboration** — Multiple users in same ERP simultaneously
10. **Audit trail** — Complete versioning of all changes

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **Draft** | Unsaved invoice in progress |
| **Session** | User's interaction instance with system |
| **Context** | Current state (customer, draft, etc) |
| **Stock Balance** | Inventory quantity per warehouse |
| **Finalize** | Convert draft to permanent invoice |
| **Provider** | LLM source (Ollama or llama.cpp) |
| **Validation** | Check data correctness before execution |
| **Rollback** | Undo database changes on error |
| **PDFs** | Invoice/report documents |
| **Mid-session switching** | Change LLM provider during conversation |

---

## 13. Appendix: Database Migration

### 13.1 From SQLite to MySQL

```sql
-- Create database
CREATE DATABASE erp_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE erp_system;

-- Import schema (provided in schema.sql)
-- Adjust data types as needed (INTEGER → INT, BOOLEAN → TINYINT, etc)

-- Create indexes for performance
CREATE INDEX idx_customers_code ON customers(customer_code);
CREATE INDEX idx_items_code ON items(item_code);
CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoice_items_invoice ON invoice_items(invoice_id);
CREATE INDEX idx_stock_balances ON stock_balances(item_id, warehouse_id);
```

### 13.2 Required User & Permissions

```sql
-- Create application user
CREATE USER 'erp_user'@'localhost' IDENTIFIED BY 'secure_password';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON erp_system.* TO 'erp_user'@'localhost';
FLUSH PRIVILEGES;
```

---

## 14. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-28 | Claude | Initial PRD |

---

**End of Document**
