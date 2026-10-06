# Veles Hack 2026 — Challenge Reality Matrix

Status: QUALIFY (living). Each fact carries OBSERVED / INFERRED / UNKNOWN and its source.
Last update: 2026-10-06T10:10Z.

## 1. Timeline (OBSERVED — TAIKAI timeline page, UTC)

| Event | UTC | Toronto |
|---|---|---|
| Registration closed | 2026-10-05 21:59 | 17:59 |
| Introduction | 2026-10-06 07:00 | 03:00 |
| Hacking starts | 2026-10-06 08:00 | 04:00 |
| **Project submission deadline** | **2026-10-07 21:59** | **17:59** |
| Pitches | 2026-10-08 07:00 | 03:00 |
| Award ceremony | 2026-10-08 09:30 | 05:30 |

Internal submission safety boundary: **2026-10-07 19:00 UTC** (3 h before deadline). See AUTONOMY-LOG D-000.

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

## 4. Rules, judging, deliverables

| Item | State | Note |
|---|---|---|
| Rules page text | UNKNOWN | TAIKAI renders client-side; fetchers return shell only; workspace egress to taikai.network blocked; Browserbase errored; built-in browser not connected. |
| Judging criteria | UNKNOWN | Not published on any reachable page. |
| Deliverables (repo/video/deck) | UNKNOWN | aicompetition.dev lists "working solution for chosen challenge" (aggregator, INFERRED only). |
| License requirement | UNKNOWN | Sponsor code observed: aeriOS repos Apache-2.0. Product will use Apache-2.0 (compatible, Eclipse norm). |
| AI-use rules | UNKNOWN | Disclosure will be made in README regardless (benchmark protocol requires it). |
| Pre-existing code | UNKNOWN | Product is built from an empty repo created 2026-10-06T10:06Z; history proves in-event authorship. |

## 5. Sponsor resources discovered

| Resource | Track | Access from workspace | Class |
|---|---|---|---|
| ide-tutorial.hyperai.di.uoa.gr (Hyperion contract, DSL native + device, cookbook) | 1 | READ via web fetch | REFERENCE (official) |
| gitlab.eclipse.org/eclipse-research-labs/hyper-ai-project/hyperion-starter | 1 | BLOCKED (shell egress denied; robots.txt disallows fetchers) | REQUIRED if track 1 |
| ide.hyperai.di.uoa.gr (live IDE, login) | 1 | BLOCKED from shell | — |
| github.com/eclipse-aerios/iota-tangle, iota-messages-api, iota-tangle-peerer | 2 | GitHub reachable (public) | REFERENCE |
| ENACT CCC clusters | 3 | UNKNOWN credentials; organiser-hosted | — |
| CoGNETs auction boilerplate | 4 | NOT FOUND publicly yet | — |

## 6. Workspace constraints (OBSERVED, AUTONOMY-LOG D-004)

Reachable: npm, PyPI, api.anthropic.com, GitHub (session-scoped). Unreachable: TAIKAI, GitLab Eclipse, deploy-provider APIs, Docker Hub, sponsor hosts. No product LLM key in env.
