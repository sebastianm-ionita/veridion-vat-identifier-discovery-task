# UK Company VAT Discovery: feasibility study

**Question:** can a dataset mapping UK companies to their VAT numbers be built from the open web?

**Answer:** partially, and not at a coverage that solves the customer's problem. The limiting factor is not crawling. It is that most UK companies never publish their VAT number anywhere, and that verification, the only step that can tell you whether a number belongs to the right company, is rate-limited by policy, not by capacity.

## 1. Summary

| | |
|---|---|
| Active companies in Companies House (2026-09 snapshot) | 5,171,600 |
| UK VAT registrations nationally (incl. sole traders) | ~2.28M |
| Theoretical ceiling: companies that could have a VAT number | at most 44% |
| Target population after filtering | 3,832,642 |
| Sample | 300, stratified, 75 per size band |

**Source A: company websites.** Domain guessed from the legal name, then homepage + /contact + /terms + /about scraped for a checksum-valid VAT pattern. **8 of 300 (2.7%)**, all 8 confirmed against HMRC and matched to the right Companies House record. Zero false positives out of 8. Rate varies 6x by company size: 8.0% for large, 1.3% for small, 0% for companies that file no accounts.

**Source B: HMRC customs data.** 207,983 unique importers (4% of the population), name and postcode only, no VAT numbers. Not a discovery source, a **prioritisation** source. Of the 16 sample companies that appear in it, **6 publish their VAT (37.5%)**, against 2.7% for the sample at large. Filtering before searching raises the hit rate by an order of magnitude, on 4% of the population.

**Source C: Common Crawl.** 104,282 pages of extracted text yielded 131 unique checksum-valid VAT numbers, roughly **1 per 800 pages**. Extrapolated across the crawl's 100,000 WET files, the order of magnitude is comparable to the entire national VAT population. Regex precision against HMRC: **97.7%**. Attribution precision, after manual review: **75%**, so one in four numbers belongs to someone other than the site it was found on.

**Source D: commercial aggregators.** Two services (Creditsafe, vat-lookup.co.uk) do exactly the reverse lookup the brief describes as non-existent. Both prohibit automated extraction, and Creditsafe's terms additionally forbid using the data to build a competing service and require deletion on termination. The data exists. The right to redistribute it does not.

### What I'd flag before promising this to a customer

1. **Verification is the bottleneck, not discovery.** After ~130 checks in one day, at 2-5s intervals, with an identifying user-agent, the public checker returned 429 and kept returning it for over an hour. The application itself answers in 12ms; the limit is CDN policy. More machines do not fix this.
2. **A quarter of web-harvested numbers are attributed to the wrong company**, and the largest single cause is systematic: web agencies leave their own VAT in the footer of sites they build for clients. 8 of my 12 false positives.
3. **"Not found" is ambiguous and stays ambiguous.** There is no way to separate "this company has no VAT number" from "I failed to find it", so recall cannot be reported honestly. Only precision can.
4. **The mapping is not one-to-one.** VAT group registrations mean one number can cover several companies, and sole traders hold VAT numbers that will never match a Companies House row.

**For the customer in the brief:** of 26,000 suppliers missing a VAT number, the website route would recover between roughly 340 and 700, depending on how the supplier mix compares with the population (section 5.3). Prioritising by customs presence would find ~600 of ~1,600 candidates at far lower cost per company. Neither closes the gap.

## 2. The problem, restated

The brief asks whether a dataset can be built. Before measuring anything, three properties of the problem determine what "measuring" can even mean.

**The verifier runs backwards.** HMRC will confirm any VAT number you hand it and return the registered name and address. It will not take a company name and give you a number. So verification is an oracle for numbers you already have, never a source of numbers. Every pipeline must therefore produce candidates elsewhere and use HMRC only to confirm them.

**Verification is not a yes/no.** Because the checker returns a name and address, "this number is registered" and "this number belongs to my company" are different questions. A number can pass HMRC and still be wrong for the Companies House row you are trying to enrich. Four outcomes, not two:

| | |
|---|---|
| not registered | reject |
| registered, entity clearly matches | accept |
| registered, entity clearly does not match | **reject: this is the dangerous one** |
| registered, cannot decide | uncertain |

The third case is where false positives are born, and the fourth is where an honest pipeline has to admit defeat rather than guess. Given that a wrong number is more expensive than a gap, I reject the uncertain cases and count them separately.

**"Not found" is two different results wearing the same clothes.** With 5.17M active companies and ~2.28M national VAT registrations, a figure that includes sole traders who appear nowhere in Companies House, fewer than 44% of companies can possibly hold a VAT number, and realistically far fewer. When a search comes back empty, the company may simply not be registered. There is no reference dataset that would let me tell the two apart, which is why this report states precision and deliberately does not state recall.

## 3. How to reproduce
```
.
|-- src/                    # all code
|-- data/
|   |-- MANIFEST.md         # source files: URL, download date, sha256, row count
|   |-- raw/                # gitignored, re-downloadable inputs
|   `-- sample.csv          # the 300 companies this report measures (committed)
|-- results/                # every number in this report traces to a file here
|-- fixtures/hmrc/vrn.csv   # HMRC sandbox mock VRNs
`-- research-log.md         # chronological working notes, written as I went
```

### Inputs

Not committed: they are large and re-downloadable. `data/MANIFEST.md` records the exact URL, download timestamp, sha256 and row count for each, because every figure below is tied to a specific snapshot.

| source | licence | what it is |
|---|---|---|
| Companies House basic company data, 2026-09-01 | Open Government Licence v3.0 | 5.69M rows, all live UK companies |
| HMRC `uktradeinfo` importer details, Jan-Jun 2026 | Open Government Licence v3.0 | 657,580 rows, importer names and postcodes |
| Common Crawl CC-MAIN-2026-34, 5 of 100,000 WET files | - | 104,282 pages of extracted text |

### Pipeline

Run in order. Each step writes to `results/` and is resumable: re-running skips what is already cached.

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
| - | `compare_address.py` | stdout | Compares HMRC-returned addresses against Companies House records |

### Shared modules

| module | responsibility |
|---|---|
| `config.py` | Constants, the `CheckResult` type, and the population filter, shared by steps 3 and 4 so the sample can never drift from the population it was drawn from |
| `hmrc_checker.py` | One verification: session, CSRF token, POST, verdict from the redirect `Location` |
| `html_parser.py` | Extracts the registered name, address and postcode from a result page |
| `html_storage.py` | Saves raw HTML and maintains the local result cache |

### Access parameters

These are deliberate choices, not tuning knobs, and section 4.1 explains each:

| | |
|---|---|
| Delay between requests | 2s initially, 10s after hitting a rate limit |
| Concurrency | none: the result lives in the session, not the URL |
| User-agent | identifies the project and gives a contact address |
| Caching | every result stored locally; a number is never re-requested |

### Verification status

All 131 candidates harvested from Common Crawl received a verdict from HMRC,
read from the redirect: 128 registered, 3 not. For 80 of the 128, the follow-up
request for the registered name hit the rate limit, so their verdict is known
but their name is not (section 4.1). The first run, with those verdicts, is kept
in `results/old_checks.jsonl`.

Names were retrieved for 48 numbers when the attribution analysis in 4.5 was
run, and every attribution figure in this report is computed on those 48. The
rate limit then blocked the re-run for over an hour. I report the numbers as
they stood rather than wait for a complete set, and section 4.1 treats the rate
limit as a finding rather than an obstacle.

## 4. Part 1 - Research

### 4.1 Verification is the bottleneck, not discovery

I expected the hard part to be finding numbers. It is, but verification turned out to be the binding constraint on everything downstream, so it is worth establishing first: it determines what can be measured at all, and it is where I spent the first two days.

#### The official route is closed for this purpose

HMRC's Check a UK VAT Number API v2.0 is the sanctioned way to verify programmatically. Version 1 was withdrawn in February 2025 and v2 sits behind OAuth 2.0. Production credentials take roughly two weeks to approve and require passing a terms-of-use questionnaire that asks for an organisation URL, evidence of registration, a privacy policy, terms and conditions, penetration testing results, and WCAG AA conformance.

None of that applies to a developer with no product, no customers and no user data. But the deeper mismatch is the stated scope: the API exists **"for the sole purpose of allowing traders to do due diligence on VAT-registered businesses."** Bulk-validating automatically discovered candidates to build a dataset is not that, whichever HTTP call it makes.

I registered for sandbox access and built a working client against it. The sandbox accepts only the fictitious VRNs shipped in `vrn.csv`. That is confirmed rather than assumed: one of them (553557881) returns `/unknown` on the live service. So the sandbox can exercise code but cannot validate a single real discovery.

**Decision: I did not pursue production access.** Not because of the two-week timeline, but because my purpose does not fall within the purpose the API is offered for. That is a decision I would make the same way with a month to spare.

#### What I used instead, and on what basis

The public checker at `gov.uk/check-uk-vat-number` verifies real numbers with no authentication. Before automating anything against it I checked what the service says about automated access:

| | |
|---|---|
| `www.gov.uk/robots.txt` | Disallows only `/*/print$` and `/search/all*`. Named blocks on `deepcrawl` and `MS Search 6.0`, both annotated in the file as making too many requests. `Crawl-delay: 10` for AhrefsBot. |
| `www.tax.service.gov.uk/robots.txt` | 404: no file, no directives |
| Terms and conditions (last updated April 2005) | *"Our website is maintained for your personal use and viewing"*, *"in a manner that does not restrict or inhibit the use and enjoyment of this site by any third party"*. No mention of scraping, automation, bulk or systematic access. |
| Response headers | `x-robots-tag: noindex, nofollow` |

Two things follow. First, nothing explicitly prohibits automated access, and the only documented concern, visible in which bots are blocked and why, is **volume**, not method. Second, "personal use and viewing" is the restrictive phrase, and it predates the checker by well over a decade.

So: a few hundred checks at a deliberate pace, for a technical evaluation, sits comfortably inside reasonable use. A commercial product continuously validating against this endpoint does not, and I would not build one on it. That answers one of the debate topics, and section 7 returns to it.

#### How the service actually works

| | |
|---|---|
| Request | `POST /check-vat-number/enter-vat-details` with `csrfToken`, `target`, `requester` |
| Response | `303 See Other` |
| Verdict | Read from the `Location` header: `/known` or `/unknown` |
| Session | CSRF token is reusable for the session: one GET up front, then one POST per check |
| Caching | `Cache-Control: no-cache, no-store`: every check reaches the server |

Three consequences shaped the client:

**The verdict is in the redirect, not the page.** With `allow_redirects=False` a
negative result costs one request and a positive result two. Parsing is needed
only for the name and address. If the page layout changes, verdict extraction
does not break.

**The result lives in the session, not the URL.** `/known` is a fixed path with
no VRN in it. Two concurrent requests on one session would overwrite each other's
result, which is how a number gets attached to the wrong company. So: strictly
sequential, and the parser cross-checks the VRN displayed on the result page
against the one requested, raising rather than returning on mismatch.

**A script is lighter than a browser.** A human check loads 10 requests and
~10.7 kB: CSS, JavaScript, fonts, Google Tag Manager, an SVG. The client makes
one or two and executes no JavaScript, so it also fires no analytics events and
does not distort the service's own usage figures.

#### Access parameters

| | |
|---|---|
| Delay | 2s between requests, raised to 10s after the rate limit was hit |
| Concurrency | None |
| User-agent | `vat-identifier-discovery/0.1 (contact: sebi.ionita23@gmail.com)` |
| Caching | Every result persisted locally; no number requested twice |

The user-agent is the one worth defending. If someone at HMRC looks at their logs and sees unusual traffic, they should be able to tell immediately what it is and who to contact. A user-agent imitating Chrome would be an attempt to hide, and if hiding were the correct choice, the activity would not be appropriate in the first place.

#### The rate limit, and why it is a finding

After roughly 130 checks in one day, the service returned `429 Too Many Requests`. It kept returning it for over an hour, including on fresh sessions.

| observation | |
|---|---|
| Source | CloudFront (`x-cache`, `via`, `x-amz-cf-pop`): CDN, not the application |
| `Retry-After` | Absent. `Content-Length: 0`. Checked with a HEAD request. |
| Which request failed | The GET for the result page, not the POST |
| Application latency | `x-envoy-upstream-service-time: 12`: the service answers in 12ms |

The last row is the important one. The limit has nothing to do with server capacity. It is policy, applied at the edge, and **it does not yield to more machines, more bandwidth or more parallelism.** Any pipeline that needs to validate millions of candidates runs into it immediately, and the only way through is contractual access to the official API, which carries its own limits and its own declared purpose.

That closes a loop with the brute-force debate topic: the reason enumeration is infeasible is not arithmetic, it is that the service will not serve it.

#### One bug worth reporting

The rate limit exposed a fault in my own code. The client read the verdict from
the redirect correctly, but did not check the status of the follow-up request for
the result page. When that request got a 429, the parser found nothing and the
record was written as a complete `VALID` result with an empty name. **80 of 128
records looked complete while missing the one field attribution depends on.**
The verdicts were right; the records were not.

The fix was to treat a missing name on a `/known` page as an error rather than a
result, and to separate `ERROR` from `UNKNOWN` throughout, so that a network
failure can never be counted as "this company is not registered". `ERROR` is
retried on a later run; `UNKNOWN` is cached as an answer. I removed the
incomplete records from `checks.jsonl`, kept the first run in
`results/old_checks.jsonl` as the evidence for the verdicts, and re-ran.

This is the class of bug that silently degrades a dataset: nothing crashed, nothing looked wrong, and the numbers would have been quietly false.

### 4.2 What the population actually looks like

Before choosing where to look, I profiled the whole Companies House snapshot. The brief's framing and the real population differ in ways that change every rate reported later.

| | |
|---|---|
| Rows in snapshot | 5,689,367 |
| Status "Active" | 5,171,600 |
| Status "Active - Proposal to Strike off" | 401,947 |

The active population is larger than the brief states, which makes the ceiling lower: about 2.28M VAT registrations nationally, a figure that includes sole traders who never appear in Companies House, against 5.17M active companies. At most 44% of companies can hold a VAT number of their own, and realistically far fewer.

#### Most companies are small, young, or not trading

The accounts filing category is the only size signal in the file. The legal thresholds that decide which accounts a company must file make it a usable proxy.

| account category | companies | share of active |
|---|---|---|
| MICRO ENTITY | 1,668,834 | 32.3% |
| NO ACCOUNTS FILED | 1,347,758 | 26.1% |
| TOTAL EXEMPTION FULL | 1,227,653 | 23.7% |
| DORMANT | 565,741 | 10.9% |
| FULL + MEDIUM + GROUP | 112,450 | 2.2% |

Four categories hold 93% of active companies. Dormant companies do not trade by definition. Companies with no accounts filed are largely newly incorporated or never started trading.

By incorporation date, 55% of active companies (2,854,461) were formed in the 2020s, and 83% in the last 16 years.

No SIC division dominates: the largest, 68 (real estate), holds 12%. 216,320 companies have no SIC code at all.

A sample drawn uniformly from 5.17M would be dominated by micro, dormant and very young companies, most of which structurally cannot hold a VAT number. Section 5.1 covers how I handled that.

#### Two SIC divisions that were not what they looked like

Divisions 98 and 99 were unusually large for what the classification says they represent. Among active companies:

| code | companies | description |
|---|---|---|
| 98000 | 124,043 | Residents property management |
| 99999 | 97,473 | Dormant Company |
| 98200 | 606 | Undifferentiated service-producing activities of private households |
| 99000 | 554 | Activities of extraterritorial organisations |
| 98100 | 469 | Undifferentiated goods-producing activities of private households |
| 9999 | 69 | Dormant company |
| 9800 | 4 | Residents property management |

I had guessed both were dormancy markers. Half right. 99999 is one. 98000 is not: it is 124,000 residents' management companies, where leaseholders collectively own the company that runs their building. Real, active, and almost certainly never a supplier to a manufacturer. The two dormancy signals overlap but are not the same thing. Of 97,542 active companies coded 99999 or 9999, 71.8% are also DORMANT by account category, against a 10.9% base rate. And 27,482 of them declare themselves dormant by SIC while filing active-company accounts. The source contradicts itself, and I cannot tell which field is right.

#### The reference data is not clean

This came up repeatedly, and it matters because the whole method depends on matching against these sources:

- **Impossible incorporation dates.** Active companies dated to the 1320s, 1410s and 1500s. Companies House was established in 1844.
- **Inconsistent code formats.** The same SIC activity appears in 4-digit and 5-digit form (99999 and 9999, 98000 and 9800).
- **Contradictory fields.** The 27,482 companies above.
- **Typos in HMRC's own records.** The address returned for BP International reads "CHERSTEY ROAD". The road is Chertsey Road.

None of these is large. Together they mean no source can be treated as ground truth, including the verifier.


### 4.3 Source A: company websites

The obvious route, and the one the brief anticipates when it notes that some contexts legally require a VAT number to be published. UK electronic commerce regulations require online service providers to make their VAT number easily accessible, which is why it turns up in footers and terms pages.

**Method.** For each of the 300 sample companies:

1. Guess a domain from the legal name: strip the legal suffix, build a concatenated slug and a hyphenated variant, try each on `.co.uk`, `.com` and `.uk`.
2. Fetch the homepage plus `/contact`, `/contact-us`, `/terms`, `/terms-and-conditions`, `/about` and `/privacy`.
3. Extract candidates with two patterns: `GB` followed by nine digits, or nine digits within 40 characters after the word "VAT".
4. Discard anything that fails the mod-97 checksum.
5. Verify the survivors at HMRC and match the returned name and postcode against the Companies House record.

**Results.**

| band | n | site found | VAT found |
|---|---|---|---|
| small | 75 | 22 (29.3%) | 1 (1.3%) |
| medium | 75 | 18 (24.0%) | 1 (1.3%) |
| large | 75 | 19 (25.3%) | 6 (8.0%) |
| unknown | 75 | 22 (29.3%) | 0 (0.0%) |
| **total** | **300** | **81 (27.0%)** | **8 (2.7%)** |

All 8 passed HMRC and matched the right Companies House record. Zero false positives, though 8 cases say little about a rate.

**What the numbers mean.**

Large companies publish at 6x the rate of small ones. That is the most useful single result for the customer, because it says which suppliers this route can serve.

The site-found rate is nearly flat across bands, 24% to 29%. That does not mean 27% of companies have a website. It means guessing a domain from the legal name works 27% of the time. Large companies almost certainly have sites, at domains that do not derive from their registered name.

Companies that file no accounts yielded nothing.

**The method loses on two fronts, and I can show both.** In section 4.4 I searched by hand for the 16 sample companies that also appear in the customs data, and found a VAT number for 6. The script had found 2 of those 6. For the other 4, the log in `discovery_web.jsonl` shows why:

| company | found by script | why not |
|---|---|---|
| JAGEX LIMITED | yes | |
| ARDEN DIES LIMITED | yes | |
| ROTOSOUND MANUFACTURING LTD. | no | Real domain `rotosound.com` drops a word. Also exposed a bug: the trailing period in "LTD." stopped the suffix from being stripped, so the script tried `rotosoundmanufacturingltd.co.uk`. |
| JACKSON ENGINEERING UK LTD | no | Real domain `jeukparts.com`, not derivable from the name at all |
| GILEAD SCIENCES LTD | no | Real domain drops a word |
| FACULTATIEVE TECHNOLOGIES LIMITED | no | Site found, but the number sits on a company registration page the script does not request |

Three of four failures are domain discovery, one is page selection. **2.7% is what this method finds, not what exists.** Part 3 addresses both.


### 4.4 Source B: HMRC customs data

HMRC publishes monthly lists of businesses importing into the UK from outside the EU, under the Open Government Licence. I used January to June 2026.

| | |
|---|---|
| Rows | 657,580 across 6 monthly files |
| Format | Tab-separated, 59 fields: name, 5 address lines, postcode, up to 50 commodity codes |
| Unique (name, postcode) pairs | 207,983 |
| Share of active companies | 4% |
| VAT numbers | None |

**It is not a discovery source.** It holds no identifiers, so the question became what else it is good for.

A business importing into the UK needs an EORI number, and for VAT-registered businesses the EORI is derived from the VAT number: `GB` + VRN + `000`. So the companies in this file almost certainly hold a VAT number, even though the file does not say what it is.

**Overlap with the sample:**

| band | in customs data |
|---|---|
| small | 1/75 (1.3%) |
| medium | 2/75 (2.7%) |
| large | 13/75 (17.3%) |
| unknown | 0/75 (0.0%) |
| **total** | **16/300 (5.3%)** |

The same shape as the website results, steeper: large companies appear 13x more often than small ones.

**I then searched those 16 by hand.**

| | |
|---|---|
| VAT number published | 6 (37.5%) |
| Website, no VAT number | 8 |
| No website found | 2 |

37.5% against 2.7% for the sample at large. **Filtering on customs presence before searching raises the hit rate by an order of magnitude.** For Part 3 that is the most useful result in this report, because it changes the cost structure: 16 searches for 6 numbers instead of 300 for 8.

The limit is coverage. The filter reaches 4% of the population. For the customer's 40,000 suppliers that means roughly 1,600 worth searching and around 600 found, against about 26,000 missing.

**Sources overlap rather than add.** JAGEX and ARDEN DIES appear in both the website results and the customs data. Adding sources does not add coverage linearly, because they tend to reach the same well-documented companies. Part 3 accounts for this.


### 4.5 Source C: Common Crawl

Sources A and B both start from a company and look for its number. The brief hints this may be the wrong shape: if numbers are scattered across millions of pages, crawling site by site is slow and depends on finding the right domain, which Source A showed fails most of the time.

So I inverted the pipeline:

```
Sources A, B: company -> find website -> find number -> verify
Source C: harvest numbers -> verify -> HMRC returns the name -> match to Companies House
```


The inversion matters because HMRC returns the registered name for every valid number. Identity comes free with verification, so you no longer need to know which company you are looking for.

**Method.** Five WET files (extracted text) from crawl CC-MAIN-2026-34, the same regex and checksum as Source A, recording the URL and domain of every hit.

| | |
|---|---|
| Pages processed | 104,282 |
| Pages on `.uk` domains | 2,166 (2.1%) |
| VAT occurrences | 197 |
| Unique checksum-valid numbers | 131 |
| Numbers seen on more than one domain | 2 |

**Density: about one unique number per 800 pages.** The crawl lists 100,000 WET files, so scaling by 20,000 gives roughly 2.6M. That is an upper bound, since a full run would collapse numbers repeated across files, but the order of magnitude matches the national VAT population. It is the first result in this study suggesting the dataset might be buildable from the open web.

**Where the numbers come from.** 2.1% of pages are on `.uk` domains, but they produce 59% of occurrences. Filtering to `.uk` would process 2% of the data for most of the yield, and would also drop UK companies on `.com` domains.

#### Regex precision

All 131 numbers went through HMRC. The verdict is read from the redirect, which the rate limit did not affect, so every number has one.

| | registered at HMRC |
|---|---|
| all | 128/131 (97.7%) |
| `.uk` domains | 78/79 (98.7%) |
| other domains | 50/52 (96.2%) |

The checksum does most of the work. Almost anything that looks like a UK VAT number and passes mod-97 is one.

#### Attribution precision

The harder question: is the number registered to the company whose site it appeared on?

HMRC returned a name for 48 of the 128. The other 80 hit the rate limit on the result page (section 4.1), so their verdict is known but their name is not.

An automatic comparison of domain against HMRC name reported 16% matching. That was wrong. Brands rarely resemble legal names, the same failure as domain guessing in Source A. I reviewed every non-match by hand.

| | |
|---|---|
| Matched automatically | 21 |
| Rejected automatically, correct on review | 15 |
| Wrong | 12 |
| **Attribution precision** | **36/48 = 75%** |

Correct attributions the heuristic rejected, for example:

| domain | HMRC registered name |
|---|---|
| `kfh.co.uk` | KINLEIGH LTD (Kinleigh Folkard & Hayward) |
| `topra.org` | THE ORGANIS'N FOR PROFES'NLS IN REGULATO RY AFFAIRS LTD |
| `hussle.com` | ARCHWAY FITNESS LIMITED |
| `getmecarfinance.co.uk` | JIGSAW FINANCE LIMITED |
| `imperialengineering.co.uk` | AWD DWIGHT & SONS (ENGINEERS) LTD |

**A 4x gap between the automatic and the reviewed figure.** A production version needs a better entity matcher than string similarity, or it will throw away most of its correct results.

#### The systematic false positive

8 of the 12 wrong attributions share one cause: **web agencies leave their own VAT number in the footer of sites they build for clients.**

| found on | registered to |
|---|---|
| `cloudwaysapps.com` | MJ WEB STUDIO LIMITED |
| `british-sign.co.uk` | LISIA DIGITAL LIMITED |
| `creative-solutions-direct.co.uk` | BLUEBIRD GRAPHICS LTD |
| `everythingliquid.co.uk` | IBI MEDIA LIMITED |
| `securityjournaluk.com` | CENTURIAN MEDIA LIMITED |
| `futurevisuals.co.uk` | ALL OFFICE LIMITED |
| `staging.theaccountancy.co.uk` | PANDLE LTD |
| `staines.able-drainage.co.uk` | VIABL LTD |

This is exactly the error the brief warns about: a real number, verified by HMRC, attached to the wrong company. It passes every check a naive pipeline would run. Delivered to the customer, it would corrupt their joins and nobody would notice.

It is also detectable. One agency builds many sites, so its number appears on many unrelated domains. In this sample only 2 numbers appeared on more than one domain, too few for the signal to be reliable. At crawl scale it would be.

The other 4 wrong attributions have no shared pattern:

| found on | registered to |
|---|---|
| `boutique-retreats.co.uk` | CLASSIC COTTAGES LIMITED |
| `pearllemoncapital.co.uk` | PURR TRAFFIC LTD |
| `fasten.it` | BEARINGNET LIMITED |
| `halusky.co.uk` | JIAAN ENTERPRISES LTD |

#### What else the names revealed

- **Sole traders.** RICHARD HARKNETT (`theminiskipcompany.co.uk`) and ELAINE ELIZABETH GLEAVE, LUKE GRAHAM GLEAVE are individuals, not companies. The attribution is correct, but they will never match a Companies House row. This is the gap between the national VAT figure and the company population, made concrete.
- **Group registrations.** `greycon.com` returns VESTA SOFTWARE GROUP LIMITED, likely a VAT group registration where one number covers several companies. Correct at group level, but a name and postcode match against the subsidiary's own Companies House record would fail. The mapping is not one-to-one.
- **Formation agent addresses.** ARCHWAY FITNESS LIMITED is registered at 20-22 Wenlock Road, N1 7GU, the same address as the shell namesake of BP International that my own matching initially picked (section 5.4). Addresses shared by thousands of companies are recurring noise in any postcode match.


### 4.6 Source D: commercial aggregators

While looking for other sources, I found services that do exactly the reverse lookup the brief describes as non-existent.

**vat-lookup.co.uk** (Market Footprint Ltd) claims VAT details for over 1.5 million UK companies, searchable by name. Its terms prohibit automated scraping and extraction, and state that its licences with an unnamed "primary source" prevent it from offering the data on any other terms. The same operator's older site, datalog.co.uk, says HMRC has never released a VAT dataset and describes a crowdsourced effort holding 30 entries. The two claims do not reconcile, and neither says where 1.5 million records came from.

**Creditsafe** returns a VAT number when searched by company name, and the numbers I checked were valid at HMRC. Its terms close off every use relevant here:

| clause | effect |
|---|---|
| 6.1.4 | Screen scraping expressly prohibited; also prohibited to access the service in order to build a product or service that competes with it |
| 4.3 | No copying, adapting or creating derivative works from output data without written permission |
| 6.2 | Internal use only; no resale, transfer, distribution or inclusion in a product sold on |
| 8.3.2 | On termination, all downloaded or stored data must be deleted, in any format |
| 4.1 | No ownership rights in the database |

Clause 6.1.4 covers the purpose, not only the method: Veridion would be building precisely a competing service. And 8.3.2 makes a permanent dataset impossible even as a paying subscriber.

I used both only by hand, on a few companies, to confirm the data exists.


### 4.7 Dead ends

Each of these looked promising and failed for a specific, checkable reason.

| source | what I expected | why it failed |
|---|---|---|
| HMRC API v2, production | Programmatic verification | Stated purpose is trader due diligence, which building a dataset is not. Around 2 weeks to approve, with a questionnaire built for commercial software. Not pursued. |
| HMRC API v2, sandbox | A test harness for real numbers | Accepts only fictitious VRNs. Confirmed: 553557881 from the sandbox list returns `/unknown` on the live service. |
| EORI checker | A second verification oracle, no authentication | Confirms validity but returned no name or address for any company I tried. Businesses opt in to disclosure when registering. Without identity it cannot support entity matching. |
| data.gov.uk "VAT registered businesses" | A register of businesses | Aggregate statistics only: counts of registrations and deregistrations by region, 1994 to 2008, discontinued. No identifiers. |
| Local authority spending over GBP 25,000 | Supplier VAT numbers from published payments | The Transparency Code requires supplier name, amount, date and expense type. No VAT field. |
| HMRC customs data, as discovery | VAT numbers for importers | No VAT field. Useful as a prioritisation filter instead (4.4). |
| Domain guessing | A way to find company websites | Works 27% of the time. Brands rarely derive from legal names. |
| Enumerating the checker | Every valid number | See section 7. |

The EORI result deserves a note. The relationship `GB` + VRN + `000` is real and documented, so a published EORI number is a VAT number in disguise. That is the adjacent-identifier route the brief mentions, and it holds. What fails is using the EORI checker to establish identity: an EORI found in the wild still has to go through the VAT checker to learn whose it is.


### 4.8 What the premise gets wrong

The brief states: "Nobody sells it, and there is no dataset to buy."

That is not quite true. Two commercial services sell exactly this lookup, and the numbers they return verify. **The data exists. What does not exist is the right to redistribute it.** Every provider I found prohibits extraction, and the most explicit also prohibits building a competing service and requires deletion on termination.

So the premise holds from Veridion's commercial position, but for a different reason than it implies. It is not a gap in the data. It is a licensing wall around data someone has already assembled.

That changes the question. Not "can it be built?" but "can it be built from sources whose terms allow it to be sold?" Among the sources tested:

| | contains VAT numbers | terms allow resale |
|---|---|---|
| Companies House | no | yes (OGL v3.0) |
| HMRC customs data | no | yes (OGL v3.0) |
| Commercial aggregators | yes | no |
| Company websites, Common Crawl | yes | numbers the companies chose to publish themselves |

The last row is the only one where both columns are favourable, and it is where Part 3 concentrates.

A smaller discrepancy: the brief cites roughly 4.2 million live companies. The September 2026 snapshot has 5.17 million with status "Active", plus 402,000 with a strike-off proposal pending. The difference lowers every ceiling in this report.

## 5. Part 2 - Proof of concept

### 5.1 The sample

The brief is explicit about the trap: a sample of companies already known to publish their VAT number produces an impressive figure and teaches nothing. So the sample was fixed before any discovery source was tested, drawn at random within strata, with no knowledge of which companies publish anything.

#### Defining the target population

The customer has 40,000 suppliers: companies that invoice a manufacturer. Not all 5.17 million active companies could appear in such a list, and a sample full of companies that structurally cannot hold a VAT number would say more about the filter than about the method.

So I restricted the population to companies that could plausibly be a supplier. This is a decision about how to define the problem, not a data-cleaning step, and I flag it because it has a direct effect on the results: **every exclusion removes cases where there is nothing to find, and raises the discovery rate automatically.** The rule I held to was to exclude only what cannot trade by its nature, and never anything that correlates with publishing a VAT number. Filtering on "has a website", for example, would select exactly the companies where the method works, and measure the filter instead of the method.

| criterion | removed | reason |
|---|---|---|
| Status is not "Active" | 517,767 | Not trading |
| Account category DORMANT | 565,741 | Does not trade, by definition |
| SIC division 98 | 81,548 | Residents' management companies: active, but not suppliers |
| Incorporated less than 12 months before the snapshot | 691,634 | Activity cannot be judged from filings yet |
| Incorporation date invalid or before 1800 | 35 | Data errors |
| **Kept** | **3,832,642** | |

The filter lives in one shared module, used by both the profiling script and the sampling script, so the sample cannot drift from the population it describes. The counts of eligible companies per band reported by the two scripts match exactly.

#### The filter I replaced

My first version excluded every company with NO ACCOUNTS FILED. That removed 1.35 million companies and left 3,187,409.

It was the wrong criterion, because NO ACCOUNTS FILED mixes two different populations: companies that have never filed anything, and companies too new to have reached their first filing deadline, which is 21 months after incorporation. Excluding the whole category removed real traders along with dead ones. The effect showed up in the age profile:

| incorporated in | unfiltered | first filter | final filter |
|---|---|---|---|
| 2020s | 55.2% | 40.6% | 48.1% |
| 2010s | 28.3% | 38.4% | 33.5% |

The final filter replaces it with an explicit age criterion that does exactly what it says. Companies older than 12 months with no accounts filed stay in, as their own stratum. The population still skews older than the unfiltered one, but the skew is now intended and can be stated in one sentence.

#### Stratification

The accounts filing category is the only size signal available, and legal thresholds tie it to company size. I grouped the 14 categories into four bands:

| band | categories | companies | share |
|---|---|---|---|
| small | MICRO ENTITY, TOTAL EXEMPTION SMALL, ACCOUNTS TYPE NOT AVAILABLE, PARTIAL EXEMPTION | 1,620,885 | 42.3% |
| medium | SMALL, UNAUDITED ABRIDGED, TOTAL EXEMPTION FULL, AUDIT EXEMPTION SUBSIDIARY, FILING EXEMPTION SUBSIDIARY | 1,452,459 | 37.9% |
| large | FULL, MEDIUM, GROUP, AUDITED ABRIDGED | 113,471 | 3.0% |
| unknown | NO ACCOUNTS FILED | 645,827 | 16.9% |

"Unknown" is a band of its own because these companies are over 12 months old but have never filed. Nothing in the data says whether they are large or small, and at 17% of the population they are too many to drop or assign arbitrarily.

#### Allocation: equal, not proportional

**75 companies per band, 300 in total.**

Proportional allocation would give the large band about 9 companies, too few to say anything about it. Equal allocation supports the statement that matters most to the customer: *the rate is X for large suppliers and Y for small ones*, which answers which suppliers this can serve.

The cost is that the sample no longer mirrors the population, so a single overall rate must be re-weighted by the true band sizes. Section 5.3 reports both, with the formula.

#### Drawing it

Reservoir sampling, one pass over the 2.6 GB file, holding exactly 75 records per band in memory rather than 1.6 million. The first 75 eligible companies in a band enter directly; the n-th enters with probability 75/n, replacing one at random. Every eligible company ends up in the sample with equal probability, and the total does not need to be known in advance.

Fixed seed (23), so the same 300 companies are reproducible from the same snapshot. The result is committed as `data/sample.csv`, with no duplicate company numbers.


### 5.2 The pipeline

```
candidate VAT number (from Source A or Source C)
    |
    v
mod-97 checksum  -> discard if invalid
    |
    v
HMRC checker     -> UNKNOWN / MALFORMED / ERROR
    |  VALID: registered name + address
    v
entity match     -> REJECT / UNCERTAIN
    |  ACCEPT
    v
(company number, VAT number)
```


**Verdicts are four-valued, not boolean.**

| verdict | meaning | cached |
|---|---|---|
| VALID | Registered; name and address retrieved | yes |
| UNKNOWN | Not registered | yes |
| MALFORMED | Rejected by the form's validation | yes |
| ERROR | No answer: timeout, 429, parse failure | **no, retried** |

ERROR is separate from UNKNOWN because a timeout is not an answer. Merged, a network failure would be counted as "this company has no VAT number". The rate-limit bug in section 4.1 was the same class of error in the other direction: 80 failed lookups recorded as complete results.

**The checksum is filtered locally.** The service does not apply it: GB111111111, GB999999999, GB555555555 and GB123456789 all fail mod-97 and all return UNKNOWN rather than MALFORMED. Validation stops at format (prefix, nine digits, no letters). So the only way to avoid spending requests on impossible numbers is to check them before sending.

**Entity matching.** HMRC returns a name and address. Matching them to the right Companies House record follows three rules, each learned from a failure described in 5.4:

1. A name match produces a **list** of candidates, not an answer. Companies House holds distinct companies with identical normalised names.
2. The **postcode** decides among them. It is structured, normalisable, and the only field directly comparable between the two sources.
3. If no candidate matches on postcode, the result is **UNCERTAIN**, rejected, and counted separately. Never "the first one found".

**Client test.** Before any real run, the checker went through 27 numbers built to cover every path: 13 real VAT numbers, 11 deliberately invalid ones and 3 malformed. Output 13 VALID, 11 UNKNOWN, 3 MALFORMED. Also confirmed: a second run served everything from cache, an interrupted run resumed where it stopped, and every VALID result had its HTML saved.


### 5.3 Results

#### Source A: company websites, on the full sample

| band | n | VAT found | rate | 95% CI |
|---|---|---|---|---|
| small | 75 | 1 | 1.3% | 0.2 - 7.2% |
| medium | 75 | 1 | 1.3% | 0.2 - 7.2% |
| large | 75 | 6 | 8.0% | 3.7 - 16.4% |
| unknown | 75 | 0 | 0.0% | 0.0 - 4.9% |
| **sample** | **300** | **8** | **2.7%** | **1.4 - 5.2%** |

Confidence intervals are Wilson score intervals. They are wide, and they are there to be read: a band rate of 1.3% on 75 companies is compatible with anything from 0.2% to 7%.

**The 2.7% is the sample rate, not the population rate.** Large companies are 25% of the sample but 3% of the population, and they are the band that publishes most. Re-weighting each band's rate by its true size:

rate = sum over bands of (companies in band x band rate) / all companies

```
   1,620,885 x 1/75  +  1,452,459 x 1/75  +  113,471 x 6/75  +  645,827 x 0
 = -----------------------------------------------------------------------
                              3,832,642

 = 1.3%
```

| population | estimated rate |
|---|---|
| Sample, as drawn | 2.7% |
| Filtered population, re-weighted | **1.3%** |
| All 5.17M active companies, if excluded companies yield nothing | 1.0% |

The last row assumes that dormant, very young and residents' management companies publish no VAT number. That is likely, but it is unmeasured.

**Which rate applies to the customer depends on who their suppliers are.** A manufacturer's suppliers are not a random draw from UK companies: they invoice, so they skew towards trading and larger firms. The customer's true rate sits somewhere between 1.3% and the rates for the medium and large bands. For the 26,000 suppliers without a VAT number, that is between roughly 340 and 700 recovered.

#### Source B: customs data as a filter

| | |
|---|---|
| Sample companies found in customs data | 16/300 (5.3%, CI 3.3 - 8.5%) |
| Re-weighted to the population | 2.1% |
| Of those 16, VAT number found by hand | 6/16 (37.5%, CI 18.5 - 61.4%) |

Even at the bottom of its confidence interval, 18.5%, the filtered rate is 7x the unfiltered 2.7%. The order-of-magnitude claim survives the uncertainty.

#### Source C: Common Crawl

| | | 95% CI |
|---|---|---|
| Unique checksum-valid numbers | 131 from 104,282 pages | |
| Registered at HMRC | 128/131 (97.7%) | 93.5 - 99.2% |
| Registered name retrieved | 48 | |
| Attributed to the right company | 36/48 (75.0%) | 61.2 - 85.1% |

These are not rates on the sample. Source C starts from the web, not from the 300 companies, and none of the 131 numbers belongs to a sample company, which is what you would expect when drawing 300 companies from 3.8 million.


### 5.4 False positives: measured

The brief asks for the false-positive rate, how it was measured, and on what. Three measurements, from three different stages.

#### Source A: 0 of 8

All 8 numbers found on company websites were registered at HMRC, and the returned name and postcode matched the sample company's Companies House record.

**Zero false positives, but not a zero rate.** On 8 cases, the 95% upper bound is 32%: the data is consistent with up to one in three being wrong. The honest claim is that numbers published in a company's own footer or terms page tend to belong to that company, which is plausible, and that 8 cases do not prove it.

#### Source C: 12 of 48

Measured by checking each harvested number at HMRC, then comparing the registered name against the site the number was found on, then reviewing every non-match by hand.

**25% false positives (CI 14.9 - 38.8%).** Two-thirds of them come from one mechanism, agencies leaving their own number on client sites (section 4.5).

The contrast with Source A is the useful part. A number on a company's own site, found by looking for that company, is almost always theirs. A number found on an arbitrary page belongs to the site owner only three times in four. Harvesting buys coverage at the price of precision, and the price is measurable.

#### My own matching: the BP case

The third false positive was produced by my code, not by a source, and it changed how I match.

Testing the client, I verified 13 VAT numbers of large, well-known companies and compared the addresses HMRC returned against Companies House:

| | |
|---|---|
| Postcode matches | 11/13 |
| Genuine address difference | 1 (Royal Mail: registered in London EC1A 1AA, VAT address at the group tax department in Chesterfield S49 1PF) |
| Wrong company | 1 (BP) |

For BP INTERNATIONAL LTD the script picked company **#10543031, at 20-22 Wenlock Road, N1 7GU**, a formation agent address. It stopped at the first name match. Collecting every match instead showed two companies with the same normalised name. The real one, **#00542515 on Chertsey Road, TW16 7BP**, matches the address HMRC returned.

That is a real number, verified by HMRC, attached to the wrong company. It is the invisible error the brief describes, and it came from assuming a name is an identifier. It produced the three matching rules in section 5.2.

#### Which entity in a group

The same 13 test numbers showed something that is not strictly a false positive but matters as much. Numbers collected from the websites of well-known groups are frequently registered to a subsidiary, not to the parent:

| brand | registered name |
|---|---|
| Vodafone | VODAFONE GROUP SERVICES LIMITED |
| BT | BRITISH TELECOMMUNICATIONS LIMITED |
| Barclays | BARCLAYS EXECUTION SERVICES LIMITED |
| Sainsbury's | SAINSBURY'S SUPERMARKETS LTD |

Whether that is right depends on which entity sits in the customer's supplier record. Attaching the subsidiary's number to the parent would pass HMRC and still be wrong. This is where postcode matching earns its place: the registered address identifies which legal entity holds the number.


### 5.5 What these numbers do not capture

**Recall.** No figure in this report says what share of existing VAT numbers was found. "Not found" cannot be separated from "not registered", and there is no reference dataset to check against. Precision is measured; recall is not, and I have not estimated it.

**What exists, as opposed to what the method finds.** Source A's 2.7% is bounded by domain guessing, which works 27% of the time. Section 4.3 shows the method missing 4 of 6 numbers that were there to find. The real publication rate is higher, by an amount I did not measure.

**Sample size.** 75 per band is enough to see the shape and not enough to pin the rates. Every band interval spans several percentage points.

**The Source B figure was found by hand.** The 6 of 16 came from manual searching, not from the script, and 16 is a small base.

**Source C attribution rests on 48 of 128 numbers.** The rate limit cut off the names for the other 80. If those 80 differ systematically from the 48, the 75% does not hold for them.

**Attribution was judged by me.** For the 27 cases the heuristic rejected, the decision on whether a site and a registered name belong to the same business was mine, made by reading the sites.

**The density extrapolation is an upper bound.** 131 numbers x 20,000 files ignores repeats across files, which a full run would collapse.

**One snapshot.** Companies House from 1 September 2026, customs data for January to June 2026, one crawl. Companies register and deregister continuously, and none of these figures describes a moving target.

**Excluded companies are assumed to yield nothing.** Dormant, very young and residents' management companies were not sampled, so their rate is not measured, only assumed.

## 6. Part 3 - With real resources

The main result of Parts 1 and 2 is that money is not the binding constraint. Crawling is cheap, and Veridion already processes Common Crawl at scale. What limits the dataset is who publishes a VAT number at all, whether the number can be attributed to the right company, and whether it can be verified at volume. This part is organised around those three, with costs attached.

### 6.1 The shape of the solution

Source A lost most of its yield at domain discovery: guessing a domain from the legal name worked 27% of the time. Source C removed that step by harvesting numbers first and letting HMRC supply the identity, but paid for it with 25% wrong attributions.

With resources, I would combine the two ideas around a join key the web already provides. UK trading disclosure rules require a company to show its registered number on its website. So a page that carries both a company number and a VAT number links them directly:

```
crawl page
    |
    +-- company number found  -> exact join to Companies House (no name matching)
    +-- VAT number found      -> HMRC returns registered name and address
    |
    v
consistency check: does the HMRC name belong to the Companies House company?
    yes -> accept
    no  -> reject, and flag the VAT number (likely an agency or a parent)
```


This replaces fuzzy name matching with an exact join plus one check. It also turns the agency false positive into something detected automatically: an agency's VAT number printed next to a client's company number produces an HMRC
name that does not match the Companies House record for that number.

**The first thing I would measure** is how often a company number and a VAT number appear on the same page. My data suggests company numbers are published far more often than VAT numbers (several sites in the sample showed only the company number), but I did not measure the co-occurrence rate, and the design depends on it.

### 6.2 Where coverage comes from, and where it stops

Coverage is a product of stages, and each loses something:

| stage | what I measured | where the loss comes from |
|---|---|---|
| Company has a website | 27% found by guessing; 14 of 16 importers had one | Domain discovery, fixable with search |
| Website publishes a VAT number | 8 of 81 sites found (9.9%); higher for importers | Company's choice; not fixable |
| Page containing it gets crawled | Not measured | Crawl depth; terms and contact pages are often missed |
| Number is registered | 97.7% | Checksum does most of the work |
| Attributed to the right company | 75%, target over 90% with the join key | Agencies, groups, parents |
| Matches a Companies House record | Not measured | Sole traders and VAT groups never will |

Money improves rows 1, 3 and 5. **It does nothing for row 2.** A small company that publishes its VAT number nowhere cannot be found on the open web by any amount of crawling. That is the ceiling, and it falls hardest on exactly the small suppliers the customer is missing.

### 6.3 Cost per company

All figures are estimates with the assumption stated, so they can be argued with.

#### Building the dataset from Common Crawl

| item | assumption | cost |
|---|---|---|
| One full crawl | 100,000 WET files, about 6.4 TB compressed, about 2.1 billion pages | |
| Compute | Measured: 5 files in 17 seconds on one core, CPU-bound, from local disk. Scaled: 17s x 20,000 = about 94 core-hours. A substring prefilter skips most pages before the regex runs. | A few dollars, at an assumed $0.01 to $0.02 per core-hour on spot instances |
| Reading the data | 6.4 TB per crawl. My timing excludes it, since the files were already on disk. | The real cost driver, not compute. Run in the same AWS region as the crawl to avoid transfer charges. |
| Numbers harvested | 131 per 5 files, so up to about 2.6M per crawl before deduplication | |
| Compute per number | About $2 spread over 2.6M numbers | Negligible |
| Human review of uncertain attributions | 1 minute per case at about $20/hour; 25% of numbers today, falling with the join key | About $0.08 per number today |
| Verification | Marginal cost near zero under an agreement | Not a budget line: a permission |

**Per delivered VAT number: under $0.10, almost all of it human review.** Processing an entire crawl costs about as much as six minutes of human review.

#### Enriching one customer's supplier list

The customer's 26,000 suppliers without a VAT number:

| step | assumption | cost per company attempted |
|---|---|---|
| Match supplier names to Companies House | Veridion's existing entity resolution | |
| Check customs presence | Free, OGL | $0 |
| Find the website | Search API, about 2 queries at roughly $0.005 each (check current vendor pricing) | $0.01 |
| Fetch disclosure pages | 5 to 10 pages | Under $0.001 |
| Verify and review | As above, only for numbers found | |

| segment | hit rate | cost per number found |
|---|---|---|
| All suppliers | 2.7% measured with guessed domains; higher with real ones | About $0.50 |
| Importers only | 37.5% | About $0.10 |

Even at the low hit rate, recovering a number costs cents. **The cost that matters is not money but coverage**: at 1.3% to 2.7%, the customer gets a few hundred numbers out of 26,000, whatever the budget.

#### The one thing money directly buys

Two commercial providers already hold this data and forbid redistribution. A redistribution licence, negotiated with them or with the unnamed primary source behind them, is the only route where budget converts directly into coverage. I would price that before building anything, because it may be cheaper than the ceiling above suggests the build is worth.

### 6.4 What breaks first

**1. Verification, on day one.** The public checker blocked me after about 130 checks. At that budget, verifying 2.6 million harvested numbers would take over 50 years. This is policy at the CDN, not capacity (the application answers in 12ms), so more machines do not help, and rotating addresses to get around it would be deliberate circumvention. The only route is a data agreement with HMRC, which runs into the API's stated purpose of trader due diligence. **Nothing else in this plan matters until this is settled.**

**2. Attribution at scale.** 25% wrong today. At 2.6 million numbers that is 650,000 wrong numbers, each one invisible to the customer. The join key in 6.1 is the main fix; the agency detector (a number on many unrelated domains) becomes reliable only at this volume.

**3. The coverage ceiling.** Once crawling is solved, yield plateaus at whatever share of companies publish. Adding sources does not lift it much, because sources overlap: they reach the same well-documented companies.

**4. Freshness.** A number verified today can be deregistered next month. Without re-verification the dataset decays silently, and re-verification runs into constraint 1.

### 6.5 What I would monitor in production

| metric | baseline from this study | what a change means |
|---|---|---|
| Yield per crawl (numbers per 1,000 pages) | about 1.3 | A drop means crawl composition changed or extraction broke |
| Regex precision (share registered at HMRC) | 97.7% | A drop means the pattern is catching something new |
| Attribution precision, audited sample, with interval | 75% | The core quality number; tracked per source |
| Numbers on many unrelated domains | 2 in 131 | The agency detector; should grow with volume |
| Share of VALID numbers that re-verify as UNKNOWN | Not measured | Deregistration rate; sets the re-verification schedule |
| Verifier errors and 429s | 429 after about 130 checks | Early warning that access is being withdrawn |
| Coverage by size band vs the customer's supplier mix | 8% large, 1.3% small | Whether the dataset serves the suppliers that matter |
| Agreement with the customer's known third | Not measured | The only ground truth available; see section 7 |


## 7. Debate topics

### 7.1 Pointing the checksum at HMRC's checker

UK VAT numbers are 7 digits plus 2 check digits computed from them. Counting every 9-digit number that passes either of the two mod-97 rules:

```
20,615,843 checksum-valid numbers = 2.06% of the 1,000,000,000 possible
```


So the observation is real: it cuts the space fiftyfold. About 2.28 million of those are allocated, so roughly 11% would be hits.

| pace | time to enumerate |
|---|---|
| My measured rate, 2s per miss and 4s per hit | 530 days, non-stop |
| Raw network latency, about 0.2s per request | 53 days |
| The budget I actually got before being blocked, about 130 per day | 434 years |

The last row settles feasibility. It could only be done by evading the rate limit, which is deliberate circumvention.

But it would be a bad idea even if it were fast:

- **It is enumeration, not verification.** The checker exists so a trader can check a supplier. Twenty million automated requests extract the register through its query interface.
- **The output is the dataset HMRC chose not to publish.** Obtaining it one request at a time does not change what it is.
- **It degrades a public service** that stays free and open because nobody uses it this way.
- **It endangers the legitimate route.** The only lasting fix for verification is an agreement with HMRC, and this is the fastest way to foreclose one.

### 7.2 Keeping the dataset current

Registrations and deregistrations are continuous, so every record needs a date and a way to go stale.

- **Store `last_verified` on every number** and deliver it to the customer, so freshness is visible rather than assumed.
- **Re-harvest each new crawl.** New numbers appear, and a number disappearing from a company's own site is a signal worth acting on.
- **Watch Companies House monthly.** A company moving to dissolved, liquidation or dormant is a cheap trigger to re-verify or retire its number.
- **Re-verify by risk, not uniformly.** Verification is the scarce resource, so spend it where churn is likely: young companies, small companies, and any record whose Companies House status changed. Re-verify a random sample of everything else to measure the deregistration rate.
- **Re-verify every record before delivery to a customer.** The one moment freshness is guaranteed is the moment it matters.

### 7.3 Knowing the dataset is wrong at scale

The brief says there is no reference dataset. For this customer, there is one: **the third of suppliers they already have a VAT number for.** Their invoices carry it, and the brief says it is the one identifier on both the invoice and the tax record.

Run the pipeline on those companies as if the number were unknown, then compare. That measures precision directly, and it is the only place where **recall can be measured too**, because here "not found" can be told apart from "not registered". The caveat is bias: the known third is probably larger and better established than the rest, so rates measured on it are likely optimistic. Report them as an upper bound.

Beyond that, several signals need no reference:

- **Internal contradictions.** One number on many unrelated domains (agencies); one company with several numbers; an HMRC postcode that disagrees with the Companies House postcode.
- **Cross-source agreement.** A number found on the company's own site and in the crawl and derived from a published EORI is more trustworthy than one found once.
- **A standing audit.** A random sample reviewed by hand each cycle, with a confidence interval, tracked over time. Section 5 is the first round of it.
- **The customer's own feedback.** Every new invoice that arrives with a VAT number is a free check against the record.

### 7.4 Sources I would not use in a product we sell

| source | would I build on it | why |
|---|---|---|
| HMRC public web checker | No | Terms say "personal use and viewing"; `noindex, nofollow`; no contract, no guarantee, blocked me after about 130 checks |
| HMRC API v2 | Only within its purpose | Offered for trader due diligence; bulk validation of harvested numbers is outside it |
| Creditsafe | No | Terms prohibit scraping, building a competing service, derivative works and resale, and require deletion on termination |
| vat-lookup.co.uk | No | Prohibits extraction; its own licence from an unnamed primary source forbids passing the data on |
| EORI checker | Same as the VAT checker | Same service family, and returns no identity anyway |
| Companies House, HMRC customs data | Yes | Open Government Licence v3.0; neither contains VAT numbers |
| Numbers companies publish on their own sites | Yes, with care | A disclosure the company made itself, often by legal obligation; the question is attribution, not permission |

The first two are the instructive cases. Neither is prohibited outright, and both work. The problem is that "works" and "can be sold" are different questions, and a product built on a service whose terms do not cover it can be switched off without notice, with contracts already signed downstream.


## 8. Beyond the UK

### 8.1 Germany: the same problem, turned inside out

The UK is easy to verify and hard to discover. Germany is the reverse.

**Discovery is easier.** Section 5(1) no. 6 of the German Digital Services Act (DDG) requires any business website to state its VAT identification number (USt-IdNr) in the Impressum, if the business has one. It is enforced in practice: competitors send cease-and-desist letters over missing or wrong Impressum details. The same page must also carry the full company name with legal form and the commercial register number. So the join key I had to design for the UK in 6.1 is mandatory in Germany, on a page with a predictable name.

**Verification is harder.** VIES confirms whether a German number is valid, but Germany does not release the trader's name or address through it, citing federal data protection law. The inverted pipeline that made Common Crawl useful in the UK depends on the verifier returning an identity. In Germany it does not.

**Would the pipeline survive?** Partly. Harvesting, checksum filtering and validity checks carry over unchanged. The identity step moves from the verifier to the page: attribution comes from the Impressum, where name, register number and VAT number sit together, instead of from what HMRC returns. Without an independent identity check, the agency false positive becomes harder to catch, so the register number on the page matters even more.

**And "not found" changes meaning.** German businesses receive a domestic tax number automatically, but the USt-IdNr used in cross-border trade has to be applied for separately. A domestic-only German company may be tax registered and still hold no VAT ID to publish. The ambiguity from the UK gets a third branch.

### 8.2 A country where the number is barely discovered: France

A French VAT number is `FR` + a 2-digit key + the company's 9-digit SIREN, and the key is computed from the SIREN:

key = (12 + 3 * (SIREN mod 97)) mod 97

SIREN numbers are published in France's open business register. So discovery is arithmetic: every VAT number can be computed for every company, with no crawling. What remains is status, since a company can hold a SIREN without being VAT registered, and France's VIES responses include the trader's name and address.

**What this implies for prioritising markets.** The UK is one of the harder places to start, not a typical one. I would rank markets on three questions:

1. Can the VAT number be derived from a public register identifier?
2. Does the verifier return an identity, or only valid and invalid?
3. Is web publication mandatory and enforced?

France answers yes to 1 and 2, which makes it close to a solved problem. Germany answers no to 1 and 2 but yes to 3. The UK answers no to 1, yes to 2 under heavy rate limits, and only partly to 3. Start with the countries where the problem is arithmetic, and budget the search-heavy ones last.

### 8.3 Which countries are genuinely hard

On the three questions above, "hard" means failing on both sides:

- **Discovery-hard**: no derivable number and no enforced publication. The UK is here.
- **Verification-hard**: the verifier returns no identity. Germany is here, and Spain appears to be as well, since its VIES responses also omit name and address.
- **Both**: a country with neither a derivable number, nor an identity from VIES, nor an enforced disclosure rule.

I have not established which countries fall in the third group. For Spain, the open question is whether a disclosure rule on websites compensates for the missing identity, the way the Impressum does in Germany. That is the next thing I would check, and it decides whether Spain is Germany's problem or a harder one.

### Sources for this section

- German Digital Services Act, Section 5 (official text): https://www.gesetze-im-internet.de/ddg/__5.html
- French VAT key formula and its legal basis: https://hayot-expertise.fr/en/blog/french-tax-identification-number-2026-nif-siren-vat
- French VAT key formula and legal basis: https://hayot-expertise.fr/en/blog/french-tax-identification-number-2026-nif-siren-vat