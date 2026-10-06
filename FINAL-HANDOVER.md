# Final handover: Hyperion Steward (Veles Hack 2026, Challenge 1)

Status at 2026-10-06T16:45Z: **SUBMITTABLE, pending human steps.** Deadline 2026-10-07 14:59 UTC; internal freeze
2026-10-07 11:59 UTC. Pitches 2026-10-08 07:30 UTC.

## What exists

| Item | Where | State |
|---|---|---|
| Product | `steward/`, `main.py`, `Dockerfile` | `/chat` SSE microservice, starter-compatible |
| Evaluation image | Docker Hub `faadil12/hyperion:latest`, pushed by CI on every push to main | First push 2e62095 (sha256:c2c1d6fc…) |
| Tests | `tests/` | 100 passing, CI green |
| Live evidence | `evidence/`, branch `ci-evidence` | Official GUI + backend images, browser-driven, llama3.1 8B: 7/7; validator parity 0/5,536; live slice 6/6 |
| Deck | `docs/pitch/Hyperion-Steward-VelesHack.pptx` (official template) | Ready |
| Pitch script and Q&A | `docs/pitch/PITCH.md` | Ready |
| Submission text and organiser message | `docs/SUBMISSION.md` | Ready |
| Decisions | `AUTONOMY-LOG.md` D-000 to D-033 | Current |
| Truth labels | `docs/REALITY-LEDGER.md` | Current |

## Human steps (only these)

1. Send the organiser message in `docs/SUBMISSION.md` (image tag).
2. Submit on TAIKAI before 2026-10-07 14:59 UTC: project text, repo link, deck.
3. Pitch on 2026-10-08 with `docs/pitch/PITCH.md`.

## Known limits (stated in the README and deck)

- Answer quality on the organiser's legion1 server not measured before submission (he injects his own key).
- Runnability findings are rules, not a deployment on HYPER-AI.
- On a CPU runner the 8B model can exceed the 300 s CI timeout; Steward then answers from cited documents.
- The GUI generates a new `user_id` per page load, so session memory resets on reload.

## Clean-room verification

Fresh clone of 5fea8f8: install, 97/97 tests, official example created and undone against the real backend source
with no model (LOCAL). CI rebuilds and tests the image on every commit and runs it against the official backend image.
