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
- sub-agent 5개, skill 5개를 `~/.codex/`에 설치
- `process/`에 REQUIREMENTS·NOTES·HANDOFF·DM_LOG 생성, `.kit/`는 git status/diff에서 제외
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
| sub-agent | wb-grader | 모의 채점: 공개된 평가 기준으로 증거 채점, 보완점 | high |
| skill | wb-kickoff · wb-slice · wb-verify · wb-handoff · wb-finish | 단계별 절차 | — |
| 도구 | `tools/profile.py` | 데이터 요약 (토큰 안 씀) | — |
| 도구 | `tools/audit.py` | 제출 전 점검 | — |
| 도구 | `tools/trace.py` | 내 프롬프트·위임·토큰 사용 기록 요약 | — |
| 도구 | `tools/sample.py` | 검산용 표본 뽑기 (결측·특수값·중복·극값·범주별) | — |

기록은 R-id로 이어져요: DM 답변 → `process/REQUIREMENTS.md` (R1, R2…) → `process/specs/` → 테스트 이름 `test_R1_…` → `process/REPORT.md` 추적표 → 확인 문제 답변.

## 시간표 (10:00 과제 시작 기준)
| 시각 | 단계 | 할 일 |
|---|---|---|
| 09:40 | 접속 | 링크 접속, 규정 동의, 웹캠·전체 화면 공유·Proctor 연결. 추가 공지 메일 확인 |
| 10:00 | 과제 시작 | "과제 시작" → 녹화 시작 → 휴대폰 거치 → 신분증·안경 확인 (이 시간도 180분에 포함) |
| 10:05 | 준비 | 키트 설치, Codex 실행·설정, README 읽기, [P0](cards/prompts.md) |
| 10:15 | DISCOVER | kickoff 결과 확인, DM 질문 다듬기 |
| 10:20 | DM | `process/DM_LOG.md`의 질문을 업무 담당자에게 보내고 답을 그대로 붙여넣기 ([DM 카드](cards/dm.md)) → P1 → 합의 확인 |
| 10:40 | PLAN | P2, slice 계획 확인 |
| 10:50 | BUILD | P3 반복. 11:35까지 처음부터 끝까지 한 번 돌아가게 |
| 11:40 | 중간 점검 | P6.5: wb-grader 모의 채점 → 부족한 증거 보완 |
| 12:15 | FINISH | P7: 리뷰, 수정, 점검, 보고서 |
| 12:40 | 대비 | P8: 예상 질문 읽기, 코드에서 사실 다시 확인 |
| 12:50 | 제출 | 작업 종료 10분 전 제출 시작 (가이드 권장): 저장 확인 → "제출하고 문제풀기" → "제출물 확정하고 문제풀기" |
| ~13:00 | 확인 문제 | 문제 준비 대기 (최대 10분) → "문제 풀기" → 6문항 × 5분 ([카드](cards/qa.md)) |

14:00에 전부 강제 종료돼요. 늦게 시작하면 확인 문제가 잘려요.

## 함정 (공식 가이드 기준)
- **웹 서버는 `0.0.0.0`으로.** 왼쪽 Browser 도구에 PORT와 경로를 넣고 새로고침해서 확인해요. 서버를 띄운 터미널 탭은 닫지 마세요.
- **"외부 변경 감지"가 뜨면** 양쪽 내용을 비교하고 "외부 변경 불러오기"나 "현재 내용으로 저장"을 골라요. 제출 전 탭이 전부 "저장됨"인지 확인 (Ctrl/Cmd+S).
- **git:** push는 막혀 있어요. reset·rebase·clean·stash는 쓰지 않아요. commit은 필요할 때만 해요 (git 로그·diff·테스트 실행 결과가 모두 수집돼요).
- **금지:** Claude Code와 별도 AI 연결, Astra 모델, Computer Use(자동 조작) 전 단계, 개인 API 키. Codex 업데이트 안내는 무시해요.
- **외부 브라우저로 자료를 찾지 않아요.** 필요한 정보는 플랫폼 안에서 Codex로 얻어요.
- **전체화면이 강제되고, 화면 이탈과 캡처 단축키를 감지해요.** 다른 앱으로 넘어가거나 스크린샷을 찍지 마세요.
- **"비활성 상태·일시정지" 안내가 뜨면 "계속 작업"을 눌러요.** Codex 응답을 오래 기다릴 때 뜰 수 있고, 그동안에도 타이머는 흘러요.
- **우측 상단 CPU/RAM을 보세요.** 내 프로세스 때문에 생긴 메모리 부족(OOM)은 구제되지 않아요.
- **터미널 붙여넣기:** Mac은 Cmd+V, Windows·Linux는 Ctrl+Shift+V.
- **MCP 탭**에서 MCP 서버 JSON을 설정할 수 있어요. 필요할 때만 써요.
- **제출 미리보기에 `.kit` 같은 숨김 폴더가 안 보일 수 있어요.** 정상이에요. 최종 화면에서 제출 ID·파일 수를 확인해요.

## 카드
[행동 전략](cards/play.md) · [스택 카드](cards/stack.md) · [Codex 능력 지도](cards/codex.md) · [평가 기준 지도](cards/rubric.md) · [DM 카드](cards/dm.md) · [프롬프트 카드](cards/prompts.md) · [확인 문제 카드](cards/qa.md)

## sub-agent 기능이 안 될 때
두 번째 터미널에서 `.kit/cx`를 실행하고 이렇게 보내요.
```
.kit/agents/wb-worker.toml의 developer_instructions대로 worker로 동작해. process/specs/S1-<이름>.md를 구현해.
```
skill이 안 읽히면 메인 세션에서 `.kit/skills/wb-kickoff/SKILL.md를 읽고 따라` 처럼 경로로 지시해요.
