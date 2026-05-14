"""Minimal OpenAI wrapper.

One public helper, `chat_json`, used by both pipeline calls. It hides the
"system + user + structured-output schema" boilerplate so `pipeline.py` reads
as a pair of named calls instead of a pair of slightly-different request
builders.

The client is constructed lazily on first use so importing this module never
requires `OPENAI_API_KEY` to be set (handy for tests and `/health`).
"""

from __future__ import annotations

import os
from typing import TypeVar

from aws_lambda_powertools import Logger
from openai import OpenAI
from pydantic import BaseModel

_DEFAULT_MODEL = "gpt-4o-mini"
logger = Logger(service="advertisement-backend")

T = TypeVar("T", bound=BaseModel)

_client: OpenAI | None = None


def _client_or_init() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set; populate backend/.env or export it."
            )
        _client = OpenAI(api_key=api_key)
        logger.info("openai.client.initialized")
    return _client


def chat_json(*, system: str, user: str, schema: type[T]) -> T:
    """One-shot structured-output completion. Returns a populated `schema` instance.

    Uses OpenAI's `chat.completions.parse`, which converts the Pydantic model
    to a strict JSON schema (all fields required, no `additionalProperties`)
    and validates the response against it before handing us a parsed object.
    """
    client = _client_or_init()
    model = os.environ.get("OPENAI_MODEL") or _DEFAULT_MODEL
    logger.info("openai.chat_json.request", model=model, schema=schema.__name__)

    completion = client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=schema,
    )

    choice = completion.choices[0].message
    if choice.parsed is None:
        raise RuntimeError(
            f"OpenAI returned no parsed object for {schema.__name__} "
            f"(refusal: {choice.refusal!r})."
        )
    logger.info("openai.chat_json.response", schema=schema.__name__)
    logger.info("openai.chat_json.response.parsed", content=choice.parsed)
    return choice.parsed
