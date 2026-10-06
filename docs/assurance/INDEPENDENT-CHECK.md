# Independent read-only cross-check of the Final Canonical Assurance receipt

Date: 2026-10-06T16:45Z. Performed by a separate agent instance with no write access and no role in production,
reading the repository and the `ci-evidence` branch only.

| Item | Result |
|---|---|
| 1. Runtime binding (last runtime commit, revision label, digest) | PASS: d00df7b = last commit on Dockerfile/requirements.txt/steward; revision.txt and digest match the receipt |
| 2. Reliability recomputation from the three candidate runs | PASS on the declared rules (21/21). Truth review of replies: M5 run-3 contains an untrue aside; M5 run-1 is evasive but true |
| 3. Quoted numbers (5,536 / 0; 9/9 vs 1/9; 0 vs 5; 6/6; 7/7) | PASS, each traced to an evidence file |
| 4. Claims stronger than evidence | PASS, with a note: the ablation figures lacked the "stub" label in SUBMISSION.md and the deck |
| 5. Placeholders | PASS |
| 6. Log timestamps vs commit times (D-031..D-037) | PASS |

## Discrepancies and how they were handled

| Severity | Finding | Action |
|---|---|---|
| Medium | M5 run-3 untrue aside passed the substring grader | Recorded in LEDGER.yaml (strict truth 2/3, still meets the declared 2-of-3), receipt limitation added, classified ACCEPTED_RISK (no workspace effect). Grader not loosened |
| Low-Medium | README linked evidence from the older runtime 2e62095 | README now points to the published-image and k=3 evidence of d00df7b; the older recording is labelled with its runtime |
| Low | CASES.yaml candidate field named the declaration-time runtime | Annotated: declared against 2e62095; candidate after D-037 is d00df7b |
| Low | M1 run-3 took 305.6 s vs a 300 s timeout | Consistent with the documented fallback; no change |
| Low | Ablation figures not labelled as stub-based in SUBMISSION.md and the deck | Labels added |
