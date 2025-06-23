import React, { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, AlertCircle, Wifi, WifiOff, Settings, FileText, Code, Hash, Eye, EyeOff } from 'lucide-react'

interface LLMChatPanelProps {
  workspaceId: number
  notebookPath?: string
  onClose?: () => void
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  error?: boolean
  analysis_info?: {
    total_cells_analyzed: number
    cell_indices?: number[]
    notebook_summary?: {
      total_cells: number
      code_cells: number
      markdown_cells: number
    }
  }
}

interface LLMStatus {
  connections: {
    azure: boolean
    ollama: boolean
  }
  available_models: {
    azure: string[]
    ollama: string[]
  }
  azure_available: boolean
  ollama_available: boolean
}

interface NotebookCell {
  index: number
  cell_type: string
  preview: string
  line_count: number
  execution_count?: number
  has_output: boolean
  has_error: boolean
}

interface NotebookStructure {
  summary: {
    total_cells: number
    code_cells: number
    markdown_cells: number
  }
  cells: NotebookCell[]
}

const LLMChatPanel: React.FC<LLMChatPanelProps> = ({ 
  workspaceId, 
  notebookPath, 
  onClose 
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null)
  const [selectedProvider, setSelectedProvider] = useState<'azure' | 'ollama'>('ollama')
  const [isConnected, setIsConnected] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showNotebookStructure, setShowNotebookStructure] = useState(false)
  const [notebookStructure, setNotebookStructure] = useState<NotebookStructure | null>(null)
  const [selectedCells, setSelectedCells] = useState<Set<number>>(new Set())
  const [isLoadingStructure, setIsLoadingStructure] = useState(false)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const token = localStorage.getItem('token')

  // 스크롤을 맨 아래로
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // LLM 상태 확인
  useEffect(() => {
    checkLLMStatus()
  }, [])

  // 노트북 경로가 변경될 때 구조 정보 초기화
  useEffect(() => {
    setNotebookStructure(null)
    setSelectedCells(new Set())
  }, [notebookPath])

  const checkLLMStatus = async () => {
    try {
      const response = await fetch('/api/llm/status', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const status = await response.json()
        setLlmStatus(status)
        
        // 연결 가능한 첫 번째 제공자 선택
        if (status.connections.azure) {
          setSelectedProvider('azure')
          setIsConnected(true)
        } else if (status.connections.ollama) {
          setSelectedProvider('ollama')
          setIsConnected(true)
        } else {
          setIsConnected(false)
        }
      }
    } catch (error) {
      console.error('LLM 상태 확인 실패:', error)
      setIsConnected(false)
    }
  }

  const loadNotebookStructure = async () => {
    if (!notebookPath) {
      alert('노트북 파일이 선택되지 않았습니다.')
      return
    }

    setIsLoadingStructure(true)
    try {
      const response = await fetch('/api/llm/notebook-structure', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          workspace_id: workspaceId,
          notebook_path: notebookPath
        })
      })

      if (response.ok) {
        const result = await response.json()
        setNotebookStructure(result)
        setShowNotebookStructure(true)
      } else {
        const error = await response.json()
        alert(`노트북 구조 로드 실패: ${error.detail}`)
      }
    } catch (error) {
      alert('노트북 구조 로드 중 오류가 발생했습니다.')
    } finally {
      setIsLoadingStructure(false)
    }
  }

  const toggleCellSelection = (cellIndex: number) => {
    const newSelection = new Set(selectedCells)
    if (newSelection.has(cellIndex)) {
      newSelection.delete(cellIndex)
    } else {
      newSelection.add(cellIndex)
    }
    setSelectedCells(newSelection)
  }

  const selectAllCells = () => {
    if (!notebookStructure) return
    const allIndices = notebookStructure.cells.map(cell => cell.index)
    setSelectedCells(new Set(allIndices))
  }

  const clearCellSelection = () => {
    setSelectedCells(new Set())
  }

  const sendMessage = async (analysisType: 'full' | 'cells' = 'full') => {
    if (!inputMessage.trim() || isLoading || !isConnected) return

    // 선택된 셀 분석의 경우 셀이 선택되어 있는지 확인
    if (analysisType === 'cells' && selectedCells.size === 0) {
      alert('분석할 셀을 선택해주세요.')
      return
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      let endpoint = '/api/llm/chat'
      let requestBody: any = {
        message: userMessage.content,
        workspace_id: workspaceId,
        notebook_path: notebookPath,
        provider: selectedProvider
      }

      if (analysisType === 'cells') {
        endpoint = '/api/llm/analyze-cells'
        requestBody.cell_indices = Array.from(selectedCells)
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestBody)
      })

      if (response.ok) {
        const result = await response.json()
        
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: result.response,
          timestamp: new Date(),
          analysis_info: result.analysis_info
        }
        
        setMessages(prev => [...prev, assistantMessage])
      } else {
        const error = await response.json()
        const errorMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `오류가 발생했습니다: ${error.detail}`,
          timestamp: new Date(),
          error: true
        }
        
        setMessages(prev => [...prev, errorMessage])
      }
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '연결 오류가 발생했습니다. 다시 시도해주세요.',
        timestamp: new Date(),
        error: true
      }
      
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleProviderChange = async (provider: 'azure' | 'ollama') => {
    setSelectedProvider(provider)
    
    // 선택한 제공자 연결 상태 확인
    try {
      const response = await fetch('/api/llm/check-connection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ provider })
      })
      
      if (response.ok) {
        const result = await response.json()
        setIsConnected(result.connections[provider])
      }
    } catch (error) {
      setIsConnected(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage('full')
    }
  }

  const getCellTypeIcon = (cellType: string) => {
    switch (cellType) {
      case 'code':
        return <Code className="w-4 h-4 text-blue-500" />
      case 'markdown':
        return <FileText className="w-4 h-4 text-green-500" />
      default:
        return <Hash className="w-4 h-4 text-gray-500" />
    }
  }

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      {/* 헤더 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-2">
          <Bot className="w-5 h-5 text-blue-500" />
          <h3 className="font-medium text-gray-900">AI 노트북 도우미</h3>
          {isConnected ? (
            <Wifi className="w-4 h-4 text-green-500" />
          ) : (
            <WifiOff className="w-4 h-4 text-red-500" />
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-1 hover:bg-gray-200 rounded"
          >
            <Settings className="w-4 h-4 text-gray-500" />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-200 rounded text-gray-500"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* 설정 패널 */}
      {showSettings && (
        <div className="p-4 bg-gray-50 border-b border-gray-200">
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                LLM 제공자
              </label>
              <div className="flex space-x-2">
                {llmStatus?.azure_available && (
                  <button
                    onClick={() => handleProviderChange('azure')}
                    className={`px-3 py-1 text-xs rounded-full ${
                      selectedProvider === 'azure'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    Azure OpenAI
                    {llmStatus?.connections.azure && (
                      <span className="ml-1 text-green-600">●</span>
                    )}
                  </button>
                )}
                {llmStatus?.ollama_available && (
                  <button
                    onClick={() => handleProviderChange('ollama')}
                    className={`px-3 py-1 text-xs rounded-full ${
                      selectedProvider === 'ollama'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    Ollama
                    {llmStatus?.connections.ollama && (
                      <span className="ml-1 text-green-600">●</span>
                    )}
                  </button>
                )}
              </div>
            </div>
            
            {notebookPath && (
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  분석 중인 노트북
                </label>
                <p className="text-xs text-gray-500">{notebookPath}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 노트북 구조 패널 */}
      {showNotebookStructure && notebookStructure && (
        <div className="border-b border-gray-200 bg-gray-50">
          <div className="p-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-700">노트북 셀 선택</h4>
              <button
                onClick={() => setShowNotebookStructure(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <EyeOff className="w-4 h-4" />
              </button>
            </div>
            
            <div className="text-xs text-gray-500 mb-2">
              총 {notebookStructure.summary.total_cells}개 셀 
              (코드: {notebookStructure.summary.code_cells}, 마크다운: {notebookStructure.summary.markdown_cells})
            </div>
            
            <div className="flex space-x-2 mb-3">
              <button
                onClick={selectAllCells}
                className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
              >
                전체 선택
              </button>
              <button
                onClick={clearCellSelection}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                선택 해제
              </button>
              <span className="text-xs text-gray-500 self-center">
                {selectedCells.size}개 선택됨
              </span>
            </div>
            
            <div className="max-h-32 overflow-y-auto space-y-1">
              {notebookStructure.cells.map((cell) => (
                <div
                  key={cell.index}
                  onClick={() => toggleCellSelection(cell.index)}
                  className={`p-2 text-xs border rounded cursor-pointer ${
                    selectedCells.has(cell.index)
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center space-x-1">
                      {getCellTypeIcon(cell.cell_type)}
                      <span className="font-medium">셀 {cell.index + 1}</span>
                      {cell.has_error && (
                        <AlertCircle className="w-3 h-3 text-red-500" />
                      )}
                    </div>
                    <div className="text-gray-400">
                      {cell.line_count}줄
                      {cell.execution_count && ` [${cell.execution_count}]`}
                    </div>
                  </div>
                  <div className="text-gray-600 truncate">
                    {cell.preview || '(빈 셀)'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 컨텍스트 전송 버튼들 */}
      {notebookPath && (
        <div className="p-3 border-b border-gray-200 bg-gray-50">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => sendMessage('full')}
              disabled={!inputMessage.trim() || !isConnected || isLoading}
              className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              전체 노트북 분석
            </button>
            
            <button
              onClick={loadNotebookStructure}
              disabled={isLoadingStructure}
              className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50"
            >
              {showNotebookStructure ? <EyeOff className="w-3 h-3 inline mr-1" /> : <Eye className="w-3 h-3 inline mr-1" />}
              {isLoadingStructure ? '로딩...' : (showNotebookStructure ? '셀 목록 숨기기' : '셀 선택하기')}
            </button>
            
            {selectedCells.size > 0 && (
              <button
                onClick={() => sendMessage('cells')}
                disabled={!inputMessage.trim() || !isConnected || isLoading}
                className="px-3 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                선택된 {selectedCells.size}개 셀 분석
              </button>
            )}
          </div>
        </div>
      )}

      {/* 연결 상태 경고 */}
      {!isConnected && (
        <div className="p-3 bg-yellow-50 border-b border-yellow-200">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-yellow-600" />
            <p className="text-sm text-yellow-700">
              LLM 서비스에 연결할 수 없습니다. 설정을 확인해주세요.
            </p>
          </div>
        </div>
      )}

      {/* 메시지 목록 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <Bot className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-sm">
              안녕하세요! Jupyter 노트북 분석을 도와드리겠습니다.
            </p>
            <p className="text-xs text-gray-400 mt-1">
              노트북 코드에 대해 질문하거나 개선 방안을 요청해보세요.
            </p>
            {notebookPath && (
              <p className="text-xs text-blue-500 mt-2">
                💡 "셀 선택하기" 버튼을 눌러 특정 셀만 분석할 수 있습니다.
              </p>
            )}
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : message.error
                  ? 'bg-red-50 text-red-800 border border-red-200'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="flex items-start space-x-2">
                {message.role === 'assistant' && (
                  <Bot className="w-4 h-4 mt-0.5 flex-shrink-0" />
                )}
                {message.role === 'user' && (
                  <User className="w-4 h-4 mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1">
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  {message.analysis_info && (
                    <div className="text-xs opacity-70 mt-2 p-2 bg-black bg-opacity-10 rounded">
                      분석된 셀: {message.analysis_info.total_cells_analyzed}개
                      {message.analysis_info.cell_indices && (
                        <span> (셀 번호: {message.analysis_info.cell_indices.map(i => i + 1).join(', ')})</span>
                      )}
                    </div>
                  )}
                  <p className="text-xs opacity-70 mt-1">
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3 max-w-[80%]">
              <div className="flex items-center space-x-2">
                <Bot className="w-4 h-4" />
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="flex space-x-2">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              isConnected 
                ? "노트북에 대해 질문해보세요..." 
                : "LLM 서비스에 연결되지 않았습니다"
            }
            disabled={!isConnected || isLoading}
            className="flex-1 resize-none border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:text-gray-400"
            rows={2}
          />
          <button
            onClick={() => sendMessage('full')}
            disabled={!inputMessage.trim() || !isConnected || isLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default LLMChatPanel 