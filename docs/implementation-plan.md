# MVP implementation plan and acceptance

## Shared contract first

1. Freeze record headers, enums, five dimensions, A0 evidence shape, and the mastery gate.
2. Freeze one-path-per-record repository semantics and body-preserving writes.
3. Keep all deterministic policy in Python; keep teaching judgment in the Tutor Skill.

## Parallelizable work after the contract

- **Data/persistence:** frontmatter codec, dataclasses, repository, schema validation.
- **Policy:** mastery gate, A0 counters, review scheduler interface, repeated blockers, dashboard aggregation.
- **Workflow services:** Concept, Paper, Mistake, Session, and Foundation operations.
- **CLI:** thin argparse commands that call services and support human/JSON output.
- **Documentation:** AGENTS, rubrics, hint/evidence policy, templates, Tutor Skill.
- **Tests:** unit tests for policies and parser plus CLI smoke/end-to-end tests.

Shared model names and enum values must be settled before those streams write integrations. This prevents each stream from inventing a different schema.

## Deliberately removed from the MVP

- React/Web UI, mobile, authentication, multi-user, SaaS, cloud sync;
- PostgreSQL, vector DB, embeddings, RAG, Neo4j, Elasticsearch;
- self-built FSRS or opaque automatic natural-language scoring;
- internet-wide crawling, flashcard floods, and a complex agent orchestrator.

The only extra beyond the minimum list is small structured support for paper evidence labels, formula target depth, and prediction-before-experiment records. They are single-list frontmatter fields and do not introduce a new service or storage layer.

## Acceptance matrix

| Scenario | Observable evidence |
| --- | --- |
| Strong Convexity learning | Concept file, prerequisites, Session attempts/hint, A0 event, deterministic `next_review`, weakness, and finish reflection. |
| EFIM/SPEB/Schur Complement paper | Paper blocker typed and prioritized, linked Concept dependency, `paper map`, resolution, and A0 explanation record. |
| Repeated probability gap | Three distinct papers produce a repeated blocker/foundation candidate; no fake mastery or fabricated historical sessions are created. |
| Mastery safety | Assisted correctness does not increment `a0_successes`; only three dated A0 successes plus one novel transfer success and score thresholds can produce `mastered`. |
| Daily use | `dashboard` reports due reviews, weak concepts, unresolved mistakes, repeated blockers, assistance/A0 metrics, and foundation candidates. |
| Vault integrity | `validate` rejects malformed/truncated frontmatter, missing/type-invalid fields, duplicate IDs, filename/ID drift, broken explicit links, partial-write artifacts, and inconsistent mastery counters. |

## Exit checks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m learning_os --help
PYTHONPATH=src python3 -m learning_os validate --json
```

The repository is ready for real use when those checks pass and one fresh vault has completed each acceptance scenario. Real learner records are never fabricated to make the dashboard look healthy.

The current MVP also treats integrity failures as fail-closed diagnostics: validation does not silently normalize or delete a user-authored file. Known explicit links are checked at service boundaries, while `validate` remains the final cross-record audit after manual Markdown edits.
