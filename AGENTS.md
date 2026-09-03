# Codex Learning OS

## Goal

Maximize the learner's future unassisted performance, not current assisted performance.
This is a personal, Markdown-first learning and research training system.

## Non-negotiable rules

- Assisted performance is not mastery; recognition is not mastery.
- A0 evidence and active output are the main basis for mastery.
- Keep FACT, INFERENCE, HYPOTHESIS, SPECULATION, and UNKNOWN separate.
- Keep AI assistance high for low-value friction and progressively lower it for derivations, critique, evidence judgment, and research decisions.
- Deterministic code owns validation, dates, counters, status transitions, dashboards, and file updates. LLM behavior belongs in the local tutor Skill.
- Markdown frontmatter is the single persisted source of truth. Do not add a parallel JSON/database mastery store.

## Repository map

- `Concepts/`, `Papers/`, `Mistakes/`, `Sessions/`, `Foundation/`, `Sources/`: Markdown vault data.
- `Templates/`: human-readable record templates.
- `src/learning_os/`: deterministic domain model, persistence, policies, and CLI.
- `docs/`: architecture, pedagogy, schema, rubrics, and workflow contracts.
- `.agents/skills/ai-tutor/SKILL.md`: state-aware tutor workflow for Codex.
- `tests/`: policy and end-to-end CLI tests.

Read `docs/architecture.md` and `docs/implementation-plan.md` before changing boundaries, and `docs/mastery-rubric.md` before changing mastery rules.

## Development rules

- Prefer the standard library in the core runtime; optional PyYAML, Pydantic, Typer, and pytest are not required for the CLI to start.
- Preserve existing user-authored Markdown bodies and unknown frontmatter fields when practical.
- Make state changes explicit, deterministic, and testable.
- Use IDs as stable filenames. Never create a second file for the same record type and ID.

## Test commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m learning_os --help
```

If development dependencies are installed, also run `python3 -m pytest`.
