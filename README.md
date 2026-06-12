# The Question Engine

**Live:** https://ask.lailarallc.com

Fifteen questions every specialty food brand CEO asks, answered with rules-based verdicts on the Cinderhaven canonical dataset. The CEO picks a question; the engine runs documented rules against the Cinderhaven mart layer and returns a verdict (one sentence, opinionated), the one chart that justifies it, the three numbers behind it, and a link into the deep-dive portfolio piece. Fifteen questions, each a 30-second experience, each a doorway.

Deliberately not an LLM. Every verdict is produced by explicit, readable rules with documented thresholds — transparency is the product.

## Cinderhaven context

Built on the Cinderhaven synthetic dataset — a ~$25M specialty food brand, 50 SKUs across 5 product lines and 6 contracted retailers. Data is synthetic; methodology and deliverables are real.

## What it does

| # | Question | Source piece |
|---|---|---|
| Q01 | Should I fire my biggest customer? | Retailer Scorecard |
| Q02 | Can I afford this retailer launch? | Cost of Saying Yes |
| Q03 | Which SKUs should die? | SKU Rationalization |
| Q04 | Where is my trade spend going? | Trade Spend Diagnostic |
| Q05 | Why don't my numbers match my distributor's? | EDI Reconciliation (stub) |
| Q06 | What would a recall cost me? | Recall Blast Radius (stub) |
| Q07 | Is my product data going to break at Walmart? | Product Data Health Audit |
| Q08 | What does one wrong weight cost? | Dimension & Weight Integrity |
| Q09 | Which channel actually makes money? | Channel Profitability |
| Q10 | Am I leaving deduction money on the table? | Deduction Recovery |
| Q11 | What are stockouts costing me? | Stockout Cost |
| Q12 | How accurate are my forecasts? | Forecast Accuracy |
| Q13 | What is my OTIF exposure? | OTIF Exposure |
| Q14 | Which SKUs are losing velocity? | Velocity Decay |
| Q15 | What is my cash conversion cycle? | Cash Conversion |

13 verdicts live; Q05 and Q06 return 503 pending their source pieces (EDI Reconciliation v2, Recall Blast Radius).

## Stack

- Python 3.13 — FastAPI + Uvicorn
- Rules engine: one module per question, YAML thresholds (`config/thresholds.yaml`)
- Frontend: vanilla JS + D3 (no build step)
- One-pagers: Quarto templates rendered to PDF (`make pdfs`)
- Data: Postgres / dbt — reads existing Cinderhaven marts, no new models
- Deploy: Fly.io (API) + Cloudflare (DNS)
- Dev: pytest, pytest-asyncio, httpx, ruff

## Data contract

**Canonical baseline:** 50 SKUs · 5 product lines (AS·PS·SC·DG·SB) · 6 retailers (Walmart·Costco·Whole Foods·Sprouts·Kroger·Regional Group) · 10 channels (6 retail + UNFI·KeHE·DPI + DTC)

Every figure shown reconciles to its source piece via `scripts/check_canonical.py`. An inconsistency breaks the entire portfolio's coherence — it is the one unforgivable bug.

## Run

```
git clone https://github.com/MsShawnP/the-question-engine.git
cd the-question-engine
cp .env.example .env
# edit .env — set DATABASE_URL to your Cinderhaven Postgres instance
pip install -r requirements.txt
make dev
# → http://localhost:8000
```

Release gate (run before every deploy):

```
make preflight
```

Deploy:

```
fly deploy
```

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics consulting for specialty food brands scaling into national retail.
