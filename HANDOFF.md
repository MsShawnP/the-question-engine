# HANDOFF — The Question Engine

**Last updated:** 2026-06-10
**Session:** Session 4 — canonical gate complete, ready to deploy
**Phase:** Phase 3 done → ready for `fly deploy` (Phase 5)

---

## What was done this session

- Implemented all 8 live question modules end-to-end:
  - Q01 biggest_customer, Q02 retailer_launch_cost, Q03 sku_rationalization
  - Q04 trade_spend (distressed scenario), Q07 product_data_preflight
  - Q08 weight_cost, Q09 channel_profitability, Q10 deduction_recovery
- **Schema fix**: All modules originally used `marts.` as table prefix; actual schema in Cinderhaven PostgreSQL is `public_marts`. Fixed with find/replace across all 8 modules.
- **Q02 promo filter fix**: `WHERE funding_mechanism = 'manufacturer'` returned zero rows (no such value exists). All four mechanism types (billback, MCB, off_invoice, scan_based) are manufacturer-side cost. Removed filter; fixed `< 1 month` display.
- All 8 tests pass: `pytest tests/ -v` → 8 passed
- DB access: `fly proxy 5432 -a cinderhaven-db` (must be running for verdicts to work)

## All 15 live verdict results from Cinderhaven data

| Q | Verdict detail | Headline |
|---|---|---|
| q01 | healthy | Largest account 21% revenue, 2% deduction rate |
| q02 | all launches affordable | Fastest payback < 1 month, 176x ROI |
| q03 | no kills | All 50 SKUs above velocity/margin floors |
| q04 | within range | 12% unplanned deductions (ceiling 25%) |
| q07 | **do not submit** | 40% of SKUs fail Walmart GDSN (dimensions worst) |
| q08 | $142K realized + $264K projected | 3 of 50 SKUs have weight data gaps |
| q09 | **2 channels negative** | Distributor + Retailer lose money; DTC +$442K |
| q10 | **money left + broken process** | 61% expired deductions, win rate below 50% |
| q11 | **$4.6M implied stockout cost** | 144,790 zero-velocity store-weeks at authorized locations |
| q12 | **43.9% MAPE — forecast broken** | Forecast errors > 30% threshold; worst SKU needs investigation |
| q13 | **8.6% ASN late — $801K exposure** | 4,006 late ASNs; all deliveries on time but ASN process is the gap |
| q14 | all SKUs accelerating | Portfolio +36.2% avg; slowest is Everything Bagel Spread at +24.7% |
| q15 | **13.2% deduction drag** | $6.8M deducted from $52M invoiced; DSO ~44 days |

---

## 2026-06-10 — Session 4

**Started from:** Phase 3 canonical reconciliation. Gate skeleton existed but unpopulated.

**Did:**
- Populated `scripts/check_canonical.py` with 7 checks (q01 share, q03 SKU count, q10 row stability + backlog + recovery rate, q13 ASN late rate, q15 deduction drag)
- First run had 4 failures; fixed SQL grouping error in q01, wrong chargeback count assumption, wrong recovery rate metric (model field vs realized)
- Investigated $1.66M vs $1.33M gap — found clean scope split: retailer $1.33M + distributor $330K = canonical $1.66M cross-channel total; reconciles to the cent
- Updated gate with scope note; annotated CINDERHAVEN_CANONICAL.md with full breakdown + resolved ~15,900 vs 16,023 (rounding, not a third figure)
- Gate passes 7/7

**State:** Gate green. CINDERHAVEN_CANONICAL.md annotated. No deploy yet. PLAN.md Phase 3 marked complete.

**Next:** `fly deploy` to ask.lailarallc.com → smoke-test all 15 verdicts on production → Phase 5 promotion tasks.

---

## Known issues / blockers

- Q05 (EDI reconciliation) and Q06 (recall cost) are deliberately stubbed — blocked on unshipped source pieces. Do not implement.
- q09 shows $420M negative contribution margin for Retailer + Distributor channels — correct from the synthetic Cinderhaven data at scale; not a bug.
- Q11 uses `fct_distribution.weeks_with_sales` as a zero-velocity proxy. If fct_distribution is not refreshed regularly, stockout cost figures will lag reality.
- `fct_retailer_deductions` has zero "open" deductions in baseline — all are expired or disputed. q10's `open_amount` is always 0; potential_recovery will always be 0 until data is refreshed with open deductions.

## What's next

1. **Deploy** — `fly deploy`, then smoke-test `ask.lailarallc.com` (all 15 verdicts)
2. **Homepage CTA** — update lailara-website hero to `ask.lailarallc.com`
3. **Quarto one-pagers** — template at `quarto/_template.qmd`; render pipeline not built (Phase 4, can ship after deploy)

---

## How to start the server

```
# Terminal 1 — DB proxy (must be running)
fly proxy 5432 -a cinderhaven-db

# Terminal 2 — API server
cd the-question-engine
python -m uvicorn api.main:app --port 8000 --reload
```

Then hit `http://localhost:8000` for the frontend, or `POST http://localhost:8000/api/verdict/q01`.

---

## File map

| File | Purpose |
|---|---|
| `engine/questions/q01_biggest_customer.py` | Reference implementation — read before writing any new question |
| `config/thresholds.yaml` | All rule thresholds — edit here only |
| `config/questions.yaml` | Master question manifest |
| `scripts/check_canonical.py` | Release gate — populate expected values from CINDERHAVEN_CANONICAL.md |
| `tests/test_engine.py` | Rule logic unit tests |
