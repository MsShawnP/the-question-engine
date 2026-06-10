# PLAN — The Question Engine

**Tier:** Heavy (portfolio front door / capstone, maintained > 3 months)
**Status:** Phase 3 complete — gate passes 7/7, ready to deploy
**Priority:** Next #1 — ship to ask.lailarallc.com

---

## Current focus

Gate passes 7/7. CINDERHAVEN_CANONICAL.md annotated with scope notes. Next: `fly deploy` to ask.lailarallc.com.

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
- [ ] `fly deploy` to ask.lailarallc.com
- [ ] Smoke-test all 15 verdicts on production
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
