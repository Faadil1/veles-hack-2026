# Reality Ledger: what is real today

Updated: 2026-10-06T15:50Z. Labels: LIVE · LOCAL · LOCAL_STUB · PARTIAL · SIMULATED · NOT_IMPLEMENTED; OBSERVED · INFERRED · UNKNOWN.

"Real backend source" means server.js and validation/ copied out of `donmichael/ide-backend:latest` by CI recon and
run under Node (LOCAL). "Official image" means `docker run donmichael/ide-backend:latest` in CI (LIVE image, CI runner).

| Capability | State | Evidence | Gap |
|---|---|---|---|
| `/chat` SSE contract (`response`, `action`, `[DONE]`, CORS) as in the official starter | LIVE in CI container and in the official GUI | tests/test_contract.py; CI smoke test; ci-evidence:gui-e2e, gui-model | — |
| Container talks to the real backend over `host.docker.internal` | LIVE (CI, official image sha256:3b29068…) | CI run 37468245981, commit d6924d9: `check ci/hello.yaml` answered "IDE validator: valid" by the official backend | — |
| Exact IDE validator rules | LIVE (validator code from the official image), OBSERVED parity | evidence/validator-parity/ci-official-image-d6924d9.json: 5,536 docs, 0 disagreements | — |
| Ambiguity: backend 409 with matches | LIVE (official image) | evidence/live-slice/ci-official-image-d6924d9.json (L3) | — |
| GUI action semantics (fire-and-forget, exact or unique-suffix resolution, create fails on existing) | OBSERVED in GUI source; LIVE in the official GUI (browser in CI) | recon GUI bundle; stub_ide; ci-evidence:gui-e2e | — |
| Read-back verification of every action | LIVE backend (official image), GUI replicated | live slice: 4/4 effects verified; tests/test_real_ide_semantics.py | Timing with the real GUI in a browser not measured |
| Validator loop with rollback | LOCAL_STUB for rejections (forced); real validator accepts every profile Steward writes | ablation S3; parity | A real-validator rejection after a passing local check cannot occur for schema reasons by construction |
| Restore points and `undo` | LIVE backend (official image): undo restored identical bytes | live slice L5/L6 | — |
| Runnability verdict | TESTED (rules); cookbook native example flagged | tests | Runtime failure of the cookbook example is INFERRED, not run on HYPER-AI |
| Profile builder | LOCAL: all builder outputs pass the real validator with no warnings | tests/test_validator_port.py; parity | — |
| Docs Q&A with citations | LIVE in the official GUI with llama3.1 8B (Ollama): "What is HyperAI?" answered from the deliverables | ci-evidence:gui-model (07a7343) | Quality on the organiser's server not measured yet (optional team key) |
| Topical guardrail | TESTED | tests/test_guardrail.py; N6 | — |
| Language layer with a real model | OBSERVED: official GUI + llama3.1 8B (Ollama, CPU) 5/7 (07a7343) and 4/7 (7f81593, one step timed out). Failures: model asked a needless question on the create example; model pasted invented YAML instead of editing. Fixed by deterministic routing of action requests and an edit_profile tool (D-031); re-run pending | ci-evidence:gui-model; scenarios/llama3.1_8b-*.json | At evaluation the organiser injects his own API_KEY (D-030). Running on legion1 before the freeze is optional (team key not required) |
| Evaluation image `<user>/hyperion:latest` on Docker Hub | Secrets added by the human (2026-10-06 ~15:30Z); first push expected from the next CI run | ci.yml step "Push evaluation image to Docker Hub" | Confirm push and digest; human sends the tag to the organiser |
| Production use | Not claimed | | Out of scope |
