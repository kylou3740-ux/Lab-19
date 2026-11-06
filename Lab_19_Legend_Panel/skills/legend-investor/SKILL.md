---
name: legend-investor-panel
description: Analyze the same five years of SEC EDGAR 10-K facts from Buffett, Cathie Wood, and Michael Burry perspectives; calculate each investor's specified checks in Python and write three separate evidence-grounded memos.
---

# Lab 19 — Legend Panel

## Data rules
- Use SEC EDGAR companyfacts only; do not invent, estimate, or hardcode financial values.
- Use five annual 10-K periods; flow facts must span 330–380 days; latest filing wins for repeated fiscal periods.
- Missing facts print `not found`; dependent checks become `not known`.
- Monetary facts are USD millions. The printed report is the exclusive source for numeric values in memos.

## Investor checks
### Buffett
- ROE = net income / year-end stockholders' equity × 100; at least 15% every year.
- Owner earnings = operating cash flow − capital spending; positive every year.
- Owner earnings in the last year exceed the first year.
### Cathie Wood
- Revenue CAGR = (last revenue / first revenue)^(1/4) − 1; at least 15%.
- Latest-year R&D at least 5% of latest-year revenue.
### Michael Burry
- Operating cash flow at least net income every year.
- Latest-year liabilities no more than twice stockholders' equity.

## Memos
Create `<TICKER>_buffett_memo.md`, `<TICKER>_cathie_wood_memo.md`, and `<TICKER>_burry_memo.md` in `outputs/`. Each must have exactly one `Verdict: OWN`, `Verdict: WATCH`, or `Verdict: PASS`; explain every check from the printed status and figures; distinguish a mechanical screen from qualitative judgment; discuss limitations and missing data; end with next research needed. Do not add any number not in the printed report.

## Costco known-answer validation
Expected: Buffett 3/3; Cathie Wood growth fails at 7.51% and R&D is not known because the fact is not found; Burry 2/2 with liabilities/equity 1.49. Liability/equity ratios by fiscal year: 2.11, 1.75, 1.96, 1.64, 1.49 (2022–2026). These are comparison targets, not pipeline inputs. If the run differs, debug tags, dates, and filing selection.

## Threshold probe
After baseline COST matches, lower Cathie Wood's revenue-growth threshold from 15% to 5%, rerun COST, and confirm growth passes while R&D remains not known. Choose the threshold to retain and explain why in one sentence under Cathie's memo. This changes a screen rule, not Costco's facts.

## Example Project 2 company
VT is the example fund. Vanguard's 2026-09-30 holdings disclosure identifies NVIDIA (NVDA) as its largest holding. Run NVDA. If the student later provides their own fund selection, use that fund's largest eligible company instead.
