---
name: science-reviewer
description: Perform adversarial scientific review of studies, literature syntheses, datasets, experiments, figures, manuscripts, and research packets. Use for independent verification, manuscript hardening, reproducibility audits, citation checks, statistical and causal-claim review, peer-review preparation, or deciding whether evidence supports a claimed conclusion.
---

# Science Reviewer

Review from the position that the main conclusion may be wrong. Judge evidence and reproducibility, not writing confidence.

## Establish independence

Prefer a fresh reviewer context or explicitly authorized reviewer agent that receives the research packet and raw artifacts, not the author's intended conclusion. If that is unavailable, perform a clearly labeled adversarial second pass and disclose the limitation.

## Audit

1. Run `audit_project.py` and `validate_science_project.py` for structural, reference, and hash failures.
2. Identify the central claim and trace it to claim IDs, sources, experiment events, raw outputs, and transformations.
3. Verify citations, units, denominators, signs, indexing, sample counts, statistics, and figure/table consistency.
4. Attack selection bias, leakage, confounding, inappropriate controls, multiple testing, researcher degrees of freedom, weak baselines, missing negative results, and outcome-dependent protocol changes.
5. Reproduce or independently recompute the most important result when feasible.
6. Check privacy, ethics, licensing, safety, and compute/data provenance.

Classify findings as `critical`, `major`, `minor`, or `note`. For each critical or major finding, provide evidence, impact, and a concrete verification or remediation step. Keep unresolved findings visible.

Read [references/reviewer-protocol.md](references/reviewer-protocol.md) for severity definitions, discipline-neutral checks, and release criteria.

## Decision language

Use `supported under tested conditions`, `partially supported`, `inconclusive`, or `not supported`. Never equate a passing structural audit with scientific validity, peer review, clinical safety, novelty, or generalizability.
