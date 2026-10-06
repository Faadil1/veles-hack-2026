# Live-model scenario rounds (product learning loop)

Setup: Steward full stack, LOCAL_STUB IDE, open models served by Ollama on a GitHub Actions runner through the
OpenAI-compatible adapter (no personal API key). 7 natural-language scenarios with deterministic checks
(`evaluation/scenarios.py`). Raw reports: branch `ci-evidence`, folder `scenarios/`.
Evidence class: BEHAVIOR on a stub IDE with small local models. These are not the models judges will use; the
rounds exist to find product bugs, and each fix is validated by the next round.

| Round | Code | qwen2.5:3b | qwen2.5:7b | What the round revealed | Fix shipped |
|---|---|---|---|---|---|
| 1 | 01feac2 | 2/7 | — | Guard blocked an ambiguous delete but the user got an empty reply; model passed a path to `check_profile`; hand-written YAML invented fields | Deterministic guard/confirmation messages; path-tolerant tools; `create_profile` builder (f8c8f3d) |
| 2 | f8c8f3d / 66b1d2f | 4/7, 4/7 | 5/7 | `create_profile` crashed on every call (TypeError, receipt keyword collision); docs answers skipped retrieval | Fix the bug class (positional-only `kind`); retrieval injected every turn; parse text-printed tool calls; agent-level test per tool (d063e1d) |
| 3 | d063e1d | 5/7 | 6/7 | Double confirmation: model asked "would you like me to…", then the overwrite guard asked again | Exact-path consent for overwrite (PRD v0.2); act-don't-ask rule (bc2dd1d) |
| 4 | bc2dd1d | 4/7 | 3/7 (invalid) | 7B: every model call hit the 90 s adapter timeout (all scenarios ~90.0 s) after retrieval-by-default enlarged prompts on a CPU runner; Steward fell back to degraded mode. Infrastructure-limited, not a quality score. 3B: N5 still fails | Timeout configurable (`STEWARD_LLM_TIMEOUT`, 300 s in CI); injected passages trimmed (k=2, 900 chars) |


### Rounds with llama3.1:8b (the model family the organisers serve)

| Round | Code | Stub IDE scenarios | Official GUI + backend (browser) | What it revealed | Fix shipped |
|---|---|---|---|---|---|
| 5 | d6924d9 / 3e04a45 | 7/9, 6/9 (0 invalid files left, 0 unchecked edits) | 5/7 (07a7343), 4/7 (7f81593, one timeout) | N1/N9/M2: on create requests the model asked a clarifying question instead of acting. N5/M4: asked to fix a file, the model pasted an invented YAML and asked to confirm; "yes" then reached a Steward with nothing pending | Intent-first routing of action requests, field-level `edit_profile` tool, "nothing pending" note, plain-text output (D-031, 2e62095) |

Safety outcome: rounds 1–4 did not record final-workspace safety metrics, so no safety claim is made for them
beyond the pass/fail checks above. From round 5 each report records, per scenario: files changed that were not
targeted, spec-invalid files left in the workspace, and actions emitted without a confirmed lookup.
