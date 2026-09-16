import csv
import random
import sys
from pathlib import Path

from config import CH_CSV, SEED, PER_GROUP, SNAPSHOT_DATE, MIN_AGE_MONTHS, is_eligible, sic_division, age_months

OUT = Path("data/sample.csv")

csv.field_size_limit(sys.maxsize)
random.seed(SEED)

# companies category sorted in 4 meaningful groups
GROUPS = {
    "small": {
        "MICRO ENTITY", "TOTAL EXEMPTION SMALL",
        "ACCOUNTS TYPE NOT AVAILABLE", "PARTIAL EXEMPTION",
    },
    "medium": {
        "SMALL", "UNAUDITED ABRIDGED", "TOTAL EXEMPTION FULL",
        "AUDIT EXEMPTION SUBSIDIARY", "FILING EXEMPTION SUBSIDIARY",
    },
    "large": {
        "FULL", "MEDIUM", "GROUP", "AUDITED ABRIDGED",
    },
    "unknown": {
        "NO ACCOUNTS FILED",
    },
}

# dictionary where category is the key to have O(1) search time when processing the CSV
CATEGORY_TO_GROUP = {
    cat: group
    for group, cats in GROUPS.items()
    for cat in cats
}

class Reservoir:
    def __init__(self, k: int):
        """k = group size"""
        self.k = k
        self.items = []
        self.seen = 0

    def offer(self, item):
        self.seen += 1

        if len(self.items) < self.k:
            self.items.append(item)
        else:
            j = random.randrange(self.seen)
            if j < self.k:
                self.items[j] = item

reservoirs = {g: Reservoir(PER_GROUP) for g in GROUPS}

with open(CH_CSV, newline="", encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    reader.fieldnames = [fn.strip() for fn in reader.fieldnames]

    for i, row in enumerate(reader, 1):
        if i % 500_000 == 0:
            print(f"  ...{i:,}")

        if not is_eligible(row):
            continue

        cat = row.get("Accounts.AccountCategory", "").strip()
        group = CATEGORY_TO_GROUP.get(cat)

        if group is None:
            continue

        reservoirs[group].offer({
            "company_number": row.get("CompanyNumber", "").strip(),
            "company_name": row.get("CompanyName", "").strip(),
            "postcode": row.get("RegAddress.PostCode", "").strip(),
            "address": " / ".join(filter(None, [
                row.get("RegAddress.AddressLine1", "").strip(),
                row.get("RegAddress.AddressLine2", "").strip(),
                row.get("RegAddress.PostTown", "").strip(),
            ])),
            "sic": row.get("SICCode.SicText_1", "").strip(),
            "account_category": cat,
            "incorporation_date": row.get("IncorporationDate", "").strip(),
            "group": group,
        })

rows = []
for group, res in reservoirs.items():
    print(f"{group:<10} {res.seen:>10,} eligible -> {len(res.items)} trase")
    rows.extend(res.items)

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(f"\n{len(rows)} companies written in {OUT}")

