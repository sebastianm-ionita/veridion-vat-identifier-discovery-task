from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path
from datetime import datetime

BASE = "https://www.tax.service.gov.uk/check-vat-number"
FORM_URL = f"{BASE}/enter-vat-details"

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / 'results' / 'raw_html'
RAW_DIR.mkdir(parents=True, exist_ok=True)

CH_CSV = BASE_DIR / 'data' / 'raw' / 'companies-house' / 'BasicCompanyDataAsOneFile-2026-09-01.csv'

SEED = 42
PER_GROUP = 75
SNAPSHOT_DATE = datetime(2026, 9, 1)
MIN_AGE_MONTHS = 12

class Verdict(str, Enum):
    VALID = "VALID"
    UNKNOWN = "UNKNOWN"
    MALFORMED = "MALFORMED"
    ERROR = "ERROR"

@dataclass
class CheckResult:
    vrn: str
    verdict: Verdict
    timestamp: str
    registered_name: Optional[str] = None
    registered_address: Optional[str] = None
    html_path: Optional[str] = None
    error: Optional[str] = None