# MAX Lab OAuth 표준 준수 마이그레이션 가이드

## 개요

기존 MAX Lab의 OAuth 구현에서 OAuth 표준을 준수하는 구현으로 마이그레이션하는 가이드입니다.

### 현재 문제점
```
User → [OAuth Token] → MAX Lab Backend → [SERVICE_TOKEN] → Auth Server
```
- 사용자 토큰을 SERVICE_TOKEN으로 대체하여 OAuth 표준 위반
- 감사(audit) 추적 불가능
- 토큰 대체 공격(Token Substitution Attack) 가능성

### 개선된 OAuth 표준 방식
```
User → [OAuth Token] → MAX Lab Backend → [Same OAuth Token] → Auth Server
```
- 사용자 토큰을 그대로 전달하여 OAuth 표준 준수
- 완전한 감사 추적 가능
- 보안성 향상

## 새로운 API 엔드포인트

### 1. 사용자 관련 API (/api/users/*)

#### 사용자 검색
```http
GET /api/users/search?email={email}&limit=10
Authorization: Bearer {USER_TOKEN}
```

#### 이메일로 사용자 조회 (UUID 매핑용)
```http
GET /api/users/email/{email}
Authorization: Bearer {USER_TOKEN}
```

#### 내 프로필 조회
```http
GET /api/users/me
Authorization: Bearer {USER_TOKEN}
```

#### 특정 사용자 프로필 조회
```http
GET /api/users/{user_id}
Authorization: Bearer {USER_TOKEN}
```

### 2. 그룹 관련 API (/api/groups/*)

#### 그룹 검색
```http
GET /api/groups/search?name={name}&limit=10
Authorization: Bearer {USER_TOKEN}
```

#### 그룹명으로 그룹 조회
```http
GET /api/groups/name/{group_name}
Authorization: Bearer {USER_TOKEN}
```

#### 내 그룹 정보 조회
```http
GET /api/groups/my
Authorization: Bearer {USER_TOKEN}
```

#### 특정 그룹 상세 정보 조회
```http
GET /api/groups/{group_id}?include_members=true
Authorization: Bearer {USER_TOKEN}
```

## 코드 마이그레이션 예시

### Before (잘못된 방식)

```python
class AuthServerClient:
    async def get_user_uuid_by_email(self, email: str):
        """SERVICE_TOKEN을 사용한 잘못된 방식"""
        service_token = await self._get_service_token()
        headers = {"Authorization": f"Bearer {service_token}"}
        
        # 내부 서비스 API 호출
        url = f"{self.auth_server_url}/internal/users/by-email/{email}"
        response = await self.http_client.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()["user_id"]
        return None
    
    async def get_group_uuid_by_name(self, group_name: str):
        """SERVICE_TOKEN을 사용한 잘못된 방식"""
        service_token = await self._get_service_token()
        headers = {"Authorization": f"Bearer {service_token}"}
        
        url = f"{self.auth_server_url}/internal/groups/by-name/{group_name}"
        response = await self.http_client.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()["group_id"]
        return None
```

### After (올바른 OAuth 표준 방식)

```python
class AuthServerClient:
    async def get_user_uuid_by_email(self, email: str, user_token: str):
        """사용자 토큰을 사용한 OAuth 표준 방식"""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # 사용자 토큰으로 접근 가능한 공개 API 사용
        url = f"{self.auth_server_url}/api/users/email/{email}"
        response = await self.http_client.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()["id"]
        elif response.status_code == 403:
            raise PermissionError("사용자가 해당 정보에 접근할 권한이 없습니다")
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()
    
    async def get_group_uuid_by_name(self, group_name: str, user_token: str):
        """사용자 토큰을 사용한 OAuth 표준 방식"""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        url = f"{self.auth_server_url}/api/groups/name/{group_name}"
        response = await self.http_client.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()["id"]
        elif response.status_code == 403:
            raise PermissionError("사용자가 해당 그룹에 접근할 권한이 없습니다")
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()
    
    async def search_users_by_email(self, email_pattern: str, user_token: str, limit: int = 10):
        """사용자 검색 (새로운 기능)"""
        headers = {"Authorization": f"Bearer {user_token}"}
        params = {"email": email_pattern, "limit": limit}
        
        url = f"{self.auth_server_url}/api/users/search"
        response = await self.http_client.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    async def get_my_group_info(self, user_token: str):
        """내 그룹 정보 조회 (새로운 기능)"""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        url = f"{self.auth_server_url}/api/groups/my"
        response = await self.http_client.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return None
```

## FastAPI 엔드포인트 마이그레이션

### Before (내부 서비스 토큰 방식)

```python
from fastapi import APIRouter, Depends, HTTPException
from .auth import get_current_user, get_service_token

@router.post("/experiments")
async def create_experiment(
    experiment_data: ExperimentCreate,
    current_user: User = Depends(get_current_user)
):
    # 잘못된 방식: SERVICE_TOKEN 사용
    service_token = await get_service_token()
    
    # 사용자 정보 조회
    user_uuid = await auth_client.get_user_uuid_by_email(current_user.email)
    
    # 실험 생성
    experiment = await create_experiment_logic(user_uuid, experiment_data)
    return experiment
```

### After (사용자 토큰 전달 방식)

```python
from fastapi import APIRouter, Depends, HTTPException, Request

@router.post("/experiments")
async def create_experiment(
    experiment_data: ExperimentCreate,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # 올바른 방식: 사용자 토큰 전달
    user_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    try:
        # 사용자 정보 조회
        user_uuid = await auth_client.get_user_uuid_by_email(
            current_user.email, 
            user_token
        )
        
        # 실험 생성
        experiment = await create_experiment_logic(user_uuid, experiment_data)
        return experiment
        
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="실험 생성 중 오류가 발생했습니다")
```

## 권한 체계

### 사용자 정보 접근
- **본인 정보**: 항상 접근 가능
- **관리자**: 모든 사용자 정보 접근 가능  
- **같은 그룹 멤버**: 제한된 정보만 접근 가능
- **타인**: 공개된 기본 정보만 접근 가능

### 그룹 정보 접근
- **그룹 멤버**: 자신이 속한 그룹의 상세 정보 접근 가능
- **관리자**: 모든 그룹 정보 접근 가능
- **일반 사용자**: 활성화된 그룹의 기본 정보만 접근 가능

## 에러 처리

```python
# 표준 HTTP 상태 코드 사용
# 200: 성공
# 400: 잘못된 요청 (필수 파라미터 누락)
# 403: 권한 없음 (접근 권한 부족)
# 404: 리소스 없음 (사용자/그룹을 찾을 수 없음)
# 500: 서버 오류

try:
    result = await auth_client.get_user_uuid_by_email(email, user_token)
except PermissionError:
    # 403 에러 - 권한 부족
    raise HTTPException(status_code=403, detail="접근 권한이 없습니다")
except requests.HTTPError as e:
    if e.response.status_code == 404:
        # 404 에러 - 사용자 없음
        return None
    else:
        # 기타 에러
        raise HTTPException(status_code=500, detail="사용자 조회 실패")
```

## 마이그레이션 체크리스트

### 1. 코드 변경
- [ ] `get_service_token()` 호출을 `user_token` 전달로 변경
- [ ] 내부 API URL을 공개 API URL로 변경
- [ ] 에러 처리 로직 추가 (403, 404 처리)
- [ ] 함수 시그니처에 `user_token` 파라미터 추가

### 2. 테스트
- [ ] 사용자 토큰으로 API 호출 테스트
- [ ] 권한 부족 시나리오 테스트 (403 에러)
- [ ] 존재하지 않는 리소스 테스트 (404 에러)
- [ ] 다양한 사용자 권한 레벨 테스트

### 3. 보안 검증
- [ ] SERVICE_TOKEN 사용 완전 제거 확인
- [ ] 사용자 토큰 검증 로직 확인
- [ ] 권한 체계 적절성 검증
- [ ] 감사 로그 기록 확인

### 4. 성능 고려사항
- [ ] API 호출 횟수 최적화
- [ ] 캐싱 전략 수립 (필요시)
- [ ] 타임아웃 설정
- [ ] 재시도 로직 구현

## 테스트 실행

구현된 API들을 테스트하려면:

```bash
# 테스트 스크립트 실행
python test_oauth_standard_apis.py http://localhost:8000

# 또는 기본 URL로 실행
python test_oauth_standard_apis.py
```

## 참고사항

1. **하위 호환성**: 기존 내부 API는 당분간 유지되므로 점진적 마이그레이션 가능
2. **OAuth 표준 준수**: RFC 6750 Bearer Token 사용법 준수
3. **감사 로그**: 모든 API 호출이 사용자별로 로깅됨
4. **확장성**: 향후 새로운 OAuth 스코프 추가 시 기존 코드 영향 최소화

## 추가 지원

마이그레이션 과정에서 문제가 발생하면:
1. 테스트 스크립트로 API 동작 확인
2. 로그 파일에서 에러 원인 분석
3. 권한 설정 재확인
4. 개발팀 문의