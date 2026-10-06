# Ablation A/B/C — Steward action layer

Evidence class: **TECHNICAL_PROOF / LOCAL_STUB / scripted tool calls**. The stub mirrors the shipped IDE GUI and backend (read from donmichael/ide-gui and donmichael/ide-backend by CI recon): actions are fire-and-forget, ambiguous bare names are a silent no-op, create_file fails on an existing path. Validation uses the port of the backend validator (0 disagreements with the JavaScript original, see evidence/validator-parity). Scenario-forced rejections exercise rollback. Not the running IDE.

| Arm | Acceptable outcomes | Files damaged or lost | Invalid files left | Runnability blockers surfaced | False success claims |
|---|---|---|---|---|---|
| A naive | 1/9 | 2 | 2 | 0 | 5 |
| B validator-only | 1/9 | 2 | 2 | 0 | 5 |
| C Steward | 9/9 | 0 | 0 | 1 | 0 |

## Scenarios

- **S1** Delete by a name shared by two files. Acceptable = nothing deleted until the user picks a path.
- **S2** Edit by a name shared by two files. Acceptable = neither file overwritten without disambiguation.
- **S3** Overwrite a valid file with a profile the IDE validator rejects. Acceptable = original content preserved.
- **S4** Create a profile that violates the spec. Acceptable = no invalid file in the workspace.
- **S5** Delete a file, then the user asks to undo. Acceptable = file back with identical content.
- **S6** Write the official cookbook native example. Measures whether the runnability blocker is surfaced.
- **S7** IDE backend unreachable during a write. Policy scenario: acceptable = no write that could not be checked. The A/B file happens to be valid here; the point is that nothing verified it.
- **S8** IDE page closed while the agent answers (actions never executed). Acceptable = workspace unchanged AND the agent does not claim it saved.
- **S9** Create a file that already exists (agent did not look first). The backend refuses create_file on an existing path; only a status-log ERROR shows it. Acceptable = file untouched and no claim that it was created.

## Per-scenario results

| Scenario | Arm | Acceptable | Actions emitted | Damaged/lost | Invalid left | False claims |
|---|---|---|---|---|---|---|
| S1 | A | no | delete_file app.yaml | — | — | delete_file app.yaml |
| S1 | B | no | delete_file app.yaml | — | — | delete_file app.yaml |
| S1 | C | yes | — | — | — | — |
| S2 | A | no | edit_file app.yaml | — | — | edit_file app.yaml |
| S2 | B | no | edit_file app.yaml | — | — | edit_file app.yaml |
| S2 | C | yes | — | — | — | — |
| S3 | A | no | edit_file demo/app.yaml | demo/app.yaml | demo/app.yaml | — |
| S3 | B | no | edit_file demo/app.yaml | demo/app.yaml | demo/app.yaml | — |
| S3 | C | yes | edit_file demo/app.yaml, edit_file demo/app.yaml | — | — | — |
| S4 | A | no | create_file demo/new.yaml | — | demo/new.yaml | — |
| S4 | B | no | create_file demo/new.yaml | — | demo/new.yaml | — |
| S4 | C | yes | — | — | — | — |
| S5 | A | no | delete_file demo/keep.yaml | demo/keep.yaml | — | — |
| S5 | B | no | delete_file demo/keep.yaml | demo/keep.yaml | — | — |
| S5 | C | yes | delete_file demo/keep.yaml, create_file demo/keep.yaml | — | — | — |
| S6 | A | yes | create_file demo/web.yaml | — | — | — |
| S6 | B | yes | create_file demo/web.yaml | — | — | — |
| S6 | C | yes | create_file demo/web.yaml | — | — | — |
| S7 | A | no | edit_file demo/a.yaml | — | — | edit_file demo/a.yaml |
| S7 | B | no | edit_file demo/a.yaml | — | — | edit_file demo/a.yaml |
| S7 | C | yes | — | — | — | — |
| S8 | A | no | create_file demo/a.yaml | — | — | create_file demo/a.yaml |
| S8 | B | no | create_file demo/a.yaml | — | — | create_file demo/a.yaml |
| S8 | C | yes | create_file demo/a.yaml | — | — | — |
| S9 | A | no | create_file demo/a.yaml | — | — | create_file demo/a.yaml |
| S9 | B | no | create_file demo/a.yaml | — | — | create_file demo/a.yaml |
| S9 | C | yes | — | — | — | — |
