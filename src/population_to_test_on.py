import csv
import json
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from config import CH_CSV, SNAPSHOT_DATE, MIN_AGE_MONTHS

OUT_FILE = Path("results/population_to_test_on.json")

csv.field_size_limit(sys.maxsize)

stats = {
    "total": 0,
    "kept": 0,
    "status": Counter(),
    "account_category": Counter(),
    "sic_division": Counter(),
    "incorporation_decade": Counter(),
}
excluded = Counter()


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


with open(CH_CSV, newline="", encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    reader.fieldnames = [fn.strip() for fn in reader.fieldnames]

    for i, row in enumerate(reader, 1):
        if i % 500_000 == 0:
            print(f" ... {i:,} rows")

        stats["total"] += 1
        status = row.get("CompanyStatus", "").strip()
        stats["status"][status] += 1

        if status != "Active":
            excluded["not_active"] += 1
            continue

        cat = row.get("Accounts.AccountCategory", "").strip()
        if cat == "DORMANT":
            excluded["dormant"] += 1
            continue

        if sic_division(row.get("SICCode.SicText_1", "")) == "98":
            excluded["sic_98_residents_property_mgmt"] += 1
            continue

        age = age_months(row.get("IncorporationDate", ""))
        if age is None:
            excluded["bad_incorporation_date"] += 1
            continue
        if age < MIN_AGE_MONTHS:
            excluded["younger_than_12_months"] += 1
            continue

        inc_date = row.get("IncorporationDate", "").strip()
        if int(inc_date[-4:]) < 1800:
            excluded["older_than_1800"] += 1
            continue

        stats["kept"] += 1
        stats["account_category"][cat or "unknown"] += 1
        stats["sic_division"][sic_division(row.get("SICCode.SicText_1", ""))] += 1
        stats["incorporation_decade"][decade(row.get("IncorporationDate", ""))] += 1

out = {
    "source_file": CH_CSV.name,
    "snapshot_date": SNAPSHOT_DATE.date().isoformat(),
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "total_rows": stats["total"],
    "companies_kept": stats["kept"],
    "filter_criteria": [
        "CompanyStatus must be exactly 'Active'",
        "excluded Accounts.AccountCategory == 'DORMANT' (does not trade)",
        "excluded SIC division 98 (residents property management active but not a supplier)",
        f"excluded companies incorporated less than {MIN_AGE_MONTHS} months before snapshot "
        "(21-month deadline for first accounts, so activity cannot be judged from filings)",
        "excluded rows with missing or invalid IncorporationDate",
    ],
    "excluded_counts": dict(excluded.most_common()),
    "status": dict(stats["status"].most_common()),
    "account_category": dict(stats["account_category"].most_common()),
    "sic_division": dict(stats["sic_division"].most_common(30)),
    "incorporation_decade": dict(sorted(stats["incorporation_decade"].items())),
}

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUT_FILE.write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))