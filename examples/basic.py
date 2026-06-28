from findout import SelfVerifyPipeline, Config, LLMConfig


def main():
    # Supply endpoint settings explicitly.
    config = Config(
        llm=LLMConfig(
            model="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key="",
        )
    )

    pipe = SelfVerifyPipeline(config)

    result = pipe.run("What is PostgreSQL and why do people like it?")
    print(result.answer)
    print(f"\n[Pipeline: {result.pipeline_variant}]")
    print(f"[Verified: {result.verified_claims}/{result.total_claims} claims]")

    result = pipe.run("How does MVCC work in PostgreSQL?")
    print("\n" + "=" * 80 + "\n")
    print(result.answer)
    print(f"\n[Pipeline: {result.pipeline_variant}]")
    print(f"[Citations: {len(result.citations)}]")

    result = pipe.run(
        "What if databases could negotiate consistency levels in natural language?"
    )
    print("\n" + "=" * 80 + "\n")
    print(result.answer)
    print(f"\n[Pipeline: {result.pipeline_variant}]")
    print(f"[Gate: {result.gate_decision}]")


if __name__ == "__main__":
    main()
