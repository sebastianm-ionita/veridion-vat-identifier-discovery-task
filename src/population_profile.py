import csv
import json
import re
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

CH_CSV = "data/raw/companies-house/BasicCompanyDataAsOneFile-2026-09-01.csv"
OUT_FILE = Path("results/population_profile.json")

csv.field_size_limit(sys.maxsize)

stats = {
    "total": 0,
    "active": 0,
    "status": Counter(),
    "account_category": Counter(),
    "sic_division": Counter(),
    "incorporation_decade": Counter(),
}

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

def sic_division(sic_text: str) -> str:
    """47110 - Retail ...  -> 47"""
    code = (sic_text or "").strip().split()[0] if sic_text.strip() else ""
    return code[:2] if code[:2].isdigit() else "unknown"

def decade(date_str: str) -> str:
    """12/03/2017 -> 2010s"""
    try:
        year = int((date_str or "").strip()[-4:])
        return f"{(year // 10) * 10}s"
    except (ValueError, IndexError):
        return "unknown"

with open(CH_CSV, newline="", encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    reader.fieldnames = [fn.strip() for fn in reader.fieldnames]
    for i, row in enumerate(reader,1):
        if i % 500_000 == 0:
            print(f" ... {i:,} rows")

        stats["total"] += 1
        status = row.get("CompanyStatus", "").strip()
        stats["status"][status] += 1

        if status != "Active":
            continue

        stats["active"] += 1
        stats["account_category"][row.get("Accounts.AccountCategory", "").strip() or "unknown"] += 1
        stats["sic_division"][sic_division(row.get("SICCode.SicText_1", ""))] += 1
        stats["incorporation_decade"][decade(row.get("IncorporationDate", ""))] += 1

# json format
out = {
    "source_file": Path(CH_CSV).name,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "total_rows": stats["total"],
    "active_companies": stats["active"],
    "note": "Distribution of companies based only on ACTIVE companies",
    "status": dict(stats["status"].most_common()),
    "account_category": dict(stats["account_category"].most_common()),
    "sic_division": dict(stats["sic_division"].most_common(30)),
    "incorporation_decade": dict(sorted(stats["incorporation_decade"].items())),
}

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUT_FILE.write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))