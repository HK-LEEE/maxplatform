import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { MessageSquare } from 'lucide-react'
import LLMChatPanel from '../components/LLMChatPanel'

const SimpleWorkspaceDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const [showChatPanel, setShowChatPanel] = useState(true)
  const [workspaceId, setWorkspaceId] = useState<number>(0)

  useEffect(() => {
    if (id) {
      setWorkspaceId(parseInt(id))
    }
  }, [id])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <h1 className="text-3xl font-bold text-gray-900">Jupyter 워크스페이스 {id}</h1>
            <p className="mt-2 text-gray-600">AI 노트북 도우미가 포함된 워크스페이스</p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-8">
          {/* Jupyter Lab 영역 */}
          <div className={`bg-white shadow rounded-lg ${showChatPanel ? 'flex-1' : 'w-full'}`}>
            <div className="p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Jupyter Lab</h2>
              <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg">
                <div className="text-center">
                  <MessageSquare className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                  <p className="text-gray-500">
                    Jupyter Lab 영역 - 실제 환경에서는 iframe으로 표시됩니다
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* LLM 채팅 패널 */}
          {showChatPanel && (
            <div className="w-96 bg-white shadow rounded-lg overflow-hidden">
              <div style={{ height: '600px' }}>
                <LLMChatPanel
                  workspaceId={workspaceId}
                  onClose={() => setShowChatPanel(false)}
                />
              </div>
            </div>
          )}
        </div>

        {/* 채팅 토글 버튼 */}
        {!showChatPanel && (
          <div className="fixed bottom-8 right-8">
            <button
              onClick={() => setShowChatPanel(true)}
              className="bg-purple-600 text-white p-4 rounded-full shadow-lg hover:bg-purple-700 transition-colors"
            >
              <MessageSquare className="w-6 h-6" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default SimpleWorkspaceDetail 