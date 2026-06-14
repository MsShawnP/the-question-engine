# Portfolio Project Brief: The Question Engine

**Created:** June 10, 2026
**Source:** `portfolio_priority_list_gtd.md` Next list
**Template:** `portfolio_brief_template.md`

**Status:** Brief stage
**Tier:** 1 (portfolio front door / capstone)
**Priority:** Next #5 — last by design. It aggregates every shipped piece; building it earlier would have meant rebuilding it. Score 23/35 understates it because its value is positional, not standalone.

### 1. The Pain

The CEO doesn't wake up thinking "I need a data consultant." They wake up with a question: *Should I fire my biggest customer? Can I afford the Costco launch? Which SKUs are killing me? Why is cash tight when sales are up?* The pain this piece addresses is the *practice's* discoverability pain wearing the buyer's clothes: every shipped portfolio piece answers one of these questions brilliantly, but the buyer has to already know which piece to open. There is no front door organized the way the buyer actually thinks — by question.

- **Who feels it:** CEO/founder, in question form.
- **Positioning truth:** this piece is the practice thesis ("decision-framework consulting") made literal — decisions in, frameworks out.

#### The Status Quo

A portfolio /work page organized by deliverable type — fine for evaluators, wrong for a CEO at 11pm with a specific anxiety.

### 2. Why This Piece

- It is the aggregation layer: 15 curated questions, each answered with a rules-based verdict + one chart, each routing into the shipped piece that goes deep. Every prior build becomes a destination; this is the router.
- Proves the practice identity better than any single diagnostic: the buyer experiences "ask a business question, get a framework" in 30 seconds.
- Sequencing logic (long established): built last because it consumes everything else. Everything else now exists.

### 3. The Portfolio Piece

**Working title:** *What's Actually Going On In My Business? — Fifteen Questions Every Food Brand CEO Asks* (working; final title should be the question itself, e.g. *Ask Cinderhaven*)

The user picks a question. The engine runs rules against the Cinderhaven canonical dataset and returns: a **verdict** (one sentence, opinionated), the **one chart** that justifies it, the **three numbers** behind it, and the **"go deeper"** link into the relevant shipped piece. Fifteen questions, each a 30-second experience, each a doorway.

#### Structure

- **Part 1 — The hook:** the question list itself. Reading it IS the hook — a CEO scans fifteen questions and recognizes at least four as theirs. Candidate set (draws on every shipped piece): Should I fire my biggest customer? (Retailer Scorecard) · Can I afford this retailer launch? (Cost of Saying Yes) · Which SKUs should die? (SKU Rationalization) · Where is my trade spend going? (Trade Spend Diagnostic) · Why don't my numbers match my distributor's? (EDI Reconciliation) · What would a recall cost me? (Blast Radius) · Is my product data going to break at Walmart? (PDHA/Pre-flight) · What does one wrong weight cost? (Dimension & Weight) · Which channel actually makes money? (Channel Profitability) · Am I leaving deduction money on the table? (Deduction Recovery) · …+5, finalized at build.
- **Part 2 — The proof:** the verdict mechanics. Each question has explicit, documented rules (thresholds, comparisons) — not a black box, not an LLM. The transparency is the point: "here is exactly how this verdict was reached" — the anti-dashboard.
- **Part 3 — The evidence:** Quarto export — any question's answer downloads as a board-ready one-pager; the rules files themselves in the repo (readable YAML/Python per question).

#### The Margin Math

Inherited — each question surfaces the dollar figure its underlying piece established ($93K in data-attributable chargebacks, $460K in operational waste, etc.). The engine is where all the portfolio's numbers appear on one surface for the first time. That synthesis is itself the demo: "imagine this running on your data."

#### Before / After

- **Before:** the buyer browses a portfolio of deliverables and has to map their anxiety onto it.
- **After:** the buyer clicks their actual question and gets an opinionated, justified answer in 30 seconds — then finds the deep piece behind it.

#### Who Else Sees This?

- **Primary:** CEO/founder — this is the most CEO-native artifact in the portfolio.
- **Secondary:** everyone they forward a one-pager to.
- **Shared:** the Quarto export is the share mechanism — a verdict PDF lands in a leadership Slack.

### 4. Technical Specification

- **Repo:** `question-engine` — "Fifteen questions every specialty food CEO asks, answered with rules-based verdicts on a realistic dataset."

| Tool | Role |
|------|------|
| FastAPI | Verdict API over the platform marts |
| Python | Rules engine (per-question rule modules, YAML-configured thresholds) |
| JS + D3 | Question UI + the one-chart-per-question |
| Quarto | One-pager export per question |
| Postgres/dbt | Reads existing marts only — no new models if possible |

#### Deliverables

| Deliverable | Format | Purpose |
|------------|--------|---------|
| The engine | Web app | The front door |
| 15 verdict one-pagers | Quarto → PDF | The shareables |
| Rules library | Repo (YAML + Python) | Transparency = credibility |
| Question → piece routing map | In-app | The portfolio's new nav layer |

#### Deployment

Fly.io + Cloudflare, `ask.lailarallc.com` — and promoted to primary CTA on the homepage. This becomes the front door, not just another card on /work.

#### Simulated Data Sources

None new — reads canonical marts. Hard requirement: **every figure shown must reconcile to its source piece.** A verdict that contradicts the piece it links to is the one unforgivable bug.

### 5. Skills Demonstrated

Synthesis. Rules-engine design, API design, the judgment to compress fifteen complex analyses into fifteen honest one-sentence verdicts, and a coherent portfolio architecture — the meta-skill the whole practice sells.

### 6. Foot-in-the-Door Offering

- **Offering:** "The Fifteen Questions, On Your Data" — the engine's question set run as a diagnostic engagement.
- **Format:** fixed-fee 3-week engagement; client gets all fifteen verdicts on their actual data, with the same one-pager format.
- **Price range:** $20K–$35K (it's a compressed version of several audits).
- **Client lift:** data exports per the standard pattern (ERP, deduction remittances, EDI archive, Shopify) — the engine's question list doubles as the data request list.

#### The DIY Defense

The rules are visible — deliberately. What can't be copied: the thresholds are calibrated by the domain depth of fourteen prior pieces, and running them on real data requires the cleaning/mapping layer every prior piece demonstrates. Showing the rules and being uncopyable anyway is the flex.

### 7. Marketing / Distribution

- **Portfolio:** becomes the homepage hero CTA. /work reorganizes around it.
- **LinkedIn:** one post per question — fifteen posts of pre-made content, each ending at the engine. This is a content calendar, not a launch post.
- **SEO:** the questions are literal search queries ("should I fire my biggest retail customer," "what does a product recall cost").
- **Gating:** engine open; consider gating only bulk one-pager download.

### 8. Competitor / Existing Content Scan

"Ask your data" products are all LLM-on-a-database now — confident, unexplainable, generic. **Gap/angle:** the deliberate anti-LLM positioning — fifteen questions chosen by domain expertise, answered by transparent rules, on a dataset realistic enough to feel like yours. Curation as the product.

### 9. Cinderhaven Integration

The capstone consumer. Reads every canonical mart; figures must match every shipped piece (the $93K, the $460K, channel rankings, SKU kill list). Run `make check-canonical` style validation as a release gate — an inconsistency here breaks the entire portfolio's coherence, not just this piece. Decision needed: trade-spend questions read baseline or distressed scenario (whichever the linked piece shows — likely distressed for the trade question, baseline elsewhere; document it).

### 10. Tactical Notes

- The fifteen questions are the design. Spend the brainstorm budget there; the engineering is straightforward.
- Verdicts must be opinionated. "It depends" answers kill the piece. Every verdict takes a position and shows its rule.
- Scenario-flag handling (baseline vs distressed) must be explicit per question to avoid silently mixing canonical universes.
- Resist adding question #16. Fifteen, curated, final.

#### The Credibility Marker

The verdict sentences themselves — each one must sound like a operator who has seen the pattern, not a BI tool. ("Your biggest account by revenue is your least profitable after cost-to-serve. Renegotiate terms before walking — three of five levers are negotiable.")

#### Data Paranoia / Security

Low for the demo. The engagement version inherits the standard reassurance stack (NDA, anonymizer, on-your-infrastructure option).

### 11. Open Questions

- [ ] Final fifteen questions (have ~10 locked from shipped pieces; need ~5 more)
- [ ] Final name (*Ask Cinderhaven* vs question-as-title)
- [ ] Homepage takeover: full hero replacement or co-primary CTA
- [ ] Baseline vs distressed scenario per question — document the mapping
- [ ] LLM-assisted natural-language question matching on top of the fixed fifteen, or pure click-to-select (lean pure select for v1 — preserves the anti-LLM positioning)

### 12. Build Estimate

- **Effort:** Medium (engineering) / Large (design + curation + reconciliation testing)
- **Dependencies:** everything — by design. All currently satisfied except EDI Reconciliation v2 and Recall Blast Radius (two of the fifteen questions); build after those or stub those two questions.
- **New skills:** none

#### Out of Scope

- Free-text question input / LLM interpretation (v2 at most)
- User-uploaded data ("run on your numbers" stays an engagement, not a feature)
- More than fifteen questions
- Any new data generation


---
## Cross-brief notes

- **Canonical governance applies to all five.** Briefs 2 and 3 generate new data (genealogy, X12 corpus): new isolated seeds, registered in `CINDERHAVEN_CANONICAL.md`, drift-guard coverage, injected-error ledgers as validation ground truth. Briefs 1, 4, 5 generate none and must reconcile exactly.
- **Hero SKU continuity:** CHP-0009 is the worked example in briefs 1 and 4; candidate hero lot for brief 2.
- **Research tasks before any build:** FSMA 204 current enforcement dates + retailer mandates (brief 2); GS1 Sunrise 2027 current status (brief 4). Both verified at build time, not from memory.
- **Sequencing within the five:** 1 → 2 → 3 → 4 → 5 as listed. Brief 4 can float anywhere as filler. Brief 5 wants 2 and 3 done first or ships with two stubbed questions.
