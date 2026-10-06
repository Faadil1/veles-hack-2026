# Hyperion Steward

**The Hyperion agent for the HYPER-AI IDE that never leaves your workspace worse than it found it.**

Veles Hack 2026, Challenge 1 (HYPER-AI: *Hyperion, an LLM-powered agentic assistant*).

Ask it questions about HYPER-AI, or ask it to create, fix, or delete application profiles. It does the work through the IDE's own action stream, and it refuses the three mistakes the IDE contract makes easy:

| What can go wrong with a naive agent | What Steward does |
|---|---|
| `delete_file app.yaml` hits the **first** `app.yaml` in the workspace, not necessarily the one you meant. | Looks the name up first. If the IDE reports it as ambiguous (409), it lists every match and asks. It never sends a first-match action. |
| `edit_file` replaces the whole file and there is no undo action. | Reads the file before every edit or delete and keeps a restore point. `undo` puts it back exactly. |
| A profile can pass the schema and still never run. The official cookbook's native example starts `uvicorn` inside an `nginx` image. | Checks runnability beyond the schema (image vs entry point, listen port vs exposed ports, workload vs architecture, and more) and says so. |

Every profile it writes is checked by the IDE's own validator. If the validator rejects it, Steward rolls the file back to what it was.

## Proof so far

| Claim | Evidence | Class |
|---|---|---|
| Guard + journal prevent damage that naive and validator-only agents cause | [`evidence/ablation/ABLATION.md`](evidence/ablation/ABLATION.md): 7 scenarios, same tool calls. Acceptable outcomes: naive 1/7, validator-only 1/7, Steward 7/7. Files damaged or lost: 4, 4, 0. | TECHNICAL, on a contract-faithful stub IDE |
| Safety invariants hold on error paths (backend down, model down, path traversal, declined confirmation) | [`tests/`](tests) (40 tests, run in CI on every push) | TECHNICAL |
| A real language model drives the full stack from plain language | [`evaluation/scenarios.py`](evaluation/scenarios.py), run in CI on an open local model with no personal API key; reports on the `ci-evidence` branch | BEHAVIOR, on the stub IDE |
| Works inside the real HYPER-AI IDE | Not yet verified | PENDING |

What is real today, and what is not, is kept in [`docs/REALITY-LEDGER.md`](docs/REALITY-LEDGER.md).

## Run it

```bash
docker run -p 8000:8000 \
  -e IDE_BACKEND_URL=http://host.docker.internal:3001/api \
  -e STEWARD_PROVIDER=openai_compatible \
  -e OPENAI_BASE_URL=http://host.docker.internal:11434/v1 \
  -e STEWARD_MODEL=qwen2.5:7b \
  ghcr.io/faadil1/hyperion-steward:latest
```

Model provider, chosen by environment:

| `STEWARD_PROVIDER` | Needs |
|---|---|
| `openai_compatible` | `OPENAI_BASE_URL`, `STEWARD_MODEL`, optional `OPENAI_API_KEY`. Works with an organiser-provided endpoint, Ollama, vLLM, llama.cpp or a hosted API. |
| `anthropic` | `ANTHROPIC_API_KEY`, optional `STEWARD_MODEL` |
| `none` | Nothing. Steward still answers from the docs, runs `check <file>.yaml` and `undo`, and refuses to write. |

Without Docker:

```bash
pip install -r requirements.txt
IDE_BACKEND_URL=http://localhost:3001/api python -m steward.app
```

### The contract it speaks

`POST /chat` (also accepted on `/`) with `{"user_id": "...", "text": "..."}` returns `text/event-stream`:

```
data: {"response": "Creating edge/sensor-reader.yaml. "}
data: {"action": "create_file", "path": "edge/sensor-reader.yaml", "content": "apiVersion: hyper.ai/v1\n..."}
data: {"response": "The IDE validator reports it valid. Say undo to remove it."}
```

It reads and validates through the IDE backend (`GET /api/agent/file`, `GET /api/agent/validation/file`). Per-user memory is keyed by `user_id`. `GET /receipts/<user_id>` shows every lookup, guard decision, action, validator call, model call (tokens, latency) and restore point for a session.

## Try these in the Hyperion panel

- `Create a device app called sensor-reader that runs acme/sensor:1.2 on arm64 edge devices with a 200 ms latency budget, in edge/sensor-reader.yaml`
- `delete app.yaml` (with two `app.yaml` files in the workspace)
- `check native.yaml` (with the cookbook native example)
- `Fix it so it runs`, then `undo`
- `What does delete_file do if I only give a file name?`

## How it is built

```
IDE panel ──SSE──> app.py ──> agent.py (model + tools) ──> engine.py SafeOps ──> IDE actions
                                   │                          │   guard, confirmation, restore points,
                                   │                          │   validator loop, rollback
                                   ├── retrieval.py           ├── spec.py         (local DSL checks)
                                   │   (official docs, cited) ├── runnability.py  (will it actually run)
                                   └── llm.py                 └── templates.py    (parameters to full profile)
                                       (Anthropic / OpenAI-compatible / none)
```

The model handles language. Everything that can damage the workspace goes through `SafeOps`, which enforces its invariants whatever the model says.

## Project records

[PRD](docs/PRD.md) · [Concept selection](docs/CONCEPT-SELECTION.md) · [Autonomy log](AUTONOMY-LOG.md) · [Gateway registry](docs/CONDITIONAL-GATEWAY-REGISTRY.yaml) · [Challenge reality](docs/CHALLENGE-REALITY.md)

## AI use disclosure

This entry was built by Claude (Anthropic) as the autonomous arm of a build benchmark run by Faadil Boussari, who acted only on identity, account and submission steps. Steward itself can run on any OpenAI-compatible model or on Anthropic's API.

## License

Apache-2.0. See [LICENSE](LICENSE).
