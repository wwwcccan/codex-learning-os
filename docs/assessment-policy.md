# Assessment policy

The Tutor can propose a score, but a persisted score must identify its dimension, score, assistance level, timestamp, and optional confidence/note. The CLI validates bounds and records the assessment history.

Before important tests, ask for confidence from 0–100. Interpret the pair explicitly:

```text
high confidence + wrong  -> dangerous misconception; create a high-severity mistake
low confidence + correct -> knowledge may be present but calibration is weak
```

Do not give 4/5 merely because the learner recognized a solution. Use the rubric's observable A0 behavior. Do not let the LLM update counters, review dates, or status directly.

Natural-language scoring is intentionally not automated in the MVP. A future scorer must output a structured assessment for human review before persistence.
