# OAuth 서버 구현 체크리스트

## 문제 요약

OAuth 서버가 `oauth_return` 방식을 사용하지만, 로그인 후 OAuth 플로우를 계속하지 않아 프론트엔드와 통신이 되지 않습니다.

## 구현 확인 사항

### 1. OAuth Authorization Endpoint (`/api/oauth/authorize`)

- [ ] `prompt=login` 파라미터 처리
  - [ ] 현재 세션 쿠키 삭제
  - [ ] OAuth 파라미터를 JSON으로 인코딩하여 `oauth_return`에 저장
  - [ ] `/login?oauth_return=...&force_login=true`로 리다이렉트

- [ ] 로그인되지 않은 경우 처리
  - [ ] OAuth 파라미터를 `oauth_return`에 저장
  - [ ] `/login?oauth_return=...`로 리다이렉트

- [ ] 로그인된 경우 처리
  - [ ] Authorization code 생성
  - [ ] Callback URL로 리다이렉트 (`redirect_uri?code=xxx&state=xxx`)

### 2. Login Endpoint (`/api/auth/login` 또는 로그인 처리 부분)

- [ ] 로그인 폼에서 `oauth_return` 파라미터 수신
- [ ] 사용자 인증 성공 시:
  - [ ] `oauth_return` URL 디코딩
  - [ ] JSON 파싱하여 OAuth 파라미터 복원
  - [ ] OAuth authorize URL 재구성
  - [ ] `/api/oauth/authorize?...` 로 리다이렉트
- [ ] 로그인 실패 시:
  - [ ] `oauth_return` 값 유지하여 재시도 가능하게

### 3. Login Page Template

- [ ] Hidden field로 `oauth_return` 전달
- [ ] `force_login=true`일 때 특별 메시지 표시
- [ ] 로그인 폼이 `/api/auth/login`으로 POST 전송

## 테스트 방법

### 1. 수동 테스트

1. 브라우저에서 직접 OAuth URL 접속:
   ```
   http://localhost:8000/api/oauth/authorize?response_type=code&client_id=maxlab&redirect_uri=http://localhost:3010/oauth/callback&scope=openid%20profile%20email&state=test123&prompt=login
   ```

2. 로그인 페이지로 리다이렉트되는지 확인
3. URL에 `oauth_return` 파라미터가 있는지 확인
4. 로그인 후 어디로 이동하는지 확인

### 2. 디버그 로그 추가

```python
# OAuth Authorization Endpoint
logger.info(f"OAuth authorize called with prompt={prompt}")
logger.info(f"Creating oauth_return: {oauth_params}")

# Login Endpoint
logger.info(f"Login called with oauth_return={oauth_return}")
if oauth_return:
    logger.info(f"Decoded oauth_return: {decoded_return}")
    logger.info(f"Redirecting to: {oauth_url}")
```

### 3. 예상 로그 시퀀스

```
1. OAuth authorize called with prompt=login
2. Creating oauth_return: {"response_type": "code", ...}
3. Redirecting to /login?oauth_return=...
4. Login called with oauth_return=%7B%22response_type%22%3A...
5. Decoded oauth_return: {"response_type": "code", ...}
6. Redirecting to: /api/oauth/authorize?response_type=code&...
7. OAuth authorize called with prompt=None
8. Generating authorization code
9. Redirecting to http://localhost:3010/oauth/callback?code=xxx&state=xxx
```

## 일반적인 실수

1. **oauth_return을 파싱하지 않음**
   - 로그인 후 단순히 홈페이지로 리다이렉트

2. **JSON 인코딩/디코딩 오류**
   - URL 인코딩과 JSON 파싱 순서 문제

3. **세션 쿠키 처리 오류**
   - Response 객체 없이 쿠키 삭제 시도

4. **리다이렉트 루프**
   - 로그인 확인 로직이 잘못되어 무한 리다이렉트

## 참고 코드

### FastAPI 예제
```python
from fastapi import Form, Response
from fastapi.responses import RedirectResponse
import json
from urllib.parse import quote, unquote, urlencode

@app.post("/api/auth/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    oauth_return: Optional[str] = Form(None)
):
    # 인증 로직...
    
    if oauth_return:
        try:
            decoded = unquote(oauth_return)
            params = json.loads(decoded)
            query_string = urlencode(params)
            return RedirectResponse(
                url=f"/api/oauth/authorize?{query_string}",
                status_code=302
            )
        except Exception as e:
            logger.error(f"OAuth return parsing failed: {e}")
    
    return RedirectResponse(url="/dashboard")
```

### Express.js 예제
```javascript
app.post('/api/auth/login', (req, res) => {
    const { username, password, oauth_return } = req.body;
    
    // 인증 로직...
    
    if (oauth_return) {
        try {
            const decoded = decodeURIComponent(oauth_return);
            const params = JSON.parse(decoded);
            const queryString = new URLSearchParams(params).toString();
            return res.redirect(`/api/oauth/authorize?${queryString}`);
        } catch (e) {
            console.error('OAuth return parsing failed:', e);
        }
    }
    
    res.redirect('/dashboard');
});
```