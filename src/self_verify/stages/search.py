"""Stage 4: 3-angle web search per claim.

Each claim gets three searches using the predictions from Stage 3:
1. Evidence-biased query — based on the "what would exist if true" prediction
2. Neutral query — unbiased, lets the web decide
3. Antithesis query — based on the "what would surprise/disprove" prediction

Results are bundled per-claim for the rewrite stage to use.
"""

from dataclasses import dataclass, field
from self_verify.search_client import SearchClient, SearchResult, ClaimSearchResults
from self_verify.stages.predict import ClaimPredictions


def search_claim_set(
    search_client: SearchClient,
    predictions: list[ClaimPredictions],
    max_results_per_query: int = 5,
) -> list[ClaimSearchResults]:
    """Pass 4: Run 3-angle search for each claim's predictions.

    Uses the predictions from Stage 3 to construct targeted queries.
    """
    results: list[ClaimSearchResults] = []

    for pred in predictions:
        csr = ClaimSearchResults(claim_text=pred.claim)

        # Angle 1: Evidence-biased search
        if pred.evidence_prediction:
            evidence_query = _build_evidence_query(pred)
            csr.evidence_results = search_client.search(
                evidence_query, max_results=max_results_per_query
            )

        # Angle 2: Neutral search
        if pred.neutral_query:
            csr.neutral_results = search_client.search(
                pred.neutral_query, max_results=max_results_per_query
            )

        # Angle 3: Antithesis search
        if pred.surprise_prediction:
            antithesis_query = _build_antithesis_query(pred)
            csr.antithesis_results = search_client.search(
                antithesis_query, max_results=max_results_per_query
            )

        results.append(csr)

    return results


def _build_evidence_query(pred: ClaimPredictions) -> str:
    """Build a query biased toward finding supporting evidence.

    Uses key terms from the evidence prediction to search for sources
    that the model predicted would exist if the claim were true.
    """
    # Use the first 80 characters of the evidence prediction as a query
    ev = pred.evidence_prediction[:120].strip()
    if not ev:
        return pred.claim
    return ev


def _build_antithesis_query(pred: ClaimPredictions) -> str:
    """Build a query biased toward finding contradicting evidence.

    Uses key terms from the surprise prediction to look for
    evidence that would disprove the claim.
    """
    sp = pred.surprise_prediction[:120].strip()
    if not sp:
        return f'"{pred.claim}" myth debunked'
    return sp
