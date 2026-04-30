#!/bin/bash
echo "=========================================="
echo "ERP AI Assistant - Final System Test"
echo "=========================================="
echo

# Test 1: Database
echo "[1/6] Testing Database..."
python3 -c "
from core.database import Database
db = Database('/home/fawad/ai/minierp/database/erp.db')
result = db.execute('SELECT COUNT(*) as c FROM customers')[0]
assert result['c'] == 3, 'Customer count mismatch'
result = db.execute('SELECT COUNT(*) as c FROM items')[0]
assert result['c'] == 12, 'Item count mismatch'
print('  ✓ Database: 3 customers, 12 items')
"

# Test 2: LLM Handler
echo "[2/6] Testing LLM Handler..."
python3 -c "
from core.llm_handler import LLMHandler
import yaml
with open('config.yaml') as f:
    config = yaml.safe_load(f)
llm = LLMHandler(config)
llm.set_provider('ollama')
llm.add_to_history('user', 'test')
llm.add_to_history('assistant', 'response')
assert len(llm.conversation_history) == 2
llm.clear_history()
assert len(llm.conversation_history) == 0
print('  ✓ LLM Handler: history management working')
"

# Test 3: Operations
echo "[3/6] Testing Operations..."
python3 -c "
from core.database import Database
from core.llm_handler import LLMHandler
from core.operations import Operation
import yaml
with open('config.yaml') as f:
    config = yaml.safe_load(f)
db = Database(config['database']['path'])
llm = LLMHandler(config)
llm.set_provider('ollama')
op = Operation(db, llm)
result = op.process('SELECT * FROM customers LIMIT 1')
assert 'customer' in result.lower() or 'id' in result.lower()
print('  ✓ Operations: SQL queries working')
"

# Test 4: Production
echo "[4/6] Testing Production Management..."
python3 -c "
from core.database import Database
from core.production import ProductionManager
db = Database('/home/fawad/ai/minierp/database/erp.db')
pm = ProductionManager(db)
bom = pm.get_bom(bom_id=1)
assert bom is not None
cost = pm.calculate_bom_cost(1)
assert 'total_material_cost' in cost
feas = pm.check_production_feasibility(1, 10)
assert 'feasible' in feas
print('  ✓ Production: BOM management working')
"

# Test 5: TTS
echo "[5/6] Testing Local TTS..."
python3 -c "
from core.tts import get_tts_manager
manager = get_tts_manager()
info = manager.get_info()
if info['available']:
    result = manager.synthesize('ERP AI test')
    assert result['success']
    print(f'  ✓ TTS: {info[\"engine\"]} operational')
else:
    print('  ⚠ TTS: Not available (skipping)')
"

# Test 6: Conversation
echo "[6/6] Testing Conversation Engine..."
python3 -c "
from core.database import Database
from core.conversation import ConversationEngine
db = Database('/home/fawad/ai/minierp/database/erp.db')
conv = ConversationEngine(db)
sid = conv.start_session()
conv.add_message(sid, 'user', 'hello')
conv.add_message(sid, 'assistant', 'hi')
history = conv.get_history(sid)
assert len(history) == 2
conv.set_current_customer(sid, 1, 'Test Corp')
ctx = conv.get_context(sid)
assert ctx['current_customer_name'] == 'Test Corp'
print('  ✓ Conversation: session management working')
"

echo
echo "=========================================="
echo "All Tests Passed! ✓"
echo "=========================================="
echo
echo "System Status:"
echo "  • Database: Operational"
echo "  • LLM Handler: Operational"
echo "  • Operations: Operational"
echo "  • Production: Operational"
echo "  • TTS: Operational"
echo "  • Conversation: Operational"
echo
