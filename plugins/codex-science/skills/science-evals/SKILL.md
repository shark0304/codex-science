---
name: science-evals
description: Prepare, record, grade, validate, and compare reproducible scientific-agent benchmark runs across Codex, Claude, or other systems. Use when measuring evidence traceability, uncertainty, protocol discipline, safety gates, reproducibility, loop decisions, regression behavior, or claims of scientific-agent parity on the same tasks and resource constraints.
---

# Science Evals

Measure behavior before claiming parity. Run the same versioned suite, task prompts, tool/data access, model settings, time budget, attempt count, and human rubric for every system. Preserve all attempts, failures, costs, durations and output hashes.

## Initialize a run

```bash
python3 scripts/science_eval.py init \
  --run-dir <run-directory> --system <codex-science-or-claude-science> \
  --model <exact-model> --repetitions 3
```

The bundled `codex-science-core-v1` suite tests conflicted evidence, dataset lineage, outcome leakage, remote-compute approval, artifact tampering, loop stalls, third-party capability admission, and citation uncertainty. It uses synthetic metadata and transparent deterministic checks; it does not establish domain-level scientific competence.

Read [references/benchmark-protocol.md](references/benchmark-protocol.md) before a comparative run. Read [references/scoring-contract.md](references/scoring-contract.md) before interpreting scores or changing the suite.

## Execute and record every task

Print one prompt without its checks:

```bash
python3 scripts/science_eval.py task --run-dir <run-directory> --id <task-id>
```

Give that prompt to the evaluated system in an isolated workspace. Save its raw JSON response unchanged, then record it:

```bash
python3 scripts/science_eval.py record \
  --run-dir <run-directory> --task <task-id> --attempt 1 \
  --output <raw-response.json> --status completed \
  --duration-seconds <seconds> --cost <provider-cost-or-zero>
```

Do not repair malformed answers before recording. Do not omit failed, blocked, timed-out or inconvenient runs. Human scores are optional and must be assigned blind to system identity using the published rubric.

## Grade, validate, and compare

```bash
python3 scripts/science_eval.py grade --run-dir <run-directory>
python3 scripts/science_eval.py validate --run-dir <run-directory>
python3 scripts/science_eval.py compare \
  --run-a <codex-run> --run-b <comparison-run> --output <comparison.md>
```

Report coverage, structural mean, strict pass rate, human-score coverage, duration and cost separately. Treat differences as descriptive unless the protocol has enough independent repetitions and an appropriate statistical analysis. Never call the bundled suite a proof of overall scientific intelligence, novelty, causal reasoning, clinical safety, or full Claude Science equivalence.

## Feed failures into the loop

Use `$loop-engine` when an eval exposes a repeatable defect. Freeze the failing task and suite hash, create an explicit repair gate, change the smallest relevant harness component, rerun the entire affected slice, and preserve both pre-change and post-change runs. Do not optimize only against one visible example and call it general improvement.
