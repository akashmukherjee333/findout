"""Pipeline result types."""

from dataclasses import dataclass, field
from typing import Optional
from findout.search_client import ClaimSearchResults


@dataclass
class PipelineResult:
    """Result from running any pipeline variant."""

    query: str
    answer: str
    pipeline_variant: str  # "base" | "consistency" | "hybrid"

    # Raw intermediate data (for debugging / transparency)
    raw_answer: str = ""
    claims: list[str] = field(default_factory=list)
    search_results: list[ClaimSearchResults] = field(default_factory=list)

    # Summary
    total_claims: int = 0
    verified_claims: int = 0
    contradicted_claims: int = 0
    uncertain_claims: int = 0

    # Citations
    citations: list[str] = field(default_factory=list)

    # For the gate
    skipped_pipeline: bool = False
    gate_decision: Optional[str] = None

    @property
    def unverified_claims(self) -> list[str]:
        """Claims that couldn't be verified."""
        return [
            r.claim_text
            for r in self.search_results
            if r.uncertain
        ]
