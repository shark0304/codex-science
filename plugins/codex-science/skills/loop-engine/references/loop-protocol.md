# Loop protocol

## State layout

```text
.science/loop/
├── contract.json
├── capabilities.jsonl
├── capability-lock.json
├── iterations.jsonl
├── traces.jsonl
├── evaluations.jsonl
├── decisions.jsonl
└── NEXT.md
```

The contract fixes objective, required gates and resource limits before the first result. JSONL files are append-only. `capability-lock.json` and `NEXT.md` are derived current-state views and may be regenerated from their ledgers.

## State machine

An iteration follows `plan -> trace -> evaluation -> decision`. Multiple trace and evaluation events may belong to one iteration. The latest evaluation for each required gate determines whether that gate passes.

- `continue`: close the current iteration and create a next-action handoff. Reject when the maximum iteration count, budget or consecutive low-progress limit is reached.
- `succeed`: close the loop only when every required gate has a latest `pass` evaluation for that iteration.
- `stop`: close without success because of safety, authority, feasibility, budget, evidence or user direction.

A later iteration is valid only after the previous iteration has a `continue` decision. Never append work after `succeed` or `stop`; fork the study instead.

## IDs and immutable evidence

Use stable IDs such as `I001` iterations, `T001` traces, `V001` evaluations and `X001` decisions. Every ID is unique within its ledger. Local inputs, outputs, evaluation evidence and scan reports carry path, SHA-256 and byte size. Mutation creates a validation failure; record a new event instead of rewriting history.

## Recovery

- Interrupted before trace: preserve the plan and resume it or record `stop`.
- Tool failure: append a failed trace and evaluate the affected gates.
- Bad capability: append a blocked registry event, rebuild the lock, and continue only with another approved capability.
- Contract no longer appropriate: fork the study and initialize a new loop; do not edit acceptance gates after seeing outcomes.
- Validator failure: repair structural corruption without changing historical meaning, run `capability_registry.py rebuild-lock` when only the derived lock is stale, then rerun validation.
