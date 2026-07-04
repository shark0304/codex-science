# Public capability alignment

Codex Science is an independent implementation of publicly documented scientific-agent practices. It does not copy Claude Science source code, private prompts, model weights, proprietary UI, or licensed connectors.

| Public capability | Codex Science implementation | Default status |
|---|---|---|
| Coordinating agent and specialist workflows | Workbench coordinator plus literature, experiment, artifact and reviewer skills | ready |
| Literature and multi-step research | Search/source/claim ledgers, paper cards, contradiction and gap protocols | ready |
| Auditable figures and manuscripts | Code/input/environment/artifact lineage, hash verification, rendered-artifact QA | ready when a suitable renderer exists |
| Local scientific environment | Plain-file project state, environment snapshots and deterministic scripts | ready |
| Local, SSH, HPC and on-demand compute | Approval-aware compute plans and event ledger; execution uses tools supplied by the user's environment | degraded until backend exists and is authorized |
| Persistent session memory | Append-oriented lab notes, plans, event ledgers and version-control guidance | ready |
| Fork research sessions | Metadata-preserving study forks plus version-control workflow | ready |
| Reviewer agent | Dedicated adversarial reviewer skill and deterministic audit | degraded when independent context/agent is unavailable |
| Scientific databases and specialist tools | Capability inventory and optional Codex plugins/MCP connectors | unavailable by default; varies by installation and authorization |
| Native rich scientific rendering | Artifact workflow can use installed renderers and emits static fallbacks | degraded; plugin does not ship a proprietary native viewer |
| Data locality and privacy controls | Local ledgers, secret exclusion and explicit transfer gates | ready for local files; model/provider data handling remains governed by the active Codex deployment |

## Public sources

- Claude Science product announcement and public feature description: https://www.anthropic.com/news/claude-science-ai-workbench
- Long-running scientific computing patterns: https://www.anthropic.com/research/long-running-Claude
- Objective scientific evaluation and validation notebooks: https://www.anthropic.com/research/Evaluating-Claude-For-Bioinformatics-With-BioMysteryBench
- Deterministic scientific retrieval: https://www.anthropic.com/research/agents-in-biology
- Codex plugin packaging and distribution: https://developers.openai.com/codex/plugins/build

This matrix is an engineering acceptance boundary, not a claim of product identity or model-level parity.
