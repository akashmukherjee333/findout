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

## Pipeline Variant Tradeoffs

| Variant | Design goal | When the extra cost is worth it |
|---------|------------|--------------------------------|
| `base` (3.5x) | Structural verification | Reliable models (32B+) on simple factual claims. One cold pass is enough if the model is good. |
| `consistency` (8-9x) | Anti-confirmation-bias | Models prone to self-reinforcement (14-32B). Three samples ensure the same hallucination is unlikely in all — the consensus signal is strong. |
| `hybrid` (4-5x) | Shaky-model rescue | Small models (3-14B) with poor instruction following. Short-circuit on agreement saves tokens when the model is on solid ground. |

## The Fuzzy Explainer Protocol

For abstract/"what if" queries where the user is thinking through 3D ideas in a 1D medium (text):

1. **The agent carries the compute burden** — no clarifying questions from the agent to the user, because typing is the bottleneck
2. **Restate for recognition**, not confirmation — say "I hear X, does that match?" not "tell me more about Y"
3. **One-word corrections** — let the user correct with a single word ("simpler", "faster", "less") instead of requiring full re-explanation
4. **No multi-model fan-out** — the user explicitly rejects asking multiple models; single-model deterministic passes only

This protocol shaped the `hybrid` variant's design (short-circuit on agreement = zero friction when the model correctly understood).

## Empirical Cost Data

Measured against qwen3.5:14b via Ollama (DuckDuckGo search):

| Pipeline | Tokens consumed | Wall-clock (3 claims) | Search calls |
|----------|----------------|----------------------|--------------|
| Base | ~7,500 | ~25s | 3-9 |
| Consistency | ~18,000 | ~60s | 0-9 |
| Hybrid | ~9,000 | ~30s | 0-6 |

Search is the bottleneck — each DuckDuckGo call takes 2-5s. Short-circuit variants (hybrid on agreement, consistency on ≥2/3 consensus) save the most time by skipping search entirely.
