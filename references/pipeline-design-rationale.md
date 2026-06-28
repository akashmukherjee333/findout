# Pipeline Design Rationale

## The Core Insight: Evidence Prediction Over Confidence Tags

**The problem with "are you sure?":** Asking an LLM to self-evaluate its confidence is asking it to meta-judge its own knowledge. Models are demonstrably bad at this — they can't distinguish fluent confabulation from genuine knowledge. Confidence tags from the same model that generated the answer are circular.

**The fix — evidence prediction:** Instead of asking "are you sure?", ask generative questions the model IS good at:
- "If this claim is true, what specific articles, studies, or data would exist?"
- "What would disprove or surprise you about this claim?"

These are *extension* tasks, not *evaluation* tasks. The model naturally generates plausible search queries for both sides.

## Why Three Angles Per Claim

Single-search-then-judge misses the model's blind spots. Three angles:

| Angle | Query | Catches |
|-------|-------|---------|
| Evidence-biased | Predicted evidence keywords | Confirms true claims |
| Neutral | Claim as a question | Unbiased facts |
| Antithesis | Surprise prediction keywords | Catches hallucinations |

If the evidence-biased angle finds support but the antithesis and neutral don't — likely hallucination (the model's prediction of evidence was itself confabulated).

## Why the package now uses one pipeline

The old multi-sample branches (`consistency`, `hybrid`) added cost, config surface,
and maintenance burden. They also conflicted with the user's preference: no extra
sampling branch, no separate env-var driven execution path, no side-channel model
selection when Hermes already has a live model loaded.

So the package is now intentionally narrower:
- one deterministic pipeline (`base`)
- one model
- one search strategy
- explicit runtime config when used standalone
- no required `FINDOUT_*` env-var contract for Hermes-side usage

Less surface area. Fewer lies. Easier to keep correct.

## The Fuzzy Explainer Protocol

For abstract/"what if" queries where the user is thinking through 3D ideas in a 1D medium (text):

1. **The agent carries the compute burden** — no clarifying questions from the agent to the user, because typing is the bottleneck
2. **Restate for recognition**, not confirmation — say "I hear X, does that match?" not "tell me more about Y"
3. **One-word corrections** — let the user correct with a single word ("simpler", "faster", "less") instead of requiring full re-explanation
4. **No multi-model fan-out** — the user explicitly rejects asking multiple models; single-model deterministic passes only

## Empirical cost intuition

Measured historically against qwen3.5:14b via Ollama (DuckDuckGo search), the
single deterministic path was the stable baseline. The removed branches were more
expensive and harder to justify operationally than they were useful.
