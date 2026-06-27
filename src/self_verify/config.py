"""Configuration dataclasses for self-verify-pipelines."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM endpoint configuration."""

    model: str = "qwen3.5:14b"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
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
        """Load config from environment variables."""
        import os

        return cls(
            llm=LLMConfig(
                model=os.getenv("SELF_VERIFY_MODEL", "qwen3.5:14b"),
                base_url=os.getenv(
                    "SELF_VERIFY_BASE_URL", "http://localhost:11434/v1"
                ),
                api_key=os.getenv("SELF_VERIFY_API_KEY", "ollama"),
                max_tokens=int(os.getenv("SELF_VERIFY_MAX_TOKENS", "4096")),
                timeout_seconds=int(os.getenv("SELF_VERIFY_TIMEOUT", "120")),
            ),
            search=SearchConfig(
                provider=os.getenv("SELF_VERIFY_SEARCH_PROVIDER", "duckduckgo"),
                api_key=os.getenv("SELF_VERIFY_SEARCH_API_KEY"),
                max_results_per_query=int(
                    os.getenv("SELF_VERIFY_SEARCH_RESULTS", "5")
                ),
            ),
            pipeline=PipelineConfig(
                default_variant=os.getenv(
                    "SELF_VERIFY_PIPELINE", "hybrid"
                ),
                gate_enabled=os.getenv(
                    "SELF_VERIFY_GATE_ENABLED", "true"
                ).lower()
                in ("true", "1", "yes"),
                short_circuit_on_agreement=os.getenv(
                    "SELF_VERIFY_SHORT_CIRCUIT", "true"
                ).lower()
                in ("true", "1", "yes"),
            ),
        )
