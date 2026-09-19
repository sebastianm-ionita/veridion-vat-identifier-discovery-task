import json, re, difflib
from pathlib import Path
from collections import Counter

CC     = Path("results/commoncrawl_vats.jsonl")
CHECKS = Path("results/checks.jsonl")

LEGAL = r"(LIMITED|LTD|PLC|LLP|GROUP|HOLDINGS|UK|COMPANY|CO)"


def norm_vrn(v: str) -> str:
    return re.sub(r"[^0-9]", "", v or "")


def norm_name(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def domain_slug(domain: str) -> str:
    """www.fun-party-supplies.co.uk -> FUNPARTYSUPPLIES"""
    d = (domain or "").lower()
    d = re.sub(r"\.(co\.uk|org\.uk|ac\.uk|ltd\.uk|me\.uk|uk|com|net|org|it|es|ca|tv|london)$", "", d)
    parts = [p for p in d.split(".") if p not in ("www", "staging", "shop", "store", "careers")]
    core = parts[-1] if parts else ""
    return re.sub(r"[^A-Z0-9]", "", core.upper())


def attribution(slug: str, hmrc_name: str) -> str:
    """Numele returnat de HMRC corespunde domeniului de unde am luat numarul?"""
    if not slug or not hmrc_name:
        return "NO_DATA"
    name = norm_name(hmrc_name)
    stripped = re.sub(LEGAL + r"$", "", name)          # scoate sufixul juridic
    if slug in name or name in slug or slug in stripped:
        return "MATCH"
    ratio = difflib.SequenceMatcher(None, slug, stripped).ratio()
    if ratio >= 0.75:
        return "MATCH"
    if ratio >= 0.55:
        return "PARTIAL"
    return "NO_MATCH"


# --- incarca verificarile HMRC ---
checked = {}
for line in CHECKS.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    r = json.loads(line)
    checked[norm_vrn(r["vrn"])] = r

# --- un rand per VAT unic din Common Crawl ---
cc = {}
for line in CC.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    r = json.loads(line)
    v = norm_vrn(r["vrn"])
    cc.setdefault(v, {"domains": [], "urls": []})
    cc[v]["domains"].append(r["domain"])
    cc[v]["urls"].append(r["url"])

print(f"VAT-uri unice din Common Crawl: {len(cc)}")
print(f"dintre care verificate la HMRC: {sum(1 for v in cc if v in checked)}\n")

rows = []
for vrn, info in cc.items():
    chk = checked.get(vrn)
    verdict = chk["verdict"] if chk else "NOT_CHECKED"
    hmrc_name = (chk or {}).get("registered_name")
    domain = info["domains"][0]
    is_uk = domain.endswith(".uk")
    attr = attribution(domain_slug(domain), hmrc_name) if verdict == "VALID" else None
    rows.append({
        "vrn": vrn, "domain": domain, "is_uk": is_uk,
        "verdict": verdict, "hmrc_name": hmrc_name, "attribution": attr,
    })


def report(label, subset):
    n = len(subset)
    if not n:
        return
    valid = [r for r in subset if r["verdict"] == "VALID"]
    attr = Counter(r["attribution"] for r in valid)
    print(f"--- {label}  (n={n})")
    print(f"  VAT real (HMRC VALID):   {len(valid):>3} / {n}  = {len(valid)/n*100:5.1f}%   <- precizia regex")
    if valid:
        m = attr["MATCH"]
        print(f"  se potriveste cu domeniul: {m:>3} / {len(valid)}  = {m/len(valid)*100:5.1f}%   <- precizia atribuirii")
        print(f"  end-to-end (din toate):   {m:>3} / {n}  = {m/n*100:5.1f}%")
        print(f"  detaliu atribuire: {dict(attr)}")
    print()


report("TOATE", rows)
report("domenii .uk", [r for r in rows if r["is_uk"]])
report("domenii non-.uk", [r for r in rows if not r["is_uk"]])

print("=== de verificat manual (PARTIAL / NO_MATCH) ===")
for r in rows:
    if r["attribution"] in ("PARTIAL", "NO_MATCH"):
        print(f"  {r['vrn']}  {r['domain'][:45]:<45} -> {r['hmrc_name']}  [{r['attribution']}]")