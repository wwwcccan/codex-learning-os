# Architecture

## Outcome

The MVP optimizes future independent performance. It is a local Markdown vault with a deterministic Python command line, not an answer-generation application.

## Repository structure

```text
Concepts/       current concept model, scores, assessments, A0 evidence
Papers/         paper claims, blockers, dependencies, evidence notes
Mistakes/       cognitive bugs and retest state
Sessions/       process logs for learning and research sessions
Foundation/     suggested or active systematic learning tracks
Sources/        optional source notes and stable references
Templates/      copyable Markdown templates
src/learning_os/ deterministic model, YAML frontmatter, repository, policies, CLI
docs/           contracts and rubrics
.agents/skills/ai-tutor/ Codex tutor behavior
tests/          policy and end-to-end tests
```

There is no `Mastery/` directory, JSON mastery cache, database, vector store, or graph database. A record is one Markdown file named by its stable ID. Frontmatter is the persisted state; Markdown body is the human-readable context.

## Domain boundaries

| Area | Owns | Does not own |
| --- | --- | --- |
| Concept | current five-dimensional projection, prerequisites, assessment history, A0 evidence | session narrative or paper explanation |
| Paper | blocker history, P0–P3 dependency buckets, claim/evidence notes | concept scores |
| Mistake | the learner's cognitive bug and retest | the canonical concept state |
| Session | attempts, hints, reflection, links to evidence | mastery decisions |
| Foundation | a systematic track suggested by repeated gaps | individual paper blockers |

Session `a0_tests` contains a compact context snapshot and the evidence ID. The authoritative A0 evidence used for mastery is embedded in the linked Concept file. This is an event log plus a deterministic current projection, not a second mastery database.

## Deterministic versus LLM responsibilities

The Python core owns:

- YAML parsing, schema validation, file paths, duplicate IDs, timestamps, and explicit cross-record link checks;
- counter updates (`a0_successes`), review dates, score bounds, and status transitions;
- blocker aggregation, repeated-gap detection, foundation candidates, and dashboard statistics;
- the scheduler interface and the transparent fixed-interval fallback.

The Tutor Skill/LLM owns:

- interpreting a learner's natural-language response;
- proposing a misconception, Feynman follow-up, blocker category, minimal prerequisite path, or critique prompt;
- deciding whether a response deserves a rubric score, while following the rubric and recording uncertainty;
- generating questions and counterexamples appropriate to the current weakness.

The LLM must ask the CLI to persist a decision; it must not invent counters or silently mark mastery.

## Technology choice

The prompt suggested Pydantic, Typer, and pytest. The MVP keeps the runtime core on `dataclasses`, `argparse`, and the standard library because this is a single-user local vault and the current environment has no package manager dependencies available. That reduces installation friction and keeps state transitions easy to inspect. The package exposes ordinary Python service boundaries, so Pydantic/Typer can be added as adapters later; pytest remains an optional development dependency while the checked-in tests also run with `unittest`.

## State transitions

```text
Concept: inbox -> learning -> review -> mastered
                         ^          |
                         |          v
                         +------ learning (if the gate is not satisfied)

Paper: planned -> reading -> blocked (P0 blocker) -> reading -> completed
Mistake: unresolved -> retesting -> resolved
Session: active -> completed | abandoned
```

`mastered` is only reachable when all five dimension thresholds, three distinct A0-success dates, and one novel transfer A0 success are present. An assisted correct response never increments the A0 success counter.

## CLI surface

```text
learning-os init
learning-os concept {create,show,update,validate,list}
learning-os paper {create,show,list,blocker(add,link,resolve),dependency,map,evidence,formula,prediction}
learning-os mistake {create,show,resolve,list,link}
learning-os session {start,show,list,attempt,hint,a0,finish}
learning-os a0 record
learning-os assessment record
learning-os review
learning-os dashboard
learning-os foundation {suggest,create}
learning-os validate
```

All commands accept `--vault PATH` either before or after the command. `--json` is available on read/report commands for scripts.

## Integrity and failure behavior

`learning-os validate` is the vault integrity boundary. It scans every record file, parses the versioned frontmatter, validates nested event IDs and types, and then resolves explicit links:

- Concept prerequisites and A0 evidence `session_id`;
- Paper blocker `concept_id`;
- Mistake `concept_id`;
- Session `concept_id`, `paper_id`, mistake IDs, and linked A0 evidence IDs;
- Foundation-track concept IDs.

It also detects a frontmatter ID that does not match its filename, duplicate IDs within a record directory, inconsistent mastery/A0 counters, malformed or truncated Markdown, and leftover `.tmp`, `.partial`, or `.part` files from an interrupted write. Validation reports every discovered error and returns non-zero; it does not delete, rewrite, or guess a repair. Service operations validate known link targets before creating a new explicit link. When a blocker is recorded before its prerequisite Concept exists, `paper blocker link` provides the explicit second step after the Concept is created.

## Milestones

- M1 foundation and versioned Markdown schemas.
- M2 Concept CRUD, validation, scores, and prerequisites.
- M3 Paper blockers, priorities, dependency map, and resolution.
- M4 Mistake lifecycle and concept link validation.
- M5 Session lifecycle, attempts, hints, and A0 context.
- M6 explicit five-dimension assessment records and rubric.
- M7 A0 evidence, deterministic mastery gate, and replaceable scheduler.
- M8 blocker history and foundation-track candidates.
- M9 dashboard and end-to-end scenarios.

## Main risks and mitigations

1. **False mastery from assisted work.** A0-only evidence drives the gate; assistance is stored on every event.
2. **Schema drift.** Every record has `schema_version: 1`; validators reject wrong types and unsupported state transitions.
3. **Duplicate truth.** No parallel mastery directory; Concept current fields are an explicit projection of its evidence/history.
4. **Rabbit holes.** P0–P3 dependency buckets and a “repair P0 first, then return to paper” workflow keep scope bounded.
5. **Overfitted scheduling.** `ReviewScheduler` is a small protocol; the MVP fallback is replaceable and documented, not presented as FSRS.
6. **YAML dependency friction.** PyYAML is optional; the core emits and reads a deliberately limited human-readable subset using the standard library.
