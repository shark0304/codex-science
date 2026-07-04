# Project contract

Use `.science/` as an append-oriented control plane alongside the user's existing project.

```text
.science/
├── study.json
├── QUESTION.md
├── PLAN.md
├── GOVERNANCE.md
├── LAB_NOTES.md
├── capabilities.json
├── evidence/
│   ├── sources.jsonl
│   ├── claims.jsonl
│   ├── searches.jsonl
│   ├── snapshots/               # optional connector result snapshots
│   └── paper-cards/
├── datasets/registry.jsonl
├── experiments/registry.jsonl
├── compute/jobs.jsonl
├── artifacts/manifest.jsonl
├── reviews/
│   └── REVIEW.md
├── loop/                         # optional bounded improvement loop
│   ├── contract.json
│   ├── capabilities.jsonl
│   ├── capability-lock.json
│   ├── iterations.jsonl
│   ├── traces.jsonl
│   ├── evaluations.jsonl
│   ├── decisions.jsonl
│   └── NEXT.md
├── runs/
├── evals/                       # optional comparable benchmark runs
└── forks.jsonl
```

## Invariants

- Keep raw inputs immutable and outside generated-output directories.
- Use UTC ISO-8601 timestamps and append events instead of rewriting history.
- Use stable IDs: `S` sources, `C` claims, `Q` searches, `D` datasets, `E` experiment events, `J` compute events, and `A` artifacts.
- Store one valid JSON object per JSONL line. Append corrections with a `supersedes` reference.
- Hash local inputs, datasets, results and artifacts with SHA-256.
- Never store credentials, access tokens, participant identifiers, protected health information, or restricted raw data in ledgers.
- Pin external capabilities to immutable revisions. Popularity and registry inclusion are not trust signals.

## Evidence

Source records require `id`, `title`, `location`, and `retrieved_at`. Claim records require `id`, `text`, `status`, `sources`, `experiments`, and `created_at`; evidence-backed claims must reference a source or experiment event. Search records preserve query, source/database, filters, reason, selection/rejection and next search. Paper cards bind structured extraction to one source ID.

Connector snapshots preserve sanitized request metadata, response hashes, provider payloads and normalized discovery records. They remain metadata-only until a researcher screens the source. Never infer peer review, correction status, full-text access or claim support from database inclusion.

## Datasets

Register original datasets with identity, location, local hash when available, version, license, access classification, description and timestamp. Derived datasets additionally reference parent dataset IDs and an exact transformation/command. Do not copy restricted data into `.science/`.

## Experiment events

Append a `plan` event with objective, inputs, parameters, seeds, command, test oracle and acceptance threshold. Append each execution as a separate `result` event whose `parent_id` points to the plan. Keep failed, error and inconclusive runs.

## Compute events

Append `plan`, `approval` and `result` events. Remote, paid, shared or sensitive compute plans require an explicit user approval event before execution. Approval is scoped to the recorded command, target, data, resources, cost/time limit and stop condition.

## Artifacts, reviews and forks

Artifacts bind path, kind, SHA-256, byte size, generating command/notebook, input hashes and environment. Reviews classify findings and preserve unresolved risks. Fork records identify source study, destination, reason and timestamp. A valid manifest proves identity and lineage, not scientific validity.

## Closed-loop events

Fix objective, required evaluation gates, iteration limit, stall limit, progress threshold and optional budget before the first loop trace. Each iteration follows plan, trace, evaluation and decision. Only approved, scanned and pinned capability IDs may appear in plans. A success decision requires every declared gate to pass in the same iteration. Stop rather than continuing beyond resource or no-progress limits.
