# Reviewer protocol

## Severity

- **Critical**: invalidates the main conclusion, violates safety/ethics/privacy, fabricates evidence, or makes reproduction impossible.
- **Major**: materially weakens a key claim and requires new analysis, evidence, control, or substantial revision.
- **Minor**: bounded issue that does not overturn the conclusion but should be corrected.
- **Note**: clarification, optional improvement, or residual uncertainty.

## Core attacks

- Evidence: fabricated/misapplied citations, abstract-only support, hidden contradictory evidence.
- Design: post-hoc hypotheses, weak controls, selection bias, confounding, underpowering.
- Analysis: leakage, multiplicity, inappropriate tests, unstable numerics, cherry-picked seeds/metrics.
- Artifacts: mismatched values, misleading axes, missing units/denominators, inaccessible generation path.
- Reproducibility: missing inputs, code, environment, parameters, logs, failures, or checksums.
- Claims: causality without design, generalization beyond tested scope, novelty or superiority without comparison.
- Governance: missing consent/ethics, restricted-data leakage, license breach, unsafe wet-lab or clinical implication.

## Release criteria

Do not recommend release with unresolved critical findings. For major findings, require remediation or explicit limitation accepted by the decision owner. State what was not reproduced and what specialist review remains necessary.
