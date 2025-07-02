# OAuth 2.0 통합 테스트 가이드

## 구현 완료 사항

### ✅ 1. OAuth Authorization 엔드포인트 개선
- **미로그인 사용자 처리**: 로그인 페이지로 자동 리다이렉트
- **OAuth 파라미터 보존**: 로그인 후 원래 OAuth 요청으로 복귀
- **자동 승인 로직**: 신뢰할 수 있는 MAX Platform 클라이언트 자동 승인
- **세션 관리**: 기존 권한 확인 및 세션 업데이트

### ✅ 2. 팝업 기반 OAuth 로그인 시스템
- **PopupOAuthLogin 클래스**: 팝업 창을 통한 OAuth 플로우
- **PostMessage 통신**: 팝업과 부모 창 간 안전한 데이터 전달
- **PKCE 지원**: 보안 강화된 Authorization Code Flow
- **자동 정리**: 팝업 종료 및 리소스 정리

### ✅ 3. MAX Platform 로그인 페이지 개선
- **OAuth 복귀 처리**: oauth_return 파라미터 처리
- **자동 리다이렉트**: 로그인 후 OAuth 플로우 자동 재개

## 테스트 시나리오

### 시나리오 1: 신규 사용자 OAuth 로그인

#### 초기 상태
- maxflowstudio 사용자가 로그아웃 상태
- MAX Platform에도 로그인되지 않음

#### 테스트 단계
1. **maxflowstudio에서 OAuth 로그인 시도**
   ```
   http://localhost:3005 → "MAX Platform으로 로그인" 버튼 클릭
   ```

2. **팝업 창 열림**
   ```
   팝업 창에서 MAX Platform 로그인 페이지 표시
   URL: http://localhost:3000/login?oauth_return=...
   ```

3. **MAX Platform 로그인**
   ```
   팝업에서 admin@test.com / admin123 입력 후 로그인
   ```

4. **OAuth 자동 승인**
   ```
   로그인 성공 후 자동으로 OAuth 요청 처리
   maxflowstudio로 authorization code 전달
   ```

5. **토큰 교환 및 완료**
   ```
   팝업 창 자동 종료
   maxflowstudio에서 토큰 획득 및 사용자 정보 표시
   ```

### 시나리오 2: 기존 사용자 OAuth 로그인

#### 초기 상태
- MAX Platform에 이미 로그인된 상태
- maxflowstudio에서는 로그아웃 상태

#### 테스트 단계
1. **maxflowstudio에서 OAuth 로그인 시도**
   ```
   "MAX Platform으로 로그인" 버튼 클릭
   ```

2. **즉시 승인**
   ```
   팝업 창이 열리지만 즉시 OAuth 승인 처리
   기존 세션 확인 후 자동 승인
   ```

3. **빠른 완료**
   ```
   팝업 창 즉시 종료
   토큰 획득 및 로그인 완료
   ```

### 시나리오 3: 에러 처리 테스트

#### 팝업 차단 테스트
1. 브라우저에서 팝업 차단 설정
2. OAuth 로그인 시도
3. "팝업이 차단되었습니다" 에러 메시지 확인

#### 네트워크 오류 테스트
1. 백엔드 서버 중지
2. OAuth 로그인 시도
3. 적절한 에러 메시지 표시 확인

## 실제 테스트 방법

### 1. 백엔드 서버 실행
```bash
cd /home/lee/proejct/maxplatform/backend
python app/main.py
```

### 2. MAX Platform 프론트엔드 실행
```bash
cd /home/lee/proejct/maxplatform/frontend
npm run dev
```

### 3. maxflowstudio 설정
maxflowstudio 프로젝트에 다음 파일들 추가:
- `/src/utils/popupOAuth.js`
- `/src/pages/OAuthCallback.jsx`
- 로그인 페이지에 OAuth 버튼 추가
- 라우터에 `/oauth/callback` 경로 등록

### 4. 테스트 실행
1. `http://localhost:3005` 접속 (maxflowstudio)
2. "MAX Platform으로 로그인" 버튼 클릭
3. 팝업에서 MAX Platform 로그인 진행
4. 자동 승인 및 토큰 획득 확인

## 디버깅 팁

### 브라우저 개발자 도구 활용
```javascript
// 팝업 통신 디버깅
window.addEventListener('message', (event) => {
  console.log('PostMessage received:', event.data);
});

// OAuth 상태 확인
console.log('OAuth State:', sessionStorage.getItem('oauth_state'));
console.log('Code Verifier:', sessionStorage.getItem('oauth_code_verifier'));
```

### 백엔드 로그 확인
```bash
# OAuth 관련 로그 필터링
tail -f backend_logs.log | grep -i oauth
```

### 네트워크 요청 모니터링
1. 브라우저 개발자 도구 → Network 탭
2. OAuth 플로우 진행하며 다음 요청들 확인:
   - `GET /api/oauth/authorize`
   - `POST /api/oauth/token`
   - `GET /api/oauth/userinfo`

## 성공 기준

### ✅ 기능적 요구사항
- [ ] 팝업을 통한 OAuth 로그인 완료
- [ ] 로그인 후 자동으로 maxflowstudio로 복귀
- [ ] 사용자 정보 정상 획득
- [ ] 기존 로그인 사용자 자동 승인

### ✅ 사용자 경험 요구사항
- [ ] 팝업 차단 시 적절한 안내 메시지
- [ ] 로딩 상태 표시
- [ ] 에러 상황 처리
- [ ] 팝업 자동 종료

### ✅ 보안 요구사항
- [ ] PKCE 구현 완료
- [ ] State 파라미터 검증
- [ ] Origin 검증을 통한 PostMessage 보안
- [ ] 토큰 안전 저장

## 추가 개선 사항

### 1. 토큰 갱신 자동화
```javascript
// 토큰 만료 시 자동 갱신
setInterval(async () => {
  const token = localStorage.getItem('access_token');
  if (token && isTokenExpiringSoon(token)) {
    await refreshToken();
  }
}, 60000); // 1분마다 체크
```

### 2. 로그아웃 동기화
```javascript
// MAX Platform 로그아웃 시 maxflowstudio도 로그아웃
window.addEventListener('storage', (e) => {
  if (e.key === 'access_token' && e.newValue === null) {
    // 로그아웃 처리
    handleLogout();
  }
});
```

### 3. 오프라인 지원
```javascript
// 네트워크 상태 확인
if (!navigator.onLine) {
  showOfflineMessage();
  return;
}
```

이 가이드를 통해 maxflowstudio의 OAuth 2.0 통합을 완전히 테스트하고 검증할 수 있습니다.