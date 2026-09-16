import csv, json, re, time, sys
from pathlib import Path
from datetime import datetime, timezone
import requests

SAMPLE = Path("data/sample.csv")
OUT = Path("results/discovery_web.jsonl")
HTML_DIR = Path("results/raw_html_web")

UA = "vat-discovery-research/0.1 (+https://github.com/sebastianm-ionita/veridion-vat-identifier-discovery-task; sebi.ionita23@gmail.com)"
DELAY = 1.0
TIMEOUT = 10
PAGES = ["", "/contact", "/contact-us", "/terms", "/terms-and-conditions", "/about", "/privacy"]

LEGAL_SUFFIXES = [
    "LIMITED PARTNERSHIP", "LIMITED", "LTD", "PLC", "P.L.C.", "LLP", "L.P.", "LP",
    "C.C.C.", "L.L.C", "LLC", "HOLDINGS", "GROUP",
]

# VAT cu prefix GB explicit, sau 9 cifre precedate de cuvantul VAT
VAT_PATTERNS = [
    re.compile(r"\bGB\s?(\d{3})\s?(\d{4})\s?(\d{2})\b", re.I),
    re.compile(r"VAT[^0-9]{0,40}?(\d{3})\s?(\d{4})\s?(\d{2})\b", re.I),
]


def vat_checksum_ok(vrn: str) -> bool:
    """Mod-97 UK. Verifica-l pe cele 13 VRN-uri deja confirmate la HMRC."""
    if len(vrn) != 9 or not vrn.isdigit():
        return False
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(int(vrn[i]) * weights[i] for i in range(7)) + int(vrn[7:9])
    return total % 97 == 0 or (total + 55) % 97 == 0


def candidate_domains(name: str):
    n = name.upper()
    for suf in LEGAL_SUFFIXES:
        if n.endswith(" " + suf):
            n = n[: -len(suf) - 1]
            break
    slug = re.sub(r"[^A-Z0-9]+", "", n).lower()
    dashed = re.sub(r"[^A-Z0-9]+", "-", n.strip()).strip("-").lower()
    out = []
    for base in dict.fromkeys([slug, dashed]):
        if 3 <= len(base) <= 40:
            out += [f"{base}.co.uk", f"{base}.com", f"{base}.uk"]
    return out


def find_vats(text: str):
    found = set()
    for pat in VAT_PATTERNS:
        for m in pat.finditer(text):
            vrn = "".join(m.groups())
            if vat_checksum_ok(vrn):
                found.add(vrn)
    return sorted(found)


def save_html(company_no: str, url: str, html: str) -> str:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:80]
    path = HTML_DIR / f"{company_no}_{safe}.html"
    path.write_text(html, encoding="utf-8", errors="replace")
    return str(path)


def load_done():
    if not OUT.exists():
        return set()
    return {
        json.loads(l)["company_number"]
        for l in OUT.read_text().splitlines() if l.strip()
    }


def probe(company):
    """Incearca domeniile candidate, descarca paginile, cauta VAT."""
    session = requests.Session()
    session.headers["User-Agent"] = UA

    result = {
        "company_number": company["company_number"],
        "company_name": company["company_name"],
        "group": company["group"],
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "domains_tried": [],
        "site_found": None,
        "pages_fetched": [],
        "vats_found": [],
        "html_paths": [],
        "error": None,
    }

    for domain in candidate_domains(company["company_name"]):
        url = f"https://{domain}"
        result["domains_tried"].append(domain)
        try:
            r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
            time.sleep(DELAY)
            if r.status_code != 200 or len(r.text) < 500:
                continue
            result["site_found"] = r.url
            break
        except requests.RequestException:
            time.sleep(DELAY)
            continue

    if not result["site_found"]:
        return result

    base = result["site_found"].rstrip("/")
    for page in PAGES:
        url = base + page
        try:
            r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
            time.sleep(DELAY)
            if r.status_code != 200:
                continue
            result["pages_fetched"].append(url)
            vats = find_vats(r.text)
            if vats:
                result["vats_found"] = sorted(set(result["vats_found"]) | set(vats))
                result["html_paths"].append(
                    save_html(company["company_number"], url, r.text)
                )
        except requests.RequestException:
            time.sleep(DELAY)
            continue

    return result


def main():
    done = load_done()
    companies = list(csv.DictReader(SAMPLE.open(encoding="utf-8")))
    OUT.parent.mkdir(parents=True, exist_ok=True)

    for i, c in enumerate(companies, 1):
        if c["company_number"] in done:
            print(f"[{i}/{len(companies)}] {c['company_name'][:40]:<40} CACHED")
            continue
        res = probe(c)
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(res) + "\n")
        status = "no site"
        if res["site_found"]:
            status = f"VAT {res['vats_found']}" if res["vats_found"] else "site, no VAT"
        print(f"[{i}/{len(companies)}] {c['company_name'][:40]:<40} {status}")


if __name__ == "__main__":
    vrns = [
    # VALID
    "220430231", "660454836", "788622577", "116300129",
    "569953277", "232128892", "179765890", "232457280",
    "245719348", "243852262", "243170002", "745360825",
    "243510593",

    # UNKNOWN
    "000000000", "123456789", "999999999", "555555555",
    "111111111", "287461520", "365682329", "244155572",
    "238713801", "244760461", "218408345",

    # MALFORMED
    "220430231"]
    for vrn in vrns:
        print(vrn, vat_checksum_ok(vrn))

    main()
