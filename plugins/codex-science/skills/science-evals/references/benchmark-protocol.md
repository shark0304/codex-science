# Benchmark protocol

## Fair comparison

1. Freeze suite file and SHA-256 before running either system.
2. Use the same public prompt, synthetic fixture, allowed tools, connector snapshots, network policy, time limit, attempt count and stopping rule.
3. Record exact product/version, model, date, configuration, installed skills/plugins and any human intervention.
4. Start each task from a fresh context. Do not carry feedback, expected answers, prior attempts or the other system's output into the task.
5. Preserve raw responses before parsing or grading.
6. Randomize and blind system labels before human review.
7. Include failures, refusals, timeouts and malformed outputs in denominators.
8. Separate structural score, human rubric, resource use and safety violations. Do not hide tradeoffs in one composite number.

## Leakage boundary

The bundled suite is transparent and its checks ship with the plugin. It is suitable for regression testing and symmetric product comparisons, not for contamination-resistant leaderboard claims. For publishable evaluation, keep a separately governed held-out suite outside agent-accessible files and disclose its creation, review and release policy.

## Repetitions and uncertainty

Use at least three independent attempts per task for an exploratory comparison. Report per-task distributions and missing attempts. Larger claims require more tasks, domain experts, uncertainty intervals and a preregistered analysis. Do not infer model superiority from one run or a tiny score difference.

## Human review

Use two reviewers when possible. Resolve rubric disagreements without showing system identity. Preserve original scores and adjudication notes. Reviewers assess only the supplied response and fixture; they must not reward unsupported external knowledge.
