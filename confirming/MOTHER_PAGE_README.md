# Mother Page - 서비스 허브 시스템

## 개요

Mother 페이지는 기존의 로그인 → 쥬피터 워크스페이스 구조를 **로그인 → Mother 페이지 → 서비스 페이지** 구조로 변경한 통합 서비스 허브입니다. 사용자의 권한에 따라 접근 가능한 서비스 목록을 5×N 그리드 레이아웃으로 표시하며, 향후 추가될 모든 서비스의 중앙 허브 역할을 수행합니다.

## 주요 기능

### 1. 권한 기반 서비스 표시
- 로그인한 사용자의 **역할(Role)**과 **개별 권한**에 따라 접근 가능한 서비스만 표시
- 일반 사용자: 쥬피터 워크스페이스 등 기본 서비스
- 관리자: 모든 서비스 + 관리자 도구

### 2. 5×N 그리드 레이아웃
- **데스크톱**: 5열 그리드
- **태블릿**: 3-4열 그리드  
- **모바일**: 1-2열 그리드
- 반응형 디자인으로 모든 기기에서 최적화된 경험 제공

### 3. 서비스 카드 디자인
- **아이콘/썸네일**: 서비스별 시각적 식별
- **서비스명**: 명확한 서비스 이름
- **설명**: 간단한 서비스 설명
- **호버 효과**: 인터랙티브한 사용자 경험
- **외부 링크 표시**: 외부 서비스 구분

### 4. 카테고리 필터링
- **데이터 분석**: 쥬피터, 데이터 시각화 도구
- **개발 도구**: 파일 관리자, IDE, 버전 관리
- **관리 도구**: 시스템 관리, 사용자 관리
- **협업 도구**: 팀 커뮤니케이션, 문서 관리

## 데이터베이스 스키마

### 새로 추가된 테이블

#### 1. `services` - 서비스 정보
```sql
- id: 서비스 고유 ID
- name: 서비스 고유명 (시스템용)
- display_name: 화면 표시명
- description: 서비스 설명
- url: 서비스 URL/라우트
- icon_url: 아이콘 이미지 URL
- thumbnail_url: 썸네일 이미지 URL
- is_active: 활성화 여부
- is_external: 외부 서비스 여부
- requires_auth: 인증 필요 여부
- open_in_new_tab: 새 탭 열기 여부
- sort_order: 정렬 순서
- category: 서비스 카테고리
- created_by: 생성자 UUID
```

#### 2. `service_categories` - 서비스 카테고리
```sql
- id: 카테고리 ID
- name: 카테고리 고유명
- display_name: 화면 표시명
- description: 카테고리 설명
- sort_order: 정렬 순서
```

#### 3. `user_services` - 사용자별 서비스 권한
```sql
- user_id: 사용자 UUID
- service_id: 서비스 ID
- granted_at: 권한 부여 시간
- granted_by: 권한 부여자
```

#### 4. `role_services` - 역할별 서비스 권한
```sql
- role_id: 역할 ID
- service_id: 서비스 ID
- granted_at: 권한 부여 시간
- granted_by: 권한 부여자
```

#### 5. `user_service_permissions` - 상세 권한 관리
```sql
- user_id: 사용자 UUID
- service_id: 서비스 ID
- permission_level: 권한 레벨 (read/write/admin)
- custom_permissions: JSON 형태 커스텀 권한
- expires_at: 권한 만료일
```

## API 엔드포인트

### Mother 페이지 API
```
GET /api/services/mother-page
- 사용자 정보 + 접근 가능한 서비스 목록 + 카테고리 목록 반환
```

### 서비스 관리 API (관리자 전용)
```
GET    /api/services/              # 모든 서비스 목록
POST   /api/services/              # 새 서비스 생성
PUT    /api/services/{id}          # 서비스 정보 수정
DELETE /api/services/{id}          # 서비스 삭제

POST   /api/services/permissions/grant   # 권한 부여
DELETE /api/services/permissions/revoke  # 권한 회수
```

### 사용자 API
```
GET /api/services/accessible       # 접근 가능한 서비스 목록
GET /api/services/categories        # 서비스 카테고리 목록
GET /api/services/check-access/{service_name}  # 특정 서비스 접근 권한 확인
```

## 설치 및 설정

### 1. 데이터베이스 마이그레이션

#### MySQL
```bash
mysql -u username -p database_name < backend/migrations/mysql_migration_001_add_service_system.sql
```

#### MSSQL
```bash
sqlcmd -S server -d database -i backend/migrations/mssql_migration_001_add_service_system.sql
```

### 2. 서비스 시스템 초기화
```bash
# 자동 설정 스크립트 실행
setup_mother_page.bat

# 또는 수동 실행
cd backend
python init_service_system.py
```

### 3. 서버 시작
```bash
# 백엔드 서버
start_backend.bat

# 프론트엔드 서버  
start_frontend.bat
```

### 4. 접속 확인
- URL: `http://localhost:3000`
- 로그인 후 자동으로 Mother 페이지로 이동

## 사용 방법

### 일반 사용자
1. 로그인 후 Mother 페이지 자동 이동
2. 권한이 있는 서비스 카드들이 표시됨
3. 카테고리 필터로 서비스 분류별 조회
4. 서비스 카드 클릭으로 해당 서비스 접속

### 관리자
1. 모든 서비스에 접근 가능
2. API를 통해 새로운 서비스 등록
3. 사용자별/역할별 서비스 권한 관리
4. 서비스 카테고리 관리

## 새로운 서비스 추가 방법

### 1. API를 통한 서비스 등록
```javascript
// 새 서비스 등록 예시
const newService = {
  name: "data_visualization",
  display_name: "데이터 시각화 도구",
  description: "대화형 차트 및 대시보드 생성 도구",
  url: "https://viz.example.com",
  category: "analytics",
  is_external: true,
  open_in_new_tab: true,
  sort_order: 5
};

fetch('/api/services/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(newService)
});
```

### 2. 권한 부여
```javascript
// 특정 사용자에게 서비스 권한 부여
fetch('/api/services/permissions/grant', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: "user-uuid",
    service_id: 1,
    permission_level: "read"
  })
});
```

## 확장성 고려사항

### 1. 새로운 서비스 타입
- **내부 서비스**: React 라우터를 통한 SPA 내 이동
- **외부 서비스**: 새 탭 또는 현재 탭에서 외부 URL 접속
- **임베디드 서비스**: iframe을 통한 서비스 임베딩

### 2. 권한 시스템 확장
- **역할 기반 권한**: 역할에 따른 기본 권한
- **개별 사용자 권한**: 특정 사용자에게 추가 권한 부여
- **시간 제한 권한**: 만료일이 있는 임시 권한
- **기능별 세분화 권한**: 읽기/쓰기/관리자 권한 구분

### 3. UI/UX 개선
- **드래그 앤 드롭**: 사용자별 서비스 순서 커스터마이징
- **즐겨찾기**: 자주 사용하는 서비스 상단 고정
- **검색 기능**: 서비스명/설명 기반 검색
- **최근 사용**: 최근 접속한 서비스 우선 표시

## 문제 해결

### 1. 서비스가 표시되지 않는 경우
```bash
# 서비스 시스템 상태 확인
cd backend
python init_service_system.py check

# 사용자 권한 확인
GET /api/services/accessible
```

### 2. 권한 문제
- 관리자 계정으로 로그인하여 권한 확인
- 역할별 권한 설정 확인
- 개별 사용자 권한 설정 확인

### 3. 데이터베이스 문제
- 마이그레이션 파일 정상 실행 확인
- 테이블 생성 상태 확인
- 외래키 제약조건 확인

## 향후 개발 계획

### Phase 1 (현재)
- ✅ 기본 Mother 페이지 구현
- ✅ 권한 기반 서비스 표시
- ✅ 5×N 그리드 레이아웃
- ✅ 카테고리 필터링

### Phase 2 (예정)
- 🔄 관리자 웹 인터페이스
- 🔄 서비스 사용 통계
- 🔄 사용자별 대시보드 커스터마이징
- 🔄 서비스 상태 모니터링

### Phase 3 (계획)
- 📋 SSO(Single Sign-On) 통합
- 📋 서비스 간 데이터 연동
- 📋 워크플로우 자동화
- 📋 모바일 앱 지원

## 기술 스택

### 백엔드
- **FastAPI**: REST API 서버
- **SQLAlchemy**: ORM 및 데이터베이스 관리
- **Pydantic**: 데이터 검증 및 직렬화
- **JWT**: 인증 토큰 관리

### 프론트엔드
- **React**: 사용자 인터페이스
- **TypeScript**: 타입 안전성
- **Tailwind CSS**: 스타일링 및 반응형 디자인
- **React Router**: 클라이언트 사이드 라우팅

### 데이터베이스
- **MySQL/MSSQL**: 관계형 데이터베이스
- **마이그레이션**: 스키마 버전 관리

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 