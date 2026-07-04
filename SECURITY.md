# Security and responsible disclosure

Do not open a public issue containing credentials, private datasets, participant information, protected health information, controlled research data, exploitable infrastructure details, or unsafe experimental instructions.

For a sensitive vulnerability, use GitHub private vulnerability reporting for this repository. Include the affected version, reproducible impact, and the minimum safe evidence needed to validate the report.

Codex Science intentionally does not execute or approve remote compute, publish manuscripts, transfer data, or authorize clinical/wet-lab actions. Those boundaries must remain explicit in contributions.

Third-party capability scan reports are triage aids, not guarantees. Review the complete pinned checkout, dependency chain, license, network behavior, credential access, and data destination before marking a capability approved. Runtime authorization in Codex remains separate from registry trust.

Scientific connectors accept provider credentials only through documented environment variables. Never commit those variables, copied request headers, unsanitized URLs, or private provider responses. Connector snapshots are metadata inputs and must be reviewed for data-use or redistribution restrictions before publication.

The unified doctor reports only whether documented credential variables are configured; it never records their values. Tool discovery and credential presence do not establish authorization, quota, compatibility, or permission to transfer research data.

The generated `.science/PORTAL.html` is self-contained and read-only: it embeds no scripts, external fonts, trackers, or network resources, and all ledger content is HTML-escaped. It can still contain sensitive study titles, claims, paths, provider status, or project metadata. Review it and `.science/RESUME.md` before publishing, emailing, or serving them outside the governed project boundary.
