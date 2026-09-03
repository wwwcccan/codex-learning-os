# Data model

All records use YAML frontmatter between `---` delimiters and `schema_version: 1`. IDs are stable, filename-safe, and unique within a record directory.

## Concept

```yaml
type: concept
id: strong-convexity
name: Strong Convexity
domain: convex-optimization
status: learning
recall: 0
explanation: 0
derivation: 0
transfer: 0
debug: 0
assistance_required: A5
a0_successes: 0
last_review: null
next_review: null
weakness: [recall, explanation, derivation, transfer, debug]
prerequisites: [convex-functions, gradient]
a0_evidence: []
assessments: []
```

`a0_successes` is always recomputed from `a0_evidence` entries where `correct: true` and `assistance: A0`. The five scores are the current projection; `assessments` is the auditable sequence that produced it. `weakness` is an actionable/prioritized subset chosen by the learner or recomputed by deterministic updates from low scores and latest failed A0 dimensions; it need not list every low dimension. `assistance_required` is the lowest assistance level observed on a correct evidence event, defaulting to A5 when there is no successful evidence.

## Paper

Required state includes `title`, `status`, `research_question`, `core_claim`, `current_reading_status`, `blockers`, `p0_dependencies` through `p3_dependencies`, `core_formulas`, `benchmarks`, `classical_methods`, and `related_sota`.

The MVP also stores structured `formula_map`, `evidence_notes`, and `experiment_predictions` entries. Formula entries carry an intentional target depth (`L1`–`L5`); evidence entries carry an explicit evidence kind; prediction entries separate pre-experiment expectations from post-experiment observations.

Each blocker has:

```yaml
- id: blocker-20260903-a1b2c3
  type: prerequisite_concept
  label: Schur complement
  description: The block inverse step is not yet reconstructible.
  priority: P0
  status: open
  concept_id: schur-complement
  foundation_track: Probability & Estimation
  created: "2026-09-03T10:00:00+08:00"
```

Valid types are `notation`, `prerequisite_concept`, `derivation`, `classical_method`, `benchmark`, and `recent_related_work`. The CLI accepts `prerequisite` as a friendly alias.

## Mistake

The frontmatter stores `concept_id`, `error_type`, `severity`, `status`, `assistance`, `confidence`, `created`, and `retest`. The body keeps:

```text
Problem
My Answer
What Was Wrong
Why I Made This Mistake
Correct Mental Model
Retest Question
```

## Session

`mode` is `learning` or `research`; a session can link to one Concept or one Paper, never both. `attempts`, `hints`, and `a0_tests` are append-only process records. `finished_at` is required when `status: completed`.

## Evidence labels

Research notes use `FACT`, `INFERENCE`, `HYPOTHESIS`, `SPECULATION`, or `UNKNOWN`. A plausible explanation without direct paper/experiment support must never be serialized as `FACT`.
