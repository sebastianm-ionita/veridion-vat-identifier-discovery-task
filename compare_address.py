from collections import defaultdict
import csv, json, re, sys
from pathlib import Path
from config import CH_CSV

CHECKS = "results/checks.jsonl"

csv.field_size_limit(sys.maxsize)

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

targets = {}
for line in Path(CHECKS).read_text().splitlines():
    if not line.strip():
        continue
    rec = json.loads(line)
    if rec["verdict"] != "VALID" or not rec.get("registered_name"):
        continue
    key = norm_name(rec["registered_name"])
    addr_lines = (rec.get("registered_address") or "").split("\n")
    targets[key] = {
        "vrn": rec["vrn"],
        "hmrc_name": rec["registered_name"],
        "hmrc_postcode": addr_lines[-2].strip() if len(addr_lines) >= 2 else "",
        "hmrc_address": rec.get("registered_address"),
    }

print(f"caut {len(targets)} firme in CH...\n")

found = defaultdict(list)
with open(CH_CSV, newline="", encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    reader.fieldnames = [fn.strip() for fn in reader.fieldnames]
    for i, row in enumerate(reader, 1):
        if i % 500_000 == 0:
            print(f"  ...{i:,} randuri, {len(found)}/{len(targets)} gasite")
        key = norm_name(row.get("CompanyName", ""))
        # pentru mai multe companii cu acelasi nume
        if key in targets:
            found[key].append(row)

print(f"\ngasite: {len(found)}/{len(targets)}\n")
for key, t in targets.items():
    rows = found.get(key, [])
    rows = found.get(key, [])
    print(f"  {len(rows)} potriviri pe nume in CH")
    for row in rows:
        print("=" * 70)
        print(f"VRN {t['vrn']}  |  {t['hmrc_name']}")
        if not row:
            print("  NEGASIT in Companies House")
            continue
        ch_pc = row.get("RegAddress.PostCode", "")
        ch_addr = " / ".join(filter(None, [
            row.get("RegAddress.CareOf", ""),
            row.get("RegAddress.AddressLine1", ""),
            row.get("RegAddress.AddressLine2", ""),
            row.get("RegAddress.PostTown", ""),
            ch_pc,
        ]))
        match = norm_postcode(t["hmrc_postcode"]) == norm_postcode(ch_pc)
        print(f"  CH  #{row.get('CompanyNumber','').strip()}  {ch_addr}")
        print(f"  HMRC {t['hmrc_address'].replace(chr(10), ' / ')}")
        print(f"  postcode: {'MATCH' if match else 'DIFERIT'}  ({ch_pc} vs {t['hmrc_postcode']})")