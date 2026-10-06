# AUTONOMY-LOG — Veles Hack 2026

Agent: Claude (autonomous build benchmark v1). Owner: Faadil Boussari.
Timezone of record: UTC (local Toronto = UTC-4).

> Timestamp correction (2026-10-06T10:06Z, clock verified by tool): entries D-000..D-005 carried estimated timestamps that ran ahead of the real clock. All of them actually occurred between 10:00Z and 10:06Z. From D-006 onward, timestamps come from the clock tool.

---

## D-000 — Deadline and time budget
- **Timestamp:** 2026-10-06T10:00Z
- **Observed (at ~10:00Z):** TAIKAI timeline listed Hacking 2026-10-06 08:00 UTC, Project Submission Deadline 2026-10-07 21:59 UTC, Pitches 2026-10-08 07:00 UTC, four "Challenge N voting" tracks. Registration closed 2026-10-05 21:59 UTC. Rules page content not rendered without session (UNKNOWN).
- **Options:** (a) plan to the hard deadline; (b) plan to a frozen submission margin.
- **Decision:** (b). ~~Submission freeze 2026-10-07 19:00 UTC~~ **SUPERSEDED by D-015: deadline 2026-10-07 14:59 UTC, freeze 2026-10-07 11:59 UTC.** 3 h buffer for upload, video processing, form errors.
- **Justification:** Canon requires submission safety margin; platform uploads are a known failure point.
- **Evidence:** https://taikai.network/en/eclipse-foundation/hackathons/veles-hack-2026/timeline (OBSERVED 2026-10-06T10:00Z)
- **Expected consequence:** ~~~33h~~ superseded by D-015 (~25 h to freeze from 10:47Z).
- **Reversible:** yes (margin can tighten only if submission is already validated).
- **Human required:** YES, limited: confirm TAIKAI account registration status (registration closed). Not a product decision. Work continues in parallel.

---

## D-001 — Order of work
- **Timestamp:** 2026-10-06T10:05Z
- **Decision:** Read canon (baseline 61f853a + benchmark branch + repository packet) and official challenge sources before any track or concept choice.
- **Justification:** Explicit protocol rule; avoids inventing canon from prompt.
- **Reversible:** n/a. **Human required:** no.

---

## D-002 — Registration checkpoint resolved from canon
- **Timestamp:** 2026-10-06T10:25Z
- **Observed:** ROUND-1.yaml (benchmark branch, commit 9b1db87) records Veles as `SELECTED_AND_REGISTERED`, `registration_state: CONFIRMED_BY_HUMAN`, participant location Canada, online.
- **Decision:** Close the D-000 human checkpoint; no further registration request.
- **Evidence:** research/autonomous-build-benchmark/v1/ROUND-1.yaml. **Reversible:** n/a. **Human required:** no.

## D-003 — Canon access and pin
- **Timestamp:** 2026-10-06T10:20Z
- **Observed:** faadil-agent-system is private; attached via session repo scope and cloned. main HEAD = c4404a1 (advanced past pin). Baseline 61f853a present. Benchmark branch = baseline + 4 protocol files only (diff verified).
- **Decision:** Work from worktree pinned at 61f853a + benchmark overlay. Do not silently adopt main c4404a1; classify delta later only if material.
- **Evidence:** `git diff --stat 61f853a bench` = 4 files, research/ only. **Reversible:** yes. **Human required:** no.

## D-004 — Workspace egress reality (constrains concept and deploy choice)
- **Timestamp:** 2026-10-06T10:40Z
- **Observed (probe):** reachable: npm, PyPI, api.anthropic.com (direct), GitHub (session-scoped; can push to attached repos). NOT reachable from shell: taikai.network, gitlab.eclipse.org, Vercel/Render/Fly/Netlify/Cloudflare APIs, Docker Hub, GHCR, GitLab.com, HuggingFace, sponsor hosts (ide.hyperai.di.uoa.gr). GitHub repo creation: HTTP 403. No product LLM API key in env.
- **Consequences:** (a) sponsor starters must be read via web-fetch tools, file by file; (b) any track that needs live access to organiser-hosted infra (K8s clusters, aeriOS Tangle) cannot be exercised from this workspace; (c) deployment must go through GitHub (Actions/Pages) or a claude.ai Artifact, not a direct provider CLI; (d) a dedicated repo needs one human creation step.
- **Human required:** YES — create empty repo only (D-005).

## D-005 — Dedicated product repository
- **Timestamp:** 2026-10-06T10:42Z
- **Options:** (a) wait for Concept Lock to name repo; (b) request a neutral name now so the human step overlaps with research.
- **Decision:** (b). Name chosen autonomously: `Faadil1/veles-hack-2026` (public, empty, Apache-2.0 compatible). Product name can live in README; the repo name does not leak a concept.
- **Justification:** Repo creation is the only non-delegable blocker on the critical path; overlapping it with research saves wall-clock time.
- **Human required:** YES — `HUMAN_REQUIRED: create/authorize dedicated Veles product repository`.

- **Observed consequence (10:06Z):** human created `Faadil1/veles-hack-2026` (empty). Attached with push access and cloned. Checkpoint closed.

---

## D-006 — Repository as source of truth
- **Timestamp:** 2026-10-06T10:08Z
- **Decision:** Seed repo with AUTONOMY-LOG, state/CURRENT.yaml, state/HANDOVER.yaml, docs/CHALLENGE-REALITY.md, docs/GATEWAY-REGISTRY.yaml before any product code. Work on `main` with small commits during research; branch per material build step once code exists.
- **Justification:** Canon continuity protocol (update after every material step; handover after milestones). Branch ceremony during pure research adds cost without assurance.
- **Reversible:** yes. **Human required:** no.

---

> Timestamp correction (clock-verified 10:15Z): D-007..D-010 below carry estimated times; they actually occurred between 10:08Z and 10:14Z. All later entries use `date -u`.

## D-007 — Track selection: Challenge 1 (Hyperion / HYPER-AI)
- **Timestamp:** 2026-10-06T10:40Z
- **Observed:** Track 1 has a fully documented public contract (SSE schema, 5 actions, read/validate endpoints, DSL specs). Track 2 read path undocumented and Tangle unreachable. Track 3 needs organiser clusters (unreachable) and Java/Eclipse IDE. Track 4 has no discoverable contract.
- **Options:** T1, T2, T3, T4.
- **Decision:** T1. Kill T3, T4 (technical reality); T2 kept as fallback #1.
- **Justification:** Only track where the sponsor mechanism can be load-bearing *and* specified from primary evidence today. Prize identical across tracks.
- **Evidence:** docs/CONCEPT-SELECTION.md §1; ide-tutorial.hyperai.di.uoa.gr pages.
- **Expected consequence:** crowded track → differentiation must come from platform-native mechanisms, not chat polish.
- **Reversible:** yes until first live run (fallback T2). **Human required:** no.

## D-008 — Concept lock (provisional): "never leaves the workspace worse"
- **Timestamp:** 2026-10-06T10:45Z
- **Observed:** contract hazards — first-match destructive actions, whole-file `edit_file`, cookbook example schema/runtime inconsistency, validator oracle available.
- **Options:** L1 generic chat agent; L2 validated author; L3 safe hands; L4 auditor; L5 runnability verdict.
- **Decision:** converge L2 + L3 + L5 (L4 folded in). L1 kept as ablation control.
- **Justification:** AI Commodity Test HIGH for L1; L2/L3/L5 rely on observed platform-native mechanisms. Causal Mechanism Assurance triggered; ablation A/B/C planned.
- **Evidence:** docs/CONCEPT-SELECTION.md §3–5.
- **Reversible:** yes; re-verify at Technical Reality Check (first live IDE run). **Human required:** no.

## D-009 — CI as live execution environment
- **Timestamp:** 2026-10-06T10:50Z
- **Observed:** GitHub Actions run 37448187481 succeeded on this repo. Job log download redirects to blob storage, which this workspace cannot reach.
- **Decision:** Use Actions for live checks needing secrets/egress; surface results via check-run annotations (readable through api.github.com). Keep the LLM key as a repo Actions secret, never in chat.
- **Boundary:** I will NOT use CI to clone Eclipse GitLab, because my fetch tools were refused by robots.txt and routing around that is out of bounds. The starter must come through the human.
- **Reversible:** yes. **Human required:** see D-010.

## D-010 — Bundled human checkpoint
- **Timestamp:** 2026-10-06T10:52Z
- **Decision:** One message, three non-delegable items: (1) starter download (robots-refused source; human can open it), (2) LLM API key as GitHub secret (secret) — **reclassified CONDITIONAL in D-016, request withdrawn**, (3) TAIKAI rules/judging text (account-gated, client-rendered).
- **Product decision requested:** none.
- **Human required:** YES.

---

## D-011 — Build the deterministic core before human dependencies land
- **Timestamp:** 2026-10-06T10:16Z
- **Observed:** starter, key and rules all pending human action.
- **Options:** (a) wait; (b) build framework-independent core (spec, runnability, guard, journal, SSE) against the documented contract plus a contract-faithful LOCAL_STUB.
- **Decision:** (b). HTTP layer mounts the plausible routes until the starter fixes the real one.
- **Result (10:24Z):** 31 tests passing; CI test job green on GitHub runner.
- **Reversible:** yes (adapter layer isolated). **Human required:** no.

## D-012 — Spec ambiguity handled as warning, not error
- **Timestamp:** 2026-10-06T10:20Z
- **Observed:** native spec says securityLevel "1–3"; device spec and the native cookbook example use "high".
- **Decision:** local checker warns; IDE validator decides. Avoids Steward blocking writes the platform accepts.
- **Reversible:** yes, once live validator behaviour is seen.

## D-013 — Ablation control made faithful after it flattered the baseline
- **Timestamp:** 2026-10-06T10:25Z
- **Observed:** first ablation run had the naive arm treat a 409 as "absent" and create a new file, which under-counted naive damage in S2.
- **Decision:** naive/validator-only arms now edit whenever the name exists (as the real first-match IDE would). S7 models the realistic case where only the backend API is unreachable.
- **Result:** A 1/7, B 1/7, C 7/7 acceptable; files damaged or lost A=4, B=4, C=0. Finding: validator-only does not reduce damage; guard + journal carry the value.
- **Evidence:** evidence/ablation/ (TECHNICAL_PROOF, LOCAL_STUB, scripted tool calls).
- **Reversible:** n/a. **Human required:** no.

## D-014 — CI ordering: smoke-test before publishing
- **Timestamp:** 2026-10-06T10:26Z
- **Observed:** first CI image job pushed, then failed the smoke test (exit 125, image not loaded locally).
- **Decision:** build+load, smoke-test in degraded mode, push only on success.
- **Reversible:** yes.

---

## D-015 — Deadline correction (binding)
- **Timestamp:** 2026-10-06T10:47Z (clock-verified)
- **Observed:** human reported the official timeline as Submission Deadline 2026-10-07 14:59 UTC, Pitches 2026-10-08 07:30 UTC. Re-fetched TAIKAI timeline at 10:46Z: **"10/7/2026 02:59 PM – Project Submission Deadline", "10/8/2026 07:30 AM – Pitches", "10/8/2026 10:00 AM – Award Ceremony"** (UTC). My 10:00Z fetch had returned 09:59 PM / 07:00 AM / 09:30 AM for the same three rows. Both observations are real; the published value changed or was mis-rendered earlier. The current, human-confirmed value binds.
- **Decision:** official_deadline = **2026-10-07T14:59Z**; internal submission freeze = **2026-10-07T11:59Z** (3 h margin kept). All occurrences corrected in AUTONOMY-LOG, state/CURRENT.yaml, state/HANDOVER.yaml, docs/PRD.md, docs/CONDITIONAL-GATEWAY-REGISTRY.yaml, docs/CHALLENGE-REALITY.md, docs/CONCEPT-SELECTION.md, docs/PROJECT-CONTROL-PLANE.yaml.
- **Consequence:** ~28 h to deadline, ~25 h to freeze from 10:47Z. Plan re-cut below. The freeze lands at 07:59 Toronto, so the human submit step must be scheduled for that morning.
- **Lesson:** a deadline read once from a client-rendered page is not stable evidence. Re-verify the deadline at every milestone and before the freeze, and treat any change as binding toward the earlier value.
- **Reversible:** only toward an earlier deadline. **Human required:** no.

## D-016 — LLM key reclassified as CONDITIONAL dependency
- **Timestamp:** 2026-10-06T10:47Z
- **Observed:** no evidence yet that a personal key is needed. The starter, official rules or organiser resources may provide a model endpoint (UNKNOWN). Steward already runs without a model (degraded deterministic mode), and the model sits behind an interface.
- **Decision:** withdraw the key request. Status `CONDITIONAL_DEPENDENCY`. A key is requested only if all three hold: (1) no hackathon-provided model/resource fits; (2) the chosen live path truly needs an external provider; (3) the secret's location is decided (Actions secret vs. runtime env of the judge-run container).
- **Valid human checkpoints now:** (1) hyperion-starter ZIP; (2) authenticated TAIKAI Rules / Categories / FAQs and relevant Challenge 1 announcements.
- **Engineering consequence:** make the model provider pluggable (Anthropic, OpenAI-compatible endpoint such as an organiser-provided or local server), selected by env, so whatever the starter specifies can be adopted without redesign.
- **Reversible:** yes. **Human required:** no.

## D-017 — Plan re-cut to the corrected clock
- **Timestamp:** 2026-10-06T10:48Z
- **Plan (UTC):**
  - 10:48–14:00 Oct 6: provider-agnostic model layer; deepen core (multi-file awareness, explain/audit, intent-to-profile templates); scenario suite runnable with a real model.
  - On starter arrival: adapter + Technical Reality Check + first live vertical slice (top priority, preempts everything).
  - Oct 6 afternoon/evening: Post-Vertical-Slice Depth Gap Review and product exploitation loop.
  - Oct 7 00:00–06:00: Engineering Quality pass, clean-room run, Reality Ledger, Evidence Graph.
  - Oct 7 06:00–10:00: demo video, README, submission text, Q&A, Final Canonical Assurance.
  - **Oct 7 11:59: freeze.** 11:59–14:59 human submission window and receipt verification.

---

## D-018 — Exercise the language layer with an open local model in CI (no personal key)
- **Timestamp:** 2026-10-06T10:49Z
- **Observed:** D-016 removed the key request; the language layer was untested with any real model.
- **Options:** (a) wait for a key/organiser endpoint; (b) run an open model (Ollama) on the GitHub runner behind the OpenAI-compatible adapter.
- **Decision:** (b). Scenario suite N1–N7 with deterministic pass/fail checks; reports pushed to `ci-evidence` branch.
- **Boundary:** a 3B/7B local model is not the model judges will use. Results are BEHAVIOR evidence on the stub IDE, labelled as such, and are used to find product bugs, not to claim quality.
- **Reversible:** yes. **Human required:** no.

## D-019 — First live-model run: 2/7, safety held, two product bugs found
- **Timestamp:** 2026-10-06T10:56Z
- **Observed (qwen2.5:3b, code 01feac2):** N6, N7 pass; N1, N3, N4, N5 fail on model quality (invented YAML fields, misused tools); **N2: guard blocked the ambiguous delete correctly but the user received an empty reply** because the model said nothing. N3/N5: model passed a path to `check_profile`. No scenario caused workspace damage.
- **Decision:** (1) guard and confirmation questions are now emitted deterministically by Steward and end the turn; (2) `check_profile` accepts a path; tool descriptions sharpened; (3) `create_profile` (D-020) removes hand-written YAML from the model's job.
- **Evidence:** ci-evidence:scenarios/qwen2.5_3b-01feac2.json; fix commit f8c8f3d; tests 43 passing.
- **Lesson:** a safety mechanism whose user-facing message depends on the model is only half a safety mechanism.
- **Reversible:** yes. **Human required:** no.

## D-020 — Deterministic profile builder
- **Timestamp:** 2026-10-06T10:52Z
- **Observed:** hand-writing ~40 typed, unit-bearing fields is where models fail (N1).
- **Decision:** `create_profile` tool: model extracts parameters; `templates.py` emits a complete spec-correct profile with cookbook-aligned defaults visible in the YAML; still goes through SafeOps (validator, rollback).
- **Evidence:** tests/test_templates.py.
- **Reversible:** yes.
- **Next:** re-run scenarios on 3B and 7B with f8c8f3d to measure the delta (product learning loop: feedback → decision → shipped delta → observed result).

## D-021 — Second live-model round: fixes replicated, two more product bugs found
- **Timestamp:** 2026-10-06T11:06Z
- **Observed (code f8c8f3d / 66b1d2f):** qwen2.5:3b 4/7 on two independent runs (up from 2/7); qwen2.5:7b 5/7. N2 (silent guard) and N3 (path to check_profile) fixed on every model. N1 failed on every model; N4 failed on every model.
- **Root causes:** N1: `create_profile` crashed with a TypeError (receipt keyword collision, the same class as the earlier `kind=` bug) on every call; the builder unit tests never went through the agent, so they missed it. N4: the model answered from assumptions without calling `search_docs`.
- **Decision:** (1) fix the bug class, not the instance: `Session.receipt` takes `kind` positional-only; agent-level test for `create_profile`; (2) retrieval by default: top passages are injected into context every turn with [Dn] citations; (3) parse tool calls a local model prints as text, and never show that markup to the user; (4) CI report publishing retries with rebase (one report was lost to a concurrent push).
- **Evidence:** ci-evidence:scenarios/qwen2.5_3b-66b1d2f.json, qwen2.5_7b-f8c8f3d.json; fix commit d063e1d; tests 46 passing.
- **Lesson:** a passing unit test of a component is not evidence the agent can use it. Every tool needs at least one test through the agent loop.
- **Reversible:** yes. **Human required:** no.

## D-022 — Third live-model round and a human-boundary refinement (PRD v0.2)
- **Timestamp:** 2026-10-06T11:19Z
- **Observed (code d063e1d):** qwen2.5:3b 5/7 (N1, N4 now pass; N3 flipped to fail: variance at 3B), qwen2.5:7b 6/7. N5 failed on both: the model asked "would you like me to…?", the user said yes, then Steward's overwrite guard asked again; the scenario ended before the write. No damage in any run.
- **Options:** (a) leave double confirmation; (b) drop the overwrite confirmation; (c) treat an exact path named in the request as consent for overwriting that file, keep the restore point, keep deletions and bare names confirmed; plus tell the model to act rather than ask.
- **Decision:** (c). PRD bumped to v0.2 (material human-boundary change, per PBPD standard §12). Tests cover explicit path, bare name, and delete.
- **Evidence:** ci-evidence:scenarios/qwen2.5_3b-d063e1d.json, qwen2.5_7b-d063e1d.json; tests 57 passing; ablation unchanged (C 7/7, A/B 1/7).
- **Reversible:** yes. **Human required:** no.

## D-023 — Official starter received: align to the organiser contract
- **Timestamp:** 2026-10-06T12:51Z
- **Observed:** the human checkpoint delivered the starter ZIP, the Challenge 1 PDF, the official docx set and the TAIKAI rules/FAQ. Contract: `POST /chat {user_id, text}`, SSE `data: {"response"}` plus action events, optional `data: [DONE]`, CORS required (the GUI calls `http://localhost:8000/chat` from the browser), LLM server `legion1.di.uoa.gr/v1` (OpenAI-compatible, `llama3.1`, 8k context) with the per-team key in `API_KEY`, evaluation image `<dockerhub-user>/hyperion:latest`. Licence: Apache-2.0 (starter LICENCE).
- **Decision:** single `/chat` route, `[DONE]` terminator, CORS, organiser defaults for the model, `.env`/`main.py`/compose like the starter, 8192-token context budget, official docs ingested into retrieval, deterministic topical guardrail (criterion 2) before any model call.
- **Evidence:** commits a89fc88, 9109624; tests/test_contract.py, tests/test_guardrail.py.
- **Reversible:** yes. **Human required:** no.

## D-024 — Read the shipped IDE instead of trusting its documentation
- **Timestamp:** 2026-10-06T12:51Z
- **Observed:** the tutorial describes the IDE, but the judges run the images `donmichael/ide-backend:latest` and `donmichael/ide-gui:latest`. A CI recon job ran both and copied the backend source (server.js, validation/*.js) and the GUI bundle to `ci-evidence:recon/`.
- **Decision:** treat the shipped code as the contract, the tutorial as secondary.
- **Evidence:** ci-evidence:recon/ (ide-recon 7e5f45f). Assumption A-02 (409 on ambiguous names) confirmed in server.js `lookupAgentFile`.
- **Reversible:** yes. **Human required:** no.

## D-025 — Port the backend validator exactly and prove parity
- **Timestamp:** 2026-10-06T13:00Z
- **Problem:** `steward/spec.py` approximated the DSL from the tutorial pages. Several rules differed from the real validator (YAML 1.2 semantics: `yes`/`no` are strings and unquoted `1.1` is a number; `securityLevel` accepts any string; native `trustScore` is a string 1-5; `ports` only required once an entry exists; unknown fields are warnings).
- **Options:** (a) patch the approximation; (b) port the rule tables and engine line for line and test against the JavaScript original.
- **Decision:** (b). `steward/hyperai_schema.py` (Core 1.2 YAML loader, duplicate keys rejected, rule tables, implied ancestors, unknown-field warnings, workload block rule). `spec.check_profile` now delegates to it. Differential harness `evaluation/validator_parity.py`: 5,536 documents (cookbook, every builder output, every field deleted/retyped/out of range, YAML edge cases), **0 disagreements** with the backend's own validator run under Node. All four builders produce profiles the real validator accepts with no warnings.
- **Evidence:** evidence/validator-parity/PARITY.json (LOCAL, backend source under Node); CI job `real-ide` repeats it against the code inside the official image.
- **Consequence:** a profile Steward writes is never rejected by the IDE for a schema reason; the rollback path remains for anything else.
- **Reversible:** yes. **Human required:** no.

## D-026 — The shipped GUI contradicts the tutorial; correct our claims, find the real hazards
- **Timestamp:** 2026-10-06T13:03Z
- **Observed (GUI bundle index-RTP-3qes.js):** (1) for edit/delete the GUI uses the exact path, else the unique file ending in `/<name>`; zero or several matches is a no-op with a WARN in the status log. The tutorial's "first match" does not happen. (2) Actions are dispatched without `await`: fire-and-forget, concurrent, and the outcome never reaches the agent. (3) `create_file` on an existing path fails (backend 400). (4) The GUI also supports `write_yaml_to_editor` (not in the starter contract; unused).
- **Consequence for the product story:** our claim "a bare-name delete hits the first match" is false for the shipped IDE and is withdrawn everywhere. The real hazard is different and worse for users: an agent that cannot see the outcome reports "done" when nothing happened (ambiguous name, existing file, IDE tab closed).
- **Decision:** (1) after every action Steward reads the workspace back through the backend (`/agent/file`, `/files`) and only claims what it saw; the validator runs only after the change is visible (otherwise it would validate the old file); an unseen change is reported as unconfirmed. (2) LOCAL_STUB rewritten to mirror the shipped GUI and backend. (3) Ablation re-run with a "false success claims" metric: naive 1/9 acceptable and 5 false claims, validator-only 1/9 and 5, Steward 9/9 and 0. (4) Docs corpus gains an "observed behaviour" page so answers match the real IDE.
- **Live check (LOCAL, backend source):** live slice 6/6, 4/4 effects verified by read-back, real 409 observed, undo restored identical bytes.
- **Evidence:** tests/test_real_ide_semantics.py; evidence/ablation/ABLATION.md; evidence/live-slice/local-backend-source.json; commit d6924d9.
- **Reversible:** yes. **Human required:** no.

## D-027 — Key and Docker Hub become proven human dependencies
- **Timestamp:** 2026-10-06T13:01Z
- **Observed:** D-016's three conditions now hold: (1) the hackathon provides the model (legion1) and it suits the chosen path; (2) that path needs the per-team key; (3) the secret lives only in the container env `API_KEY` (never in the image) and, for CI live runs, in the repo secret `HYPERAI_API_KEY`. The evaluation image must be pushed to the team's Docker Hub account (account-owner action).
- **Decision:** HUMAN_REQUIRED request sent for `HYPERAI_API_KEY`, `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` as repo secrets. CI step pushes `<user>/hyperion:latest` and a SHA tag when the secrets exist and warns otherwise. Work continues without blocking.
- **Reversible:** yes. **Human required:** yes (secrets; later, sending the image tag to the organiser and the final submit).

## D-028 — Robustness when the evaluation container has no model
- **Timestamp:** 2026-10-06T13:12Z
- **Observed:** the Challenge PDF says the organisers run our image and test it; how `API_KEY` reaches the container is not stated (UNKNOWN). The starter excludes `.env` from the image.
- **Options:** (a) bake a key into the public image (rejected: leaks a secret); (b) assume a key; (c) make the canonical requests work without a model.
- **Decision:** (c) plus asking the human to confirm with the organisers. `steward/intents.py` parses the official example requests (create a profile for an image, delete, create folder) and runs them through the same SafeOps path. Questions fall back to cited documentation passages; guardrail, check and undo never needed a model.
- **Evidence:** tests/test_intents.py (official example creates a valid nginx.yaml with no model).
- **Reversible:** yes. **Human required:** a question to the organisers (how the key is injected at evaluation).

## D-029 — Browser end to end in the official IDE; plain text output
- **Timestamp:** 2026-10-06T13:20Z
- **Observed:** the official GUI shows agent text as is; `**` and backticks appeared literally in the panel (screenshot from the first browser run).
- **Decision:** strip emphasis marks and backticks at the single exit point; system prompt asks for plain text. CI job `gui-e2e` runs the official GUI and backend images with Chromium typing into the Hyperion panel: 4/4 deterministic steps. Workflow `gui-model-e2e` runs the same with llama3.1 8B (or legion1 once the key exists).
- **Evidence:** ci-evidence:gui-e2e/ (images sha256:a805e9d…, sha256:3b29068…).
- **Reversible:** yes. **Human required:** no.

## D-030 — Evaluation key provisioning resolved by the organiser
- **Timestamp:** 2026-10-06T13:25Z
- **Observed:** on Discord #challenge1_hyper-ai, Michael (organiser) answered the human's question: "I will use my key". The evaluation container receives the organiser's key, consistent with the starter's `API_KEY` variable.
- **Consequence:** no key is ever baked into the image (unchanged). The team key `HYPERAI_API_KEY` is no longer needed for evaluation; it remains useful only to test on legion1 from CI before the freeze (optional). Docker Hub credentials remain HUMAN_REQUIRED (account-owner action). The deterministic intent fallback (D-028) stays as a safety net, not the main path.
- **Evidence:** screenshot of the Discord thread provided by the human (2026-10-06 09:18 local).
- **Reversible:** n/a. **Human required:** Docker Hub secrets; optional team key.

## D-031 — First runs in the official GUI with llama3.1 8B: diagnose and re-route actions
- **Timestamp:** 2026-10-06T15:45Z
- **Observed (official GUI + backend images, llama3.1:8b on Ollama CPU):** run 07a7343 5/7; run 7f81593 4/7 (step M1 hit the 420 s limit while video recording slowed the CPU runner). Passing: off-topic refusal, "What is HyperAI?" grounded answer, ambiguous delete (real 409), undo. Failing in both runs: (M2) on the official example "Create a deployment YAML for a service using the nginx Docker image" the model asked "which architecture?" instead of acting; (M4/M5) asked to fix cookbook/native.yaml, the model pasted an invented YAML into the chat and asked to confirm, then on "yes" (nothing pending in Steward) it asked what to build. No workspace damage in any step.
- **Root cause:** an 8B model is unreliable at deciding to act and at re-emitting whole profiles; the conversational "yes" refers to a model-side proposal that Steward never registered.
- **Options:** (a) prompt tuning only; (b) route unambiguous action requests deterministically before the model, and give the model a field-level `edit_profile` tool instead of whole-file rewrites; (c) both.
- **Decision:** (c). Intent-first routing for create (image named), fix (path + stated facts), delete, create folder: same SafeOps path, no model call, deterministic text that is also written to session memory. New `edit_profile` tool (dotted fields). A "yes"/"no" with nothing pending reaches the model with a note to act now. Prompt forbids pasting profiles as proposals. Model suite step M5 now tests memory ("Which container image did you just put in that file?").
- **Evidence:** tests/test_intents.py (official create example and fix request run without calling the model; undo restores bytes); tests/test_tools_through_agent.py (edit_profile). 100 tests.
- **Expected consequence:** M2 and M4 pass independent of model quality; latency for actions drops from minutes (CPU 8B) to about a second.
- **Reversible:** yes. **Human required:** no.

## D-032 — Evidence push failed on a 110 MB recording
- **Timestamp:** 2026-10-06T15:45Z
- **Observed:** the gui-model publish step failed: the raw WebM (110.64 MB) exceeds GitHub's 100 MB limit. A pre-fix live-model publish (workflow of d6924d9) had also wiped other evidence folders again; they were restored from their commits (0a0c8ec, d02b9e2, 6b07870, e9c26e7).
- **Decision:** transcode the recording in CI to an 8x time-lapse MP4 at 1280 px (libx264, crf 30), delete the WebM, refuse any file over 90 MB before pushing.
- **Reversible:** yes. **Human required:** no.

## D-033 — Re-run in the official GUI after D-031: 7/7
- **Timestamp:** 2026-10-06T16:30Z
- **Observed (2e62095, official images, llama3.1:8b Ollama CPU):** 7/7. Action steps (create, ambiguous delete, fix, undo) now take 3 to 5 s instead of minutes. Memory question answered by the model from session history. Caveat recorded, not hidden: "What is HyperAI?" hit the 300 s model timeout on the CPU runner and was answered by the cited documentation fallback; the same step passed with the model in 07a7343. Recording published as an 8x time-lapse (1 MB).
- **Evidence:** evidence/gui-model/ (copied from ci-evidence:gui-model, commit 2e62095). Docker Hub image pushed at 2e62095 (digest sha256:c2c1d6fc…).
- **Reversible:** n/a. **Human required:** Docker Hub username for the README, deck and organiser message.
