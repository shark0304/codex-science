# Provider notes

## Crossref

Use `https://api.crossref.org/works` for bounded work queries. Crossref exposes public scholarly metadata without registration and recommends identifying polite clients. Member-deposited metadata may be missing, stale, incorrect, corrected, or include content with separate copyright terms. Verify core records at their DOI and publisher/source page.

Official documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/

## PubMed and NCBI E-utilities

Use ESearch to retrieve PubMed IDs and ESummary to retrieve document summaries. Query syntax, indexing and update timing affect recall. A PubMed record is bibliographic metadata; it is not equivalent to reading the article, assessing bias, or checking corrections.

Official documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/

## OpenAlex

Use `https://api.openalex.org/works` with a user-owned API key. API list/search operations consume credits under the current provider policy. OpenAlex coverage and graph-derived fields differ from Crossref and PubMed; do not collapse records solely by title.

Official documentation: https://developers.openalex.org/

Provider APIs and terms can change. Recheck official documentation before modifying endpoints, authentication, limits, pricing assumptions or redistribution behavior.
