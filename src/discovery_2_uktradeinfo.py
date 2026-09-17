import csv, glob
from collections import Counter
from config import norm_name, norm_postcode

traders = {}
name_only = {}

for path in sorted(glob.glob("data/raw/uktradeinfo/importers26*.txt")):
    n = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        f = line.rstrip("\n").split("\t")
        if len(f) < 9:
            continue
        name, pc = f[2].strip(), f[8].strip()
        if not name:
            continue
        key = (norm_name(name), norm_postcode(pc))
        traders.setdefault(key, name)
        name_only.setdefault(norm_name(name), set()).add(norm_postcode(pc))
        n += 1
    print(f"{path}: {n:,} lines")

print(f"\nunique companies (name+postcode): {len(traders):,}")
print(f"unique names: {len(name_only):,}")

sample = list(csv.DictReader(open("data/sample.csv", encoding="utf-8")))
hits = Counter(); totals = Counter()
for c in sample:
    g = c["group"]; totals[g] += 1
    k = (norm_name(c["company_name"]), norm_postcode(c["postcode"]))
    if k in traders:
        hits[g] += 1
        print(f"  MATCH  {g:<8} {c['company_name']}")

print()
for g in ["small", "medium", "large", "unknown"]:
    print(f"{g:<10} {hits[g]}/{totals[g]}")
print(f"TOTAL      {sum(hits.values())}/{len(sample)}")