import uuid
from datetime import datetime, timezone
from typing import Optional
from app.models import InstallationHistory, Postponement

# Dictionary for mapping external reasons to standard categories.
# In a fully scaled app, this could be stored in a database table.
REASON_MAP = {
    "болеет": "employee_fault",
    "проспал": "employee_fault",
    "вина монтажника": "employee_fault",
    "не успел": "employee_fault",
    "отказ клиента": "client_request",
    "клиент перенес": "client_request",
    "нет материалов": "materials",
    "брак": "materials",
    "ошибка диспетчера": "dispatcher_error",
    "забыли": "dispatcher_error",
    "погода": "weather",
    "дождь": "weather",
    "техника сломалась": "technical",
    "машина": "technical",
    "форс-мажор": "force_majeure",
}

class PostponementDetector:
    """
    Component responsible for analyzing installation changes 
    to detect true postponements and correctly categorize them.
    """
    
    @staticmethod
    def categorize_reason(raw_reason: Optional[str]) -> str:
        """
        Maps a raw CRM string to a standardized reason category.
        """
        if not raw_reason:
            return "unknown"
            
        lower_reason = raw_reason.lower().strip()
        for key, category in REASON_MAP.items():
            if key in lower_reason:
                return category
                
        return "other"
        
    @staticmethod
    def detect(hist: InstallationHistory, raw_reason: Optional[str] = None) -> Optional[Postponement]:
        """
        Evaluates an InstallationHistory record. Returns a Postponement object if 
        the change represents a true postponement. Returns None otherwise.
        """
        is_from_chat = hist.raw_payload and hist.raw_payload.get("from_chat") is True
        
        # If it's a standard CRM event, we strictly check dates
        if not is_from_chat:
            # 1. To be a postponement, both old and new dates must be present
            if not hist.old_date or not hist.new_date:
                return None
                
            # 2. Date must actually change. Employee change alone is not a postponement.
            if hist.old_date == hist.new_date:
                return None
                
            # 3. Exclude cancellations. If the order/installation was canceled, it's not a postponement.
            if hist.new_status and hist.new_status.lower() in ["canceled", "cancelled", "отменен", "отмена"]:
                return None
            
        # 4. (Optional rule depending on business) If new date is BEFORE old date (data correction)
        if hist.new_date and hist.old_date and hist.new_date < hist.old_date:
            # We could return None here if "postponement" strictly means shifting forward.
            # However, sometimes users make a mistake and fix it backwards. 
            # We will classify this as "technical / correction" or just track it.
            pass

        category = PostponementDetector.categorize_reason(raw_reason)
        
        # The employee responsible for the postponement is the one assigned to the OLD date
        responsible_employee_id = hist.old_employee_id if hist.old_employee_id else hist.new_employee_id
        
        return Postponement(
            installation_id=hist.installation_id,
            employee_id=responsible_employee_id,
            old_date=hist.old_date,
            new_date=hist.new_date,
            reason=raw_reason,
            reason_category=category,
            detected_at=datetime.now(timezone.utc),
            source=hist.change_source,
            event_id=hist.event_id
        )
