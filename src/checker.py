from hmrc_checker import HMRCChecker
from html_storage import CacheStorage

class Checker:
    def __init__(self, vrns: list[str]):
        self.vrns = vrns
        self.checker = HMRCChecker()
        self.storage = CacheStorage()

    def run(self):
        vrns_length = len(self.vrns)

        for i, vrn in enumerate(self.vrns, 1):
            cached = self.storage.get(vrn)
            if cached:
                print(f"[{i}/{vrns_length}] {vrn} CACHED {cached['verdict']}")
                continue

            result = self.checker.check(vrn)

            self.storage.append(result)
            print(f"[{i}/{vrns_length}] {vrn} {result.verdict}")


vrns = [
    # VALID
    "GB220430231", "GB660454836", "GB788622577", "GB116300129",
    "GB569953277", "GB232128892", "GB179765890", "GB232457280",
    "GB245719348", "GB243852262", "GB243170002", "GB745360825",
    "GB243510593",

    # UNKNOWN
    "GB000000000", "GB123456789", "GB999999999", "GB555555555",
    "GB111111111", "GB287461520", "GB365682329", "GB244155572",
    "GB238713801", "GB244760461", "GB218408345",

    # MALFORMED
    "UK220430231", "GB1234567", "GB78862257A"
]

c = Checker(vrns)
c.run()
