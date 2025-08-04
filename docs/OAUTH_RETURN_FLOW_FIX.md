# OAuth Return Flow 수정 가이드

## 현재 문제

OAuth 서버가 `oauth_return` 방식을 사용하지만, 로그인 후 OAuth 플로우를 계속하지 않고 있습니다.

### 현재 플로우 (문제 있음)
1. `/api/oauth/authorize` 요청 (prompt=login)
2. 세션 무효화 후 `/login?oauth_return=...` 로 리다이렉트
3. 사용자 로그인
4. ❌ **문제: 로그인 후 OAuth 플로우가 계속되지 않음**

### 올바른 플로우
1. `/api/oauth/authorize` 요청 (prompt=login)
2. 세션 무효화 후 `/login?oauth_return=...` 로 리다이렉트
3. 사용자 로그인
4. ✅ **로그인 성공 후 `/api/oauth/authorize` 로 다시 리다이렉트**
5. Authorization code 생성
6. Callback URL로 최종 리다이렉트

## OAuth 서버 수정 필요 사항

### 1. OAuth Authorization Endpoint

```python
# backend/app/routers/oauth.py
import json
from urllib.parse import quote, unquote

@router.get("/api/oauth/authorize")
async def authorize(
    request: Request,
    response: Response,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None,
    nonce: Optional[str] = None,
    prompt: Optional[str] = None,
    max_age: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # 현재 로그인된 사용자 확인
    current_user = get_current_user_from_session(request, db)
    
    # prompt=login 처리 (강제 재로그인)
    if prompt == "login":
        if current_user:
            # 현재 세션 쿠키 삭제
            response.delete_cookie("session_id")
            response.delete_cookie("session_token")
        
        # OAuth 파라미터를 JSON으로 인코딩
        oauth_params = {
            "response_type": response_type,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "nonce": nonce,
            "prompt": prompt,
            "max_age": max_age
        }
        
        # None 값 제거
        oauth_params = {k: v for k, v in oauth_params.items() if v is not None}
        
        # JSON으로 인코딩하고 URL 인코딩
        oauth_return = quote(json.dumps(oauth_params))
        
        # 로그인 페이지로 리다이렉트
        login_url = f"/login?oauth_return={oauth_return}&force_login=true"
        return RedirectResponse(url=login_url, status_code=302)
    
    # 로그인되지 않은 경우
    if not current_user:
        # OAuth 파라미터 인코딩 (위와 동일)
        oauth_params = {
            "response_type": response_type,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "nonce": nonce
        }
        oauth_params = {k: v for k, v in oauth_params.items() if v is not None}
        oauth_return = quote(json.dumps(oauth_params))
        
        login_url = f"/login?oauth_return={oauth_return}"
        return RedirectResponse(url=login_url)
    
    # 로그인된 경우 authorization code 생성
    auth_code = generate_authorization_code(
        user_id=current_user.id,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        nonce=nonce
    )
    
    # 클라이언트로 리다이렉트
    redirect_url = f"{redirect_uri}?code={auth_code}&state={state}"
    return RedirectResponse(url=redirect_url)
```

### 2. 로그인 처리 Endpoint

```python
# backend/app/routers/auth.py

@router.post("/api/auth/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    oauth_return: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # 사용자 인증
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "잘못된 이메일 또는 비밀번호입니다.",
                "oauth_return": oauth_return
            }
        )
    
    # 세션 생성
    session_token = create_session(user.id, db)
    response.set_cookie("session_token", session_token, httponly=True)
    
    # OAuth return 처리
    if oauth_return:
        try:
            # URL 디코딩 후 JSON 파싱
            decoded_return = unquote(oauth_return)
            oauth_params = json.loads(decoded_return)
            
            # OAuth authorize URL 재구성
            query_params = urllib.parse.urlencode(oauth_params)
            oauth_url = f"/api/oauth/authorize?{query_params}"
            
            # OAuth 플로우로 다시 리다이렉트
            return RedirectResponse(url=oauth_url, status_code=302)
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"OAuth return 파싱 실패: {e}")
            # 기본 대시보드로 리다이렉트
            return RedirectResponse(url="/dashboard")
    
    # OAuth가 아닌 일반 로그인인 경우
    return RedirectResponse(url="/dashboard")
```

### 3. 로그인 페이지 Template

```html
<!-- templates/login.html -->
<!DOCTYPE html>
<html>
<head>
    <title>로그인 - MAX Platform</title>
</head>
<body>
    <div class="login-container">
        {% if force_login %}
        <div class="alert alert-info">
            다른 계정으로 로그인하려면 이메일과 비밀번호를 입력하세요.
        </div>
        {% endif %}
        
        <form method="POST" action="/api/auth/login">
            <!-- oauth_return을 hidden field로 전달 -->
            {% if oauth_return %}
            <input type="hidden" name="oauth_return" value="{{ oauth_return }}">
            {% endif %}
            
            <div class="form-group">
                <label>이메일</label>
                <input type="email" name="username" required>
            </div>
            
            <div class="form-group">
                <label>비밀번호</label>
                <input type="password" name="password" required>
            </div>
            
            <button type="submit">로그인</button>
        </form>
    </div>
</body>
</html>
```

## 핵심 포인트

1. **OAuth 파라미터 보존**: JSON으로 인코딩하여 `oauth_return` 파라미터에 저장
2. **로그인 후 OAuth 재개**: 로그인 성공 시 저장된 OAuth 파라미터로 `/api/oauth/authorize` 재호출
3. **세션 관리**: `prompt=login` 시 기존 세션 삭제
4. **에러 처리**: JSON 파싱 실패 시 안전하게 처리

## 테스트 시나리오

1. **일반 OAuth 플로우**
   - 로그인되지 않은 상태에서 OAuth 요청
   - 로그인 페이지로 리다이렉트
   - 로그인 후 OAuth 플로우 완료

2. **강제 재로그인 (prompt=login)**
   - 이미 로그인된 상태에서 OAuth 요청
   - 세션 삭제 후 로그인 페이지로 리다이렉트
   - 새 계정으로 로그인
   - OAuth 플로우 완료

3. **에러 케이스**
   - 잘못된 oauth_return 값
   - 로그인 실패 시 oauth_return 유지

## 디버깅 팁

1. 로그인 페이지 URL에서 `oauth_return` 파라미터 확인
2. 로그인 후 리다이렉트되는 URL 확인
3. 최종적으로 callback URL로 리다이렉트되는지 확인
4. Authorization code와 state가 올바르게 전달되는지 확인