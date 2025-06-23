# GenbaX Platform 크로스 플랫폼 설정 가이드

이 가이드는 GenbaX Platform을 Windows와 Mac OS 모두에서 실행할 수 있도록 도와줍니다.

## 📋 시스템 요구사항

### 공통 요구사항
- **Python**: 3.8 이상
- **Node.js**: 16 이상
- **npm**: 8 이상
- **데이터베이스**: PostgreSQL, MySQL, 또는 MSSQL 중 하나

### Windows 추가 요구사항
- **Visual Studio Build Tools** (C++ 컴파일러, 일부 Python 패키지용)
- **Git for Windows**

### Mac OS 추가 요구사항
- **Xcode Command Line Tools**: `xcode-select --install`
- **Homebrew** (권장)

## 🚀 빠른 시작

### 1단계: 저장소 클론
```bash
git clone <repository-url>
cd genbax
```

### 2단계: 환경 설정
```bash
# Python 3 사용 (Windows에서는 python, Mac에서는 python3)
python scripts/setup_environment.py
```

### 3단계: 서비스 시작
```bash
python scripts/start_services.py all
```

## 📝 상세 설정 가이드

### 환경 변수 설정

프로젝트는 `.env` 파일을 통해 환경 변수를 관리합니다.

1. **자동 설정** (권장):
   ```bash
   python scripts/setup_environment.py
   ```

2. **수동 설정**:
   ```bash
   cp .env.template .env
   # .env 파일을 편집하여 실제 값으로 변경
   ```

### 데이터베이스 설정

#### PostgreSQL (권장)

**Windows:**
```bash
# PostgreSQL 설치 (Chocolatey 사용)
choco install postgresql

# 또는 공식 인스톨러 다운로드
# https://www.postgresql.org/download/windows/
```

**Mac OS:**
```bash
# Homebrew 사용
brew install postgresql
brew services start postgresql

# 또는 Postgres.app 사용
# https://postgresapp.com/
```

#### MySQL

**Windows:**
```bash
# MySQL 설치
choco install mysql
```

**Mac OS:**
```bash
# Homebrew 사용
brew install mysql
brew services start mysql
```

### Python 의존성 설치

크로스 플랫폼 호환성을 위해 다음과 같이 설치하세요:

**Windows:**
```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Mac OS/Linux:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Node.js 의존성 설치

**모든 플랫폼:**
```bash
cd frontend
npm install
```

## 🔧 개발 도구

### 서비스 관리

기존의 `.bat` 파일 대신 크로스 플랫폼 Python 스크립트를 사용합니다:

```bash
# 모든 서비스 시작
python scripts/start_services.py all

# 백엔드만 시작
python scripts/start_services.py backend

# 프론트엔드만 시작
python scripts/start_services.py frontend
```

### 환경 설정 도구

```bash
# 초기 환경 설정
python scripts/setup_environment.py

# 강제 재설정
python scripts/setup_environment.py --force
```

## 🐛 문제 해결

### Windows 관련 문제

**1. Python 패키지 컴파일 오류**
```bash
# Visual Studio Build Tools 설치
# https://visualstudio.microsoft.com/visual-cpp-build-tools/

# 또는 미리 컴파일된 wheel 사용
pip install --only-binary=all -r requirements.txt
```

**2. 긴 경로 문제**
```bash
# Windows 설정에서 긴 경로 지원 활성화
# 또는 프로젝트를 C:\dev\ 같은 짧은 경로에 배치
```

### Mac OS 관련 문제

**1. Xcode Command Line Tools 없음**
```bash
xcode-select --install
```

**2. homebrew 권한 문제**
```bash
sudo chown -R $(whoami) /usr/local/share/zsh /usr/local/share/zsh/site-functions
```

**3. Python 버전 문제**
```bash
# pyenv를 사용하여 Python 버전 관리
brew install pyenv
pyenv install 3.9.0
pyenv global 3.9.0
```

### 공통 문제

**1. 포트 충돌**
`.env` 파일에서 포트 번호를 변경하세요:
```
PORT=8001  # 8000 대신
```

**2. 데이터베이스 연결 실패**
- 데이터베이스 서비스가 실행 중인지 확인
- `.env` 파일의 데이터베이스 URL 확인
- 방화벽 설정 확인

**3. 권한 문제**
```bash
# Mac/Linux
chmod +x scripts/*.py

# Windows (관리자 권한으로 실행)
```

## 📁 디렉토리 구조

```
genbax/
├── backend/                 # Python FastAPI 백엔드
│   ├── app/
│   ├── venv/               # 가상환경 (자동 생성)
│   └── requirements.txt
├── frontend/               # React 프론트엔드
│   ├── src/
│   ├── node_modules/       # 의존성 (자동 생성)
│   └── package.json
├── scripts/                # 크로스 플랫폼 스크립트
│   ├── setup_environment.py
│   └── start_services.py
├── data/                   # 사용자 데이터 (자동 생성)
├── chroma_data/           # 벡터 데이터베이스 (자동 생성)
├── file_storage/          # 파일 저장소 (자동 생성)
├── logs/                  # 로그 파일 (자동 생성)
├── .env.template          # 환경 변수 템플릿
├── .env                   # 실제 환경 변수 (자동 생성)
└── CROSS_PLATFORM_SETUP.md
```

## 🌟 주요 변경사항

### Windows 전용 .bat 파일 대체

기존 `.bat` 파일들이 크로스 플랫폼 Python 스크립트로 대체되었습니다:

| 기존 파일 | 새 스크립트 |
|-----------|-------------|
| `start_all_services.bat` | `python scripts/start_services.py all` |
| `start_backend.bat` | `python scripts/start_services.py backend` |
| `start_frontend.bat` | `python scripts/start_services.py frontend` |

### 환경 변수 관리 개선

- `.env.template` 파일로 표준화된 환경 변수 관리
- 운영체제별 기본값 자동 설정
- 보안 키 자동 생성

### 크로스 플랫폼 경로 처리

- `pathlib.Path` 사용으로 경로 호환성 확보
- 상대 경로 우선 사용
- 운영체제별 파일 시스템 차이 자동 처리

## 📚 추가 정보

- [개발 가이드](README.md)
- [배포 가이드](INSTALL.md)
- [문제 해결](TROUBLESHOOTING.md)

## 💡 팁

1. **개발 환경과 프로덕션 환경 분리**: 서로 다른 `.env` 파일 사용
2. **정기적인 의존성 업데이트**: `pip list --outdated` 및 `npm outdated` 확인
3. **교차 플랫폼 테스트**: 가능하면 두 플랫폼에서 모두 테스트
4. **백업**: 중요한 설정 파일은 버전 관리에 포함하되 민감한 정보는 제외

## 🤝 기여하기

크로스 플랫폼 호환성 개선에 기여하고 싶으시다면:

1. 이슈 리포트: 특정 플랫폼에서의 문제점 보고
2. 풀 리퀘스트: 호환성 개선 코드 제출
3. 문서 개선: 설정 가이드 보완

---

문제가 있거나 질문이 있으시면 이슈를 생성해 주세요! 