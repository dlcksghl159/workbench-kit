---
name: wb-finish
description: "Last 30-40 min before submitting: reviewer pass, fixes, audit, REPORT with R-id traceability, and the examiner drill."
---

# Finish: review → fix → audit → report → drill

1. Freeze scope. No new features; only fixes for Must requirements, correctness, and security.
2. Spawn `wb-reviewer`: "Review the current work against process/REQUIREMENTS.md." Show the human the ranked findings; the human picks what to fix. Record the choice and its reasons in NOTES (as a changed judgment if it reverses a decision).
3. Fix with small specs (`wb-slice`) or direct edits for one-liners, then rerun the `wb-verify` rungs that apply.
4. Run `python3 .kit/tools/audit.py --run-tests`. Resolve every FAIL. Explain any WARN you keep in the report.
5. Write process/REPORT.md from `.kit/templates/REPORT.md`, in Korean, concise:
   - problem definition with DM evidence
   - traceability table: R-id → code (file:function) → check (command or test) → result
   - key decisions and the alternatives rejected
   - verification summary
   - limitations and the conditions under which the result is wrong
   - how AI was used: roles, specs, reviews, what was corrected or rejected
   If the task demands its own report format, fill that format and keep ours as an appendix or skip it.
6. Make sure the README (or the report) has run instructions that work from a clean shell.
7. Spawn `wb-grader`. Show the human its scores, claims without evidence, and top fixes. Fix what fits in the remaining time by doing the real work (run the check, then record it); never add a claim that was not executed.
8. Spawn `wb-examiner`. Tell the human to read .kit/runtime/QA_DRILL.md and re-check the listed facts in the code themselves.
9. Remind the human: every editor tab saved (저장됨), demo server state as intended, then submit.
