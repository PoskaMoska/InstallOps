import pytest
import uuid
from datetime import date
from app.models import InstallationHistory
from app.services.postponement_engine import PostponementDetector

def test_detect_valid_postponement():
    hist = InstallationHistory(
        installation_id=uuid.uuid4(),
        old_date=date(2026, 8, 25),
        new_date=date(2026, 8, 27),
        old_employee_id=uuid.uuid4(),
        new_status="scheduled"
    )
    
    postponement = PostponementDetector.detect(hist, raw_reason="Клиент перенес на завтра")
    
    assert postponement is not None
    assert postponement.old_date == date(2026, 8, 25)
    assert postponement.new_date == date(2026, 8, 27)
    assert postponement.reason_category == "client_request"
    assert postponement.employee_id == hist.old_employee_id

def test_detect_no_old_date():
    hist = InstallationHistory(
        old_date=None,
        new_date=date(2026, 8, 27),
        new_status="scheduled"
    )
    assert PostponementDetector.detect(hist) is None

def test_detect_same_date_change_employee():
    hist = InstallationHistory(
        old_date=date(2026, 8, 27),
        new_date=date(2026, 8, 27),
        old_employee_id=uuid.uuid4(),
        new_employee_id=uuid.uuid4(),
        new_status="scheduled"
    )
    assert PostponementDetector.detect(hist) is None

def test_detect_cancellation():
    hist = InstallationHistory(
        old_date=date(2026, 8, 25),
        new_date=date(2026, 8, 27),
        new_status="отменен"
    )
    assert PostponementDetector.detect(hist) is None
    
def test_categorize_reason():
    assert PostponementDetector.categorize_reason("Монтажник болеет, не выйдет") == "employee_fault"
    assert PostponementDetector.categorize_reason("сломалась машина по пути") == "technical"
    assert PostponementDetector.categorize_reason(None) == "unknown"
    assert PostponementDetector.categorize_reason("Что-то странное и непонятное") == "other"
