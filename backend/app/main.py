"""FastAPI app entrypoint.

Loads the publisher and persona catalogs once at startup (they live in
`disco-takehome-candidate/data/` and are small enough to keep in memory for
the life of the process). Exposes:

* `GET  /health`    — liveness + catalog-size sanity check.
* `POST /campaign`  — runs the two-call pipeline and returns the combined
                      `CampaignResult`.

The route handler is a plain `def`, so FastAPI offloads the (blocking) LLM
calls to its threadpool instead of stalling the event loop.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aws_lambda_powertools import Logger
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import CampaignRequest, CampaignResult
from .pipeline import plan_campaign, write_creatives

load_dotenv()
logger = Logger(service="advertisement-backend")

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


app = FastAPI(title="Disco Ad Placement Prototype", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.publishers = _load_json(DATA_DIR / "publishers.json")
app.state.personas = _load_json(DATA_DIR / "shopper_personas.json")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "publishers": len(app.state.publishers),
        "personas": len(app.state.personas),
    }


@app.post("/campaign", response_model=CampaignResult)
def campaign(request: CampaignRequest) -> CampaignResult:
    """Run plan -> creatives -> assemble the response.

    Each LLM call is its own try-block so the error message can name the stage
    that failed (useful when smoke-testing — "plan failed" vs "creatives
    failed" points at a different prompt/schema).
    """
    brief = request.advertiser_brief.strip()
    logger.info("campaign.start", brief_preview=brief[:120])

    try:
        plan = plan_campaign(
            advertiser_brief=brief,
            publishers=app.state.publishers,
            personas=app.state.personas,
        )
    except Exception as exc:
        logger.exception("plan_campaign failed")
        raise HTTPException(status_code=502, detail=f"plan_campaign failed: {exc}") from exc

    try:
        bundle = write_creatives(
            advertiser_brief=brief,
            selected_personas=plan.selected_personas,
            personas_catalog=app.state.personas,
        )
    except Exception as exc:
        logger.exception("write_creatives failed")
        raise HTTPException(status_code=502, detail=f"write_creatives failed: {exc}") from exc

    logger.info(
        "campaign.done",
        ranked_publishers=len(plan.ranked_publishers),
        excluded_publishers=len(plan.excluded_publishers),
        selected_personas=len(plan.selected_personas),
        creatives=len(bundle.creatives),
    )

    return CampaignResult(
        advertiser_brief=brief,
        ranked_publishers=plan.ranked_publishers,
        excluded_publishers=plan.excluded_publishers,
        selected_personas=plan.selected_personas,
        creatives=bundle.creatives,
        campaign_config=plan.campaign_config,
    )
