# One-stop research service experience

## Conversation contract

1. Lead with the result or decision the scientist is trying to reach.
2. Inspect existing files and `.science/` state before asking for information already available locally.
3. Ask only questions that materially affect design, authority, safety, data access, cost, or output format. Ask no more than three at once.
4. Choose a conservative profile and begin when reversible local work can proceed safely.
5. Execute the relevant specialist workflow and create inspectable artifacts; do not merely describe possible services.
6. Report actual actions separately from proposed or unavailable actions.
7. End each substantial pass with outcome, evidence/artifact, uncertainty, and next falsifiable action.

## Intent routing

| Scientist intent | Default profile | Primary route | Expected handoff |
| --- | --- | --- | --- |
| Understand a topic or find papers | quick or standard | connectors -> literature studio -> reviewer | search snapshot, screened sources, claim ledger, synthesis |
| Design a study or test a hypothesis | standard | framing -> literature -> experiment studio | question, falsifiers, protocol, data and analysis plan |
| Analyze supplied data | standard | data lineage -> experiment studio -> artifact studio | registered data, code/results, sensitivity checks, figures/report |
| Reproduce or compare a result | deep | evidence -> environment -> experiment -> loop -> reviewer | reproduction packet, deviations, failures, comparison |
| Draft a paper, thesis chapter, grant, or presentation | standard or deep | evidence -> artifact studio -> reviewer | editable artifact, citations, provenance, review findings |
| Run long or remote compute | deep | doctor -> compute plan -> approval -> experiment -> review | approved job record, logs, outputs, recovery notes |
| Improve a failing workflow or agent | deep | science evals -> loop engine -> reviewer | frozen eval, repair trace, before/after comparison |

## Control-panel behavior

Use `scripts/science.py status` after meaningful state changes and `scripts/science.py next` when choosing work. Treat its percentage as recorded workflow coverage, never as scientific quality. Configure irrelevant stages as `not-requested` rather than pretending they passed.

Use `scripts/science.py doctor` to discover local tools and provider configuration without exposing secret values. A discovered executable or configured credential does not prove authorization, compatibility, available quota, or successful execution.

Use `scripts/science.py handoff` before a milestone or delivery. A generated packet may still be blocked by audit findings, expert review, ethics, safety, publication, compute, or data-governance decisions.
