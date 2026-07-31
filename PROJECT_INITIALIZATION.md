# MCP KIPRIS 프로젝트 초기화 가이드

## 📋 프로젝트 개요

### 프로젝트명
**MCP KIPRIS** - 한국특허정보원(KIPRIS) API를 활용한 특허 검색 MCP(Model Context Protocol) 서버

### 주요 기능
- **한국 특허 검색**: 출원인, 키워드, 출원번호, 권리자, 상세 정보, 요약 정보 검색
- **해외 특허 검색**: 15개국 특허 정보 검색 (미국, 유럽, 일본, 중국 등)
- **MCP 서버**: stdio 및 HTTP(SSE) 모드 지원
- **보안 기능**: API 키 마스킹, Rate limiting, 재시도/백오프 메커니즘

---

## 🚀 초기화 절차

### 1. 시스템 요구사항

```bash
# Python 버전 확인
python --version  # 3.12 이상 필요
```

### 2. 환경 설정

#### 2.1. 가상환경 생성
```bash
# 프로젝트 디렉토리로 이동
cd /Users/nuri/dev/git/mcp_kipris

# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
# Linux/Mac
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

#### 2.2. 환경 변수 설정
```bash
# API 키 설정 (필수)
export KIPRIS_API_KEY="your_api_key_here"

# 로그 레벨 설정 (선택)
# 프로덕션: INFO, 개발: DEBUG
export LOG_LEVEL=INFO
```

⚠️ **중요**: API 키는 `src/.env` 파일에 이미 설정되어 있으나, 보안을 위해 환경 변수 사용을 권장합니다.

### 3. 의존성 설치

#### 3.1. 프로젝트 설치
```bash
# 개발 모드 설치
pip install -e .

# 또는 requirements.txt로 설치
pip install -r requirements.txt
```

#### 3.2. 개발 의존성 설치
```bash
# Linting 및 타입 체크 도구
pip install ruff pyright
```

### 4. 설정 파일 확인

#### 4.1. 주요 설정 파일
- `pyproject.toml`: 프로젝트 설정, 의존성, Ruff 설정
- `requirements.txt`: 전체 의존성 목록
- `.gitignore`: Git 무시 파일 목록
- `src/.env`: API 키 설정 (로컬 전용)

#### 4.2. 코드 품질 설정
```bash
# 코드 포맷팅 (Ruff)
ruff format .

# 코드 검사 (Ruff)
ruff check .

# 타입 체크 (Pyright)
pyright src/
```

---

## 🏗️ 프로젝트 구조

### 디렉토리 구조
```
mcp_kipris/
├── README.md                 # 사용자 문서
├── pyproject.toml           # 프로젝트 설정
├── requirements.txt         # 의존성 목록
├── project_spec.md          # 프로젝트 개선 기록
├── assets/                  # 이미지/자산
│   └── Claude-settings.png
├── src/                     # 소스 코드
│   └── mcp_kipris/
│       ├── __init__.py
│       ├── _version.py      # 버전 정보
│       ├── server.py        # stdio MCP 서버
│       ├── sse_server.py    # HTTP(SSE) 서버
│       ├── .env             # 로컬 환경 변수
│       └── kipris/
│           ├── __init__.py
│           ├── abc.py        # 툴 핸들러 추상 클래스
│           ├── api_client_factory.py  # API 클라이언트 팩토리
│           ├── rate_limiter.py      # Rate limiting
│           ├── logging_utils.py     # 보안 로깅
│           ├── errors.py            # 오류 처리
│           ├── api/          # API 클라이언트
│           │   ├── __init__.py
│           │   ├── abs_class.py
│           │   ├── utils.py
│           │   ├── korean/     # 한국 특허 API
│           │   └── foreign/    # 해외 특허 API
│           └── tools/       # MCP 툴
│               ├── __init__.py
│               ├── code.py
│               ├── korean/     # 한국 특허 툴
│               └── foreign/    # 해외 특허 툴
├── Dockerfile.stdio         # stdio 모드 Dockerfile
├── Dockerfile.sse           # HTTP 모드 Dockerfile
└── sse_server_build.sh      # 서버 빌드 스크립트
```

---

## 🛠️ 실행 방법

### 1. stdio 모드 (기본)
```bash
# MCP 서버 시작
python -m mcp_kipris.server
```

### 2. HTTP/SSE 모드
```bash
# HTTP 서버 시작
python -m mcp_kipris.sse_server --http --port 6274 --host 0.0.0.0
```

### 3. Docker 실행
```bash
# stdio 모드 Docker
docker build -f Dockerfile.stdio -t mcp-kipris-stdio .
docker run mcp-kipris-stdio

# HTTP 모드 Docker
docker build -f Dockerfile.sse -t mcp-kipris-sse .
docker run -p 6274:6274 mcp-kipris-sse
```

---

## 🔧 개발 환경 설정

### 1. IDE 설정
```bash
# VS Code 설정 (이미 설정됨)
# .vscode/settings.json 참조
```

### 2. Linting 설정 (pyproject.toml)
- 라인 길이: 120자
- 들여쓰기: 4스페이스
- 따옴표: 더블 쿼트

### 3. 테스트 실행
```bash
# pytest 실행
pytest

# 비동기 테스트
pytest --asyncio-mode=auto
```

---

## 🔍 API 사용 예제

### 1. 클라이언트 연결 확인
```bash
# 도구 목록 조회 (HTTP 모드)
curl http://localhost:6274/tools | jq .
```

### 2. 특허 검색 예제
```bash
# SSE 세션 연결
curl -N http://localhost:6274/messages/

# 출원인 검색
curl -X POST "http://localhost:6274/messages/?session_id=<session_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "tool",
    "name": "patent_applicant_search",
    "args": {
      "applicant": "삼성전자",
      "docs_count": 5
    }
  }'
```

---

## 📝 주요 기능 상세

### 1. 한국 특허 검색 툴
- `patent_applicant_search`: 출원인 기준 검색
- `patent_keyword_search`: 키워드 기준 검색
- `patent_application_number_search`: 출원번호 검색
- `patent_righter_search`: 권리자 기준 검색
- `patent_summary_search`: 요약 정보 검색
- `patent_detail_search`: 상세 정보 검색

### 2. 해외 특허 검색 툴
- `foreign_patent_applicant_search`: 출원인 기준 검색
- `foreign_patent_application_number_search`: 출원번호 검색
- `foreign_patent_free_search`: 자유 텍스트 검색
- `foreign_patent_international_application_number_search`: 국제출원번호 검색
- `foreign_patent_international_open_number_search`: 국제공개번호 검색

### 3. 보안 기능
- **API 키 마스킹**: 로그에서 민감 정보 자동 제거
- **Rate Limiting**: 분당 60개 요청 제한
- **재시도 메커니즘**: 지수 백오프로 안정적인 요청 처리
- **환경 인식 로깅**: 프로덕션/개발 환경별 로그 레벨 조정

---

## 🚨 주의사항

### 1. 보안
- API 키를 절대 코드에 하드코딩하지 마세요
- `src/.env` 파일은 버전 관리에서 제외됩니다
- 프로덕션 환경에서는 환경 변수 사용을 권장합니다

### 2. Rate Limiting
- KIPRIS API는 분당 60개 요청으로 제한됩니다
- 자동으로 Rate limiting이 적용되지만, 대량 요청 시 주의가 필요합니다

### 3. 의존성
- Python 3.12 이상이 필요합니다
- 일부 의존성은 시스템별 설치가 필요할 수 있습니다

---

## 📚 추가 리소스

### 1. 문서
- `README.md`: 사용자 가이드 및 API 예제
- `project_spec.md`: 프로젝트 개선 이력

### 2. 외존 정보
- [KIPRIS API 공식 문서](https://www.kipris.or.kr/)
- [MCP 프로토콜 문서](https://modelcontextprotocol.io/)

### 3. 지원 국가
- US, EP, WO, JP, PJ, CP, CN, TW, RU, CO, SE, ES, IL

---

## ✅ 초기화 체크리스트

- [ ] Python 3.12+ 설치 확인
- [ ] 가상환경 생성 및 활성화
- [ ] KIPRIS API 키 설정
- [ ] 의존성 설치 (`pip install -e .`)
- [ ] 코드 품질 도구 설치 (ruff, pyright)
- [ ] 서버 실행 테스트 (stdio/HTTP 모드)
- [ ] API 연결 테스트
- [ ] 로그 레벨 확인
- [ ] Docker 빌드 테스트 (선택)

---

이 가이드를 따라 프로젝트를 성공적으로 초기화하면 KIPRIS 특허 검색 MCP 서버를 사용할 수 있습니다.