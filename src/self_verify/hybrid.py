"""Hybrid Pipeline: Combined multi-sample + verification for small models.

For models 3B-14B where instruction-following is unreliable:

1. Generate N=2 answers at temp=0.7
2. If they agree on ALL claims → short-circuit, return directly (no search)
3. If they disagree → search only the conflicting set
4. Rewrite with conflicts explicitly marked

The core assumption: for a weak model, agreement between 2 runs is stronger
evidence than any single run's "confidence."
"""

import logging
from self_verify.result import PipelineResult
from self_verify.stages.generate import generate_answer
from self_verify.stages.extract import extract_claims
from self_verify.stages.predict import predict
from self_verify.stages.search import search_claim_set
from self_verify.stages.rewrite import rewrite
from self_verify.consistency import _find_consensus, _find_disputed, _normalize

logger = logging.getLogger(__name__)


def run_hybrid_pipeline(pipeline, query: str) -> PipelineResult:
    """Run the hybrid pipeline for small local models.

    Short-circuits when both samples agree — saving search costs.
    Only spends tokens on verification when samples disagree.
    """
    cfg = pipeline.config.pipeline
    logger.info(f"Running hybrid pipeline for: {query[:80]}...")

    # Step 1: Generate 2 answers at gentle temp
    raw_1 = generate_answer(
        pipeline.client, query, temperature=cfg.temp_hybrid
    )
    raw_2 = generate_answer(
        pipeline.client, query, temperature=cfg.temp_hybrid
    )

    # Step 2: Extract claims from both
    claims_1 = extract_claims(
        pipeline.client, raw_1, max_claims=cfg.max_claims_per_answer
    )
    claims_2 = extract_claims(
        pipeline.client, raw_2, max_claims=cfg.max_claims_per_answer
    )

    all_claims_sets = [claims_1, claims_2]

    # Step 3: Find consensus and disputed claims
    consensus = _find_consensus(all_claims_sets, threshold=1.0)  # Both must agree
    disputed = _find_disputed(all_claims_sets)

    # Step 4: Short-circuit if full agreement
    if not disputed and cfg.short_circuit_on_agreement:
        logger.info("Both samples agree — short-circuiting, no search needed.")
        # Use the more detailed answer
        best_raw = raw_1 if len(raw_1) >= len(raw_2) else raw_2
        return PipelineResult(
            query=query,
            answer=best_raw,
            raw_answer=best_raw,
            pipeline_variant="hybrid",
            claims=list(set(claims_1 + claims_2)),
            search_results=[],
            citations=[],
            gate_decision="visionary",
            total_claims=len(consensus),
            verified_claims=len(consensus),
            contradicted_claims=0,
            uncertain_claims=0,
        )

    # Only search disputed claims
    if disputed:
        predictions = predict(pipeline.client, disputed)
        search_results = search_claim_set(
            pipeline.search_client,
            predictions,
            max_results_per_query=cfg.max_search_results,
        )
    else:
        search_results = []

    # Step 5: Rewrite with search results
    # Use the longer answer as the base
    best_raw = raw_1 if len(raw_1) >= len(raw_2) else raw_2

    if search_results:
        verified = rewrite(pipeline.client, query, best_raw, search_results)
    else:
        verified = best_raw

    stats = pipeline._compute_stats(search_results) if search_results else _empty_stats(len(disputed))

    return PipelineResult(
        query=query,
        answer=verified,
        raw_answer=best_raw,
        pipeline_variant="hybrid",
        claims=list(set(claims_1 + claims_2)),
        search_results=search_results or [],
        citations=pipeline._collect_citations(search_results) if search_results else [],
        gate_decision="visionary",
        total_claims=stats.total_claims,
        verified_claims=stats.verified_claims,
        contradicted_claims=stats.contradicted_claims,
        uncertain_claims=stats.uncertain_claims,
    )


def _empty_stats(n: int):
    from collections import namedtuple
    Stats = namedtuple("Stats", [
        "total_claims", "verified_claims",
        "contradicted_claims", "uncertain_claims",
    ])
    return Stats(n, 0, 0, n)
