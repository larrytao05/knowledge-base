import json
from dataclasses import dataclass
from typing import Any, cast

from openai import BadRequestError, OpenAI

from app.config import settings
from app.schemas import Source, Verdict

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class AgentCheckError(Exception):
    """Raised when the agent fails to produce a usable report."""


@dataclass
class CheckResult:
    verdict: Verdict
    reasoning: str
    sources: list[Source]


SYSTEM_PROMPT = (
    "You are a fact-checking research assistant helping someone keep their "
    "notes honest. You'll be given a claim someone wrote down, and recent "
    "web search results. Your ONLY job is to check the "
    "claim against the evidence and output a verdict. Do NOT write your own "
    "essay or notes on the topic. Do NOT use markdown headers, bullet points, "
    "or bold text anywhere.\n\n"
    "Your entire reply must be exactly one JSON object and nothing else - no "
    "preamble, no explanation before or after it. It must match this shape:\n"
    '{"verdict": "on_track" | "diverging" | "unclear", "reasoning": "2-4 plain '
    'text paragraphs grounded in the search results", "sources": [{"title": '
    '"...", "url": "..."}]}\n\n'
    "verdict meanings: on_track = evidence supports the claim. diverging = "
    "evidence contradicts or undermines it. unclear = insufficient or mixed "
    "evidence.\n\n"
    "Reminder: reply with the JSON object only."
)

VALID_VERDICTS = {"on_track", "diverging", "unclear"}

REPORT_JSON_SCHEMA: dict[str, Any] = {
    "name": "check_report",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": sorted(VALID_VERDICTS)},
            "reasoning": {"type": "string"},
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": ["string", "null"]},
                        "url": {"type": "string"},
                    },
                    "required": ["title", "url"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["verdict", "reasoning", "sources"],
        "additionalProperties": False,
    },
}


def _extract_json(content: str) -> dict[str, Any] | None:
    """Parse a JSON object out of a model response, tolerating markdown fences
    or stray prose around it (weaker free models don't always follow
    "respond with ONLY JSON" exactly)."""
    candidates = [content, content.strip("`").removeprefix("json").strip()]
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        candidates.append(content[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _request(client: OpenAI, messages: list[dict[str, str]], *, strict: bool) -> Any:
    extra_body: dict[str, Any] = {"plugins": [{"id": "web", "max_results": 5}]}
    kwargs: dict[str, Any] = {"extra_body": extra_body}
    if strict:
        kwargs["response_format"] = {"type": "json_schema", "json_schema": REPORT_JSON_SCHEMA}
        # Route only to providers that actually honor response_format, instead
        # of silently ignoring it - OpenRouter support for structured outputs
        # varies by provider even for the same model.
        extra_body["provider"] = {"require_parameters": True}
    return client.chat.completions.create(
        model=settings.openrouter_model, messages=messages, **kwargs  # type: ignore[arg-type]
    )


def run_check(*, claim: str) -> CheckResult:
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)
    user_content = f"Claim:\n{claim}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    try:
        response = _request(client, messages, strict=True)
    except BadRequestError:
        # No provider behind the current model/routing alias supports strict
        # structured outputs right now - fall back to prompt-only JSON.
        response = _request(client, messages, strict=False)

    content = response.choices[0].message.content
    if not content:
        raise AgentCheckError("model returned an empty response")

    return _coerce_result(content)


def _coerce_result(content: str) -> CheckResult:
    """Build a result from the model's response, degrading gracefully instead
    of failing outright when the output doesn't match the expected shape -
    the raw content is still useful to the user even as an "unclear" verdict."""
    data = _extract_json(content) or {}

    verdict = data.get("verdict")
    if verdict not in VALID_VERDICTS:
        verdict = "unclear"

    reasoning = data.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        reasoning = content.strip()

    sources: list[Source] = []
    raw_sources = data.get("sources")
    if isinstance(raw_sources, list):
        for entry in raw_sources:
            if isinstance(entry, dict) and isinstance(entry.get("url"), str):
                sources.append(Source(title=entry.get("title"), url=entry["url"]))

    return CheckResult(verdict=cast(Verdict, verdict), reasoning=reasoning, sources=sources)
