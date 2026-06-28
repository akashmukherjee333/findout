"""Configuration dataclasses for findout."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM endpoint configuration.

    Model and base_url should be supplied explicitly by the caller.
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
    """Single deterministic pipeline configuration."""

    default_variant: str = "base"

    # Generation
    temp_generate: float = 0.0

    # Limits
    max_claims_per_answer: int = 12
    max_search_results: int = 5

    # Gate
    gate_enabled: bool = True
    gate: GateConfig = field(default_factory=GateConfig)


@dataclass
class Config:
    """Top-level configuration."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
