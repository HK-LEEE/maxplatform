import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mail, Phone } from 'lucide-react'

const ResetPasswordPage = () => {
  const [formData, setFormData] = useState({
    email: '',
    phone_last_digits: ''
  })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  const navigate = useNavigate()

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8000/api/auth/reset-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      })

      const data = await response.json()

      if (response.ok) {
        setMessage(`${data.message} 임시 비밀번호: ${data.temp_password}`)
        setTimeout(() => {
          navigate('/login')
        }, 5000)
      } else {
        setError(data.detail || '비밀번호 초기화에 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <div className="min-h-screen flex flex-col">
        {/* 헤더 */}
        <header className="bg-white border-b border-neutral-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <Link to="/login" className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-neutral-900 rounded-xl flex items-center justify-center">
                  <span className="text-white text-xl font-bold">M</span>
                </div>
                <h1 className="text-2xl font-bold text-neutral-900">
                  MAX Platform
                </h1>
              </Link>
            </div>
          </div>
        </header>

        {/* 메인 콘텐츠 */}
        <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 py-12">
          <div className="max-w-md w-full">
            {/* 비밀번호 초기화 카드 */}
            <div className="bg-white rounded-2xl shadow-lg border border-neutral-100 p-8">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">
                  비밀번호 초기화
                </h2>
                <p className="text-neutral-600">
                  등록된 이메일과 전화번호 뒷자리로 비밀번호를 초기화하세요
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
                    {error}
                  </div>
                )}

                {message && (
                  <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-xl text-sm">
                    {message}
                  </div>
                )}

                <div className="space-y-2">
                  <label htmlFor="email" className="block text-sm font-medium text-neutral-700">
                    이메일
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Mail className="h-5 w-5 text-neutral-400" />
                    </div>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      required
                      className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-neutral-900"
                      placeholder="등록된 이메일을 입력하세요"
                      value={formData.email}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="phone_last_digits" className="block text-sm font-medium text-neutral-700">
                    전화번호 뒷자리 4자리
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Phone className="h-5 w-5 text-neutral-400" />
                    </div>
                    <input
                      id="phone_last_digits"
                      name="phone_last_digits"
                      type="text"
                      maxLength="4"
                      pattern="[0-9]{4}"
                      required
                      className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-neutral-900"
                      placeholder="전화번호 뒷자리 4자리"
                      value={formData.phone_last_digits}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-neutral-900 text-white py-3 px-4 rounded-xl font-medium hover:bg-neutral-800 focus:ring-2 focus:ring-neutral-900 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                  {isLoading ? (
                    <div className="flex items-center justify-center">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                      초기화 중...
                    </div>
                  ) : (
                    '비밀번호 초기화'
                  )}
                </button>

                <div className="text-center pt-4">
                  <Link 
                    to="/login" 
                    className="text-neutral-600 hover:text-neutral-900 font-medium transition-colors duration-200"
                  >
                    로그인으로 돌아가기
                  </Link>
                </div>
              </form>
            </div>

            {/* 안내 메시지 */}
            <div className="mt-6 bg-neutral-50 rounded-xl p-4 border border-neutral-200">
              <div className="flex items-start space-x-3">
                <div className="w-5 h-5 bg-neutral-300 rounded-full flex items-center justify-center mt-0.5">
                  <span className="text-neutral-600 text-xs">i</span>
                </div>
                <div>
                  <h3 className="font-medium text-neutral-900 mb-1">안내사항</h3>
                  <p className="text-sm text-neutral-600">
                    등록 시 사용한 이메일과 전화번호 뒷자리 4자리를 정확히 입력해주세요. 
                    임시 비밀번호가 발급되면 로그인 후 비밀번호를 변경하세요.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ResetPasswordPage 