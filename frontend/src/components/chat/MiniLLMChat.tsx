import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageCircle, Plus, Send, Bot, User, X, Maximize2, 
  Settings, Trash2, ChevronLeft, ChevronRight, Minimize2,
  Loader2, AlertCircle, Menu, Database, Brain, ThumbsUp, 
  ThumbsDown, Copy, Share, Search, Filter, Check
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { llmChatApi } from '../../services/llmChatApi';
import {
  Chat, Message, Persona, LLMModel, RAGDataSource,
  ChatCreateRequest, MessageSendRequest, SenderType
} from '../../types/llmChat';

interface MiniLLMChatProps {
  isOpen: boolean;
  onClose: () => void;
  onExpand: (chatId?: string) => void;
}

const MiniLLMChat: React.FC<MiniLLMChatProps> = ({ isOpen, onClose, onExpand }) => {
  const navigate = useNavigate();
  
  // 상태 관리
  const [chats, setChats] = useState<Chat[]>([]);
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [ragSources, setRagSources] = useState<RAGDataSource[]>([]);
  
  const [newMessage, setNewMessage] = useState('');
  const [selectedPersona, setSelectedPersona] = useState<number | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedRAGSources, setSelectedRAGSources] = useState<number[]>([]);
  
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageInputRef = useRef<HTMLTextAreaElement>(null);

  // 초기 데이터 로드
  useEffect(() => {
    if (isOpen) {
      loadInitialData();
    }
  }, [isOpen]);

  // 메시지 스크롤
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadInitialData = async () => {
    try {
      setIsLoading(true);
      
      const [chatsData, personasData, modelsData, ragSourcesData] = await Promise.all([
        llmChatApi.getChats(),
        llmChatApi.getPersonas(),
        llmChatApi.getAvailableModels(),
        llmChatApi.getRAGDataSources()
      ]);
      
      setChats(chatsData);
      setPersonas(personasData);
      setModels(modelsData);
      setRagSources(ragSourcesData);
      
      // 기본 모델 선택
      if (modelsData.length > 0 && !selectedModel) {
        setSelectedModel(modelsData[0].id);
      }

      // 첫 번째 채팅 선택 또는 새 채팅 생성
      if (chatsData.length > 0) {
        await handleChatSelect(chatsData[0]);
      } else {
        await handleCreateChat();
      }
      
    } catch (error) {
      console.error('초기 데이터 로드 실패:', error);
      setError('데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChatSelect = async (chat: Chat) => {
    try {
      setSelectedChat(chat);
      setIsLoading(true);
      
      const chatMessages = await llmChatApi.getChatMessages(chat.id);
      setMessages(chatMessages);
      
      // 채팅에 설정된 페르소나가 있으면 선택
      if (chat.persona_id) {
        setSelectedPersona(chat.persona_id);
      }
      
    } catch (error) {
      console.error('채팅 메시지 로드 실패:', error);
      setError('채팅 메시지를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateChat = async () => {
    if (!selectedModel) {
      setError('모델을 선택해주세요.');
      return;
    }

    try {
      const chatData: ChatCreateRequest = {
        title: `새 채팅 ${new Date().toLocaleTimeString()}`,
        model_id: selectedModel,
        persona_id: selectedPersona || undefined
      };

      const newChat = await llmChatApi.createChat(chatData);
      setChats([newChat, ...chats]);
      setSelectedChat(newChat);
      setMessages([]);
      
    } catch (error) {
      console.error('채팅 생성 실패:', error);
      setError('채팅 생성 중 오류가 발생했습니다.');
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedChat || isLoading) return;

    const userMessage = newMessage.trim();
    const userMessageObj: Message = {
      id: `temp-user-${Date.now()}`,
      chat_id: selectedChat.id,
      sender_type: 'USER' as SenderType,
      content: userMessage,
      created_at: new Date().toISOString()
    };

    // 사용자 메시지를 즉시 표시
    setMessages(prev => [...prev, userMessageObj]);
    setNewMessage('');
    setIsTyping(true);

    // AbortController 생성 (응답 중지용)
    const controller = new AbortController();
    setAbortController(controller);

    try {
      const messageData: MessageSendRequest = {
        content: userMessage,
        rag_datasource_ids: selectedRAGSources.length > 0 ? selectedRAGSources : undefined
      };

      const aiResponse = await llmChatApi.sendMessage(selectedChat.id, messageData);
      
      // AI 응답을 메시지 목록에 추가
      setMessages(prev => [...prev, aiResponse]);
      
      // 채팅 목록 갱신
      await loadInitialData();
      
    } catch (error: any) {
      console.error('메시지 전송 실패:', error);
      if (error.name !== 'AbortError') {
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          chat_id: selectedChat.id,
          sender_type: 'AI' as SenderType,
          content: '죄송합니다. 메시지 전송 중 오류가 발생했습니다.',
          created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } finally {
      setIsTyping(false);
      setAbortController(null);
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    try {
      await llmChatApi.deleteChat(chatId);
      setChats(prev => prev.filter(chat => chat.id !== chatId));
      
      if (selectedChat?.id === chatId) {
        const remainingChats = chats.filter(chat => chat.id !== chatId);
        if (remainingChats.length > 0) {
          await handleChatSelect(remainingChats[0]);
        } else {
          setSelectedChat(null);
          setMessages([]);
        }
      }
    } catch (error) {
      console.error('채팅 삭제 실패:', error);
      setError('채팅을 삭제하는 중 오류가 발생했습니다.');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleMessageFeedback = async (messageId: string, rating: 'LIKE' | 'DISLIKE') => {
    try {
      await llmChatApi.addMessageFeedback(messageId, { rating });
    } catch (error) {
      console.error('피드백 전송 실패:', error);
    }
  };

  const formatMessageTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  };

  const handleStopResponse = () => {
    if (abortController) {
      abortController.abort();
      setIsTyping(false);
      setAbortController(null);
    }
  };

  const copyMessageToClipboard = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* 미니 채팅 창 - ChatPage와 동일한 디자인 */}
      <div className={`h-[600px] bg-gray-50 rounded-2xl shadow-2xl border border-gray-200 flex overflow-hidden transition-all duration-300 ${
        showSettings && sidebarOpen ? 'w-[736px]' : 
        showSettings ? 'w-[544px]' :
        sidebarOpen ? 'w-[512px]' : 'w-80'
      }`}>
        
        {/* 왼쪽 사이드바 */}
        <div className={`bg-white border-r border-gray-200 flex flex-col transition-all duration-300 ${
          sidebarOpen ? 'w-48' : 'w-12'
        }`}>
          
          {/* 사이드바 헤더 */}
          <div className="p-3 border-b border-gray-200 flex items-center justify-between">
            {sidebarOpen && (
              <div className="flex items-center space-x-2">
                <MessageCircle className="w-5 h-5 text-gray-800" />
                <h1 className="text-sm font-semibold text-gray-800">AI 채팅</h1>
              </div>
            )}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors"
            >
              {sidebarOpen ? (
                <ChevronLeft className="w-3 h-3 text-gray-600" />
              ) : (
                <ChevronRight className="w-3 h-3 text-gray-600" />
              )}
            </button>
          </div>

          {sidebarOpen && (
            <>
              {/* 새 채팅 버튼 */}
              <div className="p-3">
                <button
                  onClick={handleCreateChat}
                  disabled={!selectedModel}
                  className="w-full flex items-center justify-center space-x-2 bg-gray-800 text-white py-2 px-3 rounded-lg hover:bg-gray-700 transition-colors text-sm disabled:bg-gray-400"
                >
                  <Plus className="w-3 h-3" />
                  <span>새 채팅</span>
                </button>
              </div>

              {/* 채팅 목록 */}
              <div className="flex-1 overflow-y-auto">
                <div className="px-3 pb-3">
                  <h3 className="text-xs font-medium text-gray-600 mb-2">최근 채팅</h3>
                  <div className="space-y-1">
                    {chats.map((chat) => (
                      <div
                        key={chat.id}
                        className={`relative group rounded-lg transition-colors ${
                          selectedChat?.id === chat.id
                            ? 'bg-gray-200 border border-gray-300'
                            : 'hover:bg-gray-100 border border-transparent'
                        }`}
                      >
                        <button
                          onClick={() => handleChatSelect(chat)}
                          className="w-full text-left p-2 pr-8"
                        >
                          <div className="flex items-start space-x-2">
                            <MessageCircle className="w-3 h-3 text-gray-600 mt-0.5 flex-shrink-0" />
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-medium text-gray-800 truncate">
                                {chat.title}
                              </p>
                              <p className="text-xs text-gray-500 mt-0.5">
                                {new Date(chat.updated_at).toLocaleDateString()}
                              </p>
                              {chat.persona && (
                                <p className="text-xs text-blue-600 mt-0.5">
                                  {chat.persona.persona_name}
                                </p>
                              )}
                            </div>
                          </div>
                        </button>
                        
                        {/* 삭제 버튼 */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteChat(chat.id);
                          }}
                          className="absolute top-1 right-1 p-1 opacity-0 group-hover:opacity-100 hover:bg-red-100 text-red-600 rounded transition-all"
                          title="채팅 삭제"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* 메인 채팅 영역 */}
        <div className="flex-1 flex flex-col">
          {selectedChat ? (
            <>
              {/* 채팅 헤더 */}
              <div className="bg-white border-b border-gray-200 p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Bot className="w-4 h-4 text-gray-800" />
                    <div>
                      <h2 className="text-sm font-semibold text-gray-800 truncate">{selectedChat.title}</h2>
                      <p className="text-xs text-gray-600 truncate">
                        {models.find(m => m.id === selectedChat.model_id)?.name || selectedChat.model_id}
                        {selectedChat.persona && ` • ${selectedChat.persona.persona_name}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => setShowSettings(!showSettings)}
                      className={`p-1.5 hover:bg-gray-100 rounded-lg transition-colors ${showSettings ? 'bg-gray-100' : ''}`}
                      title="설정"
                    >
                      <Settings className="w-3 h-3 text-gray-600" />
                    </button>
                    <button
                      onClick={() => onExpand(selectedChat?.id)}
                      className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                      title="전체 화면으로 확대"
                    >
                      <Maximize2 className="w-3 h-3 text-gray-600" />
                    </button>
                    <button
                      onClick={onClose}
                      className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      <X className="w-3 h-3 text-gray-600" />
                    </button>
                  </div>
                </div>
              </div>

              {/* 에러 메시지 */}
              {error && (
                <div className="bg-red-50 border-b border-red-200 p-2">
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="w-3 h-3 text-red-600" />
                    <p className="text-xs text-red-700">{error}</p>
                    <button
                      onClick={() => setError(null)}
                      className="ml-auto text-red-600 hover:text-red-800"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              )}

              {/* 메시지 영역 */}
              <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-gradient-to-b from-gray-50 to-white">
                {isLoading && messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-center">
                    <div>
                      <MessageCircle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                      <h3 className="text-sm font-medium text-gray-600 mb-1">새로운 대화를 시작하세요</h3>
                      <p className="text-xs text-gray-500">메시지를 입력하여 AI와 대화해보세요.</p>
                    </div>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.sender_type === 'USER' ? 'justify-end' : 'justify-start'} group mb-3`}
                    >
                      <div className={`max-w-[85%] ${message.sender_type === 'USER' ? 'ml-4' : 'mr-4'} relative`}>
                        {/* 사용자 메시지 */}
                        {message.sender_type === 'USER' ? (
                          <div className="bg-gradient-to-r from-gray-700 to-gray-800 text-white rounded-2xl rounded-br-md px-3 py-2 shadow-lg">
                            <p className="text-xs leading-relaxed whitespace-pre-wrap">
                              {message.content}
                            </p>
                            <div className="flex justify-end mt-1">
                              <span className="text-xs text-gray-300 opacity-75">
                                {formatMessageTime(message.created_at)}
                              </span>
                            </div>
                          </div>
                        ) : (
                          /* AI 메시지 */
                          <div className="bg-white rounded-2xl rounded-bl-md px-3 py-2 shadow-lg border border-gray-100">
                            <div className="flex items-start space-x-2 mb-1">
                              <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-1 rounded-full">
                                <Bot className="w-2.5 h-2.5 text-white" />
                              </div>
                              <div className="flex-1">
                                <p className="text-xs leading-relaxed whitespace-pre-wrap text-gray-800">
                                  {message.content}
                                </p>
                              </div>
                            </div>
                            
                            <div className="flex items-center justify-between mt-2 pt-1 border-t border-gray-100">
                              <span className="text-xs text-gray-400">
                                {formatMessageTime(message.created_at)}
                              </span>
                              
                              <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button
                                  onClick={() => handleMessageFeedback(message.id, 'LIKE')}
                                  className="p-1 hover:bg-green-50 text-green-600 rounded-full transition-colors"
                                  title="좋아요"
                                >
                                  <ThumbsUp className="w-2.5 h-2.5" />
                                </button>
                                <button
                                  onClick={() => handleMessageFeedback(message.id, 'DISLIKE')}
                                  className="p-1 hover:bg-red-50 text-red-600 rounded-full transition-colors"
                                  title="싫어요"
                                >
                                  <ThumbsDown className="w-2.5 h-2.5" />
                                </button>
                                <button 
                                  className="p-1 hover:bg-gray-50 text-gray-600 rounded-full transition-colors"
                                  title="복사"
                                  onClick={() => copyMessageToClipboard(message.content)}
                                >
                                  <Copy className="w-2.5 h-2.5" />
                                </button>
                              </div>
                            </div>
                            
                            {/* 비용 정보 (AI 메시지만) */}
                            {message.total_cost && (
                              <div className="text-xs text-gray-400 mt-1 bg-gray-50 rounded-lg px-2 py-1">
                                토큰: {message.prompt_tokens || 0} + {message.completion_tokens || 0} 
                                • 비용: ${message.total_cost.toFixed(6)}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] mr-4">
                      <div className="bg-gray-100 border border-gray-200 rounded-lg px-3 py-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Bot className="w-3 h-3 text-gray-600" />
                            <span className="text-xs text-gray-600">AI가 답변을 작성 중입니다</span>
                            <div className="flex space-x-1">
                              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                            </div>
                          </div>
                          <button
                            onClick={handleStopResponse}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50 p-1 rounded transition-colors"
                            title="응답 중지"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>

              {/* 메시지 입력 영역 */}
              <div className="bg-white border-t border-gray-200 p-3">
                {/* RAG 소스 표시 */}
                {selectedRAGSources.length > 0 && (
                  <div className="mb-2 flex flex-wrap gap-1">
                    {selectedRAGSources.map(sourceId => {
                      const source = ragSources.find(s => s.id === sourceId);
                      return source ? (
                        <span key={sourceId} className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
                          <Database className="w-2 h-2 mr-1" />
                          {source.name}
                        </span>
                      ) : null;
                    })}
                  </div>
                )}
                
                <div className="flex space-x-2">
                  <textarea
                    ref={messageInputRef}
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="메시지를 입력하세요..."
                    className="flex-1 resize-none border border-gray-300 rounded-lg p-2 text-xs focus:outline-none focus:ring-2 focus:ring-gray-500 focus:border-transparent"
                    rows={2}
                    disabled={isLoading || !selectedChat}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!newMessage.trim() || isLoading || !selectedChat}
                    className="px-3 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex-shrink-0 transition-colors"
                  >
                    <Send className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </>
          ) : (
            /* 채팅 선택 안내 */
            <div className="flex-1 flex items-center justify-center bg-gray-50">
              <div className="text-center">
                <MessageCircle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <h3 className="text-sm font-medium text-gray-600 mb-1">채팅을 선택해주세요</h3>
                <p className="text-xs text-gray-500 mb-3">새로운 대화를 시작하거나 기존 채팅을 선택하세요.</p>
                <button
                  onClick={handleCreateChat}
                  className="bg-gray-800 text-white px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors flex items-center space-x-2 mx-auto text-xs"
                >
                  <Plus className="w-3 h-3" />
                  <span>새 채팅 시작</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 설정 패널 - 오른쪽 사이드바 */}
        <div className={`bg-white border-l border-gray-200 flex flex-col transition-all duration-300 ${
          showSettings ? 'w-56' : 'w-0'
        } overflow-hidden`}>
            <div className="flex items-center justify-between p-3 border-b border-gray-200">
              <h3 className="text-sm font-semibold text-gray-800">설정</h3>
              <button
                onClick={() => setShowSettings(false)}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-3 h-3 text-gray-600" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-3 space-y-4">
              {/* 모델 선택 */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  <Brain className="w-3 h-3 inline mr-1" />
                  AI 모델
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  {models.map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.provider})
                    </option>
                  ))}
                </select>
              </div>
              
              {/* 페르소나 선택 */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  <User className="w-3 h-3 inline mr-1" />
                  페르소나
                </label>
                <select
                  value={selectedPersona || ''}
                  onChange={(e) => setSelectedPersona(e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  <option value="">기본 설정</option>
                  {personas.map(persona => (
                    <option key={persona.id} value={persona.id}>
                      {persona.persona_name}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* RAG 데이터 소스 선택 */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  <Database className="w-3 h-3 inline mr-1" />
                  데이터 소스
                </label>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {ragSources.map(source => (
                    <label key={source.id} className="flex items-center space-x-2 text-xs">
                      <input
                        type="checkbox"
                        checked={selectedRAGSources.includes(source.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedRAGSources([...selectedRAGSources, source.id]);
                          } else {
                            setSelectedRAGSources(selectedRAGSources.filter(id => id !== source.id));
                          }
                        }}
                        className="rounded"
                      />
                      <span className="truncate">{source.name}</span>
                      <span className="text-gray-400">({source.document_count})</span>
                    </label>
                  ))}
                </div>
                             </div>
             </div>
           </div>
       </div>
     </div>
   );
 };

export default MiniLLMChat; 