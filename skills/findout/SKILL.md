---
name: findout
description: >
  ACTIVE AGENT WORKFLOW for three deterministic single-model verification pipelines.
  Uses evidence-prediction (not confidence tags) + 3-angle web search.
  Base (3.5x), consistency (8-9x), hybrid (4-5x, for small models).
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
- Explain the pipeline variants or configuration
- Provide a summary of the skill's contents

The user's message IS the query. Execute immediately.

## STEP 0: Gate Check

```python
from findout.gate import Gate, GateConfig, LLMConfig
import os
gate = Gate(GateConfig(), LLMConfig(
    model=os.environ["FINDOUT_MODEL"],
    base_url=os.environ["FINDOUT_BASE_URL"],
    api_key=os.getenv("FINDOUT_API_KEY", ""),
))
category, reason = gate.classify_with_reason(query)
print(f"Gate: {category} ({reason})")
```

- **"casual"** → answer directly, no pipeline
- **"visionary"** → proceed

> FINDOUT_MODEL, FINDOUT_BASE_URL, and FINDOUT_API_KEY are read from the environment. Set them to ANY OpenAI-compatible provider. Examples: OpenAI, Anthropic (via proxy), vLLM, Ollama, Groq, Together, etc.

## STEP 1: Choose variant

| Model size | Pipeline | Samples | Cost |
|------------|----------|---------|------|
| 3B-14B     | `hybrid` | 2       | 4-5x |
| 14B-32B    | `consistency` | 3 | 8-9x |
| 32B+       | `base` | 1 (cold) | 3.5x |

## STEP 2: Run via execute_code

```python
from findout.config import Config, LLMConfig, SearchConfig, PipelineConfig
from findout.pipeline import SelfVerifyPipeline
import os
config = Config(
    llm=LLMConfig(model=os.environ["FINDOUT_MODEL"],
        base_url=os.environ["FINDOUT_BASE_URL"],
        api_key=os.getenv("FINDOUT_API_KEY",""), max_tokens=int(os.getenv("FINDOUT_MAX_TOKENS", "4096")), timeout_seconds=int(os.getenv("FINDOUT_TIMEOUT", "120"))),
    search=SearchConfig(provider="duckduckgo",max_results_per_query=5,max_queries_per_claim=3),
    pipeline=PipelineConfig(default_variant="hybrid",gate_enabled=True,hybrid_samples=2,max_claims_per_answer=12,short_circuit_on_agreement=True),
)
pipe = SelfVerifyPipeline(config)
result = pipe.run(query="QUERY", pipeline="hybrid")
print(result.answer)
```

## STEP 3: Present results

Include verdict ("X verified, Y uncertain, Z contradicted") and citations. Catch ConnectionError → answer from knowledge. Catch ImportError → run manual 5-pass verification.

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
`findout` CLI. It loads `~/.hermes/.env` before launching the subprocess, so
fresh Hermes sessions do not need the `FINDOUT_*` variables exported in the
shell environment. Required keys: `FINDOUT_MODEL`, `FINDOUT_BASE_URL`, and
`FINDOUT_API_KEY`. For reasoning models, set `FINDOUT_MAX_TOKENS=32768` and
`FINDOUT_TIMEOUT=300`.

**Uninstall:** `rm -rf ~/.hermes/plugins/findout && /reset`

## Known Issues

**Trigger collision with grounded-research:** Resolved — the grounded-research skill uses YAML list triggers (not comma-separated) and does not include `find` as a trigger. The `/findout` and `/foundit` slash commands (plugin) bypass NL matching entirely. Prefer the slash commands for deterministic invocation.
