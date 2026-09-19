import json
from pathlib import Path

from hmrc_checker import HMRCChecker
from html_storage import CacheStorage
import time


class Checker:
    def __init__(self, vrns: list[str], batch_size: int = 10, batch_pause: float = 60.0):
        self.vrns = vrns
        self.checker = HMRCChecker()
        self.storage = CacheStorage()
        self.batch_size = batch_size
        self.batch_pause = batch_pause

    def run(self):
        total = len(self.vrns)
        done = 0

        for i, vrn in enumerate(self.vrns, 1):
            cached = self.storage.get(vrn)
            if cached:
                print(f"[{i}/{total}] {vrn} CACHED {cached['verdict']}")
                continue

            result = self.checker.check(vrn)
            self.storage.append(result)
            done += 1
            print(f"[{i}/{total}] {vrn} {result.verdict}")

            if result.error and "429" in result.error:
                print(f"\n429 dupa {done} cereri. Astept 300s...")
                time.sleep(300)
                result = self.checker.check(vrn)
                self.storage.append(result)
                if result.error and "429" in result.error:
                    print("tot 429 dupa pauza. Opresc.")
                    break

            if done % self.batch_size == 0 and i < total:
                print(f"  pauza {self.batch_pause:.0f}s dupa {done} cereri...")
                time.sleep(self.batch_pause)

FILE = Path("results/commoncrawl_vats.jsonl")

vrns = sorted({
    json.loads(line)["vrn"]
    for line in FILE.read_text(encoding="utf-8").splitlines()
    if line.strip() and "vrn" in line
})

print(f"{len(vrns)} VRN-uri unice de verificat")

Checker(vrns, batch_size=5).run()