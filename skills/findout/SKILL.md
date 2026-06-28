---
name: findout
description: >
  ACTIVE AGENT WORKFLOW for a deterministic single-model verification pipeline.
  Uses evidence-prediction (not confidence tags) + 3-angle web search.
trigger: findout, foundit, self-verify, verify answer, fact check, evidence prediction, claim verification, research pipeline, pipeline run
---

# findout — ACTIVE WORKFLOW

**⚠️ HARD RULE — READ THIS FIRST ⚠️**

**If the user's message includes a query (anything after the trigger word), you MUST:**
1. Extract that query from their message
2. Run the findout pipeline on it using `execute_code`
3. Return the pipeline output as your answer

**DO NOT:**
- Describe what this skill does instead of running it
- Ask "what claim would you like verified?" — the query is already in the message
- Explain old pipeline variants or legacy env-var setup
- Provide a summary of the skill's contents

The user's message IS the query. Execute immediately.

## Core rule

findout is now **one deterministic pipeline**. No multi-sample branch. No consistency/hybrid variant selection. No requirement for `FINDOUT_*` env vars inside Hermes-driven usage.

When this skill is used from Hermes, generation should ride the currently loaded model context. If the package is run standalone outside Hermes, the caller can still construct `Config` explicitly or pass `--model` / `--base-url` to the CLI.

## STEP 0: Gate Check

```python
from findout.gate import Gate
from findout.config import Config, LLMConfig

gate = Gate(
    Config().pipeline.gate,
    LLMConfig(model=model, base_url=base_url, api_key=api_key),
)
category, reason = gate.classify_with_reason(query)
print(f"Gate: {category} ({reason})")
```

- **"casual"** → answer directly, no pipeline
- **"visionary"** → proceed

## STEP 1: Run via execute_code

```python
from findout.config import Config, LLMConfig, SearchConfig, PipelineConfig
from findout.pipeline import SelfVerifyPipeline

config = Config(
    llm=LLMConfig(
        model=model,
        base_url=base_url,
        api_key=api_key,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
    ),
    search=SearchConfig(provider="duckduckgo", max_results_per_query=5, max_queries_per_claim=3),
    pipeline=PipelineConfig(default_variant="base", gate_enabled=True, max_claims_per_answer=12),
)
pipe = SelfVerifyPipeline(config)
result = pipe.run(query="QUERY", pipeline="base")
print(result.answer)
```

## STEP 2: Present results

Include verdict ("X verified, Y uncertain, Z contradicted") and citations. Catch connection/import failures honestly. If the package can't run, fall back to manual grounded research rather than fabricating pipeline output.

## Hermes Plugin — `/findout` and `/foundit` Slash Commands

A Hermes plugin at `plugins/hermes/` registers `/findout <query>` and
`/foundit <query>` as native slash commands in TUI, CLI, and gateway sessions.
`/foundit` is an alias for the same pipeline because the user invokes that name.

**Install:**
```bash
mkdir -p ~/.hermes/plugins/findout
cp -r plugins/hermes/* ~/.hermes/plugins/findout/
```

Then `/reset` the session or restart gateway. The plugin shells out to the
`findout` CLI. It no longer documents `FINDOUT_MODEL`, `FINDOUT_BASE_URL`, or
`FINDOUT_API_KEY` as required Hermes-side setup. Standalone CLI runs should pass
`--model` and `--base-url` explicitly.

**Uninstall:** `rm -rf ~/.hermes/plugins/findout && /reset`

## Known Issues

**Trigger collision with grounded-research:** Resolved — the grounded-research skill uses YAML list triggers (not comma-separated) and does not include `find` as a trigger. The `/findout` and `/foundit` slash commands (plugin) bypass NL matching entirely. Prefer the slash commands for deterministic invocation.
