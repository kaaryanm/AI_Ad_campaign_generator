"""Two-call planning pipeline.

* `plan_campaign()` — one LLM call. Ranks publishers, picks personas, drafts
  the campaign config. Returns a fully-validated `CampaignPlan`.
* `write_creatives()` — one LLM call. Turns each selected persona into one
  ad creative variant. Returns a `CreativeBundle`.

Prompts live in `prompts/*.md` and are the human-auditable source of truth
(per the spec). We parse the fenced code blocks under the `## System prompt`
and `## User template` headings so the markdown files do not have to be kept
in sync with separate Python strings.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from aws_lambda_powertools import Logger
from .llm import chat_json
from .models import CampaignPlan, CreativeBundle, Persona

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"
logger = Logger(service="advertisement-backend")


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


# Matches `## Title` followed (after whitespace) by the first fenced code
# block. Code-block language tag (if any) is allowed but ignored.
_SECTION_RE = re.compile(
    r"^##\s+(?P<title>[^\n]+?)\s*\n+```[^\n]*\n(?P<body>.*?)\n```",
    re.MULTILINE | re.DOTALL,
)


def _extract_named_code_blocks(markdown: str) -> dict[str, str]:
    """Map lowercased `## Heading` title -> contents of the fenced block that follows it."""
    return {
        m.group("title").strip().lower(): m.group("body")
        for m in _SECTION_RE.finditer(markdown)
    }


@lru_cache(maxsize=None)
def _load_prompt(filename: str) -> tuple[str, str]:
    """Parse `prompts/<filename>` and return (system_prompt, user_template)."""
    path = PROMPTS_DIR / filename
    blocks = _extract_named_code_blocks(path.read_text(encoding="utf-8"))
    try:
        system_prompt = blocks["system prompt"]
        user_template = blocks["user template"]
    except KeyError as exc:
        raise RuntimeError(
            f"{path.name} is missing required section: {exc.args[0]!r}"
        ) from exc
    logger.info("prompt.loaded", prompt_file=filename)
    return system_prompt, user_template


def _render(template: str, **values: Any) -> str:
    """Replace `{{var}}` placeholders. Plain string substitution; no escaping rules to fight."""
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered


# ---------------------------------------------------------------------------
# Call 1: plan_campaign
# ---------------------------------------------------------------------------


def plan_campaign(
    advertiser_brief: str,
    publishers: list[dict[str, Any]],
    personas: list[dict[str, Any]],
) -> CampaignPlan:
    """Rank publishers, choose personas, draft a campaign config (one LLM call)."""
    logger.info(
        "plan_campaign.start",
        publishers=len(publishers),
        personas=len(personas),
    )
    system, user_template = _load_prompt("01_plan_campaign.md")
    user = _render(
        user_template,
        advertiser_brief=advertiser_brief.strip(),
        publishers_json=json.dumps(publishers, indent=2),
        personas_json=json.dumps(personas, indent=2),
    )
    result = chat_json(system=system, user=user, schema=CampaignPlan)
    logger.info(
        "plan_campaign.done",
        ranked_publishers=len(result.ranked_publishers),
        selected_personas=len(result.selected_personas),
    )
    return result


# ---------------------------------------------------------------------------
# Call 2: write_creatives
# ---------------------------------------------------------------------------


def write_creatives(
    advertiser_brief: str,
    selected_personas: list[Persona],
    personas_catalog: list[dict[str, Any]],
) -> CreativeBundle:
    """Generate one creative variant per selected persona (one LLM call).

    `selected_personas` carries the planner's reasoning (`Persona` objects from
    `plan_campaign`'s output). `personas_catalog` is the raw `personas.json` so
    we can attach each persona's full profile (messaging preferences,
    disinterests, AOV) to what the copywriter sees.
    """
    logger.info("write_creatives.start", selected_personas=len(selected_personas))
    system, user_template = _load_prompt("02_write_creatives.md")
    catalog_by_id = {p["id"]: p for p in personas_catalog}

    enriched: list[dict[str, Any]] = []
    for chosen in selected_personas:
        enriched.append(
            {
                "persona_id": chosen.persona_id,
                "persona_name": chosen.name,
                "planner_reasoning": chosen.selection_reasoning,
                "profile": catalog_by_id.get(chosen.persona_id, {}),
            }
        )

    user = _render(
        user_template,
        advertiser_brief=advertiser_brief.strip(),
        personas_json=json.dumps(enriched, indent=2),
    )
    result = chat_json(system=system, user=user, schema=CreativeBundle)
    logger.info("write_creatives.done", creatives=len(result.creatives))
    return result
