"""Advanced configuration example."""

from findout.config import (
    Config, LLMConfig, SearchConfig, PipelineConfig, GateConfig
)
from findout.pipeline import SelfVerifyPipeline


def main():
    config = Config(
        llm=LLMConfig(
            model="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key="sk-...",  # Set via env var in production
            max_tokens=8192,
            timeout_seconds=180,
        ),
        search=SearchConfig(
            provider="duckduckgo",
            max_results_per_query=7,
        ),
        pipeline=PipelineConfig(
            default_variant="consistency",
            consistency_samples=5,  # More samples = higher confidence
            max_claims_per_answer=20,
            temp_generate=0.0,
            temp_consistency=0.8,
            gate=GateConfig(
                enabled=True,
                casual_threshold=0.7,
            ),
        ),
    )

    pipe = SelfVerifyPipeline(config)

    # Use the gate to decide
    result = pipe.run("What is the current state of AI alignment research?")

    if not result.skipped_pipeline:
        print(f"Pipeline: {result.pipeline_variant}")
        print(f"Claims analyzed: {result.total_claims}")
        print(f"Verified: {result.verified_claims}")
        print(f"Contradicted: {result.contradicted_claims}")
        print(f"Uncertain: {result.uncertain_claims}")
        print(f"Sources: {len(result.citations)}")

    print(result.answer)


if __name__ == "__main__":
    main()
