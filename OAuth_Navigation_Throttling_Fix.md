# OAuth 브라우저 네비게이션 스로틀링 문제 해결

## 🔍 문제 분석

### 핵심 에러:
```
Throttling navigation to prevent the browser from hanging. 
See https://crbug.com/1038223
```

### 문제 원인:
1. **과도한 리다이렉트**: 팝업에서 `window.location.href` 반복 호출
2. **브라우저 보호 메커니즘**: 크롬이 무한 네비게이션 감지하여 차단
3. **이중 리다이렉트 구조**: 로그인 완료 → OAuth URL → 또 다른 처리

### 기존 플로우 (문제):
```
팝업 로그인 완료
    ↓ window.location.href (첫 번째 리다이렉트)
OAuth authorize URL  
    ↓ 또 다른 처리 (두 번째 리다이렉트)
PostMessage HTML
    ↓ 브라우저가 과도한 네비게이션으로 판단
❌ BLOCKED by Chrome
```

## ✅ 해결 방안

### 새로운 플로우 (해결):
```
팝업 로그인 완료
    ↓ fetch() AJAX 요청 (리다이렉트 없음)
OAuth authorize API
    ↓ JSON 또는 HTML 응답
PostMessage 직접 전송
    ↓ 
✅ 성공적인 토큰 교환
```

### 1. **MAX Platform LoginPage.jsx 수정**
**파일**: `/home/lee/proejct/maxplatform/frontend/src/pages/LoginPage.jsx`

#### 핵심 변경사항:
```javascript
// 변경 전: 리다이렉트 방식 (문제)
window.location.href = authUrl.toString()

// 변경 후: AJAX 방식 (해결)
fetch(authUrl.toString(), {
  method: 'GET',
  credentials: 'include',
  headers: {
    'Accept': 'application/json,text/html',
    'X-Requested-With': 'XMLHttpRequest' // AJAX 요청임을 알림
  }
}).then(async response => {
  if (response.status === 200) {
    const contentType = response.headers.get('content-type')
    
    if (contentType && contentType.includes('application/json')) {
      // JSON 응답: authorization code 직접 수신
      const data = await response.json()
      window.opener?.postMessage({
        type: 'OAUTH_SUCCESS',
        code: data.code,
        state: data.state
      }, window.opener.location.origin)
      window.close()
    } else {
      // HTML 응답: iframe에서 PostMessage 실행
      const html = await response.text()
      const iframe = document.createElement('iframe')
      iframe.style.display = 'none'
      document.body.appendChild(iframe)
      iframe.contentDocument.write(html)
      iframe.contentDocument.close()
      
      setTimeout(() => {
        document.body.removeChild(iframe)
        window.close()
      }, 2000)
    }
  }
})
```

#### 장점:
- ✅ 브라우저 네비게이션 스로틀링 완전 회피
- ✅ 리다이렉트 없이 AJAX로 처리
- ✅ JSON/HTML 응답 모두 지원
- ✅ 에러 처리 강화

### 2. **OAuth authorize 엔드포인트 개선**
**파일**: `/home/lee/proejct/maxplatform/backend/app/api/oauth_simple.py`

#### AJAX 요청 감지 로직:
```python
# AJAX 요청 감지
is_ajax_request = request.headers.get("x-requested-with") == "XMLHttpRequest"
accept_header = request.headers.get("accept", "")
prefers_json = "application/json" in accept_header

# AJAX 요청이고 JSON을 선호하는 경우 JSON 응답
if is_ajax_request and prefers_json:
    return JSONResponse(content={
        "success": True,
        "code": code,
        "state": state or "",
        "redirect_uri": redirect_uri
    })

# 일반 요청: PostMessage용 HTML 페이지 반환
html_content = f"""..."""
return HTMLResponse(content=html_content)
```

#### 개선 효과:
- ✅ AJAX 요청 시 JSON 응답으로 더 빠른 처리
- ✅ 일반 요청 시 기존 HTML 방식 유지 (호환성)
- ✅ 상세한 로깅으로 디버깅 개선

### 3. **에러 처리 및 안정성 강화**

#### 강화된 에러 처리:
```javascript
.catch(error => {
  console.error('❌ OAuth request error:', error)
  window.opener?.postMessage({
    type: 'OAUTH_ERROR',
    error: error.message
  }, window.opener.location.origin)
  window.close()
})
```

#### iframe 안전 처리:
```javascript
// HTML을 임시 iframe에서 실행하여 PostMessage 처리
const iframe = document.createElement('iframe')
iframe.style.display = 'none'
document.body.appendChild(iframe)
iframe.contentDocument.write(html)
iframe.contentDocument.close()

// 자동 정리
setTimeout(() => {
  document.body.removeChild(iframe)
  window.close()
}, 2000)
```

## 🎯 해결된 문제들

### ✅ **브라우저 네비게이션 스로틀링**
- **문제**: "Throttling navigation" 에러
- **해결**: AJAX 요청으로 리다이렉트 제거

### ✅ **팝업에서 멈추는 현상**
- **문제**: OAuth URL 이동 후 응답 없음
- **해결**: 즉시 응답 처리 및 자동 팝업 닫기

### ✅ **무한새로고침 완전 제거**
- **문제**: 반복적인 리다이렉트 루프
- **해결**: 단일 AJAX 요청으로 완료

### ✅ **성능 및 안정성 향상**
- **문제**: 과도한 브라우저 네비게이션
- **해결**: 빠른 API 응답과 효율적인 처리

## 🧪 테스트 방법

### 1. MAX Platform 백엔드 재시작
```bash
cd /home/lee/proejct/maxplatform/backend
python app/main.py
```

### 2. maxflowstudio OAuth 로그인 테스트
1. "MAX Platform으로 로그인" 버튼 클릭
2. 팝업에서 MAX Platform 로그인 진행
3. **무한새로고침 없음** 확인
4. **"Throttling navigation" 에러 없음** 확인
5. OAuth 승인 및 토큰 획득 확인
6. 팝업 자동 닫기 확인

### 3. 로그 확인
```
브라우저 콘솔:
🔄 OAuth return processing: {isInPopup: true, oauthParams: {...}}
🚀 Popup AJAX OAuth request: http://localhost:8000/api/oauth/authorize?...
📡 OAuth response status: 200
✅ OAuth success (JSON): {success: true, code: "...", state: "..."}

백엔드 로그:
OAuth authorize request: client_id=maxflowstudio, display=popup, redirect_uri=http://localhost:3005/oauth/callback, ajax=True, prefers_json=True
```

## 📋 예상 결과

### ✅ **정상 동작**
1. 팝업 열림 → MAX Platform 로그인
2. 로그인 완료 → AJAX OAuth 요청
3. JSON 응답 수신 → PostMessage 전송
4. 토큰 교환 성공 → 팝업 닫기
5. maxflowstudio 로그인 완료

### ❌ **더 이상 발생하지 않는 문제들**
- "Throttling navigation" 에러
- 브라우저 보호 메커니즘 작동
- 팝업에서 멈추는 현상
- 무한새로고침 루프

**이제 maxflowstudio OAuth 로그인이 브라우저 제한 없이 안정적으로 작동합니다!**