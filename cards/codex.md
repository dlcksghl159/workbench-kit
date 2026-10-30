# Codex 0.162 능력 지도

시험 버전 Codex 0.162를 따로 설치해서 직접 뽑은 내용이에요 (모델 카탈로그, 모델에게 들어가는 지시문, 기능 플래그).

## 모델 (0.162 카탈로그)
| 이름 (slug) | 설명 | 비고 |
|---|---|---|
| GPT-6.1-Sol (`gpt-6.1-sol`) | 최신 주력. "near-Astra 성능, 더 낮은 비용" | 우리가 쓰는 모델 |
| GPT-6-Astra (`gpt-6-astra`) | 최상위 | **공식 가이드상 사용 제한.** 절대 고르지 않기 |
| GPT-6-Luna, GPT-5.6-Terra 외 | 가볍거나 이전 세대 | 안 씀 |

Sol 6.1 사양:
- **컨텍스트 272K** (실사용 95%). 꽉 차면 자동 요약(compaction)돼요. 그 전에 handoff로 새 세션을 여는 게 깔끔해요.
- **도구 출력은 1만 토큰에서 잘려요.** 큰 파일이나 로그를 통째로 출력시키지 마세요.
- **기본 effort가 low예요.** 시작하자마자 `/model`에서 max로 바꾸세요.
- 이미지 입력과 웹 검색을 지원해요 (설정에서 켜져 있을 때).
- Fast 모드: 속도 2배, 사용량 증가. 사용량도 평가 대상이라 막힐 때만 고려하세요.

## effort
| 값 | 의미 |
|---|---|
| low / medium / high | 가벼운 → 깊은 추론 |
| xhigh | 아주 깊은 추론 |
| max | 최대 추론 |
| ultra | 최대 추론 + **자동 작업 위임** (AI가 알아서 sub-agent를 띄움) |

**ultra보다 max를 추천해요.** ultra는 역할 분담을 AI가 정해서, "AI에 역할을 배분하고 지시했다"는 기록이 내 결정으로 남지 않아요. 토큰도 통제가 안 되고요. max에 우리 하네스로 명시적으로 위임하는 게 Intent 점수에 유리해요.

## sub-agent (multi_agent, 기본 켜짐)
- 도구: `spawn_agent`, `followup_task`, `send_message`, `wait_agent`, `interrupt_agent`, `list_agents`.
- **동시에 메인 포함 4개까지** → sub-agent는 한 번에 3개.
- 모든 agent가 같은 폴더를 써요. 한 agent가 고친 파일이 바로 다른 agent에게 보여서, 같은 파일을 두 worker에게 동시에 맡기면 충돌해요.
- `fork_turns="all"`이면 지금까지 대화를 다 넘기고 모델·effort도 그대로 따라가요. `"none"`이면 빈 맥락에서 시작하고 모델·effort를 따로 정할 수 있어요. 우리 하네스는 항상 `"none"` + 파일 경로 전달이에요.
- **AGENTS.md나 skill이 명시적으로 시키지 않으면 위임하지 않아요.** 우리 AGENTS.md가 명시하고 있어요.
- 역할은 `agent_type`으로 지정 (`~/.codex/agents/*.toml`). 우리 역할: wb-explorer, wb-worker, wb-reviewer, wb-examiner.

## skill
- 목록에 이름과 설명(앞 150자 정도)만 보이고, 쓸 때 SKILL.md를 읽어요.
- 부르는 법: `$wb-kickoff` 또는 "wb-kickoff 스킬로 시작해".

## Sol 6.1의 기본 성향 (내장 지시문)
- **매우 자율적이에요.** "사용자는 확인 질문을 싫어한다"고 배워서, 시키지 않으면 멈추지 않고 끝까지 가요. 우리 AGENTS.md가 단계마다 멈추라고 명시해 뒀어요. 그래도 질주하면 "멈춰. AGENTS.md 단계 게이트대로 해"라고 하세요.
- 작업 중에 보낸 메시지는 "방향 수정"으로 받아들여요. 기다리지 말고 바로 쳐도 돼요.
- 사소한 변경에는 테스트를 안 쓰려는 경향이 있어요. 우리 AGENTS.md는 Must 요구사항마다 실행한 검증을 요구해요.

## 권한 (sandbox)
- 설정이 없으면 **read-only + 네트워크 제한**이 기본이에요. 시험 환경 설정은 다를 수 있으니 `/status`로 sandbox와 승인 모드를 확인하세요.
- read-only면 파일을 고칠 때마다 승인을 물어서 느려요. 권한 모드를 workspace-write로 바꾸세요 (`/permissions` 또는 `/approvals`, 단축키로 다음/이전 권한 모드 전환도 있어요).
- 네트워크가 필요한 명령(pip install 등)은 승인 요청이 떠요. 이유를 읽고 판단하세요.

## 0.162에서 기본으로 켜진 기능
multi_agent, skills, hooks, goals, fast_mode, computer_use, browser_use.
→ `.kit/cx`로 실행하면 computer_use와 browser_use를 끄고 시작해요.

## 공식 가이드에서 확인된 것
- **토큰 사용량은 추적되고 간접적으로 평가에 쓰일 수 있어요.**
- **"에이전트 응답시간을 고려한 위임과 시간 안배도 AI 활용 역량으로 봐요."** max는 느려요. 정해진 일은 sub-agent(high)에게 병렬로 맡기고, max는 설계와 판단에 쓰는 이유예요.
- 제공된 Codex는 필요할 때 승인을 묻는 기본 설정이에요. 승인 대기 중에는 기다리기만 하면 진행되지 않아요. 확인하고 승인하거나 거절하세요.
- 공개 Skill, GitHub 저장소(git clone), MCP·Plugin은 써도 돼요. MCP는 IDE의 MCP 탭에서 JSON으로 설정하면 Codex에 반영돼요.
- 외부 브라우저로 자료를 찾지 않아요. 필요한 정보는 플랫폼 안에서 Codex(웹 검색 포함)로 얻어요.
- 수집되는 기록: 내장 AI·Codex·업무 담당자와의 대화, 터미널 세션, AI 도구 설정, git 로그·diff, 테스트 실행 결과, 작업 공간의 문서와 코드.
- 계획 문서·협업 기록 같은 제출 문서는 Codex와 같이 써도 불이익이 없어요. 판단과 근거, 검증 결과, 남은 한계가 담겨 있는지가 중요해요.

## 모드
- Default: 실행 모드.
- Plan: 계획만 세우고 실행하지 않아요. 실행해 달라고 해도 "실행 계획"을 세워요. DISCOVER 단계에서 써도 되지만, 우리 kickoff skill이 이미 읽기 전용으로 동작해요.
