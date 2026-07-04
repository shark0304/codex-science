# External capability policy

## Admission sequence

1. Identify the smallest capability needed; prefer an already installed and reviewed capability.
2. Resolve the upstream repository or package to an immutable commit, digest or version. Reject `main`, `master`, `HEAD`, `latest`, wildcards and unpinned URLs as lock revisions.
3. Establish license and data-handling terms. `UNKNOWN` is allowed for investigation but not silent redistribution.
4. Scan the local checkout with `scan_capability.py`.
5. Review every warning, bundled script, network endpoint, credential request, lifecycle hook and dependency installer.
6. Register the capability as `approved` only with a named reviewer. Use `--accept-risk` when the scan status is `review` and document why.
7. Invoke through the active Codex sandbox and permission model. Registry approval is not authorization for external side effects.

## Integration boundary

The registry records an adapter contract rather than copying upstream code:

- `invocation`: explicit skill mention, plugin selector, MCP server/tool, or approved command entry point.
- `input_contract`: expected inputs, data classification and prerequisites.
- `output_contract`: expected files or structured output, provenance and failure semantics.
- `revision`: immutable upstream identity.
- `scan_report`: local content digest and security findings.

Keep upstream projects independently installable and update them intentionally. Re-scan and append a new registry event whenever the revision changes.

## Default trust levels

- `unreviewed`: discoverable but unusable by loop plans.
- `reviewed`: inspected but not authorized for loop execution.
- `approved`: eligible for plans at the recorded revision; still subject to runtime permissions.
- `blocked`: prohibited until a new revision and review resolve the finding.

Popularity, stars and inclusion in an awesome list are discovery signals only. They are not evidence of safety, licensing, scientific validity, maintenance quality or compatibility.
