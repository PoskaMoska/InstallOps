import re
from typing import Optional, Tuple
from app.services.postponement_engine import PostponementDetector

# Regex to find exactly a 10-digit number starting with 1 or 2
TICKET_REGEX = re.compile(r'\b([12]\d{9})\b')

# Keywords indicating a postponement
POSTPONEMENT_KEYWORDS = [
    "перенос", "перенесена", "перенести", "переносим", "сдвигаем"
]

class ChatParser:
    """
    Parses natural language chat messages to extract 
    ticket numbers and postponement reasons.
    """
    @staticmethod
    def extract_ticket(text: str) -> Optional[str]:
        if not text: return None
        match = TICKET_REGEX.search(text)
        return match.group(1) if match else None

    @staticmethod
    def is_postponement_intent(text: str) -> bool:
        if not text: return False
        lower_text = text.lower()
        return any(kw in lower_text for kw in POSTPONEMENT_KEYWORDS)

    @staticmethod
    def clean_reason(text: str, ticket: Optional[str] = None) -> str:
        if not text: return ""
        cleaned = text
        if ticket:
            cleaned = cleaned.replace(ticket, "")
        # Remove common prefixes like "заявка", "з"
        cleaned = re.sub(r'(?i)\b(заявка|заказ|з\.)\b', '', cleaned)
        # Remove multiple spaces and strip
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    @staticmethod
    def parse_message(text: str) -> Optional[Tuple[str, str]]:
        ticket = ChatParser.extract_ticket(text)
        is_postp = ChatParser.is_postponement_intent(text)
        if ticket and is_postp:
            return (ticket, ChatParser.clean_reason(text, ticket))
        return None
