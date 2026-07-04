---
name: loop-engine
description: Run bounded, auditable improvement loops for scientific research and engineering. Use when a task needs repeated plan, execution, trace capture, evaluation, repair, and re-evaluation; when coordinating external skills, plugins, MCP tools, or compute backends; or when success must be proven by explicit gates instead of declared from prose.
---

# Loop Engine

Run a closed loop: plan one falsifiable iteration, invoke only approved capabilities, capture what happened, evaluate against declared gates, then continue, succeed, or stop. Treat the `.science/loop/` ledgers as the source of truth; never infer a pass from a persuasive narrative.

## Initialize a bounded loop

Require an existing Codex Science project. Define objective, gates, iteration ceiling, stall limit, minimum progress, and optional budget before execution:

```bash
python3 scripts/loop_engine.py --root <project-root> init \
  --objective "<measurable objective>" \
  --gate "evidence:<evidence acceptance rule>" \
  --gate "reproducibility:<reproduction acceptance rule>" \
  --max-iterations 6 --stall-limit 2 --min-progress 0.05
```

Do not weaken gates after inspecting an outcome. Start a fork when the contract must materially change.

## Admit capabilities deliberately

Do not vendor or execute a popular repository merely because it is popular. Check out a fixed revision, scan the local candidate, review findings and its license, then register the exact revision:

```bash
python3 scripts/scan_capability.py --path <candidate> --output <scan.json>
python3 scripts/capability_registry.py --root <project-root> register \
  --id <stable-id> --kind skill --source <repository-url> \
  --revision <commit-or-version> --license <SPDX-or-UNKNOWN> \
  --invocation '$skill-name' --scan-report <scan.json> \
  --trust approved --reviewed-by <human-or-team>
```

For a scan with warnings, require an explicit `--accept-risk` and preserve the warning report. Never approve a blocked scan. Read [references/capability-policy.md](references/capability-policy.md) before connecting external code, MCP servers, credentials, or networked tools.
Use [references/ecosystem-adapters.md](references/ecosystem-adapters.md) only to discover possible upstream adapters; every selected revision still needs independent admission.

## Run one iteration at a time

1. Record an iteration plan with approved capability IDs and hashed inputs.
2. Invoke skills explicitly, use MCP tools or run approved commands through the active Codex permission boundary.
3. Record a trace with outputs, status, duration and cost. The loop engine records execution; it does not silently execute third-party code.
4. Record one evaluation per required gate with hashed evidence.
5. Record `continue`, `succeed`, or `stop`. `succeed` is rejected unless every required gate passes. `continue` is rejected at iteration, budget or stall limits.

```bash
python3 scripts/loop_engine.py --root <project-root> plan \
  --id I001 --objective "<smallest discriminating step>" --capability <id> --input <file>
python3 scripts/loop_engine.py --root <project-root> trace \
  --id T001 --iteration I001 --status completed --summary "<observed outcome>" --output <file>
python3 scripts/loop_engine.py --root <project-root> evaluate \
  --id V001 --iteration I001 --gate evidence --verdict fail \
  --summary "<why the gate failed>" --evidence <file>
python3 scripts/loop_engine.py --root <project-root> decide \
  --id X001 --iteration I001 --decision continue --progress 0.2 \
  --reason "<diagnosis>" --next-action "<next falsifiable action>"
```

Use `.science/loop/NEXT.md` as the portable handoff for the next pass. Read [references/loop-protocol.md](references/loop-protocol.md) for event schemas and recovery rules.

## Validate and close

Run validation before every handoff and before declaring success:

```bash
python3 scripts/validate_loop.py --root <project-root>
python3 scripts/loop_engine.py --root <project-root> status
```

Preserve failed traces, failed gates, stopped loops and rejected capabilities. A structurally valid loop proves provenance and gate consistency, not scientific truth. Keep human approval for paid or remote compute, publication, sensitive-data transfer, clinical or wet-lab action, and any irreversible external effect.
