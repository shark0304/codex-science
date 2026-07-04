---
name: science-workbench
description: Coordinate auditable, reproducible scientific research from question framing through literature, datasets, experiments, local or remote compute, scientific figures and manuscripts, independent review, forking, and final handoff. Use for end-to-end research projects, vague scientific questions, multi-stage analyses, long-running studies, research workspaces, or requests for a Claude Science-style scientific workbench in Codex.
---

# Science Workbench

Coordinate a research chain another scientist can inspect: question -> evidence -> data -> protocol -> run -> artifact -> review. Preserve uncertainty, negative results, and failed approaches; never fill evidence gaps with plausible prose.

## Select depth

- **Quick**: one source, narrow calculation, or short critique. Do not create a full workspace unless useful.
- **Standard**: multi-source synthesis, dataset analysis, experiment, figure, or report. Maintain the relevant ledgers and provenance.
- **Deep**: long-running study, thesis/grant direction, publication, replication, expensive compute, or high-stakes conclusion. Use all gates, independent review, and a final research packet.

## Initialize and inspect

Inspect the workspace for `.science/`, existing protocols, data, notebooks, source managers, version control, compute constraints, and sensitive-data boundaries. For a new Standard/Deep study, run:

```bash
python3 scripts/init_science_project.py --root <project-root> \
  --title "<study title>" --question "<research question>"
python3 scripts/capability_report.py --root <project-root>
```

Do not overwrite an existing `.science/` directory. Run `migrate_project.py` when the validator reports an older schema.

## Coordinate specialist workflows

1. **Frame**: define scope, unit of analysis, decision, confirmatory hypotheses, exploratory questions, falsifiers, success thresholds, constraints, and required expert/ethics review.
2. **Evidence**: use `$literature-studio` for searches, source intake, paper cards, claim ledgers, contradictions, and gap analysis.
3. **Data and experiments**: use `$experiment-studio` for dataset lineage, preregistration, environment identity, controlled compute, immutable results, sensitivity analysis, and forks.
4. **Artifacts**: use `$artifact-studio` for code-backed figures, tables, notebooks, rich scientific views, reports, manuscripts, and visual QA.
5. **Review**: use `$science-reviewer` in an independent context when available and authorized. Otherwise perform a labeled adversarial pass and disclose that independence is degraded.
6. **Handoff**: run structural/integrity validation, build the research packet, and state what is supported, unresolved, unavailable, or not performed.

Do not claim a specialist pass occurred unless it actually occurred. If a required skill, renderer, connector, database, compute backend, or reviewer context is unavailable, record `degraded` or `unavailable` and continue only within the supported boundary.

## Maintain durable research state

- Update `.science/LAB_NOTES.md` after meaningful work with completed steps, failed approaches and why, unresolved questions, and the next falsifiable action.
- Keep plans immutable after outcome inspection; append deviations and result events.
- Register sources, claims, searches, paper cards, datasets, transformations, experiment plans/results, compute approvals/results, environments, artifacts, reviews, and forks.
- Use `fork_study.py` for a new analytical branch; use version control for code and full-project history.
- Never store credentials, participant identifiers, protected health information, controlled raw data, or proprietary content in public ledgers.

Follow [references/project-contract.md](references/project-contract.md) for layout and schemas, [references/coordination-protocol.md](references/coordination-protocol.md) for stage gates, and [references/capability-matrix.md](references/capability-matrix.md) for the public Claude Science alignment boundary.

## Safety and authority gates

Pause before remote/paid/shared compute, large downloads, external writes, publication submission, human-subject data transfer, controlled database access, clinical decisions, or wet-lab actions with meaningful safety risk. Present the concrete action, destination, data, cost/resources, observation window, stop condition, and rollback/recovery path before seeking approval.

## Validate and deliver

```bash
python3 scripts/validate_science_project.py --root <project-root>
python3 scripts/audit_project.py --root <project-root>
python3 scripts/build_research_packet.py --root <project-root>
```

Validation proves schema, references, and local file integrity—not scientific truth, novelty, safety, peer review, or external validity. End with conclusions by confidence, protocol deviations, negative/failed results, limitations, reviewer findings, exact reproduction commands, and work not performed.
