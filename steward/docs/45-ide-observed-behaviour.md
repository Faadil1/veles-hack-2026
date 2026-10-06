---
source: donmichael/ide-gui:latest and donmichael/ide-backend:latest (shipped code, read 2026-10-06)
title: HYPER-AI IDE — behaviour of the shipped IDE
retrieved: 2026-10-06
fidelity: observed from the official container images; where it differs from the tutorial text, this is what the IDE actually does
---
# Bare file names in delete_file and edit_file
The tutorial says a bare name is resolved to the first match. The shipped IDE does not do that. For edit_file, delete_file and delete_folder it uses the exact path if it exists; otherwise it looks for the single file (or folder) whose path ends with "/<name>". If no entry or several entries match, nothing happens: the IDE only writes a warning such as "'app.yaml' matches 2 files - nothing deleted" in its status log. The agent is not told. Hyperion Steward therefore always looks names up first, asks the user when a name is ambiguous, and sends full paths.

# Actions are fire-and-forget
The IDE starts each streamed action as soon as it arrives and does not wait for the previous one to finish, and it never reports the result back to the agent. A failed action only shows up in the IDE status log. Hyperion Steward reads the workspace back through the IDE backend after every action, so it only says something was done once it can see it, and it waits for one action to land before sending the next one on the same file.

# Creating a file that already exists
create_file fails with "File already exists" when the path is taken, and the file is left unchanged. edit_file replaces a file whole but does nothing when the file does not exist. Hyperion Steward checks first and picks the right one.

# Validator
GET /api/agent/validation/file runs the backend validator. Unknown fields are warnings, not errors. YAML is read with YAML 1.2 rules: yes/no/on/off are strings, not booleans, and an unquoted 1.1 is a number, so schemaVersion must be quoted. Hyperion Steward runs an exact copy of the same rules before writing, so a profile it writes is never rejected for a schema reason.
