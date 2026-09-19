# Data sources

Raw inputs are not committed (gitignored) they are large and re-downloadable. This file records exactly which versions produced the figures in the report. Companies House publishes a new snapshot monthly and Common Crawl a new crawl roughly every two months, so re-running against a later version will not reproduce these numbers.

---

## Companies House Basic Company Data

| | |
|---|---|
| URL | http://download.companieshouse.gov.uk/en_output.html |
| File | `BasicCompanyDataAsOneFile-2026-09-01.csv` |
| Snapshot date | 2026-09-01 |
| Downloaded | 2026-09-11 |
| Licence | Open Government Licence v3.0 |
| Size | 2,801,377,533 bytes (2.6 GiB) |
| Rows | 5,689,367 records |
| sha256 | `e295a9a8336f5334b19d711c64c85685f46a5bfa207305d1556e12028aaeec61` |

Name, company number, registered address, SIC codes, incorporation date, accounts filing category. No websites, no VAT numbers.

`wc -l` reports 5,689,370 lines against 5,689,367 records: one is the header and two are newlines embedded inside quoted fields. Parsed with Python's `csv` module rather than line splitting, for this reason.

Path: `data/raw/companies-house/`

---

## HMRC UK Trade Info Importer details

| | |
|---|---|
| URL | https://www.uktradeinfo.com/trade-data/latest-bulk-data-sets/bulk-data-sets-archive/ |
| Archive | `importers_jan-jun26archive.zip` |
| Period | January–June 2026 |
| Downloaded | 2026-09-16 |
| Licence | Open Government Licence v3.0 |
| Rows | 657,580 total |

| file | lines | sha256 |
|---|---|---|
| `importers2601.txt` | 101,917 | `beccbf43510b4b47d1693dbf942d9884878b0b2585a37978860ae92a7744432e` |
| `importers2602.txt` | 109,785 | `0ecaf830ca016806b1486d7d610972e03f4840742dbb8ece6261df671cfb8738` |
| `importers2603.txt` | 112,064 | `294df6f923db717beb97a74ff76b4731e40e6359eb20f9033b82dd289c957867` |
| `importers2604.txt` | 110,734 | `6dff93cddab7e9e377eb377cba1b991a699ca8e758752184857501ea2961dc5a` |
| `importers2605.txt` | 110,237 | `5c81e21fa4204a76fa895b4ff7a9625f3a9d76ddfa4ad731d2a74ca525b067db` |
| `importers2606.txt` | 112,843 | `70027c2ea72a1970cca56df4e8b37faad98f9f732d3757f14ed814a46dd61d3e` |

Tab-separated, 59 fixed fields. Field 2 is the company name, field 8 the postcode, fields 9–58 up to 50 commodity codes. Covers businesses importing into the UK from non-EU countries. No VAT numbers.

Yields 207,983 unique (name, postcode) pairs across the six months.

Path: `data/raw/uktradeinfo/`

---

## Common Crawl CC-MAIN-2026-34

| | |
|---|---|
| Path index | https://data.commoncrawl.org/crawl-data/CC-MAIN-2026-34/wet.paths.gz |
| Crawl segment | `1786091384908.68`, captured 2026-08-07 |
| Files used | first 5 of the 100,000 listed WET files |
| Downloaded | 2026-09-18 |
| Pages processed | 104,282 (2.1% on `.uk` domains) |

| file | size | sha256 |
|---|---|---|
| `…-00000.warc.wet.gz` | 63,890,507 | `a7637296d56b737e116998fdff0cb2217e56c2541ffaa95d17960a44efda7af6` |
| `…-00001.warc.wet.gz` | 63,025,891 | `2f5f7b065343d676c345ac54df1cbac574514ca5816ae4f3a461ac723ffeaf66` |
| `…-00002.warc.wet.gz` | 66,153,967 | `9c9eeeeba34465ec05d7ce3a334b21ebce72987ccbabe59d71aa11621c8c45fe` |
| `…-00003.warc.wet.gz` | 65,776,522 | `b96edd5a0971d7e7ecd007469af7013393e1d05fc4afec0b46aff68fbb2c0181` |
| `…-00004.warc.wet.gz` | 63,030,139 | `890db65244f76b793d932b9c6936f3125e2fb9f6832bc6a8c41524ff79af9950` |

Full filenames share the prefix `CC-MAIN-20260807101845-20260807131845-`.

WET files hold plain text extracted from crawled pages, without markup.

Path: `data/raw/commoncrawl/`

---

## HMRC sandbox test VRNs

| | |
|---|---|
| Source | HMRC Developer Hub, Check a UK VAT Number API v2.0 |
| File | `fixtures/hmrc/vrn.csv` |

Fictitious VRNs, valid only in the sandbox environment. Committed because they are small and make the client's tests reproducible.

Confirmed fictitious rather than assumed, VRN 553557881 from this file returns `/unknown` on the live service.