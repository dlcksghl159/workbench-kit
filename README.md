# workbench — Codex 하네스 (시간제 과제용)

Codex 0.162 + Sol 6.1 기준. 문제 정의와 판단은 사람이 하고, Codex는 역할을 나눠 탐색·구현·검증·리뷰를 맡아요. 공식 채점 항목(코드 실행성·구조·보안 / 문제 정의·우선순위 / AI 지시 품질 / 근거 탐색·의사결정 / 반복 개선·오류 복구 / 결과 검증)이 작업 기록에 그대로 남도록 설계했어요.

## 시작 (과제 workspace 루트에서)
```bash
git clone https://github.com/dlcksghl159/workbench-kit.git .kit && bash .kit/install.sh
.kit/cx
```
`.kit/cx`는 computer_use와 browser_use를 끄고 Codex를 띄워요. 띄운 뒤 바로:
1. `/model` → **GPT-6.1-Sol, effort max** (기본값이 low예요. ultra는 AI가 알아서 위임해서 쓰지 않아요)
2. `/status` → sandbox가 read-only면 권한 모드를 workspace-write로 바꿔요 (`/permissions` 또는 `/approvals`)

Codex가 무엇을 어디까지 하는지는 [Codex 능력 지도](cards/codex.md)에 정리했어요.

install.sh가 하는 일:
- `~/.codex/AGENTS.md`에 규칙 블록 추가 (기존 내용은 백업하고 유지)
- sub-agent 4개, skill 5개를 `~/.codex/`에 설치
- `process/`에 REQUIREMENTS·NOTES·HANDOFF 생성, `.kit/`는 git status/diff에서 제외
- Codex 설정 파일(config.toml)은 건드리지 않음

sub-agent는 `gpt-6.1-sol`로 고정돼요. 시험 환경의 모델 이름이 다르면 `KIT_MODEL=<모델명> bash .kit/install.sh`로 다시 설치하고, 세션 모델을 그대로 따르게 하려면 `KIT_MODEL=none`.

## 구성
| 종류 | 이름 | 역할 | effort |
|---|---|---|---|
| 메인 | (내 세션) | 설계, 스펙 작성, 위임, 통합, 판단 | max |
| sub-agent | wb-explorer | 코드·데이터·오류 원인 탐색 (읽기 전용) | high |
| sub-agent | wb-worker | 스펙 1개 구현 + 검증 | high |
| sub-agent | wb-reviewer | 새 맥락에서 깐깐한 리뷰 (수정 안 함) | max |
| sub-agent | wb-examiner | 확인 문제 예상 질문과 4문장 답 | high |
| skill | wb-kickoff · wb-slice · wb-verify · wb-handoff · wb-finish | 단계별 절차 | — |
| 도구 | `tools/profile.py` | 데이터 요약 (토큰 안 씀) | — |
| 도구 | `tools/audit.py` | 제출 전 점검 | — |

기록은 R-id로 이어져요: DM 답변 → `process/REQUIREMENTS.md` (R1, R2…) → `process/specs/` → 테스트 이름 `test_R1_…` → `process/REPORT.md` 추적표 → 확인 문제 답변.

## 시간표 (10:00 시작 기준)
| 시각 | 단계 | 할 일 |
|---|---|---|
| 10:00 | 준비 | 설치, Codex 실행, README 읽기, [P0](cards/prompts.md) |
| 10:10 | DISCOVER | kickoff 결과 확인, DM 질문 다듬기 |
| 10:15 | DM | 업무 담당자 인터뷰 ([DM 카드](cards/dm.md)), P1, 합의 확인 |
| 10:35 | PLAN | P2, slice 계획 확인 |
| 10:45 | BUILD | P3 반복. 11:30까지 처음부터 끝까지 한 번 돌아가게 |
| 12:20 | FINISH | P7: 리뷰, 수정, 점검, 보고서 |
| 12:45 | 대비 | P8: 예상 질문 읽기, 코드에서 사실 다시 확인 |
| 12:55 | 제출 | 에디터 탭 전부 저장 확인 후 제출, 확인 문제 ([카드](cards/qa.md)) |

14:00에 전부 강제 종료돼요. 문제 생성 대기(5~10분)와 확인 문제(약 6문항 × 5분)에 40분은 남겨야 해요.

## 함정
- 웹 서버는 `0.0.0.0`으로 띄워요. localhost면 내장 브라우저 미리보기가 연결되지 않아요.
- Codex가 고치는 파일을 에디터에서 동시에 수정하지 마세요. "외부 변경 감지"가 뜨면 보통 "외부 변경 불러오기"를 골라요.
- 제출 전에 에디터 탭이 전부 "저장됨"인지 확인 (Ctrl+S).
- `git add/commit/reset/clean` 하지 않아요. Codex 업데이트 안내는 무시해요.
- Claude Code 실행 금지, Computer Use 금지.
- 확인 문제는 AI, 복붙, 외부 창, 이전 문항 이동이 모두 불가예요.

## 카드
[Codex 능력 지도](cards/codex.md) · [DM 카드](cards/dm.md) · [프롬프트 카드](cards/prompts.md) · [확인 문제 카드](cards/qa.md)

## sub-agent 기능이 안 될 때
두 번째 터미널에서 `.kit/cx`를 실행하고 이렇게 보내요.
```
.kit/agents/wb-worker.toml의 developer_instructions대로 worker로 동작해. process/specs/S1-<이름>.md를 구현해.
```
skill이 안 읽히면 메인 세션에서 `.kit/skills/wb-kickoff/SKILL.md를 읽고 따라` 처럼 경로로 지시해요.
