"""Consistency Pipeline: Multi-sample consensus verification.

Generates N answers at temp=0.7, extracts claims from all,
finds consensus (≥2/3 agreement), and only searches conflicting claims.

The key insight: hallucinations are random across samples.
If all 3 samples agree on a claim, it's very likely true.
If they disagree, something is off — that's where to search.
"""

import logging
from collections import Counter
from difflib import SequenceMatcher
from self_verify.result import PipelineResult
from self_verify.stages.generate import generate_answer
from self_verify.stages.extract import extract_claims
from self_verify.stages.predict import predict
from self_verify.stages.search import search_claim_set
from self_verify.stages.rewrite import rewrite

logger = logging.getLogger(__name__)


def run_consistency_pipeline(pipeline, query: str) -> PipelineResult:
    """Run the N-sample consistency pipeline.

    Args:
        pipeline: SelfVerifyPipeline instance (for access to client, config, etc.)
        query: The user's question.

    Returns:
        PipelineResult with consensus-verified answer.
    """
    cfg = pipeline.config.pipeline
    n = cfg.consistency_samples
    logger.info(f"Running consistency pipeline (n={n}) for: {query[:80]}...")

    # Step 1: Generate N answers at higher temperature
    raw_answers = []
    for i in range(n):
        raw = generate_answer(
            pipeline.client,
            query,
            temperature=cfg.temp_consistency,
        )
        raw_answers.append(raw)

    # Step 2: Extract claims from each answer
    all_claims_sets = []
    for raw in raw_answers:
        claims = extract_claims(
            pipeline.client, raw, max_claims=cfg.max_claims_per_answer
        )
        all_claims_sets.append(claims)

    # Step 3: Find consensus claims
    consensus_claims = _find_consensus(all_claims_sets, threshold=2 / 3)
    disputed_claims = _find_disputed(all_claims_sets)

    # Step 4: Only predict + search disputed claims
    if disputed_claims:
        predictions = predict(pipeline.client, disputed_claims)
        search_results = search_claim_set(
            pipeline.search_client,
            predictions,
            max_results_per_query=cfg.max_search_results,
        )
    else:
        search_results = []

    # Step 5: Rewrite using the most common answer, with search results inserted
    # Pick the answer that has the most consensus claims
    best_raw = _pick_best_answer(raw_answers, all_claims_sets, consensus_claims)

    if search_results:
        verified = rewrite(pipeline.client, query, best_raw, search_results)
    else:
        verified = best_raw

    # For consistency pipeline, every disputed claim is flagged
    all_search_results = search_results
    stats = pipeline._compute_stats(search_results) if search_results else _empty_stats(len(disputed_claims))

    return PipelineResult(
        query=query,
        answer=verified,
        raw_answer=best_raw,
        pipeline_variant="consistency",
        claims=list(set(
            c for cs in all_claims_sets for c in cs
        )),
        search_results=all_search_results,
        citations=pipeline._collect_citations(search_results) if search_results else [],
        gate_decision="visionary",
        total_claims=stats.total_claims,
        verified_claims=stats.verified_claims,
        contradicted_claims=stats.contradicted_claims,
        uncertain_claims=stats.uncertain_claims,
    )


def _find_consensus(
    claim_sets: list[list[str]],
    threshold: float = 0.66,
) -> list[str]:
    """Find claims that appear in at least threshold fraction of samples."""
    all_flat = []
    for claims in claim_sets:
        all_flat.extend(claims)

    # Group similar claims (might be worded slightly differently)
    merged = _merge_similar_claims(all_flat)

    # Return those with enough samples
    n_samples = len(claim_sets)
    result = []
    for claim_text, count in merged:
        if count / n_samples >= threshold:
            result.append(claim_text)

    return result


def _find_disputed(claim_sets: list[list[str]]) -> list[str]:
    """Find claims that DON'T have consensus — these need verification."""
    all_flat = []
    for claims in claim_sets:
        all_flat.extend(claims)

    merged = _merge_similar_claims(all_flat)
    n_samples = len(claim_sets)

    disputed = []
    for claim_text, count in merged:
        if count / n_samples < 2 / 3:
            disputed.append(claim_text)

    return disputed


def _merge_similar_claims(claims: list[str]) -> list[tuple[str, int]]:
    """Merge claims that are semantically similar (different wording, same meaning).

    Uses a simple similarity heuristic — two claims match if they share
    60% of their significant words.
    """
    # Simple approach: normalize and deduplicate by word overlap
    merged: list[tuple[str, int, set[str]]] = []  # (text, count, word_set)

    for claim in claims:
        words = set(_normalize(claim).split())
        found = False
        for i, (_, _, existing_words) in enumerate(merged):
            if words and existing_words:
                overlap = len(words & existing_words) / max(len(words | existing_words), 1)
                if overlap > 0.5:
                    merged[i] = (merged[i][0], merged[i][1] + 1, existing_words | words)
                    found = True
                    break
        if not found:
            merged.append((claim, 1, words))

    return [(text, count) for text, count, _ in merged]


def _normalize(text: str) -> str:
    """Normalize a claim for comparison."""
    import re
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    # Remove very common stopwords that add noise
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                 'would', 'could', 'should', 'may', 'might', 'can', 'shall',
                 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                 'as', 'into', 'through', 'during', 'before', 'after',
                 'above', 'below', 'between', 'out', 'off', 'over', 'under',
                 'again', 'further', 'then', 'once', 'here', 'there',
                 'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both',
                 'either', 'neither', 'each', 'every', 'all', 'any', 'few',
                 'more', 'most', 'other', 'some', 'such', 'no', 'only',
                 'own', 'same', 'very', 'just', 'also', 'too', 'quite',
                 'this', 'that', 'these', 'those'}
    words = [w for w in text.split() if w not in stopwords and len(w) > 2]
    return ' '.join(words)


def _pick_best_answer(
    answers: list[str],
    claim_sets: list[list[str]],
    consensus_claims: list[str],
) -> str:
    """Pick the answer that contains the most consensus claims."""
    best_idx = 0
    best_count = 0
    for i, claims in enumerate(claim_sets):
        count = sum(1 for c in consensus_claims if _claim_in_answer(c, answers[i]))
        if count > best_count:
            best_count = count
            best_idx = i
    return answers[best_idx]


def _claim_in_answer(claim: str, answer: str) -> bool:
    """Check if a claim's substance appears in the answer (fuzzy)."""
    return _normalize(claim)[:30] in _normalize(answer)


def _empty_stats(n: int):
    from collections import namedtuple
    Stats = namedtuple("Stats", [
        "total_claims", "verified_claims",
        "contradicted_claims", "uncertain_claims",
    ])
    return Stats(n, 0, 0, n)
