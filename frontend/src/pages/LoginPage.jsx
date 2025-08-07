import React, { useState, useEffect, useRef } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, EyeOff, Mail, Lock, Sparkles, ArrowRight } from 'lucide-react'
import { authApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import config, { utils } from '../config/environment'
import toast from 'react-hot-toast'

const LoginPage = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, isAuthenticated, isLoading: authLoading } = useAuth()

  // OAuth 리턴 파라미터 확인
  const oauthReturn = searchParams.get('oauth_return')
  const forceLogin = searchParams.get('force_login') === 'true'
  
  // 무한루프 방지를 위한 처리 완료 플래그 (useRef로 리렌더링 방지)
  const oauthProcessedRef = useRef(false)
  const [, setSearchParams] = useSearchParams()

  // 이미 로그인된 경우 리다이렉트 처리
  useEffect(() => {
    console.log('🔍 OAuth useEffect triggered:', {
      isAuthenticated,
      authLoading,
      oauthReturn: !!oauthReturn,
      forceLogin,
      oauthProcessedRef: oauthProcessedRef.current
    });

    // 이미 처리된 경우 무시
    if (oauthProcessedRef.current) {
      console.log('⏭️ OAuth already processed, skipping...');
      return
    }

    // force_login=true인 경우에도 새로 로그인한 후에는 OAuth 플로우를 계속해야 함
    if (forceLogin && !isAuthenticated) {
      console.log('🔒 force_login detected - showing login form')
      // 로그인 폼을 보여주기 위해 여기서는 return
      return
    }

    if (!authLoading && isAuthenticated) {
      console.log('✅ User authenticated, checking OAuth return...');
      if (oauthReturn) {
        // OAuth 플로우로 복귀
        try {
          const oauthParams = JSON.parse(decodeURIComponent(oauthReturn))
          
          // 팝업 모드 체크 - window.opener가 있으면 팝업에서 실행 중
          const isInPopup = window.opener !== null
          
          console.log('🔄 OAuth return processing:', { isInPopup, oauthParams })
          console.log(JSON.stringify(oauthParams))
          // 처리 완료 플래그 설정 (즉시)
          oauthProcessedRef.current = true
          
          // URL에서 oauth_return 파라미터 제거
          const newSearchParams = new URLSearchParams(window.location.search)
          newSearchParams.delete('oauth_return')
          setSearchParams(newSearchParams, { replace: true })
          
          if (isInPopup) {
            // 팝업 모드: 이미 인증된 경우에도 OAuth authorize 엔드포인트로 리다이렉트
            // OAuth 서버가 authorization code를 생성하여 callback으로 전달함
            console.log('🚀 User already authenticated in popup, redirecting to OAuth authorize...')
            
            // OAuth authorize URL 생성
            const authUrl = new URL(`/api/oauth/authorize`, config.apiBaseUrl)
            Object.keys(oauthParams).forEach(key => {
              if (oauthParams[key] !== null) {
                authUrl.searchParams.append(key, oauthParams[key])
              }
            })
            
            console.log('🔄 Popup redirecting to OAuth authorize for code generation:', authUrl.toString())
            
            // OAuth authorize 엔드포인트로 리다이렉트
            // 쿠키 전달을 위해 Form Submit 사용 (GET 메서드는 URL에 파라미터 포함됨)
            const form = document.createElement('form')
            form.method = 'GET'
            form.action = authUrl.href.split('?')[0]  // 베이스 URL만 사용
            
            // URL 파라미터를 hidden input으로 변환
            for (const [key, value] of authUrl.searchParams) {
              const input = document.createElement('input')
              input.type = 'hidden'
              input.name = key
              input.value = value
              form.appendChild(input)
            }
            
            document.body.appendChild(form)
            form.submit()
            return
          } else {
            // 일반 창 모드: 기존 로직 유지
            const authUrl = new URL(`/api/oauth/authorize`, config.apiBaseUrl)
            Object.keys(oauthParams).forEach(key => {
              if (oauthParams[key] !== null) {
                authUrl.searchParams.append(key, oauthParams[key])
              }
            })
            console.log('🚀 Regular window redirecting to OAuth URL:', authUrl.toString())
            window.location.href = authUrl.toString()
            return
          }
        } catch (error) {
          console.error('OAuth return parameter parsing error:', error)
          oauthProcessedRef.current = true // 에러 시에도 플래그 설정
          
          // URL 정리
          const newSearchParams = new URLSearchParams(window.location.search)
          newSearchParams.delete('oauth_return')
          setSearchParams(newSearchParams, { replace: true })
        }
      }
      // 일반 로그인인 경우 대시보드로
      if (!oauthReturn) {
        navigate('/dashboard', { replace: true })
      }
    }
  }, [isAuthenticated, authLoading, navigate, oauthReturn, setSearchParams])

  // 컴포넌트 마운트 시 세션스토리지 체크
  useEffect(() => {
    const isProcessing = sessionStorage.getItem('oauth_processing')
    if (isProcessing) {
      console.log('🔄 OAuth processing in progress, preventing re-execution')
      oauthProcessedRef.current = true
      sessionStorage.removeItem('oauth_processing')
    }
  }, [])

  // 로그아웃 상태 메시지 처리
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const logoutStatus = params.get('logout')
    
    if (logoutStatus === 'success') {
      toast.success('성공적으로 로그아웃되었습니다.')
    } else if (logoutStatus === 'error') {
      toast.error('로그아웃 중 오류가 발생했습니다.')
    } else if (logoutStatus === 'local') {
      toast.info('로컬 세션에서 로그아웃되었습니다.')
    }
    
    // URL에서 logout 파라미터 제거
    if (logoutStatus) {
      params.delete('logout')
      const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '')
      window.history.replaceState({}, '', newUrl)
    }
  }, [])

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
    if (error) setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      await login(formData.email, formData.password)
      
      // 로그인 성공 후 OAuth return 처리
      if (oauthReturn) {
        console.log('🚀 Login successful, processing OAuth return...')
        console.log('🚀 API BASE URL: ',config.apiBaseUrl)
        
        // 팝업 모드 체크 - window.opener가 있으면 팝업에서 실행 중
        const isInPopup = window.opener !== null
        console.log('🪟 Popup detection after login:', { isInPopup, hasOpener: !!window.opener })
        
        if (isInPopup) {
          // 팝업 모드: 부모 창에 로그인 성공과 OAuth 계속 진행 메시지 전송
          console.log('🔄 Popup mode - notifying parent of login success and continuing OAuth...')
          
          try {
            const oauthParams = JSON.parse(decodeURIComponent(oauthReturn))
            
            // 로그인 성공 후 OAuth authorize로 리다이렉트하여 authorization code 받기
            console.log('🔄 Login successful, redirecting to OAuth authorize for code generation...')
            
            // OAuth authorize URL 생성 (prompt=login 제거)
            delete oauthParams.prompt
            delete oauthParams.max_age
            
            const authUrl = new URL(`/api/oauth/authorize`, config.apiBaseUrl)
            Object.keys(oauthParams).forEach(key => {
              if (oauthParams[key] !== null) {
                authUrl.searchParams.append(key, oauthParams[key])
              }
            })
            
            // OAuth authorize 엔드포인트로 리다이렉트
            // 쿠키 전달을 위해 Form Submit 사용
            const form = document.createElement('form')
            form.method = 'GET'
            form.action = authUrl.href.split('?')[0]  // 베이스 URL만 사용
            
            // URL 파라미터를 hidden input으로 변환
            for (const [key, value] of authUrl.searchParams) {
              const input = document.createElement('input')
              input.type = 'hidden'
              input.name = key
              input.value = value
              form.appendChild(input)
            }
            
            document.body.appendChild(form)
            form.submit()
            return
          } catch (error) {
            console.error('OAuth popup message sending error:', error)
            // 에러 시 fallback으로 일반 redirect 처리
          }
        }
        
        // 일반 창 모드 또는 팝업 메시지 전송 실패시: OAuth로 리다이렉트
        try {
          const oauthParams = JSON.parse(decodeURIComponent(oauthReturn))
          
          // prompt=login 제거 (무한 루프 방지)
          delete oauthParams.prompt
          delete oauthParams.max_age
          
          const authUrl = new URL(`/api/oauth/authorize`, config.apiBaseUrl)
          
          Object.keys(oauthParams).forEach(key => {
            if (oauthParams[key] !== null && oauthParams[key] !== undefined) {
              authUrl.searchParams.append(key, oauthParams[key])
            }
          })
          
          console.log('🔄 Redirecting to OAuth authorize (without prompt=login):', authUrl.toString())
          
          // 즉시 리다이렉트
          window.location.href = authUrl.toString()
          return
        } catch (error) {
          console.error('OAuth return processing error:', error)
        }
      }
    } catch (error) {
      console.error('Login error:', error)
      const errorMessage = error.response?.data?.detail || error.message || '로그인에 실패했습니다.'
      setError(errorMessage)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="w-full max-w-md px-6">
        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-lg border border-neutral-100 p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-neutral-900 rounded-2xl flex items-center justify-center">
                <span className="text-white font-bold text-2xl">M</span>
              </div>
            </div>
            
            <h1 className="text-3xl font-bold text-neutral-900 mb-2">
              MAX Platform
            </h1>
            <p className="text-neutral-600">
              Manufacturing AI & DX Platform
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {forceLogin && (
              <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-xl text-sm animate-slide-up">
                다른 계정으로 로그인하려면 이메일과 비밀번호를 입력하세요.
              </div>
            )}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm animate-slide-up">
                {error}
              </div>
            )}

            {/* Email Field */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700 block">
                이메일
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-neutral-400" />
                </div>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200"
                  placeholder="이메일을 입력하세요"
                  required
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700 block">
                비밀번호
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-neutral-400" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  className="w-full pl-10 pr-12 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200"
                  placeholder="비밀번호를 입력하세요"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-neutral-400 hover:text-neutral-600 transition-colors"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-neutral-900 text-white py-3 px-4 rounded-xl font-medium hover:bg-neutral-800 focus:ring-2 focus:ring-neutral-900 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 group"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
              ) : (
                <>
                  <span>로그인</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-8 text-center space-y-4">
            <div className="flex items-center justify-center space-x-4 text-sm">
              <Link 
                to="/register" 
                className="text-neutral-600 hover:text-neutral-900 transition-colors"
              >
                회원가입
              </Link>
              <span className="text-neutral-300">•</span>
              <Link 
                to="/reset-password" 
                className="text-neutral-600 hover:text-neutral-900 transition-colors"
              >
                비밀번호 찾기
              </Link>
            </div>
            <p className="text-xs text-neutral-500">
              계정이 없으신가요? 회원가입을 통해 가입하세요
            </p>
          </div>
        </div>

        {/* Copyright */}
        <div className="text-center mt-8">
          <p className="text-neutral-400 text-sm">
            © 2025 MAX Platform. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  )
}

export default LoginPage 