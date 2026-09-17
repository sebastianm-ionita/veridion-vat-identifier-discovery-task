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

[7:15 PM] : Filtrat populatia ca sa am din ce trage sample-ul. (src/population_to_test_on.py) (output in result/population_to_test_on.json)

Am scos firmele cu account_category DORMANT (nu tranzactioneaza, deci nu pot fi furnizor), cele cu SIC 98000 - Residents property management (societati de administrare a blocurilor, active dar nu factureaza un producator) si cele cu NO ACCOUNTS FILED. Au ramas 3.187.409 firme din 5.171.600 active, adica 61.6%.

Filtrul nu e neutru pe vechime:
  anii 2020 - inainte de filtru 55.2% din populatie, dupa filtru 40.6%
  anii 2010 - inainte 28.3%, dupa 38.4%

Excluderea NO ACCOUNTS FILED a scos ~1.5M firme recente, pentru ca o firma infiintata acum cateva luni n-a ajuns inca la primul termen de depunere. Printre ele sunt si comercianti reali.

Am acceptat asta pentru ca firmele foarte noi au cea mai mica sansa sa fie inregistrate la TVA si mi-ar fi umplut sample-ul cu cazuri unde n-am ce gasi. Dar efectul secundar e ca imi creste artificial rata de descoperire am scos cazurile grele. De asta raportez rata si pe populatia nefiltrata, ca sa se vada cat a adus filtrul.

[7:40 PM] Am refacut filtrul.

Am scos criteriul NO ACCOUNTS FILED si l-am inlocuit cu unul explicit pe vechime: exclud firmele infiintate cu mai putin de 12 luni inainte de data snapshotului (01-09-2026). Motivul: firmele au 21 de luni pentru prima situatie financiara, deci sub 12 luni nu am cum sa judec activitatea din depuneri.

Am schimbat pentru ca  NO ACCOUNTS FILED amesteca doua populatii diferite firme care n-au depus niciodata nimic, si firme infiintate recent care pur si simplu n-au ajuns la termen. Scotand toata categoria, excludeam si comercianti reali. Criteriul pe vechime face exact ce spune.

Rezultat: 3.832.677 firme pastrate (fata de 3.187.409 cu filtrul vechi), deci am recuperat ~645.000 de firme care au NO ACCOUNTS FILED dar au peste 12 luni.

Distributia pe decade, cat de mult deformeaza filtrul populatia:
             nefiltrat   filtru vechi   filtru nou
  2020s        55.2%        40.6%         48.1%
  2010s        28.3%        38.4%         33.5%
Tot deviaza, dar acum devierea e intentionata si o pot explica.

Excluderi, pe motiv:
  691.634  sub 12 luni
  565.741  DORMANT
  517.767  status diferit de Active
  81.548  SIC 98 (administrare blocuri)

*16 sep*

[12:38 PM] : Impartirea pe grupe, dupa account_category ca proxy de marime. Companies House nu da cifra de afaceri, dar tipul de conturi depuse depinde de praguri legale de marime, deci e un indiciu indirect.

  Mici       MICRO + TOTAL EXEMPTION SMALL + ACCOUNTS TYPE NOT AVAILABLE
             + PARTIAL EXEMPTION                          1.620.885  (50.8%)
  Medii      SMALL + UNAUDITED ABRIDGED + TOTAL EXEMPTION FULL
             + AUDIT/FILING EXEMPTION SUBSIDIARY          1.452.459  (45.5%)
  Mari       FULL + MEDIUM + GROUP + AUDITED ABRIDGED       113.471   (3.6%)
  Necunoscut NO ACCOUNTS FILED                              645.827

"Necunoscut" e grupa separata pentru ca sunt firme cu peste 12 luni care n-au depus conturi. Nu pot spune daca sunt mari sau mici si reprezinta 17% din populatie, prea mult ca sa le ignor sau sa le bag in alta categorie.

[12:45 PM] : Iau egal din fiecare grupa, 75 + 75 + 75 + 75 = 300.

De ce: grupa "mari" e 3.6% din populatie, deci proportional as avea ~11 firme din 300, prea putine ca sa raportez ceva pe ele. Cu esantion egal pot spune "rata e X% la firmele mari si Y% la cele mici", ceea ce raspunde la intrebarea de business: pentru ce fel de furnizori putem livra.

Cifra globala o sa o calculez la final ca medie ponderata cu marimile reale a grupelor din populatia si o raportez separat cu tot cu formula de calcul.

[13:15 PM] : Implementat build_sample.py cu reservoid sampling si seed fix 23.

Reservoir pentru ca nu vreau sa tin 1.6M de randuri in memorie ca sa aleg 75. Algoritmul trece o data prin fisier si tine exact 75 per grupa: primele 75 intra direct, iar firma numarul n intra cu probabilitatea 75/n si da afara una la intamplare. Fiecare firma ajunge in esantion cu aceeasi sansa, si nu trebuie sa stiu totalul dinainte.

SEED fix ca oricine sa reproduca aceleasi 300 de firme.

Am mutat filtrele in config.py pentru ca e folosit si de script-ul de filtrare. Verificarea am facut-o uitandu-ma la numarul de eligibile/grupa raportat de build_sample si population (1.620.885 / 1.452.459 / 113.471 / 645.827), ambele au aceasi populatie.

Rezultatul se afla in data/sample.csv, 300 de firme fara duplicate pe company_number.

[18:32 PM] : discovery_1_website.py -> discovery_web.jsonl

Prima sursa de discovery testata: site-ul propriu al firmei, cu domeniu ghicit din denumire (slug si varianta cu cratime, pe .co.uk/.com/.uk), apoi homepage + /contact + /terms + /about + /privacy, cu regex pe GB+9 cifre si validare de checksum mod-97.

Rezultat pe cele 300 de firme din sample:

  grupa       n   site gasit   VAT gasit
  small      75    22 (29.3%)   1 (1.3%)
  medium     75    18 (24.0%)   1 (1.3%)
  large      75    19 (25.3%)   6 (8.0%)
  unknown    75    22 (29.3%)   0 (0.0%)
  TOTAL     300    81 (27.0%)   8 (2.7%)

Toate cele 8 au trecut HMRC si matching-ul nume+cod postal cu firma din Companies House. Zero false pozitive din 8 verificate dar pe 8 cazuri cifra spune putin.

Are sens ca precizia sa fie mare aici, daca o firma isi pune VAT-ul in footer-ul propriului site, e al ei. Falsurile pozitive apar la surse unde numarul e mentionat de altcineva.

Trei observatii:

1. Firmele mari dau de 6 ori mai mult decat restul (8% vs 1.3%). Are sens factureaza B2B si au nevoie sa-si publice VAT-ul. Cifra e slaba (6 din 75), dar directia e clara si e exact raspunsul la intrebarea de business: pentru ce fel de furnizori se poate livra.
2. Rata de gasire a site-ului e aproape identica in toate grupele (24-29%). Asta nu inseamna ca 27% din firme au site. Inseamna ca ghicirea domeniului din denumirea legala functioneaza in 27% din cazuri. Firmele mari au aproape sigur site, dar la un domeniu care nu se deduce din numele legal (brand diferit de denumire). Deci 27% e limita metodei mele, nu prezenta reala a site-urilor.

3. Zero VAT-uri in grupa "unknown". Firmele care nu depun conturi nici nu-si publica   VAT-ul.

In concluzie 2.7% acoperire generala. Sursa asta singura nu construieste datasetul cerut clientul are 40.000 de furnizori si i-ar lipsi in continuare ~97%. Dar ghicirea domeniului e partea slaba: daca as rezolva gasirea site-ului, rata ar creste. De testat separat cat de mult.

*17 sep*

[3:40 PM] : A doua sursa testata: datele vamale HMRC (uktradeinfo.com), fisiere "Importer details", jan-iun 2026, Open Government Licence v3.0.

Format: tab-separated, 59 campuri fixe. Camp 2 = numele firmei, camp 8 = cod postal, campurile 9-58 = pana la 50 de coduri de marfa. 657.580 de linii in 6 fisiere lunare.

Nu contine VAT. Doar nume, adresa, cod postal, coduri de marfa.

207.983 firme unice (nume+cod postal) din 5.17M firme active = 4% din populatie. Asta e plafonul absolut al sursei.

Suprapunere cu esantionul meu de 300:
  small      1/75    1.3%
  medium     2/75    2.7%
  large     13/75   17.3%
  unknown    0/75    0.0%
  TOTAL     16/300   5.3%

Acelasi tipar ca la site-uri, dar mai pronuntat: firmele mari sunt de 13x mai prezente decat cele mici.

JAGEX LIMITED apare in ambele surse, e si firma la care am gasit VAT pe site. Deci sursele se suprapun, nu se aduna, adaugand surse noi lovesc in mare parte aceleasi firme, nu unele noi. Conteaza pentru Part 3, cand estimez cat ar creste acoperirea cu mai multe surse.

Totusi ne foloseste pentru ca firmele care importa au nevoie de EORI, iar pentru cele inregistrate la TVA EORI = GB + VRN + 000. Deci astea 208.000 de firme au aproape sigur VAT. Nu e sursa de discovery, e sursa de prioritizare imi spune unde merita cautat. Pentru clientul din enunt ar fi un filtru: din 40.000 de furnizori, cei care apar aici sunt cei pentru care cautarea are sens.

[4:15 PM] : Am luat toate cele 16 firme care apar si in datele vamale si in esantionul meu, si le-am cautat VAT-ul manual pe site.

Gasit (6):
  ROTOSOUND MANUFACTURING     terms and conditions   rotosound.com
  JACKSON ENGINEERING UK      terms and conditions   jeukparts.com
  JAGEX LIMITED               pe site
  GILEAD SCIENCES LTD         pe site
  ARDEN DIES LIMITED          footer                 ardendies.com
  FACULTATIEVE TECHNOLOGIES   company registration information

Are site dar nu publica VAT (8): FEME, EF CORPORATE EDUCATION, HI-REL LIDS, BRAND FACTORY (doar company number), SENSECO  YSTEMS, FISCAL IOR (doar company number), SACKERS, PHARMARON UK.

Fara site (2): OPTILIGHT, CPL PRODUCTS.

6/16 = 37.5%, fata de 2.7% pe esantionul general de 300.

Deci firmele care importa sunt de ~14x mai probabil sa-si publice VAT-ul. Daca importa, inseamna ca factureaza B2B, deci au nevoie ca partenerii sa le vada VAT-ul.

In concluzie pentru Part 3 nu cauti in toata populatia. Filtrezi intai pe firme care sigur tranzactioneaza, apoi cauti doar acolo. Datele vamale sunt un astfel de filtru, gratuit si sub OGL v3.0. Costul scade drastic in loc de 300 de cautari pentru 8 rezultate, faci 16 pentru 6.

Filtrul are o limita, acopera doar 4% din populatie (207.983 din 5.17M). Deci rata mare pe un segment mic. Pentru clientul cu 40.000 de furnizori, asta ar insemna ~1.600 de firme unde cautarea are sens, din care ~600 gasite. Tot departe de cele 26.000 care ii lipsesc.

In plus cautarea manuala gaseste VAT-uri pe care scriptul meu le-a ratat. JAGEX a iesit la ambele, dar ROTOSOUND, JACKSON ENGINEERING, GILEAD, ARDEN DIES si FACULTATIEVE nu. Deci scriptul pierde pe doua paliere: nu gaseste domeniul (ghicire din denumirea legala, jeukparts.com nu se deduce din JACKSON ENGINEERING UK LTD), si nu cere paginile potrivite. Rata reala de publicare e mai mare decat 2.7% (cat gaseste metoda mea, nu cat exista).

[4:20 PM] : Gasit creditsafe.com.

Cauti dupa numele firmei si returneaza VAT-ul, care s-a dovedit valid la HMRC. Al doilea serviciu comercial care face exact lookup-ul invers pe care enuntul il descrie ca inexistent ("nobody sells it, and there is no dataset to buy"), dupa vat-lookup.co.uk.

De verificat inainte sa ma bazez pe el: ToS, daca cere cont, de unde au datele, si acuratetea testata pe cele 8 VAT-uri pe care le am deja confirmate.

[4:35 PM] Citit ToS-ul Creditsafe. Sursa inchisa:

  6.1.4  screen scraping expres interzis, interzis si accesul "pentru a construi
         un produs sau serviciu care concureaza cu Serviciile"
  4.3    interzisa copierea, adaptarea sau crearea de lucrari derivate din datele
         lor fara permisiune scrisa
  6.2    acces exclusiv pentru uz intern al companiei, fara revanzare, transfer,
         distributie sau includere intr-un produs vandut
  8.3.2  la incheierea abonamentului, obligatia de a sterge toate datele
         descarcate sau stocate, in orice format
  4.1    niciun drept de proprietate asupra bazei de date

Clauza 6.1.4 acopera chiar scopul. Veridion ar construi exact un serviciu concurent. Iar 8.3.2 face imposibil un dataset permanent chiar platind abonamentul.

Sursa functioneaza (cauti dupa nume, primesti VAT valid), dar nu poate fi folosita pentru cazul din enunt in nicio forma, nici scrapata, nici cumparata legal ca input pentru un produs revandut.

La fel si vat-lookup.co.uk: "automated scraping... is prohibited" plus "our licences with the primary source do not allow us to give you the information under different terms".

Raspuns la debate topic-ul "care surse nu le-ai folosi intr-un produs pe care il vindem": Creditsafe si vat-lookup. Pentru ca termenii interzic explicit exact utilizarea asta. Le-am folosit doar manual, pe cateva firme, ca sa masor ce acoperire au.

Si o nuanta pentru premisa enuntului ("nobody sells it, and there is no dataset to buy"): datele EXISTA comercial, la cel putin doi furnizori. Nu exista e dreptul de a le reutiliza intr-un produs propriu.