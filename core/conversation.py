import json
import uuid
from datetime import datetime
from .database import Database


class ConversationEngine:
    def __init__(self, db: Database):
        self.db = db
        self.sessions = {}
    
    def start_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'session_id': session_id,
            'current_customer_id': None,
            'current_customer_name': None,
            'current_draft_id': None,
            'current_invoice_no': None,
            'last_operation': None,
            'last_operation_id': None,
            'warehouse_id': 1,
            'user_id': 1,
            'conversation_history': []
        }
        return session_id
    
    def get_context(self, session_id: str) -> dict:
        return self.sessions.get(session_id, {})
    
    def update_context(self, session_id: str, **kwargs):
        if session_id in self.sessions:
            self.sessions[session_id].update(kwargs)
    
    def add_message(self, session_id: str, role: str, content: str):
        if session_id in self.sessions:
            self.sessions[session_id]['conversation_history'].append({
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat()
            })
    
    def get_history(self, session_id: str, limit: int = 10) -> list:
        ctx = self.sessions.get(session_id, {})
        hist = ctx.get('conversation_history', [])
        return hist[-limit:] if len(hist) > limit else hist
    
    def set_current_customer(self, session_id: str, customer_id: int, customer_name: str):
        self.update_context(
            session_id,
            current_customer_id=customer_id,
            current_customer_name=customer_name
        )
    
    def set_current_draft(self, session_id: str, draft_id: int):
        self.update_context(session_id, current_draft_id=draft_id)
    
    def get_conversation_summary(self, session_id: str) -> str:
        ctx = self.get_context(session_id)
        parts = []
        
        if ctx.get('current_customer_name'):
            parts.append(f"Current customer: {ctx['current_customer_name']}")
        if ctx.get('current_invoice_no'):
            parts.append(f"Current invoice: {ctx['current_invoice_no']}")
        if ctx.get('last_operation'):
            parts.append(f"Last operation: {ctx['last_operation']}")
        
        return ", ".join(parts) if parts else "No active context"