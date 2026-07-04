# Experiment protocol

## Test oracles

Prefer objective validation: reference implementation, analytical solution, ground truth, held-out data, conservation law, calibrated instrument, positive/negative controls, or independently computed result. If the oracle is subjective, define blinded scoring, multiple raters, and agreement criteria.

## Preregistration fields

Record objective/hypothesis, unit of analysis, inputs, primary/secondary outcomes, control/baseline, parameters, randomization, blinding, seeds, repetitions, exclusions, test oracle, acceptance threshold, stopping rule, and planned analysis.

## Compute approval packet

Record backend and target, exact command/container, requested CPU/GPU/memory/time, data classification and transfer, expected cost, output/log paths, recovery method, stop condition, and approver. Approval is scoped to that packet; material changes require new approval.

## Analysis checks

Check effect size and uncertainty, power/sample size where relevant, multiplicity, missingness, leakage, confounding, convergence, numerical stability, seed/parameter sensitivity, failed runs, and whether the statistical test matches the design.

## Completion gate

- Plans predate results and deviations are appended.
- Inputs, code, environment, commands, logs, and raw outputs are recoverable.
- Failed and inconclusive runs remain visible.
- Headline results are independently recomputed.
- Conclusions do not exceed the tested population/system and conditions.
