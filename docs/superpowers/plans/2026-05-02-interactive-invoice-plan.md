# Interactive Invoice Creation via Natural Language

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable users to create invoices through natural language conversation with voice input support, optimized for small models and low-power devices.

**Architecture:** State Machine pattern - code controls flow, LLM only extracts simple entities (customer name, item name, quantity). Uses existing conversation.py for session state and invoice_drafts table for draft management.

**Tech Stack:** Python (Flask), SQLite, existing TTS for voice output, Web Speech API for voice input

---

## File Structure

```
core/
├── operations.py          # Add InvoiceStateMachine class
├── conversation.py        # Extend with invoice state fields
├── intent_extractor.py   # NEW - Simple intent detection
└── llm_handler.py        # Minor changes for short prompts

web.py                    # Add voice input endpoint
templates/
└── index.html            # Add voice input button
```

---

## Chunk 1: Core State Machine

### Task 1: Create InvoiceStateMachine Class

**Files:**
- Create: `core/invoice_state.py` (NEW)
- Modify: `core/operations.py` (import)

- [ ] **Step 1: Create invoice_state.py with state machine**

```python
# core/invoice_state.py
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class InvoiceState(Enum):
    IDLE = "idle"
    SELECTING_CUSTOMER = "selecting_customer"
    SELECTING_WAREHOUSE = "selecting_warehouse"
    ADDING_ITEMS = "adding_items"
    FINALIZING = "finalizing"

class InvoiceStateMachine:
    """Manages interactive invoice creation flow."""
    
    def __init__(self):
        self.state = InvoiceState.IDLE
        self.customer_id: Optional[int] = None
        self.customer_name: Optional[str] = None
        self.warehouse_id: int = 1
        self.draft_id: Optional[int] = None
        self.items_count: int = 0
        self.created_at = datetime.now()
    
    def reset(self):
        """Reset to initial state."""
        self.state = InvoiceState.IDLE
        self.customer_id = None
        self.customer_name = None
        self.warehouse_id = 1
        self.draft_id = None
        self.items_count = 0
        self.created_at = datetime.now()
    
    def is_expired(self) -> bool:
        """Check if draft has expired (30 minutes)."""
        if self.draft_id is None:
            return False
        return (datetime.now() - self.created_at) > timedelta(minutes=30)
    
    def to_dict(self) -> dict:
        return {
            'state': self.state.value,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'warehouse_id': self.warehouse_id,
            'draft_id': self.draft_id,
            'items_count': self.items_count
        }
```

- [ ] **Step 2: Add import to operations.py**

```python
# At top of core/operations.py, add:
from .invoice_state import InvoiceStateMachine, InvoiceState
```

- [ ] **Step 3: Test import works**

Run: `cd /home/fawad/ai/minierp/ERP-AI && .venv/bin/python -c "from core.operations import InvoiceStateMachine; print('OK')"`
Expected: OK (no output means success)

- [ ] **Step 4: Commit**

```bash
git add core/invoice_state.py core/operations.py
git commit -m "feat: add InvoiceStateMachine class for invoice flow control"
```

---

### Task 2: Extend ConversationEngine with Invoice State

**Files:**
- Modify: `core/conversation.py:14-26` (session initialization)
- Modify: `core/conversation.py` (add invoice state methods)

- [ ] **Step 1: Add invoice_state to session initialization**

In `core/conversation.py`, find `start_session` method and add to the session dict:
```python
'invoice_state': InvoiceStateMachine(),
```

- [ ] **Step 2: Add helper methods to ConversationEngine**

```python
def get_invoice_state(self, session_id: str) -> Optional[InvoiceStateMachine]:
    """Get invoice state for session."""
    ctx = self.sessions.get(session_id, {})
    return ctx.get('invoice_state')

def reset_invoice_state(self, session_id: str):
    """Reset invoice state for session."""
    if session_id in self.sessions:
        self.sessions[session_id]['invoice_state'] = InvoiceStateMachine()
```

- [ ] **Step 3: Test the changes**

Run: `cd /home/fawad/ai/minierp/ERP-AI && .venv/bin/python -c "from core.conversation import ConversationEngine; ce = ConversationEngine(None); sid = ce.start_session(); print(ce.get_invoice_state(sid).state.value)"`
Expected: idle

- [ ] **Step 4: Commit**

```bash
git add core/conversation.py
git commit -m "feat: extend ConversationEngine with invoice state"
```

---

## Chunk 2: Intent Extraction

### Task 3: Create Simple Intent Extractor

**Files:**
- Create: `core/intent_extractor.py` (NEW)

- [ ] **Step 1: Create intent_extractor.py**

```python
# core/intent_extractor.py
import re
from typing import Dict, Any, Optional, Tuple

class IntentExtractor:
    """Simple intent extraction optimized for small models."""
    
    # Keywords for intent detection
    CREATE_INVOICE_KEYWORDS = ['create invoice', 'new invoice', 'make invoice', 'generate invoice']
    ADD_ITEM_KEYWORDS = ['add', 'with', 'qty', 'quantity', 'pcs', 'pieces', 'units']
    DONE_KEYWORDS = ['done', 'finish', 'complete', 'no more', "that's all", 'nothing else', 'cancel']
    LIST_KEYWORDS = ['list', 'show', 'display', 'what']
    SELECT_KEYWORDS = ['select', 'choose', 'pick', 'option']
    
    @staticmethod
    def extract_intent(user_input: str) -> Dict[str, Any]:
        """Extract intent and entities from user input."""
        text = user_input.lower().strip()
        
        # Check for cancel/done
        if any(kw in text for kw in IntentExtractor.DONE_KEYWORDS):
            return {'intent': 'done', 'entities': {}}
        
        # Check for list commands
        if any(kw in text for kw in IntentExtractor.LIST_KEYWORDS):
            if 'customer' in text:
                return {'intent': 'list_customers', 'entities': {}}
            if 'item' in text:
                return {'intent': 'list_items', 'entities': {}}
            if 'warehouse' in text:
                return {'intent': 'list_warehouses', 'entities': {}}
        
        # Check for selection (e.g., "1", "option 2")
        selection = IntentExtractor._extract_number(text)
        if selection and any(kw in text for kw in IntentExtractor.SELECT_KEYWORDS):
            return {'intent': 'select_option', 'entities': {'option_id': selection}}
        if selection:
            return {'intent': 'select_option', 'entities': {'option_id': selection}}
        
        # Check for create invoice
        if any(kw in text for kw in IntentExtractor.CREATE_INVOICE_KEYWORDS):
            customer_name = IntentExtractor._extract_customer_name(text)
            return {'intent': 'create_invoice', 'entities': {'customer_name': customer_name}}
        
        # Check for add item (quantity + item name)
        quantity, item_name = IntentExtractor._extract_item_with_quantity(text)
        if quantity and item_name:
            return {'intent': 'add_item', 'entities': {'quantity': quantity, 'item_name': item_name}}
        
        # Check for warehouse selection
        if 'warehouse' in text or 'warehouse' in text:
            warehouse_name = IntentExtractor._extract_warehouse_name(text)
            return {'intent': 'select_warehouse', 'entities': {'warehouse_name': warehouse_name}}
        
        # Default to add_item attempt
        return {'intent': 'add_item', 'entities': {'item_name': text, 'quantity': 1}}
    
    @staticmethod
    def _extract_number(text: str) -> Optional[int]:
        """Extract first number from text."""
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])
        # Handle word numbers
        word_numbers = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }
        for word, num in word_numbers.items():
            if word in text:
                return num
        return None
    
    @staticmethod
    def _extract_customer_name(text: str) -> Optional[str]:
        """Extract customer name from create invoice command."""
        # Remove keywords
        for kw in IntentExtractor.CREATE_INVOICE_KEYWORDS:
            text = text.replace(kw, '')
        text = text.replace('for', '').replace('customer', '').strip()
        return text if text else None
    
    @staticmethod
    def _extract_item_with_quantity(text: str) -> Tuple[Optional[int], Optional[str]]:
        """Extract quantity and item name from text."""
        # Pattern: "5 Widget A" or "Widget A 5" or "five Widget A"
        quantity = IntentExtractor._extract_number(text)
        
        if quantity:
            # Remove the number from text to get item name
            for num in re.findall(r'\d+', text):
                text = text.replace(num, '', 1)
            word_numbers = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
            for word in word_numbers:
                text = text.replace(word, '', 1)
        
        item_name = text.strip()
        # Clean up common words
        for kw in ['add', 'with', 'qty', 'quantity', 'pcs', 'pieces', 'units']:
            item_name = item_name.replace(kw, '').strip()
        
        if item_name and len(item_name) > 1:
            return quantity, item_name
        return None, None
    
    @staticmethod
    def _extract_warehouse_name(text: str) -> Optional[str]:
        """Extract warehouse name from text."""
        text = text.replace('warehouse', '').replace('wh', '').strip()
        return text if text else None
```

- [ ] **Step 2: Test intent extraction**

Run: `cd /home/fawad/ai/minierp/ERP-AI && .venv/bin/python -c "
from core.intent_extractor import IntentExtractor
tests = [
    'create invoice for ABC Corporation',
    '5 Widget A',
    'done',
    '1',
    'list customers'
]
for t in tests:
    print(f'{t} -> {IntentExtractor.extract_intent(t)}')"`
Expected: Each test shows parsed intent

- [ ] **Step 3: Commit**

```bash
git add core/intent_extractor.py
git commit -m "feat: add simple intent extractor for small models"
```

---

## Chunk 3: Invoice Operations Integration

### Task 4: Add Invoice Flow Methods to Operations

**Files:**
- Modify: `core/operations.py` (add new methods)

- [ ] **Step 1: Add customer search method**

```python
def search_customers(self, name: str) -> list:
    """Search customers by name, return matches."""
    query = """
        SELECT id, customer_code, customer_name, contact_person, email, phone
        FROM customers 
        WHERE customer_name LIKE ? AND is_active = 1
        LIMIT 10
    """
    return self.db.execute(query, (f'%{name}%',))
```

- [ ] **Step 2: Add warehouse list method**

```python
def get_warehouses(self) -> list:
    """Get all active warehouses."""
    query = "SELECT id, warehouse_code, warehouse_name, location FROM warehouses WHERE is_active = 1"
    return self.db.execute(query)
```

- [ ] **Step 3: Add item search method**

```python
def search_items(self, name: str) -> list:
    """Search items by name, return matches."""
    query = """
        SELECT id, item_code, item_name, description, standard_selling_price, unit_of_measure
        FROM items 
        WHERE item_name LIKE ? AND is_active = 1
        LIMIT 10
    """
    return self.db.execute(query, (f'%{name}%',))
```

- [ ] **Step 4: Add invoice summary method**

```python
def get_invoice_summary(self, draft_id: int) -> dict:
    """Get current invoice draft summary."""
    draft = self.db.execute("SELECT * FROM invoice_drafts WHERE id = ?", (draft_id,))
    if not draft:
        return None
    
    items_data = json.loads(draft[0]['items_data'] or '{"items": []}')
    customer = self.db.execute("SELECT customer_name FROM customers WHERE id = ?", (draft[0]['customer_id'],))
    
    return {
        'draft_id': draft_id,
        'customer': customer[0]['customer_name'] if customer else 'Unknown',
        'items': items_data.get('items', []),
        'subtotal': items_data.get('subtotal', 0),
        'tax': items_data.get('tax_amount', 0),
        'total': items_data.get('total', 0),
        'item_count': len(items_data.get('items', []))
    }
```

- [ ] **Step 5: Test the methods**

Run: `cd /home/fawad/ai/minierp/ERP-AI && .venv/bin/python -c "
from core.database import Database
from core.operations import Operation
import yaml
with open('config.yaml') as f:
    cfg = yaml.safe_load(f)
db = Database(cfg['database']['path'])
op = Operation(db, None)
customers = op.search_customers('ABC')
print(f'Found {len(customers)} customers')
warehouses = op.get_warehouses()
print(f'Found {len(warehouses)} warehouses')
items = op.search_items('Widget')
print(f'Found {len(items)} items')"`
Expected: Shows counts

- [ ] **Step 6: Commit**

```bash
git add core/operations.py
git commit -m "feat: add invoice flow helper methods (search customers, items, warehouses)"
```

---

### Task 5: Create Invoice Flow Handler

**Files:**
- Modify: `core/operations.py` (add handle_invoice_flow method)

- [ ] **Step 1: Add handle_invoice_flow method**

```python
def handle_invoice_flow(self, user_input: str, session_id: str, conversation: Any) -> str:
    """Handle interactive invoice creation flow."""
    from core.intent_extractor import IntentExtractor
    from core.invoice_state import InvoiceState, InvoiceStateMachine
    
    # Get or create invoice state
    invoice_state = conversation.get_invoice_state(session_id)
    if invoice_state is None:
        invoice_state = InvoiceStateMachine()
        conversation.update_context(session_id, invoice_state=invoice_state)
    
    # Check if expired
    if invoice_state.is_expired():
        invoice_state.reset()
    
    # Extract intent
    intent_data = IntentExtractor.extract_intent(user_input)
    intent = intent_data['intent']
    entities = intent_data['entities']
    
    # State machine logic
    if invoice_state.state == InvoiceState.IDLE:
        if intent == 'create_invoice':
            customer_name = entities.get('customer_name')
            if not customer_name:
                return "Which customer is this invoice for? (Enter customer name)"
            
            customers = self.search_customers(customer_name)
            if not customers:
                return f"No customer found with '{customer_name}'. Try a different name or say 'list customers' to see all."
            
            if len(customers) == 1:
                # Single customer - proceed
                invoice_state.customer_id = customers[0]['id']
                invoice_state.customer_name = customers[0]['customer_name']
                invoice_state.state = InvoiceState.SELECTING_WAREHOUSE
                warehouses = self.get_warehouses()
                wh_list = '\n'.join([f"  {w['id']}. {w['warehouse_name']} ({w['warehouse_code']})" for w in warehouses])
                return f"Customer: {invoice_state.customer_name}\n\nSelect warehouse:\n{wh_list}\n\nOr say warehouse name (default: warehouse 1)"
            else:
                # Multiple customers - ask to select
                invoice_state.state = InvoiceState.SELECTING_CUSTOMER
                options = '\n'.join([f"  {c['id']}. {c['customer_name']} ({c['customer_code']})" for c in customers])
                return f"Multiple customers found:\n{options}\n\nEnter the customer ID to select:"
        
        elif intent == 'list_customers':
            customers = self.search_customers('')
            if not customers:
                return "No customers found."
            return "Available customers:\n" + '\n'.join([f"  {c['id']}. {c['customer_name']} ({c['customer_code']})" for c in customers[:10]])
        
        return "Say 'create invoice for [customer name]' to start a new invoice."
    
    elif invoice_state.state == InvoiceState.SELECTING_CUSTOMER:
        if intent == 'select_option':
            option_id = entities.get('option_id')
            customers = self.search_customers(invoice_state.customer_name or '')
            selected = next((c for c in customers if c['id'] == option_id), None)
            if not selected:
                return "Invalid selection. Enter a valid customer ID."
            
            invoice_state.customer_id = selected['id']
            invoice_state.customer_name = selected['customer_name']
            invoice_state.state = InvoiceState.SELECTING_WAREHOUSE
            warehouses = self.get_warehouses()
            wh_list = '\n'.join([f"  {w['id']}. {w['warehouse_name']} ({w['warehouse_code']})" for w in warehouses])
            return f"Customer: {invoice_state.customer_name}\n\nSelect warehouse:\n{wh_list}\n\nOr say warehouse name (default: warehouse 1)"
        
        return "Please enter the customer ID number."
    
    elif invoice_state.state == InvoiceState.SELECTING_WAREHOUSE:
        if intent == 'select_option':
            warehouse_id = entities.get('option_id')
            warehouses = self.get_warehouses()
            selected = next((w for w in warehouses if w['id'] == warehouse_id), None)
            if not selected:
                invoice_state.warehouse_id = 1
            else:
                invoice_state.warehouse_id = warehouse_id
        elif entities.get('warehouse_name'):
            warehouses = self.get_warehouses()
            selected = next((w for w in warehouses if entities['warehouse_name'].lower() in w['warehouse_name'].lower()), None)
            invoice_state.warehouse_id = selected['id'] if selected else 1
        
        # Create draft
        draft = self.create_invoice_draft(invoice_state.customer_id, invoice_state.customer_name, invoice_state.warehouse_id)
        invoice_state.draft_id = draft['draft_id']
        invoice_state.state = InvoiceState.ADDING_ITEMS
        
        return f"Invoice draft created for {invoice_state.customer_name}.\n\nWhat items? (Enter item name and quantity, e.g., '5 Widget A')"
    
    elif invoice_state.state == InvoiceState.ADDING_ITEMS:
        if intent == 'done':
            return self._finalize_invoice_flow(invoice_state, conversation, session_id)
        
        if intent == 'list_items':
            items = self.search_items('')
            if not items:
                return "No items found."
            return "Available items:\n" + '\n'.join([f"  {i['id']}. {i['item_name']} ({i['item_code']}) - ${i['standard_selling_price']}" for i in items[:10]])
        
        item_name = entities.get('item_name')
        quantity = entities.get('quantity', 1)
        
        if not item_name:
            return "Please provide item name and quantity (e.g., '5 Widget A')."
        
        items = self.search_items(item_name)
        if not items:
            return f"Item '{item_name}' not found. Say 'list items' to see available items."
        
        if len(items) == 1:
            # Single item - add directly
            self.add_item_to_draft(invoice_state.draft_id, items[0]['id'], quantity)
            invoice_state.items_count += 1
        else:
            # Multiple items - ask to select
            options = '\n'.join([f"  {i['id']}. {i['item_name']} ({i['item_code']}) - ${i['standard_selling_price']}" for i in items])
            return f"Multiple items found:\n{options}\n\nEnter the item ID to select:"
        
        # Show running total
        summary = self.get_invoice_summary(invoice_state.draft_id)
        return f"Added {quantity} x {items[0]['item_name']}\n\nCurrent total: ${summary['total']:.2f} ({summary['item_count']} items)\n\nAnything else? (Add more items or say 'done' to finalize)"
    
    return "Say 'create invoice for [customer name]' to start a new invoice."

def _finalize_invoice_flow(self, invoice_state, conversation, session_id) -> str:
    """Finalize the invoice draft."""
    if not invoice_state.draft_id:
        return "No invoice in progress. Say 'create invoice' to start."
    
    result = self.finalize_invoice(invoice_state.draft_id)
    invoice_state.reset()
    conversation.update_context(session_id, invoice_state=InvoiceStateMachine())
    
    return f"Invoice created successfully!\n\nInvoice No: {result['invoice_no']}\nCustomer: {result['customer_name']}\nTotal: ${result['total_amount']:.2f}\nStatus: {result['status']}"
```

- [ ] **Step 2: Test the flow handler**

Run: `cd /home/fawad/ai/minierp/ERP-AI && .venv/bin/python -c "
from core.database import Database
from core.operations import Operation
from core.conversation import ConversationEngine
import yaml
with open('config.yaml') as f:
    cfg = yaml.safe_load(f)
db = Database(cfg['database']['path'])
op = Operation(db, None)
conv = ConversationEngine(db)
sid = conv.start_session()
# Test create invoice
result = op.handle_invoice_flow('create invoice for ABC', sid, conv)
print(result[:200])"`
Expected: Shows customer selection or proceeds

- [ ] **Step 3: Commit**

```bash
git add core/operations.py
git commit -m "feat: add handle_invoice_flow for interactive invoice creation"
```

---

## Chunk 4: Web Integration

### Task 6: Integrate Invoice Flow with Chat API

**Files:**
- Modify: `web.py` (add invoice flow handling)

- [ ] **Step 1: Find chat endpoint in web.py**

Search for: `def api_chat` or `/api/chat`

- [ ] **Step 2: Modify chat endpoint to use invoice flow**

After getting the user message, add:
```python
# Check if invoice flow is active
invoice_state = conversation.get_invoice_state(current_session)
if invoice_state and invoice_state.state.value != 'idle':
    # Use invoice flow handler
    result = operations.handle_invoice_flow(user_message, current_session, conversation)
    # ... rest of existing code
```

- [ ] **Step 3: Test the integration**

Start server and test: `curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"message": "create invoice for ABC"}'`

- [ ] **Step 4: Commit**

```bash
git add web.py
git commit -m "feat: integrate invoice flow with chat API"
```

---

## Chunk 5: Voice Input Support

### Task 7: Add Voice Input to Web UI

**Files:**
- Modify: `templates/index.html` (add voice button)
- Create: Add voice handling JavaScript

- [ ] **Step 1: Add voice input button to HTML**

In the chat input area, add:
```html
<button id="voice-btn" type="button" class="btn-voice" title="Hold to speak">
    🎤
</button>
```

- [ ] **Step 2: Add JavaScript for voice input**

```javascript
// Voice input using Web Speech API
const voiceBtn = document.getElementById('voice-btn');
const chatInput = document.getElementById('chat-input');
let isRecording = false;

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    
    voiceBtn.addEventListener('mousedown', () => {
        isRecording = true;
        recognition.start();
        voiceBtn.classList.add('recording');
    });
    
    voiceBtn.addEventListener('mouseup', () => {
        isRecording = false;
        recognition.stop();
        voiceBtn.classList.remove('recording');
    });
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        chatInput.value = transcript;
        // Optionally auto-send
        // sendMessage();
    };
    
    recognition.onerror = (event) => {
        console.error('Voice recognition error:', event.error);
        voiceBtn.classList.remove('recording');
    };
} else {
    voiceBtn.style.display = 'none'; // Hide if not supported
}
```

- [ ] **Step 3: Add CSS for voice button**

```css
.btn-voice {
    background: #667eea;
    border: none;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    cursor: pointer;
    font-size: 18px;
}
.btn-voice.recording {
    background: #f56565;
    animation: pulse 1s infinite;
}
@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
}
```

- [ ] **Step 4: Test voice input**

Open browser, hold voice button, speak "create invoice for ABC"

- [ ] **Step 5: Commit**

```bash
git add templates/index.html
git commit -m "feat: add voice input support via Web Speech API"
```

---

## Chunk 6: Testing & Polish

### Task 8: End-to-End Testing

**Files:**
- Test all flows manually

- [ ] **Test 1: Single customer flow**

```
User: "create invoice for ABC Corporation"
System: Creates draft, asks for items
User: "5 Widget A"
System: Adds item, shows total
User: "done"
System: Finalizes invoice with summary
```

- [ ] **Test 2: Multiple customers selection**

```
User: "create invoice for Tech"
System: Shows multiple matches with IDs
User: "1"
System: Proceeds to warehouse selection
```

- [ ] **Test 3: Voice input**

```
User: Holds voice button, says "create invoice for XYZ"
System: Converts to text, processes
```

- [ ] **Test 4: Cancel flow**

```
User: "create invoice for ABC"
System: Creates draft
User: "cancel"
System: Cancels draft, returns to idle
```

- [ ] **Test 5: List commands**

```
User: "list customers" (during invoice flow)
System: Shows customer list
User: "list items"
System: Shows item list
```

- [ ] **Commit final**

```bash
git add -A
git commit -m "feat: complete interactive invoice creation with voice support"
git push
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | InvoiceStateMachine class | Create core/invoice_state.py |
| 2 | Extend ConversationEngine | Modify core/conversation.py |
| 3 | Intent Extractor | Create core/intent_extractor.py |
| 4 | Invoice helper methods | Modify core/operations.py |
| 5 | Invoice flow handler | Modify core/operations.py |
| 6 | Web API integration | Modify web.py |
| 7 | Voice input UI | Modify templates/index.html |
| 8 | End-to-end testing | Manual testing |

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-02-interactive-invoice-plan.md`. Ready to execute?**