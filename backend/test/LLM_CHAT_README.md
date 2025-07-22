# 🤖 LLM Chat Assistant for Jupyter Lab

Jupyter Lab에 통합된 LLM 채팅 어시스턴트로, Continue나 Cursor AI와 유사한 코드 분석 및 개선 기능을 제공합니다.

## 📋 기능 개요

### 🎯 주요 기능
- **💬 실시간 채팅**: Azure OpenAI(GPT-4o) 또는 Ollama 로컬 LLM과 대화
- **📊 코드 분석**: 현재 Jupyter 셀의 코드를 분석하고 피드백 제공  
- **🔧 코드 개선**: 코드 최적화 및 개선 제안
- **🎛️ 다중 LLM 지원**: Azure OpenAI와 Ollama 간 실시간 전환
- **📱 반응형 UI**: 크기 조절 가능한 사이드바 형태

### 🔧 지원 LLM 제공자
1. **Azure OpenAI**
   - GPT-4o 모델 지원
   - 기업용 환경에 최적화
   - API 키 설정 필요

2. **Ollama** 
   - 로컬 LLM 실행
   - 프라이버시 보장
   - 다양한 모델 지원 (llama3.2, codellama 등)

## 🚀 설치 및 설정

### 1. 백엔드 패키지 설치

```bash
cd backend
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```env
# Azure OpenAI 설정 (선택사항)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Ollama 설정
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2

# LLM 일반 설정
DEFAULT_LLM_PROVIDER=ollama
MAX_TOKENS=4000
TEMPERATURE=0.1
```

### 3. Ollama 설치 및 실행 (로컬 LLM 사용 시)

```bash
# Ollama 설치 (Windows)
curl -fsSL https://ollama.ai/install.sh | sh

# 모델 다운로드
ollama pull llama3.2
ollama pull codellama

# Ollama 서버 실행
ollama serve
```

### 4. 백엔드 서버 실행

```bash
cd backend
python main.py
```

## 💻 사용 방법

### 1. 기본 채팅

1. **채팅창 열기**: Jupyter Lab에서 자동으로 오른쪽에 채팅창이 나타납니다
2. **LLM 선택**: 상단의 Provider 드롭다운에서 Azure 또는 Ollama 선택
3. **모델 선택**: Model 드롭다운에서 사용할 모델 선택
4. **메시지 입력**: 하단 입력창에 질문 작성 후 Enter 또는 전송 버튼 클릭

### 2. 코드 분석

1. **Jupyter 셀 선택**: 분석하고 싶은 코드가 있는 셀 클릭
2. **코드 분석 버튼**: 채팅창의 "📊 코드 분석" 버튼 클릭
3. **결과 확인**: AI가 코드의 기능, 문제점, 개선사항을 분석해서 제공

### 3. 코드 개선

1. **Jupyter 셀 선택**: 개선하고 싶은 코드가 있는 셀 클릭  
2. **코드 개선 버튼**: 채팅창의 "🔧 코드 개선" 버튼 클릭
3. **개선 제안**: AI가 최적화된 코드와 변경 이유를 제공

### 4. 채팅창 제어

- **크기 조절**: 채팅창 왼쪽 경계를 드래그하여 너비 조절
- **열기/닫기**: 우상단의 "🤖 LLM Chat" 버튼으로 토글
- **대화 지우기**: "🗑️ 대화 지우기" 버튼으로 히스토리 초기화

## 🎯 고급 기능

### 프로그래밍 방식 접근

Jupyter 셀에서 직접 LLM Chat을 활성화:

```python
# LLM Chat 설정 실행
exec(open('jupyter_custom.py').read())
```

### 수동 채팅 페이지 접근

브라우저에서 직접 접근:
```
http://localhost:8000/api/llm/chat-ui
```

### API 엔드포인트

- **채팅**: `POST /api/llm/chat`
- **코드 분석**: `POST /api/llm/analyze-code`  
- **코드 개선**: `POST /api/llm/improve-code`
- **제공자 목록**: `GET /api/llm/providers`
- **모델 목록**: `GET /api/llm/models`

## 🛠️ 트러블슈팅

### 1. "LLM 제공자 목록을 로드할 수 없습니다"
- 백엔드 서버가 실행 중인지 확인
- 인증 토큰이 유효한지 확인
- 네트워크 연결 상태 점검

### 2. "Azure OpenAI 사용 불가"
- `.env` 파일에 API 키와 엔드포인트가 올바르게 설정되었는지 확인
- Azure OpenAI 리소스의 배포 상태 확인

### 3. "Ollama 연결 실패"
```bash
# Ollama 서비스 상태 확인
ollama list

# Ollama 재시작
pkill ollama
ollama serve
```

### 4. "코드 분석/개선 버튼이 작동하지 않음"
- Jupyter 셀이 선택되었는지 확인
- 셀에 코드가 작성되어 있는지 확인
- 수동으로 코드를 복사-붙여넣기로 시도

## 🎨 UI 커스터마이징

### 채팅창 크기 기본값 변경

`jupyter_custom.py`에서 수정:

```python
# 기본 너비 변경 (픽셀)
width: 500px;  # 400px에서 500px로 변경
```

### 다크 테마 지원

Jupyter Lab의 다크 테마에 자동으로 적응됩니다.

## 🔒 보안 고려사항

- **API 키 보안**: `.env` 파일을 버전 관리에 포함하지 마세요
- **CORS 설정**: 프로덕션 환경에서는 CORS 설정을 더 엄격하게 구성
- **토큰 관리**: JWT 토큰의 만료 시간을 적절히 설정

## 📈 성능 최적화

### 로컬 LLM (Ollama) 최적화
- **GPU 사용**: NVIDIA GPU가 있다면 CUDA 지원 버전 설치
- **모델 크기**: 시스템 사양에 맞는 모델 선택
- **메모리**: 최소 8GB RAM 권장

### Azure OpenAI 최적화  
- **토큰 제한**: `MAX_TOKENS` 설정으로 비용 관리
- **Temperature**: 코드 분석에는 낮은 값(0.1) 권장

## 🤝 기여하기

이 프로젝트는 오픈소스이며, 기여를 환영합니다!

1. Fork 생성
2. Feature 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙋‍♂️ 지원

문제가 발생하거나 질문이 있으시면:

1. **GitHub Issues**: 버그 리포트 및 기능 요청
2. **Wiki**: 상세한 설정 가이드
3. **Discussions**: 사용법 질문 및 팁 공유

---

**즐거운 코딩 되세요! 🎉** 