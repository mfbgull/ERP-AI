import json
import re
import time
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

CRITICAL RULE - ALWAYS USE SELECT *:
When user asks to "show", "list", "display", "view" data or "show all" or "get all" - you MUST use SELECT * to return ALL columns.
NEVER use "SELECT id" alone - that is useless and frustrates users.
User wants to SEE the actual data, not just IDs.

IMPORTANT SECURITY RULES:
- NEVER use DROP, DELETE, ALTER, TRUNCATE, or UPDATE without explicit confirmation
- Only use SELECT for read operations
- For INSERT/UPDATE/DELETE, explain what you'll do first and wait for confirmation
- Sanitize all inputs to prevent SQL injection
- Validate numeric inputs are actually numbers
- Check foreign key constraints before operations

DATABASE SCHEMA - USE THESE EXACT COLUMN NAMES:

# Master Data
- users: id, username, email, password_hash, full_name, role, is_active, created_at, updated_at
- settings: id, key, value, description, updated_at

# Inventory & Warehouse
- items: id, item_code, item_name, description, category, unit_of_measure, current_stock, reorder_level, standard_cost, standard_selling_price, is_raw_material, is_finished_good, is_purchased, is_manufactured, is_active, created_by, created_at, updated_at
- warehouses: id, warehouse_code, warehouse_name, location, is_active, created_at
- stock_movements: id, movement_no, item_id, warehouse_id, movement_type, quantity, unit_cost, reference_doctype, reference_docno, remarks, movement_date, created_by, created_at
- stock_balances: id, item_id, warehouse_id, quantity, last_updated

# Suppliers & Procurement
- suppliers: id, supplier_code, supplier_name, contact_person, email, phone, address, payment_terms, is_active, created_at, updated_at
- purchase_orders: id, po_no, supplier_id, po_date, expected_delivery_date, status, total_amount, notes, warehouse_id, created_by, created_at, updated_at
- purchase_order_items: id, po_id, item_id, quantity, received_quantity, unit_price, amount
- goods_receipts: id, receipt_no, po_id, receipt_date, warehouse_id, remarks, created_by, created_at
- goods_receipt_items: id, receipt_id, po_item_id, item_id, received_quantity

# Customers & Sales
- customers: id, customer_code, customer_name, contact_person, email, phone, billing_address, shipping_address, payment_terms, is_active, created_at, updated_at, credit_limit, current_balance, opening_balance, payment_terms_days
- sales_orders: id, so_no, customer_id, so_date, delivery_date, status, total_amount, notes, warehouse_id, created_by, created_at, updated_at
- sales_order_items: id, so_id, item_id, quantity, delivered_quantity, unit_price, amount

# Invoices & Payments
- invoices: id, invoice_no, customer_id, so_id, invoice_date, due_date, status, total_amount, paid_amount, balance_amount, notes, created_by, created_at, updated_at, discount_scope, discount_type, discount_value, terms
- invoice_items: id, invoice_id, item_id, quantity, unit_price, amount, tax_rate, discount_type, discount_value
- payments: id, payment_no, customer_id, invoice_id, payment_date, amount, payment_method, reference_no, notes, created_by, created_at
- payment_allocations: id, payment_id, invoice_id, amount, created_at

# Manufacturing
- boms: id, bom_no, bom_name, finished_item_id, quantity, description, is_active, created_by, created_at, updated_at
- bom_items: id, bom_id, item_id, quantity, created_at
- work_orders: id, wo_no, bom_id, finished_item_id, planned_quantity, produced_quantity, status, start_date, expected_completion_date, actual_completion_date, warehouse_id, notes, created_by, created_at, updated_at
- material_consumption: id, wo_id, item_id, consumed_quantity, consumption_date, created_by, created_at
- productions: id, production_no, output_item_id, output_quantity, warehouse_id, production_date, remarks, created_by, created_at, updated_at, bom_id, raw_materials_warehouse_id
- production_inputs: id, production_id, item_id, quantity, warehouse_id

# Expenses
- expenses: id, expense_no, expense_category, description, amount, expense_date, payment_method, reference_no, vendor_name, project, status, created_by, created_at, updated_at
- expense_categories: id, category_name, description, is_active, created_at, updated_at

# Ledgers
- customer_ledger: id, customer_id, transaction_date, transaction_type, reference_no, debit, credit, balance, description, created_at
- supplier_ledger: id, supplier_id, transaction_date, transaction_type, reference_no, debit, credit, balance, description, created_at
- activity_log: id, user_id, action, entity_type, entity_id, description, created_at, log_level, ip_address, user_agent, metadata, duration_ms

# Other
- purchases: id, purchase_no, item_id, warehouse_id, quantity, unit_cost, total_cost, supplier_name, purchase_date, invoice_no, remarks, created_by, created_at, updated_at
- sales: id, sale_no, item_id, warehouse_id, quantity, unit_price, total_amount, customer_name, sale_date, invoice_no, remarks, created_by, created_at, updated_at
- invoice_drafts: id, session_id, customer_id, invoice_date, due_date, terms, notes, items_data, status, created_at, updated_at, expires_at
- tax_rates: id, name, rate, description, is_default, is_active, created_at, updated_at
- payment_terms: id, name, days, description, is_default, is_active, created_at, updated_at

EXAMPLES - ALWAYS use these exact table names:
- "show all customers" -> SELECT * FROM customers
- "show items" -> SELECT * FROM items
- "show invoices" -> SELECT * FROM invoices
- "show all expenses" -> SELECT * FROM expenses
- "show all suppliers" -> SELECT * FROM suppliers
- "show all stock movements" -> SELECT * FROM stock_movements
- "show all work orders" -> SELECT * FROM work_orders
- "show all productions" -> SELECT * FROM productions
- "show all purchase orders" -> SELECT * FROM purchase_orders
- "show all sales orders" -> SELECT * FROM sales_orders
- "show pending invoices" -> SELECT * FROM invoices WHERE status = 'pending'
- "show expenses for May 2026" -> SELECT * FROM expenses WHERE expense_date LIKE '2026-05%'
- "show invoices for customer 2" -> SELECT * FROM invoices WHERE customer_id = 2
- "total revenue" -> SELECT SUM(total_amount) as total FROM invoices WHERE status = 'Paid'

CRITICAL: For "show all [table]" queries, use SELECT * FROM [table] with NO WHERE clause.
The user wants to see ALL records, not a filtered subset.
Only add WHERE when the user explicitly mentions a filter condition.

ERP Context:
- Items can be raw materials, finished goods, or packaging
- BOM (Bill of Materials) defines production recipes
- Work orders consume materials per BOM
- Inventory movements track stock changes
- Always check stock availability before production
- Invoices reference customers by customer_id (foreign key to customers.id)

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
        (session_id, customer_id, invoice_date, due_date, status, items_data)
        VALUES (?, ?, ?, ?, 'draft', '{}')
        """
        
        draft_id = self.db.execute_write(query, (
            f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            customer_id, invoice_date, due_date
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
        
        unit_price = item['standard_selling_price']
        amount = unit_price * quantity
        items_data['items'].append({
            'item_id': item_id,
            'item_code': item['item_code'],
            'item_name': item['item_name'],
            'quantity': quantity,
            'unit_price': float(unit_price),
            'amount': float(amount),
            'is_raw_material': bool(item['is_raw_material'])
        })
        
        subtotal = sum(i['amount'] for i in items_data['items'])
        tax_rate = items_data.get('tax_rate', 0.17)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        items_data['subtotal'] = subtotal
        items_data['tax_amount'] = tax_amount
        items_data['total'] = total
        
        query = "UPDATE invoice_drafts SET items_data = ? WHERE id = ?"
        self.db.execute_write(query, (json.dumps(items_data), draft_id))
        
        return items_data
    
    def finalize_invoice(self, draft_id: int, user_id: int = 1) -> dict:
        draft = self.db.execute("SELECT * FROM invoice_drafts WHERE id = ?", (draft_id,))[0]
        
        items_data = json.loads(draft['items_data'] or '{"items": []}')
        
        if not items_data.get('items'):
            raise ValueError("Draft has no items")
        
        today = datetime.now().strftime('%Y%m%d')
        # Get last invoice number for today
        last_inv = self.db.execute(
            "SELECT invoice_no FROM invoices WHERE invoice_no LIKE ? ORDER BY id DESC LIMIT 1",
            (f"INV-{today}-%",)
        )
        if last_inv:
            last_no = int(last_inv[0]['invoice_no'].split('-')[-1])
        else:
            last_no = 0
        next_num = last_no + 1
        invoice_no = f"INV-{today}-{next_num:04d}"
        
        due_date = draft['due_date']
        
        query = """
        INSERT INTO invoices 
        (invoice_no, customer_id, invoice_date, due_date, status,
         total_amount, paid_amount, balance_amount, created_by)
        VALUES (?, ?, ?, ?, 'pending', ?, 0, ?, ?)
        """
        invoice_id = self.db.execute_write(query, (
            invoice_no, draft['customer_id'],
            draft['invoice_date'], due_date,
            items_data['total'], items_data['total'], user_id
        ))
        
        for item in items_data['items']:
            query = """
            INSERT INTO invoice_items 
            (invoice_id, item_id, quantity, unit_price, amount, tax_rate)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            self.db.execute_write(query, (
                invoice_id, item['item_id'], item['quantity'],
                item['unit_price'], item['amount'], items_data.get('tax_rate', 0.17)
            ))
            
            # Only deduct stock if item is a raw material
            if item.get('is_raw_material'):
                self._deduct_stock(item['item_id'], item['quantity'], 1)
        
        self.db.execute_write("UPDATE invoice_drafts SET status = 'finalized' WHERE id = ?", (draft_id,))
        
        return {
            'invoice_no': invoice_no,
            'invoice_id': invoice_id,
            'total': items_data['total'],
            'due_date': due_date
        }
    
    def get_low_stock_items(self, threshold: int = None) -> list:
        """Get items below reorder level.
        
        Args:
            threshold: Optional custom threshold, uses item's reorder_level if None
        
        Returns:
            List of low stock items
        """
        if threshold is not None:
            query = """
                SELECT i.*, sb.quantity as current_stock
                FROM items i
                LEFT JOIN stock_balances sb ON i.id = sb.item_id
                WHERE i.is_active = 1 AND sb.quantity < ?
                ORDER BY sb.quantity ASC
            """
            return self.db.execute(query, (threshold,))
        else:
            query = """
                SELECT i.*, sb.quantity as current_stock
                FROM items i
                LEFT JOIN stock_balances sb ON i.id = sb.item_id
                WHERE i.is_active = 1 AND sb.quantity < i.reorder_level
                ORDER BY sb.quantity ASC
            """
            return self.db.execute(query)

    def get_stock_movements(self, item_id: int = None, days: int = 30) -> list:
        """Get recent stock movements.
        
        Args:
            item_id: Optional item ID to filter
            days: Number of days to look back
        
        Returns:
            List of stock movements
        """
        if item_id:
            query = """
                SELECT sm.*, i.item_name, w.warehouse_name
                FROM stock_movements sm
                JOIN items i ON sm.item_id = i.id
                JOIN warehouses w ON sm.warehouse_id = w.id
                WHERE sm.item_id = ?
                AND sm.created_at >= datetime('now', '-' || ? || ' days')
                ORDER BY sm.created_at DESC
            """
            return self.db.execute(query, (item_id, days))
        else:
            query = """
                SELECT sm.*, i.item_name, w.warehouse_name
                FROM stock_movements sm
                JOIN items i ON sm.item_id = i.id
                JOIN warehouses w ON sm.warehouse_id = w.id
                WHERE sm.created_at >= datetime('now', '-' || ? || ' days')
                ORDER BY sm.created_at DESC
            """
            return self.db.execute(query, (days,))

    def create_stock_adjustment(self, item_id: int, warehouse_id: int, 
                                quantity: int, reason: str = "Adjustment") -> dict:
        """Create a manual stock adjustment.
        
        Args:
            item_id: Item ID
            warehouse_id: Warehouse ID
            quantity: Adjustment quantity (positive for addition, negative for reduction)
            reason: Reason for adjustment
        
        Returns:
            Adjustment record
        """
        # Record movement
        movement_id = self.db.execute_write("""
            INSERT INTO stock_movements 
            (item_id, warehouse_id, movement_type, quantity, notes, created_by)
            VALUES (?, ?, 'adjustment', ?, ?, 1)
        """, (item_id, warehouse_id, quantity, reason))
        
        # Update stock balance
        self.db.execute_write("""
            UPDATE stock_balances 
            SET quantity = quantity + ?
            WHERE item_id = ? AND warehouse_id = ?
        """, (quantity, item_id, warehouse_id))
        
        # Update item stock
        self.db.execute_write("""
            UPDATE items SET current_stock = (
                SELECT SUM(quantity) FROM stock_balances WHERE item_id = ?
            ) WHERE id = ?
        """, (item_id, item_id))
        
        return {
            'movement_id': movement_id,
            'item_id': item_id,
            'warehouse_id': warehouse_id,
            'quantity': quantity,
            'reason': reason
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

    def record_payment(self, invoice_id: int, amount: float, payment_method: str = 'cash',
                      reference: str = None, notes: str = None) -> dict:
        """Record a payment against an invoice.
        
        Args:
            invoice_id: Invoice ID
            amount: Payment amount
            payment_method: cash, bank_transfer, credit_card, etc.
            reference: Payment reference/transaction ID
            notes: Additional notes
        
        Returns:
            Payment record
        """
        # Get invoice details
        invoice = self.db.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        )
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        invoice = invoice[0]
        
        # Calculate current outstanding
        current_paid = self.db.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_paid
            FROM payments
            WHERE invoice_id = ?
        """, (invoice_id,))[0]['total_paid']
        
        outstanding = invoice['total_amount'] - current_paid
        
        if amount > outstanding:
            raise ValueError(f"Payment amount ({amount}) exceeds outstanding balance ({outstanding})")
        
        # Record payment
        payment_date = datetime.now().strftime('%Y-%m-%d')
        # Generate payment number
        payment_no = f"PAY-{payment_date.replace('-', '')}-{int(time.time())}"
        payment_id = self.db.execute_write("""
            INSERT INTO payments 
            (payment_no, invoice_id, customer_id, payment_date, amount, payment_method, reference_no, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (payment_no, invoice_id, invoice['customer_id'], payment_date, amount, payment_method, reference or '', notes or ''))
        
        # Update invoice status
        new_paid = current_paid + amount
        if new_paid >= invoice['total_amount']:
            status = 'Paid'
        elif new_paid > 0:
            status = 'Partial'
        else:
            status = 'Unpaid'
        
        self.db.execute_write("""
            UPDATE invoices SET status = ?, paid_amount = ?, balance_amount = ? WHERE id = ?
        """, (status, new_paid, invoice['total_amount'] - new_paid, invoice_id))
        
        return {
            'payment_id': payment_id,
            'invoice_id': invoice_id,
            'invoice_no': invoice['invoice_no'],
            'amount': amount,
            'payment_date': payment_date,
            'payment_method': payment_method,
            'outstanding': outstanding - amount,
            'status': status
        }

    def get_aging_report(self) -> dict:
        """Generate accounts receivable aging report.
        
        Returns:
            Aging report with buckets: current, 1_30, 31_60, 61_90, 90_plus
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        report = self.db.execute("""
            SELECT 
                c.id as customer_id,
                c.customer_code,
                c.customer_name,
                COALESCE(SUM(i.total_amount), 0) as total_invoices,
                COALESCE(SUM(p.amount), 0) as total_paid,
                COALESCE(SUM(i.total_amount), 0) - COALESCE(SUM(p.amount), 0) as outstanding,
                -- Current (0-30 days)
                COALESCE(SUM(CASE 
                    WHEN julianday(?) - julianday(i.due_date) <= 30 
                    AND i.status != 'paid'
                    THEN i.total_amount - COALESCE((SELECT SUM(amount) FROM payments WHERE invoice_id = i.id), 0)
                    ELSE 0 
                END), 0) as current,
                -- 31-60 days
                COALESCE(SUM(CASE 
                    WHEN julianday(?) - julianday(i.due_date) BETWEEN 31 AND 60
                    AND i.status != 'paid'
                    THEN i.total_amount - COALESCE((SELECT SUM(amount) FROM payments WHERE invoice_id = i.id), 0)
                    ELSE 0 
                END), 0) as days_31_60,
                -- 61-90 days
                COALESCE(SUM(CASE 
                    WHEN julianday(?) - julianday(i.due_date) BETWEEN 61 AND 90
                    AND i.status != 'paid'
                    THEN i.total_amount - COALESCE((SELECT SUM(amount) FROM payments WHERE invoice_id = i.id), 0)
                    ELSE 0 
                END), 0) as days_61_90,
                -- 90+ days
                COALESCE(SUM(CASE 
                    WHEN julianday(?) - julianday(i.due_date) > 90
                    AND i.status != 'paid'
                    THEN i.total_amount - COALESCE((SELECT SUM(amount) FROM payments WHERE invoice_id = i.id), 0)
                    ELSE 0 
                END), 0) as days_90_plus
            FROM customers c
            LEFT JOIN invoices i ON c.id = i.customer_id
            LEFT JOIN payments p ON i.id = p.invoice_id
            WHERE i.status != 'draft'
            GROUP BY c.id, c.customer_code, c.customer_name
            HAVING outstanding > 0
            ORDER BY outstanding DESC
        """, (today, today, today, today))
        
        # Calculate totals
        totals = {
            'total_outstanding': 0,
            'current': 0,
            'days_31_60': 0,
            'days_61_90': 0,
            'days_90_plus': 0
        }
        
        for row in report:
            totals['total_outstanding'] += row['outstanding']
            totals['current'] += row['current']
            totals['days_31_60'] += row['days_31_60']
            totals['days_61_90'] += row['days_61_90']
            totals['days_90_plus'] += row['days_90_plus']
        
        return {
            'customers': report,
            'totals': totals,
            'as_of': today
        }

    def get_invoice_status(self, invoice_id: int) -> dict:
        """Get detailed invoice status with payment history.
        
        Args:
            invoice_id: Invoice ID
        
        Returns:
            Invoice status details
        """
        invoice = self.db.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        )
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        invoice = invoice[0]
        
        payments = self.db.execute("""
            SELECT * FROM payments 
            WHERE invoice_id = ?
            ORDER BY payment_date DESC
        """, (invoice_id,))
        
        total_paid = sum(p['amount'] for p in payments)
        outstanding = invoice['total_amount'] - total_paid
        
        # Calculate days overdue
        days_overdue = 0
        if invoice['status'] not in ['Paid', 'draft']:
            due_date = datetime.strptime(invoice['due_date'], '%Y-%m-%d')
            today = datetime.now()
            days_overdue = (today - due_date).days
            if days_overdue < 0:
                days_overdue = 0
        
        return {
            'invoice': invoice,
            'payments': payments,
            'total_paid': total_paid,
            'outstanding': outstanding,
            'days_overdue': days_overdue,
            'payment_history': [{
                'date': p['payment_date'],
                'amount': p['amount'],
                'method': p['payment_method'],
                'reference': p['reference_no']
            } for p in payments]
        }