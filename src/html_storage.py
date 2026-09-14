import hashlib
import json
from pathlib import Path
from dataclasses import asdict

from config import RAW_DIR, CheckResult, Verdict

def save_html(vrn: str, html: str) -> str:
    # if page was changed it will be saved with a different hash
    # if page is already created there are no duplicates created

    hashed = hashlib.sha256(html.encode()).hexdigest()[:12]
    path = RAW_DIR / f"{vrn}_{hashed}.html"
    path.write_text(html, encoding="utf-8")

    return str(path)

class CacheStorage:
    def __init__(self, path: str = "results/checks.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(exist_ok=True, parents=True)
        self._seen = self._load()

    def _load(self) -> dict:
        seen = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if not line.strip():
                    continue

                rec = json.loads(line)

                if rec["verdict"] != "ERROR":
                    seen[rec["vrn"]] = rec

        return seen

    def get(self, vrn):
        return self._seen.get(vrn)

    def append(self, result: CheckResult):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result)) + "\n")

        if result.verdict != Verdict.ERROR:
            self._seen[result.vrn] = asdict(result)
