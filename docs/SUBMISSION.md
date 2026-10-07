# Submission package

## TAIKAI project text (brief README)

**Hyperion Steward**: the Hyperion agent for the HYPER-AI IDE that only says done once it has seen it done.

We ran the organisers' own IDE images and read their code before designing. The IDE executes agent actions
fire-and-forget and never reports the result; many actions silently do nothing (a name shared by two files, a file
that already exists, a closed tab), and nothing validates a profile unless asked. Steward answers HYPER-AI questions
from the official documents and turns plain language into IDE actions, but every change goes through one gate: scope
guard, lookup, a copy of the IDE validator (0 disagreements with the real one over 5,536 test profiles), confirmation
when required, the action, a read-back of the workspace, then the IDE validator with rollback. Deletions always ask; overwrites ask unless you named the exact file or Steward created it in this session. File creates, edits and deletes keep a restore point that undo reverts; deleting a folder asks first and cannot be undone.

Proof, all reproducible from the repo: official GUI and backend images driven by a browser in CI with llama3.1 8B
(7/7); live slice against the official backend image (6/6, undo restores identical bytes); ablation with identical tool
calls on a stub that mirrors the shipped IDE (Steward 9/9 safe outcomes and 0 false "done" claims, naive agent 1/9
and 5).

- Repo: https://github.com/Faadil1/veles-hack-2026 (Apache-2.0)
- Docker image: `faadil12/hyperion:latest` (exposes :8000/chat; set `API_KEY`)
- Deck: docs/pitch/Hyperion-Steward-VelesHack.pptx
- Development note: AI-assisted development was used during this hackathon; full build provenance is documented in the Autonomy Log.

## Message to the organiser (image tag)

> Hi Michael, our Challenge 1 image is `faadil12/hyperion:latest` (repo: https://github.com/Faadil1/veles-hack-2026).
> It reads `API_KEY` from the environment like the starter and defaults to legion1 / llama3.1; the IDE backend
> default is http://host.docker.internal:3001/api (add `--add-host host.docker.internal:host-gateway` on Linux).
> Thanks!

## Human steps, in order

1. Send the message above to Michael.
2. On TAIKAI: paste the project text, link the repo, upload the deck, press Submit before 2026-10-07 14:59 UTC.
