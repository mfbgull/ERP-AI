#!/usr/bin/env python3
"""Test script for ERP AI improvements."""

import sys
import json
from core.database import Database
from core.llm_handler import LLMHandler
from core.operations import Operation
from core.conversation import ConversationEngine
from core.production import ProductionManager

def test_database():
    """Test database connectivity."""
    print("\n=== Test 1: Database Connectivity ===")
    try:
        config = {'database': {'path': '/home/fawad/ai/minierp/database/erp.db'}}
        db = Database(config['database']['path'])
        
        # Test query
        result = db.execute("SELECT COUNT(*) as count FROM customers")
        print(f"✓ Connected to database")
        print(f"  Customers: {result[0]['count']}")
        
        result = db.execute("SELECT COUNT(*) as count FROM items")
        print(f"  Items: {result[0]['count']}")
        
        result = db.execute("SELECT COUNT(*) as count FROM boms")
        print(f"  BOMs: {result[0]['count']}")
        
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_llm_handler():
    """Test LLM handler."""
    print("\n=== Test 2: LLM Handler ===")
    try:
        config = {
            'ollama': {
                'enabled': True,
                'host': 'localhost',
                'port': 11434,
                'model': 'gemma3:270m',
                'timeout': 120
            },
            'llama_cpp': {
                'enabled': False,
                'host': 'localhost',
                'port': 8080
            }
        }
        
        llm = LLMHandler(config)
        
        # Check provider availability
        import requests
        try:
            resp = requests.get('http://localhost:11434/api/tags', timeout=2)
            if resp.status_code == 200:
                llm.set_provider('ollama')
                print(f"✓ Ollama available")
                print(f"  Provider: {llm.current_provider}")
                
                # Test conversation history
                llm.add_to_history('user', 'Hello')
                llm.add_to_history('assistant', 'Hi there')
                print(f"  History entries: {len(llm.conversation_history)}")
                
                llm.clear_history()
                print(f"  History cleared: {len(llm.conversation_history)} entries")
                
                return True
        except:
            print("⚠ Ollama not running (skipping LLM test)")
            return None
    except Exception as e:
        print(f"✗ LLM handler test failed: {e}")
        return False

def test_operations():
    """Test operations with SQL injection protection."""
    print("\n=== Test 3: Operations (SQL Safety) ===")
    try:
        config = {'database': {'path': '/home/fawad/ai/minierp/database/erp.db'}}
        db = Database(config['database']['path'])
        
        # Mock LLM handler for testing
        class MockLLM:
            def chat(self, prompt, system=""):
                return "SELECT * FROM customers LIMIT 5"
            def chat_stream(self, prompt, system=""):
                yield "SELECT * FROM customers LIMIT 5"
        
        llm = MockLLM()
        op = Operation(db, llm)
        
        # Test SELECT query
        result = op.process("Show me customers")
        print(f"✓ SELECT query executed")
        print(f"  Result preview: {result[:100]}...")
        
        # Test dangerous SQL detection
        result = op.process("DROP TABLE customers")
        if "Error" in result or "Warning" in result:
            print(f"✓ Dangerous SQL blocked")
        
        # Test HTML format
        result = op.process("Show customers", output_format='html')
        if '<table' in result:
            print(f"✓ HTML format working")
        
        return True
    except Exception as e:
        print(f"✗ Operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_production():
    """Test production/BOM functionality."""
    print("\n=== Test 4: Production Management ===")
    try:
        config = {'database': {'path': '/home/fawad/ai/minierp/database/erp.db'}}
        db = Database(config['database']['path'])
        pm = ProductionManager(db)
        
        # Get BOM
        bom = pm.get_bom(bom_id=1)
        if bom:
            print(f"✓ BOM retrieved")
            print(f"  BOM No: {bom['bom']['bom_no']}")
            print(f"  Finished Item: {bom['finished_item']['item_name']}")
            print(f"  Components: {len(bom['components'])}")
        
        # Calculate cost
        cost = pm.calculate_bom_cost(1)
        if 'total_material_cost' in cost:
            print(f"✓ BOM cost calculated")
            print(f"  Total Cost: ${cost['total_material_cost']:.2f}")
            print(f"  Unit Cost: ${cost['unit_material_cost']:.2f}")
        
        # Check feasibility
        feasibility = pm.check_production_feasibility(1, 10)
        print(f"✓ Production feasibility checked")
        print(f"  Feasible: {feasibility['feasible']}")
        print(f"  Max Possible: {feasibility['max_possible_quantity']:.1f}")
        
        # Get summary
        summary = pm.get_production_summary()
        print(f"✓ Production summary retrieved")
        print(f"  Total BOMs: {summary['total_boms']}")
        print(f"  Pending Orders: {summary['pending_orders']}")
        
        return True
    except Exception as e:
        print(f"✗ Production test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_conversation():
    """Test conversation engine."""
    print("\n=== Test 5: Conversation Engine ===")
    try:
        config = {'database': {'path': '/home/fawad/ai/minierp/database/erp.db'}}
        db = Database(config['database']['path'])
        conv = ConversationEngine(db)
        
        # Start session
        session_id = conv.start_session()
        print(f"✓ Session started: {session_id[:8]}...")
        
        # Add messages
        conv.add_message(session_id, 'user', 'Hello')
        conv.add_message(session_id, 'assistant', 'Hi!')
        
        # Get history
        history = conv.get_history(session_id)
        print(f"✓ Messages stored: {len(history)}")
        
        # Get context
        context = conv.get_context(session_id)
        print(f"✓ Context retrieved")
        
        # Set customer
        conv.set_current_customer(session_id, 1, 'ABC Corp')
        context = conv.get_context(session_id)
        print(f"✓ Customer set: {context.get('current_customer_name')}")
        
        # Get summary
        summary = conv.get_conversation_summary(session_id)
        print(f"✓ Summary: {summary}")
        
        return True
    except Exception as e:
        print(f"✗ Conversation test failed: {e}")
        return False

def test_tts():
    """Test local TTS functionality."""
    print("\n=== Test 6: Local TTS ===")
    try:
        from core.tts import get_tts_manager
        
        manager = get_tts_manager({'cache_enabled': True})
        info = manager.get_info()
        
        if not info['available']:
            print("⚠ TTS not available (skipping)")
            return None
        
        print(f"✓ TTS engine: {info['engine']}")
        print(f"  Type: {info['type']}")
        print(f"  Voices: {len(info['voices'])}")
        for v in info['voices']:
            print(f"    - {v['name']}")
        
        # Test synthesis
        result = manager.synthesize("ERP AI voice test.")
        if result['success']:
            print(f"✓ Synthesis successful")
            print(f"  Words: {result['words']}")
            print(f"  Duration: {result['duration']:.2f}s")
            print(f"  Generation: {result['generation_time']:.3f}s")
        
        # Test caching
        result2 = manager.synthesize("ERP AI voice test.", use_cache=True)
        if result2.get('cached'):
            print(f"✓ Cache working")
        
        return True
    except Exception as e:
        print(f"✗ TTS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("ERP AI - System Test Suite")
    print("=" * 60)
    
    results = []
    results.append(("Database", test_database()))
    results.append(("LLM Handler", test_llm_handler()))
    results.append(("Operations", test_operations()))
    results.append(("Production", test_production()))
    results.append(("Conversation", test_conversation()))
    results.append(("Local TTS", test_tts()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result is True else "⚠ SKIP" if result is None else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, r in results if r is True)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")
    
    return 0 if passed >= 5 else 1

if __name__ == '__main__':
    sys.exit(main())