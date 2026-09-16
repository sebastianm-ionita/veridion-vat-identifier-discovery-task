import csv
import json
import re
import sys
from pathlib import Path
from collections import Counter
from config import CH_CSV


csv.field_size_limit(sys.maxsize)

def sic_code(sic_text: str) -> str:
    m = re.match(r"\s*(\d+)", sic_text or "")
    return m.group(1) if m else ""

def is_sic_dormant(sic_text: str) -> bool:
    return sic_code(sic_text) in ("99999", "9999")

def sic_division(sic_text: str) -> str:
    code = sic_code(sic_text)
    return code[:2] if len(code) >= 2 else "unknown"

texts = Counter()
overlap = Counter()
active_totals = Counter()
sic_dormant_total = 0
both = 0

with open(CH_CSV, newline="", encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    reader.fieldnames = [fn.strip() for fn in reader.fieldnames]

    for i, row in enumerate(reader):
        if i % 500_000 == 0:
            print(f"  ...{i:,}")

        if row.get("CompanyStatus", "").strip() != "Active":
            continue

        sic_raw = row.get("SICCode.SicText_1", "")
        cat = row.get("Accounts.AccountCategory", "").strip() or "unknown"
        active_totals[cat] += 1

        if sic_division(sic_raw) in ("98", "99"):
            texts[sic_raw.strip()] += 1

        if is_sic_dormant(sic_raw):
            sic_dormant_total += 1
            overlap[cat] += 1
            if cat == "DORMANT":
                both += 1

print("\n--- SIC 98/99 ---")
for text, n in texts.most_common():
    print(f"{n:>8,}  {text}")

print(f"\n--- firme cu SIC dormant: {sic_dormant_total:,} ---")
print(f"din care si DORMANT la conturi: {both:,} ({both/sic_dormant_total:.1%})")
print("\naccount_category la firmele cu SIC dormant (vs. procent in toata populatia activa):")
total_active = sum(active_totals.values())
for cat, n in overlap.most_common():
    share_here = n / sic_dormant_total
    share_all = active_totals[cat] / total_active
    print(f"  {cat:<28} {n:>8,}  {share_here:>6.1%}  (general {share_all:>5.1%})")