"""Basic usage example for self-verify-pipelines."""

from self_verify.config import Config
from self_verify.pipeline import SelfVerifyPipeline


def main():
    # Load config from environment (or use defaults)
    config = Config.from_env()

    # Override if needed
    config.llm.model = "qwen3.5:14b"
    config.llm.base_url = "http://localhost:11434/v1"

    # Create the pipeline
    pipe = SelfVerifyPipeline(config)

    # --- Example 1: Casual question (gate skips pipeline) ---
    result = pipe.run("What are squirrels known for?")
    print(f"[Gate: {result.gate_decision}]")
    if result.skipped_pipeline:
        print("(No verification needed — casual question)")
    print(result.answer)
    print()

    # --- Example 2: Visionary question (runs base pipeline) ---
    result = pipe.run(
        "I'm thinking about a system where the frontend is entirely "
        "AI-generated at runtime based on what the user types into a search bar.",
        pipeline="base",
        skip_gate=True,  # Force pipeline for demo
    )
    print(f"[Pipeline: {result.pipeline_variant}]")
    print(f"Claims: {result.total_claims} total, "
          f"{result.verified_claims} verified, "
          f"{result.uncertain_claims} uncertain")
    print(result.answer)
    print()

    # --- Example 3: Consistency pipeline for high-stakes ---
    result = pipe.run(
        "Explain how PostgreSQL's MVCC implementation differs from MySQL's.",
        pipeline="consistency",
        skip_gate=True,
    )
    print(f"[Pipeline: {result.pipeline_variant}]")
    print(f"Claims: {result.total_claims}")
    print(result.answer)
    print()

    # --- Example 4: Hybrid mode for small local models ---
    result = pipe.run(
        "Design a distributed task scheduler with AI-driven prioritization.",
        pipeline="hybrid",
        skip_gate=True,
    )
    print(f"[Pipeline: {result.pipeline_variant}]")
    print(f"Claims: {result.total_claims}")
    print(result.answer)


if __name__ == "__main__":
    main()
