import re
from typing import Dict, Any, Optional, Tuple

class IntentExtractor:
    """Simple intent extraction optimized for small models."""
    
    CREATE_INVOICE_KEYWORDS = ['create invoice', 'new invoice', 'make invoice', 'generate invoice']
    ADD_ITEM_KEYWORDS = ['add', 'with', 'qty', 'quantity', 'pcs', 'pieces', 'units']
    DONE_KEYWORDS = ['done', 'finish', 'complete', 'no more', "that's all", 'nothing else', 'cancel']
    LIST_KEYWORDS = ['list', 'show', 'display', 'what']
    SELECT_KEYWORDS = ['select', 'choose', 'pick', 'option']
    
    @staticmethod
    def extract_intent(user_input: str) -> Dict[str, Any]:
        text = user_input.lower().strip()
        
        if any(kw in text for kw in IntentExtractor.DONE_KEYWORDS):
            return {'intent': 'done', 'entities': {}}
        
        if any(kw in text for kw in IntentExtractor.LIST_KEYWORDS):
            if 'customer' in text:
                return {'intent': 'list_customers', 'entities': {}}
            if 'item' in text:
                return {'intent': 'list_items', 'entities': {}}
            if 'warehouse' in text:
                return {'intent': 'list_warehouses', 'entities': {}}
        
        selection = IntentExtractor._extract_number(text)
        if selection and any(kw in text for kw in IntentExtractor.SELECT_KEYWORDS):
            return {'intent': 'select_option', 'entities': {'option_id': selection}}
        if selection and not re.search(r'[a-zA-Z]', text):
            return {'intent': 'select_option', 'entities': {'option_id': selection}}
        
        if any(kw in text for kw in IntentExtractor.CREATE_INVOICE_KEYWORDS):
            customer_name = IntentExtractor._extract_customer_name(text)
            return {'intent': 'create_invoice', 'entities': {'customer_name': customer_name}}
        
        quantity, item_name = IntentExtractor._extract_item_with_quantity(text)
        if quantity and item_name:
            return {'intent': 'add_item', 'entities': {'quantity': quantity, 'item_name': item_name}}
        
        if 'warehouse' in text:
            warehouse_name = IntentExtractor._extract_warehouse_name(text)
            return {'intent': 'select_warehouse', 'entities': {'warehouse_name': warehouse_name}}
        
        return {'intent': 'add_item', 'entities': {'item_name': text, 'quantity': 1}}
    
    @staticmethod
    def _extract_number(text: str) -> Optional[int]:
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])
        word_numbers = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
        for word, num in word_numbers.items():
            if word in text:
                return num
        return None
    
    @staticmethod
    def _extract_customer_name(text: str) -> Optional[str]:
        for kw in IntentExtractor.CREATE_INVOICE_KEYWORDS:
            text = text.replace(kw, '')
        text = text.replace('for', '').replace('customer', '').strip()
        return text if text else None
    
    @staticmethod
    def _extract_item_with_quantity(text: str) -> Tuple[Optional[int], Optional[str]]:
        quantity = IntentExtractor._extract_number(text)
        if quantity:
            for num in re.findall(r'\d+', text):
                text = text.replace(num, '', 1)
        word_numbers = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
        for word in word_numbers:
            text = text.replace(word, '', 1)
        item_name = text.strip()
        for kw in IntentExtractor.ADD_ITEM_KEYWORDS:
            item_name = item_name.replace(kw, '').strip()
        if item_name and len(item_name) > 1:
            return quantity, item_name
        return None, None
    
    @staticmethod
    def _extract_warehouse_name(text: str) -> Optional[str]:
        text = text.replace('warehouse', '').replace('wh', '').strip()
        return text if text else None