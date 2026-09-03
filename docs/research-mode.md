# Research Mode workflow

```text
Paper
  -> scan
  -> blocker diagnosis
  -> dependency map
  -> P0/P1/P2/P3
  -> repair P0 first
  -> return to paper
  -> A0 explanation / derivation check
```

## Blockers

Use `notation`, `prerequisite_concept`, `derivation`, `classical_method`, `benchmark`, and `recent_related_work`. Give each a priority:

- `P0`: the core paper cannot be understood without it;
- `P1`: know the central idea, but a full derivation is unnecessary;
- `P2`: know what it is and why it appears;
- `P3`: defer safely for now.

Record the linked Concept when a repair can be tested. If the Concept is created after the blocker, use `learning-os paper blocker link PAPER_ID BLOCKER_ID --concept CONCEPT_ID`. `learning-os paper map PAPER_ID` returns the current dependency map and next action.

## Evidence discipline

Claims and interpretations belong in separate labeled notes:

```yaml
kind: FACT
statement: The paper reports ...
source: section/table/page
```

Use `INFERENCE` for a reasoned consequence, `HYPOTHESIS` for a testable but unverified explanation, `SPECULATION` for a possibility, and `UNKNOWN` when evidence is insufficient.

## Foundation trigger

The dashboard counts a blocker across distinct papers. Three or more occurrences in one domain/foundation label, involving at least two concepts or distinct blocker labels, produce a foundation-track candidate. The threshold is a transparent default, not a claim that three is universally correct.
