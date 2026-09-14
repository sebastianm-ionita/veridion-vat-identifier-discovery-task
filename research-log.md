*11-sep*

[2:11 PM] : Verificare VAT INVALID CU CHECKSUM VALID
Invalid UK VAT number
You searched for ‘027298852’.

This does not match the VAT number of any UK VAT-registered business.

Search completed on 11 September 2026 at 12:10pm (BST).

[2:13 PM] : Verificare VAT VALID CU CHECKSUM VALID
VAT registration details
Registered business name
DAVID JAMES BIRD

Registered business address
NEIDIN
EASENHALL ROAD
HARBOROUGH MAGNA
RUGBY
CV23 0HX
GB

Search completed on 11 September 2026 at 12:10pm (BST).

[2:20 PM] : Aplicatia veridion-vat-identifier-discovery-task a fost adaugata in sandbox pe hmrc

[2:25 PM] : Am creat client-id si client-secret pentru aplicatia din sanbox

[2:33 PM] : Am adaugat un test_user si i-am salvat datele in folderul proiectului si trebuie urmat pasii de la https://developer.service.hmrc.gov.uk/api-documentation/docs/authorisation/user-restricted-endpoints#auth-endpoint-syntax

*13-sep*

[1:00 PM] : Incerc sa fac rost de OAuth2.0 Token ...

[1:11 PM] : Am facut rost de oauth token

[1:40 PM] : Am citit ToS pentru production access. Sandbox-ul merge doar cu VRN-urimock din vrn.csv, deci nu pot verifica firme reale cu el. Pentru date reale imi trebuie production, si aia inseamna aprobare de ~2 saptamani plus un formular care cere URL de organizatie, dovada de inregistrare, privacy policy, terms and conditions, penetration testing si WCAG AA. Eu n-am produs comercial si n-am clienti, deci jumatate din intrebari nu mi se aplica.

API-ul e declarat "for the sole purpose of allowing traders to do due diligence on VAT-registered businesses". Nu ma incadrez , chiar daca tehnic fac acelasi apel.

Raman pe serviciul web public de la gov.uk/check-uk-vat-number, care mi-a intors nume si adresa reale la testele de la 14:10. De verificat inainte sa automatizez ceva: robots.txt si ToS-ul serviciului web.

[1:51 PM] :  Verificat robots.txt pe ambele domenii.

www.gov.uk/robots.txt: Disallow doar pe /*/print$ si /search/all*. Blocari punctuale pe deepcrawl si MS Search 6.0, ambele mentionate explicit ca fac prea multe requesturi. AhrefsBot are Crawl-delay: 10. Deci nu exista interdictie generala, iar preocuparea lor documentata e volumul, nu accesul automat.

www.tax.service.gov.uk/robots.txt: 404, fisierul nu exista. Nicio directiva.

Deci robots.txt nu imi interzice verificarea automata, dar nici nu mi-o permite explicit. Ramane sa verific ToS.

[1:55 PM] : Citit ToS HMRC (last update 2005)

Relevant:
- "Our website is maintained for your personal use and viewing" - cea mai restrictiva fraza. Verificare in masa pentru un dataset comercial nu intra acolo.
- "in a manner that does not restrict or inhibit the use and enjoyment of this site by any third party" + mentiune de perturbare a functionarii normale, criteriul e volumul.
- Nu exista nicio interdictie explicita pe automated / scraping / bulk / systematic.

Se potriveste cu robots.txt, singurii boti blocati erau cei care faceau prea multe requesturi. Le pasa de incarcare, nu de metoda de acces.

O sa verific automat un esantion mic, cu delay intre request-uri, pentru Part2. O sa doc volumul exact si ritmul, dar pentru un produs vandut nu as construi pe sursa asta pentru o linie de business, si nu am nicio garantie contractuala pentru disponibiltate.

[2:14 PM] : Testat fluxul complet pe serviciul web.

POST /check-vat-number/enter-vat-details cu form data: csrfToken, target, requester (gol = unverified check). Urmeaza redirect 302 catre rezultat.

Verdict din url:
- /check-vat-number/known    -> VAT valid, pagina contine nume + adresa
- /check-vat-number/unknown  -> nu corespunde niciunei firme inregistrate

Deci am nevoie de textul paginii doar pentru nume si adresa dar asta doar cand este valid.

Response headers: Cache-Control: no-cache, no-store, max-age=0. Deci fiecare verificare loveste serverul, nu exista cache  intermediar. Imi tin eu cache local ca sa nu repet verificari.

Am facut peste 10 verificari consecutive, fara 429 si fara CAPTCHA, aflam mai tarziu daca exista rate limiting.

Browser-ul face 10 requesturi pentru o singura verificare (css, js, fonturi ...), deci o sa incarc mai putin serviciul decat un browser, facand doar 2 request-uri si zero analytics

[2:23 PM] : Testat refolosirea csrfToken in aceeasi sesiune. (reusetoken.py)

./python3 reusetoken.py
token: 23ba7dd90fe8f9bd919b
POST 1: 303 /check-vat-number/known
POST 2: 303 /check-vat-number/unknown

Token-ul e refolosibil toata sesiunea deci pot face 1 GET la inceput si 1 POST / verificare. Redirect-ul e 303, deci codul corect si in plus, la POST2 am pus un vrn din sandbox-ul hmrc deci da dovada ca cele de acolo sunt fictive.

[17:20 PM] : Inceput script-ul hmrc_checker.py


*14 sep*

[12:45 PM] : Inceput script-ul html_parser.py care va contine functia parse_known_page() -> name, address sau None

Am analizat html-ul paginii /known si o sa folosesc BeautifulSoup sa caut heading-ul ce contine 'Registered business name' care este urmat intotdeauna de un paragraph ce contine numele business-ului, la fel pentru 'Registered business address' doar ca separ liniile din interiorul <p> cu un '\n'. De asemanea verific ca VRN-ul cautat sa fie acelasi cu cel de pe pagina. Si o functie ce extrage codul postal de pe penultima linie folosind regex. (O sa ma folosesc de nume si cod postal pentru a decide verdictul)

[1:17 PM] : Inapoi la hmrc_checker.py.

- Urmeaza salvarea html-ului pentru a nu reface cererile in caz de am gresit ceva la functii, si pentru a avea dovada cifrelor din raport.
- Urmeaza implementarea cache-ului local pentru a nu relua verificari in caz de crash.
