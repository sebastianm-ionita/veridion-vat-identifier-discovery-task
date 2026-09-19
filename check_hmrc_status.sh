BASE="https://www.tax.service.gov.uk/check-vat-number"
UA="vat-identifier-discovery/0.1 (contact: sebi.ionita23@gmail.com)"

# 1. ia formularul, salveaza cookie-urile
curl -s -c cookies.txt -H "User-Agent: $UA" "$BASE/enter-vat-details" -o form.html

# 2. extrage csrfToken
TOKEN=$(grep -o 'name="csrfToken"[^>]*value="[^"]*"' form.html | grep -o 'value="[^"]*"' | cut -d'"' -f2)
echo "token: $TOKEN"

# 3. POST, fara sa urmeze redirectul
curl -s -i -b cookies.txt -c cookies.txt \
  -H "User-Agent: $UA" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "csrfToken=$TOKEN" \
  --data-urlencode "target=220430231" \
  --data-urlencode "requester=" \
  "$BASE/enter-vat-details" | head -20
