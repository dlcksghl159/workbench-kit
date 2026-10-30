# 스택 카드 (구현 과제용 빠른 참조)

과제에 템플릿이 있으면 **그 스택을 그대로** 써요. 새 의존성은 내가 승인한 것만 써요.

## 서버를 0.0.0.0으로 띄우는 법
| 스택 | 명령 / 코드 |
|---|---|
| Python 표준 라이브러리 | `HTTPServer(("0.0.0.0", 8000), Handler)` · `python3 -m http.server 8000 --bind 0.0.0.0` |
| Flask | `flask --app app run --host 0.0.0.0 --port 8000` · `app.run(host="0.0.0.0", port=8000)` |
| FastAPI | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Streamlit | `streamlit run app.py --server.address 0.0.0.0 --server.port 8000` |
| Vite (React·Vue) | `npm run dev -- --host 0.0.0.0 --port 5173` |
| Next.js | `npx next dev -H 0.0.0.0 -p 3000` |
| Express | `app.listen(3000, "0.0.0.0")` |

띄운 다음에는 왼쪽 Browser 도구에 PORT와 경로를 넣고 새로고침해요. 서버를 띄운 터미널 탭은 닫지 않아요.

## 테스트 실행
| 스택 | 명령 |
|---|---|
| Python (pytest 있음) | `python3 -m pytest -q` |
| Python (표준 라이브러리) | `python3 -m unittest discover -s tests -v` |
| Node | `npm test` |
| 빠른 HTTP 확인 | `curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/경로` |
| 잘못된 입력 확인 | 4xx가 나와야 하고 500이면 안 돼요 |

## 구현 기본값 (고민 줄이기)
- 화면이 단순하면 서버에서 HTML 표로 렌더링해요 (프런트 프레임워크 없이).
- 에러 응답 형식은 하나로 통일해요: `{"error": "사람이 읽을 메시지"}`와 적절한 상태 코드.
- 설정값(경로, 포트)은 상수나 환경변수 한 곳에 모아요.
- 데이터 정제 규칙은 함수 하나에 모으고, 규칙마다 R-id 테스트를 붙여요.
- 시간은 저장된 기준(UTC 등)과 보여줄 기준(KST 등)을 README와 DM으로 확인한 뒤 한 곳에서 변환해요.

## 앱에서 LLM 호출이 필요한 과제라면
과제용 키를 앱에서 써도 되는지 먼저 Helper나 README로 확인해요. 쓸 수 있으면 환경변수에서 읽고, 키를 코드에 쓰거나 출력하지 않아요.
