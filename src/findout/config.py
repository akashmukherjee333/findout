"""Configuration dataclasses for findout."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM endpoint configuration.

    Set model and base_url explicitly, or use Config.from_env().
    Both are required — there are no built-in defaults.
    """

    model: str = ""
    base_url: str = ""
    api_key: str = ""
    max_tokens: int = 4096
    timeout_seconds: int = 120


@dataclass
class SearchConfig:
    """Search provider configuration."""

    provider: str = "duckduckgo"  # "duckduckgo" | "serpapi" | "custom"
    api_key: Optional[str] = None
    max_results_per_query: int = 5
    max_queries_per_claim: int = 3  # evidence, neutral, antithesis


@dataclass
class GateConfig:
    """Gate classifier configuration."""

    enabled: bool = True
    model: Optional[str] = None  # If None, uses main LLM config
    casual_threshold: float = 0.5
    max_input_tokens: int = 100


@dataclass
class PipelineConfig:
    """Pipeline variant configuration."""

    default_variant: str = "hybrid"  # "base" | "consistency" | "hybrid"

    # Generation
    temp_generate: float = 0.0
    temp_consistency: float = 0.7
    temp_hybrid: float = 0.7

    # Multi-sample
    consistency_samples: int = 3
    hybrid_samples: int = 2

    # Limits
    max_claims_per_answer: int = 12
    max_search_results: int = 5
    short_circuit_on_agreement: bool = True  # hybrid mode

    # Gate
    gate_enabled: bool = True
    gate: GateConfig = field(default_factory=GateConfig)


@dataclass
class Config:
    """Top-level configuration."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Load config from environment variables.

        Raises:
            ValueError: If FINDOUT_MODEL or FINDOUT_BASE_URL are not set.
        """
        import os

        model = os.getenv("FINDOUT_MODEL")
        base_url = os.getenv("FINDOUT_BASE_URL")

        if not model or not base_url:
            raise ValueError(
                "FINDOUT_MODEL and FINDOUT_BASE_URL must be set. "
                "Example: FINDOUT_MODEL=gpt-4o FINDOUT_BASE_URL=https://api.openai.com/v1"
            )

        return cls(
            llm=LLMConfig(
                model=model,
                base_url=base_url,
                api_key=os.getenv("FINDOUT_API_KEY", ""),
                max_tokens=int(os.getenv("FINDOUT_MAX_TOKENS", "4096")),
                timeout_seconds=int(os.getenv("FINDOUT_TIMEOUT", "120")),
            ),
            search=SearchConfig(
                provider=os.getenv("FINDOUT_SEARCH_PROVIDER", "duckduckgo"),
                api_key=os.getenv("FINDOUT_SEARCH_API_KEY"),
                max_results_per_query=int(
                    os.getenv("FINDOUT_SEARCH_RESULTS", "5")
                ),
            ),
            pipeline=PipelineConfig(
                default_variant=os.getenv(
                    "FINDOUT_PIPELINE", "hybrid"
                ),
                gate_enabled=os.getenv(
                    "FINDOUT_GATE_ENABLED", "true"
                ).lower()
                in ("true", "1", "yes"),
                short_circuit_on_agreement=os.getenv(
                    "FINDOUT_SHORT_CIRCUIT", "true"
                ).lower()
                in ("true", "1", "yes"),
            ),
        )
