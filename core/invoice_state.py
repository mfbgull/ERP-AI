from enum import Enum
from typing import Optional
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
        self.state = InvoiceState.IDLE
        self.customer_id = None
        self.customer_name = None
        self.warehouse_id = 1
        self.draft_id = None
        self.items_count = 0
        self.created_at = datetime.now()
    
    def is_expired(self) -> bool:
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