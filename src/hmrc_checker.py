from typing import Optional
from datetime import datetime, timezone
import requests, re
import time

from config import BASE, FORM_URL, CheckResult, Verdict
from html_parser import parse_known_page
from html_storage import save_html

class HMRCChecker:
    def __init__(self, delay: float = 2.0):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "vat-identifier-discovery/0.1 (contact: sebi.ionita23@gmail.com)"
        self.delay = delay
        self._token: Optional[str] = None

    def _fetch_token(self):
        r = self.session.get(FORM_URL, timeout=30)
        r.raise_for_status()

        m = re.search(r'name="csrfToken"[^>]*value="([^"]+)"', r.text)
        if not m:
            raise RuntimeError("csrfToken not found")

        # retrieve the token from the html input tag
        self._token = m.group(1)
        return self._token


    def _refresh_token(self) -> str:
        return self._token or self._fetch_token()

    def check(self, vrn) -> CheckResult:
        now = datetime.now(timezone.utc).isoformat()
        token = self._refresh_token()

        try:
            r = self.session.post(
                FORM_URL,
                data={"csrfToken": token, "target": vrn, "requester": ""},
                allow_redirects=False,
                timeout=30
            )

        except requests.RequestException as re:
            return CheckResult(vrn=vrn, verdict=Verdict.ERROR, timestamp=now, error=str(re))

        finally:
            time.sleep(self.delay)

        # token expired or rejected
        if r.status_code == 403:
            self._fetch_token()
            return self.check(vrn)

        if r.status_code != 303:
            return CheckResult(vrn=vrn, verdict=Verdict.MALFORMED, timestamp=now)

        location = r.headers.get("Location", "")

        if location.endswith("/unknown"):
            return CheckResult(vrn=vrn, verdict=Verdict.UNKNOWN, timestamp=now)

        if not location.endswith("/known"):
            return CheckResult(vrn=vrn, verdict=Verdict.ERROR, timestamp=now, error=f'Location unexpected: {location}')


        page = self.session.get(f'{BASE}/known', timeout=30)
        with open("succespage.html", "w+") as f:
            f.write(page.text)

        html_path = save_html(vrn, page.text)

        time.sleep(self.delay)

        name, address = parse_known_page(page.text, vrn)
        return CheckResult(vrn=vrn, verdict=Verdict.VALID, timestamp=now, registered_name=name, registered_address=address, html_path=html_path)


