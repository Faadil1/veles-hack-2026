# Reality Ledger: what is real today

Updated: 2026-10-06T13:15Z. Labels: LIVE · LOCAL · LOCAL_STUB · PARTIAL · SIMULATED · NOT_IMPLEMENTED; OBSERVED · INFERRED · UNKNOWN.

"Real backend source" means server.js and validation/ copied out of `donmichael/ide-backend:latest` by CI recon and
run under Node (LOCAL). "Official image" means `docker run donmichael/ide-backend:latest` in CI (LIVE image, CI runner).

| Capability | State | Evidence | Gap |
|---|---|---|---|
| `/chat` SSE contract (`response`, `action`, `[DONE]`, CORS) as in the official starter | LIVE in CI container | tests/test_contract.py; CI smoke test | Not yet exercised by the real GUI in a browser |
| Container talks to the real backend over `host.docker.internal` | LIVE (CI, official image sha256:3b29068…) | CI run 37468245981, commit d6924d9: `check ci/hello.yaml` answered "IDE validator: valid" by the official backend | — |
| Exact IDE validator rules | LIVE (validator code from the official image), OBSERVED parity | evidence/validator-parity/ci-official-image-d6924d9.json: 5,536 docs, 0 disagreements | — |
| Ambiguity: backend 409 with matches | LIVE (official image) | evidence/live-slice/ci-official-image-d6924d9.json (L3) | — |
| GUI action semantics (fire-and-forget, exact or unique-suffix resolution, create fails on existing) | OBSERVED in GUI source; replicated | recon GUI bundle; stub_ide; evaluation/live_slice.GuiReplica | Real GUI in a browser not driven yet (PARTIAL) |
| Read-back verification of every action | LIVE backend (official image), GUI replicated | live slice: 4/4 effects verified; tests/test_real_ide_semantics.py | Timing with the real GUI in a browser not measured |
| Validator loop with rollback | LOCAL_STUB for rejections (forced); real validator accepts every profile Steward writes | ablation S3; parity | A real-validator rejection after a passing local check cannot occur for schema reasons by construction |
| Restore points and `undo` | LIVE backend (official image): undo restored identical bytes | live slice L5/L6 | — |
| Runnability verdict | TESTED (rules); cookbook native example flagged | tests | Runtime failure of the cookbook example is INFERRED, not run on HYPER-AI |
| Profile builder | LOCAL: all builder outputs pass the real validator with no warnings | tests/test_validator_port.py; parity | — |
| Docs Q&A with citations | TESTED retrieval; answers depend on model | scenarios N4, N8 | Judges' model quality UNKNOWN until the team key arrives |
| Topical guardrail | TESTED | tests/test_guardrail.py; N6 | — |
| Language layer with a real model | BEHAVIOR on open models (qwen2.5 3B/7B, llama3.1 8B) in CI, stub IDE | ci-evidence:scenarios/ | legion1 llama3.1 not called yet: needs the team key (HUMAN_REQUIRED) |
| Evaluation image `<user>/hyperion:latest` on Docker Hub | NOT_IMPLEMENTED until secrets exist; CI step ready | ci.yml | HUMAN_REQUIRED: Docker Hub account and token |
| Production use | Not claimed | | Out of scope |
