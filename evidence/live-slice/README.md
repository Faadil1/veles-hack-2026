# Live vertical slice

`local-backend-source.json`: **LOCAL**. The backend's own source (server.js + validation/, copied from
donmichael/ide-backend:latest by CI recon) run with Node in the build workspace, dependencies installed from npm.
Same code as the image, not the image itself.

The CI job `real-ide` runs the same slice against the **official image** (`docker run donmichael/ide-backend:latest`)
and publishes `real-ide/live-slice.json` and `real-ide/validator-parity.json` to the `ci-evidence` branch, with the
image digest and the commit SHA.

GUI behaviour is replicated (`GuiReplica`, a port of the shipped GUI's action handlers), so the GUI part is PARTIAL.
