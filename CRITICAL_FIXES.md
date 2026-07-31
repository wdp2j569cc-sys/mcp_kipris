# MCP KIPRIS 긴급 수정 제안

## 🚨 즉시 수정 필요

### 1. server.py 완전 재작성

```python
# 현재 server.py의 문제점들:
# - app 정의 안됨
# - tool_handlers 초기화 안됨  
# - logger 정의 안됨
# - api_key 정의 안됨
# - 중복 import 존재

# 수정된 server.py 예시:
import datetime
import logging
import os
import sys
from collections.abc import Sequence
from typing import Dict

from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

from mcp_kipris.kipris.abc import ToolHandler
from mcp_kipris.kipris.api_client_factory import get_api_client_factory
from mcp_kipris.kipris.errors import KiprisApiError
from mcp_kipris.kipris.tools import (
    # ... tool imports
)

# 🔧 필수 수정점 1: app 객체 초기화
app = Server("mcp-kipris")

# 🔧 필수 수정점 2: logger 초기화
logger = logging.getLogger("mcp-kipris")

# 🔧 필수 수정점 3: tool_handlers 초기화
tool_handlers: Dict[str, ToolHandler] = {}

# 🔧 필수 수정점 4: api_key 초기화
load_dotenv()
api_key = os.getenv("KIPRIS_API_KEY")

if not api_key:
    logger.error("KIPRIS_API_KEY environment variable is required")
    sys.exit(1)

def add_tool_handler(tool_class: ToolHandler):
    global tool_handlers
    tool_handlers[tool_class.name] = tool_class
    logger.info(f"Tool handler added: {tool_class.name}")

def get_tool_handler(name: str) -> ToolHandler | None:
    global tool_handlers
    logger.info(f"Tool handler find: {name}")
    if name not in tool_handlers:
        return None
    logger.info(f"Tool handler found: {name}")
    return tool_handlers[name]

# 툴 핸들러 등록
add_tool_handler(KoreanPatentApplicantSearchTool())
# ... other tools

@app.list_tools()
async def list_tools() -> list[Tool]:
    logger.info(f"Tool handler list: {tool_handlers.values()}")
    return [tool.get_tool_description() for tool in tool_handlers.values()]

@app.call_tool()
async def call_tool(tool_name: str, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    if not isinstance(args, dict):
        raise RuntimeError("arguments must be dictionary")

    tool_handler = get_tool_handler(tool_name)
    if not tool_handler:
        raise ValueError(f"Unknown tool: {tool_name}")

    try:
        # API 클라이언트 팩토리 초기화
        api_client_factory = get_api_client_factory(api_key)
        logger.info("API client factory initialized successfully")
        
        # 비동기 실행 시도
        logger.info(f"비동기 실행 시작: {tool_name}")
        start_time = datetime.datetime.now()
        
        try:
            result = await tool_handler.run_tool_async(args)
        except (AttributeError, NotImplementedError) as e:
            logger.warning(f"비동기 메서드 실패, 동기 메서드로 폴백: {str(e)}")
            result = tool_handler.run_tool(args)
        
        end_time = datetime.datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()
        logger.info(f"도구 실행 완료: {tool_name}, 소요시간: {elapsed_time:.2f}초")
        
        return result
    except Exception as e:
        logger.error(f"도구 실행 중 오류 발생: {str(e)}")
        raise RuntimeError(f"Caught Exception. Error: {str(e)}")

async def main():
    logger.info("Starting MCP KIPRIS server...")
    
    try:
        # stdio 서버 시작
        async with stdio_server() as (read_stream, write_stream):
            logger.info("stdio_server initialized")
            init_options = app.create_initialization_options()
            logger.info(f"Initialization options created: {init_options}")
            await app.run(read_stream, write_stream, init_options)
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        raise RuntimeError(f"Caught Exception. Error: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 2. 통합 서버 모드 제안

```python
# unified_server.py - 단일 진입점
import argparse
import asyncio

async def main():
    parser = argparse.ArgumentParser(description="MCP KIPRIS Server")
    parser.add_argument("--mode", choices=["stdio", "sse"], default="stdio", help="Server mode")
    parser.add_argument("--port", type=int, default=6274, help="Port for SSE mode")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE mode")
    
    args = parser.parse_args()
    
    if args.mode == "sse":
        from mcp_kipris.sse_server import main as sse_main
        await sse_main()
    else:
        from mcp_kipris.server import main as stdio_main
        await stdio_main()

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. 테스트 스크립트

```bash
#!/bin/bash
# test_mcp_server.sh

echo "🧪 MCP KIPRIS 서버 테스트 시작..."

# 환경변수 확인
if [ -z "$KIPRIS_API_KEY" ]; then
    echo "❌ KIPRIS_API_KEY가 설정되지 않음"
    exit 1
fi

echo "✅ 환경변수 확인 완료"

# stdio 모드 테스트
echo "📡 stdio 모드 테스트..."
timeout 10s python -m mcp_kipris.server || echo "⚠️ stdio 모드 타임아웃"

# SSE 모드 테스트  
echo "🌐 SSE 모드 테스트..."
python -m mcp_kipris.sse_server --http --port $((PORT)) &
SERVER_PID=$!
sleep 5

# 도구 목록 확인
curl -s http://localhost:$PORT/tools | jq . > /tmp/tools_response.json
if [ $? -eq 0 ]; then
    echo "✅ /tools 엔드포인트 정상"
else
    echo "❌ /tools 엔드포인트 실패"
fi

# 세션 생성 테스트
curl -s -N http://localhost:$PORT/messages/ | head -5 > /tmp/sse_response.txt
if [ $? -eq 0 ]; then
    echo "✅ SSE 엔드포인트 정상"
else
    echo "❌ SSE 엔드포인트 실패"
fi

# 정리
kill $SERVER_PID 2>/dev/null
echo "🧹 테스트 완료"
```

## 🔧 즉시 실행 명령어

```bash
# 1. LSP 오류 확인 및 수정
echo "🔍 현재 LSP 오류:"
python -c "import mcp_kipris.server" 2>&1 | head -10

# 2. 수정된 server.py로 테스트
echo "🧪 수정된 서버 테스트:"
KIPRIS_API_KEY="test_key" python -m mcp_kipris.server --help

# 3. SSE 서버 테스트 (현재 안정적)
echo "🌐 SSE 서버 테스트:"
python -m mcp_kipris.sse_server --http --port 6274 &
curl -s http://localhost:6274/tools | jq .

# 4. 의존성 확인
echo "📦 의존성 확인:"
pip list | grep -E "(mcp|requests|pandas|xmltodict)"
```

## ⚡ 즉시 조치할 우선순위

1. **🚨 server.py 수정**: LSP 오류 해결 (30분)
2. **🧪 기본 테스트**: 서버 시작 확인 (15분) 
3. **🌐 SSE 서버 확인**: 현재 상태 검증 (10분)
4. **📚 문서 업데이트**: 구동 방법 수정 (20분)

**총 소요시간**: 약 1시간 15분