# macOS 개발 환경 설정 가이드

MAX (Manufacturing AI & DX) Platform을 macOS 환경에서 실행하기 위한 설정 가이드입니다.

## 📋 시스템 요구사항

- **macOS**: 10.15 (Catalina) 이상
- **Python**: 3.8 이상
- **Node.js**: 18 이상
- **RAM**: 8GB 이상 권장
- **디스크 공간**: 5GB 이상

## 🛠️ 필수 도구 설치

### 1. Homebrew 설치
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Python 3 설치
```bash
brew install python3
python3 --version  # 버전 확인
```

### 3. Node.js 설치
```bash
brew install node
node --version  # 버전 확인
npm --version   # npm 버전 확인
```

### 4. Git 설치 (미설치 시)
```bash
brew install git
```

## 🗄️ 데이터베이스 설치

### PostgreSQL 설치 (권장)
```bash
# PostgreSQL 설치
brew install postgresql

# 서비스 시작
brew services start postgresql

# 데이터베이스 생성
createdb platform_integration
```

### MySQL 설치 (선택사항)
```bash
# MySQL 설치
brew install mysql

# 서비스 시작
brew services start mysql

# 보안 설정
mysql_secure_installation

# 데이터베이스 생성
mysql -u root -p
CREATE DATABASE jupyter_platform;
```

### Microsoft SQL Server 설정 (선택사항)
```bash
# ODBC Driver 18 설치
brew install microsoft/mssql-release/msodbcsql18

# ODBC 설정 확인
odbcinst -q -d
```

## 🚀 프로젝트 실행

### 빠른 실행 (추천)
```bash
cd ipnyb_workspace
./start_all_services_macos.sh
```

### 수동 실행

#### 1. 백엔드 서버 실행
```bash
cd ipnyb_workspace
./start_backend_macos.sh
```

#### 2. 프론트엔드 서버 실행 (새 터미널)
```bash
cd ipnyb_workspace
./start_frontend_macos.sh
```

## ⚙️ 환경 설정

### 환경 변수 파일 설정
기본적으로 `.env.macos` 설정이 활성화됩니다. 필요에 따라 `.env` 파일을 수정하세요.

```bash
cd ipnyb_workspace/backend
vi .env  # 또는 nano .env
```

### 주요 설정 항목
```env
# 데이터베이스 설정
DATABASE_URL=postgresql://postgres:password@localhost:5432/platform_integration

# AI API 키 (선택사항)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_API_KEY=your-google-api-key
```

## 🔧 OCR 기능 설정 (선택사항)

PDF 및 이미지 텍스트 추출 기능을 사용하려면:

```bash
# OCR 도구 설치
brew install tesseract tesseract-lang poppler

# 설치 확인
tesseract --version
pdfinfo -v
```

## 📱 서비스 접속

서비스가 정상적으로 시작되면:
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 🐛 문제 해결

### 포트 충돌 문제
```bash
# 포트 사용 중인 프로세스 확인
lsof -ti:3000  # 프론트엔드 포트
lsof -ti:8000  # 백엔드 포트

# 프로세스 종료
kill -9 $(lsof -ti:3000)
kill -9 $(lsof -ti:8000)
```

### Python 패키지 설치 오류
```bash
# pip 업그레이드
pip install --upgrade pip

# Xcode 명령줄 도구 설치
xcode-select --install

# 개별 패키지 설치 시도
pip install --no-cache-dir package_name
```

### 데이터베이스 연결 오류
```bash
# PostgreSQL 서비스 상태 확인
brew services list | grep postgresql

# 서비스 재시작
brew services restart postgresql

# 연결 테스트
psql -U postgres -d platform_integration
```

### 권한 오류
```bash
# 스크립트 실행 권한 부여
chmod +x start_*_macos.sh

# 디렉토리 권한 확인
ls -la
```

## 🔄 서비스 중지

각 터미널에서 `Ctrl + C`를 눌러 서비스를 중지하거나:

```bash
# 백그라운드 프로세스 종료
pkill -f "uvicorn app.main:app"
pkill -f "npm start"
```

## 📚 추가 리소스

- [Python 가상환경 가이드](https://docs.python.org/3/tutorial/venv.html)
- [Node.js 공식 문서](https://nodejs.org/en/docs/)
- [PostgreSQL macOS 설치 가이드](https://www.postgresql.org/download/macosx/)
- [Homebrew 공식 사이트](https://brew.sh/)

## 💡 개발 팁

### VS Code 설정
```bash
# VS Code 설치
brew install --cask visual-studio-code

# 유용한 확장 프로그램
# - Python
# - React
# - TypeScript
# - REST Client
```

### 터미널 개선
```bash
# Oh My Zsh 설치 (선택사항)
sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

문제가 지속되면 GitHub Issues에 제보해주세요.