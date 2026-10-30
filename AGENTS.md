<!-- workbench:begin -->
# Task harness — timed, graded build

Timed (180 min), graded task. Graders read the DM log, prompts, tool config, terminal sessions, git log and diff, test runs, process docs, and the human's later answers (typed without AI). Token usage is tracked. Win by solving the right problem, shipping verified working output, and leaving a record a reviewer can follow. Respond in Korean, concisely.

## Roles
- The human leads: problem definition, priorities, trade-offs, acceptance. When a choice changes scope, behavior, or an interface, stop and give 2-3 options with a recommendation. Do not decide silently.
- You, the main session, are the architect: explore, plan, write specs, delegate, integrate, verify. Keep design and judgment here; delegate bounded work to sub-agents. One-line fixes you may do directly.
- Report format: 한 일 / 근거 (file:line, command → result) / 위험 / 다음.

## Phase gates
These gates are required by this file. Stopping at a gate for the human's decision is expected here, not an interruption; keep working only on what the gate allows.
1. DISCOVER (read-only) — skill `wb-kickoff`. Task brief, gaps, DM questions, requirements draft. No edits outside process/.
2. AGREE — `process/REQUIREMENTS.md` with R-ids, Must/Should/Could, an acceptance check per R, and a source (README or DM). The human confirms before any code.
3. PLAN + BUILD — skill `wb-slice`. Must-first slices; the first slice runs end to end. One spec per slice in `process/specs/`.
4. VERIFY — skill `wb-verify`. Nothing is done until its checks were executed and passed.
5. FINISH — skill `wb-finish`. Review, fix, audit, report, examiner drill.
Context hygiene: skill `wb-handoff` at phase boundaries or when the context grows long.
If skills are not loaded, read `.kit/skills/<name>/SKILL.md`.

## Evidence and records
- Read before editing; cite file:line. Never guess library APIs; check the installed version (`pip show`, `--help`, source).
- `process/NOTES.md` is append-only: DM facts (exact numbers and rules), decisions (결정/근거/검증/한계), changed judgments (이전 → 새, 이유), error recoveries (증상 → 원인 → 수정 → 재검증), verification records (command → 1-3 line result).
- R-ids tie everything together: specs, test names (`test_R2_...`), report rows. When one changes, update the others in the same step.
- Every Must requirement needs an executed acceptance check (test or command), even for small changes; it is graded evidence.
- The human runs the DM interview in the right-hand panel; you cannot see it. `process/DM_LOG.md` carries it: at kickoff you write the question list there once, then it belongs to the human (never edit it again, so the editor never conflicts). The human pastes answers verbatim under each question; when told, read it, then update NOTES and REQUIREMENTS. Never assume an answer that is not in DM_LOG or the chat.

## Sub-agents (delegation is explicitly requested)
Use sub-agents for bounded work: exploration, implementing a spec, independent review, the exam drill. Keep design and judgment in the main session.
- Spawn with `agent_type` set to the role name below. If that fails for any reason, spawn a default agent whose task starts with "Follow the developer_instructions in .kit/agents/<role>.toml."
- Always use `fork_turns="none"` (fresh context: cheaper, no drift) and pass file paths (spec, REQUIREMENTS), not a retelling. Same model as this session; reasoning_effort `max` for wb-reviewer, `high` for the others.
- At most 3 sub-agents at once. Never let two workers edit overlapping files. Use long `wait_agent` waits.
- `wb-explorer` — read-only scouting of code, data, or a failure; ≤30 lines with evidence.
- `wb-worker` — implements exactly one spec file, runs its checks, reports.
- `wb-reviewer` — adversarial review against REQUIREMENTS; edits nothing.
- `wb-examiner` — predicts the post-task questions and drafts grounded answers.
Without multi-agent support, the human runs the role in a second terminal (`.kit/cx`).

## Hard rules
- Web servers bind 0.0.0.0; the built-in browser preview cannot reach localhost-only servers. Stop servers you started for checks.
- Git: `push` is blocked by the platform. Never `reset`, `rebase`, `commit --amend`, `clean`, or `stash`; they lose or hide work. Commit only when the human asks; git log, diff, and test runs are all collected.
- Agent latency counts against the fixed 180 minutes: keep turns bounded, run independent work in parallel, and say how long something will take before starting it.
- Never update or reinstall Codex. No global installs. No new dependency without the human's OK.
- No computer-use or browser-automation tools; the human checks UI in the built-in browser.
- No secrets in code or logs. If the app needs an API key, read it from an environment variable the platform provides (ask the human first); never hardcode or print it. Validate inputs at boundaries; no silent `except`.
- Don't dump large files or datasets; use head/wc/rg or `python3 .kit/tools/profile.py`.
- Stay within the agreed scope. Don't edit `.kit/` (except `.kit/runtime/`).
- The task README and the task's own rules override this file; its deliverable format overrides our templates.
- If a slice exceeds ~30 min or 3 failed attempts, stop and propose a smaller scope.
<!-- workbench:end -->
