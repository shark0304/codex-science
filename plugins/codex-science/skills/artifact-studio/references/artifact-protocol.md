# Artifact protocol

## Supported artifact families

- Figures: raster, vector, multi-panel, statistical, microscopy, spectra, maps.
- Scientific views: structures, molecules, genome tracks, networks, spatial data, interactive HTML.
- Tables and datasets: CSV/TSV, spreadsheets, machine-readable metadata, data dictionaries.
- Computational narratives: notebooks, scripts, environment locks, run logs.
- Documents: reports, manuscripts, supplements, PDFs, slide decks and posters.

Use an installed format-specific skill or renderer when available. Keep the scientific lineage in `.science/` regardless of output format.

## Visual integrity

Verify scale, origin, transform, units, uncertainty, sample count, exclusions, legend, caption, panel ordering, color accessibility, resolution and export dimensions. Avoid truncated axes and encodings that exaggerate effects. Pair interactive/3D outputs with a static, citable fallback.

## Machine-readable handoff

Bundle source data or stable identifiers, generating code, command/notebook, environment, dependencies, artifact SHA-256, license, and a plain-language interpretation. Prefer open formats and include schema/data dictionaries.

## Manuscript integrity

Check that citations support exact wording; figures/tables match prose; values, units and denominators agree; limitations and protocol deviations remain visible; and supplementary material can reproduce headline results.
