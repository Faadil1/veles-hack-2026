# Engineering quality receipt

Date: 2026-10-06T16:43Z. Runtime revision d00df7b. ENGINEERING-QUALITY-ASSURANCE-POLICY (pinned canon).

| Check | Result |
|---|---|
| Tests | 103 passing locally and in CI (unit, contract, behaviour, agent-level per tool, real-IDE semantics, validator port, intents, ablation regression) |
| Static analysis (correctness) | `ruff --select F,B`: clean on steward/, evaluation/, tests/, stub_ide/ |
| Static analysis (style) | 40 non-functional findings (e.g. RUF100, C405, FURB188) accepted as debt; no correctness rule involved |
| Secrets | No key in the image or repo; `.env` ignored; `API_KEY` read from the environment only |
| Container | python:3.12-slim, non-root user, healthcheck, only steward/ and requirements copied |
| Network exposure | CORS open by design (the official GUI calls :8000/chat from the browser); no auth by design of the starter contract |
| Supply chain | Pinned requirements; CI builds from the repo; image carries its runtime revision label |
| Failure paths | Backend down, model down or slow, GUI closed, typo paths, ambiguous names: tested |
| Known debt | Internal receipt label `blocked_first_match` kept (renaming would change the runtime after verification); visible only in the receipts viewer |
