import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from .database import Database
from decimal import Decimal


class ProductionManager:
    """Manages Bill of Materials (BOM) and production workflows."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_bom(self, bom_id: int = None, finished_item_id: int = None) -> Optional[Dict]:
        """Get BOM details."""
        if bom_id:
            result = self.db.execute(
                "SELECT * FROM boms WHERE id = ?", (bom_id,)
            )
        elif finished_item_id:
            result = self.db.execute(
                "SELECT * FROM boms WHERE finished_item_id = ? AND is_active = 1",
                (finished_item_id,)
            )
        else:
            return None
        
        if not result:
            return None
        
        bom = result[0]
        bom_id = bom['id']
        
        # Get BOM items
        items = self.db.execute("""
            SELECT bi.*, i.item_name, i.item_code, i.unit_of_measure
            FROM bom_items bi
            JOIN items i ON bi.item_id = i.id
            WHERE bi.bom_id = ?
        """, (bom_id,))
        
        # Get finished item details
        finished = self.db.execute(
            "SELECT * FROM items WHERE id = ?", (bom['finished_item_id'],)
        )[0]
        
        return {
            'bom': bom,
            'finished_item': finished,
            'components': items
        }
    
    def calculate_bom_cost(self, bom_id: int) -> Dict:
        """Calculate total cost for a BOM."""
        bom_data = self.get_bom(bom_id=bom_id)
        if not bom_data:
            return {"error": "BOM not found"}
        
        total_cost = Decimal('0')
        components_detail = []
        
        for comp in bom_data['components']:
            item = self.db.execute(
                "SELECT standard_cost, current_stock FROM items WHERE id = ?",
                (comp['item_id'],)
            )[0]
            
            unit_cost = Decimal(str(item['standard_cost'] or 0))
            qty = Decimal(str(comp['quantity']))
            line_cost = unit_cost * qty
            
            components_detail.append({
                'item_id': comp['item_id'],
                'item_code': comp['item_code'],
                'item_name': comp['item_name'],
                'quantity': float(qty),
                'unit_cost': float(unit_cost),
                'line_cost': float(line_cost),
                'available_stock': item['current_stock']
            })
            
            total_cost += line_cost
        
        bom_qty = Decimal(str(bom_data['bom']['quantity'] or 1))
        unit_cost = total_cost / bom_qty if bom_qty > 0 else total_cost
        
        return {
            'bom_id': bom_id,
            'bom_no': bom_data['bom']['bom_no'],
            'finished_item': bom_data['finished_item']['item_name'],
            'finished_item_id': bom_data['bom']['finished_item_id'],
            'bom_quantity': float(bom_qty),
            'total_material_cost': float(total_cost),
            'unit_material_cost': float(unit_cost),
            'components': components_detail
        }
    
    def check_production_feasibility(self, bom_id: int, quantity: int) -> Dict:
        """Check if production is feasible given available stock."""
        bom_data = self.get_bom(bom_id=bom_id)
        if not bom_data:
            return {"feasible": False, "error": "BOM not found"}
        
        bom_qty = Decimal(str(bom_data['bom']['quantity'] or 1))
        required_runs = Decimal(str(quantity)) / bom_qty
        
        shortages = []
        max_production = None
        
        for comp in bom_data['components']:
            item = self.db.execute(
                "SELECT current_stock FROM items WHERE id = ?",
                (comp['item_id'],)
            )[0]
            
            available = Decimal(str(item['current_stock'] or 0))
            required_per_run = Decimal(str(comp['quantity']))
            total_required = required_per_run * required_runs
            
            if available < total_required:
                shortages.append({
                    'item_id': comp['item_id'],
                    'item_name': comp['item_name'],
                    'required': float(total_required),
                    'available': float(available),
                    'shortage': float(total_required - available)
                })
            
            # Calculate max production possible
            if required_per_run > 0:
                possible_runs = available / required_per_run
                possible_qty = possible_runs * bom_qty
                if max_production is None or possible_qty < max_production:
                    max_production = possible_qty
        
        return {
            'feasible': len(shortages) == 0,
            'requested_quantity': quantity,
            'bom_quantity': float(bom_qty),
            'required_runs': float(required_runs),
            'max_possible_quantity': float(max_production) if max_production else 0,
            'shortages': shortages
        }
    
    def create_work_order(self, bom_id: int, quantity: int, warehouse_id: int = 1,
                         notes: str = "") -> Dict:
        """Create a work order for production."""
        feasibility = self.check_production_feasibility(bom_id, quantity)
        
        if not feasibility['feasible']:
            return {
                "error": "Insufficient materials",
                "feasibility": feasibility
            }
        
        bom_data = self.get_bom(bom_id=bom_id)
        bom_qty = Decimal(str(bom_data['bom']['quantity'] or 1))
        
        # Create work order
        wo_date = datetime.now().strftime('%Y-%m-%d')
        # Generate work order number
        last_wo = self.db.execute(
            "SELECT wo_no FROM work_orders WHERE wo_no LIKE ? ORDER BY id DESC LIMIT 1",
            (f"WO-{wo_date.replace('-', '')}-%",)
        )
        if last_wo:
            last_no = int(last_wo[0]['wo_no'].split('-')[-1])
        else:
            last_no = 0
        next_num = last_no + 1
        wo_no = f"WO-{wo_date.replace('-', '')}-{next_num:04d}"
        
        query = """
        INSERT INTO work_orders 
        (wo_no, bom_id, finished_item_id, planned_quantity, warehouse_id, status, notes, created_at, created_by)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, 1)
        """
        wo_id = self.db.execute_write(query, (
            wo_no, bom_id, bom_data['bom']['finished_item_id'], quantity, warehouse_id, notes, wo_date
        ))
        
        # Create material consumption entries
        required_runs = Decimal(str(quantity)) / bom_qty
        
        for comp in bom_data['components']:
            required_per_run = Decimal(str(comp['quantity']))
            total_required = required_per_run * required_runs
            
            self.db.execute_write("""
            INSERT INTO material_consumption
            (wo_id, item_id, consumed_quantity, consumption_date, created_by)
            VALUES (?, ?, ?, ?, 1)
            """, (wo_id, comp['item_id'], float(total_required), wo_date))
        
        return {
            'work_order_id': wo_id,
            'bom_id': bom_id,
            'bom_no': bom_data['bom']['bom_no'],
            'quantity': quantity,
            'status': 'pending',
            'warehouse_id': warehouse_id,
            'created_at': wo_date
        }
    
    def complete_work_order(self, wo_id: int) -> Dict:
        """Complete a work order and update inventory."""
        wo = self.db.execute(
            "SELECT * FROM work_orders WHERE id = ?", (wo_id,)
        )
        
        if not wo:
            return {"error": "Work order not found"}
        
        wo = wo[0]
        
        if wo['status'] == 'completed':
            return {"error": "Work order already completed"}
        
        bom_data = self.get_bom(bom_id=wo['bom_id'])
        bom_qty = Decimal(str(bom_data['bom']['quantity'] or 1))
        total_output = Decimal(str(wo['planned_quantity']))
        
        # Consume materials
        materials = self.db.execute(
            "SELECT * FROM material_consumption WHERE wo_id = ?",
            (wo_id,)
        )
        
        for mat in materials:
            self.db.execute_write("""
            UPDATE stock_balances
            SET quantity = quantity - ?
            WHERE item_id = ? AND warehouse_id = ?
            """, (mat['consumed_quantity'], mat['item_id'], wo['warehouse_id']))
            
            # Update item stock
            self.db.execute_write("""
            UPDATE items SET current_stock = (
                SELECT COALESCE(SUM(quantity), 0) FROM stock_balances WHERE item_id = ?
            ) WHERE id = ?
            """, (mat['item_id'], mat['item_id']))
        
        # Add finished goods to inventory
        self.db.execute_write("""
        UPDATE stock_balances
        SET quantity = quantity + ?
        WHERE item_id = ? AND warehouse_id = ?
        """, (float(total_output), bom_data['bom']['finished_item_id'], wo['warehouse_id']))
        
        # Update item stock
        self.db.execute_write("""
        UPDATE items SET current_stock = (
            SELECT COALESCE(SUM(quantity), 0) FROM stock_balances WHERE item_id = ?
        ) WHERE id = ?
        """, (bom_data['bom']['finished_item_id'], bom_data['bom']['finished_item_id']))
        
        # Update work order status
        self.db.execute_write("""
        UPDATE work_orders SET status = 'completed', actual_completion_date = ? WHERE id = ?
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), wo_id))
        
        return {
            'work_order_id': wo_id,
            'status': 'completed',
            'output_quantity': float(total_output),
            'finished_item': bom_data['finished_item']['item_name']
        }
    
    def get_production_summary(self) -> Dict:
        """Get production summary statistics."""
        pending = self.db.execute(
            "SELECT COUNT(*) as count FROM work_orders WHERE status = 'pending'"
        )[0]['count']
        
        completed = self.db.execute(
            "SELECT COUNT(*) as count FROM work_orders WHERE status = 'completed'"
        )[0]['count']
        
        total_boms = self.db.execute(
            "SELECT COUNT(*) as count FROM boms WHERE is_active = 1"
        )[0]['count']
        
        return {
            'total_boms': total_boms,
            'pending_orders': pending,
            'completed_orders': completed,
            'total_orders': pending + completed
        }