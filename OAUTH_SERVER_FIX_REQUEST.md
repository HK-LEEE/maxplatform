# OAuth 서버 수정 요청서

## 요약
MaxLab Frontend에서 OAuth 인증 시 이미 인증된 사용자의 경우 로그인이 완료되지 않는 문제가 발생하고 있습니다. OAuth 서버가 `OAUTH_ALREADY_AUTHENTICATED` 메시지를 보내지만 실제 인증 데이터(authorization code 또는 access token)를 포함하지 않아 인증 프로세스가 중단됩니다.

## 현재 동작

### 신규 로그인 사용자 (정상 동작)
1. 사용자가 OAuth 로그인 버튼 클릭
2. OAuth 서버 팝업 창에서 인증
3. Callback URL로 리다이렉트 (`/oauth/callback?code=xxx&state=yyy`)
4. Authorization code를 access token으로 교환
5. 로그인 완료

### 이미 인증된 사용자 (문제 발생)
1. 사용자가 OAuth 로그인 버튼 클릭
2. OAuth 서버가 `OAUTH_ALREADY_AUTHENTICATED` 메시지 전송
3. **문제: authorization code나 access token이 없음**
4. 클라이언트가 무한 대기 상태
5. 로그인 실패

## 문제점 상세 분석

### OAuth 서버 응답 내용
```javascript
// 현재 OAuth 서버가 보내는 메시지
{
  type: "OAUTH_ALREADY_AUTHENTICATED",
  oauthParams: {
    // 실제 인증 데이터가 아닌 클라이언트 요청 파라미터만 포함
    response_type: "code",
    client_id: "maxlab",
    redirect_uri: "https://maxlab.dwchem.co.kr/oauth/callback",
    scope: "openid profile email offline_access",
    state: "HRtRjUe-k1CKOa0Sk3-KTdGWDrwkPE35I9VTNjQnILM",
    code_challenge: "k21lFSzMRNLHclwKDOKqd9V-bJX3GPm7eLHnRZBA6kw",
    code_challenge_method: "S256",
    nonce: "P_pxSwDY2l9ftFGjObo2Ftn8KRUZPjnobFW-x_Ho7-o"
  }
}
```

### 문제점
1. **OAuth 2.0 표준 미준수**: 인증된 사용자에게도 authorization code를 제공해야 함
2. **인증 데이터 누락**: `code` 또는 `access_token`이 없음
3. **잘못된 응답 구조**: 클라이언트 요청 파라미터를 그대로 반환

## 수정 요청 사항

### Option 1: Authorization Code 제공 (권장)
```javascript
// 수정된 OAuth 서버 응답
{
  type: "OAUTH_ALREADY_AUTHENTICATED",
  oauthParams: {
    code: "generated_authorization_code_here",  // 실제 authorization code
    state: "HRtRjUe-k1CKOa0Sk3-KTdGWDrwkPE35I9VTNjQnILM"  // 원래 state 유지
  }
}
```

## OAuth 2.0 표준 참조

RFC 6749 Section 4.1.2에 따르면:
> "If the resource owner grants the access request, the authorization server issues an authorization code and delivers it to the client"

이미 인증된 사용자의 경우에도:
- 자동 승인(auto-approval) 후 authorization code 발급
- 또는 사용자 확인 없이 즉시 code 생성

## 구현 예시 (서버 측 수정)

```python
# Python/Flask 예시
@app.route('/api/oauth/authorize')
def oauth_authorize():
    user = get_authenticated_user()
    
    if user and user.is_authenticated:
        # 이미 인증된 사용자
        if client_has_approval(user, client_id, scope):
            # Authorization code 생성
            auth_code = generate_authorization_code(
                user_id=user.id,
                client_id=request.args.get('client_id'),
                scope=request.args.get('scope'),
                redirect_uri=request.args.get('redirect_uri')
            )
            
            # Option 1: PostMessage로 전달
            return send_oauth_message({
                'type': 'OAUTH_ALREADY_AUTHENTICATED',
                'oauthParams': {
                    'code': auth_code,
                    'state': request.args.get('state')
                }
            })
            
            # Option 2: 직접 리다이렉트
            # return redirect(f"{redirect_uri}?code={auth_code}&state={state}")
```

## 영향도 및 우선순위

### 영향도: **높음**
- 현재 이미 인증된 사용자는 로그인할 수 없음
- 사용자 경험 심각하게 저하
- 페이지 새로고침 필요

### 우선순위: **긴급**
- 프로덕션 환경에서 발생
- 모든 재방문 사용자에게 영향

## 테스트 시나리오

수정 후 다음 시나리오를 테스트해야 합니다:

1. **신규 사용자 로그인**
   - OAuth 팝업에서 인증
   - Callback으로 정상 리다이렉트
   - 토큰 교환 성공

2. **이미 인증된 사용자 재로그인**
   - OAuth 팝업 열림
   - Authorization code 즉시 제공
   - 토큰 교환 성공
   - 팝업 자동 닫힘

3. **다른 계정으로 전환**
   - Force account selection 옵션
   - 계정 선택 화면 표시
   - 새 계정으로 로그인

## 연락처

문제 해결 관련 문의:
- Frontend 팀: [MaxLab Frontend Team]
- 담당자: [이름]
- 이메일: [이메일]

## 참고 자료

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- MaxLab Frontend 코드: `src/utils/popupOAuth.ts` (line 893-960)

---

작성일: 2025-08-07
문서 버전: 1.0