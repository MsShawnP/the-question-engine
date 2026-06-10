# The Question Engine

Fifteen questions every specialty food brand CEO asks, answered with rules-based verdicts on the Cinderhaven canonical dataset.

**Live:** https://ask.lailarallc.com

---

## What it does

The CEO picks a question. The engine runs documented rules against the Cinderhaven mart layer and returns: a verdict (one sentence, opinionated), the one chart that justifies it, the three numbers behind it, and a link into the deep-dive portfolio piece. Fifteen questions, each a 30-second experience, each a doorway.

Deliberately not an LLM. Every verdict is produced by explicit, readable rules with documented thresholds — transparency is the product.

## How to run

```bash
cp .env.example .env
# edit .env — set DATABASE_URL to your Cinderhaven postgres instance

pip install -r requirements.txt
make dev
# → http://localhost:8000
```

## Stack

| Layer | Tool |
|---|---|
| API | FastAPI + Uvicorn |
| Rules engine | Python (one module per question) |
| Thresholds | YAML (`config/thresholds.yaml`) |
| Frontend | Vanilla JS + D3 |
| One-pagers | Quarto → PDF |
| Data | Postgres/dbt — reads existing Cinderhaven marts, no new models |
| Deploy | Fly.io + Cloudflare |

## Project structure

```
api/          FastAPI routes and Pydantic schemas
engine/       Rules engine — base class, registry, one module per question
config/       YAML thresholds and question manifest
frontend/     Static HTML/CSS/JS — no build step
quarto/       One-pager PDF template
db/           DB connection (read-only, hits existing marts)
scripts/      check_canonical.py — release gate
tests/        Unit tests for rule logic
```

## The fifteen questions

| # | Question | Source piece | Scenario |
|---|---|---|---|
| Q01 | Should I fire my biggest customer? | Retailer Scorecard | baseline |
| Q02 | Can I afford this retailer launch? | Cost of Saying Yes | baseline |
| Q03 | Which SKUs should die? | SKU Rationalization | baseline |
| Q04 | Where is my trade spend going? | Trade Spend Diagnostic | distressed |
| Q05 | Why don't my numbers match my distributor's? | EDI Reconciliation | baseline |
| Q06 | What would a recall cost me? | Recall Blast Radius | distressed |
| Q07 | Is my product data going to break at Walmart? | Product Data Health Audit | baseline |
| Q08 | What does one wrong weight cost? | Dimension & Weight Integrity | baseline |
| Q09 | Which channel actually makes money? | Channel Profitability | baseline |
| Q10 | Am I leaving deduction money on the table? | Deduction Recovery | baseline |
| Q11–Q15 | TBD | — | — |

Q05 and Q06 are stubs pending EDI Reconciliation v2 and Recall Blast Radius pieces.
Q11–Q15 are finalized during build.

## Release gate

Before shipping, run:

```bash
make preflight
```

This runs `check_canonical.py` (every engine figure must reconcile to its source piece) and the test suite. An inconsistency here breaks the entire portfolio's coherence — it is the one unforgivable bug.

## Deployment

```bash
fly deploy
```

Configured for `ask.lailarallc.com` via Cloudflare. Set `DATABASE_URL` as a Fly secret:

```bash
fly secrets set DATABASE_URL="postgresql://..."
```

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics consulting for specialty food brands scaling into national retail.
