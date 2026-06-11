# PLAN — The Question Engine

**Tier:** Heavy (portfolio front door / capstone, maintained > 3 months)
**Status:** Phase 5 shipped — live at ask.lailarallc.com, all 13 verdicts verified in production
**Priority:** Phase 4 (Quarto one-pagers) or Phase 5 promotion tasks

---

## Current focus

Live at https://ask.lailarallc.com. 13/13 live verdicts return correct Cinderhaven data; q05/q06 return 503 (stubs awaiting source pieces). q12 runs ~40s (GROUP BY SKU over 1.4M rows) — acceptable for v1. Remaining Phase 5 tasks are non-engineering (homepage CTA, LinkedIn posts).

---

## Task list

### Phase 1 — Infrastructure ✅
- [x] Scaffold project structure
- [x] FastAPI app + verdict router
- [x] BaseQuestion abstract class + registry pattern
- [x] YAML thresholds config
- [x] DB connection (read-only)
- [x] Frontend shell (HTML/CSS/JS + D3)
- [x] Quarto one-pager template
- [x] check_canonical.py release gate skeleton
- [x] Unit tests

### Phase 2 — Question implementation ✅
- [x] Q01: Should I fire my biggest customer?
- [x] Q02: Can I afford this retailer launch?
- [x] Q03: Which SKUs should die?
- [x] Q04: Where is my trade spend going? (distressed)
- [x] Q05: EDI reconciliation — STUB
- [x] Q06: Recall blast radius — STUB
- [x] Q07: Product data preflight
- [x] Q08: Weight cost
- [x] Q09: Channel profitability
- [x] Q10: Deduction recovery
- [x] Q11: Stockout cost
- [x] Q12: Forecast accuracy
- [x] Q13: OTIF exposure
- [x] Q14: Velocity decay
- [x] Q15: Cash conversion

### Phase 3 — Canonical reconciliation ✅
- [x] Populate check_canonical.py expected values from CINDERHAVEN_CANONICAL.md
- [x] Run gate and fix any drift (7/7 pass; $1.66M scope documented)
- [x] Verify: every figure shown reconciles to its source piece

### Phase 4 — One-pagers + export
- [ ] Quarto render pipeline per question (`quarto render quarto/_template.qmd`)
- [ ] PDF download endpoint
- [ ] Consider gating bulk download

### Phase 5 — Deploy + promote
- [x] `fly deploy` → https://ask-cinderhaven.fly.dev (2026-06-11)
- [x] Smoke-test all 15 verdicts on production (13 pass, 2 stubs 503 as expected)
- [x] Custom domain: ask.lailarallc.com — live (CNAME → fly app, cert Issued 2026-06-11)
- [ ] Homepage hero CTA takeover
- [ ] /work page reorganizes around the engine
- [ ] LinkedIn content calendar (15 posts, one per question)

---

## Open questions

1. Final name: *Ask Cinderhaven* vs question-as-title
2. Homepage: full hero replacement or co-primary CTA
3. LLM natural-language question matching in v2? Lean pure select for v1.

---

## Out of scope (v1)

- Free-text question input / LLM interpretation
- User-uploaded data
- More than fifteen questions
- Any new data generation
