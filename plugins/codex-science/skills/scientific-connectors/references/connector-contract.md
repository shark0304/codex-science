# Connector contract

## Snapshot schema

`codex-science.connector-snapshot.v1` records:

- connector name and implementation version;
- exact query, result limit and UTC retrieval time;
- sanitized request URLs with secrets and contact identifiers removed;
- SHA-256 and byte size for each provider response;
- bounded, secret-sanitized provider response objects used for normalization;
- normalized records with provider ID, title, authors, year, DOI, URL, type and venue;
- an interpretation warning that metadata has not been screened as scientific evidence.

Snapshots are immutable inputs. Run a new search instead of overwriting a snapshot used by a study.

## Environment variables

- `CROSSREF_MAILTO`: optional contact for Crossref polite access; used in requests but excluded from snapshots.
- `NCBI_EMAIL`: optional contact supplied to NCBI; excluded from snapshots.
- `NCBI_API_KEY`: optional authorized NCBI API key; excluded from snapshots.
- `OPENALEX_API_KEY`: required for production OpenAlex access; excluded from snapshots.

Credentials and contact identifiers are sent only to the connector's exact official HTTPS hostname on the default port. Custom or localhost endpoints receive no environment credentials, and HTTP redirects are rejected instead of forwarding a credential-bearing request.

Never pass secrets through output filenames, query strings supplied in prompts, study ledgers, or command examples.

## Import behavior

Import requires explicit one-based result indices. Each source record is marked:

- `evidence_level: unknown`
- `review_status: unknown`
- `access_status: metadata-only`
- `correction_status: unknown` unless provider metadata explicitly establishes otherwise

The import skips an already-recorded DOI or location and records selected source IDs in a search event. It does not fabricate unavailable fields or infer article quality from database inclusion.
