import re
from typing import Optional, Tuple
from app.services.postponement_engine import PostponementDetector

# Regex to find exactly a 10-digit number starting with 2 or 22
TICKET_REGEX = re.compile(r'\b(2\d{9})\b')

# Keywords indicating a postponement
POSTPONEMENT_KEYWORDS = [
    "перенос", "переношу", "отмена", "отбой", "перенесли"
]

class ChatParser:
    """
    Parses natural language chat messages to extract 
    ticket numbers and postponement reasons.
    """
    @staticmethod
    def parse_message(text: str) -> Optional[Tuple[str, str]]:
        """
        Returns (ticket_number, reason) if it's a postponement message, 
        else None.
        """
        if not text:
            return None
            
        lower_text = text.lower()
        
        # 1. Quick check for intent
        is_postponement = any(kw in lower_text for kw in POSTPONEMENT_KEYWORDS)
        
        # 2. Extract ticket
        match = TICKET_REGEX.search(text)
        
        if is_postponement and match:
            ticket_number = match.group(1)
            # The rest of the message might be the reason
            # Clean out the ticket number
            cleaned_reason = text.replace(ticket_number, "")
            # Remove common prefixes like "Заявка", "Заказ" case-insensitively
            cleaned_reason = re.sub(r'(?i)\b(заявка|заказ|з\.)\b', '', cleaned_reason)
            # Remove multiple spaces and strip
            cleaned_reason = re.sub(r'\s+', ' ', cleaned_reason).strip()
            
            # Use our existing categorizer to see if it makes sense, 
            # or just return the raw cleaned string
            category = PostponementDetector.categorize_reason(cleaned_reason)
            return (ticket_number, cleaned_reason)
            
        return None
