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

Am analizat html-ul paginii /known si o sa folosesc BeautifulSoup sa caut heading-ul ce contine 'Registered business name' care este urmat intotdeauna de un paragraph ce contine numele business-ului, la fel pentru 'Registered business address' doar ca separ liniile din interiorul <p> cu un '\n'. De asemanea verific ca VRN-ul cautat sa fie acelasi cu cel de pe pagina. Si o functie ce extrage codul postal de pe penultima linie folosind regex. (TODO: O sa ma folosesc de nume si cod postal pentru a decide verdictul)

[1:50 PM] : Creat html_storage.py.

- Urmeaza salvarea html-ului pentru a nu reface cererile in caz de am gresit ceva la functii, si pentru a avea dovada cifrelor din raport.
- Urmeaza implementarea cache-ului local pentru a nu relua verificari in caz de crash.

[3:35 PM] : Inceput checker.py.

Va verifica 20-30 de VRN-uri, iar eu voi face urmatoarele verificari:
1. checks.jsonl are ac numar de linii ca numarul de VRN-uri
2. daca rulez a doua oara totul e cached
3. opresc rularea si continua de unde a ramas
4. am toate tipurile de verdict-uri
5. html-urile sunt salvate si pot fii accesate

[3:48 PM] : Parametrii alesi.

- delay 2 secunde intre requesturi, browser-ul face 10 request-uri, eu fac 1-2 ca sa nu declansez analytics si incarc serviciul mai putin decat cineva care verifica manual
- user-agent care ma identifica cu link la repo si mail.
- fara paralelism , pentru ca 2 request-uri simultane s-ar suprapune si as pune detalii gresite firmei

[3:50 PM] : Am terminat checker.py. Am scris logica de verificare in spatele unei interfete, nu direct legata de HMRC, din doua motive concrete:

1. Calea oficiala (API-ul HMRC) exista, dar am decis sa n-o folosesc din motive de scop si termeni. Daca situatia se schimba - primesc acces la productie, sau se schimba conditiile trec pe ea schimband o singura implementare, fara sa umblu in restul pipeline-ului.

2. Task-ul intreaba la final cum ar arata acelasi lucru pentru Germania, iar acolo verificarea se face prin VIES, care nu se comporta identic pentru fiecare stat membru. Daca tin verificarea separata de restul (esantionare, discovery, matching), schimbarea de tara inseamna o implementare noua de verifier, nu un pipeline nou. Asta imi da si un raspuns mai bun la intrebarea "ar supravietui pipeline-ul tau mutarii", pot arata exact ce se schimba si ce ramane.

[4:40 PM] : Am rulat checker-ul pe 27 VRN-uri. Rezultat: 13 VALID, 11 UNKNOWN, 3 MALFORMED. Toate cele 5 verificari din plan au trecut jsonl complet, a doua rulare tot cached, reluare dupa Ctrl+C ok, toate verdictele prezente, html-urile salvate si accesibile.

Throughput masurat din timestamp-uri: ~2.2s per UNKNOWN (1 request) si ~4.4s per VALID (2 requesturi). Confirma ca designul cu  allow_redirects=False injumatateste costul.

[4:55 PM] : Serviciul nu verifica checksum-ul, GB111111111, GB999999999, GB555555555, GB123456789 au checksum invalid si au iesit UNKNOWN, nu MALFORMED. Validarea se opreste la forma (prefix, 9 cifre, fara litere), nu face % 97. Deci nu pot diferentia "checksum  gresit" de "neinregistrat" prin serviciu, filtrarea pe checksum o fac local, inainte sa trimit cererea.

[5:30 PM] : Am comparat adresele HMRC cu Companies House pe cele 13 VALID, dintre care 11/13 MATCH pe cod postal. In general HMRC intoarce adresa de sediu social, Royal Mail fiin singurul caz real de adresa diferita (CH: Farringdon Road EC1A 1AA, HMRC: Group Tax la Chesterfield S49 1PF)

[5:37 PM] : BP nu era adresa diferita, era firma gresita. Scriptul meu oprea la prima potrivire pe nume si luase BP INTERNATIONAL LTD #10543031, de la 20-22 Wenlock Road N1 7GU, adresa de formation agent. Am scos oprirea si am colectat toate potrivirile: exista 2 firme cu acelasi nume normalizat. A doua, #00542515 de pe Chertsey Road TW16 7BP, e cea reala si face MATCH cu HMRC.

De retinut:
- numele nu e identificator, CH are firme distincte cu acelasi nume
- la potrivirea pe nume am o lista de candidati, codul postal decide
- daca niciun candidat are codul postal potrivit -> UNCERTAIN

[5:39 PM] : Detaliu: HMRC are "CHERSTEY ROAD" in loc de Chertsey. Typoo in sursa de referinta. HMRC-ul are informatii gresite uneori.


*15 sep*

[2:50 PM] : Profilat populatia din Companies House in 'population_profile.json'

5.689.367 randuri, din care 5.171.600 ACTIVE. Task-ul zice 4.2M Live companies eu am 5.17M doar ACTIVE, plus inca 402K "ACTIVE-Proposal to Strike off". 2.73M inregistrari VAT la nivel national (incluzand sole traders, am luat cifra de pe ONS) la 5.17M firme active. Maxim 52% din firme ar putea avea VAT, dar realist mult mai putine au.

Distributia pe conturi e dezechilibrata:
  MICRO ENTITY          1.668.834
  NO ACCOUNTS FILED     1.347.758
  TOTAL EXEMPTION FULL  1.227.653
  DORMANT                 565.741
  ......
  FULL + MEDIUM + GROUP   112.450  (~2.2%)

Primele patru fac 93% din firmele active. DORMANT (11%) aproape sigur n-au VAT (o firma dormanta nu tranzactioneaza). NO ACCOUNTS FILED (26%) sunt in mare nou-infiintate sau care n-au inceput activitatea.

Pe vechime: 2.854.461 firme active infiintate in anii 2020 = 55% din total. Plus 1.464.327 in 2010. Deci 83% din firmele active au sub 16 ani. Multe dintre ele se suprapun cu NO ACCOUNTS FILED.

Pe SIC: 605.263 sunt Real Estate = 12%. Nicio diviziune nu domina distributia. 216.320 fara SIC.

[3:12 PM] : Datele de infiintare contin erori evidente. Am firme active infiintate in 1320, 1410, 1500 etc., Companies House exista din 1844, orice inainte de asta e eroare de date. Sunt putine companii dar confirma ce am vazut la "Cherstey Road", sursele nu sunt intotdeauna corecte.

De verificat: diviziunile SIC 98 (125K) si 99 (98K), par cam mari pentru ce reprezinta, probabile sunt marcaje pentru DORMANT

[3:30 PM] : Verificat ce se intampla cu SIC 98 si 99. (src/sic99_98_uncertainty.py)

 126,042  98000 - Residents property management
 105,409  99999 - Dormant Company
     645  98200 - Undifferentiated service-producing activities of private households for own use
     629  99000 - Activities of extraterritorial organizations and bodies
     506  98100 - Undifferentiated goods-producing activities of private households for own use
     153  9999 - Dormant company
      12  9800 - Residents property management

99999 chiar e marcaj, 105.409 firme se marcheaza DORMANT prin SIC separat de cele 565.741 marcate DORMANT la account_category.

98000 nu este marcaj, 126.042 societati de administrare a blocurilor, mai mult ca sigur nu apar niciodata ca furnizor intr-un sistem de achizitii.

Al treilea semn ca datele nu sunt uniforme este ca coexista coduri de 4/5 cifre pentru acelasi lucru (99999/9999 si 98000/9800).

[4:20 PM] : Verificat suprapunerea dintre SIC dormand (99999/9999) si account_category DORMANMT.

97.542 firme active cu SIC dormand din care 71.8% sunt si DORMANT la conturi. General, DORMANT doar 10.9% din firmele active, deci este o asociere puternica, dar nu o identitate.

27.482 (28.2%) isi declara SIC-ul ca "Dormant Company" dar depun conturi de firma activa: 10.159 MICRO ENTITY, 9.838 NO ACCOUNTS FILED, 5.261 TOTAL EXEMPTION FULL. Contradictie in sursa SIC zice una conturile alta, nu stiu care e corecta

Invers: din 565.741 DORMANT la conturi, doar 70.020 au si SIC 99999. Deci ~495.000 sunt dormante fara sa o declare prin SIC.

In concluzie DORMANT la conturi e criteriul mai cuprinzator. SIC 99999 adauga doar ~27k peste el, si alea sunt tocmai cazurile contradictorii. Daca filtrez, filtrez pe account_category si tratez SIC-ul ca semnal secundar.