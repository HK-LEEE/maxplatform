#!/usr/bin/env python3
"""
OAuth 팝업 로그인 Playwright 테스트
"""

import asyncio
from playwright.async_api import async_playwright
import time

async def test_oauth_popup_login():
    async with async_playwright() as p:
        # 브라우저 실행 (디버깅을 위해 headless=False)
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-web-security', '--disable-features=VizDisplayCompositor']
        )
        
        try:
            # 새 브라우저 컨텍스트 생성
            context = await browser.new_context()
            
            # maxflowstudio 페이지 열기
            page = await context.new_page()
            
            print("🌐 maxflowstudio 페이지로 이동 중...")
            await page.goto("http://localhost:3005")
            
            # 페이지 로드 대기
            await page.wait_for_load_state("networkidle")
            
            print("🔍 OAuth 로그인 버튼 찾는 중...")
            
            # OAuth 로그인 버튼을 찾기 위해 여러 가능한 셀렉터 시도
            possible_selectors = [
                'button:has-text("MAX Platform으로 로그인")',
                'button:has-text("OAuth")',
                'button:has-text("로그인")',
                '[data-testid="oauth-login"]',
                '.oauth-login-button',
                'button[onclick*="oauth"]'
            ]
            
            oauth_button = None
            for selector in possible_selectors:
                try:
                    oauth_button = await page.wait_for_selector(selector, timeout=5000)
                    if oauth_button:
                        print(f"✅ OAuth 버튼 발견: {selector}")
                        break
                except:
                    continue
            
            if not oauth_button:
                print("❌ OAuth 로그인 버튼을 찾을 수 없습니다.")
                print("🔍 페이지의 모든 버튼들을 확인해보겠습니다...")
                
                buttons = await page.query_selector_all('button')
                for i, button in enumerate(buttons):
                    text = await button.inner_text()
                    print(f"버튼 {i+1}: '{text}'")
                
                return
            
            print("🖱️ OAuth 로그인 버튼 클릭...")
            
            # 팝업 이벤트 리스너 설정
            popup_promise = context.wait_for_event("page")
            
            # OAuth 버튼 클릭
            await oauth_button.click()
            
            print("⏳ 팝업 창 대기 중...")
            
            # 팝업 창 대기 (최대 10초)
            try:
                popup = await asyncio.wait_for(popup_promise, timeout=10.0)
                print(f"🎉 팝업 창 열림: {popup.url}")
            except asyncio.TimeoutError:
                print("❌ 팝업 창이 열리지 않았습니다.")
                return
            
            # 팝업 페이지 로드 대기
            await popup.wait_for_load_state("networkidle")
            
            print("🔍 팝업 페이지 분석 중...")
            print(f"현재 팝업 URL: {popup.url}")
            
            # 현재 페이지가 로그인 페이지인지 확인
            is_login_page = "login" in popup.url or await popup.query_selector('input[type="email"]') is not None
            
            if is_login_page:
                print("📝 로그인 페이지 감지됨. 로그인 진행...")
                
                # 이메일 입력
                email_input = await popup.wait_for_selector('input[type="email"], input[name="email"]', timeout=5000)
                await email_input.fill("admin@test.com")
                print("✅ 이메일 입력 완료")
                
                # 비밀번호 입력
                password_input = await popup.wait_for_selector('input[type="password"], input[name="password"]', timeout=5000)
                await password_input.fill("admin123")
                print("✅ 비밀번호 입력 완료")
                
                # 로그인 버튼 클릭
                login_button = await popup.wait_for_selector('button[type="submit"], button:has-text("로그인")', timeout=5000)
                await login_button.click()
                print("🔐 로그인 버튼 클릭")
                
                # 로그인 후 페이지 변화 대기
                await popup.wait_for_load_state("networkidle")
                
                print(f"🔄 로그인 후 URL: {popup.url}")
            
            # OAuth 처리 모니터링
            print("⏳ OAuth 처리 모니터링 중...")
            
            # 콘솔 로그 수집
            def handle_console(msg):
                if any(keyword in msg.text for keyword in ['OAuth', '🔄', '🚀', '🎉', '❌']):
                    print(f"📄 팝업 콘솔: {msg.text}")
            
            popup.on("console", handle_console)
            
            # PostMessage 또는 팝업 닫힘 대기
            start_time = time.time()
            popup_closed = False
            oauth_success = False
            
            while time.time() - start_time < 30:  # 최대 30초 대기
                if popup.is_closed():
                    popup_closed = True
                    print("🚪 팝업 창이 닫혔습니다.")
                    break
                
                # 무한새로고침 감지
                current_url = popup.url
                await asyncio.sleep(1)
                new_url = popup.url
                
                if current_url != new_url:
                    print(f"🔄 URL 변경 감지: {current_url} → {new_url}")
                    
                    # 같은 URL로 계속 변경되면 무한루프
                    if "oauth_return" in new_url and current_url == new_url:
                        print("❌ 무한새로고침 감지됨!")
                        break
                
                await asyncio.sleep(0.5)
            
            if popup_closed:
                print("✅ 팝업이 정상적으로 닫혔습니다.")
                
                # 메인 페이지에서 로그인 상태 확인
                await page.wait_for_load_state("networkidle")
                
                # 로그인 성공 여부 확인
                try:
                    await page.wait_for_selector('[data-testid="user-profile"], .user-info, button:has-text("로그아웃")', timeout=5000)
                    print("🎉 OAuth 로그인 성공!")
                    oauth_success = True
                except:
                    print("❌ 로그인 상태 확인 실패")
            else:
                print("❌ 팝업이 정상적으로 닫히지 않았습니다.")
            
            # 최종 결과 보고
            print("\n" + "="*50)
            print("📊 테스트 결과 요약")
            print("="*50)
            print(f"팝업 열림: {'✅' if 'popup' in locals() else '❌'}")
            print(f"로그인 페이지 접근: {'✅' if is_login_page else '❌'}")
            print(f"팝업 정상 닫힘: {'✅' if popup_closed else '❌'}")
            print(f"OAuth 로그인 성공: {'✅' if oauth_success else '❌'}")
            
            # 스크린샷 저장
            await page.screenshot(path="/home/lee/proejct/maxplatform/test_result.png")
            print("📸 스크린샷 저장: test_result.png")
            
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

if __name__ == "__main__":
    print("🚀 OAuth 팝업 로그인 테스트 시작...")
    asyncio.run(test_oauth_popup_login())