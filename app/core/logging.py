import logging
import sys
import json
from datetime import datetime, timezone
from app.core.config import settings

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "environment": settings.ENVIRONMENT
        }
        if hasattr(record, "extra_info"):
            log_record.update(record.extra_info)
        
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logging():
    logger = logging.getLogger("installops")
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    # Avoid adding duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

logger = setup_logging()
