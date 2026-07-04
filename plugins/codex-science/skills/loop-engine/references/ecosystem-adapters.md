# Ecosystem adapter candidates

Treat these as discovery sources, not bundled dependencies or endorsements. Reconfirm current license, revision, security posture and compatibility before registration.

| Source | Potential role | Preferred integration |
|---|---|---|
| `github.com/openai/skills` | Official reusable workflows | Install upstream; register selected skill revision |
| `github.com/anthropics/skills` | Open Agent Skills examples | Adapt only compatible, licensed individual skills |
| `github.com/K-Dense-AI/scientific-agent-skills` | Scientific databases and domain packages | Select narrow domain skills; never load the entire catalog by default |
| `github.com/VoltAgent/awesome-agent-skills` | Candidate discovery | Do not execute list entries without upstream review |
| `github.com/gotalab/skillport` | Search and SkillOps experiments | Optional MCP/CLI adapter after evaluation |
| `github.com/promptfoo/promptfoo` | Repeatable behavioral evaluation | External eval gate with pinned package/version |
| `github.com/Arize-ai/phoenix` | Trace and evaluation observability | Optional telemetry backend with data-boundary review |
| `github.com/langfuse/langfuse` | Trace and feedback observability | Optional self-hosted/cloud backend with privacy review |

Prefer static file adapters and local deterministic checks first. Add networked services only when they materially improve the gate and their data destination is authorized.
