from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path
from datetime import datetime
import re

# URLS FOR REQUESTS
BASE = "https://www.tax.service.gov.uk/check-vat-number"
FORM_URL = f"{BASE}/enter-vat-details"

# FILE PATHS
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / 'results' / 'raw_html'
RAW_DIR.mkdir(parents=True, exist_ok=True)
CH_CSV = BASE_DIR / 'data' / 'raw' / 'companies-house' / 'BasicCompanyDataAsOneFile-2026-09-01.csv'

# CONSTANTS
SEED = 23
PER_GROUP = 75
SNAPSHOT_DATE = datetime(2026, 9, 1)
MIN_AGE_MONTHS = 12

# CLASSES
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

# FILTERS USE FOR POPULATION AND SAMPLE
def sic_division(sic_text: str) -> str:
    code = (sic_text or "").strip().split()[0] if (sic_text or "").strip() else ""
    return code[:2] if code[:2].isdigit() else "unknown"


def decade(date_str: str) -> str:
    try:
        year = int((date_str or "").strip()[-4:])
        return f"{(year // 10) * 10}s"
    except (ValueError, IndexError):
        return "unknown"


def age_months(date_str: str):
    try:
        d = datetime.strptime((date_str or "").strip(), "%d/%m/%Y")
    except (ValueError, AttributeError):
        return None
    if d > SNAPSHOT_DATE:
        return None
    return (SNAPSHOT_DATE.year - d.year) * 12 + (SNAPSHOT_DATE.month - d.month)

def exclusion_reason(row: dict) -> str:
    """None if the firm can go in population, otherwise the reason it is excluded"""

    if row.get("CompanyStatus", "").strip() != "Active":
        return "not_active"

    if row.get("Accounts.AccountCategory", "").strip() == "DORMANT":
        return "dormant"

    if sic_division(row.get("SICCode.SicText_1", "")) == "98":
        return "sic_98_residents_property_mgmt"

    inc_date = row.get("IncorporationDate", "").strip()
    age = age_months(inc_date)
    if age is None:
        return "bad_incorporation_date"
    if age < MIN_AGE_MONTHS:
        return f"younger_than_{MIN_AGE_MONTHS}_months"

    try:
        if int(inc_date[-4:]) < 1800:
            return "older_than_1800"
    except ValueError:
        return "bad_incorporation_date"

    return None

def is_eligible(row: dict) -> bool:
    return exclusion_reason(row) is None


def norm_name(s: str) -> str:
    """TESCO PLC / Tesco P.L.C. -> TESCOPLC"""
    if not s:
        return ""
    s = s.upper()
    s = re.sub(r"\b(LIMITED)\b", "LTD", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def norm_postcode(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())

# VAT
# VAT cu prefix GB explicit sau 9 cifre precedate de cuvantul VAT
VAT_PATTERNS = [
    re.compile(r"\bGB\s?(\d{3})\s?(\d{4})\s?(\d{2})\b", re.I),
    re.compile(r"VAT[^0-9]{0,40}?(\d{3})\s?(\d{4})\s?(\d{2})\b", re.I),
]


def vat_checksum_ok(vrn: str) -> bool:
    if len(vrn) != 9 or not vrn.isdigit():
        return False
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(int(vrn[i]) * weights[i] for i in range(7)) + int(vrn[7:9])
    return total % 97 == 0 or (total + 55) % 97 == 0