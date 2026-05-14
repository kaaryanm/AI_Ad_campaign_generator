# Disco ad-placement prototype

This demo turns a short advertiser brief into a usable campaign draft:
- ranked publishers with rationale plus explicit exclusions,
- 3-5 selected shopper personas with reasoning,
- one creative per selected persona (headline/body/CTA),
- structured campaign config (`targeting`, `publisher_allocation`, `budget`, `bid_strategy`).

## How to run

Canonical reviewer path (single command from repo root):

```bash
cd AI_Ad_campaign_generator
echo "OPENAI_API_KEY=sk-..." > backend/.env    # optional: OPENAI_MODEL=gpt-4o-mini
./start_servers.sh
```

`./start_servers.sh` bootstraps `backend/.venv` if needed, installs deps, and starts:
- backend at `http://localhost:8000`
- frontend at `http://localhost:5173`

Stop with `Ctrl+C`.

Submission smoke check (run while `./start_servers.sh` is active):
- `curl localhost:8000/health` -> `{"ok":true,"publishers":20,"personas":10}`
- submit one brief in the UI (or `POST /campaign`) and expect HTTP `200` with:
  - `ranked_publishers` + `excluded_publishers`
  - `selected_personas` (3-5)
  - `creatives` (one per persona)
  - `campaign_config` (`targeting`, `publisher_allocation`, `budget`, `bid_strategy`)

## What I built

Pipeline is intentionally two calls:
1. `plan_campaign`: plans publishers/personas/campaign config using structured output (`CampaignPlan` schema).
2. `write_creatives`: writes persona-specific copy from that plan.

Prompts are auditable in `prompts/01_plan_campaign.md` and `prompts/02_write_creatives.md` (with intent documented in each).

## What I cut (and why)

- Kept orchestration to two LLM calls (`plan_campaign` + `write_creatives`) to ship a reliable end-to-end prototype quickly; did not split ranking, persona selection, config assembly, and creative generation into separate calls yet.
- No staged/streaming UI progression yet: users currently wait for the final assembled response (typically ~10-25 seconds) instead of seeing intermediate outputs section by section.
- No advertiser budget input in the UI: campaign budget and allocation are inferred by the model rather than constrained by a user-provided target spend.
- No retrieval/embeddings or deterministic pre-scoring layer yet: rationale text is the current "show your work" surface for recommendations.
- No eval harness, persistence, auth, clarifying-question loop, or regeneration UX in this prototype: scope stayed focused on proving the core flow.

## What I'd add with one more week

1. Move from 2 calls to a multi-step call graph (intent extraction -> publisher ranking -> persona selection -> campaign config -> creative generation) so each step has narrower context and more controllable outputs.
2. Run independent steps in parallel where possible and update the UI progressively (publishers first, then personas, then config, then creatives) to improve perceived responsiveness.
3. Add optional advertiser inputs (daily/total budget, geography, risk preference) and use those as hard constraints when generating strategy and publisher allocation.
4. Add deterministic pre-filtering and score features ahead of LLM reasoning to increase consistency and improve explainability.
5. Add golden-brief evaluation plus LLM-judge checks for rationale quality and persona-to-creative alignment.
6. Add better low-signal handling (clarifying questions or explicit low-confidence mode) and persona-level creative regeneration.
7. Introduce retrieval/indexing once catalogs grow beyond prompt-friendly size.

## What's hard vs. easy

Easy: wiring FastAPI + Vite + structured LLM outputs.

Hard:
- defining "good fit" without ground-truth labels,
- co-designing prompt + schema to improve consistency and auditability,
- handling pathological or underspecified briefs gracefully,
- scaling from small inline catalogs to large retrieval-backed catalogs.
