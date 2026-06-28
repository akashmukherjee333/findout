"""Stage 2: Extract atomic claims from an answer.

Each claim should be a single factual assertion that can be independently verified.
"""

import re
from findout.llm import LLMClient

_SYSTEM = """Extract atomic factual claims from the given text.

Rules:
- Each claim must be ONE verifiable assertion — a single fact that could be true or false.
- Break compound sentences into multiple claims.
- Keep the original wording as much as possible.
- Skip: opinions, subjective statements, rhetorical questions, transitional phrases.
- Skip: meta-commentary ("as previously mentioned", "in conclusion").
- Output format: one claim per line, starting with "- ".
- Maximum 12 claims. If there are more, list the most important ones.

Example:
Input: "PostgreSQL uses MVCC for concurrency control. It was created in 1996 by Michael Stonebraker. Some people think it's better than MySQL for complex queries."
Output:
- PostgreSQL uses MVCC for concurrency control
- PostgreSQL was created in 1996
- PostgreSQL was created by Michael Stonebraker

Note: "Some people think it's better" is an opinion — skip it.
"""


def extract_claims(client: LLMClient, answer: str, max_claims: int = 12) -> list[str]:
    """Pass 2: Split the answer into atomic, verifiable claims."""
    result = client.generate(
        system=_SYSTEM,
        prompt=f"Extract claims from this text:\n\n{answer}",
        temperature=0.0,
        max_tokens=1024,
    )

    # Parse bullet points
    claims = []
    for line in result.split("\n"):
        line = line.strip()
        # Match "- " or "* " bullets
        if line.startswith("- ") or line.startswith("* "):
            claim = line[2:].strip()
            if claim:
                claims.append(claim)
        # Also match numbered lists like "1. claim"
        elif re.match(r"^\d+[.)]\s+", line):
            claim = re.sub(r"^\d+[.)]\s+", "", line).strip()
            if claim:
                claims.append(claim)

    return claims[:max_claims]
