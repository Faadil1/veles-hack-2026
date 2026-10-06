# Veles Hack 2026: Challenge Reality Matrix

Status: QUALIFY (living). Each fact carries OBSERVED / INFERRED / UNKNOWN and its source.
Last update: 2026-10-06T13:35Z.

## 1. Timeline (OBSERVED — TAIKAI timeline page, UTC)

| Event | UTC | Toronto |
|---|---|---|
| Registration closed | 2026-10-05 21:59 | 17:59 |
| Introduction | 2026-10-06 07:00 | 03:00 |
| Hacking starts | 2026-10-06 08:00 | 04:00 |
| **Project submission deadline** | **2026-10-07 14:59** | **10:59** |
| Pitches | 2026-10-08 07:30 | 03:30 |
| Award ceremony | 2026-10-08 10:00 | 06:00 |

Internal submission freeze: **2026-10-07 11:59 UTC** (3 h before deadline). Corrected in AUTONOMY-LOG D-015: a fetch at ~10:00Z on 6 Oct showed 21:59 / 07:00 / 09:30 for these rows; the re-fetch at 10:46Z and the human's authenticated view show the values above, which bind.

## 2. Organisation and format (OBSERVED)

- Organiser: Eclipse Foundation (Research @ Eclipse), hosted at UPV Valencia, hybrid, remote via Discord. Source: TAIKAI overview; hyper-ai-project.eu event + news pages.
- Sponsors / challenge owners: four Horizon Europe projects — HYPER-AI, CoGNETs, ENACT, O-CEI.
- Teams 1–3, 18+, free. Registration: CONFIRMED (ROUND-1.yaml).
- Prizes: EUR 3,000 Amazon gift cards. **Per challenge:** winner EUR 500, runner-up EUR 250. Four separate voting tracks ("Challenge 1..4 voting") on TAIKAI. Source: hyper-ai-project.eu news.
- Pitches on 8 Oct; remote pitch format: UNKNOWN.

## 3. Tracks (OBSERVED — hyper-ai-project.eu event page)

| # | Owner | Challenge | Required tech (stated) | Skills stated |
|---|---|---|---|---|
| 1 | HYPER-AI | Hyperion: LLM agentic microservice for the HYPER-AI IDE (answer questions about HYPER-AI, control IDE, create/edit/delete files) | LLM, RAG, SSE, session memory | Python, Docker, LLM APIs |
| 2 | O-CEI | Trust Ledger Traceability: mechanism (e.g. dashboard) to inspect messages inserted into the aeriOS IOTA Tangle, search on demand, present results | Eclipse aeriOS, IOTA Tangle, encryption | APIs, DLT basics |
| 3 | ENACT | Kubernetes Dynamic Adaptation: deploy to live K8s clusters, runtime policies, adaptation | ENACT CCC, K8s/Helm | Java/Python/Go, Eclipse IDE |
| 4 | CoGNETs | Smart Edge Resource Auctions: dynamic node registration, game-theory bidding agents competing for resources | Auction mechanisms | Python, Docker, REST, JSON |

## 4. Rules, judging, deliverables (OBSERVED: TAIKAI rules and FAQ pasted by the human at 08:49 local; Challenge 1 PDF)

| Item | State | Source / note |
|---|---|---|
| Fresh code only, public GitHub/GitLab repo created at event start | OBSERVED | TAIKAI rules. Repo created 2026-10-06T10:06Z; full history in-event. |
| Licence file defined by the challenge | OBSERVED | Starter LICENCE is Apache-2.0; repo LICENSE is Apache-2.0. |
| Submission: repo link + brief README on TAIKAI; template deck | OBSERVED | VelesHack_ProjectSubmissionTemplate.pptx (Project name, GitHub repo, Summary, Highlights). |
| Pitch | OBSERVED | 6 minutes, live, free format; independent jury. |
| Evaluation (Challenge 1) | OBSERVED | Organisers run `<dockerhub-user>/hyperion:latest` and test against 5 criteria: (1) /chat microservice answering HYPER-AI questions and turning NL into IDE actions, e.g. "What is HyperAI?" and "Create a deployment YAML for a service using the nginx Docker image" (writes the file and opens it in the editor); (2) guardrails reject irrelevant queries ("What is the weather today?"); (3) RAG on HYPER-AI docs; (4) memory within a session; (5) optional human-in-the-loop confirmation for delete/overwrite. |
| How the evaluation container gets its model key | UNKNOWN | Starter reads `API_KEY` from env (`.env` excluded from the image). Mitigation: deterministic intent fallback (D-028). Question for the organisers is a human action. |
| Prizes | OBSERVED | Per track 1st and 2nd. |
| AI-use rules | UNKNOWN | Disclosure in README regardless. |

## 5. Sponsor resources

| Resource | Access from workspace | Class |
|---|---|---|
| ide-tutorial.hyperai.di.uoa.gr (contract, DSL, cookbook) | READ via web fetch | REFERENCE (secondary to shipped code) |
| hyperion-starter | Received as ZIP from the human | REQUIRED, aligned (D-023) |
| donmichael/ide-backend:latest, donmichael/ide-gui:latest | Run in GitHub Actions (Docker Hub unreachable from the workspace) | CONTRACT (D-024); digests sha256:3b29068… and sha256:a805e9d… |
| legion1.di.uoa.gr/v1 (llama3.1, 8k context, OpenAI-compatible) | Unreachable from workspace; per-team key | REQUIRED for the judged model; HUMAN_REQUIRED key |
| Official docx set (D3.3, D4.2, D4.3), Hyperai.pdf | Received from the human | RAG corpus |

## 6. Workspace constraints (OBSERVED, AUTONOMY-LOG D-004)

Reachable: npm, PyPI, api.anthropic.com, GitHub (session-scoped), GitHub Actions (Docker Hub reachable there).
Unreachable: TAIKAI, GitLab Eclipse, Docker Hub, legion1, deploy providers.
