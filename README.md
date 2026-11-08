# KIPRIS 특허 검색 MCP 서버

KIPRIS Plus 오픈 API로 한국 특허·실용신안을 검색하는 원격 MCP 서버입니다.
Claude 앱(모바일 포함)에 **커스텀 커넥터**로 연결해서 쓰도록 만들었습니다.

- 전송 방식: **Streamable HTTP** (`/mcp`), 상태 없음(stateless)
- 인증: **Bearer 토큰** (`MCP_AUTH_TOKEN`). 토큰이 없거나 틀리면 401
- 도구 3개
  - `search_patents` 키워드 검색
  - `advanced_search_patents` 발명의 명칭·초록·청구항·IPC·출원인 조건 검색
  - `get_patent_detail` 출원번호로 서지·초록·청구항 조회
- `/healthz` 는 인증 없이 `ok` 를 돌려줍니다 (Render 상태 확인용)

## Render에 배포 (기존 서비스를 고치는 방법)

1. Render → 해당 서비스 → **Settings**
   - **Branch**: `kipris-streamable-server`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn --factory --app-dir src kipris_mcp.server:create_app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/healthz`
2. **Environment** 탭
   - `KIPRIS_API_KEY` = KIPRIS Plus에서 받은 ServiceKey
   - `MCP_AUTH_TOKEN` = 아무도 모르는 긴 무작위 문자열(16자 이상). 예: 비밀번호 관리자의 "무작위 32자"
   - `PYTHON_VERSION` = `3.11.9`
3. 저장하면 자동 배포됩니다. Logs에 `Uvicorn running on ...` 이 보이면 성공입니다.

새 서비스로 만들고 싶다면 `render.yaml` 이 있는 이 브랜치로 **New → Blueprint** 를 하면 됩니다.
이때 `MCP_AUTH_TOKEN` 은 Render가 무작위로 만들어 주고, `KIPRIS_API_KEY` 만 직접 입력합니다.

## Claude에 연결

claude.ai 웹 → 설정 → 커넥터 → **Add** → **Custom** → **Web**

| 항목 | 값 |
|---|---|
| 이름 | KIPRIS 특허 |
| URL | `https://<서비스 이름>.onrender.com/mcp` |
| Request headers | `Authorization` = `Bearer <MCP_AUTH_TOKEN 값>` |

한 번 추가하면 같은 계정의 모바일 앱에서도 커넥터 목록에 나타납니다.

## 로컬 실행·테스트

```bash
pip install -r requirements.txt pytest pytest-asyncio
python -m pytest            # 단위 테스트 + 가짜 KIPRIS 서버를 쓰는 종단 테스트

export KIPRIS_API_KEY=...  MCP_AUTH_TOKEN=$(python -c "import secrets;print(secrets.token_urlsafe(32))")
uvicorn --factory --app-dir src kipris_mcp.server:create_app --port 8000
curl -s localhost:8000/healthz
```

## 주의

- 테스트는 KIPRIS 응답을 흉내 낸 XML로 했습니다. **실제 KIPRIS 서버와의 통신은 이 저장소 작성 환경에서 확인하지 못했습니다.**
  배포 후 첫 검색에서 오류가 나면 오류 메시지의 `[코드]` 를 확인하세요
  (`30` 등록되지 않은 키, `31` 상품 미신청·기간 만료, `10` 파라미터 오류).
- KIPRIS Plus에서 "특허·실용신안 공개·등록공보" 계열 Open API 상품을 신청한 키여야 합니다.
- Render 무료 서비스는 15분 동안 요청이 없으면 잠들고, 다음 첫 요청은 약 1분 걸립니다.
- API 키와 토큰은 코드나 채팅에 적지 말고 Render 환경변수에만 넣으세요.
