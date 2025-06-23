# MySQL to MSSQL Migration Guide
## GenbaX Platform Database Migration

### 📋 개요
이 가이드는 GenbaX 플랫폼의 MySQL 데이터베이스를 MSSQL로 완전히 이관하는 과정을 설명합니다.

### 🎯 마이그레이션 목표
- 모든 테이블 스키마 및 데이터 이관
- 외래키 관계 및 제약조건 보존
- 인덱스 및 트리거 재생성
- 데이터 무결성 보장

### 📊 이관 대상 테이블

#### 1. 기본 테이블
- `users` - 사용자 정보
- `roles` - 역할 정보
- `groups` - 그룹 정보
- `workspaces` - 워크스페이스
- `services` - 서비스 목록
- `service_categories` - 서비스 카테고리
- `permissions` - 권한 목록
- `features` - 기능 목록
- `user_service_permissions` - 사용자별 서비스 권한

#### 2. 다대다 관계 테이블
- `user_permissions` - 사용자-권한 매핑
- `user_features` - 사용자-기능 매핑
- `role_permissions` - 역할-권한 매핑
- `role_features` - 역할-기능 매핑
- `group_permissions` - 그룹-권한 매핑
- `group_features` - 그룹-기능 매핑
- `user_services` - 사용자-서비스 매핑
- `role_services` - 역할-서비스 매핑

### 🛠️ 사전 요구사항

#### 1. 소프트웨어 설치
```bash
# Python 패키지
pip install pymysql pyodbc

# MSSQL ODBC Driver
# Windows: Download from Microsoft
# https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

#### 2. 데이터베이스 준비
- MySQL 서버 접근 권한
- MSSQL 서버 관리자 권한
- 네트워크 연결 확인

### 📋 마이그레이션 단계

#### Step 1: 백업 생성
```sql
-- MySQL 백업
mysqldump -u root -p jupyter_platform > mysql_backup_$(date +%Y%m%d).sql

-- MSSQL 백업 (기존 데이터가 있는 경우)
BACKUP DATABASE jupyter_platform_mssql 
TO DISK = 'C:\backup\jupyter_platform_mssql_backup.bak'
```

#### Step 2: MSSQL 스키마 생성
```bash
# SQL Server Management Studio에서 실행
mysql_to_mssql_migration.sql
```

#### Step 3: 데이터 마이그레이션 실행
```bash
# Windows
run_migration.bat

# 또는 직접 Python 실행
python mysql_to_mssql_migration.py
```

#### Step 4: 데이터 검증
```sql
-- 테이블별 행 수 비교
SELECT 'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'roles', COUNT(*) FROM roles
-- ... 다른 테이블들
```

### 🔧 설정 방법

#### 1. 데이터베이스 연결 설정
```python
# 환경 변수로 설정 (권장)
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=jupyter_platform

export MSSQL_SERVER=localhost
export MSSQL_DATABASE=jupyter_platform_mssql
export MSSQL_USERNAME=sa
export MSSQL_PASSWORD=your_password
```

#### 2. 애플리케이션 설정 업데이트
```python
# backend/.env 파일 수정
DATABASE_URL=mssql://sa:password@localhost/jupyter_platform_mssql
DB_TYPE=mssql
DB_HOST=localhost
DB_PORT=1433
DB_NAME=jupyter_platform_mssql
DB_USER=sa
DB_PASSWORD=your_password
```

### 📈 데이터 타입 매핑

| MySQL | MSSQL | 비고 |
|-------|-------|------|
| `CHAR(36)` | `CHAR(36)` | UUID |
| `VARCHAR(n)` | `NVARCHAR(n)` | 유니코드 지원 |
| `TEXT` | `NTEXT` | 긴 텍스트 |
| `TINYINT(1)` | `BIT` | Boolean |
| `INT AUTO_INCREMENT` | `INT IDENTITY(1,1)` | 자동 증가 |
| `DATETIME` | `DATETIME2` | 높은 정밀도 |
| `TIMESTAMP` | `DATETIME2` | 기본값 GETDATE() |

### 🚨 주의사항

#### 1. 외래키 제약조건
- 마이그레이션 중 임시로 비활성화
- 완료 후 다시 활성화
- 데이터 무결성 검증 필수

#### 2. 인덱스 재생성
- 기본키 인덱스 자동 생성
- 외래키 인덱스 수동 생성 필요
- 성능 최적화를 위한 추가 인덱스 고려

#### 3. 트리거 및 함수
- `updated_at` 컬럼을 위한 트리거 생성
- MySQL 함수의 MSSQL 함수로 변환

### 🔍 검증 체크리스트

#### 1. 데이터 무결성
- [ ] 모든 테이블 행 수 일치
- [ ] 외래키 참조 무결성 확인
- [ ] NULL 값 처리 검증
- [ ] 특수 문자 인코딩 확인

#### 2. 기능 검증
- [ ] 사용자 로그인 테스트
- [ ] 워크스페이스 생성/조회 테스트
- [ ] 권한 시스템 동작 확인
- [ ] 서비스 접근 권한 확인

#### 3. 성능 검증
- [ ] 쿼리 실행 시간 비교
- [ ] 인덱스 사용률 확인
- [ ] 메모리 사용량 모니터링

### 📝 트러블슈팅

#### 문제: 연결 오류
```bash
# MSSQL 서비스 상태 확인
net start mssqlserver

# 방화벽 포트 확인 (1433)
netsh advfirewall firewall add rule name="SQL Server" dir=in action=allow protocol=TCP localport=1433
```

#### 문제: 인코딩 오류
```sql
-- 데이터베이스 콜레이션 확인
SELECT DATABASEPROPERTYEX('jupyter_platform_mssql', 'Collation')

-- 필요시 콜레이션 변경
ALTER DATABASE jupyter_platform_mssql COLLATE SQL_Latin1_General_CP1_CI_AS
```

#### 문제: 권한 오류
```sql
-- MSSQL 사용자 권한 확인
SELECT 
    p.name as principal_name,
    p.type_desc as principal_type,
    dp.permission_name,
    dp.state_desc as permission_state
FROM sys.database_permissions dp
JOIN sys.database_principals p ON dp.grantee_principal_id = p.principal_id
WHERE p.name = 'sa'
```

### 📊 성능 최적화

#### 1. 인덱스 튜닝
```sql
-- 자주 사용되는 컬럼에 인덱스 추가
CREATE INDEX IX_users_email_active ON users(email, is_active);
CREATE INDEX IX_workspaces_owner_status ON workspaces(owner_id, is_active);
CREATE INDEX IX_services_category_active ON services(category, is_active);
```

#### 2. 통계 정보 업데이트
```sql
-- 통계 정보 업데이트
UPDATE STATISTICS users;
UPDATE STATISTICS workspaces;
UPDATE STATISTICS services;
```

#### 3. 쿼리 최적화
```sql
-- 실행 계획 분석
SET STATISTICS IO ON;
SET STATISTICS TIME ON;
-- 쿼리 실행
SET STATISTICS IO OFF;
SET STATISTICS TIME OFF;
```

### 🔄 롤백 계획

#### 1. 즉시 롤백
```sql
-- MSSQL 백업에서 복원
RESTORE DATABASE jupyter_platform_mssql 
FROM DISK = 'C:\backup\jupyter_platform_mssql_backup.bak'
WITH REPLACE;
```

#### 2. MySQL로 복귀
```bash
# 애플리케이션 설정 복원
cp backend/.env.mysql backend/.env

# 서비스 재시작
systemctl restart genbax-backend
```

### 📋 마이그레이션 체크리스트

#### 사전 준비
- [ ] MySQL 데이터 백업 완료
- [ ] MSSQL 서버 설치 및 설정
- [ ] 필요한 도구 및 라이브러리 설치
- [ ] 네트워크 연결 확인

#### 마이그레이션 실행
- [ ] MSSQL 스키마 생성
- [ ] 데이터 마이그레이션 실행
- [ ] 외래키 제약조건 적용
- [ ] 인덱스 생성
- [ ] 트리거 생성

#### 검증 및 테스트
- [ ] 데이터 무결성 검증
- [ ] 애플리케이션 기능 테스트
- [ ] 성능 테스트
- [ ] 사용자 수용 테스트

#### 배포 및 모니터링
- [ ] 애플리케이션 설정 업데이트
- [ ] 서비스 재시작
- [ ] 모니터링 설정
- [ ] 백업 스케줄 설정

### 📞 지원 및 문의
- 기술 지원: tech-support@genbax.com
- 문서 업데이트: docs@genbax.com
- 긴급 문의: emergency@genbax.com

---
**📅 최종 업데이트:** 2024-12-19  
**📝 문서 버전:** 1.0  
**👤 작성자:** GenbaX Development Team 