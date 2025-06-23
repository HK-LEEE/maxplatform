import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Play, Square, Trash2, FileText, MessageSquare, X } from 'lucide-react'
import { workspaceAPI, jupyterAPI } from '../services/api'
import LLMChatPanel from '../components/LLMChatPanel'

interface WorkspaceDetail {
  id: number
  name: string
  description?: string
  status?: string
  port?: number
  jupyter_url?: string
  path?: string
}

const WorkspaceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState<WorkspaceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [showChatPanel, setShowChatPanel] = useState(false)
  const [currentNotebook] = useState<string | undefined>()

  useEffect(() => {
    if (id) {
      fetchWorkspace()
    }
  }, [id])

  const fetchWorkspace = async () => {
    try {
      setLoading(true)
      const data = await workspaceAPI.get(parseInt(id!))
      setWorkspace(data)
    } catch (error) {
      console.error('워크스페이스 정보를 가져오는데 실패했습니다:', error)
    } finally {
      setLoading(false)
    }
  }

  const startWorkspace = async () => {
    if (!workspace) return

    try {
      setIsStarting(true)
      await jupyterAPI.start(workspace.id)
      await fetchWorkspace() // 상태 새로고침
    } catch (error) {
      console.error('워크스페이스 시작 실패:', error)
      alert('워크스페이스 시작에 실패했습니다.')
    } finally {
      setIsStarting(false)
    }
  }

  const stopWorkspace = async () => {
    if (!workspace) return

    try {
      setIsStopping(true)
      await jupyterAPI.stop(workspace.id)
      await fetchWorkspace() // 상태 새로고침
    } catch (error) {
      console.error('워크스페이스 중지 실패:', error)
      alert('워크스페이스 중지에 실패했습니다.')
    } finally {
      setIsStopping(false)
    }
  }

  const deleteWorkspace = async () => {
    if (!workspace) return

    if (window.confirm('정말로 이 워크스페이스를 삭제하시겠습니까?')) {
      try {
        await workspaceAPI.delete(workspace.id)
        navigate('/dashboard')
      } catch (error) {
        console.error('워크스페이스 삭제 실패:', error)
        alert('워크스페이스 삭제에 실패했습니다.')
      }
    }
  }

  const openJupyter = () => {
    if (workspace?.jupyter_url) {
      window.open(workspace.jupyter_url, '_blank')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-gray-600">로딩 중...</p>
        </div>
      </div>
    )
  }

  if (!workspace) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">워크스페이스를 찾을 수 없습니다</h2>
          <button
            onClick={() => navigate('/dashboard')}
            className="text-blue-600 hover:text-blue-500"
          >
            대시보드로 돌아가기
          </button>
        </div>
      </div>
    )
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-600 bg-green-100'
      case 'starting':
        return 'text-yellow-600 bg-yellow-100'
      case 'stopped':
        return 'text-gray-600 bg-gray-100'
      case 'error':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running':
        return '실행 중'
      case 'starting':
        return '시작 중'
      case 'stopped':
        return '중지됨'
      case 'error':
        return '오류'
      default:
        return '알 수 없음'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-center justify-between">
              <div>
                <button
                  onClick={() => navigate('/dashboard')}
                  className="text-gray-500 hover:text-gray-700 mb-4"
                >
                  ← 대시보드로 돌아가기
                </button>
                <h1 className="text-3xl font-bold text-gray-900">{workspace.name}</h1>
                <p className="mt-2 text-gray-600">{workspace.description}</p>
              </div>
              <div className="flex items-center space-x-4">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(workspace.status || 'stopped')}`}>
                  {getStatusText(workspace.status || 'stopped')}
                </span>
                {workspace.port && (
                  <span className="text-sm text-gray-500">
                    포트: {workspace.port}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 gap-8">
          {/* 컨트롤 패널 */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">워크스페이스 제어</h2>
            <div className="flex flex-wrap gap-4">
              {workspace.status === 'running' ? (
                <>
                  <button
                    onClick={openJupyter}
                    className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    Jupyter Lab 열기
                  </button>
                  <button
                    onClick={stopWorkspace}
                    disabled={isStopping}
                    className="flex items-center px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50"
                  >
                    <Square className="w-4 h-4 mr-2" />
                    {isStopping ? '중지 중...' : '중지'}
                  </button>
                  <button
                    onClick={() => setShowChatPanel(!showChatPanel)}
                    className={`flex items-center px-4 py-2 rounded-md ${
                      showChatPanel 
                        ? 'bg-green-600 text-white hover:bg-green-700'
                        : 'bg-purple-600 text-white hover:bg-purple-700'
                    }`}
                  >
                    {showChatPanel ? (
                      <>
                        <X className="w-4 h-4 mr-2" />
                        AI 채팅 닫기
                      </>
                    ) : (
                      <>
                        <MessageSquare className="w-4 h-4 mr-2" />
                        AI 노트북 도우미
                      </>
                    )}
                  </button>
                </>
              ) : (
                <button
                  onClick={startWorkspace}
                  disabled={isStarting || workspace.status === 'starting'}
                  className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  <Play className="w-4 h-4 mr-2" />
                  {isStarting || workspace.status === 'starting' ? '시작 중...' : '시작'}
                </button>
              )}
              
              <button
                onClick={deleteWorkspace}
                className="flex items-center px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                삭제
              </button>
            </div>
          </div>

          {/* 메인 콘텐츠 영역 */}
          <div className="flex gap-8">
            {/* Jupyter Lab 임베드 영역 */}
            <div className={`bg-white shadow rounded-lg ${showChatPanel ? 'flex-1' : 'w-full'}`}>
              <div className="p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Jupyter Lab</h2>
                {workspace.status === 'running' && workspace.jupyter_url ? (
                  <div className="border rounded-lg overflow-hidden" style={{ height: '600px' }}>
                    <iframe
                      src={workspace.jupyter_url}
                      className="w-full h-full"
                      title="Jupyter Lab"
                      frameBorder="0"
                    />
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg">
                    <div className="text-center">
                      <FileText className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                      <p className="text-gray-500">
                        {workspace.status === 'starting' 
                          ? 'Jupyter Lab을 시작하고 있습니다...'
                          : '워크스페이스를 시작하여 Jupyter Lab을 사용하세요.'
                        }
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* LLM 채팅 패널 */}
            {showChatPanel && (
              <div className="w-96 bg-white shadow rounded-lg overflow-hidden">
                <div style={{ height: '600px' }}>
                  <LLMChatPanel
                    workspaceId={workspace.id}
                    notebookPath={currentNotebook}
                    onClose={() => setShowChatPanel(false)}
                  />
                </div>
              </div>
            )}
          </div>

          {/* 워크스페이스 정보 */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">워크스페이스 정보</h2>
            <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-gray-500">ID</dt>
                <dd className="mt-1 text-sm text-gray-900">{workspace.id}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">상태</dt>
                <dd className="mt-1">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(workspace.status || 'stopped')}`}>
                    {getStatusText(workspace.status || 'stopped')}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">포트</dt>
                <dd className="mt-1 text-sm text-gray-900">{workspace.port || 'N/A'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">경로</dt>
                <dd className="mt-1 text-sm text-gray-900 font-mono">{workspace.path}</dd>
              </div>
              {workspace.jupyter_url && (
                <div className="sm:col-span-2">
                  <dt className="text-sm font-medium text-gray-500">Jupyter URL</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    <a 
                      href={workspace.jupyter_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-500 break-all"
                    >
                      {workspace.jupyter_url}
                    </a>
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}

export default WorkspaceDetailPage 