import gzip, json, re, glob
from pathlib import Path
from urllib.parse import urlparse
from warcio.archiveiterator import ArchiveIterator
from config import vat_checksum_ok, VAT_PATTERNS

OUT = Path("results/commoncrawl_vats.jsonl")

def find_vats(text):
    out = set()
    for pat in VAT_PATTERNS:
        for m in pat.finditer(text):
            vrn = "".join(m.groups())
            if vat_checksum_ok(vrn):
                out.add(vrn)
    return out

pages = 0
pages_uk = 0
hits = 0
seen = {}

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8") as fout:
    for path in sorted(glob.glob("data/raw/commoncrawl/*.wet.gz")):
        print(f"--- {path}")
        with open(path, "rb") as stream:
            for record in ArchiveIterator(stream):
                if record.rec_type != "conversion":
                    continue
                pages += 1
                if pages % 20000 == 0:
                    print(f"  {pages:,} pagini, {hits} hituri")

                url = record.rec_headers.get_header("WARC-Target-URI") or ""
                domain = urlparse(url).netloc.lower()
                if domain.endswith(".uk"):
                    pages_uk += 1

                text = record.content_stream().read().decode("utf-8", errors="replace")
                if "vat" not in text.lower() and "GB" not in text:
                    continue

                for vrn in find_vats(text):
                    hits += 1
                    seen.setdefault(vrn, set()).add(domain)
                    fout.write(json.dumps({
                        "vrn": vrn, "url": url, "domain": domain
                    }) + "\n")

print(f"\npagini procesate:   {pages:,}")
print(f"pagini .uk:         {pages_uk:,}  ({pages_uk/pages*100:.1f}%)")
print(f"aparitii VAT:       {hits:,}")
print(f"VAT-uri unice:      {len(seen):,}")
print(f"pe mai multe domenii: {sum(1 for d in seen.values() if len(d) > 1):,}")