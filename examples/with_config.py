from findout import SelfVerifyPipeline
from findout.config import Config, LLMConfig, SearchConfig, PipelineConfig


def main():
    config = Config(
        llm=LLMConfig(
            model="qwen3.5:14b",
            base_url="http://localhost:11434/v1",
            api_key="",
            max_tokens=16384,
            timeout_seconds=180,
        ),
        search=SearchConfig(
            provider="duckduckgo",
            max_results_per_query=5,
        ),
        pipeline=PipelineConfig(
            default_variant="base",
            max_claims_per_answer=12,
            temp_generate=0.0,
            gate_enabled=True,
        ),
    )

    pipe = SelfVerifyPipeline(config)

    queries = [
        "Design a distributed AI task scheduler that learns which agent to assign based on outcome history.",
        "What's the difference between PostgreSQL and MySQL?",
        "Could a database use LLMs to generate adaptive indexes in real-time?",
    ]

    for query in queries:
        print("=" * 80)
        print(f"Query: {query}\n")

        result = pipe.run(query)

        print(result.answer)
        print()
        print(f"Pipeline: {result.pipeline_variant}")
        print(f"Gate decision: {result.gate_decision}")
        print(
            f"Claims: {result.total_claims} total, {result.verified_claims} verified, {result.contradicted_claims} contradicted, {result.uncertain_claims} uncertain"
        )
        if result.citations:
            print(f"Citations: {len(result.citations)}")
            for url in result.citations[:3]:
                print(f"  - {url}")
        print()


if __name__ == "__main__":
    main()
