# Disco ad-placement prototype

An advertiser types one or two sentences, hits **Run**, and sees:

1. **Ranked publishers** with a per-pick rationale, plus a short list of publishers we considered and excluded (and why).
2. **3–5 selected shopper personas** with the planner's reasoning for each.
3. **One ad creative per persona** (headline, body, CTA), written in voice for that persona.
4. **A campaign config** (targeting, per-publisher allocation, suggested budget + flight, bid model + range + rationale) — the minimum shape a downstream order-creation system would need.

## Run it

```bash
# 1. Backend (FastAPI + OpenAI)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env       # OPENAI_MODEL=gpt-4o-mini is the default
uvicorn app.main:app --reload --port 8000

# 2. Frontend (Vite + React)
cd frontend
npm install
npm run dev                                # opens http://localhost:5173
```

Sanity check: `curl localhost:8000/health` should return `{"ok":true,"publishers":20,"personas":10}`. Then drop one of the lines from `disco-takehome-candidate/data/example_advertisers.txt` into the textarea and hit Run.

## How it works

Two LLM calls. That is the whole pipeline.

```
brief ──► plan_campaign  ──►  ranked publishers + exclusions
                              selected personas + reasoning
                              campaign config (targeting / allocation / budget / bid)
       └► write_creatives ──► one creative per selected persona
```

- **Call 1 (`plan_campaign`)** is the analyst. It receives the full publisher catalog (20) and full persona catalog (10) inline — they fit in a single prompt so we don't need retrieval. Output is constrained to the `CampaignPlan` Pydantic schema via OpenAI structured outputs, so the prompt focuses on *judgment*, not formatting.
- **Call 2 (`write_creatives`)** is the copywriter. It is split out because planning and copywriting want different voices (hedged-analyst vs. punchy-direct-response) and because we want to re-roll creatives without re-planning.

Prompts live under `prompts/` and are the audit surface — both files have an `## Intent` block explaining why the call exists. `pipeline.py` parses the fenced blocks directly so the markdown is the source of truth, not a duplicate Python string.

### Why the campaign config has *this* shape

It pins the smallest set of fields a real downstream system would actually need to write an order: who to target (`targeting`), where to spend (`publisher_allocation`), how much (`budget`), and how to bid (`bid_strategy`). The LLM fills the values using the publisher AOVs and audience signals it just used to rank — so the config is internally consistent with the ranking instead of being a separate guess.

## What I cut, intentionally

- **No embeddings / vector search.** 20 publishers fit in a prompt. RAG here would be solving a problem that does not exist at this scale.
- **No deterministic rubric scoring layer.** The rationale strings *are* the "show your work" surface. A scored pre-filter would be the obvious v2 once the catalog has thousands of publishers — the LLM would re-rank a top-K instead of seeing the whole list.
- **No clarifying-question flow for vague briefs.** The prompt instead instructs the planner to lower its `fit_score`s and admit uncertainty in rationales when the brief is thin.
- **No golden-input eval / LLM-as-judge harness.** Smoke-tested manually against the four lines in `example_advertisers.txt`.
- **No persistence, history, regeneration, auth, or per-signal score breakdowns in the UI.** Single-page render of whatever the backend returned.

## What I'd do next, given another week

1. **Deterministic pre-filter + score breakdowns.** Tag each publisher with a structured fit signal (category overlap, audience overlap, AOV alignment, geo). Surface those numbers in the UI as a drawer behind each rationale, so a planner can see *why* the LLM said what it said.
2. **Eval harness.** A handful of golden advertiser briefs with expected publisher sets and an LLM-as-judge over rationale quality. Run on every prompt change. This is the single biggest lever for trusting iteration.
3. **Vague-brief handling.** A pre-pass that detects under-specified briefs and either asks one targeted clarifying question or commits to a "low confidence" rendering path with banners.
4. **Creative regeneration per persona.** A "re-roll this card" button — cheap because creatives are already a separate call.
5. **Catalog scale-out.** Move the publisher/persona catalogs behind a thin retrieval layer so the prompt size stays bounded as the catalog grows.

## What's actually hard here vs. easy

**Easy:** the stack. FastAPI + Vite + a structured-output LLM call is a few hours of plumbing. With OpenAI's `responses.parse` against a Pydantic schema, the LLM cannot return malformed JSON, so the API contract more or less validates itself.

**Hard, and where the interesting work lives:**

- **Defining "good fit" without ground truth.** Rankings are inherently opinion. The interesting engineering is making those opinions auditable (visible rationale, surfaced exclusions) and evaluable (golden inputs, judge prompts) so you can move from "the demo looks plausible" to "we are confident this is improving week over week."
- **Prompt + schema co-design.** The schema constrains what the model *can* say; the prompt constrains what it *should* say. Splitting planner from copywriter, forcing exclusions, capping fit scores on vague input — those are all schema/prompt decisions that materially change output quality.
- **Pathological input.** A real system has to gracefully handle "we sell stuff online" and "advertise me a b2b enterprise sales tool against this DTC pet catalog." This prototype admits low confidence; production needs a real strategy (clarification, rejection, or routing to a different catalog).
- **Scaling the catalog.** Once publishers go from 20 to 20,000 the whole "stuff it in the prompt" approach breaks and you need retrieval + a deterministic scoring stage. The prompt stops being the brain and becomes the explainer.
