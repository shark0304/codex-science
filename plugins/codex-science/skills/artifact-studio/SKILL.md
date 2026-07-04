---
name: artifact-studio
description: Create and refine reproducible scientific artifacts including figures, tables, notebooks, reports, manuscripts, slide decks, spreadsheets, interactive HTML, molecular or structural views, and data packages with code, input lineage, environment identity, checksums, and visual verification. Use whenever scientific results must become publication-ready or reviewable artifacts.
---

# Artifact Studio

Make each artifact explainable, reproducible, and visually honest.

## Build from lineage

1. Identify the claim or decision the artifact supports and the exact source data or experiment event.
2. Generate the artifact from code or a recorded deterministic transformation where practical.
3. Preserve raw data; write derived data and rendered outputs separately.
4. Record generating code/notebook, parameters, environment, input hashes, and output SHA-256 with `record_artifact.py`.
5. Use installed document, spreadsheet, presentation, PDF, image, browser, or domain renderers when appropriate. Degrade explicitly when a native renderer is unavailable.

## Verify the rendering

Inspect the actual rendered artifact, not only its source. Check axes, units, denominators, uncertainty, sample counts, captions, legends, color accessibility, clipping, resolution, page layout, and consistency between figure/table values and prose.

For interactive or 3D scientific views, also provide a static fallback and the exact data/code needed to regenerate the view. Never imply that visual plausibility validates the underlying analysis.

## Manuscripts and reports

Trace every substantive statement to claim IDs. Recompute headline values from recorded outputs. Preserve protocol deviations, negative results, limitations, reviewer findings, and exact reproduction commands. Build the final handoff with `build_research_packet.py`.

Read [references/artifact-protocol.md](references/artifact-protocol.md) for artifact types, visual integrity checks, and publication handoff requirements.

## Boundaries

Do not hand-edit generated numbers or figures without recording the transformation. Do not use decorative precision, misleading axes, hidden exclusions, unsupported causal language, or inaccessible proprietary formats as the only deliverable.
