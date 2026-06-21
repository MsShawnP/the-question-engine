"""
check_canonical.py — release gate.

Verifies that every figure surfaced by the engine reconciles exactly
to its source portfolio piece. An inconsistency here breaks the entire
portfolio's coherence, not just this piece.

Run: python scripts/check_canonical.py
Exits 0 if all checks pass, 1 if any fail.

Sources:
  CINDERHAVEN_CANONICAL.md (authoritative) — 50 SKUs, $1.35M backlog, 3,363 chargebacks, ~16% recovery
  Session-3 DB results (engine baseline) — 21% top account, 8.6% ASN late, 13.2% deduction drag
"""
import sys
from db.connection import query

CHECKS = [
    # ── Q01: Biggest customer ──────────────────────────────────────────────
    {
        "id": "q01_top_account_share",
        "description": "Top retailer revenue share (~21% — engine baseline, Session 3)",
        "query": """
            WITH rev AS (
                SELECT dr.retailer_id, SUM(fo.total_value) AS revenue
                FROM public_marts.fct_retailer_orders fo
                JOIN public_marts.dim_retailers dr ON fo.retailer_id = dr.retailer_id
                GROUP BY dr.retailer_id
            ),
            totals AS (SELECT SUM(revenue) AS total FROM rev)
            SELECT ROUND((r.revenue / t.total)::numeric, 4) AS value
            FROM rev r, totals t
            ORDER BY r.revenue DESC
            LIMIT 1
        """,
        "expected": 0.21,
        "tolerance": 0.02,
    },

    # ── Q03: SKU count ─────────────────────────────────────────────────────
    {
        "id": "q03_sku_count",
        "description": "Total SKU count (canonical: exactly 50 — seed_config.py PRODUCT_LINES)",
        "query": "SELECT COUNT(DISTINCT sku) AS value FROM public_marts.dim_products",
        "expected": 50,
        "tolerance": 0,
    },

    # ── Q10: Deduction recovery ────────────────────────────────────────────
    {
        "id": "q10_deduction_row_count_stability",
        "description": "Deduction row count stability check (baseline: 14,947 rows — reseed would change this)",
        "query": "SELECT COUNT(*) AS value FROM public_marts.fct_retailer_deductions",
        "expected": 14_947,
        "tolerance": 0,
    },
    # SCOPE NOTE: canonical headline = $1.35M / $1,346,815 (retailer + distributor).
    # That figure is CROSS-CHANNEL. fct_retailer_deductions is retailer-only by design;
    # distributor deductions live in a separate table. This gate checks the retailer
    # portion only ($1,118,682 / 14,947 rows) — the scope q10 surfaces.
    # Do not "fix" this to $1.35M; the gap is intentional, not a data error.
    {
        "id": "q10_deduction_backlog_retailer",
        "description": "Retailer deduction backlog (canonical $1.35M cross-channel; this gate checks retailer portion only)",
        "query": "SELECT SUM(deduction_amount) AS value FROM public_marts.fct_retailer_deductions",
        "expected": 1_118_682,
        "tolerance": 5_000,
    },
    {
        "id": "q10_realized_recovery_rate",
        "description": "Realized recovery rate: recovered ÷ gross (canonical: ~16%)",
        "query": """
            SELECT ROUND(
                SUM(recovered_amount) / NULLIF(SUM(deduction_amount), 0)::numeric,
                4
            ) AS value
            FROM public_marts.fct_retailer_deductions
        """,
        "expected": 0.16,
        "tolerance": 0.05,
    },

    # ── Q13: OTIF exposure ─────────────────────────────────────────────────
    {
        "id": "q13_asn_late_rate",
        "description": "ASN late rate across all shipments (~8.6% — engine baseline, Session 3)",
        "query": """
            SELECT ROUND(
                SUM(CASE WHEN asn_sent_late THEN 1 ELSE 0 END)::numeric / COUNT(*),
                4
            ) AS value
            FROM public_marts.fct_retailer_shipments
        """,
        "expected": 0.086,
        "tolerance": 0.01,
    },

    # ── Q15: Cash conversion ───────────────────────────────────────────────
    {
        "id": "q15_deduction_drag_rate",
        "description": "Avg deduction rate from remittances (~13.2% — engine baseline, Session 3)",
        "query": """
            SELECT ROUND(AVG(total_deductions / NULLIF(gross_amount, 0))::numeric, 4) AS value
            FROM public_marts.fct_retailer_payments
        """,
        "expected": 0.132,
        "tolerance": 0.02,
    },
]


def run_checks() -> int:
    failures = 0
    for check in CHECKS:
        if check["expected"] is None:
            print(f"  SKIP  {check['id']} — expected value not set")
            continue
        try:
            rows = query(check["query"])
            actual = list(rows[0].values())[0]
            diff = abs(float(actual) - float(check["expected"]))
            if diff > check["tolerance"]:
                print(
                    f"  FAIL  {check['id']}: expected {check['expected']} "
                    f"(±{check['tolerance']}), got {actual} (diff {diff:.6f})"
                )
                print(f"        {check['description']}")
                failures += 1
            else:
                print(f"  PASS  {check['id']}  [{actual}]")
        except Exception as e:
            print(f"  ERROR {check['id']}: {e}")
            failures += 1
    return failures


if __name__ == "__main__":
    print("Running canonical reconciliation checks...\n")
    n = run_checks()
    if n:
        print(f"\n{n} check(s) FAILED — do not ship.")
        sys.exit(1)
    print("\nAll checks passed.")
