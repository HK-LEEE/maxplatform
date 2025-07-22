# 🤖 Jupyter AI 통합 가이드

사용자별 워크스페이스에서 AI Agent 기능을 사용하는 방법입니다.

## 🚀 **주요 기능**

- ✅ **사용자별 독립 AI 설정**: 각 워크스페이스마다 별도 AI 설정
- ✅ **.env 기반 모델 제한**: 관리자가 사용 가능한 모델 제어
- ✅ **다중 프로바이더 지원**: OpenAI, Anthropic, Google Gemini, GPT4All, Ollama
- ✅ **자동 설치 및 설정**: 워크스페이스 생성 시 자동 구성

## ⚙️ **설정 방법**

### **1. .env 파일 설정**

```bash
# 기본 제공 모델 (API 키 없이도 사용 가능)
AI_DEFAULT_PROVIDER=gpt4all
AI_DEFAULT_MODEL=gpt4all:orca-mini-3b-gguf2-q4_0

# OpenAI 설정 (선택사항)
OPENAI_API_KEY=your-openai-api-key-here
AI_OPENAI_MODELS=gpt-3.5-turbo,gpt-4

# Anthropic 설정 (선택사항)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
AI_ANTHROPIC_MODELS=claude-3-sonnet,claude-3-haiku

# Google Gemini 설정 (선택사항)
GOOGLE_API_KEY=your-google-api-key-here
AI_GOOGLE_MODELS=gemini-pro

# AI 사용 제한
AI_MAX_TOKENS=1000
AI_TEMPERATURE=0.7
AI_MAX_CHAT_HISTORY=10
AI_ENABLED_FEATURES=chat,completion,learn
```

### **2. 자동 설치**

워크스페이스 생성 시 자동으로:
- Jupyter AI 패키지 설치 확인
- 사용자별 AI 설정 파일 생성
- API 키 환경변수 설정

## 🎯 **사용 방법**

### **1. 채팅 인터페이스**

JupyterLab에서:
1. 좌측 사이드바에서 **"Jupyter AI Chat"** 클릭
2. 실시간 AI 대화 시작
3. 코드 생성, 설명, 디버깅 요청

### **2. 매직 커맨드**

노트북 셀에서 직접 사용:

```python
# 기본 AI 대화
%%ai
파이썬으로 데이터 분석 코드를 작성해줘

# 특정 모델 지정
%%ai openai-chat:gpt-3.5-turbo
머신러닝 모델을 만드는 방법을 알려줘

# 코드만 생성
%%ai anthropic-chat:claude-3-sonnet -f code
CSV 파일을 읽어서 그래프를 그리는 함수

# 현재 노트북 컨텍스트 포함
%%ai --learn-data
이 데이터를 분석해서 인사이트를 찾아줘
```

### **3. 로컬 모델 (GPT4All)**

API 키 없이도 사용 가능:

```python
%%ai gpt4all:orca-mini-3b-gguf2-q4_0
파이썬 기초 문법을 설명해줘
```

## 🔧 **프로바이더별 설정**

### **OpenAI**
- **필요**: `OPENAI_API_KEY`
- **모델**: gpt-3.5-turbo, gpt-4
- **특징**: 높은 품질, 빠른 응답

### **Anthropic Claude**
- **필요**: `ANTHROPIC_API_KEY`
- **모델**: claude-3-sonnet, claude-3-haiku
- **특징**: 안전성 중시, 긴 컨텍스트

### **Google Gemini**
- **필요**: `GOOGLE_API_KEY`
- **모델**: gemini-pro
- **특징**: 멀티모달 지원

### **GPT4All (로컬)**
- **필요**: 없음 (로컬 실행)
- **모델**: orca-mini-3b-gguf2-q4_0
- **특징**: 프라이버시, 오프라인

### **Ollama (로컬)**
- **필요**: Ollama 설치
- **모델**: llama3.2, mistral 등
- **특징**: 커스텀 모델 지원

## 📊 **생성된 설정 파일 예시**

각 워크스페이스의 `.jupyter/jupyter_jupyter_ai_config.json`:

```json
{
  "AiExtension": {
    "default_language_model": "gpt4all:orca-mini-3b-gguf2-q4_0",
    "allowed_providers": [
      "gpt4all",
      "openai-chat",
      "anthropic-chat"
    ],
    "default_max_chat_history": 10,
    "model_parameters": {
      "openai-chat:gpt-3.5-turbo": {
        "temperature": 0.7,
        "max_tokens": 1000
      },
      "anthropic-chat:claude-3-sonnet": {
        "temperature": 0.7,
        "max_tokens": 1000
      }
    }
  }
}
```

## 🛡️ **보안 및 제한**

### **API 키 관리**
- 환경변수로 안전하게 저장
- 사용자별 격리된 환경
- 잘못된 키는 자동으로 제외

### **사용량 제한**
- `AI_MAX_TOKENS`: 응답 최대 토큰 수
- `AI_MAX_CHAT_HISTORY`: 대화 기록 제한
- `AI_TEMPERATURE`: 창의성 수준 제어

### **프로바이더 제한**
- .env에서 허용된 모델만 사용
- API 키가 없으면 해당 프로바이더 비활성화
- 로컬 모델(GPT4All) 기본 제공

## 🚨 **문제 해결**

### **AI 채팅이 보이지 않는 경우**
1. JupyterLab 재시작
2. Jupyter AI 설치 확인: `pip list | grep jupyter-ai`
3. 브라우저 캐시 클리어

### **API 키 오류**
1. .env 파일의 API 키 확인
2. 키 형식 검증 (sk-... 등)
3. 워크스페이스 재시작

### **모델이 응답하지 않는 경우**
1. 모델 파라미터 확인
2. 토큰 제한 확인
3. 로그에서 오류 메시지 확인

## 📋 **설치 확인**

```bash
# 패키지 설치 확인
pip install jupyter-ai[all]

# 설치된 패키지 확인
jupyter labextension list | grep ai

# 사용 가능한 모델 확인
jupyter ai list
```

---

**✨ 이제 각 사용자는 완전히 개인화된 AI Assistant를 워크스페이스에서 사용할 수 있습니다!** 