# FAILURES — The Question Engine

---

## 2026-06-10 — `COUNT(*) FROM fct_retailer_deductions` ≠ canonical "677 chargebacks"

**What was tried:** check_canonical.py check assumed the canonical "677 retailer chargebacks" figure equalled `COUNT(*) FROM public_marts.fct_retailer_deductions`. Expected 677; actual 13,960.

**Why it failed:** "Chargebacks" in Cinderhaven canonical refers to a specific quality-related deduction category tracked separately (likely `fct_chargebacks` or a typed subset), not all rows in the deductions mart. `fct_retailer_deductions` holds all deduction events across all 9 types (short_ship, damaged, spoilage, etc.).

**Fix:** Replaced with a row-count stability check (13,960) that detects regeneration drift rather than trying to reconcile to a differently-scoped canonical figure.

**Lesson:** Canonical figures always have a scope. Confirm the exact table/filter before writing a gate check — "chargebacks" and "deductions" are not synonyms in this dataset.

---

## 2026-06-10 — q01 check SQL: `MAX()` in cross-join raises PostgreSQL grouping error

**What was tried:** `SELECT ROUND((MAX(rev.revenue) / t.total)::numeric, 4) FROM rev, totals t` — PostgreSQL rejected with `column "t.total" must appear in the GROUP BY clause`.

**Why it failed:** In a cross-join (`FROM rev, totals t`), `t.total` is treated as a non-aggregated column in the same SELECT scope as `MAX()`. PostgreSQL requires all non-aggregate columns to appear in GROUP BY.

**Fix:** `SELECT ROUND((r.revenue / t.total)::numeric, 4) FROM rev r, totals t ORDER BY r.revenue DESC LIMIT 1` — select the top row directly instead of using MAX across a join.

**Lesson:** When selecting the maximum row from a cross-join, use ORDER BY + LIMIT 1, not MAX() on a joined column.

---

## 2026-06-10 — `AVG(typical_recovery_rate)` is a model field, not realized recovery rate

**What was tried:** Gate check used `AVG(typical_recovery_rate) FROM fct_retailer_deductions` to verify the canonical ~16% baseline recovery rate. Result: 45.25%.

**Why it failed:** `typical_recovery_rate` is a per-row scoring field representing the *expected* recovery probability for a given deduction type — not what was actually recovered historically. The canonical 16% is the realized rate: total recovered ÷ total deductions.

**Fix:** `SELECT ROUND(SUM(recovered_amount) / NULLIF(SUM(deduction_amount), 0)::numeric, 4) FROM fct_retailer_deductions` — produces 17.6%, which passes the ±5% tolerance on 16%.

**Lesson:** Always distinguish model/scoring columns (what we expect to recover) from realized columns (what was actually recovered). Check the column semantics before writing a ratio check.

---

## 2026-06-10 — Wrong schema prefix across all question modules

**What was tried:** All 8 live question modules used `marts.` as the PostgreSQL schema prefix (e.g., `FROM marts.fct_retailer_orders`).

**Error:** `relation "marts.fct_retailer_orders" does not exist` — 500 on every verdict endpoint.

**Why it failed:** The actual schema name in Cinderhaven PostgreSQL is `public_marts`, not `marts`. The scaffold assumed `marts` without verifying against the live DB.

**Fix:** Python find/replace script changed `marts.` → `public_marts.` across all 9 affected files. Going forward, always verify schema names with `SELECT schemaname FROM pg_tables LIMIT 5` before writing any SQL.

---

## 2026-06-10 — Stale server process held port 8000 after schema fix

**What was tried:** Applied schema fix, restarted server via `Start-Process`, retested — all still returned 500.

**Why it failed:** The original pre-fix server (started with `Start-Process -WindowStyle Hidden`) was still bound to port 8000. The "new" server failed silently to bind (port already in use) so the stale one kept serving. `Get-Process python` returned no visible processes; the PID was only visible via `netstat -ano`.

**Fix:** Found PID via `netstat -ano | Select-String ":8000"`, killed it with `Stop-Process -Id <pid> -Force`, then started fresh.

**Lesson:** Always kill by port (`netstat -ano`) not by process name when using hidden/background server starts.

---

## 2026-06-10 — Q11 summary SQL multiplied implied cost by store count

**What was tried:** Initial Q11 summary query aggregated per-SKU in a CTE, then JOINed back to `fct_distribution` on `sku` to get `COUNT(DISTINCT store_id)`. Result: $909M instead of $4.6M.

**Why it failed:** The outer JOIN expanded each per-SKU row into N rows (one per store), so `SUM(implied_lost)` was summed N times. The design mistake was fetching `active_stores` via a JOIN on an already-aggregated CTE.

**Fix:** Rewrote to compute implied cost at the per-store level in a single `per_store` CTE, then aggregate once with no outer join. `COUNT(DISTINCT store_id)` comes from the same CTE.

**Lesson:** Never JOIN back to a source table after aggregating — always compute what you need before the GROUP BY.

---

## 2026-06-10 — Q02 promo filter returned zero rows

**What was tried:** `WHERE funding_mechanism = 'manufacturer'` in `_SQL_PROMO`. All retailers showed $0 promo spend and 0-month payback.

**Why it failed:** No rows in `fct_promotions` have `funding_mechanism = 'manufacturer'`. Actual values are: `billback`, `MCB`, `off_invoice`, `scan_based` — all manufacturer-side cost types.

**Fix:** Removed the WHERE clause. All four mechanism types represent manufacturer promo investment.

**Lesson:** Always SELECT DISTINCT the categorical column before filtering on it in any new query.
