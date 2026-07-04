# Coordination protocol

## Stage gates

1. **Question gate**: scope, decision, falsifier, success criterion, constraints and safety boundary are explicit.
2. **Evidence gate**: material claims have source IDs; contradictions, null evidence and inaccessible sources are visible.
3. **Data gate**: datasets have identity, version/hash, license/access class and transformation lineage.
4. **Protocol gate**: experiment plan, oracle, threshold, controls, exclusions, repeats, seeds and stop conditions predate outcomes.
5. **Compute gate**: remote/paid/shared work has a scoped user approval event; local work has bounded resource expectations.
6. **Artifact gate**: outputs bind to inputs, code/command, environment and SHA-256; actual renderings were inspected.
7. **Review gate**: structural audit and adversarial scientific review completed; critical findings are resolved or block release.
8. **Handoff gate**: research packet contains evidence, methods, results, failures, limitations, review, provenance and reproduction commands.
9. **Iteration gate**: repeated work has a frozen loop contract, pinned capabilities, trace evidence, explicit eval verdicts, bounded resources and a valid continue/succeed/stop decision.

## State labels

Use `ready`, `degraded`, `unavailable`, `not-requested`, and `not-verified` for capabilities. Use `observed`, `derived`, `hypothesis`, `conflicted`, and `unsupported` for claims. Never collapse these vocabularies into a generic success label.

Use `required`, `adaptive`, and `not-requested` for workflow relevance. Use `not-started`, `in-progress`, `ready`, and `not-requested` for recorded workflow coverage. A `ready` workflow stage means its minimum local evidence is present; it is not expert approval or a scientific verdict.

## Long-running work

Treat `LAB_NOTES.md` as portable memory. Record current status, completed work, failed approaches and why, known limitations, key accuracy/evidence checkpoints, and the next falsifiable action. Use a fork for materially different protocols instead of silently changing the active study.

## Human roles

Identify who owns scientific judgment, ethics/safety, data access, compute spend, and release/publication. Codex may prepare and verify packets but must not invent approvals or impersonate expert review.

## Specialist and reviewer contexts

When the environment supports multiple agents and the user authorizes delegation, give each specialist only the scoped question and raw artifacts it needs. Keep the reviewer independent: do not reveal the intended conclusion, suspected defect, or desired verdict. Merge outputs through source, claim, experiment and finding IDs. Resolve critical findings, rerun validation and review, and preserve the original finding rather than erasing it.
