import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, useNavigate, useParams } from 'react-router-dom'
import './App.css'
import MainPage from './pages/MotherPage'
import AdminPage from './pages/AdminPage'
import LoginPage from './pages/LoginPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import RegisterPage from './pages/RegisterPage'
import LLMOpsPage from './pages/LLMOpsPage'
import RAGDataSourcePage from './pages/RAGDataSourcePage'
import FlowStudioPage from './pages/FlowStudioPage'
import DashboardLayout from './components/Layout/DashboardLayout'
import NewDashboardPage from './pages/DashboardPage'
import { AuthProvider } from './contexts/AuthContext'

// 타입 정의
interface Workspace {
  id: number;
  name: string;
  description?: string;
  path: string;
  is_active: boolean;
  jupyter_port?: number;
  jupyter_token?: string;
  owner_id: string;
  created_at: string;
}

interface FileItem {
  name: string;
  is_directory: boolean;
  size: number;
  path: string;
}

// 메인 홈페이지 컴포넌트
const HomePage = () => {
  const [activeTab, setActiveTab] = useState('login') // 'login', 'register', 'reset'
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  // 로그인 폼 데이터
  const [loginData, setLoginData] = useState({
    email: '',
    password: ''
  })

  // 회원가입 폼 데이터 (새로운 필드들 추가)
  const [registerData, setRegisterData] = useState({
    real_name: '',        // 실명
    display_name: '',     // 표시명 (선택사항)
    email: '',
    phone_number: '',
    password: '',
    confirmPassword: '',
    department: '',       // 부서 (선택사항)
    position: ''          // 직책 (선택사항)
  })

  // 패스워드 리셋 폼 데이터
  const [resetData, setResetData] = useState({
    email: '',
    phone_last_digits: ''
  })

  // 로그인 처리
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(loginData)
      })

      const data = await response.json()

      if (response.ok) {
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('user', JSON.stringify(data.user))
        setMessage('로그인 성공! Main 페이지로 이동합니다.')
        setTimeout(() => {
          navigate('/main')
        }, 1000)
      } else {
        setError(data.detail || '로그인에 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 회원가입 처리
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    if (registerData.password !== registerData.confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.')
      setIsLoading(false)
      return
    }

    if (!registerData.real_name.trim()) {
      setError('실명을 입력해주세요.')
      setIsLoading(false)
      return
    }

    try {
      // API 호출용 데이터 준비
      const apiData = {
        real_name: registerData.real_name,
        display_name: registerData.display_name || registerData.real_name, // 표시명이 없으면 실명 사용
        email: registerData.email,
        phone_number: registerData.phone_number,
        password: registerData.password,
        department: registerData.department || null,
        position: registerData.position || null
      }

      const response = await fetch('http://localhost:8000/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(apiData)
      })

      const data = await response.json()

      if (response.ok) {
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('user', JSON.stringify(data.user))
        setMessage('회원가입 성공! Main 페이지로 이동합니다.')
        setTimeout(() => {
          navigate('/main')
        }, 1000)
      } else {
        setError(data.detail || '회원가입에 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 패스워드 리셋 처리
  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const response = await fetch('http://localhost:8000/api/auth/reset-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(resetData)
      })

      const data = await response.json()

      if (response.ok) {
        setMessage(`${data.message} 임시 비밀번호: ${data.temp_password}`)
        setActiveTab('login')
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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* 헤더 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900 text-center">
            Jupyter Data Platform
          </h1>
          <p className="text-center text-gray-600 mt-2">
            데이터 분석을 위한 클라우드 플랫폼
          </p>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <div className="max-w-lg mx-auto pt-8 px-4">
        {/* 탭 메뉴 */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="flex">
            <button
              onClick={() => setActiveTab('login')}
              className={`flex-1 py-3 px-4 text-center font-medium ${
                activeTab === 'login'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              로그인
            </button>
            <button
              onClick={() => setActiveTab('register')}
              className={`flex-1 py-3 px-4 text-center font-medium ${
                activeTab === 'register'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              회원가입
            </button>
            <button
              onClick={() => setActiveTab('reset')}
              className={`flex-1 py-3 px-4 text-center font-medium ${
                activeTab === 'reset'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              비밀번호 찾기
            </button>
          </div>

          {/* 메시지 표시 */}
          {message && (
            <div className="p-4 bg-green-100 border-l-4 border-green-500 text-green-700">
              {message}
            </div>
          )}
          {error && (
            <div className="p-4 bg-red-100 border-l-4 border-red-500 text-red-700">
              {error}
            </div>
          )}

          <div className="p-6">
            {/* 로그인 폼 */}
            {activeTab === 'login' && (
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    이메일
                  </label>
                  <input
                    type="email"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={loginData.email}
                    onChange={(e) => setLoginData({...loginData, email: e.target.value})}
                    placeholder="이메일을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    비밀번호
                  </label>
                  <input
                    type="password"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={loginData.password}
                    onChange={(e) => setLoginData({...loginData, password: e.target.value})}
                    placeholder="비밀번호를 입력하세요"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  {isLoading ? '로그인 중...' : '로그인'}
                </button>
              </form>
            )}

            {/* 회원가입 폼 */}
            {activeTab === 'register' && (
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    실명 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={registerData.real_name}
                    onChange={(e) => setRegisterData({...registerData, real_name: e.target.value})}
                    placeholder="실제 이름을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    표시명
                  </label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={registerData.display_name}
                    onChange={(e) => setRegisterData({...registerData, display_name: e.target.value})}
                    placeholder="표시될 이름 (선택사항)"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    이메일 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="email"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={registerData.email}
                    onChange={(e) => setRegisterData({...registerData, email: e.target.value})}
                    placeholder="이메일을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    휴대폰 번호 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="tel"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={registerData.phone_number}
                    onChange={(e) => setRegisterData({...registerData, phone_number: e.target.value})}
                    placeholder="010-1234-5678"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      부서
                    </label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      value={registerData.department}
                      onChange={(e) => setRegisterData({...registerData, department: e.target.value})}
                      placeholder="부서명 (선택사항)"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      직책
                    </label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      value={registerData.position}
                      onChange={(e) => setRegisterData({...registerData, position: e.target.value})}
                      placeholder="직책명 (선택사항)"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    비밀번호 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="password"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={registerData.password}
                    onChange={(e) => setRegisterData({...registerData, password: e.target.value})}
                    placeholder="비밀번호를 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    비밀번호 확인 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="password"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={registerData.confirmPassword}
                    onChange={(e) => setRegisterData({...registerData, confirmPassword: e.target.value})}
                    placeholder="비밀번호를 다시 입력하세요"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  {isLoading ? '가입 중...' : '회원가입'}
                </button>
                <p className="text-xs text-gray-500 text-center">
                  <span className="text-red-500">*</span> 표시는 필수 입력 항목입니다
                </p>
              </form>
            )}

            {/* 비밀번호 찾기 폼 */}
            {activeTab === 'reset' && (
              <form onSubmit={handlePasswordReset} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    이메일
                  </label>
                  <input
                    type="email"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={resetData.email}
                    onChange={(e) => setResetData({...resetData, email: e.target.value})}
                    placeholder="등록된 이메일을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    휴대폰 번호 뒷자리 4자리
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={4}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={resetData.phone_last_digits}
                    onChange={(e) => setResetData({...resetData, phone_last_digits: e.target.value})}
                    placeholder="예: 5678"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-orange-600 text-white py-2 px-4 rounded-md hover:bg-orange-700 disabled:opacity-50"
                >
                  {isLoading ? '처리 중...' : '비밀번호 초기화'}
                </button>
                <p className="text-sm text-gray-600 text-center">
                  임시 비밀번호는 temp[뒷자리]! 형태로 생성됩니다
                </p>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// 파일 관리 페이지
const FileManagerPage = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const navigate = useNavigate()
  const [files, setFiles] = useState<FileItem[]>([])
  const [currentPath, setCurrentPath] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [uploadFiles, setUploadFiles] = useState<FileList | null>(null)
  const [showCreateFolder, setShowCreateFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  // 워크스페이스 정보 조회
  const fetchWorkspace = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/workspaces/${workspaceId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setWorkspace(data)
      } else {
        setError('워크스페이스 정보를 불러올 수 없습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    }
  }

  // 파일 목록 조회
  const fetchFiles = async (path = '') => {
    setIsLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/files/${workspaceId}/list?path=${encodeURIComponent(path)}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setFiles(data.files)
        setCurrentPath(data.current_path)
      } else {
        setError('파일 목록을 불러오는데 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 파일 업로드
  const handleFileUpload = async () => {
    if (!uploadFiles || uploadFiles.length === 0) return

    setIsLoading(true)
    const formData = new FormData()
    
    for (let i = 0; i < uploadFiles.length; i++) {
      formData.append('files', uploadFiles[i])
    }

    try {
      const response = await fetch(`http://localhost:8000/api/files/${workspaceId}/upload?path=${encodeURIComponent(currentPath)}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })
      
      if (response.ok) {
        setMessage('파일이 성공적으로 업로드되었습니다.')
        setUploadFiles(null)
        fetchFiles(currentPath)
      } else {
        const data = await response.json()
        setError(data.detail || '파일 업로드에 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 폴더 생성
  const createFolder = async () => {
    if (!newFolderName.trim()) return

    setIsLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/files/${workspaceId}/create-folder?folder_name=${encodeURIComponent(newFolderName)}&path=${encodeURIComponent(currentPath)}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        setMessage('폴더가 생성되었습니다.')
        setNewFolderName('')
        setShowCreateFolder(false)
        fetchFiles(currentPath)
      } else {
        const data = await response.json()
        setError(data.detail || '폴더 생성에 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 파일/폴더 삭제
  const deleteItem = async (filePath: string) => {
    if (!confirm('정말로 삭제하시겠습니까?')) return

    setIsLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/files/${workspaceId}/delete?file_path=${encodeURIComponent(filePath)}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        setMessage('삭제되었습니다.')
        fetchFiles(currentPath)
      } else {
        const data = await response.json()
        setError(data.detail || '삭제에 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 파일 다운로드
  const downloadFile = async (filePath: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/files/${workspaceId}/download?file_path=${encodeURIComponent(filePath)}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = filePath.split('/').pop() || 'download'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
      } else {
        setError('파일 다운로드에 실패했습니다.')
      }
    } catch (err) {
      setError('파일 다운로드 중 오류가 발생했습니다.')
    }
  }

  // 폴더 이동
  const navigateToFolder = (folderPath: string) => {
    fetchFiles(folderPath)
  }

  // 상위 폴더로 이동
  const goToParent = () => {
    const pathParts = currentPath.split('/').filter(p => p)
    pathParts.pop()
    const parentPath = pathParts.join('/')
    fetchFiles(parentPath)
  }

  useEffect(() => {
    fetchWorkspace()
    fetchFiles()
  }, [workspaceId])

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 헤더 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="text-blue-600 hover:text-blue-800"
              >
                ← 대시보드로 돌아가기
              </button>
              <h1 className="text-2xl font-bold text-gray-900">
                파일 관리 - {workspace?.name}
              </h1>
            </div>
            <span className="text-gray-600">안녕하세요, {user.display_name}님</span>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 메시지 표시 */}
        {message && (
          <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
            {message}
          </div>
        )}
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-md p-6">
          {/* 파일 관리 도구 */}
          <div className="flex flex-wrap items-center justify-between mb-6 gap-4">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">현재 경로:</span>
              <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                /{currentPath}
              </span>
              {currentPath && (
                <button
                  onClick={goToParent}
                  className="text-blue-600 hover:text-blue-800 text-sm"
                >
                  ← 상위 폴더
                </button>
              )}
            </div>
            
            <div className="flex space-x-2">
              <button
                onClick={() => setShowCreateFolder(!showCreateFolder)}
                className="bg-green-600 text-white px-3 py-2 rounded text-sm hover:bg-green-700"
              >
                새 폴더
              </button>
              <label className="bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700 cursor-pointer">
                파일 업로드
                <input
                  type="file"
                  multiple
                  className="hidden"
                  onChange={(e) => setUploadFiles(e.target.files)}
                />
              </label>
              {uploadFiles && uploadFiles.length > 0 && (
                <button
                  onClick={handleFileUpload}
                  disabled={isLoading}
                  className="bg-purple-600 text-white px-3 py-2 rounded text-sm hover:bg-purple-700 disabled:opacity-50"
                >
                  업로드 실행 ({uploadFiles.length}개)
                </button>
              )}
            </div>
          </div>

          {/* 폴더 생성 폼 */}
          {showCreateFolder && (
            <div className="mb-4 p-4 bg-gray-50 rounded-lg">
              <div className="flex space-x-2">
                <input
                  type="text"
                  placeholder="폴더 이름"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <button
                  onClick={createFolder}
                  disabled={isLoading || !newFolderName.trim()}
                  className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  생성
                </button>
                <button
                  onClick={() => setShowCreateFolder(false)}
                  className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
                >
                  취소
                </button>
              </div>
            </div>
          )}

          {/* 파일 목록 */}
          {isLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">로딩 중...</p>
            </div>
          ) : files.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-600">폴더가 비어있습니다.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      이름
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      타입
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      크기
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      작업
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {files.map((file, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <span className="mr-2">
                            {file.is_directory ? '📁' : '📄'}
                          </span>
                          {file.is_directory ? (
                            <button
                              onClick={() => navigateToFolder(file.path)}
                              className="text-blue-600 hover:text-blue-800 font-medium"
                            >
                              {file.name}
                            </button>
                          ) : (
                            <span className="text-gray-900">{file.name}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {file.is_directory ? '폴더' : '파일'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {file.is_directory ? '-' : `${(file.size / 1024).toFixed(1)} KB`}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex space-x-2">
                          {!file.is_directory && (
                            <button
                              onClick={() => downloadFile(file.path)}
                              className="text-blue-600 hover:text-blue-900"
                            >
                              다운로드
                            </button>
                          )}
                          <button
                            onClick={() => deleteItem(file.path)}
                            className="text-red-600 hover:text-red-900"
                          >
                            삭제
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// 대시보드 페이지 (워크스페이스 관리 기능 추가)
const DashboardPage = () => {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newWorkspace, setNewWorkspace] = useState({
    name: '',
    description: ''
  })
  
  const navigate = useNavigate()
  const token = localStorage.getItem('token')
  
  // 워크스페이스 목록 조회
  const fetchWorkspaces = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/workspaces/', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setWorkspaces(data)
      } else {
        setError('워크스페이스 목록을 불러오는데 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }
  
  // 워크스페이스 생성
  const createWorkspace = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    
    try {
      const response = await fetch('http://localhost:8000/api/workspaces/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(newWorkspace)
      })
      
      if (response.ok) {
        setMessage('워크스페이스가 성공적으로 생성되었습니다.')
        setNewWorkspace({ name: '', description: '' })
        setShowCreateForm(false)
        fetchWorkspaces()
      } else {
        const data = await response.json()
        setError(data.detail || '워크스페이스 생성에 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }
  
  // Jupyter Lab 시작
  const startJupyter = async (workspaceId: number) => {
    setIsLoading(true)
    setError('')
    try {
      const response = await fetch(`http://localhost:8000/api/jupyter/start/${workspaceId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setMessage('Jupyter Lab이 시작되었습니다.')
        // 새 탭에서 Jupyter Lab 열기
        if (data.url) {
          console.log('Opening Jupyter Lab:', data.url);
          window.open(data.url, '_blank', 'noopener,noreferrer');
        }
        fetchWorkspaces()
      } else {
        const data = await response.json()
        setError(data.detail || 'Jupyter Lab 시작에 실패했습니다.')
        console.error('Jupyter start error:', data)
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다. 백엔드 서버가 실행 중인지 확인해주세요.')
      console.error('Network error:', err)
    } finally {
      setIsLoading(false)
    }
  }
  
  // Jupyter Lab 중지
  const stopJupyter = async (workspaceId: number) => {
    setIsLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/jupyter/stop/${workspaceId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        setMessage('Jupyter Lab이 중지되었습니다.')
        fetchWorkspaces()
      } else {
        const data = await response.json()
        setError(data.detail || 'Jupyter Lab 중지에 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }
  
  // 워크스페이스 삭제
  const deleteWorkspace = async (workspaceId: number) => {
    if (!confirm('정말로 이 워크스페이스를 삭제하시겠습니까?')) {
      return
    }
    
    setIsLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/workspaces/${workspaceId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        setMessage('워크스페이스가 삭제되었습니다.')
        fetchWorkspaces()
      } else {
        const data = await response.json()
        setError(data.detail || '워크스페이스 삭제에 실패했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }
  
  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/'
  }
  
  // 컴포넌트 마운트 시 워크스페이스 목록 조회
  useEffect(() => {
    fetchWorkspaces()
  }, [])

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 헤더 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">Jupyter Data Platform</h1>
            <div className="flex items-center space-x-4">
              <span className="text-gray-600">안녕하세요, {user.display_name}님</span>
              <button
                onClick={handleLogout}
                className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
              >
                로그아웃
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 메시지 표시 */}
        {message && (
          <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
            {message}
          </div>
        )}
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 사용자 정보 */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">사용자 정보</h2>
              <div className="space-y-2 text-sm">
                <p><strong>실명:</strong> {user.real_name}</p>
                <p><strong>표시명:</strong> {user.display_name}</p>
                <p><strong>이메일:</strong> {user.email}</p>
                <p><strong>휴대폰:</strong> {user.phone_number}</p>
                {user.department && <p><strong>부서:</strong> {user.department}</p>}
                {user.position && <p><strong>직책:</strong> {user.position}</p>}
                <p><strong>로그인 횟수:</strong> {user.login_count}회</p>
              </div>
            </div>
          </div>

          {/* 워크스페이스 관리 */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-lg font-semibold text-gray-800">워크스페이스</h2>
                <button
                  onClick={() => setShowCreateForm(!showCreateForm)}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                >
                  새 워크스페이스
                </button>
              </div>

              {/* 워크스페이스 생성 폼 */}
              {showCreateForm && (
                <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                  <form onSubmit={createWorkspace} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        워크스페이스 이름
                      </label>
                      <input
                        type="text"
                        required
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value={newWorkspace.name}
                        onChange={(e) => setNewWorkspace({...newWorkspace, name: e.target.value})}
                        placeholder="예: 데이터 분석 프로젝트"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        설명 (선택사항)
                      </label>
                      <textarea
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={3}
                        value={newWorkspace.description}
                        onChange={(e) => setNewWorkspace({...newWorkspace, description: e.target.value})}
                        placeholder="워크스페이스에 대한 설명을 입력하세요"
                      />
                    </div>
                    <div className="flex space-x-2">
                      <button
                        type="submit"
                        disabled={isLoading}
                        className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
                      >
                        {isLoading ? '생성 중...' : '생성'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowCreateForm(false)}
                        className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
                      >
                        취소
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {/* 워크스페이스 목록 */}
              {isLoading && workspaces.length === 0 ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="mt-2 text-gray-600">로딩 중...</p>
                </div>
              ) : workspaces.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-600">아직 워크스페이스가 없습니다.</p>
                  <p className="text-sm text-gray-500 mt-1">새 워크스페이스를 생성해보세요!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {workspaces.map((workspace) => (
                    <div key={workspace.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900">{workspace.name}</h3>
                          {workspace.description && (
                            <p className="text-gray-600 text-sm mt-1">{workspace.description}</p>
                          )}
                          <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                            <span>생성일: {new Date(workspace.created_at).toLocaleDateString()}</span>
                            <span className={`px-2 py-1 rounded ${
                              workspace.jupyter_port ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                            }`}>
                              {workspace.jupyter_port ? 'Jupyter 실행 중' : 'Jupyter 중지됨'}
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2 ml-4">
                          <button
                            onClick={() => navigate(`/files/${workspace.id}`)}
                            className="bg-purple-600 text-white px-3 py-1 rounded text-sm hover:bg-purple-700"
                          >
                            파일 관리
                          </button>
                          {workspace.jupyter_port ? (
                            <>
                              <button
                                onClick={() => {
                                  const jupyterUrl = `http://localhost:${workspace.jupyter_port}/lab`;
                                  console.log('Opening Jupyter Lab:', jupyterUrl);
                                  window.open(jupyterUrl, '_blank', 'noopener,noreferrer');
                                }}
                                className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
                              >
                                열기
                              </button>
                              <button
                                onClick={() => {
                                  // 직접 Jupyter Lab 접속 (토큰 없음)
                                  const jupyterUrl = `http://localhost:${workspace.jupyter_port}/`;
                                  window.open(jupyterUrl, '_blank', 'noopener,noreferrer');
                                }}
                                className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                              >
                                홈 열기
                              </button>
                              <button
                                onClick={() => stopJupyter(workspace.id)}
                                disabled={isLoading}
                                className="bg-orange-600 text-white px-3 py-1 rounded text-sm hover:bg-orange-700 disabled:opacity-50"
                              >
                                중지
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => startJupyter(workspace.id)}
                              disabled={isLoading}
                              className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
                            >
                              시작
                            </button>
                          )}
                          <button
                            onClick={() => deleteWorkspace(workspace.id)}
                            disabled={isLoading}
                            className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 disabled:opacity-50"
                          >
                            삭제
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// 워크스페이스 목록 페이지 컴포넌트 추가
const WorkspacesPage = () => {
  return <div className="p-8 text-center text-gray-500">Workspaces Page - Will be moved to new layout</div>;
};

// 인증 체크 컴포넌트
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const navigate = useNavigate()
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      navigate('/')
    } else {
      // 토큰 유효성 검사 (선택사항)
      setIsChecking(false)
    }
  }, [navigate])

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return <>{children}</>
}

// 루트 리다이렉트 컴포넌트
const RootRedirect = () => {
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      navigate('/main')
    }
    // 토큰이 없으면 현재 페이지(HomePage)가 표시됨
  }, [navigate])

  return <HomePage />
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          
          {/* Dashboard Layout Routes */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }>
            <Route index element={<NewDashboardPage />} />
          </Route>
          
          <Route path="/llmops" element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }>
            <Route index element={<LLMOpsPage />} />
          </Route>
          
          <Route path="/analytics" element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }>
            <Route index element={<div className="p-8 text-center text-gray-500">Analytics Page - Coming Soon</div>} />
          </Route>
          
          <Route path="/workspaces" element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }>
            <Route index element={<WorkspacesPage />} />
          </Route>
          
          <Route path="/admin" element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }>
            <Route index element={<AdminPage />} />
          </Route>
          
          {/* Legacy routes for backward compatibility */}
          <Route path="/main" element={<ProtectedRoute><MainPage /></ProtectedRoute>} />
          <Route path="/files/:workspaceId" element={<ProtectedRoute><FileManagerPage /></ProtectedRoute>} />
          <Route path="/rag-datasources" element={<ProtectedRoute><RAGDataSourcePage /></ProtectedRoute>} />
          <Route path="/llmops-flow/:workspaceId" element={<ProtectedRoute><FlowStudioPage /></ProtectedRoute>} />
        </Routes>
      </div>
    </Router>
    </AuthProvider>
  )
}

export default App 