"""Stage 1: Generate raw answer (cold)."""

from self_verify.llm import LLMClient

_SYSTEM = """You are a helpful AI assistant. Answer the user's question directly and thoroughly.
Do NOT add disclaimers like "as an AI" or "I don't have real-time access to the web."
Just answer what you know. Be specific. Include concrete examples, numbers, and details where relevant.

Your answer will be fact-checked in subsequent steps. Don't try to hedge or be vague
to avoid being wrong — state claims clearly even if uncertain. Uncertainty is handled later."""


def generate_answer(
    client: LLMClient,
    query: str,
    temperature: float = 0.0,
) -> str:
    """Pass 1: Generate a cold, un-verified answer."""
    return client.generate(
        system=_SYSTEM,
        prompt=query,
        temperature=temperature,
    )
