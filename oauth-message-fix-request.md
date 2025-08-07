# OAuth postMessage 구조 수정 요청서

## 대상 시스템
- **서버**: max.dwchem.co.kr (인증 서버)
- **수정 위치**: OAuth 콜백 페이지의 postMessage 전송 코드

## 문제점
현재 max.dwchem.co.kr에서 maxlab.dwchem.co.kr로 보내는 OAuth 메시지가 표준 구조를 따르지 않아 메시지 검증에 실패합니다.

## 수정 내용

### 현재 구조 (문제)
```javascript
// 현재 max.dwchem.co.kr에서 보내는 메시지
window.opener.postMessage({
  type: "OAUTH_LOGIN_SUCCESS_CONTINUE",
  oauthParams: {
    code: "...",
    state: "..."
  },
  timestamp: 1754540685332
}, "https://maxlab.dwchem.co.kr");
```

### 수정된 구조 (표준)
```javascript
// 수정 필요: 표준 postMessage 구조
window.opener.postMessage({
  type: "OAUTH_MESSAGE",  // 최상위 메시지 타입
  data: {                 // 실제 데이터는 data 필드에 캡슐화
    type: "OAUTH_LOGIN_SUCCESS_CONTINUE",
    oauthParams: {
      code: "...",
      state: "..."
    },
    timestamp: Date.now()
  }
}, "https://maxlab.dwchem.co.kr");
```

## 수정이 필요한 모든 메시지 타입

### 1. OAUTH_LOGIN_SUCCESS_CONTINUE
```javascript
window.opener.postMessage({
  type: "OAUTH_MESSAGE",
  data: {
    type: "OAUTH_LOGIN_SUCCESS_CONTINUE",
    oauthParams: {...},
    timestamp: Date.now()
  }
}, targetOrigin);
```

### 2. OAUTH_ALREADY_AUTHENTICATED
```javascript
window.opener.postMessage({
  type: "OAUTH_MESSAGE",
  data: {
    type: "OAUTH_ALREADY_AUTHENTICATED",
    oauthParams: {...},
    timestamp: Date.now()
  }
}, targetOrigin);
```

### 3. OAUTH_ERROR
```javascript
window.opener.postMessage({
  type: "OAUTH_MESSAGE",
  data: {
    type: "OAUTH_ERROR",
    error: {
      code: "...",
      message: "..."
    },
    timestamp: Date.now()
  }
}, targetOrigin);
```

### 4. OAUTH_CANCELLED
```javascript
window.opener.postMessage({
  type: "OAUTH_MESSAGE",
  data: {
    type: "OAUTH_CANCELLED",
    timestamp: Date.now()
  }
}, targetOrigin);
```

## 구현 예시 (전체 함수)

```javascript
function sendOAuthMessage(messageType, payload = {}) {
  // 타겟 오리진 확인
  const allowedOrigins = [
    'https://maxlab.dwchem.co.kr',
    'https://devmaxlab.dwchem.co.kr'
  ];
  
  const targetOrigin = window.opener?.location?.origin;
  
  if (!allowedOrigins.includes(targetOrigin)) {
    console.error('Invalid target origin:', targetOrigin);
    return;
  }
  
  // 표준 메시지 구조
  const message = {
    type: 'OAUTH_MESSAGE',  // 최상위 타입은 항상 OAUTH_MESSAGE
    data: {
      type: messageType,    // 실제 메시지 타입
      ...payload,          // 페이로드 데이터
      timestamp: Date.now()
    }
  };
  
  // 메시지 전송
  window.opener.postMessage(message, targetOrigin);
  
  // 로깅 (개발 환경)
  if (process.env.NODE_ENV === 'development') {
    console.log('OAuth message sent:', message);
  }
}

// 사용 예시
sendOAuthMessage('OAUTH_LOGIN_SUCCESS_CONTINUE', {
  oauthParams: {
    code: authCode,
    state: state
  }
});

sendOAuthMessage('OAUTH_ALREADY_AUTHENTICATED', {
  oauthParams: {
    userId: currentUser.id
  }
});

sendOAuthMessage('OAUTH_ERROR', {
  error: {
    code: 'AUTH_FAILED',
    message: 'Authentication failed'
  }
});
```

## 테스트 방법

1. 개발 환경에서 먼저 테스트
2. 브라우저 콘솔에서 메시지 구조 확인
3. maxlab.dwchem.co.kr의 메시지 검증 통과 확인

## 영향 범위

- **영향 받는 도메인**: 
  - maxlab.dwchem.co.kr
  - devmaxlab.dwchem.co.kr
  
- **하위 호환성**: 
  - 가능하면 양쪽 구조 모두 지원하도록 수정 권장

## 우선순위
**높음** - 현재 로그인 기능이 차단되고 있음

## 참고 자료
- [MDN Web Docs - postMessage](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage)
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)

---

작성일: 2025-08-07
작성자: MaxLab Backend Team