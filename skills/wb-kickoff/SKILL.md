---
name: wb-kickoff
description: "Exam start, before any code: read-only discovery, task brief, DM questions for the human, and a draft REQUIREMENTS with R-ids."
---

# Kickoff: discover → DM questions → requirements draft

Sources of truth: the README and task instructions define the goal, mandatory conditions, and deliverables. The business owner in the DM (a scenario agent playing the person with the problem) adds business context: why it matters, how they work, detailed rules, exceptions, priorities, definitions, and requirements the README leaves implicit. When a DM answer conflicts with the README, flag it to the human and ask for a confirming question instead of silently choosing.

Goal, within about 15 minutes: (a) a brief the human can check against the README, (b) the questions only the business owner can answer, (c) a requirements draft the human will confirm. No code edits in this skill.

## Steps
1. Inventory, read-only:
   - `ls -la`, the README, and any task, spec, or rubric documents.
   - Data files: `python3 .kit/tools/profile.py <file-or-dir>`.
   - Existing tests: run them once (`python3 -m pytest -q`, `npm test`, ...) and record pass/fail counts as the baseline in process/NOTES.md.
   - If both code and data exist, spawn `wb-explorer` agents in parallel for each.
2. Brief, 15 lines max: who the user is and what they need; inputs; required deliverables and their format; constraints already stated; how the result will likely be judged.
3. Gaps the README leaves open. Check at least: what one row or record means; duplicates, cancellations, and missing values; time windows and timezones; units and rounding; exact definitions or formulas of domain terms (yield, defect rate, Cpk, ...); which rule wins when rules conflict; output format and naming; the one action the user must be able to do; behavior on invalid input; performance limits.
4. DM questions: 5-8 in Korean, one fact each, ordered by impact on the design. Ask for facts, rules, examples, and priorities. Never ask the owner what to do or how to implement. Include at least one example-based question ("이 케이스는 X로 처리하면 맞나요?"). Append them to the end of `process/DM_LOG.md`, one block per question:
   ```
   ### Q1 (영향: 높음 — R2 집계 기준)
   질문: ...
   - 답:
   ```
   This is the only time you write to DM_LOG.md; afterwards it belongs to the human.
5. Draft `process/REQUIREMENTS.md` from `.kit/templates/REQUIREMENTS.md`: R-ids, Must/Should/Could, an acceptance check per R (a command or an observable result), the source (README section or DM). Mark unconfirmed items as 가정.
6. Stop. Tell the human: DM_LOG.md를 에디터로 열고, 질문을 복사해 업무 담당자에게 보내고, 답을 `- 답:` 아래에 그대로 붙여넣은 뒤 "DM_LOG 반영해"라고 하세요.

## When the human says the DM answers are in
1. Read process/DM_LOG.md (and any answers pasted in the chat). Record each under "DM 확인 사항" in process/NOTES.md: Q-id → answer, keeping exact numbers and rules. Flag unanswered or vague answers and suggest one follow-up question for each.
2. Update REQUIREMENTS: resolve 가정 items, add newly found requirements, re-rank Must/Should/Could. Record any changed judgment.
3. Draft the confirmation message the human sends back to the owner:
   "말씀해주신 내용을 바탕으로 요구사항을 [A, B, C]로 정리했고, 예외는 [X 기준]으로 처리하고, [Y 구조]로 먼저 만들려고 합니다. 의도와 맞을까요?"
4. Wait for the human's go before planning slices.
