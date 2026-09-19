# UK Company VAT Discovery  feasibility study

**Question:** can a UK company → VAT number dataset be built from the open web?

**Answer:** partially, and not at a coverage that solves the customer's problem. The limiting factor is not crawling. It is that most UK companies never publish their VAT number anywhere, and that verification, the only step that can tell you whether a number belongs to the right company is rate-limited by policy, not by capacity.

## Headline numbers

| | |
|---|---|
| Active companies in Companies House (2026-09 snapshot) | 5,171,600 |
| UK VAT registrations nationally (incl. sole traders) | ~2.28M |
| Theoretical ceiling: companies that could have a VAT number | ≤44% |
| Target population after filtering | 3,832,677 |
| Sample | 300, stratified, 75 per size band |

**Source A  company websites.** Domain guessed from the legal name, then homepage + /contact + /terms + /about scraped for a checksum-valid VAT pattern. **8 of 300 (2.7%)**, all 8 confirmed against HMRC and matched to the right Companies House record. Zero false positives out of 8. Rate varies 6× by company size: 8.0% for large, 1.3% for small, 0% for companies that file no accounts.

**Source B  HMRC customs data.** 207,983 unique importers (4% of the population), name and postcode only, no VAT numbers. Not a discovery source, a **prioritisation** source. Of the 16 sample companies that appear in it, **6 publish their VAT (37.5%)**, against 2.7% for the sample at large. Filtering before searching raises the hit rate by an order of magnitude, on 4% of the population.

**Source C  Common Crawl.** 104,282 pages of extracted text yielded 131 unique checksum-valid VAT numbers  roughly **1 per 800 pages**. Extrapolated across the crawl's 100,000 WET files, the order of magnitude is comparable to the entire national VAT population. Regex precision against HMRC: **97.7%**. Attribution precision, after manual review: **75%**  one in four numbers belongs to someone other than the site it was found on.

**Source D  commercial aggregators.** Two services (Creditsafe, vat-lookup.co.uk) do exactly the reverse lookup the brief describes as non-existent. Both prohibit automated extraction Creditsafe's terms additionally forbid using the data to build a competing service and require deletion on termination. The data exists. The right to redistribute it does not.

## What I'd flag before promising this to a customer

1. **Verification is the bottleneck, not discovery.** After ~130 checks in one day, at 2–5s intervals, with an identifying user-agent, the public checker returned 429 and kept returning it for over an hour. The application itself answers in 12ms the limit is CDN policy. More machines do not fix this.
2. **A quarter of web-harvested numbers are attributed to the wrong company**, and the largest single cause is systematic: web agencies leave their own VAT in the footer of sites they build for clients. 8 of my 12 false positives.
3. **"Not found" is ambiguous and stays ambiguous.** There is no way to separate "this company has no VAT number" from "I failed to find it", so recall cannot be reported honestly. Only precision can.
4. **The mapping is not one-to-one.** VAT group registrations mean one number can cover several companies, and sole traders hold VAT numbers that will never match a Companies House row.

**For the customer in the brief:** of 26,000 suppliers missing a VAT number, the website route would recover roughly 700. Prioritising by customs presence would find ~600 of ~1,600 candidates at far lower cost per company. Neither closes the
gap.

## How to reproduce

.
├── src/ # all code
├── data/
│ ├── MANIFEST.md # source files: URL, download date, sha256, row count
│ ├── raw/ # gitignored  re-downloadable inputs
│ └── sample.csv # the 300 companies this report measures (committed)
├── results/ # every number in this report traces to a file here
├── fixtures/hmrc/vrn.csv # HMRC sandbox mock VRNs
└── research-log.md # chronological working notes, written as I went


### Inputs

Not committed they are large and re-downloadable. `data/MANIFEST.md` records the exact URL, download timestamp, sha256 and row count for each, because every figure below is tied to a specific snapshot.

| source | licence | what it is |
|---|---|---|
| Companies House basic company data, 2026-09-01 | Open Government Licence v3.0 | 5.69M rows, all live UK companies |
| HMRC `uktradeinfo` importer details, Jan–Jun 2026 | Open Government Licence v3.0 | 657,580 rows, importer names and postcodes |
| Common Crawl CC-MAIN-2026-34, 5 of 100,000 WET files | - | 104,282 pages of extracted text |

### Pipeline

Run in order. Each step writes to `results/` and is resumable re-running skips what is already cached.

| # | script | produces | what it does |
|---|---|---|---|
| 1 | `population_profile.py` | `population_profile.json` | Profiles the raw snapshot: status, account category, SIC division, incorporation decade |
| 2 | `sic99_98_uncertainty.py` | stdout | Checks what SIC 98/99 actually contain and whether they overlap with the DORMANT account category |
| 3 | `population_to_test_on.py` | `population_to_test_on.json` | Applies the target-population filter and records how many companies each criterion removed |
| 4 | `build_sample.py` | `data/sample.csv` | Draws 75 companies from each of 4 size bands by reservoir sampling, fixed seed |
| 5 | `discovery_1_website.py` | `discovery_web.jsonl` | Guesses a domain per company, fetches up to 7 pages, extracts checksum-valid VAT candidates |
| 6 | `discovery_2_uktradeinfo.py` | stdout | Measures how many sample companies appear in HMRC customs data |
| 7 | `discovery_3_commoncrawl.py` | `commoncrawl_vats.jsonl` | Harvests VAT candidates from Common Crawl text, recording the URL each came from |
| 8 | `checker.py` | `checks.jsonl` | Verifies candidates against HMRC and stores the registered name and address |
| 9 | `compare_url_with_company.py` | stdout | Measures regex precision and attribution precision for the Common Crawl route |
|  | `compare_address.py` | stdout | Compares HMRC-returned addresses against Companies House records |

### Shared modules

| module | responsibility |
|---|---|
| `config.py` | Constants, the `CheckResult` type, and the population filter shared by steps 3 and 4 so the sample can never drift from the population it was drawn from |
| `hmrc_checker.py` | One verification: session, CSRF token, POST, verdict from the redirect `Location` |
| `html_parser.py` | Extracts the registered name, address and postcode from a result page |
| `html_storage.py` | Saves raw HTML and maintains the local result cache |

### Access parameters

These are deliberate choices, not tuning knobs, and section 4.1 explains each:

| | |
|---|---|
| Delay between requests | 2s initially, 10s after hitting a rate limit |
| Concurrency | none  the result lives in the session, not the URL |
| User-agent | identifies the project and gives a contact address |
| Caching | every result stored locally; a number is never re-requested |

### Verification status

131 candidates were extracted from Common Crawl. **53 were verified against HMRC** (result in `checks.jsonl`) before the checker began returning 429 and continued to do so for over an hour. The remaining 78 are listed in `commoncrawl_vats.jsonl` but carry no verdict, and no figure in this report is computed from them. Section 4.1 treats the rate limit as a finding rather than an obstacle.