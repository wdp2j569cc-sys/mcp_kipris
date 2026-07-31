# MCP KIPRIS 프로젝트 현황 분석

## 📊 프로젝트 개요

### 프로젝트 정보
- **프로젝트명**: MCP KIPRIS
- **설명**: 한국특허정보원(KIPRIS) API를 활용한 특허 검색 MCP 서버
- **버전**: 동적 버전 관리 (setuptools_scm 사용)
- **Python 요구사항**: 3.12+
- **라이선스**: MIT License

### 개발 현황
- **상태**: 프로덕션 레벨로 안정화됨
- **최근 개선**: 보안 강화, Rate limiting, 재시도 메커니즘 구현 완료
- **코드 품질**: Ruff 포맷팅, Pyright 타입 체크 적용

---

## 🏗️ 아키텍처 구조

### 1. 핵심 구성요소

#### 서버 모듈
- **`server.py`**: stdio MCP 서버 (비동기 지원)
- **`sse_server.py`**: HTTP(SSE) 서버 (웹 인터페이스)

#### 핵심 유틸리티
- **`api_client_factory.py`**: 통합 API 클라이언트 팩토리
- **`rate_limiter.py`**: Token bucket 기반 Rate limiting (60 req/min)
- **`logging_utils.py`**: 보안 로깅 (API 키 마스킹)
- **`errors.py`**: 구조화된 오류 처리

#### API 클라이언트
- **`api/korean/`**: 한국 특허 검색 API
- **`api/foreign/`**: 해외 특허 검색 API (15개국 지원)

#### MCP 툴
- **`tools/korean/`**: 한국 특허·상표 검색 툴 (12개)
- **`tools/foreign/`**: 해외 특허 검색 툴 (5개)

### 2. 주요 기능

#### 한국 특허 검색 (11개 툴)
1. **출원인 검색** (`patent_applicant_search`)
2. **키워드(자유 텍스트) 검색** (`patent_free_search`)
3. **출원번호 검색 — KIPRIS 고급검색 기반** (`patent_advanced_search`)
4. **출원번호 검색** (`patent_search`) — ⚠️ **Deprecated**, 아래 참고
5. **출원번호 검색 — 전용 조회 서비스 기반** (`patent_application_number_search`)
6. **권리자 검색** (`patent_righter_search`)
7. **요약 정보 검색** (`patent_summary_search`)
8. **상세 정보 검색** (`patent_detail_search`)
9. **초록 검색** (`abstract_search`) — *[@haseo-ai](https://github.com/haseo-ai) 기여*
10. **IPC 분류 코드 검색** (`ipc_search`) — *[@haseo-ai](https://github.com/haseo-ai) 기여*
11. **대리인 검색** (`agent_search`) — *[@haseo-ai](https://github.com/haseo-ai) 기여*

> **`patent_search` → `patent_advanced_search`로 개명**: `patent_search`와 `patent_application_number_search`는 둘 다 출원번호로 검색하지만 서로 **다른 KIPRIS 엔드포인트**(`getAdvancedSearch` vs `applicationNumberSearchInfo`, API 키 파라미터명도 `ServiceKey` vs `accessKey`로 다름)를 호출하는 별개 서비스라, 단순 중복이 아니라 이름이 부정확했던 것으로 판단해 **`patent_advanced_search`로 개명**했습니다. 옛 이름 `patent_search`는 `patent_advanced_search`의 하위 클래스로 남겨 하위 호환을 유지하며(`server.py`/`sse_server.py` 양쪽 등록 유지), 인스턴스화 시 `DeprecationWarning`을 발생시키고 MCP 툴 설명(`description`)과 `metadata.deprecated`에도 폐기 예정임을 명시했습니다. **다음 메이저 버전에서 `patent_search` 제거 예정** — 신규 통합은 `patent_advanced_search`를 사용하세요. 두 툴 모두 출력 컬럼을 `ApplicationNumber/ApplicationDate/InventionName/Applicant`로 통일해 결과 형식이 일치하도록 정렬했습니다(`patent_application_number_search`의 동기/비동기 응답이 서로 다른 컬럼을 반환하던 버그도 함께 수정).

#### 한국 상표 검색 (1개 툴)
1. **상표 검색** (`trademark_search`) — *[@haseo-ai](https://github.com/haseo-ai) 기여*

#### 해외 특허 검색 (5개 툴)
1. **출원인 검색** (`foreign_patent_applicant_search`)
2. **출원번호 검색** (`foreign_patent_application_number_search`)
3. **자유 텍스트 검색** (`foreign_patent_free_search`)
4. **국제출원번호 검색** (`foreign_international_application_number_search`)
5. **국제공개번호 검색** (`foreign_international_open_number_search`)

---

## 🔧 기술 스택

### 핵심 의존성
```python
# MCP 프레임워크
mcp[cli]>=1.6.0

# 비동기 웹
httpx>=0.28.1
httpx-sse>=0.4.0
uvicorn>=0.34.0
starlette>=0.46.1
sse-starlette>=2.2.1

# 데이터 처리
pandas>=2.2.3
xmltodict>=0.14.2
networkx>=3.4.2
scikit-learn>=1.6.1

# AI/ML 관련
langchain-community>=0.3.21
langchain-core>=0.3.51

# 유틸리티
requests>=2.32.3
python-dotenv>=1.1.0
stringcase>=1.2.0
tabulate>=0.9.0
icecream>=2.1.4

# 개발 도구
pytest>=8.3.5
pytest-asyncio>=0.26.0
ruff>=0.3.0
pyright>=1.1.398
```

### 설정 관리
- **`pyproject.toml`**: 프로젝트 설정, 의존성, 빌드 설정
- **Ruff**: 라인 길이 120자, 4스페이스 들여쓰기
- **동적 버전관리**: setuptools_scm 사용

---

## 🔐 보안 및 안정성 기능

### 1. 보안 강화
- **API 키 마스킹**: 로그에서 민감 정보 자동 제거
- **환경 인식 로깅**: 프로덕션(INFO)/개발(DEBUG) 분리
- **보안 로깅 유틸리티**: `redact_sensitive_data()` 함수

### 2. 안정성 개선
- **Rate Limiting**: Token bucket 알고리즘, 60 requests/minute
- **재시도 메커니즘**: 지수 백오프, 최대 3회 재시도
- **타임아웃 처리**: 연결/요청 타임아웃 관리
- **구조화된 오류 처리**: `KiprisApiError` 클래스

### 3. 성능 최적화
- **비동기 처리**: `run_tool_async()` 메서드 지원
- **클라이언트 캐싱**: API 클라이언트 인스턴스 재사용
- **중앙 설정**: `ApiClientConfig` 데이터클래스

---

## 🌐 지원 범위

### 지원 국가 (15개)
- **US**: 미국
- **EP**: 유럽
- **WO**: PCT
- **JP**: 일본
- **PJ**: 일본영문초록
- **CP**: 중국
- **CN**: 중국특허영문초록
- **TW**: 대만영문초록
- **RU**: 러시아
- **CO**: 콜롬비아
- **SE**: 스웨덴
- **ES**: 스페인
- **IL**: 이스라엘

### 정렬 옵션
- **PD**: 공고일자
- **AD**: 출원일자
- **GD**: 등록일자
- **OPD**: 공개일자
- **FD**: 국제출원일자
- **FOD**: 국제공개일자
- **RD**: 우선권주장일자

### 특허 상태 코드
- **A**: 공개
- **C**: 정정공개
- **F**: 공고
- **G**: 정정공고
- **I**: 무효공고
- **J**: 취소공고
- **R**: 재공고

---

## 📁 파일 구조 분석

### 주요 파일 현황
```
총 100+ 파일
├── 설정 파일 (5개)
│   ├── pyproject.toml          # 프로젝트 설정
│   ├── requirements.txt         # 의존성 목록
│   ├── .gitignore              # Git 무시 파일
│   └── .vscode/settings.json   # VS Code 설정
├── 문서 파일 (3개)
│   ├── README.md               # 사용자 가이드
│   ├── project_spec.md         # 개선 기록
│   └── PROJECT_INITIALIZATION.md # 초기화 가이드
├── 소스 코드 (90+ 파일)
│   ├── 서버 파일 (2개)
│   ├── API 클라이언트 (20+ 파일)
│   ├── 툴 구현 (17개)
│   └── 유틸리티 (4개)
└── Docker 파일 (2개)
    ├── Dockerfile.stdio
    └── Dockerfile.sse
```

### 코드 품질 지표
- **총 라인 수**: 약 3,000+ 라인
- **테스트 커버리지**: `test/unit/` 61개 pytest 단위 테스트, 커버리지 약 61%
- **타입 안정성**: Pyright 정적 타입 체크 적용
- **코드 포맷**: Ruff 자동 포맷팅

---

## 🚀 실행 환경

### 개발 환경
```bash
# 가상환경
.venv/bin/activate  # Linux/Mac
.venv\Scripts\activate  # Windows

# 개발 모드 설치
pip install -e .

# 서버 실행
python -m mcp_kipris.server  # stdio 모드
python -m mcp_kipris.sse_server --http --port 6274  # HTTP 모드
```

### 프로덕션 환경
```bash
# Docker 컨테이너
docker build -f Dockerfile.sse -t mcp-kipris-sse .
docker run -p 6274:6274 -e KIPRIS_API_KEY=$API_KEY mcp-kipris-sse
```

### 환경 변수
```bash
KIPRIS_API_KEY=rC/Bd5gSN4jOoHSN8VSrVTZ/tKd5ENoUFMFhFXPaOX8=  # 현재 설정됨
LOG_LEVEL=INFO  # 프로덕션 환경
```

---

## 🔍 현재 상태 분석

### ✅ 완료된 기능
1. **MCP 서버 구현**: stdio 및 HTTP(SSE) 모드, 두 모드 모두 동일한 17개 툴 등록(양쪽 불일치 버그 수정됨)
2. **한국 특허·상표 검색**: 12개 완전한 툴 구현 (특허 11개 + 상표 1개)
3. **해외 특허 검색**: 5개 완전한 툴 구현
4. **보안 강화**: API 키 마스킹(요청 로그 경로까지 실제 적용), Rate limiting(실제 요청 경로에 연결됨)
5. **안정성 개선**: 재시도/백오프 메커니즘
6. **성능 최적화**: 비동기 처리, 클라이언트 캐싱

### ⚠️ 개선 필요 사항
1. ~~**의존성 해결**: 일부 import 오류 (LSP)~~ ✅ 해결됨 — `server.py`/`sse_server.py` import 정상 확인, `api_client_factory.py`의 잘못된 모듈 경로(`patent_agent_search_api` → `agent_search_api`)도 테스트 작성 중 발견하여 수정
2. ~~**테스트 강화**: 단위 테스트 및 통합 테스트 추가~~ ✅ 해결됨 — `test/unit/`에 네트워크 호출 없는 pytest 단위 테스트 35개 추가(도구 레지스트리 회귀 테스트, rate limiter, 에러 클래스, 로그 마스킹, API 클라이언트 팩토리). 기존 라이브 API 테스트는 `pytest.mark.integration`으로 구분. 커버리지 0%대 → 56%
3. **문서화**: API 문서 및 개발자 가이드 보강
4. **모니터링**: 성능 모니터링 및 로그 분석 기능
5. **MCP 스펙 2026-07-28 대응** (작업 후보, 대기 중): [MCP 스펙 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog)이 세션 제거, `server/discover` 도입, Streamable HTTP 전환(HTTP+SSE Deprecated), Roots/Sampling/Logging Deprecated 등 프로토콜을 대규모로 재설계함. 현재 `mcp` SDK는 `1.9.4`(요구사항 `>=1.6.0`)로 이 스펙을 지원하지 않음. **착수 조건**: `mcp` Python SDK가 신규 스펙 지원 버전을 릴리스하면 업그레이드 후, `sse_server.py`의 레거시 `SseServerTransport`(HTTP+SSE)를 Streamable HTTP로 마이그레이션.
6. ~~**응답 토큰 절감을 위한 `fields` 파라미터**~~ ✅ `patent_detail_search`에 우선 적용 — 이 툴은 원래 필터링 없이 원본 중첩 응답(`getBibliographyDetailInfoSearch`, 최상위 컬럼이 `biblioSummaryInfoArray` 등 15개의 opaque wrapper 배열이라 `to_markdown()` 결과가 사실상 못 쓰는 수준)을 그대로 반환했음. `fields`를 생략/빈 배열로 두면 6개 기본 요약 필드(`applicationNumber`, `applicationDate`, `inventionTitle`, `applicantName`, `registerStatus`, `ipcNumber`)만 반환하고, 지정하면 서지정보/IPC/초록/청구항/출원인·발명자·대리인/우선권/지정국가/선행기술/법적상태/R&D 등 약 65개 필드 중 자유 조합으로 선택 가능. 나머지 툴(특히 원본 텍스트가 긴 `abstract_search`, `patent_summary_search`)에는 이 패턴 검증 후 확장 예정.

### 🐛 테스트 작성 중 발견/수정한 버그
- `sse_server.py`가 `server.py`에 있는 4개 툴(`KoreanAbstractSearchTool`, `KoreanIpcSearchTool`, `KoreanAgentSearchTool`, `KoreanTrademarkSearchTool`)을 등록하지 않아 HTTP/SSE 모드에서 사용 불가 → 등록 추가, 회귀 테스트(`test_tool_registration.py`)로 방지
- `rate_limiter.py`의 `wait_if_rate_limited()`가 정의되지 않은 `logger`를 참조해 rate limit 발동 시 `NameError`로 죽음 → `logging` import 및 모듈 로거 추가
- `api_client_factory.py`가 존재하지 않는 모듈(`patent_agent_search_api`)을 import해 아예 import 자체가 실패함(이 모듈은 현재 다른 코드에서 쓰이지 않아 아무도 못 잡아냈던 것으로 보임) → 올바른 모듈/클래스명(`agent_search_api.AgentSearchAPI`)으로 수정
- `ApiClientFactory.get_all_clients()`가 한국/해외 클라이언트 딕셔너리를 단순 병합해 키 이름이 겹치는 3개(`applicant_search`, `free_search`, `application_number_search`) 한국 클라이언트가 해외 클라이언트에 덮어써짐 → `korean_`/`foreign_` 접두사로 네임스페이스 분리
- (실제 KIPRIS API로 라이브 검증 중 발견) `patent_detail_search`에서 `claim`/`astrtCont`처럼 여러 항목을 `"\n\n"`으로 합친 필드가 마크다운 표 셀 안에 개행 문자를 그대로 포함해, 청구항 7개짜리 실제 특허로 테스트하니 표가 13줄짜리 깨진 표로 렌더링됨 → 구분자를 공백으로 바꾸고 원본 텍스트의 개행도 정리
- (동일 라이브 검증) 존재하지 않는 출원번호로 조회하면 KIPRIS가 에러 없이 `resultCode=00`과 함께 모든 필드가 `null`인 `item`을 반환해, 기존 `response.empty` 체크로는 못 잡고 빈 값으로 채워진 표가 나감 → `biblioSummaryInfoArray`(모든 정상 특허에 존재) 부재 여부로 "결과 없음"을 판별하는 `_item_has_data()` 추가
- (17개 툴 전체를 실제 API로 재검증하며 발견, 2026-08-01) KIPRIS는 공동출원인/공동발명자가 있으면 한 필드 안에 `"삼성전자주식회사|전남대학교산학협력단"`처럼 **파이프(`|`) 문자로 값을 구분**해서 줌. 마크다운 표에서 `|`는 컬럼 구분자라서, `patent_applicant_search`/`agent_search`/`foreign_patent_applicant_search`/`foreign_patent_free_search` 등 다수 툴에서 공동출원 특허가 하나라도 섞이면 표가 깨짐(16개 파일, 31개 `to_markdown()` 호출 지점 전부 동일하게 취약했음) → `ToolHandler.format_table()` 공통 헬퍼를 추가해 `|`→`/`, 개행→공백으로 정리한 뒤 렌더링하도록 전체 교체
- (동일 라이브 검증, 미해결) `abs_class.py`의 `parse_response()`가 KIPRIS API 에러(`resultCode != "00"`, 예: 코드 31 `DEADLINE_EXPIRED`)를 감지하면 `logger.warning`만 남기고 빈 `DataFrame`을 반환함 → 모든 툴이 "실제 에러"와 "매칭 결과 0건"을 구분 못 하고 똑같이 "no result"를 보여줌. 실제로 `trademark_search`를 라이브 검증하는 중 발견 — 이 API 키가 `trademarkInfoSearchService`에 대해 코드 31을 반환해 "삼성"/"SAMSUNG" 등 어떤 검색어를 넣어도 "there is no result"만 나오는데, 이게 정말 매칭이 없는 건지 키/서비스 권한 문제인지 사용자는 알 길이 없음. 수정 방향은 논의 필요(예: 코드 20 `NO_RESULTS`만 빈 결과로 처리하고 나머지는 `kipris/errors.py`의 `KiprisApiError`를 raise — 각 툴의 기존 `except Exception` 블록이 이미 있어 별도 수정 없이 자연스럽게 사용자에게 실제 에러 메시지가 노출됨)

### 🔄 진행 중인 작업
- ~~LSP 오류 해결 (의존성 문제)~~ ✅ 해결됨
- 코드 품질 개선 — `ruff`는 CI에서 강제되고 클린하지만, `pyright`는 CI에 연결되어 있지 않고 현재 76개 타입 오류가 있음(주로 `patent_sim.py`, `sse_server.py`). "타입 안정성 적용"은 게이트가 아니라 의존성 설치 수준
- ~~배포 자동화~~ ✅ 해결됨 — `publish.yml`이 버전 태그 push 시 OIDC 기반 PyPI 배포 + GitHub Release 생성을 자동화

---

## 📈 향후 개선 방향

### 1. 기능 확장
- 실시간 특허 알림 기능
- 특허 분석 및 시각화
- 대규모 데이터 처리 최적화

### 2. 인프라 개선
- Kubernetes 배포 지원
- 모니터링 대시보드
- CI/CD 파이프라인 구축

### 3. 사용자 경험
- 웹 기반 관리 인터페이스
- API 사용량 대시보드
- 상세한 에러 리포팅

---

## 🎯 결론

MCP KIPRIS 프로젝트는 **프로덕션 레벨의 안정성과 보안성**을 갖춘 특허 검색 MCP 서버입니다. **17개의 완전한 툴**(한국 특허·상표 12개 + 해외 특허 5개, 이 중 `patent_search` 1개는 하위 호환용 deprecated 별칭)과 **15개국 해외 특허 지원**을 통해 강력한 특허 검색 기능을 제공하며, **최신 보안 기능과 안정성 메커니즘**으로 실제 운영 환경에서도 신뢰성 있는 서비스를 보장합니다.

현재 프로젝트는 안정적인 상태를 유지하고 있으며, 지속적인 개선을 통해 더욱 강력한 특허 검색 솔루션으로 발전할 잠재력을 가지고 있습니다.