---
name: wb-handoff
description: "Write process/HANDOFF.md to continue in a fresh session: at phase boundaries, after direction changes, or when context grows long."
---

# Handoff

Use it after the first end-to-end slice, after any direction change, before FINISH, or when you notice drift: repeating work, forgetting DM rules, contradicting earlier decisions.

1. Update process/HANDOFF.md (template: `.kit/templates/HANDOFF.md`). Overwrite the "현재" section; append one line to the log.
   - Goal (1 line) and current phase
   - DM conditions that must not drift, with exact values
   - Finished slices, each with a pointer to its evidence in NOTES
   - Work in progress and the next 1-3 actions, concrete enough to start without asking
   - Open questions for the human or the business owner
   - Commands to run and verify the current state
2. Make sure REQUIREMENTS, NOTES, and the specs are saved and consistent with each other.
3. Tell the human: "새 세션에서 `process/HANDOFF.md를 읽고 이어서 진행해`로 시작하세요." Then stop.
