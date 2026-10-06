# Hyperion Steward

**A Hyperion agent for the HYPER-AI IDE that only tells you something happened once it has seen it happen.**

Veles Hack 2026, Challenge 1 (HYPER-AI: *Hyperion, an LLM-powered agentic assistant*). Drop-in replacement for the
official `hyperion-starter`: same `POST /chat` contract, same `API_KEY`, same default model server.

## The problem we found in the shipped IDE

We read the code of the IDE the judges run (`donmichael/ide-gui:latest`, `donmichael/ide-backend:latest`), not
only its tutorial. Three facts shape everything Steward does:

1. **Actions are fire-and-forget.** The GUI starts each streamed action and never tells the agent the result. When
   an action fails, the only trace is a line in the IDE status log.
2. **Plenty of actions fail silently.** A bare file name shared by two files does nothing (the tutorial says "first
   match"; the shipped GUI refuses). `create_file` on an existing path does nothing. If the IDE tab is closed,
   nothing runs at all.
3. **Nothing checks a profile unless someone asks.** The validator exists (`/api/agent/validation/file`), but a
   profile with `isHighlyAvailable: no` (a string under YAML 1.2) or an unquoted `schemaVersion: 1.1` is saved as is.

So a straightforward agent says "Deleted app.yaml" or "Created your profile" when nothing happened, or saves
something the IDE will reject.

## What Steward does

| Situation | Steward |
|---|---|
| Any change to the workspace | Sends the action, then **reads the workspace back** through the IDE backend. It says "done" only when it saw the change; otherwise it says it could not confirm it. The next action on that file waits for the previous one to land. |
| Writing a profile | Checks it first with an **exact port of the IDE's own validator** (0 disagreements with the original on 5,536 test documents), writes it, waits until the file is visible, then asks the IDE validator. If the IDE still rejects it, the file is rolled back. |
| A name that matches several files | Looks it up first (the backend answers 409) and asks which one, listing every path. |
| Overwrite, delete | Keeps a restore point. Deletions ask first. `undo` restores the exact bytes. |
| A profile that is valid but will not run | Says so: the official cookbook's native example starts `uvicorn` inside an `nginx` image. Steward checks the image against the entry point, the listen port against the exposed ports, the workload against the architecture, and more. |
| New profiles from plain language | The model extracts parameters; a deterministic builder emits the full profile, so the model never hand-writes 40 typed fields. Every builder output passes the real validator with no warnings. |
| Questions about HYPER-AI | Answers from the official documents (tutorial, cookbook, D3.3/D4.2/D4.3 deliverables), with citations. |
| Questions about anything else | Declined politely before any model call, so off-topic requests cost no tokens. |

## Evaluation criteria, and where each is proven

| Criterion (Challenge 1) | How Steward meets it | Evidence |
|---|---|---|
| Working `/chat` microservice in Docker, answers HYPER-AI questions and turns language into IDE actions | `POST /chat`, SSE `response` and `action` events, `data: [DONE]`, CORS for the browser GUI | `tests/test_contract.py`; CI builds the image, smoke-tests it, and runs it **against the official backend image** (`check <file>.yaml` answered by the real validator) |
| Guardrails reject irrelevant queries | Deterministic topical guard before the model | `tests/test_guardrail.py`; scenario N6 |
| RAG grounded in HYPER-AI docs | BM25 over the official document set, HYPER-AI spelling normalised, cited `[n]` | `steward/docs/`, scenario N8 ("What is HyperAI?") |
| Session memory | Per-`user_id` history and journal, bounded to the 8k context of the provided model | `tests/test_behaviour.py` |
| Optional: human confirmation for delete/overwrite | Built in, plus restore points and undo | `tests/test_tools_through_agent.py`, ablation S1 to S5 |

## Proof

| Claim | Evidence | Class |
|---|---|---|
| Local profile checks agree exactly with the IDE validator | [`evidence/validator-parity/PARITY.json`](evidence/validator-parity/PARITY.json): 5,536 documents, 0 disagreements. CI job `real-ide` repeats it with the code inside the official image. | LOCAL; CI: LIVE image |
| End-to-end against the real backend: create, ambiguity 409, invalid profile stopped, delete with confirmation, undo | [`evidence/live-slice/`](evidence/live-slice/): 6/6 steps, every change verified by read-back, undo restored identical bytes. GUI behaviour replicated from its source. | LOCAL backend source; CI: LIVE image; GUI PARTIAL |
| Safety layer is what makes the difference | [`evidence/ablation/ABLATION.md`](evidence/ablation/ABLATION.md): 9 scenarios, identical tool calls. Acceptable outcomes: naive 1/9, validator-only 1/9, Steward 9/9. False success claims: 5, 5, 0. Invalid files left: 2, 2, 0. | TECHNICAL, stub mirroring the shipped IDE |
| In the official IDE, with a real model, from a browser | [`evidence/gui-model/`](evidence/gui-model/): official GUI and backend images, llama3.1 8B, Chromium typing into the Hyperion panel: 7/7 (one answer came from the cited docs fallback after a CPU-runner timeout; see the README there). Recording included. | LIVE images in CI; model on Ollama |
| Runs on the organisers' model server (legion1, llama3.1) | Defaults point there; the organiser runs the image with his own key | Not measured before submission |

What is real and what is not is kept in [`docs/REALITY-LEDGER.md`](docs/REALITY-LEDGER.md).

## Run it

```bash
docker run -p 8000:8000 --add-host host.docker.internal:host-gateway \
  -e API_KEY=<team key> \
  faadil12/hyperion:latest
```

Defaults match the starter: model server `https://legion1.di.uoa.gr/v1`, model `llama3.1`, IDE backend
`http://host.docker.internal:3001/api`. Or `docker compose up` with a `.env` holding `API_KEY=`.

| Variable | Default | Purpose |
|---|---|---|
| `API_KEY` | empty | Team key for the organisers' model server |
| `OPENAI_BASE_URL`, `STEWARD_MODEL` | legion1, `llama3.1` | Any OpenAI-compatible server (Ollama, vLLM...) |
| `STEWARD_PROVIDER` | `openai_compatible` | `anthropic` (needs `ANTHROPIC_API_KEY`) or `none` |
| `IDE_BACKEND_URL` | `http://host.docker.internal:3001/api` in Docker | Where the IDE backend is |

With no reachable model, Steward still answers from the docs, runs `check <file>.yaml` and `undo`, and refuses to
write. Without Docker: `pip install -r requirements.txt && python main.py`.

`GET /receipts/<user_id>/view` shows a session's timeline: lookups, guard decisions, actions, read-back results,
validator calls, model calls with tokens and latency, restore points.

## Try these in the Hyperion panel

- `Create a deployment YAML for a service using the nginx Docker image`
- `What is HyperAI?`
- `check cookbook/native.yaml` with the cookbook native example, then `Fix it so it runs`, then `undo`
- `delete app.yaml` with two `app.yaml` files in the workspace
- `What's the weather in Valencia?`

## How it is built

```
IDE panel --SSE--> app.py --> agent.py (guardrail, model, tools) --> engine.py SafeOps --> IDE actions
                                 |                                     | lookup, confirmation, restore points,
                                 |                                     | read-back verification, validator, rollback
                                 +-- retrieval.py (official docs)      +-- hyperai_schema.py (port of the IDE validator)
                                 +-- guardrail.py (topic scope)        +-- runnability.py   (will it actually run)
                                 +-- llm.py (OpenAI-compatible,        +-- templates.py     (parameters to profile)
                                     Anthropic, none)
```

The model handles language. Everything that touches the workspace goes through `SafeOps`, whatever the model says.

## Project records

[PRD](docs/PRD.md) · [Autonomy log](AUTONOMY-LOG.md) · [Reality ledger](docs/REALITY-LEDGER.md) · [Challenge reality](docs/CHALLENGE-REALITY.md) · [Gateway registry](docs/CONDITIONAL-GATEWAY-REGISTRY.yaml)

## AI use disclosure

Built by Claude (Anthropic) as the autonomous arm of a build benchmark run by Faadil Boussari, who acted only on
identity, account and submission steps. Steward runs on the organisers' model by default.

## License

Apache-2.0. See [LICENSE](LICENSE).
