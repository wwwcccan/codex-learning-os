# Mastery rubric

Scores are explicit assessments, not an automatic language-model guess.

| Score | Observable performance |
| ---: | --- |
| 0 | Cannot start or identify the relevant object. |
| 1 | Recognizes or understands an answer after seeing it. |
| 2 | Can proceed only with substantial help. |
| 3 | Can complete with a small hint or can explain the standard case with gaps. |
| 4 | Completes a standard task independently at A0. |
| 5 | Completes a genuinely unfamiliar transfer task independently at A0 and can debug a tempting wrong path. |

## Dimensions

- **Recall:** retrieve definitions, assumptions, symbols, and key facts.
- **Explanation:** explain what/why in plain language and at multiple abstraction levels.
- **Derivation:** reconstruct omitted steps and identify required assumptions.
- **Transfer:** apply the idea to an unfamiliar but structurally related problem.
- **Debug:** find and repair a plausible misconception or invalid derivation.

## Gate

A Concept becomes `mastered` only if:

```text
recall >= 4
explanation >= 4
derivation >= 4
transfer >= 4
debug >= 3
AND at least 3 A0 successes on distinct calendar dates
AND at least 1 of those successes is a novel transfer problem
```

An A1–A5 success may show progress and reduce the observed assistance requirement, but it cannot increment `a0_successes` or satisfy the gate. Correctness under assistance is useful training data, not proof of independence.

## Delayed retrieval

The scheduler fallback proposes +1, +3, +7, +14, +30, and +60 days after successive A0 successes; an incorrect A0 attempt proposes +1 day. This is intentionally transparent and replaceable. A review date is a prompt to test, not evidence that mastery exists.
