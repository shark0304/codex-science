# Contributing

Contributions should improve scientific traceability, reproducibility, safety, or usability without overstating capability.

1. Open an issue describing the research workflow and failure mode.
2. Keep skill instructions concise and route detailed protocols through references.
3. Prefer deterministic, standard-library scripts for fragile recordkeeping.
4. Add positive and negative tests for every new schema or integrity rule.
5. Run the full validation commands from `README.md`.
6. Never commit real credentials, restricted research data, participant information, copyrighted paper collections, or generated claims presented as evidence.
7. Do not vendor third-party capabilities without explicit license compatibility. Pin test fixtures and adapters to immutable revisions, preserve scan findings, and keep runtime authorization separate from registry trust.
8. Mock network providers in CI. Keep live API tests bounded and manual, never place credentials in fixtures, and update provider behavior only from official documentation.
9. Preserve the one-stop service contract: unified commands must remain non-shell, secret-free, profile-aware, and unable to claim milestone completion while required workflow or audit gates remain open.
10. Keep the research portal self-contained, read-only, script-free, and free of external resources. Escape every user- or ledger-controlled field and add adversarial rendering tests for new content.

Pull requests must explain the scientific-integrity boundary: what the change verifies and what it cannot verify.
