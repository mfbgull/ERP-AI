import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from .database import Database
from .llm_handler import LLMHandler


class Operation:
    def __init__(self, db: Database, llm: LLMHandler):
        self.db = db
        self.llm = llm
    
    def process(self, user_message: str, context: dict = None, output_format: str = 'text') -> str:
        """Process user message with enhanced security and validation."""
        prompt = self._build_prompt(user_message, context)
        
        try:
            response = self.llm.chat(prompt, self._system_prompt())
            return self._handle_response(response, output_format)
        except RuntimeError as e:
            return f"Error: LLM connection failed - {e}"
    
    def process_stream(self, user_message: str, context: dict = None):
        """Process with streaming support."""
        prompt = self._build_prompt(user_message, context)
        
        try:
            for chunk in self.llm.chat_stream(prompt, self._system_prompt()):
                yield chunk
        except RuntimeError as e:
            yield f"Error: {e}"
    
    def _system_prompt(self) -> str:
        return """You are an ERP AI assistant for a manufacturing company.

When user asks to view data, write a SQL query.
Output format: SQL: <your query>

IMPORTANT SECURITY RULES:
- NEVER use DROP, DELETE, ALTER, TRUNCATE, or UPDATE without explicit confirmation
- Only use SELECT for read operations
- For INSERT/UPDATE/DELETE, explain what you'll do first and wait for confirmation
- Sanitize all inputs to prevent SQL injection
- Validate numeric inputs are actually numbers
- Check foreign key constraints before operations

ERP Context:
- Items can be raw materials, finished goods, or packaging
- BOM (Bill of Materials) defines production recipes
- Work orders consume materials per BOM
- Inventory movements track stock changes
- Always check stock availability before production

That's it. No other text needed."""
    
    def _build_prompt(self, message: str, context):
        """Build prompt with context and sanitization."""
        message = self._sanitize_input(message)
        
        prompt = message
        if context:
            if context.get('current_customer'):
                prompt = f"Current customer: {context['current_customer']}\n\n{prompt}"
            if context.get('context'):
                prompt = f"{context['context']}\n\n{prompt}"
        return prompt
    
    def _sanitize_input(self, text: str) -> str:
        """Basic input sanitization."""
        if not isinstance(text, str):
            return ""
        dangerous = [';', '--', '/*', '*/', '@@', 'char(', 'nchar(', 
                     'varchar(', 'nvarchar(', 'alter ', 'create ', 'drop ',
                     'exec ', 'execute ', 'insert ', 'delete ', 'update ',
                     'union ', 'waitfor ', 'xp_']
        for d in dangerous:
            text = text.replace(d, f'[{d.strip()}]')
        return text
    
    def _handle_response(self, response: str, output_format: str = 'text') -> str:
        """Handle LLM response with enhanced SQL parsing and validation."""
        if self._requires_confirmation(response):
            return response + "\n\n[CONFIRMATION REQUIRED] Please confirm with 'YES' to proceed."
        
        sql = self._extract_sql(response)
        
        if not sql:
            return response
        
        sql_type = self._get_sql_type(sql)
        
        if sql_type == 'SELECT':
            return self._execute_select(sql, output_format)
        elif sql_type in ('INSERT', 'UPDATE', 'DELETE'):
            return self._execute_write_with_validation(sql, sql_type)
        else:
            return f"Unsupported SQL type: {sql_type}\n\nResponse: {response}"
    
    def _requires_confirmation(self, response: str) -> bool:
        """Check if operation requires explicit confirmation."""
        write_keywords = ['INSERT INTO', 'UPDATE ', 'DELETE FROM', 
                         'DROP ', 'ALTER ', 'TRUNCATE ']
        return any(kw in response.upper() for kw in write_keywords)
    
    def _extract_sql(self, response: str) -> Optional[str]:
        """Extract SQL query from response."""
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        for line in response.strip().split('\n'):
            line = line.strip()
            if line.upper().startswith('SQL:'):
                return line[4:].strip()
        
        if response.strip().upper().startswith('SELECT'):
            return response.strip()
        
        return None
    
    def _get_sql_type(self, sql: str) -> str:
        """Determine SQL query type."""
        sql_upper = sql.strip().upper()
        if sql_upper.startswith('SELECT'):
            return 'SELECT'
        elif sql_upper.startswith('INSERT'):
            return 'INSERT'
        elif sql_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif sql_upper.startswith('DELETE'):
            return 'DELETE'
        else:
            return 'OTHER'
    
    def _execute_select(self, sql: str, output_format: str) -> str:
        """Execute SELECT query safely."""
        try:
            if not sql.strip().upper().startswith('SELECT'):
                return f"Error: Only SELECT queries allowed for read operations.\nQuery: {sql}"
            
            results = self.db.execute(sql)
            return self._format_results(results, output_format)
        except Exception as e:
            return f"Query Error: {e}\n\nSQL: {sql}"
    
    def _execute_write_with_validation(self, sql: str, sql_type: str) -> str:
        """Execute write operation with validation."""
        try:
            if 'DROP' in sql.upper() or 'ALTER' in sql.upper() or 'TRUNCATE' in sql.upper():
                return f"Error: Dangerous operation '{sql_type}' not allowed.\n\nSQL: {sql}"
            
            if sql_type in ('UPDATE', 'DELETE'):
                sql_upper = sql.upper()
                if 'WHERE' not in sql_upper and 'LIMIT' not in sql_upper:
                    return f"Warning: {sql_type} without WHERE clause detected.\nThis could affect all rows.\n\nSQL: {sql}\n\nPlease add a WHERE clause to limit the affected rows."
            
            rowid = self.db.execute_write(sql)
            
            if sql_type == 'INSERT':
                return f"✓ Insert successful. New row ID: {rowid}"
            else:
                return f"✓ {sql_type} successful. Rows affected: {rowid if rowid else 'N/A'}"
        except Exception as e:
            return f"{sql_type} Error: {e}\n\nSQL: {sql}"
    
    def _format_results(self, rows: list, format: str = 'text') -> str:
        """Format query results."""
        if not rows:
            return "No results found."
        
        if len(rows) == 1:
            row = rows[0]
            return "\n".join(f"{k}: {v}" for k, v in row.items())
        
        headers = list(rows[0].keys())
        
        if format == 'html':
            html = '<table class="data-table"><thead><tr>'
            for h in headers:
                html += f'<th>{h}</th>'
            html += '</tr></thead><tbody>'
            
            for row in rows:
                html += '<tr>'
                for h in headers:
                    html += f'<td>{row.get(h, "")}</td>'
                html += '</tr>'
            
            html += '</tbody></table>'
            return html + f' <span class="row-count">({len(rows)} rows)</span>'
        
        col_widths = {h: len(str(h)) for h in headers}
        for row in rows:
            for h in headers:
                col_widths[h] = max(col_widths[h], len(str(row.get(h, ''))))
        
        lines = []
        header_line = ' | '.join(str(h).ljust(col_widths[h]) for h in headers)
        lines.append(header_line)
        lines.append('-' * len(header_line))
        
        for row in rows:
            line = ' | '.join(str(row.get(h, '')).ljust(col_widths[h]) for h in headers)
            lines.append(line)
        
        lines.append(f"\n({len(rows)} rows)")
        return '\n'.join(lines)
    
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