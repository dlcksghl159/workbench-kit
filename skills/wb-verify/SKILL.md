---
name: wb-verify
description: "Before calling anything done: run it, test edges and setting changes, hand-check data, check HTTP/UI, rerun regressions, log it."
---

# Verify: evidence before "done"

Climb the rungs that apply. Each rung leaves a command and a 1-3 line result under "검증 기록" in process/NOTES.md.

1. Runs: the documented run command works from a clean shell with no leftover state. Record the exact command.
2. Tests: run the project's runner (`python3 -m pytest -q`, `npm test`, ...). Report pass/fail counts, never "looks fine".
3. Edge cases: one test per edge case from REQUIREMENTS and DM facts (empty, missing, duplicate, invalid type, boundary, large).
4. Data tasks, hand check: pick 10-20 records that cover normal rows and each tricky category (`python3 .kit/tools/sample.py <file> --by <category> > process/samples.csv` does the picking). Compute the expected values independently of the code under test (a separate tiny script or by hand) and compare. Reconcile counts: input rows = kept + dropped, with a reason for every drop, so nothing disappears silently.
5. Web or API tasks: start the server on 0.0.0.0; `curl -s -o /dev/null -w "%{http_code}\n" <url>` for every route; send one invalid request and expect 4xx, not 500. Then ask the human to click through the main flow in the built-in browser. Stop servers you started.
6. Regression: rerun the baseline tests recorded at kickoff and compare the counts.
7. Determinism: run twice and compare outputs, or explain why they differ.
8. Setting changes, for every value a user can change (a limit, capacity, threshold, margin, weight, filter). Before running, write the expected direction: loosening a limit must not make the result worse, tightening it must not make it better, and shifting a time should shift the outputs by the same amount. Run with the old and the new value. Check the invariants that must always hold (limits never exceeded, every input accounted for or listed with a reason, deadlines met), and compare the two outputs (counts, totals, the worst individual case). Name the test `test_R<n>_change_<setting>`. If a heuristic moves the wrong way, record it as a limitation, or add the cheapest guard with the human's OK (for example, keep the previous result when it is still valid under the new setting and better).

When a rung fails, record 증상 → 원인 → 수정 → 재검증 (this is the error-recovery evidence). Never weaken a test to make it pass. If the requirement itself was wrong, record the changed judgment and get the human's OK.
