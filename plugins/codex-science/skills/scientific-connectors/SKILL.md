---
name: scientific-connectors
description: Search Crossref, PubMed, and OpenAlex through read-only scientific metadata APIs, save auditable normalized snapshots, and import reviewed records into Codex Science evidence ledgers. Use for literature discovery, DOI or PMID metadata, reproducible database searches, source intake, connector verification, or testing scientific database access without treating search results as scientific evidence.
---

# Scientific Connectors

Use deterministic, read-only metadata retrieval before synthesis. Save every result set to a file, inspect it, then import only records worth screening. A database hit, abstract, title, citation count, or API ranking is not evidence for a scientific claim.

## Choose a connector

- Use Crossref for DOI-centric scholarly metadata. Anonymous public access works; set `CROSSREF_MAILTO` for the polite pool when appropriate.
- Use PubMed for biomedical discovery through NCBI E-utilities. Set `NCBI_EMAIL` for responsible identification and optionally `NCBI_API_KEY` for an authorized higher request rate.
- Use OpenAlex for broad scholarly graph metadata. Set `OPENALEX_API_KEY`; current OpenAlex API access requires a key and uses a credit allowance.

Read [references/connector-contract.md](references/connector-contract.md) for fields, environment variables, privacy behavior, and upstream limitations. Read [references/provider-notes.md](references/provider-notes.md) before changing endpoints or interpreting provider metadata.

## Search and preserve the snapshot

```bash
python3 scripts/literature_connectors.py crossref \
  --query "<review question>" --limit 10 --output <crossref.json>
python3 scripts/literature_connectors.py pubmed \
  --query "<PubMed query>" --limit 10 --output <pubmed.json>
python3 scripts/literature_connectors.py openalex \
  --query "<search terms>" --limit 10 --output <openalex.json>
```

Keep queries narrow, limits bounded, and provider terms/rate limits respected. The snapshot contains normalized records, provider responses, response hashes, sanitized request URLs, retrieval time, and connector version. Credentials, API keys, contact emails, and authorization headers are excluded.

## Review before import

Inspect titles, identifiers, source types, years, authors, venues, correction status when available, and duplicates. Verify DOI/PMID resolution separately for core evidence. Then import selected result indices:

```bash
python3 scripts/literature_connectors.py import \
  --root <project-root> --file <snapshot.json> --prefix CR \
  --search-id Q-CROSSREF-001 --reason "Find primary evidence" \
  --select 1 --select 3
```

Import appends metadata-only source records and one search event. It never creates claims or paper cards, never infers peer review, and never marks the source as full-text reviewed. Use `$literature-studio` to screen sources, create paper cards, search for opposing/null evidence, and bind claims to verified source locations.

## Failure and safety behavior

Stop on non-HTTPS production endpoints, oversized responses, malformed JSON, missing OpenAlex key, network errors after bounded retries, duplicate IDs, invalid snapshots, or missing Codex Science ledgers. Do not use these connectors for bulk harvesting, copyrighted full-text downloading, bypassing access controls, clinical decisions, or automated citation insertion without source review.
