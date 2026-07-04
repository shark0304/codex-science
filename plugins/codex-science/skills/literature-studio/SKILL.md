---
name: literature-studio
description: Build evidence-grounded scientific literature reviews, source and claim ledgers, search logs, paper cards, contradiction maps, gap analyses, and citation audits. Use for papers, PDFs, BibTeX or Zotero exports, literature folders, systematic or scoping reviews, research landscapes, disputed claims, or requests to find and synthesize scientific evidence.
---

# Literature Studio

Produce a traceable source-to-claim synthesis. Never fabricate citations or let a search snippet stand in for a source.

## Choose depth

- **Quick**: one paper or narrow claim; return source-backed findings and explicit inference.
- **Standard**: multiple sources; maintain search, source, claim, and paper-card records.
- **Deep**: systematic/scoping review, gap analysis, or contested topic; preregister inclusion rules, log rejected sources, search for disconfirming evidence, and audit every material claim.

## Run the workflow

1. Define the review question, scope, source types, date/language limits, inclusion/exclusion criteria, and stopping rule before broad searching.
2. Log every material search with `../science-workbench/scripts/literature_ledger.py search`.
3. Prefer primary papers, official datasets, registrations, protocols, standards, and source repositories. Use reviews for orientation and citation chaining.
4. Add sources with `science_ledger.py`; preserve DOI/accession/version, retrieval date, peer-review status, correction/retraction status, and local checksum when available.
5. Create paper cards for core sources. Extract design, population/system, method, sample size, outcomes, effect and uncertainty, limitations, conflicts, data/code availability, and the exact claims supported.
6. Build claims by evidence lane. Include supporting, opposing, and null results together. Mark each claim `observed`, `derived`, `hypothesis`, `conflicted`, or `unsupported`.
7. Search explicitly for evidence that would weaken the leading synthesis or proposed gap.
8. Before delivery, verify every citation resolves and supports the exact wording used.

Read [references/literature-protocol.md](references/literature-protocol.md) for paper-card fields, evidence hierarchy, systematic-review gates, and completion criteria.

## Boundaries

Do not infer full methods from an abstract, assign a DOI from memory, equate citation count with quality, hide excluded contradictory studies, or call an absence of retrieved evidence proof of absence. Mark inaccessible sources and unresolved conflicts.
