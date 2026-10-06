# Official IDE, browser-driven, with llama3.1 8B

Run of commit 2e62095 in GitHub Actions: `donmichael/ide-gui:latest` and `donmichael/ide-backend:latest`, Steward from
source, llama3.1:8b served by Ollama on the CPU runner (the model family the organisers serve; not their server).
Chromium types into the Hyperion panel. **7/7 checks passed.**

| Step | Request | Path taken | Seconds |
|---|---|---|---|
| G1 | What's the weather in Valencia today? | guardrail, no model call | 4 |
| M1 | What is HyperAI? | **model call timed out after 300 s on the CPU runner; answered by the cited documentation fallback.** The earlier run 07a7343 answered this step with the model itself (252 s) | 305 |
| M2 | Create a deployment YAML for a service using the nginx Docker image | deterministic action route; file created, opened in the editor, read back, IDE validator valid | 5 |
| M3 | delete app.yaml | deterministic; real 409, both paths listed, nothing touched | 4 |
| M4 | Fix cookbook/native.yaml ... acme/hello-api:1.0.0 ... uvicorn on port 8000 | deterministic field edit; validator valid; runnability blocker gone | 4 |
| M5 | Which container image did you just put in that file? | model, from session memory | 341 |
| M6 | undo | deterministic; original bytes restored | 3 |

`session-timelapse-8x.mp4` is the browser recording at 8x speed (95 s). Model latency is CPU-bound here; the
organisers' GPU server is expected to be much faster (not measured).
