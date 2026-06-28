"""Gate classifier — casual chat vs research-worthy query.

This is the cheapest possible pass. It uses a stripped-down prompt
and a short model response to decide whether to run the full pipeline
or answer directly.

The gate is intentionally biased toward "research" — false positives
cost tokens, false negatives cost correctness.
"""

from findout.llm import LLMClient
from findout.config import GateConfig, LLMConfig

# Minimal system prompt — we want this fast, not thorough.
_SYSTEM = """You classify queries into exactly one of two categories.

Rules:
- "casual": factual recall, simple questions, common knowledge, chat, jokes, opinions.
  The model can answer this from training data with high confidence.
- "visionary": abstract systems, "what if" scenarios, novel combinations of ideas,
  multi-claim proposals, incomplete ideas the user is still forming.
  These benefit from verification and decomposition.

Respond with ONLY the word "casual" or "visionary". No explanation.
"""


class Gate:
    """Fast classifier that decides whether to trigger the pipeline."""

    def __init__(
        self,
        config: GateConfig,
        llm_config: LLMConfig,
    ):
        self.enabled = config.enabled
        model = config.model or llm_config.model
        self.client = LLMClient(
            model=model,
            base_url=llm_config.base_url,
            api_key=llm_config.api_key,
            max_tokens=10,  # We only need one word back
            timeout=30,
        )

    def classify(self, query: str) -> str:
        """Returns 'casual' or 'visionary'."""
        if not self.enabled:
            return "visionary"  # If gate is off, always pipeline

        # Strip whitespace, truncate for speed
        cleaned = query.strip()[:500]
        response = self.client.generate(
            system=_SYSTEM,
            prompt=cleaned,
            temperature=0.0,
            max_tokens=5,
        )
        response = response.strip().lower()

        if "visionary" in response:
            return "visionary"
        return "casual"

    def classify_with_reason(self, query: str) -> tuple[str, str]:
        """Returns (category, reason) — useful for debugging."""
        if not self.enabled:
            return "visionary", "gate disabled"

        cleaned = query.strip()[:500]
        # Use a slightly expanded prompt to get reasoning
        resp = self.client.generate(
            system=_SYSTEM
            + "\nIf you need to explain, append ' — REASON: <short reason>' after your answer.",
            prompt=cleaned,
            temperature=0.0,
            max_tokens=30,
        )
        parts = resp.split(" — REASON:", 1)
        category = parts[0].strip().lower()
        reason = parts[1].strip() if len(parts) > 1 else "no reason given"

        if "visionary" in category:
            return "visionary", reason
        return "casual", reason
