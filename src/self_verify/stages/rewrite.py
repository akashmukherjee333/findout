"""Stage 5: Rewrite the answer with citations and uncertainty markers.

Takes the original query, the model's raw answer, and the search results,
then produces a final grounded answer.
"""

from self_verify.llm import LLMClient
from self_verify.search_client import ClaimSearchResults

_SYSTEM = """You are a verification-aware editor. Your job:
1. Take the user's original query and the model's raw answer (which may contain errors).
2. Take the search results which provide evidence for or against specific claims.
3. Produce a corrected, cited answer.

Rules:
- Claims that have CONFIRMING evidence → include with inline citations [source: URL]
- Claims that have CONTRADICTING evidence → correct them, cite the source
- Claims with NO evidence found → mark as "[speculative — not verified]"
- If the search results don't cover some claims, note that too
- Keep the original structure and voice as much as possible
- Do NOT fabricate citations. Only cite URLs that were actually provided.

Format your answer with:
- Inline citations like [source: example.com]
- A "Sources" section at the bottom listing all cited URLs
- A "Not verified" section for any claims that couldn't be confirmed
"""


def rewrite(
    client: LLMClient,
    query: str,
    original_answer: str,
    search_results: list[ClaimSearchResults],
) -> str:
    """Pass 5: Produce the final verified answer."""
    # Format search results for the LLM
    search_block = _format_search_results(search_results)

    prompt = f"""Original query: {query}

Model's raw answer:
{original_answer}

Search results for each claim:
{search_block}

Produce a corrected, cited version of the answer."""

    return client.generate(
        system=_SYSTEM,
        prompt=prompt,
        temperature=0.0,
    )


def _format_search_results(results: list[ClaimSearchResults]) -> str:
    """Format search results into a structured block for the LLM."""
    blocks = []
    for csr in results:
        block = f"Claim: {csr.claim_text}\n"

        if csr.supporting_sources:
            block += "  CONFIRMING evidence:\n"
            for s in csr.supporting_sources[:3]:
                url = getattr(s, "url", "")
                snippet = getattr(s, "snippet", "")[:150]
                block += f"    - {snippet} [source: {url}]\n"

        if csr.contradicting_sources:
            block += "  CONTRADICTING evidence:\n"
            for s in csr.contradicting_sources[:3]:
                url = getattr(s, "url", "")
                snippet = getattr(s, "snippet", "")[:150]
                block += f"    - {snippet} [source: {url}]\n"

        if csr.uncertain:
            block += "  UNCERTAIN: No strong evidence found either way.\n"

        blocks.append(block)

    return "\n".join(blocks)
