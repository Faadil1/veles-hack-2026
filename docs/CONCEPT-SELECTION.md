# Track and Concept Selection (QUALIFY → DECIDE)

Date: 2026-10-06 ~10:40Z. Owner: Claude (autonomous arm). Evidence classes: OBSERVED / INFERRED / UNKNOWN.

## 1. Track comparison

Selection formula (from the brief): real user value × differentiation × challenge fit × demonstrable technical depth × probability of finishing cleanly.

| Track | Contract evidence available to me | Live infra reachable | Non-commodity potential | Kill / keep |
|---|---|---|---|---|
| 1 Hyperion (HYPER-AI) | **High, OBSERVED**: public tutorial documents request/SSE schema, 5 IDE actions, `read_file` and `validate_file` backend endpoints, full Native + Device DSL specs, cookbook. Starter on Eclipse GitLab (not fetchable by my tools). | IDE backend runs locally per the docs (`localhost:3001`) — needs the starter. LLM key needed. | Platform-native mechanisms observed in the contract (see §3). | **KEEP — selected** |
| 2 Trust Ledger (O-CEI) | Medium: aeriOS Tangle Helm/Docker repos and a publish-only API (`POST /upload`, `{tag, message}`) on GitHub. Read/search path undocumented. | Organiser Tangle unreachable; private Tangle needs Docker Hub images (blocked here). | Dashboard over a ledger is a familiar pattern; encryption angle is real but read path is UNKNOWN. | KILL (fallback #1 if Track 1 blocks) |
| 3 K8s Adaptation (ENACT) | Low: SDK/APM on Eclipse GitLab; live clusters organiser-hosted; Eclipse IDE + Java/Go. | No path to organiser clusters from this workspace. | High in principle, unverifiable here. | KILL — technical reality fails for this workspace |
| 4 Edge Auctions (CoGNETs) | **None**: no public boilerplate, auction-server API or scoring rules found. | UNKNOWN. | High (game theory is not LLM-commodity). | KILL for now — building against an unseen API risks total mismatch. Revisit only if its contract surfaces cheaply. |

Prize structure is identical per track (EUR 500 / 250), so the decision rests on build quality, not prize size. Participant counts per track: UNKNOWN (TAIKAI not readable). INFERRED: the LLM track is likely the most crowded, which raises the bar for differentiation rather than ruling it out.

## 2. Contrastive / winner signal

- Veles 2026 is the first edition (OBSERVED: "first joint HYPER-AI Hackathon"). No within-event winner/non-winner controls exist → contrastive signal **N/A_WITH_REASON**.
- Nearest Eclipse precedent: Eclipse SDV Hackathon 2025 published its criteria as usability, creativity and coding aspects (REFERENCE_ONLY; different event). Used as calibration, not as rubric.

## 3. AI Commodity Test (Track 1)

- **Event horizon:** ~36 h of build time.
- **What a capable AI-assisted builder reproduces easily:** an SSE chat agent with tool calls mapped to the five actions plus doc RAG. Commodity exposure for that baseline: **HIGH**.
- **What remains hard to copy — observed in the sponsor's own contract:**
  1. **First-match destructive actions (OBSERVED).** `delete_file`, `edit_file`, `delete_folder` accept a bare name and the IDE "uses the first match". `read_file` on the same ambiguous name returns **409 with all matches**. A naive agent can delete or overwrite the wrong file. The contract gives exactly the signal needed to prevent it.
  2. **`edit_file` replaces the whole file (OBSERVED).** No diff, no undo in the action set. An agent that reads before writing can keep a restore point.
  3. **Schema-valid is not runnable (OBSERVED in the official cookbook).** The native "Hello World" example declares `containerImage: nginx` with `entryPoint: uvicorn main:app` (nginx images do not ship uvicorn) and `securityLevel: "high"` while the spec defines `securityLevel` as a string "1–3". The backend validator checks schema; it cannot know an image/entrypoint mismatch.
  4. **The backend validator is a live oracle (OBSERVED).** `GET /api/agent/validation/file` returns line/column errors. It can be load-bearing in a generate → validate → repair loop.
- **Advantage class:** platform-native advantage + proprietary mechanism. Status: **OBSERVED in documentation; runtime verification PENDING** (needs the IDE backend). Concept Lock evidence readiness is therefore **conditionally satisfied** and must be re-verified at the first live run (Technical Reality Check).

## 4. Five concept lanes (Track 1)

| Lane | Idea | Verdict |
|---|---|---|
| L1 Obvious | Chat + 5 tools + RAG | Baseline / control only (commodity) |
| L2 Validated author | Intent → DSL profile; write only after the IDE validator passes; repair loop on line-level errors | Core |
| L3 Safe hands | Ambiguity guard (409 → ask, never first-match), read-before-write restore points, `undo` that re-creates prior content | Core |
| L4 Workspace auditor | Scan all profiles, explain and fix spec violations | Folded into L2 as a command |
| L5 Bold: "valid but won't run" | Semantic runtime checks the validator cannot do (image vs entrypoint, ports vs protocol, arch vs device, QoS sanity), shown as a pre-deploy verdict | Core differentiator |

## 5. Concept Lock (provisional until Technical Reality Check)

**Product:** a Hyperion agent whose promise is *"it never leaves your HYPER-AI workspace worse than it found it."*

- Every write is schema-valid according to the IDE's own validator, or it is held as a draft with the exact errors.
- Every destructive or overwriting action is unambiguous (409-guarded) and reversible (restore point + `undo`).
- Every generated profile gets a runnability verdict beyond the schema.
- Questions about HYPER-AI are answered from the official docs with citations, or explicitly declined when the docs are silent.

**Obvious-alternative sentence:** Most teams will build a chat agent that maps intents to the five IDE actions. We build the one that refuses to delete the wrong file, refuses to save an invalid profile, and can undo what it did, because the IDE contract itself makes those failures easy.

**Sponsor removal test (planned):** without the IDE backend there is no validator oracle, no file resolution, no actions → the product has no core value. Load-bearing by construction.

**Causal Mechanism Assurance:** TRIGGERED (guard/validator/undo are the differentiator). Ablation plan: A = naive agent (first-match delete, write-then-hope), B = schema validator only, C = full guard + validator + runnability + undo, on a fixed scenario workspace with duplicate filenames and a cookbook-style broken profile.

## 6. Open dependencies (human-bound, minimal)

1. Hyperion starter (Eclipse GitLab; my fetchers are refused by robots.txt and I do not route around that).
2. An LLM API key for the agent's model calls.
3. Official rules/judging text from TAIKAI (client-rendered, account-gated).
