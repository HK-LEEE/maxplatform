#!/usr/bin/env python3
"""
브라우저 상태 및 세션스토리지 디버깅 스크립트
"""

import requests
import json
import subprocess
import time

def check_browser_console():
    print("🔍 브라우저 상태 및 세션스토리지 디버깅...")
    
    # 브라우저 개발자 도구에서 실행할 JavaScript 코드 생성
    debug_js = """
// 세션스토리지 상태 확인
console.log('🔍 세션스토리지 상태:');
console.log('oauth_processing:', sessionStorage.getItem('oauth_processing'));
console.log('oauth_state:', sessionStorage.getItem('oauth_state'));
console.log('oauth_code_verifier:', sessionStorage.getItem('oauth_code_verifier'));

// 현재 URL 확인
console.log('🔍 현재 URL:', window.location.href);

// URL 파라미터 확인
const urlParams = new URLSearchParams(window.location.search);
console.log('🔍 URL 파라미터:');
urlParams.forEach((value, key) => {
    console.log(`  ${key}: ${value}`);
});

// AuthContext 상태 확인 (React DevTools 필요 없이)
console.log('🔍 인증 상태 확인...');
if (window.localStorage.getItem('access_token')) {
    console.log('✅ access_token 존재:', window.localStorage.getItem('access_token').substring(0, 50) + '...');
} else {
    console.log('❌ access_token 없음');
}

// 무한루프 감지를 위한 카운터 설정
if (!window.debugCounter) {
    window.debugCounter = 0;
}
window.debugCounter++;
console.log('🔄 페이지 로드/리렌더 카운터:', window.debugCounter);

// 팝업 상태 확인
console.log('🔍 창 상태:');
console.log('  window.opener:', !!window.opener);
console.log('  팝업 모드:', window.opener !== null);
"""
    
    print("📋 브라우저 콘솔에서 실행할 디버깅 코드:")
    print("="*60)
    print(debug_js)
    print("="*60)
    
    # 세션스토리지 정리 스크립트
    cleanup_js = """
// 세션스토리지 정리
console.log('🧹 세션스토리지 정리 중...');
sessionStorage.removeItem('oauth_processing');
sessionStorage.removeItem('oauth_state');
sessionStorage.removeItem('oauth_code_verifier');
console.log('✅ 세션스토리지 정리 완료');

// URL 파라미터 정리 (oauth_return 제거)
if (window.location.search.includes('oauth_return')) {
    const url = new URL(window.location);
    url.searchParams.delete('oauth_return');
    window.history.replaceState({}, '', url);
    console.log('✅ URL oauth_return 파라미터 제거 완료');
}
"""
    
    print("\n📋 세션스토리지 정리 코드:")
    print("="*60)
    print(cleanup_js)
    print("="*60)
    
    # 강제 OAuth 테스트 스크립트
    force_oauth_js = """
// 강제 OAuth 테스트
console.log('🚀 강제 OAuth 테스트 시작...');

// 세션스토리지 정리
sessionStorage.clear();

// 테스트용 OAuth 파라미터
const oauthParams = {
    response_type: 'code',
    client_id: 'maxflowstudio',
    redirect_uri: 'http://localhost:3005/oauth/callback',
    scope: 'read:profile read:groups manage:workflows',
    state: 'manual_test_' + Date.now(),
    code_challenge: 'test_challenge_' + Date.now(),
    code_challenge_method: 'S256',
    display: 'popup'
};

// OAuth URL 생성
const authUrl = new URL('http://localhost:8000/api/oauth/authorize');
Object.keys(oauthParams).forEach(key => {
    authUrl.searchParams.append(key, oauthParams[key]);
});

console.log('🔗 OAuth URL:', authUrl.toString());

// 현재 창이 팝업인지 확인
if (window.opener) {
    console.log('✅ 팝업 모드에서 실행 중');
    console.log('🚀 OAuth URL로 리다이렉트...');
    window.location.href = authUrl.toString();
} else {
    console.log('❌ 일반 창 모드 - 팝업으로 테스트하세요');
    // 팝업 열기
    const popup = window.open(authUrl.toString(), 'oauth_test', 'width=500,height=600');
    console.log('🎉 OAuth 테스트 팝업 열림:', !!popup);
}
"""
    
    print("\n📋 강제 OAuth 테스트 코드:")
    print("="*60)
    print(force_oauth_js)
    print("="*60)
    
    print("\n📝 디버깅 가이드:")
    print("1. maxflowstudio (http://localhost:3005) 열기")
    print("2. 브라우저 개발자 도구 열기 (F12)")
    print("3. Console 탭으로 이동")
    print("4. 위의 디버깅 코드를 복사-붙여넣기하여 실행")
    print("5. OAuth 로그인 버튼 클릭 후 팝업에서도 동일하게 실행")
    
    print("\n🔧 예상 문제 및 해결책:")
    print("1. oauth_processing이 계속 'true'로 남아있음 → 정리 스크립트 실행")
    print("2. oauth_return URL 파라미터가 계속 남아있음 → URL 정리 스크립트 실행")
    print("3. React 컴포넌트가 무한 리렌더링됨 → 디버깅 카운터로 확인")
    print("4. 팝업에서 PostMessage가 전송되지 않음 → 강제 OAuth 테스트로 확인")

def generate_manual_test_html():
    """수동 테스트용 HTML 파일 생성"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>OAuth 팝업 수동 테스트</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        button { padding: 10px 20px; margin: 10px; font-size: 16px; }
        .debug { background: #f0f0f0; padding: 10px; margin: 10px 0; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>OAuth 팝업 수동 테스트</h1>
    
    <div class="debug">
        <h3>현재 상태</h3>
        <div id="status"></div>
    </div>
    
    <button onclick="checkState()">상태 확인</button>
    <button onclick="clearStorage()">세션스토리지 정리</button>
    <button onclick="testOAuth()">OAuth 테스트</button>
    <button onclick="simulateLogin()">로그인 시뮬레이션</button>
    
    <div id="logs"></div>
    
    <script>
        function log(message, type = 'info') {
            const logs = document.getElementById('logs');
            const div = document.createElement('div');
            div.className = type;
            div.textContent = new Date().toLocaleTimeString() + ': ' + message;
            logs.appendChild(div);
            console.log(message);
        }
        
        function checkState() {
            const status = document.getElementById('status');
            status.innerHTML = `
                <strong>세션스토리지:</strong><br>
                oauth_processing: ${sessionStorage.getItem('oauth_processing')}<br>
                oauth_state: ${sessionStorage.getItem('oauth_state')}<br>
                oauth_code_verifier: ${sessionStorage.getItem('oauth_code_verifier')}<br>
                <strong>로컬스토리지:</strong><br>
                access_token: ${localStorage.getItem('access_token') ? '있음' : '없음'}<br>
                <strong>URL:</strong><br>
                ${window.location.href}<br>
                <strong>팝업 모드:</strong><br>
                ${window.opener ? '예' : '아니오'}
            `;
            log('상태 확인 완료');
        }
        
        function clearStorage() {
            sessionStorage.clear();
            localStorage.removeItem('access_token');
            const url = new URL(window.location);
            url.searchParams.delete('oauth_return');
            window.history.replaceState({}, '', url);
            log('스토리지 및 URL 정리 완료', 'success');
            checkState();
        }
        
        function testOAuth() {
            const oauthParams = {
                response_type: 'code',
                client_id: 'maxflowstudio',
                redirect_uri: 'http://localhost:3005/oauth/callback',
                scope: 'read:profile read:groups manage:workflows',
                state: 'manual_test_' + Date.now(),
                code_challenge: 'test_challenge_' + Date.now(),
                code_challenge_method: 'S256',
                display: 'popup'
            };
            
            const authUrl = new URL('http://localhost:8000/api/oauth/authorize');
            Object.keys(oauthParams).forEach(key => {
                authUrl.searchParams.append(key, oauthParams[key]);
            });
            
            log('OAuth 테스트 팝업 열기: ' + authUrl.toString());
            
            const popup = window.open(authUrl.toString(), 'oauth_test', 'width=500,height=600');
            
            if (popup) {
                log('팝업 열림 성공', 'success');
                
                // PostMessage 리스너
                window.addEventListener('message', (event) => {
                    log('PostMessage 수신: ' + JSON.stringify(event.data), 'success');
                });
                
                // 팝업 닫힘 감지
                const checkClosed = setInterval(() => {
                    if (popup.closed) {
                        clearInterval(checkClosed);
                        log('팝업 닫힘 감지', 'error');
                    }
                }, 1000);
            } else {
                log('팝업 차단됨', 'error');
            }
        }
        
        function simulateLogin() {
            // 가짜 토큰 설정
            const fakeToken = 'fake_token_' + Date.now();
            localStorage.setItem('access_token', fakeToken);
            log('가짜 로그인 토큰 설정: ' + fakeToken, 'success');
            checkState();
        }
        
        // 초기 상태 확인
        window.onload = checkState;
    </script>
</body>
</html>
"""
    
    with open('/home/lee/proejct/maxplatform/oauth_debug_test.html', 'w') as f:
        f.write(html_content)
    
    print(f"\n📄 수동 테스트 HTML 파일 생성: oauth_debug_test.html")
    print("브라우저에서 file:///home/lee/proejct/maxplatform/oauth_debug_test.html 열어서 테스트하세요")

if __name__ == "__main__":
    check_browser_console()
    generate_manual_test_html()