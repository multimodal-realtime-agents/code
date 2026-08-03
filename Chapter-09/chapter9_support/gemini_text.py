"""Gemini text-generation helper used by the model-backed examples."""

from __future__ import annotations

import re

from google import genai
from google.genai import types

from .config import require_google_credentials, settings


def deterministic_text(prompt: str) -> str:
    if "Generate exactly three concise web search queries" in prompt:
        topic_match = re.search(r"topic:\s*(.+)", prompt, flags=re.IGNORECASE | re.DOTALL)
        topic = topic_match.group(1).strip() if topic_match else "A2A protocol"
        return "\n".join(
            [
                f"{topic} overview",
                f"{topic} agent card JSON-RPC",
                f"{topic} interoperability examples",
            ]
        )

    if "Write a concise three-paragraph executive summary" in prompt:
        return (
            "These deterministic notes verify that the coordinator collected "
            "remote A2A results and invoked local synthesis.\n\n"
            "They are not publication evidence; production research should "
            "return structured source records before synthesis.\n\n"
            "The smoke check proves orchestration behavior, not factual quality."
        )

    return f"Deterministic text response for: {prompt[:80]}"


def generate_text(prompt: str, *, model: str | None = None, temperature: float = 0.2) -> str:
    if settings.deterministic_smoke:
        return deterministic_text(prompt)

    require_google_credentials()
    client = genai.Client()
    response = client.models.generate_content(
        model=model or settings.model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature),
    )
    text = getattr(response, "text", None)
    if text:
        return text.strip()
    return str(response).strip()
