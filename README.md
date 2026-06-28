# findout

**Deterministic, single-model verification pipelines for LLM outputs.**
Three-tier architecture: base → multi-sample consistency → hybrid for small models.

No multi-model fan-out. No training. No fine-tuning. One model, multiple deterministic passes, grounded in real web search.

[![GitHub](https://img.shields.io/badge/GitHub-findout-181717?logo=github)](https://github.com/akashmukherjee333/findout)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

---

## The Problem

LLMs hallucinate. They also *sound confident while doing it*. Multi-model fan-out (asking N models the same question) is expensive and inconsistent. Asking the same model to "check itself" fails because models can't reliably distinguish "I know this" from "I'm making this up."

## The Solution

Replace **confidence judgment** (which models are bad at) with **evidence prediction** (which models are good at):

1. Generate an answer
2. Decompose it into atomic claims
3. For each claim, predict what evidence *would* exist if true — and what would be surprising
4. Search the real web for those predictions
5. Rewrite with citations or "not verified" markers

The web is the ground truth. The model just suggests *where to look*.

---

## Three Pipelines

### Pipeline 1: `base` (Self-Verify)
**Best for:** 32B+ models, API-served models

| Pass | What it does | Cost |
|------|-------------|------|
| 1 | Generate cold answer (temp=0) | ~2,100 tokens |
| 2 | Extract atomic claims | ~900 |
| 3 | Predict evidence + surprises per claim | ~800 |
| 4 | 3-angle web search per claim | ~100 (tool calls) |
| 5 | Rewrite with citations | ~3,500 |
| **Total** | | **~3.5x baseline** |

### Pipeline 2: `consistency` (Multi-Sample)
**Best for:** 14B-32B models, local models, self-reinforcement risk

Generates N=3 answers at temp=0.7. Claims with consensus ≥2/3 pass through; conflicting claims get searched. Catches the "confidently wrong" case because the same hallucination rarely appears in all 3 samples.

**Cost:** ~8-9x baseline | **Reliability:** Highest of all three variants.

### Pipeline 3: `hybrid` (Combined, Low-Param)
**Best for:** 3B-14B local models

Generates N=2 answers. If they agree — short-circuit, no search. If they disagree — search only the conflicting claims. Designed for models with shaky instruction-following.

**Cost:** ~4-5x baseline | **Reliability:** Better than base for <14B models.

---

## Quick Start

```bash
pip install findout

# Set your LLM endpoint (any OpenAI-compatible provider)
export FINDOUT_MODEL=gpt-4o
export FINDOUT_BASE_URL=https://api.openai.com/v1
export FINDOUT_API_KEY=sk-...

# Run the pipeline
findout run "What would an OS look like if the frontend was entirely AI-generated?"

# Alternatively, pass params directly (works with any provider):
findout run "Explain PostgreSQL MVCC" \
  --model gpt-4o \
  --base-url https://api.openai.com/v1 \
  --api-key sk-... \
  --pipeline hybrid

# Gate-only mode (just classify, don't execute)
findout gate "squirrels are known for storing nuts"
# → casual
findout gate "I want a system where AI generates the frontend at runtime"
# → visionary
```

### Python API

```python
from findout import SelfVerifyPipeline
import os

pipeline = SelfVerifyPipeline(
    model=os.environ["FINDOUT_MODEL"],
    base_url=os.environ["FINDOUT_BASE_URL"],
)

result = pipeline.run(
    query="Design a distributed task scheduler with AI-driven prioritization.",
    pipeline="hybrid",  # "base" | "consistency" | "hybrid"
)

print(result.answer)
print(result.citations)
print(result.unverified_claims)
```

---

## Hermes Agent Integration

This project was built for [Hermes Agent](https://github.com/NousResearch/hermes-agent). It ships as a native Hermes skill so any Hermes session can use it.

### Install from GitHub

```bash
# Clone the repo
git clone https://github.com/akashmukherjee333/findout.git ~/projects/findout

# Install the Python package
cd ~/projects/findout
pip install -e .

# Install the Hermes skill
cp -r skills/findout ~/.hermes/skills/research/

# Or symlink for auto-updates:
ln -s ~/projects/findout/skills/findout ~/.hermes/skills/research/findout
```

### One-liner install

```bash
pip install findout && \
ln -s "$(python3 -c 'import findout; import os; print(os.path.dirname(findout.__file__))')/../skills/findout" \
  ~/.hermes/skills/research/findout
```

### How it works in Hermes

The skill is an **active agent workflow**, not passive documentation. When a user asks a research question, the Hermes agent:

1. **Gates** the query — is this casual or visionary?
2. **Runs the pipeline** via `execute_code` — generates, extracts, predicts, searches, rewrites
3. **Returns a verified answer** with citations + claim-by-claim verdict
4. **Falls back gracefully** if the LLM endpoint or web search is unavailable

Set environment variables to configure:

```bash
# Required — must point to any OpenAI-compatible endpoint
export FINDOUT_MODEL="gpt-4o"
export FINDOUT_BASE_URL="https://api.openai.com/v1"
export FINDOUT_API_KEY="sk-..."

# Optional
export FINDOUT_SEARCH_PROVIDER="duckduckgo"
export FINDOUT_PIPELINE="hybrid"
export FINDOUT_GATE_ENABLED="true"
```

Or configure in `~/.hermes/config.yaml`:

```yaml
env:
  FINDOUT_MODEL: gpt-4o
  FINDOUT_BASE_URL: https://api.openai.com/v1
  FINDOUT_PIPELINE: hybrid
```

Works with any OpenAI-compatible provider — OpenAI, vLLM, Ollama, Groq, Together, Anthropic (via proxy), etc.

---

## The Evidence Prediction Core

The key innovation: instead of asking the model "are you sure?" (which fails), we ask:

> **"If this claim is true, what specific articles, studies, or data would exist?"**

And:

> **"What would disprove or surprise you about this claim?"**

These are *generative* questions, not *evaluative* ones. The model can answer them naturally — it's extending the pattern, not judging itself.

Each claim gets **three search angles**:

| Angle | Query | Purpose |
|-------|-------|---------|
| Evidence-biased | Predicted evidence keywords | Catches if true |
| Neutral | Claim stated as a question | Unbiased verification |
| Antithesis | Surprise prediction keywords | Catches if wrong |

If all three return supporting sources → **verified**.
If neutral + antithesis contradict the claim → **refuted**.
If nothing returns → **speculative** (marked as unverified).

---

## When It Works / When It Doesn't

| Triggers pipeline | Skips pipeline |
|------------------|----------------|
| Abstract system ideas ("what if") | Factual recall ("what is X") |
| Multi-claim questions | Simple how-to |
| Novel/off-domain topics | Code (use execution instead) |
| Mixed known+speculative queries | Chat/meta conversation |
| High-stakes factual answers | |

---

## Architecture

```
                    ┌──────────────┐
                    │    Input     │
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │    Gate      │  ← casual vs visionary (50 tokens)
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │   Pipeline   │  ← base / consistency / hybrid
                    │  Orchestrator│
                    └──────┬───────┘
                           ▼
              ┌─────────────────────┐
              │  Stage: Generate    │  ← temp=0 (or 0.7 for multi-sample)
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │  Stage: Extract     │  ← atomic claims
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │  Stage: Predict     │  ← evidence + surprise per claim
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │  Stage: Search      │  ← 3-angle web search per claim
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │  Stage: Rewrite     │  ← verified + speculative markers
              └──────────┬──────────┘
                         ▼
                    ┌──────────────┐
                    │   Output     │
                    └──────────────┘
```

---

## Configuration

All configuration comes from environment variables — no hardcoded defaults.
`FINDOUT_MODEL` and `FINDOUT_BASE_URL` are **required**.

```python
from findout.config import Config

# Load from environment (raises ValueError if FINDOUT_MODEL/BASE_URL unset)
config = Config.from_env()

# Or construct explicitly:
from findout.config import Config, LLMConfig, SearchConfig, PipelineConfig

config = Config(
    llm=LLMConfig(
        model="gpt-4o",
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
    ),
    search=SearchConfig(
        provider="duckduckgo",  # or "serpapi", "custom"
        max_results_per_query=5,
    ),
    pipeline=PipelineConfig(
        default_variant="hybrid",
        consistency_samples=3,
        max_claims_per_answer=12,
        temp_generate=0.0,
        temp_consistency=0.7,
        gate_enabled=True,
    ),
)
```

### Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FINDOUT_MODEL` | **Yes** | — | Model name (e.g. `gpt-4o`, `claude-sonnet-4`) |
| `FINDOUT_BASE_URL` | **Yes** | — | API endpoint (e.g. `https://api.openai.com/v1`) |
| `FINDOUT_API_KEY` | No | `""` | API key |
| `FINDOUT_MAX_TOKENS` | No | `4096` | Max generation tokens |
| `FINDOUT_TIMEOUT` | No | `120` | Request timeout (s) |
| `FINDOUT_SEARCH_PROVIDER` | No | `duckduckgo` | Search backend |
| `FINDOUT_SEARCH_RESULTS` | No | `5` | Results per query |
| `FINDOUT_PIPELINE` | No | `hybrid` | Default pipeline variant |
| `FINDOUT_GATE_ENABLED` | No | `true` | Enable gate classifier |
| `FINDOUT_SHORT_CIRCUIT` | No | `true` | Skip search on full agreement |

---

## Development

```bash
git clone https://github.com/akashmukherjee333/findout.git
cd findout
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest -v

# Lint
ruff check src/
```

### Project structure

```
findout/
├── pyproject.toml          # Build config + deps
├── LICENSE                 # MIT
├── README.md               # This file
├── .gitignore
├── skills/                 # Hermes skill bundle
│   └── findout/
│       └── SKILL.md
├── src/findout/
│   ├── __init__.py
│   ├── config.py           # Dataclasses (LLM, Search, Pipeline)
│   ├── gate.py             # 50-token casual vs visionary classifier
│   ├── llm.py              # OpenAI-compatible client (sync + async + batch)
│   ├── search_client.py    # DuckDuckGo search with 3-angle results
│   ├── result.py           # PipelineResult dataclass
│   ├── pipeline.py         # Orchestrator + all 3 variants
│   ├── consistency.py      # N-sample consensus pipeline
│   ├── hybrid.py           # 2-sample short-circuit pipeline
│   ├── cli.py              # Typer CLI
│   └── stages/
│       ├── __init__.py
│       ├── generate.py
│       ├── extract.py
│       ├── predict.py
│       ├── search.py
│       └── rewrite.py
├── tests/
│   ├── __init__.py
│   └── test_all.py
└── examples/
    ├── basic.py
    └── with_config.py
```

---

## Related Work

| Paper | How this differs |
|-------|-----------------|
| **Self-RAG** (Asai et al., 2023) | Requires training special reflection tokens. This is pure prompting — works with any model. |
| **VeriFact-CoT** (2025) | Focused on step-by-step reasoning chains. This handles open-ended factual answers. |
| **VeriFY** (2026) | Training-time framework. This is zero-training, drop-in pipeline. |
| **Self-Verified Distillation** (2026) | Uses self-verification to filter training data. This is for runtime inference. |

---

## License

MIT
