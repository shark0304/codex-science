# Codex Science

Codex Science is an open, auditable scientific research workbench packaged as a Codex plugin. It turns a research question into traceable evidence, datasets, preregistered experiments, controlled compute, reproducible artifacts, independent review, and a final handoff packet.

It is an independent implementation inspired by publicly documented scientific-agent practices. It does not copy Claude Science source code, private prompts, model weights, proprietary UI, or licensed connectors.

## What it provides

- A coordinating `science-workbench` skill.
- A single `science.py` service entry point for guided intake, environment checks, workflow status, next actions, connectors, evals, loops, audits, and handoff.
- Specialist literature, connector, experiment, artifact, loop, eval, and reviewer skills.
- Source, search, paper-card, claim, dataset, experiment, compute, artifact, review, and fork records.
- Approval-aware plans for local, SSH, SLURM, Modal, or other compute backends.
- Environment and tool capability snapshots that intentionally omit credentials.
- SHA-256 lineage and mutation detection for local datasets, outputs, and artifacts.
- Deterministic structural/reproducibility audit plus an adversarial scientific-review protocol.
- A bounded plan → trace → eval → decision loop with explicit success, budget and no-progress gates.
- A capability registry that pins third-party skills, plugins, MCP tools and services to reviewed revisions.
- Static capability inventory and risk scanning before external code becomes eligible for a loop plan.
- Read-only Crossref and PubMed metadata retrieval plus keyed OpenAlex search, with secret-free snapshots and explicit source import.
- A versioned eight-task transparent benchmark for same-task scientific-agent regression and exploratory comparison.
- Timestamped Markdown research packets suitable for supervisors, collaborators, reviewers, and future sessions.
- A profile-aware workflow dashboard that distinguishes recorded coverage from scientific quality and refuses premature completion claims.
- A self-contained visual research portal plus a portable new-thread resume capsule.
- A dynamic, machine-readable audit of public Claude Science feature coverage with explicit `ready`, `degraded`, and `unavailable` states.

## Install

```bash
codex plugin marketplace add shark0304/codex-science
codex plugin add codex-science@codex-science
```

Restart Codex, start a new thread, then ask:

```text
Use Codex Science as my one-stop research concierge. My goal is: <your goal>.
Inspect what I already have, do the work you can, and keep me oriented from question to reproducible handoff.
```

You can also open `/plugins`, select the **Codex Science** marketplace, and install the plugin from the UI. Codex plugin packaging and marketplace behavior follow the [official plugin documentation](https://developers.openai.com/codex/plugins/build).

## One-stop research experience

You do not need to choose scripts or specialist skills. State the outcome you need—for example a literature review, experiment design, supplied-data analysis, reproduction, thesis chapter, grant, figure, presentation, or reviewer-ready packet. The coordinator inspects the workspace, asks only questions that materially change the design or authority boundary, selects a Quick/Standard/Deep profile, invokes the relevant specialist workflows, and reports:

- the current outcome;
- evidence or artifacts actually created;
- unresolved uncertainty;
- the next falsifiable action.

It maintains `.science/STATUS.md` as a compact control panel. Required stages can be marked `not-requested` when they genuinely do not apply; they are never marked passed merely to improve a percentage.

It also generates `.science/PORTAL.html`, a local read-only research workspace that brings workflow stages, next actions, evidence, datasets, experiments, artifacts, services, providers, and public capability gaps into one visual page. `.science/RESUME.md` carries the minimum durable context into a new Codex thread or another computer. Both remain plain files under your control.

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
   -> bounded trace/eval/repair loop when gates fail
   -> research packet
```

For Standard and Deep studies, the plugin creates a local `.science/` directory beside your project. The directory is append-oriented research memory; raw or restricted datasets should remain in their governed storage location.

## Deterministic commands

The coordinator normally uses one entry point for you. It can also be invoked directly:

```bash
SCIENCE=/path/to/codex-science/plugins/codex-science/skills/science-workbench/scripts/science.py

python3 "$SCIENCE" doctor --root .
python3 "$SCIENCE" init --root . --title "My study" \
  --question "What would falsify hypothesis H?" --profile standard --domain general
python3 "$SCIENCE" status --root .
python3 "$SCIENCE" next --root .
python3 "$SCIENCE" portal --root .
python3 "$SCIENCE" resume --root .
python3 "$SCIENCE" parity --root . --save
python3 "$SCIENCE" handoff --root .
```

Run `python3 "$SCIENCE" services` for the complete local catalog. Every command provides `--help`. None of the included scripts submit compute jobs, publish manuscripts, transfer datasets, or grant approvals. External actions remain subject to Codex permissions and explicit user authorization. A draft packet may be generated with known gaps, but `handoff` returns a blocking status rather than claiming completion while required stages or audit findings remain unresolved.

## Loop Engine

Initialize a closed loop only after the study and acceptance gates are understood:

```bash
LOOP=/path/to/codex-science/plugins/codex-science/skills/loop-engine/scripts

python3 "$LOOP/loop_engine.py" --root . init \
  --objective "Resolve the main evidence gap and reproduce the result" \
  --gate "evidence:Every material claim has verified support" \
  --gate "reproducibility:A clean rerun meets the preregistered threshold" \
  --max-iterations 6 --stall-limit 2 --min-progress 0.05
```

Each iteration is recorded as plan, trace, evaluation and decision events. The engine refuses premature success and refuses continued work after iteration, budget or no-progress limits. It writes `.science/loop/NEXT.md` as the portable next-pass handoff.

Third-party repositories are adapters, not vendored dependencies. Check out an immutable revision, scan it with `scan_capability.py`, review its scripts and license, then register that exact revision with `capability_registry.py`. Stars and inclusion in an awesome list are discovery signals—not a security or scientific-quality verdict.

## Scientific metadata connectors

The connector skill queries official metadata APIs and saves the provider response, normalized records, response hashes and sanitized request URLs. Search results remain metadata-only until explicitly screened and imported:

```bash
CONNECTORS=/path/to/codex-science/plugins/codex-science/skills/scientific-connectors/scripts

python3 "$CONNECTORS/literature_connectors.py" crossref \
  --query "reproducible scientific workflows" --limit 10 \
  --output .science/evidence/snapshots/crossref.json
python3 "$CONNECTORS/literature_connectors.py" import \
  --root . --file .science/evidence/snapshots/crossref.json \
  --prefix CR --search-id Q-CR-001 --reason "Screen primary evidence" --select 1
```

Crossref and PubMed support anonymous bounded queries. OpenAlex currently requires `OPENALEX_API_KEY`; the key and optional Crossref/NCBI contact or API-key environment variables are redacted from snapshots.

## Same-task scientific-agent evaluation

The `science-evals` skill ships a transparent synthetic process benchmark and deterministic runner:

```bash
EVALS=/path/to/codex-science/plugins/codex-science/skills/science-evals/scripts

python3 "$EVALS/science_eval.py" init \
  --run-dir .science/evals/codex-run --system codex-science \
  --model "<exact model>" --repetitions 3
python3 "$EVALS/science_eval.py" grade --run-dir .science/evals/codex-run
python3 "$EVALS/science_eval.py" validate --run-dir .science/evals/codex-run
```

Use identical tasks, tools, data, time limits and attempt counts for a comparison system. The bundled suite is appropriate for regression and exploratory comparison; it is transparent, synthetic and does not prove overall scientific intelligence or complete Claude Science parity.

## Public capability alignment

The plugin aligns with the public Claude Science workflow at the methods layer: coordinating and specialist workflows, literature synthesis, auditable artifacts, local research state, compute planning, persistent memory, study forks, reviewer passes, and optional scientific tools.

Run `python3 "$SCIENCE" parity --root . --save` for the current environment-aware audit. The report deliberately does not claim model-quality, benchmark, proprietary-service, or complete product parity. Some product capabilities necessarily remain environment-dependent:

- Scientific databases and connectors require separate installation, authentication, licensing, and institutional authorization.
- External skills and plugins require independent license, security, data-boundary and compatibility review before approval in a loop.
- OpenAlex retrieval requires a user-owned key and consumes the provider's current credit allowance; Codex Science does not supply or persist that credential.
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
python3 -m compileall -q plugins tests scripts
python3 -m unittest discover -s tests -v
python3 scripts/validate_release.py
```

## Public design sources

- [Claude Science public announcement](https://www.anthropic.com/news/claude-science-ai-workbench)
- [Long-running scientific computing](https://www.anthropic.com/research/long-running-Claude)
- [BioMysteryBench evaluation design](https://www.anthropic.com/research/Evaluating-Claude-For-Bioinformatics-With-BioMysteryBench)
- [Deterministic retrieval for scientific agents](https://www.anthropic.com/research/agents-in-biology)
- [Codex plugin documentation](https://developers.openai.com/codex/plugins/build)
- [OpenAI agent improvement loop](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop)
- [OpenAI iterative repair loops](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex)
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
- [OpenAlex developer documentation](https://developers.openalex.org/)

## License

MIT
