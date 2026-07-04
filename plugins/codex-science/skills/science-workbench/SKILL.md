---
name: science-workbench
description: Provide a one-stop, auditable scientific research service from vague intent through question framing, literature, datasets, experiments, compute, artifacts, manuscripts, evaluation, review, iteration, and final handoff. Use for end-to-end research projects, literature reviews, data analyses, reproductions, paper or grant workflows, long-running studies, scientific-agent comparisons, repeated eval-and-repair work, or requests for a Claude Science-style research workbench in Codex.
---

# Science Workbench

Coordinate a research chain another scientist can inspect: question -> evidence -> data -> protocol -> run -> artifact -> review. Preserve uncertainty, negative results, and failed approaches; never fill evidence gaps with plausible prose.

## Act as the research concierge

Accept the scientist's goal in ordinary language and coordinate the required services. Do the work that is locally possible instead of returning a menu of scripts. Use `scripts/science.py` internally as the single control entry point; show commands only when the user asks or needs to reproduce the work.

For a vague or multi-stage request, read [references/service-experience.md](references/service-experience.md). Determine the intended decision or deliverable, available evidence/data, and material constraints. Ask at most three short questions only when their answers would change the research design, safety boundary, data access, cost, or deliverable. Otherwise state conservative assumptions and begin.

Keep the user oriented with four compact facts: current outcome, evidence or artifact created, unresolved uncertainty, and next falsifiable action. Never report a capability, specialist pass, connector search, reviewer check, or computation as completed unless it actually ran and left inspectable evidence.

Treat `.science/PORTAL.html` as the visual front door for Standard and Deep studies. Refresh it after meaningful state changes so the scientist can inspect workflow coverage, evidence, data, experiments, artifacts, services, and public capability gaps in one local page. Treat `.science/RESUME.md` as the cross-thread continuity capsule and `.science/PARITY.json` as a dynamic public-feature audit. Neither file is evidence of scientific truth or model-level parity.

## Select depth

- **Quick**: one source, narrow calculation, or short critique. Do not create a full workspace unless useful.
- **Standard**: multi-source synthesis, dataset analysis, experiment, figure, or report. Maintain the relevant ledgers and provenance.
- **Deep**: long-running study, thesis/grant direction, publication, replication, expensive compute, high-stakes conclusion, or repeated improvement. Use all gates, `$loop-engine`, independent review, and a final research packet.

## Initialize and inspect

Inspect the workspace for `.science/`, existing protocols, data, notebooks, source managers, version control, compute constraints, and sensitive-data boundaries. For a new Standard/Deep study, run:

```bash
python3 scripts/science.py init --root <project-root> \
  --title "<study title>" --question "<research question>" \
  --profile <quick|standard|deep> --domain <domain>
python3 scripts/science.py doctor --root <project-root> --save
python3 scripts/science.py next --root <project-root>
python3 scripts/science.py portal --root <project-root>
```

Do not overwrite an existing `.science/` directory. Run `migrate_project.py` when the validator reports an older schema.

## Coordinate specialist workflows

1. **Frame**: define scope, unit of analysis, decision, confirmatory hypotheses, exploratory questions, falsifiers, success thresholds, constraints, and required expert/ethics review.
2. **Evidence**: use `$literature-studio` for searches, source intake, paper cards, claim ledgers, contradictions, and gap analysis. Use `$scientific-connectors` for bounded Crossref, PubMed, or OpenAlex metadata retrieval when those providers fit the question.
3. **Data and experiments**: use `$experiment-studio` for dataset lineage, preregistration, environment identity, controlled compute, immutable results, sensitivity analysis, and forks.
4. **Artifacts**: use `$artifact-studio` for code-backed figures, tables, notebooks, rich scientific views, reports, manuscripts, and visual QA.
5. **Closed-loop improvement**: use `$loop-engine` when work must repeat until explicit evidence, reproducibility, quality, safety, or performance gates pass. Register only pinned and reviewed external capabilities.
6. **Evaluation**: use `$science-evals` for regression measurement or same-task comparison claims. Keep transparent structural scores separate from blinded human review.
7. **Review**: use `$science-reviewer` in an independent context when available and authorized. Otherwise perform a labeled adversarial pass and disclose that independence is degraded.
8. **Handoff**: refresh the workflow dashboard, run structural/integrity validation and audit, build the research packet, and state what is supported, unresolved, unavailable, or not performed.

Do not claim a specialist pass occurred unless it actually occurred. If a required skill, renderer, connector, database, compute backend, or reviewer context is unavailable, record `degraded` or `unavailable` and continue only within the supported boundary.

## Maintain durable research state

- Update `.science/LAB_NOTES.md` after meaningful work with completed steps, failed approaches and why, unresolved questions, and the next falsifiable action.
- Keep plans immutable after outcome inspection; append deviations and result events.
- Register sources, claims, searches, paper cards, datasets, transformations, experiment plans/results, compute approvals/results, environments, artifacts, reviews, and forks.
- For iterative work, preserve loop contracts, capability locks, traces, evaluations, failures, decisions, resource limits, and stop reasons under `.science/loop/`.
- Use `fork_study.py` for a new analytical branch; use version control for code and full-project history.
- Refresh `status`, `resume`, `parity`, and `portal` before a thread handoff or milestone. In a new thread, inspect `.science/RESUME.md` before continuing.
- Never store credentials, participant identifiers, protected health information, controlled raw data, or proprietary content in public ledgers.

Follow [references/project-contract.md](references/project-contract.md) for layout and schemas, [references/coordination-protocol.md](references/coordination-protocol.md) for stage gates, and [references/capability-matrix.md](references/capability-matrix.md) for the public Claude Science alignment boundary.

## Safety and authority gates

Pause before remote/paid/shared compute, large downloads, external writes, publication submission, human-subject data transfer, controlled database access, clinical decisions, or wet-lab actions with meaningful safety risk. Present the concrete action, destination, data, cost/resources, observation window, stop condition, and rollback/recovery path before seeking approval.

## Validate and deliver

```bash
python3 scripts/science.py status --root <project-root>
python3 scripts/science.py parity --root <project-root> --save
python3 scripts/science.py resume --root <project-root>
python3 scripts/science.py portal --root <project-root>
python3 scripts/science.py handoff --root <project-root>
```

Validation proves schema, references, and local file integrity—not scientific truth, novelty, safety, peer review, or external validity. End with conclusions by confidence, protocol deviations, negative/failed results, limitations, reviewer findings, exact reproduction commands, and work not performed.
