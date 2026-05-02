# Interactive Invoice Creation via Natural Language

## Overview

Enable users to create invoices through natural language conversation. The system guides the user through each step: selecting customer, adding items, and finalizing. Optimized for small language models (1B-3B parameters) and low-power devices.

## Goals

1. Simple LLM interaction - model only extracts entities, code controls flow
2. Voice input support for hands-free operation
3. Warehouse selection during invoice creation
4. Works on limited hardware (4GB RAM, basic CPU)

## User Flow

```
User: "create invoice for ABC Corporation"
    ↓
[CODE] Search customer by name (LIKE %ABC Corporation%)
    ↓
[If 1 result] Create draft, ask for items
[If multiple] Show list with IDs, ask "Select customer ID"
    ↓
User: "1" (or speaks selection)
    ↓
[CODE] Create draft, ask "What items? (item name and quantity)"
    ↓
User: "5 Widget A" or voice "five Widget A"
    ↓
[CODE] Search item by name, add to draft
[CODE] Show running total, ask "Anything else?"
    ↓
User: "No that's all" or "3 Gadget B"
    ↓
[If more items] Add to draft, repeat "Anything else?"
[If done] Finalize invoice, show summary
```

## Architecture

### Components

1. **InvoiceStateMachine** (new class in operations.py)
   - Manages invoice creation state per session
   - States: IDLE → SELECTING_CUSTOMER → SELECTING_WAREHOUSE → ADDING_ITEMS → FINALIZING
   - Stores: customer_id, warehouse_id, draft_id, items_count

2. **LLM Intent Extractor** (simple function)
   - Detects: create_invoice, add_item, select_option, done, cancel
   - Extracts: customer_name, item_name, quantity, option_id, warehouse_name

3. **Voice Input Handler** (existing tts.py + new speech-to-text)
   - Uses existing TTS for output
   - Adds STT (Speech-to-Text) for voice input via browser Web Speech API

4. **Conversation Context** (extend existing conversation.py)
   - Add: invoice_state, current_draft_id, current_warehouse_id

### Data Flow

```
User Input (text/voice)
    ↓
Intent Extractor (LLM or simple regex for small models)
    ↓
State Machine (determines next action based on state)
    ↓
Database Operations (search, create draft, add items, finalize)
    ↓
Response to User (text or voice)
```

## Database Schema

### Extend invoice_drafts table (already exists)
- Already has: session_id, customer_id, invoice_date, due_date, items_data, status

### New: warehouses table (already exists)
- id, warehouse_code, warehouse_name, location, is_active

## Key Functions

### 1. Intent Detection

```python
def detect_intent(user_input: str) -> dict:
    """Simple intent detection for small models."""
    # For tiny models, use keyword matching
    # For larger models, use LLM with short prompt
```

### 2. Customer Search

```python
def search_customer(name: str) -> list:
    """Search by name, return matches with ID."""
    query = "SELECT id, customer_code, customer_name FROM customers WHERE customer_name LIKE ?"
```

### 3. Item Search & Add

```python
def search_item(name: str) -> list:
    """Search by name, return matches."""
    query = "SELECT id, item_code, item_name, standard_selling_price FROM items WHERE item_name LIKE ?"

def add_item_to_draft(draft_id: int, item_id: int, quantity: int) -> dict:
    """Add item, return updated totals."""
```

### 4. Invoice Finalization

```python
def finalize_invoice(draft_id: int) -> dict:
    """Convert draft to final invoice, return summary."""
```

## Voice Input Implementation

### Browser Web Speech API
- Use `SpeechRecognition` API in web UI
- Simple button: "Hold to speak"
- Convert speech to text → send to chat endpoint

### Audio Feedback
- Use existing TTS for reading totals, confirmations
- Configurable: enable/disable in settings

## Warehouse Selection

### Flow:
```
After customer selected → "Select warehouse:"
1. Show available warehouses (from warehouses table)
2. User selects by ID or name
3. Default to warehouse_id = 1 if user doesn't specify
```

## Error Handling

1. **Customer not found**: "No customer found with that name. Try a different name or say 'list customers' to see all."
2. **Item not found**: "Item 'X' not found. Say 'list items' to see available items."
3. **Invalid quantity**: "Please provide a valid number for quantity."
4. **Draft expired**: "Invoice draft expired. Start again with 'create invoice'."
5. **Voice not recognized**: "Sorry, didn't catch that. Please try again or type your response."

## Performance Considerations

1. **Minimal LLM usage**: Only for entity extraction, not flow control
2. **Caching**: Cache item list for quick search
3. **Lazy loading**: Load warehouses only when needed
4. **Small responses**: Keep HTML tables minimal columns

## Testing Scenarios

1. Single customer match → direct to items
2. Multiple customers → show selection list
3. Single item match → auto-add
4. Multiple items → show selection list
5. Invalid quantity → ask again
6. Voice input → text fallback on failure
7. Cancel mid-flow → discard draft

## Out of Scope (Phase 1)

- Recurring invoices
- Invoice templates
- Partial payments
- Multi-currency
- PDF generation during flow (can add after finalize)