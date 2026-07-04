---
name: experiment-studio
description: Design and manage falsifiable, reproducible scientific experiments and computational studies with preregistered plans, dataset lineage, environment snapshots, controlled local or remote compute, immutable result events, sensitivity checks, and explicit stop criteria. Use for experiment design, data analysis plans, simulations, replication studies, scientific software validation, HPC or cloud jobs, and requests to reproduce or compare results.
---

# Experiment Studio

Turn a hypothesis into an executable protocol whose success and failure are both informative.

## Design before execution

1. State hypothesis, unit of analysis, primary outcome, control/baseline, test oracle, acceptance threshold, exclusion rules, repetitions, seeds, and stop conditions.
2. Separate confirmatory outcomes from exploratory analyses. Record deviations after they occur; do not rewrite the original plan.
3. Register every input dataset and transformation with `dataset_ledger.py`.
4. Capture the environment with `capture_environment.py`.
5. Append a plan event with `experiment_ledger.py plan` before inspecting outcomes.

## Compute safely

Create a compute plan with `compute_job.py plan`. The plan must name backend, target, command, resources, data classification, cost/time limit, stop condition, and output location.

Do not execute SSH, cluster, Modal, cloud, paid, shared, or long-running compute until the user explicitly approves the concrete plan. Record that approval with `compute_job.py approve`; the script never grants approval itself. Start with a cheap smoke test and retain stdout, stderr, exit status, scheduler/job ID, wall time, and failed runs.

## Close the loop

1. Append results using `experiment_ledger.py result`; never replace the plan.
2. Link result event IDs to claims.
3. Run sensitivity checks, alternative explanations, negative controls, and independent recomputation of headline values.
4. Distinguish feasibility, reproducibility, replication, robustness, and external validity.
5. Fork the study metadata with `fork_study.py` when comparing materially different hypotheses or protocols.

Read [references/experiment-protocol.md](references/experiment-protocol.md) for validation oracles, compute approvals, statistical checks, and completion gates.

## Boundaries

One successful run is not robustness. A statistically significant result is not automatically important or causal. Pause for human-subjects, clinical, wet-lab safety, controlled-data, biosafety, publication, or irreversible external actions requiring expert or institutional approval.
