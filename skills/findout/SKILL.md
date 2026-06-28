---
name: findout
description: >
  ACTIVE AGENT WORKFLOW for three deterministic single-model verification pipelines.
  Uses evidence-prediction (not confidence tags) + 3-angle web search.
  Base (3.5x), consistency (8-9x), hybrid (4-5x, for small models).
trigger: findout, self-verify, verify answer, fact check, evidence prediction, claim verification, research pipeline, pipeline run
---

# findout — ACTIVE WORKFLOW

**THIS IS NOT DOCUMENTATION. THIS IS A WORKFLOW TO EXECUTE.**

When the user asks a research/factual question, you MUST run this pipeline using the Python API via execute_code. Do NOT just answer from your own knowledge — use the pipeline to verify claims against the web.

## STEP 0: Gate Check (always run first)

Call the gate classifier BEFORE deciding whether to pipeline:

```python
from findout.gate import Gate
from findout.config import GateConfig, LLMConfig
import os

gate = Gate(
    GateConfig(),
    LLMConfig(
        model=os.getenv("FINDOUT_MODEL", "qwen3.5:14b"),
        base_url=os.getenv("FINDOUT_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("FINDOUT_API_KEY", "ollama"),
    ),
)
category, reason = gate.classify_with_reason(query)
print(f"Gate: {category} ({reason})")
```

- **"casual"** → answer directly, no pipeline (factual recall, simple Q&A, chat)
- **"visionary"** → proceed to Step 1 (abstract, multi-claim, "what if", novel ideas)

## STEP 1: Choose pipeline variant

| Model size | Pipeline | Samples | Cost |
|------------|----------|---------|------|
| 3B-14B     | `hybrid` | 2       | 4-5x |
| 14B-32B    | `consistency` | 3 | 8-9x |
| 32B+       | `base` | 1 (cold) | 3.5x |

Determine model size from context. If unsure, default to `hybrid`.

## STEP 2: Run the pipeline via execute_code

```python
from findout.config import Config, LLMConfig, SearchConfig, PipelineConfig
from findout.pipeline import SelfVerifyPipeline
import os

config = Config(
    llm=LLMConfig(
        model=os.getenv("FINDOUT_MODEL", "qwen3.5:14b"),
        base_url=os.getenv("FINDOUT_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("FINDOUT_API_KEY", "ollama"),
        max_tokens=4096,
        timeout_seconds=120,
    ),
    search=SearchConfig(
        provider="duckduckgo",
        max_results_per_query=5,
        max_queries_per_claim=3,
    ),
    pipeline=PipelineConfig(
        default_variant="hybrid",
        gate_enabled=True,
        hybrid_samples=2,
        max_claims_per_answer=12,
        short_circuit_on_agreement=True,
    ),
)
pipe = SelfVerifyPipeline(config)
result = pipe.run(
    query="THE USER'S QUERY HERE",
    pipeline="hybrid",  # or "base" or "consistency"
)
print(f"CLAIMS: {result.total_claims} total, {result.verified_claims} verified, {result.uncertain_claims} uncertain, {result.contradicted_claims} contradicted")
print(f"SEARCHES: {result.total_searches}")
print()
print(result.answer)
```

## STEP 3: Present results

Include in your response:
- The verified answer (from `result.answer`)
- A brief verdict: "X claims verified, Y uncertain, Z contradicted"
- If search returned results, cite sources
- If the pipeline failed (LLM unreachable, search down), fall back to a normal answer and explain what went wrong

## Error Resilience

**If LLM endpoint is unreachable:**
- The pipeline raises `ConnectionError` — catch it
- Fall back to answering normally from your own knowledge
- Tell the user: "Verification pipeline unavailable (model server not running at {url}). Answered from direct knowledge."

**If search fails:**
- The pipeline catches search failures and returns claims as "uncertain"
- The final answer still gets generated, just with `[not verified]` markers

**If everything fails:**
```python
try:
    result = pipe.run(query, pipeline="hybrid")
except Exception as e:
    # Fall through to normal answering
    print(f"PIPELINE FAILED: {e}")
    print("FALLING BACK TO DIRECT ANSWER")
```

## Three Pipelines (Reference)

### Pipeline 1: `base` (5 passes)
1. Generate cold answer (temp=0)
2. Extract atomic claims
3. Predict evidence + surprises per claim
4. 3-angle web search per claim (evidence-biased, neutral, antithesis)
5. Rewrite with citations + uncertainty markers

### Pipeline 2: `consistency` (multi-sample)
1. Generate N=3 at temp=0.7
2. Extract claims from all, deduplicate by meaning
3. Tag by consensus: ✅ all 3 agree, ⚠️ 2/3 agree, ❌ all disagree
4. Search only ⚠️+❌ claims
5. Majority answer with conflict notes

### Pipeline 3: `hybrid` (combined, for small models)
1. Generate N=2 at temp=0.7
2. If both agree on ALL claims → short-circuit (return directly, no search)
3. If they disagree → extract conflicting claims only
4. Search only conflicting claims
5. Rewrite with conflicts marked explicitly

## Config

Set via env vars:

```bash
FINDOUT_MODEL=qwen3.5:14b
FINDOUT_BASE_URL=http://localhost:11434/v1
FINDOUT_API_KEY=ollama
FINDOUT_SEARCH_PROVIDER=duckduckgo
FINDOUT_PIPELINE=hybrid
FINDOUT_GATE_ENABLED=true
```
