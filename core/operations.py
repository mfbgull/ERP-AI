import json
from datetime import datetime, timedelta
from .database import Database
from .llm_handler import LLMHandler


class Operation:
    def __init__(self, db: Database, llm: LLMHandler):
        self.db = db
        self.llm = llm
    
    def process(self, user_message: str, context: dict = None) -> str:
        prompt = self._build_prompt(user_message, context)
        response = self.llm.chat(prompt, self._system_prompt())
        return self._handle_response(response)
    
    def _system_prompt(self) -> str:
        return """You are an ERP AI Assistant. You help users manage invoices, inventory, customers, and sales.

Schema:
- customers(id, customer_code, customer_name, email, is_active)
- items(id, item_code, item_name, category, unit_price, current_stock)
- warehouses(id, warehouse_code, warehouse_name)
- stock_balances(item_id, warehouse_id, quantity)
- invoices(id, invoice_no, customer_id, total_amount, status)
- invoice_items(invoice_id, item_id, quantity, unit_price)
- invoice_drafts(id, customer_id, items_data, status)

Rules:
1. Use parameterized queries
2. Return results in a user-friendly format
3. If no data found, say so clearly

Output format:
- SQL: <the SQL query to execute>
- Then execute and return results"""
    
    def _build_prompt(self, message: str, context):
        prompt = message
        if context:
            if context.get('current_customer'):
                prompt = f"Current customer: {context['current_customer']}\n\n{prompt}"
        return prompt
    
    def _handle_response(self, response: str) -> str:
        lines = response.strip().split('\n')
        sql = None
        
        for line in lines:
            if line.startswith('SQL:'):
                sql = line[4:].strip()
                break
        
        if not sql:
            return response
        
        try:
            if sql.strip().upper().startswith('SELECT'):
                results = self.db.execute(sql)
                return self._format_results(results)
            else:
                rowid = self.db.execute_write(sql)
                return f"Operation completed. Rows affected: {rowid}"
        except Exception as e:
            return f"Error: {e}\n\nResponse: {response}"
    
    def _format_results(self, rows: list) -> str:
        if not rows:
            return "No results found."
        
        if len(rows) == 1:
            row = rows[0]
            return "\n".join(f"{k}: {v}" for k, v in row.items())
        
        headers = list(rows[0].keys())
        header_line = " | ".join(headers)
        separator = "-" * len(header_line)
        
        lines = [header_line, separator]
        for row in rows:
            lines.append(" | ".join(str(row.get(h, '')) for h in headers))
        
        return "\n".join(lines) + f"\n\n({len(rows)} rows)"
    
    def create_invoice_draft(self, customer_id: int, customer_name: str, warehouse_id: int = 1) -> dict:
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
        item = self.db.execute("SELECT * FROM items WHERE id = ?", (item_id,))[0]
        draft = self.db.execute("SELECT * FROM invoice_drafts WHERE id = ?", (draft_id,))[0]
        
        items_data = json.loads(draft['items_data'] or '{"items": [], "subtotal": 0, "tax_rate": 0.17, "tax_amount": 0, "total": 0}')
        if 'items' not in items_data:
            items_data = {'items': [], 'subtotal': 0, 'tax_rate': 0.17, 'tax_amount': 0, 'total': 0}
        
        amount = item['unit_price'] * quantity
        items_data['items'].append({
            'item_id': item_id,
            'item_code': item['item_code'],
            'item_name': item['item_name'],
            'quantity': quantity,
            'unit_price': item['unit_price'],
            'amount': amount
        })
        
        subtotal = sum(i['amount'] for i in items_data['items'])
        tax_rate = items_data.get('tax_rate', 0.17)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        items_data['subtotal'] = subtotal
        items_data['tax_amount'] = tax_amount
        items_data['total'] = total
        
        query = "UPDATE invoice_drafts SET items_data = ?, subtotal = ?, tax_amount = ?, total = ? WHERE id = ?"
        self.db.execute_write(query, (json.dumps(items_data), subtotal, tax_amount, total, draft_id))
        
        return items_data
    
    def finalize_invoice(self, draft_id: int, user_id: int = 1) -> dict:
        draft = self.db.execute("SELECT * FROM invoice_drafts WHERE id = ?", (draft_id,))[0]
        
        items_data = json.loads(draft['items_data'] or '{"items": []}')
        
        if not items_data.get('items'):
            raise ValueError("Draft has no items")
        
        today = datetime.now().strftime('%Y%m%d')
        last_inv = self.db.execute(
            "SELECT MAX(CAST(RIGHT(invoice_no, 4) AS INTEGER)) as last_no FROM invoices WHERE invoice_no LIKE ?",
            (f"INV-{today}-%",)
        )
        next_num = (last_inv[0]['last_no'] or 0) + 1
        invoice_no = f"INV-{today}-{next_num:04d}"
        
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
            
            self._deduct_stock(item['item_id'], item['quantity'], draft['warehouse_id'])
        
        self.db.execute_write("UPDATE invoice_drafts SET status = 'finalized' WHERE id = ?", (draft_id,))
        
        return {
            'invoice_no': invoice_no,
            'invoice_id': invoice_id,
            'total': items_data['total']
        }
    
    def _deduct_stock(self, item_id: int, quantity: int, warehouse_id: int):
        self.db.execute_write("""
        UPDATE stock_balances 
        SET quantity = quantity - ?
        WHERE item_id = ? AND warehouse_id = ?
        """, (quantity, item_id, warehouse_id))
        
        self.db.execute_write("""
        UPDATE items SET current_stock = (
            SELECT SUM(quantity) FROM stock_balances WHERE item_id = ?
        ) WHERE id = ?
        """, (item_id, item_id))