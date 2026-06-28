"""Stage 3: For each claim, predict evidence and surprises.

This replaces the failed "confidence tag" approach with generative predictions.
The model doesn't judge whether it knows — it predicts what the external world
would look like if the claim were true.
"""

from dataclasses import dataclass, field
from findout.llm import LLMClient

_SYSTEM = """You are an evidence prediction engine. Given a factual claim, your job is to predict:

1. **Evidence prediction**: If this claim is TRUE, what specific articles, studies,
   documentation, or data sources would exist to support it? Be as concrete as possible —
   name expected authors, organizations, journals, documentation pages, or data patterns.

2. **Surprise prediction**: What would DISPROVE this claim or be genuinely surprising
   if it turned out to be false? What counter-arguments or contradictory evidence
   would you expect to find?

3. **Neutral search query**: Write a neutral, unbiased search query that would let
   a search engine determine the truth without leading the results.

Output format for each:
EVIDENCE: <concrete prediction of what supporting sources would look like>
SURPRISE: <what would disprove or contradict this>
NEUTRAL: <unbiased search query>
"""


@dataclass
class ClaimPredictions:
    """Evidence and surprise predictions for one claim."""

    claim: str
    evidence_prediction: str
    surprise_prediction: str
    neutral_query: str


def predict(
    client: LLMClient,
    claims: list[str],
) -> list[ClaimPredictions]:
    """Pass 3: For each claim, generate evidence + surprise predictions."""
    if not claims:
        return []

    claims_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))

    prompt = f"""For each of the following claims, predict what evidence would exist if true,
what would disprove it, and generate a neutral search query:

{claims_text}

Response format for EACH claim:
=== Claim N ===
EVIDENCE: <prediction>
SURPRISE: <prediction>
NEUTRAL: <query>
"""

    result = client.generate(
        system=_SYSTEM,
        prompt=prompt,
        temperature=0.0,
        max_tokens=4096,
    )

    return _parse_predictions(result, claims)


def _parse_predictions(
    raw: str,
    expected_claims: list[str],
) -> list[ClaimPredictions]:
    """Parse the structured output back into ClaimPredictions objects."""
    predictions: list[ClaimPredictions] = []
    current: dict[str, str] = {}
    current_claim: str | None = None

    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("=== ") and "Claim" in line:
            # Save previous
            if current_claim and current:
                predictions.append(
                    ClaimPredictions(
                        claim=current_claim,
                        evidence_prediction=current.get("EVIDENCE", ""),
                        surprise_prediction=current.get("SURPRISE", ""),
                        neutral_query=current.get("NEUTRAL", ""),
                    )
                )
            current = {}
            current_claim = None
        elif line.upper().startswith("EVIDENCE:"):
            current["EVIDENCE"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("SURPRISE:"):
            current["SURPRISE"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("NEUTRAL:"):
            current["NEUTRAL"] = line.split(":", 1)[1].strip()
        elif current_claim is None and line:
            # Could be a claim line found before a === marker
            for c in expected_claims:
                if c[:40] in line or line[:40] in c:
                    current_claim = c
                    break

    # Don't forget the last one
    if current_claim and current:
        predictions.append(
            ClaimPredictions(
                claim=current_claim,
                evidence_prediction=current.get("EVIDENCE", ""),
                surprise_prediction=current.get("SURPRISE", ""),
                neutral_query=current.get("NEUTRAL", ""),
            )
        )

    # Fallback: if parsing failed, map by claim position
    if not predictions and expected_claims:
        # Try simpler parsing — look for EVIDENCE/SURPRISE/NEUTRAL in order
        evidences = []
        surprises = []
        neutrals = []
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("EVIDENCE:"):
                evidences.append(line.split(":", 1)[1].strip())
            elif line.upper().startswith("SURPRISE:"):
                surprises.append(line.split(":", 1)[1].strip())
            elif line.upper().startswith("NEUTRAL:"):
                neutrals.append(line.split(":", 1)[1].strip())

        for i, claim in enumerate(expected_claims):
            predictions.append(
                ClaimPredictions(
                    claim=claim,
                    evidence_prediction=evidences[i] if i < len(evidences) else "",
                    surprise_prediction=surprises[i] if i < len(surprises) else "",
                    neutral_query=neutrals[i] if i < len(neutrals) else "",
                )
            )

    return predictions
