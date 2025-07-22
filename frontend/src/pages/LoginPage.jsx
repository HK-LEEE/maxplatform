import React, { useState, useEffect, useRef } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, EyeOff, Mail, Lock, Sparkles, ArrowRight } from 'lucide-react'
import { authApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import config from '../config/environment'

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
  
  // 무한루프 방지를 위한 처리 완료 플래그 (useRef로 리렌더링 방지)
  const oauthProcessedRef = useRef(false)
  const [, setSearchParams] = useSearchParams()

  // 이미 로그인된 경우 리다이렉트 처리
  useEffect(() => {
    // 이미 처리된 경우 무시
    if (oauthProcessedRef.current) {
      return
    }

    if (!authLoading && isAuthenticated) {
      if (oauthReturn) {
        // OAuth 플로우로 복귀
        try {
          const oauthParams = JSON.parse(decodeURIComponent(oauthReturn))
          
          // 팝업 모드 체크 - window.opener가 있으면 팝업에서 실행 중
          const isInPopup = window.opener !== null
          
          console.log('🔄 OAuth return processing:', { isInPopup, oauthParams })
          
          // 처리 완료 플래그 설정 (즉시)
          oauthProcessedRef.current = true
          
          // URL에서 oauth_return 파라미터 제거
          const newSearchParams = new URLSearchParams(window.location.search)
          newSearchParams.delete('oauth_return')
          setSearchParams(newSearchParams, { replace: true })
          
          if (isInPopup) {
            // 팝업 모드: 표준 OAuth 리다이렉트 방식
            const authUrl = new URL(`${config.apiBaseUrl}/api/oauth/authorize`)
            Object.keys(oauthParams).forEach(key => {
              if (oauthParams[key] !== null) {
                authUrl.searchParams.append(key, oauthParams[key])
              }
            })
            
            console.log('🚀 Popup redirecting to OAuth URL:', authUrl.toString())
            
            // 세션 스토리지에 처리 상태 저장
            sessionStorage.setItem('oauth_processing', 'true')
            
            // 표준 OAuth 리다이렉트 방식 (PostMessage HTML이 자동 처리됨)
            window.location.href = authUrl.toString()
            return
          } else {
            // 일반 창 모드: 기존 로직 유지
            const authUrl = new URL(`${config.apiBaseUrl}/api/oauth/authorize`)
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
      // AuthContext가 상태를 관리하므로 직접 navigate 호출 불필요
      // useEffect에서 isAuthenticated 변경 시 자동 리다이렉트됨
    } catch (error) {
      console.error('Login error:', error)
      const errorMessage = error.response?.data?.detail || error.message || '로그인에 실패했습니다.'
      setError(errorMessage)
    } finally {
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