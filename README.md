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

## The problem, restated

The brief asks whether a dataset can be built. Before measuring anything, three properties of the problem determine what "measuring" can even mean.

**The verifier runs backwards.** HMRC will confirm any VAT number you hand it and return the registered name and address. It will not take a company name and give you a number. So verification is an oracle for numbers you already have, never a source of numbers. Every pipeline must therefore produce candidates elsewhere and use HMRC only to confirm them.

**Verification is not a yes/no.** Because the checker returns a name and address, "this number is registered" and "this number belongs to my company" are different questions. A number can pass HMRC and still be wrong for the Companies House row you are trying to enrich. Four outcomes, not two:

| | |
|---|---|
| not registered | reject |
| registered, entity clearly matches | accept |
| registered, entity clearly does not match | **reject this is the dangerous one** |
| registered, cannot decide | uncertain |

The third case is where false positives are born, and the fourth is where an honest pipeline has to admit defeat rather than guess. Given that a wrong numberis more expensive than a gap, I reject the uncertain cases and count them separately.

**"Not found" is two different results wearing the same clothes.** With 5.17M active companies and ~2.28M national VAT registrations a figure that includes sole traders who appear nowhere in Companies House fewer than 44% of companies can possibly hold a VAT number, and realistically far fewer. When a search comes back empty, the company may simply not be registered. There is no reference dataset that would let me tell the two apart, which is why this report states precision and deliberately does not state recall.

## How to reproduce
```
.
├── src/ # all code
├── data/
│ ├── MANIFEST.md # source files: URL, download date, sha256, row count
│ ├── raw/ # gitignored  re-downloadable inputs
│ └── sample.csv # the 300 companies this report measures (committed)
├── results/ # every number in this report traces to a file here
├── fixtures/hmrc/vrn.csv # HMRC sandbox mock VRNs
└── research-log.md # chronological working notes, written as I went
```

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
| Caching | every result stored locally, a number is never re-requested |

### Verification status

131 candidates were extracted from Common Crawl. **53 were verified against HMRC** (result in `checks.jsonl`) before the checker began returning 429 and continued to do so for over an hour. The remaining 78 are listed in `commoncrawl_vats.jsonl` but carry no verdict, and no figure in this report is computed from them. Section 4.1 treats the rate limit as a finding rather than an obstacle.

## Part 1 Research

### Verification is the bottleneck, not discovery

I expected the hard part to be finding numbers. It is, but verification turned out to be the binding constraint on everything downstream, so it is worth establishing first: it determines what can be measured at all, and it is where I spent the first two days.

#### The official route is closed for this purpose

HMRC's Check a UK VAT Number API v2.0 is the sanctioned way to verify programmatically. Version 1 was withdrawn in February 2025 and v2 sits behind OAuth 2.0. Production credentials take roughly two weeks to approve and require passing a terms-of-use questionnaire that asks for an organisation URL, evidence of registration, a privacy policy, terms and conditions, penetration testing results, and WCAG AA conformance.

None of that applies to a developer with no product, no customers and no user data. But the deeper mismatch is the stated scope: the API exists **"for the sole purpose of allowing traders to do due diligence on VAT-registered businesses."** Bulk-validating automatically discovered candidates to build a dataset is not that, whichever HTTP call it makes.

I registered for sandbox access and built a working client against it. The sandbox accepts only the fictitious VRNs shipped in `vrn.csv` confirmed rather than assumed, since one of them (553557881) returns `/unknown` on the live service. So the sandbox can exercise code but cannot validate a single real discovery.

**Decision: I did not pursue production access.** Not because of the two-week timeline, but because my purpose does not fall within the purpose the API is offered for. That is a decision I would make the same way with a month to spare.

#### What I used instead, and on what basis

The public checker at `gov.uk/check-uk-vat-number` verifies real numbers with no authentication. Before automating anything against it I checked what the service says about automated access:

| | |
|---|---|
| `www.gov.uk/robots.txt` | Disallows only `/*/print$` and `/search/all*`. Named blocks on `deepcrawl` and `MS Search 6.0`, both annotated in the file as making too many requests. `Crawl-delay: 10` for AhrefsBot. |
| `www.tax.service.gov.uk/robots.txt` | 404 no file, no directives |
| Terms and conditions (last updated April 2005) | *"Our website is maintained for your personal use and viewing"*, *"in a manner that does not restrict or inhibit the use and enjoyment of this site by any third party"*. No mention of scraping, automation, bulk or systematic access. |
| Response headers | `x-robots-tag: noindex, nofollow` |

Two things follow. First, nothing explicitly prohibits automated access, and the only documented concern visible in which bots are blocked and why is **volume**, not method. Second, "personal use and viewing" is the restrictive phrase, and it predates the checker by well over a decade.

So: a few hundred checks at a deliberate pace, for a technical evaluation, sits comfortably inside reasonable use. A commercial product continuously validating against this endpoint does not, and I would not build one on it. That answers one of the debate topics, and section 7 returns to it.

#### How the service actually works

| | |
|---|---|
| Request | `POST /check-vat-number/enter-vat-details` with `csrfToken`, `target`, `requester` |
| Response | `303 See Other` |
| Verdict | Read from the `Location` header: `/known` or `/unknown` |
| Session | CSRF token is reusable for the session one GET up front, then one POST per check |
| Caching | `Cache-Control: no-cache, no-store` every check reaches the server |

Three consequences shaped the client:

**The verdict is in the redirect, not the page.** With `allow_redirects=False` a
negative result costs one request and a positive result two. Parsing is needed
only for the name and address. If the page layout changes, verdict extraction
does not break.

**The result lives in the session, not the URL.** `/known` is a fixed path with
no VRN in it. Two concurrent requests on one session would overwrite each other's
result which is how a number gets attached to the wrong company. So: strictly
sequential, and the parser cross-checks the VRN displayed on the result page
against the one requested, raising rather than returning on mismatch.

**A script is lighter than a browser.** A human check loads 10 requests and
~10.7 kB CSS, JavaScript, fonts, Google Tag Manager, an SVG. The client makes
one or two and executes no JavaScript, so it also fires no analytics events and
does not distort the service's own usage figures.

#### Access parameters

| | |
|---|---|
| Delay | 2s between requests, raised to 10s after the rate limit was hit |
| Concurrency | None |
| User-agent | `vat-identifier-discovery/0.1 (contact: …)` |
| Caching | Every result persisted locally, no number requested twice |

The user-agent is the one worth defending. If someone at HMRC looks at their logs and sees unusual traffic, they should be able to tell immediately what it is and who to contact. A user-agent imitating Chrome would be an attempt to hide and if hiding were the correct choice, the activity would not be appropriate in the first place.

#### The rate limit, and why it is a finding

After roughly 130 checks in one day, the service returned `429 Too Many Requests`. It kept returning it for over an hour, including on fresh sessions.

| observation | |
|---|---|
| Source | CloudFront (`x-cache`, `via`, `x-amz-cf-pop`) CDN, not the application |
| `Retry-After` | Absent. `Content-Length: 0`. Checked with a HEAD request. |
| Which request failed | The GET for the result page, not the POST |
| Application latency | `x-envoy-upstream-service-time: 12` the service answers in 12ms |

The last row is the important one. The limit has nothing to do with server capacity. It is policy, applied at the edge, and **it does not yield to more machines, more bandwidth or more parallelism.** Any pipeline that needs to validate millions of candidates runs into it immediately, and the only way through is contractual access to the official API which carries its own limits and its own declared purpose.

That closes a loop with the brute-force debate topic: the reason enumeration is infeasible is not arithmetic, it is that the service will not serve it.

#### One bug worth reporting

The rate limit exposed a fault in my own code. The client checked the redirect but not the status of the result-page GET. When a 429 arrived, the parser found nothing and the record was written as `VALID` with an empty name **80 of 128 checks were failures recorded as successes.**

I deleted them and re-ran. The fix was to treat a missing name on a `/known` page as an error rather than a result, and to separate `ERROR` from `UNKNOWN` throughout, so that a network failure can never be counted as "this company is not registered". `ERROR` is retried on a later run, `UNKNOWN` is cached as an answer.

This is the class of bug that silently degrades a dataset: nothing crashed, nothing looked wrong, and the numbers would have been quietly false.