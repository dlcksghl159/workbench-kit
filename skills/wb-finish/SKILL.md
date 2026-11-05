---
name: wb-finish
description: "Last 30-40 min before submitting: reviewer pass, fixes, audit, REPORT with R-id traceability, and the examiner drill."
---

# Finish: review → fix → audit → report → drill

1. Freeze scope. No new features; only fixes for Must requirements, correctness, and security.
2. Spawn `wb-reviewer`: "Review the current work against process/REQUIREMENTS.md." Show the human the ranked findings; the human picks what to fix. Fix findings that affect Must requirements, correctness on realistic inputs, or security; for the rest, prefer recording a known limitation over adding defensive complexity. Record the choice and its reasons in NOTES (as a changed judgment if it reverses a decision).
3. Fix with small specs (`wb-slice`) or direct edits for one-liners, then rerun the `wb-verify` rungs that apply.
4. Run `python3 .kit/tools/audit.py --run-tests`. Resolve every FAIL. Explain any WARN you keep in the report.
5. Write process/REPORT.md from `.kit/templates/REPORT.md`, in Korean, concise:
   - problem definition with DM evidence
   - traceability table: R-id → code (file:function) → check (command or test) → result
   - key decisions and the alternatives rejected
   - verification summary
   - limitations and the conditions under which the result is wrong
   - how AI was used: roles, specs, reviews, what was corrected or rejected
   - 구조 지도: entry point, modules and responsibilities, where each piece of state is stored, one request traced end to end
   If the task demands its own report format, fill that format and keep ours as an appendix or skip it. If the task requires a collaboration or AI-usage document, fill it from NOTES (AI 결과 판정, 설계 기록, 판단 변경, 오류 복구) in the task's format, keeping the same IDs. Then show the human the list of ID'd items and ask them to strike any item they could not explain in their own words; drop or rewrite those. Post-task questions pick items from these documents by ID.
6. Make sure the README (or the report) has run instructions that work from a clean shell.
7. Spawn `wb-grader`. Show the human its scores, claims without evidence, and top fixes. Fix what fits in the remaining time by doing the real work (run the check, then record it); never add a claim that was not executed.
8. Spawn `wb-examiner` (refresh it if it already ran). First close the part E evidence gaps that fit the remaining time by doing the real work (run the check, then record it). Tell the human to read parts A, B, and C of .kit/runtime/QA_DRILL.md. Then run a 10-minute drill: give two part D questions one at a time without the answers (prefer one 과정 서술 and one 변경 검증); the human types an answer within 5 minutes; reply only with the sub-asks answered, the sub-asks missed, and the numbers or names that were missing. For the remaining questions, the human says only the order of the answer.
9. Remind the human: every editor tab saved (저장됨), demo server state as intended, then submit.
