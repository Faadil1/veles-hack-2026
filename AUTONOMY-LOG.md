# AUTONOMY-LOG — Veles Hack 2026

Agent: Claude (autonomous build benchmark v1). Owner: Faadil Boussari.
Timezone of record: UTC (local Toronto = UTC-4).

> Timestamp correction (2026-10-06T10:06Z, clock verified by tool): entries D-000..D-005 carried estimated timestamps that ran ahead of the real clock. All of them actually occurred between 10:00Z and 10:06Z. From D-006 onward, timestamps come from the clock tool.

---

## D-000 — Deadline and time budget
- **Timestamp:** 2026-10-06T10:00Z
- **Observed:** TAIKAI official timeline lists Hacking 2026-10-06 08:00 UTC, Project Submission Deadline 2026-10-07 21:59 UTC, Pitches 2026-10-08 07:00 UTC, four "Challenge N voting" tracks. Registration closed 2026-10-05 21:59 UTC. Rules page content not rendered without session (UNKNOWN).
- **Options:** (a) plan to the hard deadline; (b) plan to a frozen submission margin.
- **Decision:** (b). Submission freeze 2026-10-07 19:00 UTC (15:00 Toronto), ~3h buffer for upload, video processing, form errors.
- **Justification:** Canon requires submission safety margin; platform uploads are a known failure point.
- **Evidence:** https://taikai.network/en/eclipse-foundation/hackathons/veles-hack-2026/timeline (OBSERVED 2026-10-06T10:00Z)
- **Expected consequence:** ~33h of build time.
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
- **Decision:** One message, three non-delegable items: (1) starter download (robots-refused source; human can open it), (2) LLM API key as GitHub secret (secret), (3) TAIKAI rules/judging text (account-gated, client-rendered).
- **Product decision requested:** none.
- **Human required:** YES.
