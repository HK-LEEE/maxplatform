import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User, AuthContextType } from '../types'
import { authAPI } from '../services/api'
import { startTokenRefreshTimer } from '../utils/tokenManager'
import { crossDomainLogout } from '../utils/crossDomainLogout'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  
  // SSO: MAX Lab에 로그인 세션 동기화
  const syncLoginToMaxLab = (accessToken: string, userData: User) => {
    try {
      console.log('🔄 SSO: Syncing login to MAX Lab...')
      
      // MAX Lab URL 설정 (개발/프로덕션 환경에 따라 다르게 설정)
      const maxLabUrl = process.env.NODE_ENV === 'production' 
        ? 'https://maxlab.dwchem.co.kr'
        : 'http://localhost:3010'
      
      // iframe을 통해 MAX Lab에 토큰 전달
      const iframe = document.createElement('iframe')
      iframe.style.display = 'none'
      iframe.src = `${maxLabUrl}/oauth/sync?token=${encodeURIComponent(accessToken)}&user=${encodeURIComponent(JSON.stringify(userData))}`
      
      // iframe 로드 후 자동 제거
      iframe.onload = () => {
        console.log('✅ SSO: MAX Lab sync iframe loaded')
        setTimeout(() => {
          document.body.removeChild(iframe)
        }, 3000)
      }
      
      iframe.onerror = () => {
        console.warn('⚠️ SSO: Failed to load MAX Lab sync iframe')
        document.body.removeChild(iframe)
      }
      
      document.body.appendChild(iframe)
    } catch (error) {
      console.error('❌ SSO: Failed to sync with MAX Lab:', error)
    }
  }
  

  useEffect(() => {
    const initAuth = async () => {
      console.log('🔐 AuthContext initAuth 시작:', { hasToken: !!token });
      
      try {
        // SSO 토큰 확인 (URL 파라미터에서)
        console.log('📡 TRY start');
        const urlParams = new URLSearchParams(window.location.search);
        const ssoToken = urlParams.get('sso_token');
        
        let currentToken = token;
        
        if (ssoToken && !token) {
          console.log('🔄 SSO 토큰 감지:', ssoToken);
          // SSO 토큰을 localStorage와 쿠키에 저장하고 URL에서 제거
          localStorage.setItem('token', ssoToken);
          document.cookie = `access_token=${ssoToken}; path=/; max-age=3600; SameSite=None; Secure; domain=.dwchem.co.kr`
          setToken(ssoToken);
          currentToken = ssoToken;
          
          // URL에서 sso_token 파라미터 제거
          urlParams.delete('sso_token');
          const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
          window.history.replaceState({}, '', newUrl);
        }
        
        if (currentToken) {
          console.log('📡 사용자 정보 로드 시작');
          
          // OAuth 팝업 지원을 위해 기존 토큰도 쿠키에 저장 (한 번만)
          if (!document.cookie.includes('access_token=')) {
            document.cookie = `access_token=${currentToken}; path=/; max-age=3600; SameSite=None; Secure; domain=.dwchem.co.kr`
          }
          
          const userData = await authAPI.getMe();
          console.log('✅ 사용자 정보 로드 성공:', userData);
          
          setUser(userData);
          setIsAuthenticated(true);
          
          // 토큰 갱신 타이머 시작
          startTokenRefreshTimer();
        } else {
          console.log('❌ 토큰이 없어 인증되지 않은 상태');
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error('❌ 인증 초기화 실패:', error);
        
        // 토큰이 유효하지 않은 경우 정리
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        
        // 쿠키에서도 토큰 제거
        document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; domain=.dwchem.co.kr';
        
        setToken(null);
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, [token]);

  const login = async (email: string, password: string) => {
    try {
      const response = await authAPI.login(email, password)
      const { access_token, refresh_token } = response
      
      localStorage.setItem('token', access_token)
      localStorage.setItem('refreshToken', refresh_token)
      
      // OAuth 팝업 지원을 위해 쿠키에도 토큰 저장
      document.cookie = `access_token=${access_token}; path=/; max-age=3600; SameSite=None; Secure; domain=.dwchem.co.kr`
      
      setToken(access_token)
      
      const userData = await authAPI.getMe()
      setUser(userData)
      setIsAuthenticated(true)
      
      // SSO: MAX Lab에 로그인 세션 동기화
      syncLoginToMaxLab(access_token, userData)
      
      // 로그인 후 원래 페이지로 리다이렉트
      const redirectPath = localStorage.getItem('redirectAfterLogin')
      if (redirectPath) {
        localStorage.removeItem('redirectAfterLogin')
        window.location.href = redirectPath
      }
    } catch (error) {
      throw error
    }
  }

  const register = async (username: string, email: string, password: string) => {
    try {
      await authAPI.register(username, email, password)
      // 회원가입 후 자동 로그인
      await login(email, password)
    } catch (error) {
      throw error
    }
  }

  const logout = async (forceSingleLogout: boolean = true) => {
    try {
      console.log('🔄 Starting enhanced logout process...');
      
      // 1. Get current token before clearing
      const currentToken = localStorage.getItem('token')
      const idToken = localStorage.getItem('id_token')
      
      // 2. Update state first
      setToken(null)
      setUser(null)
      setIsAuthenticated(false)
      
      // 3. Execute cross-domain logout with proper synchronization
      console.log('🔄 Executing cross-domain logout synchronization...');
      const logoutResult = await crossDomainLogout.executeLogout({
        timeout: 30000, // 30 seconds timeout
        retryCount: 2   // Retry twice if needed
      });
      
      if (logoutResult.maxLabSynced) {
        console.log('✅ MAX Lab logout synchronized successfully');
      } else {
        console.warn('⚠️ MAX Lab logout sync failed, but continuing...');
      }
      
      // 4. Add a small delay to ensure cross-domain sync completes
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // 5. Perform OIDC End Session if requested
      if (forceSingleLogout && currentToken) {
        console.log('🔄 Performing OIDC end session...');
        
        // Build logout URL
        const logoutUrl = new URL(`${window.location.origin}/api/oauth/logout`)
        logoutUrl.searchParams.append('post_logout_redirect_uri', `${window.location.origin}/login?logout=success`)
        
        // Add id_token_hint if available
        if (idToken) {
          logoutUrl.searchParams.append('id_token_hint', idToken)
        }
        
        // Redirect to logout endpoint
        window.location.href = logoutUrl.toString()
      } else {
        // Local logout only
        console.log('🔄 Local logout only, redirecting to login...');
        window.location.href = '/login?logout=local'
      }
    } catch (error) {
      console.error('❌ Logout error:', error)
      // Even on error, ensure we redirect to login page
      window.location.href = '/login?logout=error'
    }
  }

  const value: AuthContextType = {
    user,
    token,
    login,
    register,
    logout,
    isLoading,
    isAuthenticated,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
} 