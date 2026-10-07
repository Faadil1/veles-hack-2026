# Reality Ledger: what is real today

Updated: 2026-10-07T08:27Z. Labels: LIVE · LOCAL · LOCAL_STUB · PARTIAL · SIMULATED · NOT_IMPLEMENTED; OBSERVED · INFERRED · UNKNOWN.

"Real backend source" means server.js and validation/ copied out of `donmichael/ide-backend:latest` by CI recon and
run under Node (LOCAL). "Official image" means `docker run donmichael/ide-backend:latest` in CI (LIVE image, CI runner).

| Capability | State | Evidence | Gap |
|---|---|---|---|
| `/chat` SSE contract (`response`, `action`, `[DONE]`, CORS) as in the official starter | LIVE in CI container and in the official GUI | tests/test_contract.py; CI smoke test; ci-evidence:gui-e2e, gui-model | — |
| Container talks to the real backend over `host.docker.internal` | LIVE (CI, official image sha256:3b29068…) | CI run 37468245981, commit d6924d9: `check ci/hello.yaml` answered "IDE validator: valid" by the official backend | — |
| Exact IDE validator rules | LIVE (validator code from the official image), OBSERVED parity | evidence/validator-parity/ci-official-image-d6924d9.json: 5,536 docs, 0 disagreements | — |
| Ambiguity: backend 409 with matches | LIVE (official image) | evidence/live-slice/ci-official-image-d6924d9.json (L3) | — |
| GUI action semantics (fire-and-forget, exact or unique-suffix resolution, create fails on existing) | OBSERVED in GUI source; LIVE in the official GUI (browser in CI) | recon GUI bundle; stub_ide; ci-evidence:gui-e2e | — |
| Read-back verification of every action | LIVE: official backend image (live slice) and official GUI in a browser (gui-e2e, published-image) | live slice: 4/4 effects verified; tests/test_real_ide_semantics.py; evidence/published-image/d00df7b-438f8bf/ | Timing under heavy load not measured |
| Validator loop with rollback | LOCAL_STUB (scripted ablation) for rejections (forced); real validator accepts every profile Steward writes | ablation S3; parity | A real-validator rejection after a passing local check cannot occur for schema reasons by construction |
| Confirmation, restore points and `undo` | Deletions always confirmed; overwrites confirmed unless the exact path was named or Steward created the file in this session; file create/edit/delete keep a restore point. LIVE backend: undo restored identical bytes | live slice L5/L6; tests | Folder deletion is confirmed but not reversible |
| Runnability verdict | TESTED (rules); cookbook native example flagged | tests | Runtime failure of the cookbook example is INFERRED, not run on HYPER-AI |
| Profile builder | LOCAL: all builder outputs pass the real validator with no warnings | tests/test_validator_port.py; parity | — |
| Docs Q&A with citations | LIVE in the official GUI with llama3.1 8B (Ollama): "What is HyperAI?" answered from the deliverables; k=3 on d00df7b 3/3 (one via the cited docs fallback after a CPU timeout) | evidence/reliability/LEDGER.yaml; evidence/published-image/d00df7b-438f8bf/ | Quality on the organiser's server not measured before submission; he runs the image with his own API_KEY (D-030) |
| Topical guardrail | TESTED | tests/test_guardrail.py; N6 | — |
| Language layer with a real model | LIVE in the official GUI (CI) with llama3.1 8B on Ollama: k=3 21/21 on candidate d00df7b (baseline 2e62095 20/21; 5/7 and 4/7 before D-031); 7/7 on the clean-pulled image. Caveats: one M1 answer per three came from the cited docs fallback after a CPU timeout; one memory answer added an untrue aside (strict truth 2/3, ACCEPTED_RISK) | evidence/reliability/LEDGER.yaml; evidence/published-image/d00df7b-438f8bf/ | The organiser runs the image with his own API_KEY (D-030); quality on his server not measured. The team key is optional |
| Evaluation image `faadil12/hyperion:latest` on Docker Hub | LIVE, clean-pull VERIFIED: digest sha256:438f8bfab6da59254fbcd7361a0fe6e707620c3d05445edc582d793b04268afb, revision label d00df7b63dcf8aca7e11fdb72572b6cfe40b975c (= last runtime commit). Behind the official GUI and backend images, driven by a browser: 4/4 without a model, 7/7 with llama3.1 8B. CI no longer re-pushes while the runtime revision is unchanged | evidence/published-image/d00df7b-438f8bf/; workflow published-image | — |
| Production use | Not claimed | | Out of scope |
