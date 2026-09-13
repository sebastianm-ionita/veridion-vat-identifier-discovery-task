import requests, re

BASE = "https://www.tax.service.gov.uk/check-vat-number"
s = requests.Session()
s.headers["User-Agent"] = "vat-discovery-research/0.1 (contact: sebi.ionita23@gmail.com)"

r = s.get(f"{BASE}/enter-vat-details")
token = re.search(r'name="csrfToken"[^>]*value="([^"]+)"', r.text).group(1)
print("token:", token[:20])

r1 = s.post(f"{BASE}/enter-vat-details",
            data={"csrfToken": token, "target": "220430231", "requester": ""},
            allow_redirects=False)
print("POST 1:", r1.status_code, r1.headers.get("Location"))

r2 = s.post(f"{BASE}/enter-vat-details",
            data={"csrfToken": token, "target": "553557881", "requester": ""},
            allow_redirects=False)
print("POST 2:", r2.status_code, r2.headers.get("Location"))
