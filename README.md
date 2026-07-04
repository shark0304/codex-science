# Codex Science

Codex Science is an open, auditable scientific research workbench packaged as a Codex plugin. It turns a research question into traceable evidence, datasets, preregistered experiments, controlled compute, reproducible artifacts, independent review, and a final handoff packet.

It is an independent implementation inspired by publicly documented scientific-agent practices. It does not copy Claude Science source code, private prompts, model weights, proprietary UI, or licensed connectors.

## What it provides

- A coordinating `science-workbench` skill.
- Specialist literature, experiment, artifact, and reviewer skills.
- Source, search, paper-card, claim, dataset, experiment, compute, artifact, review, and fork records.
- Approval-aware plans for local, SSH, SLURM, Modal, or other compute backends.
- Environment and tool capability snapshots that intentionally omit credentials.
- SHA-256 lineage and mutation detection for local datasets, outputs, and artifacts.
- Deterministic structural/reproducibility audit plus an adversarial scientific-review protocol.
- Timestamped Markdown research packets suitable for supervisors, collaborators, reviewers, and future sessions.

## Install

```bash
codex plugin marketplace add shark0304/codex-science
codex plugin add codex-science@codex-science
```

Restart Codex, start a new thread, then ask:

```text
Use Codex Science to turn my research question into an auditable end-to-end study.
```

You can also open `/plugins`, select the **Codex Science** marketplace, and install the plugin from the UI. Codex plugin packaging and marketplace behavior follow the [official plugin documentation](https://developers.openai.com/codex/plugins/build).

## Workflow

```text
question
   -> literature and claim evidence
   -> dataset identity and lineage
   -> preregistered experiment
   -> approved/bounded compute
   -> immutable result events
   -> reproducible figures and manuscripts
   -> independent review
   -> research packet
```

For Standard and Deep studies, the plugin creates a local `.science/` directory beside your project. The directory is append-oriented research memory; raw or restricted datasets should remain in their governed storage location.

## Deterministic commands

The coordinator normally runs these for you. They can also be invoked directly:

```bash
SCRIPTS=/path/to/codex-science/plugins/codex-science/skills/science-workbench/scripts

python3 "$SCRIPTS/init_science_project.py" \
  --root . --title "My study" --question "What would falsify hypothesis H?"
python3 "$SCRIPTS/capability_report.py" --root .
python3 "$SCRIPTS/validate_science_project.py" --root .
python3 "$SCRIPTS/audit_project.py" --root .
python3 "$SCRIPTS/build_research_packet.py" --root .
```

Every command provides `--help`. None of the included scripts submit compute jobs, publish manuscripts, transfer datasets, or grant approvals. External actions remain subject to Codex permissions and explicit user authorization.

## Public capability alignment

The plugin aligns with the public Claude Science workflow at the methods layer: coordinating and specialist workflows, literature synthesis, auditable artifacts, local research state, compute planning, persistent memory, study forks, reviewer passes, and optional scientific tools.

Some product capabilities necessarily remain environment-dependent:

- Scientific databases and connectors require separate installation, authentication, licensing, and institutional authorization.
- SSH, SLURM, Modal and GPU execution require those tools and an approved target.
- Native 3D molecular, protein, genome-track, or other rich rendering requires an installed renderer; Codex Science records the lineage and requires a static fallback.
- Independent reviewer-agent status requires a fresh context or explicitly authorized reviewer agent.
- Provider-side data handling is governed by the active Codex deployment, not this local plugin.

The explicit engineering boundary lives in `capability-matrix.md` inside the coordinator skill.

## Scientific integrity and safety

- Never fabricate a citation, DOI, source location, result, reviewer comment, approval, or dataset identity.
- Distinguish observed, derived, hypothesis, conflicted, and unsupported claims.
- Preserve contradictory evidence, failed runs, protocol deviations, and unresolved reviewer findings.
- Do not treat structural validation as scientific truth, peer review, clinical safety, novelty, causality, or external validity.
- Pause for human-subject, clinical, wet-lab, biosafety, controlled-data, publication, paid-compute, or irreversible external actions that require expert or institutional approval.

## Develop and test

```bash
python3 -m py_compile plugins/codex-science/skills/science-workbench/scripts/*.py
python3 -m unittest discover -s tests -v
python3 scripts/validate_release.py
```

## Public design sources

- [Claude Science public announcement](https://www.anthropic.com/news/claude-science-ai-workbench)
- [Long-running scientific computing](https://www.anthropic.com/research/long-running-Claude)
- [BioMysteryBench evaluation design](https://www.anthropic.com/research/Evaluating-Claude-For-Bioinformatics-With-BioMysteryBench)
- [Deterministic retrieval for scientific agents](https://www.anthropic.com/research/agents-in-biology)
- [Codex plugin documentation](https://developers.openai.com/codex/plugins/build)

## License

MIT
