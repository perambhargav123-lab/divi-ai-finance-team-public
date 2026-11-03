# Divi evaluation

All numbers below come from the fictional Falcon Trading LLC books for October 2026, as of commit time. Rerun commands are given for each result.

## 1. Fraud and error benchmark

The benchmark copies the books, then plants 20 anomalies and 4 harmless decoys (`divi/benchmark.py`, seed 20). It runs the same detectors used in the close and scores the result.

| Metric | Result |
|---|---|
| Anomalies planted | 20 |
| Caught (recall) | 20 / 20 = 100% |
| Precision | 100% (0 false positives) |
| Decoys flagged | 0 of 4 |

What was planted:

- Duplicate vendor invoice (3)
- Duplicate bank payment (3)
- Weekend journal posted by a junior (3)
- Wrong VAT rate of 4% (2)
- Vendor bank details changed (2)
- Large payment to a new vendor (2)
- Price above contract (2)
- Total that does not add up (1)
- **Hard:** near-duplicate invoice with the amount changed by AED 1 (1)
- **Hard:** a payment split into 2 x 9,800 to stay under the threshold (1)

**Change log.** The benchmark first scored 19 of 20: the AED 1 near-duplicate was missed. The Red Team now has a `near_duplicate_vendor_invoice` rule: same supplier, within 7 days, amounts AED 0.01 to 5 apart. It catches the case and raises no new false positives on the real books.

Rerun: `python -c "from divi import benchmark; r=benchmark.run(); print(r['detected'], r['injected'], r['precision'])"`

Limits: the anomalies are synthetic and the seed is fixed. A real ledger will contain patterns the rules do not cover. The 100% figure measures these 20 cases only.

## 2. Claim verifier

Every AI claim that cites a number is checked twice. First, code traces the number to its source row. Then a second Muse call judges whether the evidence supports the claim.

| Metric | Result |
|---|---|
| Claims checked this close | 20 |
| Verified | 18 |
| Rejected and kept out of reports | 2 (a conditional Zenith escalation, and an AED 18,000 vs 18,000.12 prepayment) |
| Planted false claims caught | 6 / 6 |

Rerun: `python -m divi.insights` (it prints the verifier line).

## 3. Capture (vision)

| Test | Result |
|---|---|
| Clean receipts in the live run (EN, AR, bilingual) | 4 docs, 8/8 fields each |
| Crumpled and rotated Arabic receipts (doc_06, doc_11) | 16 / 16 fields |
| Grounding boxes on doc_02 | 6 of 6 fields boxed; boxes are approximate and sit slightly left of the printed value |

Rerun: `python -m divi.maxai`. The first run makes about 7 Muse calls (about AED 0.22); later runs replay from cache.

## 4. Long-context Controller review

The Controller reads the whole month in one Muse call: invoices, bank, journals, vendors, AP and AR aging, about 13,400 input tokens. It returned 6 findings, and each cited row was looked up in the source files: 6 of 6 findings are grounded.

## 5. Native tool calling

Three CFO questions were sent with three tools through the Responses API `tools` parameter. Muse picked the right tool and argument each time: `get_lowest_cash(downside)`, `get_invoice(PI-0012)` and `get_vat_payable()`.

## 6. Cash forecast

| Metric | Result |
|---|---|
| Chance cash goes below zero in any of the 13 weeks | 52.3% |
| Same chance with the six drafted actions | 3.4% |
| Chance below zero in week 6 | 10.7% |

The forecast simulates 2,000 paths, each drawn from customer payment history and from what customers said in their emails.

## 7. Learning loop

Automation rate: 90.9% (month 1), then 98.5% (month 2), then 99.4% (projected).

## 8. Reliability

- Each model call is retried once. After that, Divi falls back to a rule-based answer flagged for review (`tests/test_max.py::test_fallback_when_model_fails`).
- All tests run offline with `DIVI_MOCK=1`. The CI workflow is prepared in `deploy/ci-tests.yml`.

## 9. Cost

| Item | Result |
|---|---|
| Close run | 8 Muse calls, 48,786 tokens, AED 0.63 |
| Depth layer (vision lab, long context, tool calls) | AED 0.22 once |

Pricing: muse-spark-1.3, USD 1.25 per 1M input tokens and USD 4.25 per 1M output tokens, at USD 1 = AED 3.6725.

## Edge layer (added 27 Oct 2026)

| Check | Result | How it is verified |
|---|---|---|
| Owner control compiled by Muse | "flag any payment over AED 20k to a vendor added this month" became a 2-condition JSON rule; 1 hit (B108, AED 50,000) | rule is data, validated against a fixed field list; `tests/test_edge.py` |
| Beat the Controller | fake new vendor + AED 45,000 payment caught by 3 rules; a AED 9,400 payment to an unknown payee slips past (honest gap, becomes a test case) | `test_challenge_catches_fake_vendor_and_scores_a_miss` |
| 103-page facility agreement, one Muse call (58k tokens) | Minimum Liquidity clause 22.3 found on page 57, quote verified on that page; base forecast breaches AED 250,000 in weeks 3 and 4 (headroom AED -15,709); levers cure it | quote string searched on the cited page |
| Debate scorecard | 4 rounds, every winning citation resolves to a source row | `sources.resolve` |
| SAM 3.1 phone-photo cut-out | receipt found on a synthetic desk photo, cropped, 8/8 fields read | ground truth in `data/docs/ground_truth.json` |
| UAE tax rules via Muse web search | VAT 5%, CT 9% above AED 375,000, VAT return 28 days: all agree with Divi's rates, 3 official sources | `out/cache/tax_web.json` |
| Xero / Zoho exports | 355 journals, each balances to zero | `test_extras_endpoint_and_exports_balance` |

### JE-1040 (AED 1.19m cost of sales)
Deliberate, explainable demo finding, not a data error. The generator books October cost of sales as a 72% cost-ratio estimate (1,190,000 / 1,654,342.56 sales = 71.9%), which is how many SMEs close before a stock count. The books stay as they are. Divi's roll-forward (opening stock 385,000 + purchases 1,154,209.47 - counted stock 270,750 = 1,268,459.47) shows the estimate is AED 78,459.47 too low, and proposes a true-up (Dr 5000 / Cr 1200) that waits for approval and is never auto-posted.
