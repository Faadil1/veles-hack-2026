# Post-Vertical-Slice Depth Gap Review

Date: 2026-10-06T15:43Z. First live slice: d6924d9 (official backend image, 6/6). Reviewed against the five official
criteria and the judge path (organiser runs `faadil12/hyperion:latest` with his own `API_KEY`, the official GUI and
backend, and types the example requests).

| Area | Depth now | Gap found | Action | Status |
|---|---|---|---|---|
| Criterion 1, answers | Retrieval over tutorial, cookbook, D3.3/D4.2/D4.3; "What is HyperAI?" answered in the official GUI by llama3.1 8B | Answer quality on legion1 not measured | Optional legion1 run if the team key is in CI | OPEN (optional) |
| Criterion 1, NL to actions | Official create example works with and without a model; file opens in the editor (GUI behaviour) | 8B model hesitated or invented YAML (D-031) | Intent-first routing, `edit_profile` | CLOSED in code; live re-run pending |
| Criterion 2, guardrails | Deterministic, before any model call | Borderline topics (e.g. general Kubernetes questions) are let through by design | Keep: bias to helpfulness inside the platform domain | ACCEPTED |
| Criterion 3, RAG | BM25 + aliases + heading boost; citations | No embeddings; the provided server offers nomic-embed-text | Hybrid retrieval would need the key at runtime and adds a failure mode on the judge path | DEFERRED (risk > gain before freeze) |
| Criterion 4, memory | Per `user_id`; deterministic turns now recorded too (D-031); trimmed to 8k | GUI generates a new `user_id` per page load, so memory resets on reload | Inherent to the GUI; documented | ACCEPTED |
| Criterion 5, HITL | Delete always confirmed; overwrite confirmed unless the exact path was named; restore points; undo | — | — | CLOSED |
| Fire-and-forget actions | Read-back after every action; unconfirmed changes reported as such | Timing with a real GUI under load | gui-e2e and gui-model runs measure it in the browser | CLOSED (observed in CI) |
| Packaging | Image on Docker Hub (2e62095), wired test against the official backend | Username needed for the README and the message to the organiser | Asked the human | OPEN (human) |
| Demo | Browser screenshots and recording from CI | Model-driven recording on a CPU runner is slow (minutes per turn) | 8x time-lapse; live demo on legion1 is faster | OPEN |
