# MCP KIPRIS: 스킬 vs 플러그인 vs 확장 vs MCP 서버

## 🤔 용어 정리 및 정확한 구분

### **현재 상황: MCP 서버**

MCP KIPRIS 프로젝트는 **"MCP 서버"** 입니다:

```python
# 현재: 독립 실행형 MCP 서버
python -m mcp_kipris.server  # stdio 서버
python -m mcp_kipris.sse_server  # HTTP 서버
```

- **MCP 서버**: Model Context Protocol 서버로서, 다른 프로그램이 호출할 수 있는 API 제공
- **독립 프로세스**: 자체적으로 실행되는 별도의 서버 프로그램
- **통신 방식**: stdio, SSE, HTTP로 다른 클라이언트와 통신

---

## 📚 플랫폼별 용어 차이

### **1. VS Code 생태계 (Cursor 포함)**
```
확장(Extension) = 플러그인(Plugin) = Add-on
```

**VS Code/Cursor 확장 구조:**
```json
// package.json
{
  "name": "kipris-patent-search",
  "contributes": {
    "commands": [...],
    "views": [...],
    "configuration": {
      "mcpServers": {  // MCP 서버 연동
        "kipris": {
          "command": "python",
          "args": ["-m", "mcp_kipris.server"]
        }
      }
    }
  }
}
```

### **2. OpenCode 생태계**
```
MCP 서버 = 기능 확장 단위
```

**OpenCode 설정:**
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "kipris": {  // MCP 서버 등록
      "type": "local",
      "command": ["python", "-m", "mcp_kipris.server"]
    }
  }
}
```

### **3. Antigravity 생태계**
```
스킬(Skill) = 에이전트 기능 확장
```

**Antigravity는 에이전트 중심:**
- 전통적인 "확장"보다는 "스킬" 개념 사용
- AI 에이전트에게 새로운 능력 부여하는 방식

### **4. Gemini Code 생태계**
```
확장(Extension) = VS Code 확장 기반
```

**Gemini Code 통합:**
- VS Code 확장 형태
- 내부적으로 Gemini API와 연동

---

## 🎯 MCP KIPRIS의 정체성

### **현재: 순수 MCP 서버**
```
┌─────────────────┐    MCP Protocol    ┌─────────────────┐
│   IDE/클라이언트  │ ◄──────────────► │  MCP KIPRIS   │
│  (Cursor/OpenCode)│                  │   서버        │
└─────────────────┘                  └─────────────────┘
```

### **선택지 1: MCP 서버로 유지 (추천)**
✅ **장점:**
- 플랫폼 중립적 (모든 MCP 지원 IDE에서 동작)
- 개발 간단 (MCP SDK만 있으면 됨)
- 표준 프로토콜 (안정적이고 확장성 좋음)

❌ **단점:**
- IDE 네이티브 기능 활용 불가
- 사용자가 수동으로 설정 필요

### **선택지 2: 플랫폼별 확장 개발**
```
┌─────────────────┐    Native API     ┌─────────────────┐
│   Cursor IDE    │ ◄──────────────► │  KIPRIS 확장   │
└─────────────────┘                  └─────────────────┘

┌─────────────────┐    Native API     ┌─────────────────┐
│   OpenCode      │ ◄──────────────► │  KIPRIS 기능    │
└─────────────────┘                  └─────────────────┘
```

✅ **장점:**
- IDE 네이티브 기능 활용 가능
- 더 나은 사용자 경험
- 자동 설치 및 설정

❌ **단점:**
- 플랫폼별로 별도 개발 필요
- 유지보수 복잡
- 각 플랫폼의 API 의존

---

## 🏆 추천: 하이브리드 접근

### **단기: MCP 서버 중심**
1. **MCP 서버 강화**: 현재 MCP 서버를 더욱 안정적으로
2. **설정 자동화**: 각 플랫폼별 설정 가이드 제공
3. **문서화**: 사용자가 쉽게 연동하도록 가이드

### **장기: 선택적 확장**
```
                ┌─────────────────┐
                │   MCP KIPRIS   │
                │     코어       │
                └─────────┬───────┘
                          │
            ┌─────────────┴─────────────┐
            │                          │
    ┌───────▼───────┐      ┌───────▼───────┐
    │ Cursor 확장   │      │OpenCode MCP   │
    │ (UI/UX 강화) │      │ (기본 연동)    │
    └───────────────┘      └───────────────┘
```

---

## 💡 최종 답변

### **MCP KIPRIS는 현재 "MCP 서버" 입니다:**
- **스킬❌**: Antigravity 같은 에이전트 중심 플랫폼의 용어
- **플러그인❌**: VS Code 계열에서는 "확장(Extension)"이라고 부름
- **확장⭕**: 맞지만, 플랫폼 종속적인 용어
- **MCP 서버✅**: 가장 정확하고 플랫폼 중립적인 용어

### **따라서:**
1. **지금은 MCP 서버로 계속 발전시키는 것을 추천**
2. **각 플랫폼에서는 "MCP 서버 연동 설정"을 제공**
3. **필요시 플랫폼별 네이티브 확장을 추가 개발**

이 접근이 **가장 효율적이고 미래 확장성이 좋습니다**.