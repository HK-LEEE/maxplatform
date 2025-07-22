# SQL Server 설치 및 설정 가이드

## 1. SQL Server 설치 옵션

### 옵션 1: SQL Server Express (무료, 권장)

```bash
# Windows에서 SQL Server Express 다운로드
# https://www.microsoft.com/en-us/sql-server/sql-server-downloads
# "Express" 버전 선택하여 설치
```

### 옵션 2: Docker로 SQL Server 설치 (권장)

```bash
# SQL Server 2019 Linux 컨테이너 실행
docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=YourPassword123" \
   -p 1433:1433 --name sql_server_jupyter \
   -d mcr.microsoft.com/mssql/server:2019-latest

# 또는 SQL Server 2022
docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=YourPassword123" \
   -p 1433:1433 --name sql_server_jupyter \
   -d mcr.microsoft.com/mssql/server:2022-latest
```

### 옵션 3: Azure SQL Database (클라우드)

```bash
# Azure 포털에서 SQL Database 생성
# 연결 문자열 예제:
# mssql+pyodbc://username:password@server.database.windows.net:1433/database?driver=ODBC+Driver+17+for+SQL+Server
```

## 2. ODBC Driver 설치

### Windows
```bash
# ODBC Driver 17 for SQL Server 다운로드 및 설치
# https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

# 또는 Microsoft Command Line Utilities 15 for SQL Server
# https://docs.microsoft.com/en-us/sql/tools/sqlcmd-utility
```

### macOS
```bash
# Homebrew 사용
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
brew install mssql-tools18
```

### Ubuntu/Debian
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list | sudo tee /etc/apt/sources.list.d/msprod.list
sudo apt-get update 
sudo apt-get install mssql-tools18 unixodbc-dev
```

## 3. 데이터베이스 생성

### SQL Server Management Studio (SSMS) 사용
```sql
-- 1. SSMS 연결 후 새 쿼리 창에서 실행
CREATE DATABASE jupyter_platform;
GO

-- 2. 데이터베이스 선택 확인
USE jupyter_platform;
GO
```

### sqlcmd 명령줄 도구 사용
```bash
# SQL Server 연결
sqlcmd -S localhost -U sa -P YourPassword123

# 데이터베이스 생성
CREATE DATABASE jupyter_platform;
GO

# 종료
EXIT
```

### Docker 컨테이너에서 직접 실행
```bash
# Docker 컨테이너에 접속
docker exec -it sql_server_jupyter /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourPassword123

# 데이터베이스 생성
CREATE DATABASE jupyter_platform;
GO
EXIT
```

## 4. 환경 설정

### .env 파일 설정
```bash
# .env 파일에 다음 내용 추가
DATABASE_TYPE=mssql
MSSQL_DATABASE_URL=mssql+pyodbc://sa:YourPassword123@localhost:1433/jupyter_platform?driver=ODBC+Driver+17+for+SQL+Server

# 다른 설정들도 필요에 따라 수정
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 연결 문자열 형식
```
mssql+pyodbc://사용자명:비밀번호@서버:포트/데이터베이스?driver=드라이버명
```

**예제들:**
- 로컬 기본 인스턴스: `mssql+pyodbc://sa:password@localhost:1433/jupyter_platform?driver=ODBC+Driver+17+for+SQL+Server`
- 명명된 인스턴스: `mssql+pyodbc://sa:password@localhost\\SQLEXPRESS:1433/jupyter_platform?driver=ODBC+Driver+17+for+SQL+Server`
- 원격 서버: `mssql+pyodbc://user:password@192.168.1.100:1433/jupyter_platform?driver=ODBC+Driver+17+for+SQL+Server`
- Azure SQL: `mssql+pyodbc://user:password@server.database.windows.net:1433/jupyter_platform?driver=ODBC+Driver+17+for+SQL+Server`

## 5. 초기화 및 테스트

### 1단계: 연결 테스트
```bash
cd backend
python -c "from app.database import test_connection; print('연결 성공!' if test_connection() else '연결 실패!')"
```

### 2단계: 테이블 생성 및 데이터 삽입
```bash
cd backend
python mssql_init.py
```

### 3단계: 서버 실행 및 테스트
```bash
cd backend
python main.py
```

### 4단계: 로그인 테스트
```bash
# 브라우저에서 http://localhost:8000 접속
# 다음 계정으로 로그인 테스트:
# - admin@jupyter-platform.com / admin123!
# - test@example.com / test123!
```

## 6. 문제 해결

### 연결 오류 시 체크리스트

1. **SQL Server 서비스 실행 확인**
   ```bash
   # Windows 서비스에서 SQL Server 확인
   # 또는 Docker 컨테이너 상태 확인
   docker ps | grep sql_server_jupyter
   ```

2. **방화벽 설정**
   ```bash
   # Windows 방화벽에서 1433 포트 허용
   # 또는 Docker의 경우 포트 매핑 확인
   ```

3. **인증 모드 확인**
   ```sql
   -- SQL Server 인증 모드 확인 (혼합 모드여야 함)
   SELECT SERVERPROPERTY('IsIntegratedSecurityOnly');
   -- 0이어야 함 (혼합 모드)
   ```

4. **sa 계정 활성화**
   ```sql
   -- sa 계정 활성화
   ALTER LOGIN sa ENABLE;
   ALTER LOGIN sa WITH PASSWORD = 'YourPassword123';
   ```

5. **TCP/IP 프로토콜 활성화**
   - SQL Server Configuration Manager에서 TCP/IP 프로토콜 활성화
   - 포트 1433 설정 확인

### 일반적인 오류 해결

**오류**: `ODBC Driver 17 for SQL Server not found`
```bash
# 해결: ODBC 드라이버 재설치
# Windows: https://go.microsoft.com/fwlink/?linkid=2168524
# macOS: brew install mssql-tools18
# Linux: apt-get install mssql-tools18
```

**오류**: `Login failed for user 'sa'`
```bash
# 해결: 비밀번호 확인 및 계정 활성화
sqlcmd -S localhost -U sa -P YourPassword123
```

**오류**: `Could not connect to server`
```bash
# 해결: 서버 실행 상태 및 포트 확인
telnet localhost 1433
```

## 7. 성능 최적화

### 연결 풀 설정
```python
# database.py에서 연결 풀 설정
engine = create_engine(
    mssql_url,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True
)
```

### 인덱스 추가 (선택사항)
```sql
-- 자주 조회되는 컬럼에 인덱스 추가
CREATE INDEX IX_users_email ON users(email);
CREATE INDEX IX_workspaces_owner_id ON workspaces(owner_id);
```

이제 MSSQL 환경에서 Jupyter Platform을 완전히 사용할 수 있습니다! 