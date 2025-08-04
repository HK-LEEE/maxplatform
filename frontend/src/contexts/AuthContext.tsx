import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User, AuthContextType } from '../types'
import { authAPI } from '../services/api'
import { startTokenRefreshTimer } from '../utils/tokenManager'

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

  useEffect(() => {
    const initAuth = async () => {
      console.log('🔐 AuthContext initAuth 시작:', { hasToken: !!token });
      
      try {
        // SSO 토큰 확인 (URL 파라미터에서)
        const urlParams = new URLSearchParams(window.location.search);
        const ssoToken = urlParams.get('sso_token');
        
        let currentToken = token;
        
        if (ssoToken && !token) {
          console.log('🔄 SSO 토큰 감지:', ssoToken);
          // SSO 토큰을 localStorage와 쿠키에 저장하고 URL에서 제거
          localStorage.setItem('token', ssoToken);
          document.cookie = `access_token=${ssoToken}; path=/; max-age=3600; SameSite=Lax`
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
            document.cookie = `access_token=${currentToken}; path=/; max-age=3600; SameSite=Lax`
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
        document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
        
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
      document.cookie = `access_token=${access_token}; path=/; max-age=3600; SameSite=Lax`
      
      setToken(access_token)
      
      const userData = await authAPI.getMe()
      setUser(userData)
      setIsAuthenticated(true)
      
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
      // 1. 로컬 토큰 정리
      const currentToken = localStorage.getItem('token')
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
      
      // 2. 상태 업데이트
      setToken(null)
      setUser(null)
      setIsAuthenticated(false)
      
      // 3. Single Logout 수행 (OIDC End Session)
      if (forceSingleLogout && currentToken) {
        // OIDC End Session Endpoint로 리다이렉트
        const logoutUrl = new URL(`${window.location.origin}/api/oauth/logout`)
        logoutUrl.searchParams.append('post_logout_redirect_uri', `${window.location.origin}/login?logout=success`)
        
        // id_token_hint 추가 (있는 경우)
        const idToken = localStorage.getItem('id_token')
        if (idToken) {
          logoutUrl.searchParams.append('id_token_hint', idToken)
          localStorage.removeItem('id_token')
        }
        
        // SSO Provider 로그아웃 수행
        window.location.href = logoutUrl.toString()
      } else {
        // 로컬 로그아웃만 수행 (fallback)
        window.location.href = '/login?logout=local'
      }
    } catch (error) {
      console.error('Logout error:', error)
      // 오류 시에도 로그인 페이지로 이동
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