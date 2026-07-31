# MCP Kipris Test Directory

이 디렉토리는 두 종류의 테스트를 포함합니다.

- **`unit/`** — 실제 네트워크 호출 없이 동작하는 pytest 단위 테스트. `KIPRIS_API_KEY`가 없어도 실행되며(`conftest.py`가 더미 값을 채워줌), `pytest.mark.unit`로 마킹되어 있습니다. KIPRIS API를 호출하는 부분은 `monkeypatch`로 목(mock) 처리합니다.
- **루트의 `test_*.py`** — 실제 KIPRIS API를 호출하는 라이브 테스트/데모 스크립트. `pytest.mark.integration`로 마킹된 것은 `pytest`로 수집되어 실행되고, 나머지는 `if __name__ == "__main__":` 가드가 걸린 독립 실행 스크립트입니다.

```bash
# 단위 테스트만 실행 (네트워크 불필요, 빠름)
pytest test/unit -v

# integration 테스트 제외하고 전체 실행
pytest test/ -m "not integration" -v

# 커버리지 포함 전체 실행 (CI와 동일, KIPRIS_API_KEY 필요)
pytest test/ -v --cov=src/mcp_kipris --cov-report=term-missing
```

## 테스트 파일 목록

- `test_samsung_patents.py`: 삼성전자 특허 검색 (출원인 검색) 테스트
- `test_patent_keyword_search.py`: 키워드 기반 특허 검색 테스트
- `test_patent_detail_search.py`: 특허 상세 정보 검색 테스트
- `test_patent_summary_search.py`: 특허 요약 정보 검색 테스트
- `test_application_number_search.py`: 출원번호 기반 특허 검색 테스트
- `test_righter_search.py`: 권리자 기반 특허 검색 테스트
- `test_patent_search.py`: 기본 특허 검색 기능 테스트

## 실행 방법

각 테스트 파일은 독립적으로 실행할 수 있습니다. 프로젝트 루트 디렉토리에서 다음과 같이 실행하세요:

```bash
# 가상환경 활성화 (필요한 경우)
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 개별 테스트 실행
python test/test_samsung_patents.py
python test/test_patent_keyword_search.py
# 기타 테스트 파일들...
```

## 참고 사항

1. 각 테스트 스크립트는 동기 및 비동기 API 호출 방식을 모두 테스트합니다.
2. 테스트를 실행하기 전에 `src/.env` 파일에 `KIPRIS_API_KEY`가 설정되어 있어야 합니다.
3. 테스트 결과는 콘솔에 출력됩니다.
4. 각 스크립트는 독립적으로 실행 가능하도록 설계되었습니다.

## 사전 준비사항

1. `.env` 파일이 `src` 디렉토리에 있고, 그 안에 `KIPRIS_API_KEY`가 설정되어 있어야 합니다.
2. 프로젝트의 의존성 패키지가 설치되어 있어야 합니다.

## 테스트 스크립트 목록

### 1. 출원인 검색 테스트

출원인 이름으로 최신 특허를 검색하는 테스트입니다.

```bash
python test_samsung_patents.py
```

### 2. 키워드 검색 테스트

키워드로 특허를 검색하는 테스트입니다.

```bash
python test_patent_keyword_search.py
```

### 3. 특허 상세 정보 조회 테스트

특허 출원번호로 상세 정보를 조회하는 테스트입니다.

```bash
python test_patent_detail.py
```

## 테스트 결과

각 테스트 스크립트는 검색 결과를 콘솔에 출력합니다. 결과가 JSON 형식일 경우, 구조화된 형태로 출력됩니다.

## 추가 테스트 작성 방법

새로운 테스트를 작성할 때는 다음 구조를 따르는 것이 좋습니다:

1. `project_root`를 설정하여 상대 경로 문제 해결
2. `.env` 파일 로드
3. 적절한 도구 클래스 import 및 인스턴스화
4. 검색 파라미터 설정 및 `run_tool` 메서드 호출
5. 결과 처리 및 출력

## 문제 해결

테스트 실행 중 오류가 발생할 경우:

1. API 키가 올바르게 설정되었는지 확인
2. 가상 환경이 활성화되어 있는지 확인
3. 모든 의존성 패키지가 설치되어 있는지 확인
