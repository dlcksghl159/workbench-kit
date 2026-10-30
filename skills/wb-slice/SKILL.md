---
name: wb-slice
description: "After requirements are confirmed: write process/specs/S<n>-<name>.md, delegate it to wb-worker, check the result, record evidence."
---

# Slice: spec → worker → check → record

## Plan (once, after the human confirms REQUIREMENTS)
- Order slices Must-first. Slice 1 must run end to end (input → processing → output), even if thin.
- Each slice is about 30 minutes of work or less and touches few files. Write the plan under "작업 계획" in process/NOTES.md with the R-ids each slice covers.
- Pre-mortem: list the 3-5 most likely ways the final result could be wrong. Each one becomes a check in some slice.
- Show the plan to the human before starting slice 1.

## Per slice
1. Write `process/specs/S<n>-<name>.md` from `.kit/templates/SPEC.md`. Required: goal, R-ids, files in scope (exact paths), conditions copied from DM facts, forbidden list, checks (exact commands with the expected result), done criteria.
2. Spawn `wb-worker` with "Implement process/specs/S<n>-<name>.md". Do not restate the spec in the message.
3. When it returns: read its report, then `git diff --stat` and the diff of the in-scope files. Rerun at least one check yourself.
4. Decide: accept, fix forward with a new small spec, or undo the slice by restoring the in-scope files by hand (never git reset).
5. Record in process/NOTES.md: the slice result, check commands with 1-3 line results, any changed judgment or error recovery.
6. If the slice changed something visible, tell the human exactly what to check in the built-in browser or the output file.

## Fallback without multi-agent
The human opens a second terminal, runs `.kit/cx`, and sends:
`.kit/agents/wb-worker.toml의 developer_instructions대로 worker로 동작해. process/specs/S<n>-<name>.md를 구현해.`
