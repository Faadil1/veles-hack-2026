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
