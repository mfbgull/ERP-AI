import uuid
from flask import Flask, render_template, request, jsonify, send_file
from core.startup import run_startup, check_ollama, check_llama_cpp
from core.llm_handler import LLMHandler
from core.operations import Operation
from core.conversation import ConversationEngine
from core.database import Database

app = Flask(__name__)
app.config['SECRET_KEY'] = 'erp-ai-secret'

# Global state
config, db = None, None
llm_handler = None
operations = None
conversation = None
current_session = None


def init_app():
    global config, db, llm_handler, operations, conversation, current_session
    
    config, db = run_startup()
    llm_handler = LLMHandler(config)
    operations = Operation(db, llm_handler)
    conversation = ConversationEngine(db)
    current_session = conversation.start_session()
    
    # Auto-select provider
    if check_ollama(config['ollama']['host'], config['ollama']['port']):
        llm_handler.set_provider('ollama')
    elif check_llama_cpp(config['llama_cpp']['host'], config['llama_cpp']['port']):
        llm_handler.set_provider('llama_cpp')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400
    
    # Handle commands
    if user_message.startswith('/'):
        return handle_command(user_message)
    
    try:
        conversation.add_message(current_session, 'user', user_message)
        
        context = conversation.get_conversation_summary(current_session)
        result = operations.process(user_message, {
            'context': context,
            'current_customer': conversation.get_context(current_session).get('current_customer_name')
        })
        
        conversation.add_message(current_session, 'assistant', result)
        
        return jsonify({
            'response': result,
            'session': current_session[:8]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def handle_command(cmd):
    cmd = cmd[1:].lower()
    parts = cmd.split()
    action = parts[0] if parts else ''
    
    if action == 'customers':
        rows = db.execute('SELECT * FROM customers LIMIT 10')
        return jsonify({'response': format_results(rows)})
    elif action == 'items':
        rows = db.execute('SELECT * FROM items LIMIT 10')
        return jsonify({'response': format_results(rows)})
    elif action == 'invoices':
        rows = db.execute('SELECT * FROM invoices ORDER BY created_at DESC LIMIT 10')
        return jsonify({'response': format_results(rows)})
    elif action == 'switch':
        new = 'llama_cpp' if llm_handler.current_provider == 'ollama' else 'ollama'
        msg = llm_handler.switch_provider(new)
        return jsonify({'response': msg})
    elif action == 'model':
        rows = db.execute('SELECT * FROM items LIMIT 10')
        return jsonify({'response': format_results(rows)})
    else:
        return jsonify({'response': f'Unknown command: /{action}. Try /customers, /items, /invoices, /switch'})


@app.route('/api/customers', methods=['GET'])
def api_customers():
    rows = db.execute('SELECT * FROM customers WHERE is_active = 1')
    return jsonify(rows)


@app.route('/api/items', methods=['GET'])
def api_items():
    rows = db.execute('SELECT * FROM items WHERE is_active = 1')
    return jsonify(rows)


@app.route('/api/invoices', methods=['GET'])
def api_invoices():
    rows = db.execute('''
        SELECT i.*, c.customer_name 
        FROM invoices i 
        LEFT JOIN customers c ON i.customer_id = c.id 
        ORDER BY i.created_at DESC
    ''')
    return jsonify(rows)


@app.route('/api/invoice/<int:invoice_id>', methods=['GET'])
def api_invoice_detail(invoice_id):
    invoice = db.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
    if not invoice:
        return jsonify({'error': 'Not found'}), 404
    
    items = db.execute('''
        SELECT ii.*, i.item_name, i.item_code
        FROM invoice_items ii
        JOIN items i ON ii.item_id = i.id
        WHERE ii.invoice_id = ?
    ''', (invoice_id,))
    
    return jsonify({
        'invoice': invoice[0],
        'items': items
    })


@app.route('/api/invoice/<int:invoice_id>/pdf', methods=['GET'])
def api_invoice_pdf(invoice_id):
    from utils.invoice_generator import generate_invoice_pdf
    import os
    
    invoice = db.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
    if not invoice:
        return jsonify({'error': 'Not found'}), 404
    
    inv = invoice[0]
    items = db.execute('''
        SELECT ii.*, i.item_name
        FROM invoice_items ii
        JOIN items i ON ii.item_id = i.id
        WHERE ii.invoice_id = ?
    ''', (invoice_id,))
    
    items_list = [{
        'item_name': i['item_name'],
        'quantity': i['quantity'],
        'unit_price': i['unit_price'],
        'amount': i['amount']
    } for i in items]
    
    os.makedirs('invoices', exist_ok=True)
    pdf_path = f"invoices/{inv['invoice_no']}.pdf"
    
    generate_invoice_pdf(
        inv['invoice_no'],
        inv['customer_name'],
        items_list,
        inv['subtotal'],
        inv['tax_rate'],
        inv['tax_amount'],
        inv['total_amount'],
        inv['due_date'],
        pdf_path
    )
    
    return send_file(pdf_path, as_attachment=True)


@app.route('/api/conversation', methods=['GET'])
def api_conversation():
    hist = conversation.get_history(current_session, limit=20)
    return jsonify(hist)


def format_results(rows):
    if not rows:
        return "No results."
    if len(rows) == 1:
        return "\n".join(f"{k}: {v}" for k, v in rows[0].items())
    
    headers = list(rows[0].keys())
    header_line = " | ".join(headers)
    lines = [header_line, "-" * len(header_line)]
    for row in rows:
        lines.append(" | ".join(str(row.get(h, '')) for h in headers))
    return "\n".join(lines)


if __name__ == '__main__':
    init_app()
    print("\n🌐 Web UI: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)