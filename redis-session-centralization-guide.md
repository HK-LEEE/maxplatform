# Redis Session Centralization Configuration Guide

## Overview

이 가이드는 OAuth SSO 무한루프 문제의 핵심 원인인 **워커 프로세스 간 세션 불일치**를 해결하기 위한 Redis 기반 세션 중앙화 설정을 제공합니다.

## 문제 분석

```
CURRENT ISSUE: 
Worker 393678 ←→ Worker 393662 session mismatch
│
├── Session stored in Worker A memory
├── Request routed to Worker B  
├── Worker B has no session context
└── Authentication fails → infinite loop
```

## 해결책: Redis Session Store

```
SOLUTION:
All Workers ←→ Shared Redis Session Store
│
├── Worker A stores session in Redis
├── Worker B retrieves same session from Redis
├── Consistent authentication state
└── No more session mismatches
```

---

## 1. Redis Installation (사용자가 수행)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server

# CentOS/RHEL
sudo yum install redis

# macOS
brew install redis

# Docker (개발환경)
docker run -d --name redis -p 6379:6379 redis:alpine
```

---

## 2. Redis Configuration

### A. Redis Server 설정 (`/etc/redis/redis.conf`)

```bash
# 메모리 설정 (프로덕션 권장: 2GB+)
maxmemory 2gb
maxmemory-policy allkeys-lru

# 네트워크 설정
bind 127.0.0.1
port 6379

# 보안 설정
requirepass your_redis_password_here

# 세션 데이터 영속성 (옵션)
save 900 1
save 300 10
save 60 10000

# 로그 설정
loglevel notice
logfile /var/log/redis/redis-server.log

# 백그라운드 실행
daemonize yes

# TCP 연결 설정
tcp-keepalive 300
timeout 300
```

### B. Redis 서비스 시작

```bash
# 시스템 서비스 시작
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 상태 확인
sudo systemctl status redis-server
redis-cli ping  # 응답: PONG
```

---

## 3. Python Backend 설정

### A. 필요한 패키지 설치

```bash
cd /home/lee/maxproject/maxplatform
pip install redis
pip install aioredis  # FastAPI 비동기 지원
```

### B. Redis Session Store 구현

**파일 생성: `/home/lee/maxproject/maxplatform/backend/app/core/redis_session.py`**

```python
"""
Redis Session Store for OAuth SSO
세션 중앙화로 워커 간 세션 공유 문제 해결
"""

import json
import redis.asyncio as redis
from typing import Optional, Dict, Any
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class RedisSessionStore:
    def __init__(self, redis_url: str = "redis://localhost:6379/0", password: Optional[str] = None):
        self.redis_url = redis_url
        self.password = password
        self._redis: Optional[redis.Redis] = None
        
    async def connect(self):
        """Redis 연결 초기화"""
        try:
            self._redis = redis.from_url(
                self.redis_url,
                password=self.password,
                decode_responses=True,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # 연결 테스트
            await self._redis.ping()
            logger.info("✅ Redis 세션 스토어 연결 성공")
            
        except Exception as e:
            logger.error(f"❌ Redis 세션 스토어 연결 실패: {e}")
            raise
    
    async def disconnect(self):
        """Redis 연결 해제"""
        if self._redis:
            await self._redis.close()
            logger.info("🔌 Redis 연결 해제 완료")
    
    def _get_session_key(self, session_id: str) -> str:
        """세션 키 생성"""
        return f"session:oauth:{session_id}"
    
    def _get_user_sessions_key(self, user_id: str) -> str:
        """사용자별 세션 목록 키"""
        return f"user_sessions:{user_id}"
    
    async def set_session(self, session_id: str, session_data: Dict[str, Any], ttl: int = 3600):
        """
        세션 데이터 저장
        Args:
            session_id: 고유 세션 ID
            session_data: 저장할 세션 데이터
            ttl: 만료 시간 (초, 기본 1시간)
        """
        if not self._redis:
            await self.connect()
        
        try:
            session_key = self._get_session_key(session_id)
            
            # 세션 데이터에 타임스탬프 추가
            session_data['created_at'] = session_data.get('created_at', int(time.time()))
            session_data['last_accessed'] = int(time.time())
            
            # JSON으로 직렬화하여 저장
            await self._redis.setex(
                session_key,
                ttl,
                json.dumps(session_data, default=str)
            )
            
            # 사용자별 세션 목록에 추가 (사용자 로그아웃 시 일괄 정리용)
            if 'user_id' in session_data:
                user_sessions_key = self._get_user_sessions_key(session_data['user_id'])
                await self._redis.sadd(user_sessions_key, session_id)
                await self._redis.expire(user_sessions_key, ttl)
            
            logger.debug(f"✅ 세션 저장 완료: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ 세션 저장 실패 {session_id}: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 데이터 조회
        Returns:
            세션 데이터 또는 None (만료/없음)
        """
        if not self._redis:
            await self.connect()
        
        try:
            session_key = self._get_session_key(session_id)
            session_json = await self._redis.get(session_key)
            
            if session_json:
                session_data = json.loads(session_json)
                
                # 마지막 접근 시간 업데이트
                session_data['last_accessed'] = int(time.time())
                await self._redis.setex(
                    session_key, 
                    await self._redis.ttl(session_key),
                    json.dumps(session_data, default=str)
                )
                
                logger.debug(f"✅ 세션 조회 성공: {session_id}")
                return session_data
            
            logger.debug(f"🔍 세션 없음: {session_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ 세션 조회 실패 {session_id}: {e}")
            return None
    
    async def delete_session(self, session_id: str):
        """특정 세션 삭제"""
        if not self._redis:
            await self.connect()
        
        try:
            session_key = self._get_session_key(session_id)
            
            # 세션 데이터에서 user_id 추출
            session_data = await self.get_session(session_id)
            if session_data and 'user_id' in session_data:
                user_sessions_key = self._get_user_sessions_key(session_data['user_id'])
                await self._redis.srem(user_sessions_key, session_id)
            
            # 세션 삭제
            deleted = await self._redis.delete(session_key)
            
            if deleted:
                logger.info(f"✅ 세션 삭제 완료: {session_id}")
            else:
                logger.debug(f"🔍 삭제할 세션 없음: {session_id}")
                
        except Exception as e:
            logger.error(f"❌ 세션 삭제 실패 {session_id}: {e}")
    
    async def delete_user_sessions(self, user_id: str):
        """사용자의 모든 세션 삭제 (로그아웃 시)"""
        if not self._redis:
            await self.connect()
        
        try:
            user_sessions_key = self._get_user_sessions_key(user_id)
            session_ids = await self._redis.smembers(user_sessions_key)
            
            deleted_count = 0
            for session_id in session_ids:
                session_key = self._get_session_key(session_id)
                if await self._redis.delete(session_key):
                    deleted_count += 1
            
            # 사용자 세션 목록 삭제
            await self._redis.delete(user_sessions_key)
            
            logger.info(f"✅ 사용자 {user_id}의 세션 {deleted_count}개 삭제 완료")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ 사용자 세션 삭제 실패 {user_id}: {e}")
            return 0
    
    async def extend_session(self, session_id: str, ttl: int = 3600):
        """세션 만료 시간 연장"""
        if not self._redis:
            await self.connect()
        
        try:
            session_key = self._get_session_key(session_id)
            await self._redis.expire(session_key, ttl)
            logger.debug(f"⏰ 세션 만료시간 연장: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ 세션 연장 실패 {session_id}: {e}")
    
    async def get_session_count(self) -> int:
        """현재 활성 세션 수 조회"""
        if not self._redis:
            await self.connect()
        
        try:
            pattern = self._get_session_key("*")
            keys = await self._redis.keys(pattern)
            return len(keys)
        except Exception as e:
            logger.error(f"❌ 세션 수 조회 실패: {e}")
            return 0

# 전역 세션 스토어 인스턴스
redis_session_store = RedisSessionStore()

async def get_redis_session_store() -> RedisSessionStore:
    """FastAPI 의존성 주입용"""
    if not redis_session_store._redis:
        await redis_session_store.connect()
    return redis_session_store
```

### C. OAuth 세션 통합

**파일 수정: `/home/lee/maxproject/maxplatform/backend/app/api/oauth_simple.py`**

기존 로그인/로그아웃 함수에 Redis 세션 통합:

```python
# 파일 상단에 import 추가
from ..core.redis_session import get_redis_session_store, RedisSessionStore
import uuid
import time

# oauth_token 함수 수정 (로그인 처리)
async def oauth_token_with_redis(
    grant_type: str = Form(...),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    client_id: str = Form(...),
    client_secret: str = Form(None),
    code_verifier: str = Form(None),
    db: Session = Depends(get_db),
    redis_store: RedisSessionStore = Depends(get_redis_session_store)
):
    """Redis 세션 통합된 OAuth 토큰 발급"""
    
    # ... 기존 토큰 발급 로직 ...
    
    # 토큰 발급 성공 후 Redis에 세션 저장
    if access_token and user:
        session_id = str(uuid.uuid4())
        session_data = {
            "user_id": str(user.id),
            "client_id": client_id,
            "access_token": access_token["access_token"],
            "token_type": access_token["token_type"],
            "expires_in": access_token["expires_in"],
            "scope": access_token.get("scope", ""),
            "created_at": int(time.time()),
            "user_email": user.email,
            "user_role": getattr(user, 'role', 'user')
        }
        
        # Redis에 세션 저장 (토큰 만료시간과 동일하게 설정)
        await redis_store.set_session(
            session_id, 
            session_data, 
            ttl=access_token["expires_in"]
        )
        
        logger.info(f"✅ Redis 세션 생성: {session_id} for user {user.email}")
        
        # 응답에 세션 ID 포함
        access_token["session_id"] = session_id
    
    return access_token

# oauth_logout 함수를 앞에서 작성한 improved 버전으로 교체하고 Redis 통합
async def oauth_logout_with_redis(
    request: Request,
    post_logout_redirect_uri: Optional[str] = None,
    client_id: Optional[str] = None,
    id_token_hint: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db),
    redis_store: RedisSessionStore = Depends(get_redis_session_store)
):
    """Redis 세션 통합된 로그아웃"""
    
    # ... 앞에서 작성한 enhanced logout 로직 활용 ...
    
    # Redis 세션 정리 추가
    try:
        if target_user_id:
            # 사용자의 모든 Redis 세션 삭제
            deleted_sessions = await redis_store.delete_user_sessions(target_user_id)
            logout_stats["redis_sessions_deleted"] = deleted_sessions
            logger.info(f"✅ Redis에서 {deleted_sessions}개 세션 삭제: {target_user_id}")
            
        # 특정 세션 ID가 있다면 해당 세션도 삭제
        session_id = request.headers.get("X-Session-ID") or request.cookies.get("session_id")
        if session_id:
            await redis_store.delete_session(session_id)
            logout_stats["specific_session_deleted"] = 1
            
    except Exception as e:
        logger.error(f"❌ Redis 세션 정리 실패: {e}")
    
    # ... 나머지 로직은 동일 ...
```

---

## 4. FastAPI 애플리케이션 통합

### A. 애플리케이션 시작/종료 시 Redis 연결 관리

**파일 수정: `/home/lee/maxproject/maxplatform/backend/app/main.py`**

```python
from .core.redis_session import redis_session_store

# 애플리케이션 시작 이벤트
@app.on_event("startup")
async def startup_event():
    try:
        await redis_session_store.connect()
        logger.info("🚀 애플리케이션 시작 - Redis 세션 스토어 준비 완료")
    except Exception as e:
        logger.error(f"❌ Redis 세션 스토어 초기화 실패: {e}")
        # Redis 실패시 애플리케이션 계속 실행하되 경고 로그

@app.on_event("shutdown")
async def shutdown_event():
    await redis_session_store.disconnect()
    logger.info("🔌 애플리케이션 종료 - Redis 연결 해제 완료")
```

### B. 환경 변수 설정

**파일 수정: `/home/lee/maxproject/maxplatform/.env`**

```bash
# Redis 세션 설정
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_redis_password_here
SESSION_TTL=3600  # 1시간

# 기존 설정들...
```

### C. Settings 업데이트

**파일 수정: `/home/lee/maxproject/maxplatform/backend/app/core/config.py`**

```python
class Settings(BaseSettings):
    # 기존 설정들...
    
    # Redis 세션 설정
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None
    session_ttl: int = 3600  # 기본 1시간
    
    class Config:
        env_file = ".env"
```

---

## 5. 프론트엔드 세션 연동

### A. 세션 ID 관리

**파일 수정: `/home/lee/maxproject/maxlab/frontend/src/utils/popupOAuth.ts`**

세션 ID를 받아서 요청 헤더에 포함:

```typescript
// OAuth 성공 후 세션 ID 저장
if (tokenData.session_id) {
    sessionStorage.setItem('oauth_session_id', tokenData.session_id);
}

// API 요청 시 세션 ID 헤더 포함
const sessionId = sessionStorage.getItem('oauth_session_id');
if (sessionId) {
    headers['X-Session-ID'] = sessionId;
}
```

### B. 로그아웃 시 세션 정리

**파일 수정: `/home/lee/maxproject/maxlab/frontend/src/stores/authStore.ts`**

```typescript
logout: async () => {
    // ... 기존 로직 ...
    
    // 세션 ID도 정리
    sessionStorage.removeItem('oauth_session_id');
    
    // ... 나머지 로직 ...
}
```

---

## 6. 모니터링 및 디버깅

### A. Redis 세션 모니터링

```bash
# 현재 세션 수 확인
redis-cli --scan --pattern "session:oauth:*" | wc -l

# 특정 세션 데이터 확인
redis-cli get "session:oauth:session-id-here"

# 사용자별 세션 목록
redis-cli smembers "user_sessions:user-id-here"

# Redis 메모리 사용량
redis-cli info memory
```

### B. 로그 모니터링

```bash
# Redis 세션 관련 로그 확인
tail -f /home/lee/maxproject/maxplatform/logs/app.log | grep "Redis\|세션"

# 성공적인 세션 생성 확인
grep "Redis 세션 생성" /home/lee/maxproject/maxplatform/logs/app.log
```

---

## 7. 프로덕션 고려사항

### A. Redis 클러스터 설정 (확장성)

```bash
# Redis Cluster 설정 예시 (고가용성)
# redis-cluster-node1.conf
port 7000
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly yes
```

### B. Redis 백업 설정

```bash
# 자동 백업 설정
save 900 1
save 300 10  
save 60 10000

# 백업 파일 위치
dir /var/lib/redis
dbfilename dump.rdb
```

### C. 보안 강화

```bash
# Redis ACL 설정 (Redis 6.0+)
user session_user on >secure_password_here ~session:* +@read +@write +@string
```

---

## 8. 테스트 시나리오

### A. 세션 공유 테스트

```bash
# 1. 첫 번째 워커에서 로그인
curl -X POST "http://localhost:8000/oauth/token" -d "grant_type=authorization_code&code=..."

# 2. 두 번째 워커로 API 호출 (세션이 공유되는지 확인)
curl -H "Authorization: Bearer token" "http://localhost:8001/api/user/profile"
```

### B. 로그아웃 테스트

```bash
# 로그아웃 후 모든 세션이 정리되는지 확인
curl "http://localhost:8000/oauth/logout?post_logout_redirect_uri=..."
redis-cli --scan --pattern "session:oauth:*"  # 비어있어야 함
```

---

## 9. 트러블슈팅

### A. 일반적인 문제들

| 문제 | 원인 | 해결책 |
|------|------|--------|
| Redis 연결 실패 | 방화벽/네트워크 | `telnet localhost 6379` |
| 세션 데이터 없음 | TTL 만료 | TTL 값 확인 및 조정 |
| 메모리 부족 | Redis maxmemory | 메모리 정책 조정 |
| 성능 저하 | 대량 세션 | 정리 스크립트 실행 |

### B. 진단 명령어

```bash
# Redis 상태 확인
redis-cli ping
redis-cli info server
redis-cli client list

# 세션 통계
redis-cli info stats
redis-cli dbsize
```

---

## 완료 확인

✅ **이 가이드 완료 후 확인사항:**

1. **세션 공유 확인**: 서로 다른 워커에서 같은 사용자 인증 상태 접근 가능
2. **무한루프 해결**: 재로그인 시 NS_BINDING_ABORTED 오류 없음
3. **로그아웃 완전성**: 모든 세션이 Redis에서 정리됨
4. **모니터링**: Redis 세션 생성/삭제 로그 정상 출력

---

**🎯 최종 결과**: 워커 프로세스 간 세션 공유로 OAuth 무한루프 근본 해결