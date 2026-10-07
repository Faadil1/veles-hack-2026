# Final handover: Hyperion Steward (Veles Hack 2026, Challenge 1)

Status at 2026-10-07T09:06Z: **SUBMITTED (reported by the owner; organiser message sent, TAIKAI submitted).** Deadline 2026-10-07 14:59 UTC; internal freeze
2026-10-07 11:59 UTC. Pitches 2026-10-08 07:30 UTC.

## What exists

| Item | Where | State |
|---|---|---|
| Product | `steward/`, `main.py`, `Dockerfile` | `/chat` SSE microservice, starter-compatible |
| Evaluation image | Docker Hub `faadil12/hyperion:latest` | sha256:438f8bfa…, runtime revision d00df7b; clean pull verified 4/4 (no model) and 7/7 (llama3.1 8B); kept stable until the runtime changes |
| Tests | `tests/` | 103 passing, CI green |
| Live evidence | `evidence/`, branch `ci-evidence` | Official GUI + backend images, browser-driven; k=3 with llama3.1 8B 21/21 on d00df7b; validator parity 0/5,536; live slice 6/6 |
| Final Canonical Assurance | `docs/assurance/FINAL-CANONICAL-ASSURANCE-RECEIPT.yaml` | SUBMISSION_READY, Finisher validator b5ea200 PASS; independent cross-check in `docs/assurance/INDEPENDENT-CHECK.md` |
| Submission PDF | `docs/pitch/Hyperion-Steward-Submission.pdf` (official 3-slide template + title) | Ready: attach on TAIKAI |
| Pitch deck (final round) | `docs/pitch/Hyperion-Steward-VelesHack.pptx` | Ready |
| Pitch script and Q&A | `docs/pitch/PITCH.md` | Ready |
| Submission text and organiser message | `docs/SUBMISSION.md` | Ready |
| Decisions | `AUTONOMY-LOG.md` D-000 to D-038 | Current |
| Truth labels | `docs/REALITY-LEDGER.md` | Current |

## Human steps (only these)

1. Send the organiser message in `docs/SUBMISSION.md` (image tag).
2. On TAIKAI before 2026-10-07 14:59 UTC: project associated with the Challenge 1 category, project text, repo link, `Hyperion-Steward-Submission.pdf` attached, Submit.
3. If shortlisted (notice around 17:00 UTC today), pitch on 2026-10-08 with the pitch deck and `docs/pitch/PITCH.md`.

## Known limits (stated in the README and deck)

- Any change to Dockerfile, requirements.txt or steward/ invalidates the assurance receipt: re-run k=3, published-image and the receipt.
- Memory answers from the 8B model can include untrue asides (1 of 3 runs); no workspace effect.
- The 9/9 vs 1/9 ablation is a scripted LOCAL_STUB experiment mirroring the shipped IDE; the live evidence is separate.
- Folder deletion is confirmed but not reversible; overwrites skip confirmation when the exact path was named or Steward created the file in this session.
- Answer quality on the organiser's legion1 server not measured before submission (he injects his own key).
- Runnability findings are rules, not a deployment on HYPER-AI.
- On a CPU runner the 8B model can exceed the 300 s CI timeout; Steward then answers from cited documents.
- The GUI generates a new `user_id` per page load, so session memory resets on reload.

## Clean-room verification

Clean pull of faadil12/hyperion:latest (sha256:438f8bfa…, revision d00df7b) behind the official IDE images,
browser-driven: 4/4 without a model, 7/7 with llama3.1 8B (evidence/published-image/d00df7b-438f8bf/).


Fresh clone of 5fea8f8: install, 97/97 tests, official example created and undone against the real backend source
with no model (LOCAL). CI rebuilds and tests the image on every commit and runs it against the official backend image.

## Build provenance

Built by Claude (Anthropic) as the autonomous arm of AUTONOMOUS_BUILD_BENCHMARK_V1_ROUND_1, run by Faadil Boussari,
who acted only on identity, account and submission steps. Full decision record: `AUTONOMY-LOG.md` (D-000 onward).
The public README carries a short development note instead of a dedicated disclosure section (D-040).
