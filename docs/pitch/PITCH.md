# Pitch: Hyperion Steward (6 minutes)

Slides: `Hyperion-Steward-VelesHack.pptx` (official submission template, 9 slides). Timings are targets.

## Script

**0:00 Title (20 s).** Hyperion Steward is our Hyperion agent for the HYPER-AI IDE. One sentence: it only tells
you something happened once it has seen it happen in your workspace.

**0:20 Repo (15 s).** Public repo, Apache-2.0 like the starter, one Docker image that exposes `:8000/chat`. Same
contract and same `API_KEY` as the official starter, so it drops in.

**0:35 Summary (40 s).** It answers HYPER-AI questions from the official documents and turns plain language into IDE
actions. Before building, we ran the organisers' own IDE images and read their code. That changed our design.

**1:15 What we found (60 s).** Three facts. One: the IDE runs each agent action fire-and-forget and never tells the
agent the result. Two: many actions silently do nothing: a file name shared by two files, creating a file that
already exists, or simply a closed IDE tab. The tutorial even says a bare name hits the first match; the shipped GUI
refuses instead. Three: nothing validates a profile unless someone asks, and YAML 1.2 makes `no` a string and `1.1`
a number. So a straightforward agent tells users "done" when nothing happened.

**2:15 How it works (50 s).** Every change goes through one gate, whatever the model says: scope guard, look up the
target, check the profile with a copy of the IDE's validator, ask when it matters, send the action, read the
workspace back, then the IDE's own validator, with rollback if it rejects. The model handles language; a builder
writes the profile, so the model never hand-writes forty typed fields.

**3:05 Demo (90 s).** Live in the official IDE (or the CI recording):
1. "What's the weather in Valencia?" Declined before any model call.
2. "What is HyperAI?" Answer from the deliverables, cited.
3. "Create a deployment YAML for a service using the nginx Docker image." File created, opened in the editor, read
   back, validated.
4. "check cookbook/native.yaml". The official cookbook example is valid but will not run: uvicorn inside nginx.
5. "delete app.yaml" with two such files. It lists both and asks.
6. "undo". Restores the exact bytes.

**4:35 Highlights (45 s).** Zero disagreements with the real validator over 5,536 test profiles (validator code
taken from the official image). In a scripted experiment on a local stub that mirrors the shipped IDE, with the same
tool calls for both agents: nine out of nine safety scenarios against one out of nine for a naive agent, and zero
false "done" claims against five. That experiment is separate from the live evidence: six of six steps against the
official backend image, and the official GUI driven by a browser with llama3.1 8B, 7/7 on the published image.

**5:20 Criteria and limits (40 s).** All five criteria, each with its proof in the repo. What is not proven yet, we
say: answer quality on your server was not measured before submission (you run the image with your own key);
runnability checks are rules, not a real deployment. Every claim in
the repo carries its evidence class. Thank you.

## Q&A preparation

| Likely question | Answer |
|---|---|
| Why not LangChain / LangGraph? | Allowed but optional. The safety gate is plain code so it holds whatever the model does; the model layer is a small OpenAI-compatible adapter, so it runs on your server, Ollama or any compatible API. |
| What if no model is reachable? | Guardrail, docs answers with citations, check, undo, and the official example requests (create a profile for an image, delete with confirmation) still work through a deterministic intent parser. It refuses anything it cannot do safely. |
| How do you know your validator copy matches ours? | A differential test runs your backend's own validation code (copied out of the official image in CI) and our port on 5,536 generated profiles: zero disagreements. |
| Does the read-back slow things down? | One or two GET calls per action against the local backend, typically well under a second. It also stops two actions on the same file from racing, since the GUI does not wait between them. |
| Memory? | Per `user_id` session history and a journal of changes, trimmed to fit the 8k context of the provided model. |
| Isn't the first-match hazard in your README? | It was, from the tutorial. When we read the shipped GUI we found it refuses ambiguous names instead, so we withdrew the claim and logged the correction (AUTONOMY-LOG D-026). |
| Is the 9/9 vs 1/9 a live result? | No. It is a scripted LOCAL_STUB experiment: a stub that mirrors the shipped GUI and backend, identical tool calls, three action layers. The live evidence is separate: 6/6 against the official backend image and the browser runs in the official GUI. |
| Who built it? | Claude (Anthropic), running autonomously as one arm of a build benchmark; Faadil Boussari handled accounts and submission. Disclosed in the README. |
| What's next? | Hybrid retrieval with the server's embedding models; deployment-aware runnability using the IDE's Deploy API; per-team policies on what needs confirmation. |
