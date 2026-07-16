"""AI-powered hint generation with a deterministic fallback."""

from __future__ import annotations

import os

import requests

DEFAULT_MODEL = "gemini-2.5-flash-lite"
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)


class HintError(RuntimeError):
    """Raised when the configured AI provider cannot return a hint."""


def generate_ai_hint(
    current_title: str,
    target_title: str,
    article_text: str,
    candidate_links: list[str],
) -> str:
    """Ask Gemini for a concise clue without revealing the exact route."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HintError("GEMINI_API_KEY is not configured")

    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    links = ", ".join(candidate_links[:40])
    prompt = f"""
You are the hint system for a Wikipedia navigation game.

The player is currently reading: {current_title}
The target article is: {target_title}
Some clickable links on the current article are:
{links}

Article excerpt:
{article_text}

Give one short Traditional Chinese hint that helps the player choose a useful
link. Do not reveal a full path, do not claim a link exists unless it appears
in the supplied link list, and do not name the best link directly. Keep the
hint under 80 Traditional Chinese characters.
""".strip()

    response = requests.post(
        GEMINI_ENDPOINT.format(model=model),
        headers={"x-goog-api-key": api_key},
        json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    try:
        hint = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise HintError("Gemini returned an unexpected response") from exc

    if not hint:
        raise HintError("Gemini returned an empty hint")
    return hint


def fallback_hint(current_title: str, target_title: str, next_title: str) -> str:
    """Provide a playable hint when no AI key is configured or the API fails."""
    if next_title:
        return f"從「{current_title}」出發，尋找與「{next_title}」相關的文章連結。"
    return f"你已偏離預設路徑，先尋找能把主題帶向「{target_title}」的廣泛概念。"
