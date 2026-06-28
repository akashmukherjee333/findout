"""Base Pipeline: self-verify.

5 deterministic passes through the same model.
No multi-model fan-out. No training. Just structured prompting + web search.
"""

import logging
from findout.llm import LLMClient
from findout.search_client import SearchClient, ClaimSearchResults
from findout.gate import Gate
from findout.config import Config
from findout.result import PipelineResult
from findout.stages.generate import generate_answer
from findout.stages.extract import extract_claims
from findout.stages.predict import predict
from findout.stages.search import search_claim_set
from findout.stages.rewrite import rewrite

logger = logging.getLogger(__name__)


class SelfVerifyPipeline:
    """Base pipeline: 5 deterministic passes, single model."""

    def __init__(self, config: Config):
        self.config = config
        self.client = LLMClient(
            model=config.llm.model,
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            max_tokens=config.llm.max_tokens,
            timeout=config.llm.timeout_seconds,
        )
        self.search_client = SearchClient(
            provider=config.search.provider,
            api_key=config.search.api_key,
        )
        self.gate = Gate(
            config=config.pipeline.gate,
            llm_config=config.llm,
        )

    def run(
        self,
        query: str,
        pipeline: str = "base",
        skip_gate: bool = False,
    ) -> PipelineResult:
        """Run the pipeline on a query.

        Args:
            query: The user's question or idea.
            pipeline: Which variant — "base", "consistency", or "hybrid".
            skip_gate: If True, skip the gate classifier and always run pipeline.

        Returns:
            PipelineResult with the verified answer and metadata.
        """
        # Step 0: Gate
        if self.config.pipeline.gate_enabled and not skip_gate:
            decision = self.gate.classify(query)
            if decision == "casual":
                # Answer directly, no pipeline
                answer = generate_answer(
                    self.client, query, temperature=self.config.pipeline.temp_generate
                )
                return PipelineResult(
                    query=query,
                    answer=answer,
                    pipeline_variant=pipeline,
                    skipped_pipeline=True,
                    gate_decision="casual",
                )

        # Route to the right pipeline variant
        if pipeline == "consistency":
            return self._run_consistency(query)
        elif pipeline == "hybrid":
            return self._run_hybrid(query)
        else:
            return self._run_base(query)

    def _run_base(self, query: str) -> PipelineResult:
        """Base pipeline: generate → extract → predict → search → rewrite."""
        logger.info(f"Running base pipeline for: {query[:80]}...")

        # Pass 1: Cold answer
        raw = generate_answer(
            self.client, query, temperature=self.config.pipeline.temp_generate
        )

        # Pass 2: Extract claims
        claims = extract_claims(
            self.client, raw, max_claims=self.config.pipeline.max_claims_per_answer
        )

        if not claims:
            # No claims to verify — just return the raw answer
            return PipelineResult(
                query=query,
                answer=raw,
                raw_answer=raw,
                pipeline_variant="base",
                claims=[],
                gate_decision="visionary",
            )

        # Pass 3: Predict evidence + surprises
        predictions = predict(self.client, claims)

        # Pass 4: 3-angle search
        search_results = search_claim_set(
            self.search_client,
            predictions,
            max_results_per_query=self.config.pipeline.max_search_results,
        )

        # Pass 5: Rewrite with citations
        verified = rewrite(self.client, query, raw, search_results)

        # Collect citations and stats
        citations = self._collect_citations(search_results)
        stats = self._compute_stats(search_results)

        return PipelineResult(
            query=query,
            answer=verified,
            raw_answer=raw,
            pipeline_variant="base",
            claims=claims,
            search_results=search_results,
            citations=citations,
            gate_decision="visionary",
            **stats._asdict(),
        )

    def _run_consistency(self, query: str) -> PipelineResult:
        """Multi-sample pipeline: N answers → consensus → search conflicts.

        The key advantage: a hallucination rarely appears in ALL N samples.
        Claims with high consensus pass through, conflicts get searched.
        """
        from findout.consistency import run_consistency_pipeline
        return run_consistency_pipeline(self, query)

    def _run_hybrid(self, query: str) -> PipelineResult:
        """Hybrid pipeline: 2 samples → short-circuit on agreement → else search.

        Designed for small local models (3B-14B) where instruction-following is shaky.
        """
        from findout.hybrid import run_hybrid_pipeline
        return run_hybrid_pipeline(self, query)

    def _collect_citations(self, results: list[ClaimSearchResults]) -> list[str]:
        """Collect all unique citation URLs from search results."""
        urls = set()
        for csr in results:
            for src in csr.supporting_sources + csr.contradicting_sources:
                if src.url:
                    urls.add(src.url)
        return sorted(urls)

    def _compute_stats(self, results: list[ClaimSearchResults]) -> "_Stats":
        from collections import namedtuple
        Stats = namedtuple("Stats", [
            "total_claims", "verified_claims",
            "contradicted_claims", "uncertain_claims",
        ])
        total = len(results)
        verified = sum(1 for r in results if r.supports_claim)
        contradicted = sum(1 for r in results if r.contradicts_claim)
        uncertain = sum(1 for r in results if r.uncertain)
        return Stats(total, verified, contradicted, uncertain)
