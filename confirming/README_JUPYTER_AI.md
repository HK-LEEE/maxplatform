# 🤖 Jupyter AI 통합 플랫폼

사용자별 워크스페이스에서 AI Agent 기능을 제공하는 JupyterLab 플랫폼입니다.

## 🚀 **주요 특징**

- ✅ **사용자별 독립 워크스페이스**: 완전 격리된 Jupyter 환경
- ✅ **통합 Jupyter AI**: 공식 Jupyter AI Extension 사용
- ✅ **다중 AI 프로바이더**: OpenAI, Anthropic, Google Gemini, GPT4All
- ✅ **.env 기반 중앙 관리**: API 키 및 모델 제한 설정
- ✅ **자동 AI 설정**: 워크스페이스 생성 시 AI 자동 구성

## 📦 **설치 방법**

### **1. 자동 설치 (권장)**
```bash
# Windows
install_jupyter_ai.bat

# 또는 수동 설치
cd backend
pip install -r requirements.txt
```

### **2. 필수 패키지 목록**
```
# Jupyter 핵심
jupyterlab==4.0.9
jupyter-ai==2.25.0

# AI 프로바이더
openai==1.35.0
anthropic==0.25.0
google-generativeai==0.5.4
gpt4all==2.5.4

# LangChain 지원
langchain-core==0.1.52
langchain-openai==0.1.8
langchain-anthropic==0.1.11
```

## ⚙️ **설정**

### **1. API 키 설정 (backend/.env)**
```bash
# OpenAI (선택사항)
OPENAI_API_KEY=sk-your-openai-key-here
AI_OPENAI_MODELS=gpt-3.5-turbo,gpt-4

# Anthropic (선택사항)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
AI_ANTHROPIC_MODELS=claude-3-sonnet,claude-3-haiku

# Google Gemini (선택사항)
GOOGLE_API_KEY=your-google-api-key-here
AI_GOOGLE_MODELS=gemini-pro

# 기본 로컬 모델 (API 키 불필요)
AI_DEFAULT_PROVIDER=gpt4all
AI_DEFAULT_MODEL=gpt4all:orca-mini-3b-gguf2-q4_0

# AI 사용 제한
AI_MAX_TOKENS=1000
AI_TEMPERATURE=0.7
AI_MAX_CHAT_HISTORY=10
```

### **2. 데이터베이스 설정**
```bash
# MySQL (기본)
DATABASE_URL=mysql+pymysql://test:test@localhost/jupyter_platform

# 또는 MSSQL
DATABASE_URL=mssql+pyodbc://sa:password@localhost:1433/jupyter_platform?driver=ODBC+Driver+17+for+SQL+Server
```

## 🚀 **사용 방법**

### **1. 서버 시작**
```bash
# 백엔드 서버
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 프론트엔드 (별도 터미널)
cd frontend
npm run dev
```

### **2. 워크스페이스 생성**
1. 웹 인터페이스에서 사용자 등록/로그인
2. 새 워크스페이스 생성
3. 자동으로 Jupyter AI 설정 구성

### **3. AI 사용**

#### **채팅 인터페이스**
- JupyterLab 좌측 사이드바 → "Jupyter AI Chat"
- 실시간 AI 대화

#### **매직 커맨드**
```python
# 기본 AI 대화
%%ai
파이썬으로 데이터 분석 코드를 작성해줘

# 특정 모델 지정
%%ai openai-chat:gpt-3.5-turbo
머신러닝 모델 학습 방법을 알려줘

# 코드만 생성
%%ai anthropic-chat:claude-3-sonnet -f code
CSV 파일을 읽어서 그래프 그리는 함수

# 로컬 모델 (API 키 불필요)
%%ai gpt4all:orca-mini-3b-gguf2-q4_0
파이썬 기초 문법 설명해줘
```

## 🔧 **지원되는 AI 프로바이더**

| 프로바이더 | 모델 | API 키 필요 | 특징 |
|------------|------|-------------|------|
| **OpenAI** | GPT-3.5, GPT-4 | ✅ | 높은 품질, 빠른 응답 |
| **Anthropic** | Claude-3 시리즈 | ✅ | 안전성, 긴 컨텍스트 |
| **Google** | Gemini Pro | ✅ | 멀티모달 지원 |
| **GPT4All** | Orca-Mini | ❌ | 로컬 실행, 프라이버시 |
| **Ollama** | Llama, Mistral | ❌ | 커스텀 모델 |

## 🛡️ **보안 기능**

- **사용자별 격리**: 완전 독립된 워크스페이스
- **API 키 중앙 관리**: .env 파일에서 안전하게 관리
- **사용량 제한**: 토큰 수, 대화 기록 제한
- **프로바이더 제어**: 관리자가 사용 가능한 모델 제한

## 📁 **프로젝트 구조**

```
📦 Jupyter AI Platform
├── 🔧 backend/
│   ├── app/
│   │   ├── services/
│   │   │   └── jupyter_service.py    # AI 통합 Jupyter 서비스
│   │   └── config.py                 # AI 설정 포함
│   ├── .env                         # AI API 키 및 설정
│   └── requirements.txt             # 업데이트된 패키지 목록
├── 🎨 frontend/
├── 📖 backend/AI_INTEGRATION_GUIDE.md
└── 🚀 install_jupyter_ai.bat
```

## 🚨 **문제 해결**

### **AI 채팅이 보이지 않는 경우**
```bash
# Extension 확인
jupyter labextension list | grep ai

# 재설치
pip install jupyter-ai --force-reinstall
```

### **API 키 오류**
1. `.env` 파일에서 API 키 형식 확인
2. 키 앞의 공백이나 따옴표 제거
3. 워크스페이스 재시작

### **모델 응답 없음**
1. 네트워크 연결 확인
2. API 키 잔액 확인
3. 토큰 제한 설정 확인

## 📋 **설치 확인**

```bash
# 패키지 설치 확인
pip list | grep -E "(jupyter-ai|langchain|openai|anthropic)"

# Extension 활성화 확인
jupyter labextension list

# 사용 가능한 모델 확인
python -c "from jupyter_ai import __version__; print(f'Jupyter AI: {__version__}')"
```

## 🎯 **다음 단계**

1. **API 키 설정**: `.env` 파일에 실제 API 키 입력
2. **서버 시작**: 백엔드 및 프론트엔드 실행
3. **워크스페이스 생성**: 웹 인터페이스에서 생성
4. **AI 사용**: JupyterLab에서 채팅 또는 매직 커맨드 사용

---

**✨ 이제 공식 Jupyter AI Extension을 사용한 완전한 AI 통합 환경이 준비되었습니다!** 