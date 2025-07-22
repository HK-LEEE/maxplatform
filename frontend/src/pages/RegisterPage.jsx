import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Users } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import GroupSelectionModal from '../components/GroupSelectionModal'
import config from '../config/environment'

const RegisterPage = () => {
  const [formData, setFormData] = useState({
    real_name: '',
    display_name: '',
    email: '',
    phone_number: '',
    password: '',
    confirmPassword: '',
    department: '',
    position: '',
    group_id: ''
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [showGroupModal, setShowGroupModal] = useState(false)
  
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleGroupSelect = (group) => {
    if (group) {
      setSelectedGroup(group)
      setFormData({
        ...formData,
        group_id: group.id
      })
    } else {
      setSelectedGroup(null)
      setFormData({
        ...formData,
        group_id: ''
      })
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    // 유효성 검사
    if (formData.password !== formData.confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.')
      setIsLoading(false)
      return
    }

    if (formData.password.length < 6) {
      setError('비밀번호는 최소 6자 이상이어야 합니다.')
      setIsLoading(false)
      return
    }

    if (!formData.real_name.trim()) {
      setError('실명을 입력해주세요.')
      setIsLoading(false)
      return
    }

    if (!formData.group_id) {
      setError('그룹을 선택해주세요.')
      setIsLoading(false)
      return
    }

    try {
      const submitData = {
        real_name: formData.real_name,
        display_name: formData.display_name || formData.real_name,
        email: formData.email,
        phone_number: formData.phone_number,
        password: formData.password,
        department: formData.department,
        position: formData.position,
        group_id: formData.group_id || null
      }

      const response = await fetch(`${config.apiBaseUrl}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(submitData),
      })

      if (response.ok) {
        const data = await response.json()
        alert('회원가입이 완료되었습니다! 로그인해주세요.')
        navigate('/login')
      } else {
        const errorData = await response.json()
        setError(errorData.detail || '회원가입에 실패했습니다.')
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
          <div className="max-w-lg w-full">
            {/* 회원가입 카드 */}
            <div className="bg-white rounded-2xl shadow-lg border border-neutral-100 p-8">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">
                  회원가입
                </h2>
                <p className="text-neutral-600">
                  MAX Platform에 가입하여 시작하세요
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
                    {error}
                  </div>
                )}

                {/* 기본 정보 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="real_name" className="block text-sm font-medium text-neutral-700 mb-2">
                      실명 *
                    </label>
                    <input
                      id="real_name"
                      name="real_name"
                      type="text"
                      required
                      className="w-full px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-neutral-900"
                      placeholder="실명을 입력하세요"
                      value={formData.real_name}
                      onChange={handleChange}
                    />
                  </div>

                  <div>
                    <label htmlFor="display_name" className="block text-sm font-medium text-neutral-700 mb-2">
                      표시명
                    </label>
                    <input
                      id="display_name"
                      name="display_name"
                      type="text"
                      className="w-full px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-neutral-900"
                      placeholder="표시명 (선택)"
                      value={formData.display_name}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-neutral-700 mb-2">
                    이메일 *
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    className="w-full px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-neutral-900"
                    placeholder="이메일을 입력하세요"
                    value={formData.email}
                    onChange={handleChange}
                  />
                </div>

                <div>
                  <label htmlFor="phone_number" className="block text-sm font-medium text-neutral-700 mb-2">
                    휴대폰 번호 *
                  </label>
                  <input
                    id="phone_number"
                    name="phone_number"
                    type="tel"
                    required
                    className="w-full px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-neutral-900"
                    placeholder="010-1234-5678"
                    value={formData.phone_number}
                    onChange={handleChange}
                  />
                </div>

                {/* 그룹 선택 */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    그룹 선택 *
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowGroupModal(true)}
                    className="w-full px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-left flex items-center justify-between hover:bg-neutral-50"
                  >
                    <div className="flex items-center space-x-2">
                      <Users className="w-4 h-4 text-neutral-400" />
                      <span className={selectedGroup ? "text-neutral-900" : "text-neutral-500"}>
                        {selectedGroup ? selectedGroup.name : "그룹을 선택하세요"}
                      </span>
                    </div>
                    <span className="text-neutral-400 text-sm">클릭하여 선택</span>
                  </button>
                  {selectedGroup && selectedGroup.description && (
                    <p className="text-sm text-neutral-600 mt-1">{selectedGroup.description}</p>
                  )}
                </div>

                {/* 회사 정보 (선택) */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="department" className="block text-sm font-medium text-neutral-700 mb-2">
                      부서
                    </label>
                    <input
                      id="department"
                      name="department"
                      type="text"
                      className="w-full px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-neutral-900"
                      placeholder="부서 (선택)"
                      value={formData.department}
                      onChange={handleChange}
                    />
                  </div>

                  <div>
                    <label htmlFor="position" className="block text-sm font-medium text-neutral-700 mb-2">
                      직책
                    </label>
                    <input
                      id="position"
                      name="position"
                      type="text"
                      className="w-full px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-neutral-900"
                      placeholder="직책 (선택)"
                      value={formData.position}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                {/* 비밀번호 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="password" className="block text-sm font-medium text-neutral-700 mb-2">
                      비밀번호 *
                    </label>
                    <input
                      id="password"
                      name="password"
                      type="password"
                      required
                      className="w-full px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-neutral-900"
                      placeholder="비밀번호"
                      value={formData.password}
                      onChange={handleChange}
                    />
                  </div>

                  <div>
                    <label htmlFor="confirmPassword" className="block text-sm font-medium text-neutral-700 mb-2">
                      비밀번호 확인 *
                    </label>
                    <input
                      id="confirmPassword"
                      name="confirmPassword"
                      type="password"
                      required
                      className="w-full px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 text-neutral-900"
                      placeholder="비밀번호 확인"
                      value={formData.confirmPassword}
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
                      가입 중...
                    </div>
                  ) : (
                    '회원가입'
                  )}
                </button>

                <div className="text-center pt-4">
                  <Link 
                    to="/login" 
                    className="text-neutral-600 hover:text-neutral-900 font-medium transition-colors duration-200"
                  >
                    이미 계정이 있으신가요? 로그인
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
                  <h3 className="font-medium text-neutral-900 mb-1">가입 안내</h3>
                  <p className="text-sm text-neutral-600">
                    * 표시는 필수 입력 항목입니다. 그룹은 필수 선택이며, 부서와 직책은 선택사항으로 나중에 수정할 수 있습니다.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 그룹 선택 모달 */}
      <GroupSelectionModal
        isOpen={showGroupModal}
        onClose={() => setShowGroupModal(false)}
        onSelect={handleGroupSelect}
      />
    </div>
  )
}

export default RegisterPage