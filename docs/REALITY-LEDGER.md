# Reality Ledger: what is real today

Updated: 2026-10-06T10:55Z. Labels: LIVE · TESTED · LOCAL_STUB · SIMULATED · PLANNED · NOT_PROVEN.

| Capability | State | Evidence | Gap to LIVE |
|---|---|---|---|
| SSE request/response contract (`user_id`, `text`, `response`, `action`) | TESTED | tests/test_contract.py; CI container smoke test | Real IDE panel not yet connected |
| Five IDE actions emitted with workspace-relative paths | TESTED (LOCAL_STUB) | tests/test_behaviour.py | Real IDE execution not observed |
| Ambiguity guard (409 → ask, no first-match action) | TESTED (LOCAL_STUB) | tests, ablation S1/S2 | Real backend 409 behaviour not observed (assumption A-02) |
| Restore points and `undo` | TESTED (LOCAL_STUB) | tests, ablation S5 | Real IDE re-create after delete not observed |
| Validator loop with rollback | TESTED (LOCAL_STUB, stub validator = Steward's own spec checks + forced rejections) | tests, ablation S3 | Real HYPER-AI validator not called yet; action/backend visibility timing unknown (A-03) |
| Local DSL checks (native + device) | TESTED against official cookbook examples | tests/test_spec_runnability.py | Spec ambiguities (securityLevel wording) resolved only by live validator |
| Runnability verdict | TESTED (rule unit tests; official cookbook native example flagged) | tests | Runtime failure of the cookbook example is INFERRED, not observed on HYPER-AI |
| Docs Q&A with citations | TESTED (retrieval); language answers depend on model | retrieval tests via degraded mode; scenario N4 | Corpus partly summarised by fetch tool (marked per file) |
| Language layer with a real model | PENDING first CI report | .github/workflows/live-model.yml (open local model) | Quality with the judges' model unknown |
| Deterministic profile builder | TESTED | tests/test_templates.py | Real validator acceptance not observed |
| Degraded mode (no model) | TESTED | tests; CI container smoke test | — |
| Container image | LIVE on GHCR (built, smoke-tested in CI) | ghcr.io/faadil1/hyperion-steward:<sha> | Package visibility may be private by default |
| Running inside the HYPER-AI IDE | NOT_PROVEN | — | Needs the hyperion-starter (human checkpoint) |
| Production use | NOT_PROVEN, not claimed | — | Out of scope |
