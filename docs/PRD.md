# Hyperion Steward — Product Requirements Document

Version: `0.2`
Status: `PRD_VALIDATED_WITH_OPEN_DEPENDENCIES` (see §19)
Project ID: `veles_hack_2026`
Date: `2026-10-06`
Owner: PBPD role, executed by Claude (autonomous benchmark arm)
Authorization source: `faadil-agent-system@9b1db87:research/autonomous-build-benchmark/v1/ROUND-1.yaml` (SELECTED_AND_REGISTERED)
Standard: `pbpd-cowork-system@ff035d8 PRD-PREBUILD-STANDARD v1.1`

> This PRD cannot expand authority beyond the authorization artifact. Final submission stays human.

---

## 1. Product summary

Hyperion Steward is the Hyperion agentic microservice for the HYPER-AI IDE (Veles Hack 2026, Challenge 1). It answers questions about HYPER-AI from the official documentation and acts in the IDE (create, edit, delete files and folders) through the IDE's own action stream. Its promise: **it never leaves your workspace worse than it found it.** Every profile it writes passes the IDE's own validator or stays a labelled draft; every overwrite or deletion is unambiguous and reversible; every generated profile gets a runnability verdict that goes beyond the schema.

## 2. Target user / stakeholder

- **Primary user:** a developer or operator using the HYPER-AI IDE to describe and deploy Native Apps or Device Apps (container, Android APK, ESP32) to the continuum.
- **Secondary:** HYPER-AI maintainers (fewer support questions, fewer broken deployments); Veles judges (HYPER-AI challenge owners).

## 3. Job-to-be-done

> When I need to deploy a workload on HYPER-AI, I want to describe it in plain language and get a profile that the platform accepts and that will actually run, without risking the files already in my workspace.

## 4. Problem / evidence

Problem: application profiles are long, strictly typed YAML documents with many required, unit-bearing fields. Getting them right is error-prone, and the IDE's agent action contract makes destructive mistakes easy.

| Evidence | Class |
|---|---|
| Device App spec requires ~25 fields across `spec.app`, `network`, `qos`, `constraints`, `sensors`, many with value/unit objects and enums. | FACT (ide-tutorial `/dsl/devices/`) |
| Native App spec requires ~15 fields with typed strings ("2000m", "10Gi"). | FACT (ide-tutorial `/dsl/native-apps/`) |
| `delete_file`, `edit_file`, `delete_folder` act on the **first match** of a bare name. `read_file` on an ambiguous name returns 409 with all matches. | FACT (ide-tutorial `/hyperion-agent/`) |
| `edit_file` replaces the whole file; there is no undo action. | FACT (same page) |
| The official Native "Hello World" cookbook example sets `securityLevel: "high"` while the spec defines it as a string "1–3", and pairs `containerImage: nginx` with `entryPoint: uvicorn main:app`. | FACT for the document content (ide-tutorial `/cookbook/`); the runtime failure of that pairing is INFERENCE (nginx images ship no Python/uvicorn). |
| Users actually lose files or ship broken profiles because of this. | UNVERIFIED (no user data available). |

## 5. Goals

- G1 — A user goes from a plain-language request to a schema-valid profile in the workspace in one conversation turn when the request is complete.
- G2 — No destructive or overwriting action ever lands on a file the user did not unambiguously mean.
- G3 — Any change made by Steward can be reverted with one request.
- G4 — Questions about HYPER-AI are answered with citations to the official docs, or declined when the docs are silent.

## 5A. Product Reality / workflow evidence

Pain / friction: hand-authoring strictly typed profiles; silent wrong-file edits by an agent; schema-valid profiles that will not run.

Frequency / recurrence: every new workload needs a profile; edits recur on each change. Exact frequency UNKNOWN (no usage data).

| Dimension | Current consequence | Evidence / truth class |
|---|---|---|
| Time | Iterating validator errors by hand | INFERENCE |
| Cost | Failed deployment cycles on the continuum | INFERENCE |
| Risk | Wrong-file overwrite/delete by first-match resolution | FACT (contract) / impact INFERENCE |
| Quality | Schema-valid but non-runnable profiles reach deploy | FACT (cookbook example) / impact INFERENCE |

Real workflow:

```text
developer
→ wants to deploy workload W
→ opens IDE, writes YAML from docs/cookbook (or asks Hyperion)
→ validator errors / or valid-but-wrong profile
→ deploy → workflow fails at runtime
→ [INTERVENTION: Steward generates, validates against the IDE, checks runnability, writes safely]
→ schema-valid, runnability-checked profile in workspace, with restore point
```

Tacit knowledge / exceptions:
- Known rules: name-only paths resolve to first match; `path` relative to workspace root, never absolute or `..`; Docker-hosted agent must call `host.docker.internal:3001`.
- Exceptions: `device_name` omitted means scheduler picks; Android needs a registered device name.
- Unknown: whether the validator also checks semantic consistency; how the IDE sequences streamed actions vs. backend file visibility (race risk). To discover at first live run.

## 5B. Baseline / AI advantage / routing

- **Current/manual baseline:** user copies a cookbook example and edits by hand, then iterates against validator errors.
- **Simpler deterministic alternative:** a form wizard (the IDE already has one: "New App Profile" wizard). Steward does not replace it; it covers natural-language intent, edits to existing files, cross-file questions and safety for agent actions.
- **AI advantage hypothesis:** an LLM maps loose intent ("run my FastAPI image on an ARM edge device with < 200 ms latency") to the right DSL fields faster than form-filling, **but only becomes trustworthy when bounded by deterministic checks.** The deterministic guard, validator loop, runnability rules and journal carry the safety; the LLM carries the language.
- **Routing:**

| Dimension | Requirement / trade-off |
|---|---|
| Capability | Structured YAML generation, tool calling, doc-grounded answers |
| Latency | First streamed token < 2 s target; full profile turn < 20 s target |
| Cost | Measured per turn and shown in the receipts; default to a mid-tier model, allow override |
| Reliability | Deterministic checks gate every write; LLM failure degrades to an explicit error, never a silent write |
| Context | Official docs corpus (small), current file contents via `read_file`, session memory |

## 5C. Human boundary / production gap / moat

- **Judgment points:** ambiguous file target (409) → user chooses; deleting anything → confirm; overwriting a file Steward did not create in this session → confirm, **unless the user named that exact path in the current request** (explicit consent; restore point still kept, `undo` still works); a profile that fails the IDE validator is rolled back, never left over an existing file.
- **Protected actions:** deploying a workflow stays in the IDE UI (Deploy/Start buttons); Steward never deploys.
- **Production gap:** single-instance in-memory sessions; no auth beyond the IDE's user_id; no multi-user concurrency guarantees; validated only against the documented contract until the live IDE run.
- **Moat / learning hypothesis:** the runnability rule set and the failure catalogue grow from real validator responses and deploy outcomes. Model access is not the moat.

## 6. Non-goals

- NG1 — Deploying or starting workflows.
- NG2 — Replacing the IDE wizard.
- NG3 — Arbitrary shell or code execution.
- NG4 — Answering questions outside HYPER-AI beyond a short redirect.

## 7. Primary Path

```text
user (IDE panel): "Create a device app that runs my image ghcr.io/acme/sensor:1.2 on an arm64 edge node, 200 ms latency budget"
→ Steward streams a short plan (response events)
→ generates profile, checks it locally against the spec and runnability rules
→ create_file demo/sensor-app.yaml (action event)
→ calls validate_file → valid (or repairs with edit_file until valid, max N attempts)
→ streams verdict: schema VALID (IDE validator), runnability notes, restore point id
→ file is open in the editor; user can say "undo"
```

## 8. Hero Demo Moment

- **Start:** workspace with two files named `app.yaml` in different folders, plus a copy of the official cookbook native example.
- **Action:** user says "delete app.yaml", then "fix the hello-world profile".
- **Observable change:** Steward refuses the first-match delete and lists both paths (from the IDE's own 409); fixes the cookbook profile (securityLevel, entrypoint/image mismatch) and the IDE validator confirms it; "undo" restores the original.
- **Proof:** IDE validator responses and the Steward receipt log for the session.
- **Time budget:** < 90 s.
- **Reset path:** seed script recreates the starting workspace.

## 9. Functional requirements

### MUST

| ID | Requirement | Why | Acceptance evidence |
|---|---|---|---|
| MUST-01 | Accept `{user_id, text}` and stream SSE `data:` events with `response` text chunks and `action` objects exactly per contract | Challenge contract | Contract tests + live IDE run |
| MUST-02 | Support all 5 actions: create/delete folder, create/edit/delete file | Challenge | Tests per action |
| MUST-03 | Per-user session memory keyed by `user_id` | Challenge | Multi-turn test (pronoun resolution "undo that", "rename it") |
| MUST-04 | Answer HYPER-AI questions from the official docs with source citations; decline when not covered | Challenge (RAG) + truth | Q&A eval set with expected sources |
| MUST-05 | Ambiguity guard: before any name-based edit/delete, resolve via `read_file`; on 409 ask the user and never emit a first-match action | Contract hazard | Ablation scenario A vs C |
| MUST-06 | Restore points: read current content before `edit_file`/`delete_file`; `undo` re-creates it | No undo in contract | Undo tests incl. after delete |
| MUST-07 | Validator loop: after writing a profile, call `validate_file`; repair with bounded attempts; report errors with line numbers if still invalid | Load-bearing sponsor oracle | Live run against IDE backend |
| MUST-08 | Local spec check (native + device) before writing, so obviously invalid YAML never reaches the workspace | Avoid write-then-fix churn | Unit tests on spec rules |
| MUST-09 | Runnability verdict for generated/inspected profiles (rules beyond schema) | Differentiator | Rule unit tests incl. cookbook case |
| MUST-10 | Explicit failure behaviour: backend unreachable, LLM error/timeout → stream a clear message, emit no action | Failure safety | Fault-injection tests |
| MUST-11 | Runs as a Docker container using `host.docker.internal:3001` by default; configurable base URL | Contract | Container build in CI |

### SHOULD

| ID | Requirement | Why | Acceptance evidence |
|---|---|---|---|
| SHOULD-01 | Workspace audit command: validate all profiles and summarise | Depth | Test on seeded workspace |
| SHOULD-02 | Per-session receipt log (actions, validator calls, guard decisions, tokens, latency, cost) exposed on a read-only endpoint | Observability, economics | Receipt endpoint test |
| SHOULD-03 | Confirm before overwriting files not created in this session, unless the exact path was named in the request (v0.2) | Safety without double confirmation | tests/test_behaviour.py (explicit path, bare name, delete) |

### MAY

| ID | Requirement | Why | Acceptance evidence |
|---|---|---|---|
| MAY-01 | Read-only receipts viewer page | Judge self-serve | Screenshot + manual check |
| MAY-02 | Explain an existing profile field by field with spec links | Learning value | Q&A test |

### MUST_NOT

| ID | Forbidden behaviour / scope | Reason |
|---|---|---|
| MUST_NOT-01 | Emit a delete/edit with a bare name that resolves ambiguously | Wrong-file damage |
| MUST_NOT-02 | Overwrite an existing file with a profile that fails validation | Leaves workspace worse |
| MUST_NOT-03 | Claim a profile is valid without a validator response (or say "not checked") | Truth boundary |
| MUST_NOT-04 | Absolute paths or `..` in action paths | Contract |
| MUST_NOT-05 | Deploy/start workflows | Protected user action |

## 10. Non-functional requirements

| ID | Requirement | Metric / acceptance condition |
|---|---|---|
| NFR-01 | Reliability | No action emitted on any LLM/backend error path (tests) |
| NFR-02 | Reproducibility | `docker build` + one command run; tests run offline with the local IDE stub |
| NFR-03 | Latency | First SSE event < 2 s (measured); recorded per turn |
| NFR-04 | Safety / privacy | No secrets in repo/logs; only workspace-relative paths |
| NFR-05 | Maintainability | Typed modules; deterministic core separated from LLM orchestration; Engineering Quality receipt before terminal |

## 11. Success metrics

- **Primary outcome metric:** share of scenario-suite requests that end with the workspace in an *acceptable* state (intended change applied and validator-clean, or no change plus a correct clarification) — Steward (C) vs naive agent (A) vs validator-only (B), same model, same scenarios. Directional target: C strictly better than A and B on damage and invalid-write counts. Measurement context: local IDE stub first (TECHNICAL_PROOF), then the real IDE backend.
- **Supporting:** wrong-file actions (target 0), invalid files left in workspace (target 0), undo success rate (target 100% for Steward-made changes), doc-answer citation correctness on the Q&A set, first-token latency, cost per turn.
- **Stop threshold:** if C does not beat A on damage/invalid writes in the ablation, the differentiator claim is withdrawn.

| Proof class | Required? | Planned evidence |
|---|---:|---|
| TECHNICAL_PROOF | yes | unit/contract tests, ablation on stub |
| BEHAVIOR_PROOF | yes | live run in the real IDE (panel → actions visible) |
| OUTCOME_PROOF | partial | ablation counts on a fixed suite (lab conditions, labelled) |
| PRODUCTION_EVIDENCE | no | explicitly out of reach; limitation stated |

## 12. Acceptance criteria

Build-ready: Primary Path defined; MUST items have tests; killing assumptions A-01..A-04 tracked; human boundary explicit; production gap explicit. (Met except open dependencies in §19.)
Submission-ready: per FINAL-CANONICAL-ASSURANCE-POLICY; MUST verified or limitations explicit; Reality Ledger current.

## 13. Evidence plan

| Claim | Proof class | Artifact | Status |
|---|---|---|---|
| SSE/action contract compliance | TECHNICAL | `tests/test_contract.py` | PENDING |
| Ambiguity guard prevents wrong-file delete | TECHNICAL → BEHAVIOR | ablation report + live 409 receipt | PENDING |
| Validator loop is load-bearing | TECHNICAL → BEHAVIOR | live validator receipts; removal test | PENDING |
| Undo restores prior content | TECHNICAL | tests | PENDING |
| Runnability catches cookbook mismatch | TECHNICAL | rule test on official example | PENDING |
| Doc answers cite sources | TECHNICAL | Q&A eval | PENDING |
| Works inside the real IDE | BEHAVIOR | screen capture + receipts | BLOCKED (starter) |

## 14. Constraints

- Deadline: 2026-10-07 14:59 UTC (corrected, D-015); internal freeze 2026-10-07 11:59 UTC.
- Budget: LLM spend kept low; measured per turn.
- Tools: Python 3, FastAPI, httpx, pydantic, PyYAML; Docker image built in GitHub Actions.
- Environment: workspace cannot reach sponsor hosts; live runs need the starter + IDE backend (human-provided) or CI.
- Rules: UNKNOWN beyond the public challenge description (§19).

## 15. Authority / safety / protected actions

- Permitted: workspace file/folder actions through the IDE contract; read/validate calls.
- Prohibited: deploy/start, paths outside the workspace, secrets in logs.
- Human-gated: ambiguous targets, deletions, overwriting non-Steward files, final competition submission.

## 16. Killing assumptions

| ID | Assumption | Truth class | Test | Kill / pivot |
|---|---|---|---|---|
| A-01 | The IDE backend and validator run locally from the starter | ASSUMPTION | Starter README | If not runnable, live depth becomes PARTIAL; consider fallback Track 2 |
| A-02 | `read_file` 409 behaves as documented | FACT (docs) / live UNKNOWN | Live call with duplicate names | If not, guard switches to a workspace scan strategy |
| A-03 | Streamed actions become visible to the backend before the next `validate_file` call | UNKNOWN | Live timing test | If not, poll with bounded backoff |
| A-04 | An LLM is required for the language layer (vs. wizard) | HYPOTHESIS | Scenario suite: free-text intents | If wizard covers it, Steward's value narrows to guard + audit |

## 17. Risks

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| R-01 | No starter / no live IDE before deadline | High | Contract-faithful local stub (labelled LOCAL_STUB); honest PARTIAL claim |
| R-02 | No model endpoint available for the live language path | High | Provider-agnostic layer (Anthropic or OpenAI-compatible, incl. organiser-provided/local); deterministic paths and degraded mode work without a model. Key is a CONDITIONAL dependency (D-016) |
| R-03 | Starter imposes a different framework/endpoint | Medium | Keep core library independent of the HTTP layer |
| R-04 | LLM produces wrong YAML | Medium | Local spec check + IDE validator + bounded repair |
| R-05 | Crowded track | Medium | Differentiate on safety + validator loop, proven by ablation |

## 18. Dependencies

- External: HYPER-AI IDE backend (`/api/agent/file`, `/api/agent/validation/file`), IDE frontend action executor.
- Repository: hyperion-starter (Eclipse GitLab) — pending human download.
- Model/provider: CONDITIONAL. Prefer any model/resource the hackathon provides (starter/rules UNKNOWN); otherwise Anthropic or an OpenAI-compatible endpoint selected by env. A personal key is requested only under D-016's three conditions.
- Human: starter zip, authenticated rules text, final submission. (Model key: conditional, not requested.)

## 19. Open questions

- Q1 — Official judging criteria and deliverables (video? deck?). Pending human paste.
- Q2 — Starter's HTTP route name and framework. Pending starter.
- Q3 — Does the starter ship the IDE backend, or must agents target the hosted IDE? Pending starter.

None of these makes the core architecture arbitrary: the deterministic core is framework-independent. Consequential build of the core proceeds; the HTTP adapter is finalised when the starter arrives.

## 20. Completion boundary

PBPD ceiling: `BUILD_CANDIDATE_READY` or `BUILD_CANDIDATE_READY_WITH_LIMITATIONS`, then Project Finisher Final Canonical Assurance. Final submission: human. No production-evidence claim will be made.

## 21. Hackathon additions

- Rubric: UNKNOWN (Q1). Calibration only: Eclipse SDV 2025 judged usability, creativity, coding.
- Deliverables: UNKNOWN (Q1). Plan: public repo, README, Docker image, demo video < 3 min, short deck.
- IP/provenance: new repo created 2026-10-06T10:06Z; Apache-2.0; AI assistance disclosed in README.

## 22. Version history

| Version | Date | Change | Authority / reason | Impact |
|---|---|---|---|---|
| 0.1 | 2026-10-06 | Initial | Concept lock D-008 | — |
| 0.2 | 2026-10-06 | Human boundary: naming the exact path in a change request counts as consent to overwrite that file; deletions always confirm | Live-model scenario N5 showed double confirmation (model asked, then Steward asked again); D-022 | SHOULD-03 refined; I4 invariant text updated |
