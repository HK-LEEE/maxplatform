import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageCircle, Plus, Search, Settings, User, 
  Send, ThumbsUp, ThumbsDown, Share, Bot,
  Database, Brain, Sparkles, Filter,
  ChevronLeft, ChevronRight, X, Copy,
  Loader2, AlertCircle, Check, Trash2, MoreHorizontal,
  Home, Bell, Maximize2, Minimize2
} from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { llmChatApi } from '../services/llmChatApi';
import {
  Chat, Message, Persona, LLMModel, RAGDataSource,
  ChatCreateRequest, MessageSendRequest, SenderType
} from '../types/llmChat';
import MessageInput from '../components/chat/MessageInput';

const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
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
  const [showSettings, setShowSettings] = useState(true);
  const [isWideChat, setIsWideChat] = useState(false);
  const [pendingUserMessage, setPendingUserMessage] = useState<Message | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [floatingMenuPosition, setFloatingMenuPosition] = useState({ top: 16, left: 64 });
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageInputRef = useRef<HTMLTextAreaElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // 초기 데이터 로드
  useEffect(() => {
    loadInitialData();
  }, []);

  // 메시지 스크롤
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 플로팅 메뉴 위치 업데이트
  useEffect(() => {
    const handleScroll = () => {
      if (messagesContainerRef.current && !sidebarOpen) {
        const scrollTop = messagesContainerRef.current.scrollTop;
        const containerHeight = messagesContainerRef.current.clientHeight;
        const scrollHeight = messagesContainerRef.current.scrollHeight;
        
        // 스크롤 비율 계산 (0~1)
        const scrollRatio = scrollTop / Math.max(scrollHeight - containerHeight, 1);
        
        // 메뉴 위치 계산 (최소 80px, 최대 화면 높이의 70%)
        const maxTop = window.innerHeight * 0.7;
        const newTop = Math.max(80, Math.min(80 + (scrollRatio * 200), maxTop));
        
        setFloatingMenuPosition({ top: newTop, left: 64 });
      }
    };

    const container = messagesContainerRef.current;
    if (container && !sidebarOpen) {
      container.addEventListener('scroll', handleScroll);
      // 초기 위치 설정
      handleScroll();
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [sidebarOpen]);

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
      if (modelsData.length > 0) {
        setSelectedModel(modelsData[0].id);
      }

      // URL 파라미터에서 chatId 확인하여 해당 채팅 선택
      const chatId = searchParams.get('chatId');
      if (chatId && chatsData.length > 0) {
        const targetChat = chatsData.find(chat => chat.id === chatId);
        if (targetChat) {
          await handleChatSelect(targetChat);
          return;
        }
      }
      
      // 특정 채팅이 없으면 첫 번째 채팅 선택
      if (chatsData.length > 0) {
        await handleChatSelect(chatsData[0]);
      }
      
    } catch (error) {
      console.error('초기 데이터 로드 실패:', error);
      setError('데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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
    if (!newMessage.trim() || !selectedChat) return;

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
    setPendingUserMessage(userMessageObj);
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
      
      // 채팅 목록 갱신 (업데이트 시간 기준 정렬)
      await loadInitialData();
      
    } catch (error: any) {
      if (error?.name === 'AbortError') {
        console.log('메시지 전송이 중단되었습니다.');
      } else {
        console.error('메시지 전송 실패:', error);
        setError('메시지 전송 중 오류가 발생했습니다.');
      }
    } finally {
      setIsTyping(false);
      setPendingUserMessage(null);
      setAbortController(null);
    }
  };

  const handleStopResponse = () => {
    if (abortController) {
      abortController.abort();
      setIsTyping(false);
      setPendingUserMessage(null);
      setAbortController(null);
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    if (!confirm('정말로 이 채팅을 삭제하시겠습니까? 삭제된 채팅은 복구할 수 없습니다.')) {
      return;
    }

    try {
      await llmChatApi.deleteChat(chatId);
      
      // 채팅 목록에서 제거
      setChats(prev => prev.filter(chat => chat.id !== chatId));
      
      // 현재 선택된 채팅이 삭제된 경우 초기화
      if (selectedChat?.id === chatId) {
        setSelectedChat(null);
        setMessages([]);
      }
      
    } catch (error) {
      console.error('채팅 삭제 실패:', error);
      setError('채팅 삭제 중 오류가 발생했습니다.');
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
      // 피드백 표시 업데이트는 UI 상태로 관리할 수 있음
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

  if (isLoading && chats.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-gray-600 mx-auto mb-4" />
          <p className="text-gray-600">채팅 서비스를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 메인 컨테이너 */}
      <div className="flex w-full">
        {/* 왼쪽 사이드바 */}
        <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen">

        {/* 사이드바 헤더 */}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          {sidebarOpen && (
            <div className="flex items-center space-x-2">
              <MessageCircle className="w-6 h-6 text-gray-800" />
              <h1 className="text-lg font-semibold text-gray-800">AI 채팅</h1>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
          >
            {sidebarOpen ? (
              <ChevronLeft className="w-4 h-4 text-gray-600" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-600" />
            )}
          </button>
        </div>

        {sidebarOpen && (
          <>
            {/* 새 채팅 버튼 */}
            <div className="p-4">
              <button
                onClick={handleCreateChat}
                className="w-full flex items-center justify-center space-x-2 bg-gray-800 text-white py-3 px-4 rounded-lg hover:bg-gray-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>새 채팅</span>
              </button>
            </div>

            {/* 채팅 목록 */}
            <div className="flex-1 overflow-y-auto">
              <div className="px-4 pb-4">
                <h3 className="text-sm font-medium text-gray-600 mb-2">최근 채팅</h3>
                <div className="space-y-2">
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
                        className="w-full text-left p-3 pr-10"
                      >
                        <div className="flex items-start space-x-3">
                          <MessageCircle className="w-4 h-4 text-gray-600 mt-0.5 flex-shrink-0" />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-gray-800 truncate">
                              {chat.title}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              {new Date(chat.updated_at).toLocaleDateString()}
                            </p>
                            {chat.persona && (
                              <p className="text-xs text-blue-600 mt-1">
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
                        className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 hover:bg-red-100 text-red-600 rounded transition-all"
                        title="채팅 삭제"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>


          </>
        )}
      </div>

      {/* 플로팅 메뉴 */}
      {!sidebarOpen && (
        <div 
          className="fixed z-50 flex flex-col gap-2 transition-all duration-200"
          style={{ 
            top: `${floatingMenuPosition.top}px`, 
            left: `${floatingMenuPosition.left}px` 
          }}
        >
          <button
            onClick={handleCreateChat}
            className="bg-blue-500 text-white p-3 rounded-full shadow-lg hover:bg-blue-600 transition-colors hover:scale-110"
            title="새 채팅"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* 메인 채팅 영역 */}
      <div className="flex-1 flex flex-col">
        {selectedChat ? (
          <>
            {/* 채팅 헤더 */}
            <div className="bg-white border-b border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Bot className="w-6 h-6 text-gray-800" />
                  <div>
                    <h2 className="text-lg font-semibold text-gray-800">{selectedChat.title}</h2>
                    <p className="text-sm text-gray-600">
                      {models.find(m => m.id === selectedChat.model_id)?.name || selectedChat.model_id}
                      {selectedChat.persona && ` • ${selectedChat.persona.persona_name}`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setIsWideChat(!isWideChat)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    title={isWideChat ? "채팅창 좁게" : "채팅창 넓게"}
                  >
                    {isWideChat ? (
                      <Minimize2 className="w-4 h-4 text-gray-600" />
                    ) : (
                      <Maximize2 className="w-4 h-4 text-gray-600" />
                    )}
                  </button>
                  <button
                    onClick={() => setShowSettings(!showSettings)}
                    className={`p-2 hover:bg-gray-100 rounded-lg transition-colors ${showSettings ? 'bg-gray-100' : ''}`}
                    title="설정"
                  >
                    <Settings className="w-4 h-4 text-gray-600" />
                  </button>
                  <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                    <Share className="w-4 h-4 text-gray-600" />
                  </button>
                  <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                    <Search className="w-4 h-4 text-gray-600" />
                  </button>
                </div>
              </div>
            </div>

            {/* 메시지 영역 */}
            <div
              ref={messagesContainerRef}
              className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-gray-50 to-white"
            >
              <div className={`${!isWideChat ? 'max-w-4xl mx-auto' : ''}`}>
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.sender_type === 'USER' ? 'justify-end' : 'justify-start'} group mb-6`}
                  >
                    <div className={`${isWideChat ? 'max-w-4xl' : 'max-w-2xl'} ${message.sender_type === 'USER' ? (isWideChat ? 'ml-16' : 'ml-8') : (isWideChat ? 'mr-16' : 'mr-8')} relative`}>
                    {/* 사용자 메시지 */}
                    {message.sender_type === 'USER' ? (
                      <div className="bg-gradient-to-r from-gray-700 to-gray-800 text-white rounded-2xl rounded-br-md px-6 py-4 shadow-lg">
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">
                          {message.content}
                        </p>
                        <div className="flex justify-end mt-2">
                          <span className="text-xs text-gray-300 opacity-75">
                            {formatMessageTime(message.created_at)}
                          </span>
                        </div>
                      </div>
                    ) : (
                      /* AI 메시지 */
                      <div className="bg-white rounded-2xl rounded-bl-md px-6 py-4 shadow-lg border border-gray-100">
                        <div className="flex items-start space-x-3 mb-2">
                          <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-2 rounded-full">
                            <Bot className="w-4 h-4 text-white" />
                          </div>
                          <div className="flex-1">
                            <p className="text-sm leading-relaxed whitespace-pre-wrap text-gray-800">
                              {message.content}
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-100">
                          <span className="text-xs text-gray-400">
                            {formatMessageTime(message.created_at)}
                          </span>
                          
                          <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => handleMessageFeedback(message.id, 'LIKE')}
                              className="p-2 hover:bg-green-50 text-green-600 rounded-full transition-colors"
                              title="좋아요"
                            >
                              <ThumbsUp className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleMessageFeedback(message.id, 'DISLIKE')}
                              className="p-2 hover:bg-red-50 text-red-600 rounded-full transition-colors"
                              title="싫어요"
                            >
                              <ThumbsDown className="w-4 h-4" />
                            </button>
                            <button 
                              className="p-2 hover:bg-gray-50 text-gray-600 rounded-full transition-colors"
                              title="복사"
                              onClick={() => navigator.clipboard.writeText(message.content)}
                            >
                              <Copy className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                        
                        {/* 비용 정보 (AI 메시지만) */}
                        {message.total_cost && (
                          <div className="text-xs text-gray-400 mt-2 bg-gray-50 rounded-lg px-3 py-1">
                            토큰: {message.prompt_tokens || 0} + {message.completion_tokens || 0} 
                            • 비용: ${message.total_cost.toFixed(6)}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
                {isTyping && (
                  <div className="flex justify-start">
                    <div className={`${isWideChat ? 'max-w-3xl mr-12' : 'max-w-2xl mr-8'}`}>
                      <div className="bg-gray-100 border border-gray-200 rounded-lg px-4 py-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Bot className="w-4 h-4 text-gray-600" />
                            <span className="text-sm text-gray-600">AI가 답변을 작성 중입니다</span>
                            <div className="flex space-x-1">
                              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                            </div>
                          </div>
                          <button
                            onClick={handleStopResponse}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50 p-1 rounded transition-colors"
                            title="응답 중지"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* 메시지 입력 영역 */}
            <div className="w-full">
              <MessageInput
                value={newMessage}
                onChange={setNewMessage}
                onSend={handleSendMessage}
                onStop={handleStopResponse}
                disabled={isLoading}
                isTyping={isTyping}
                ragSources={ragSources}
                selectedRAGSources={selectedRAGSources}
                onRAGSourcesChange={setSelectedRAGSources}
              />
            </div>
          </>
        ) : (
          /* 채팅 선택 안내 */
          <div className="flex-1 flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <MessageCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-600 mb-2">채팅을 선택해주세요</h3>
              <p className="text-gray-500 mb-6">새로운 대화를 시작하거나 기존 채팅을 선택하세요.</p>
              <button
                onClick={handleCreateChat}
                className="bg-gray-800 text-white px-6 py-3 rounded-lg hover:bg-gray-700 transition-colors flex items-center space-x-2 mx-auto"
              >
                <Plus className="w-4 h-4" />
                <span>새 채팅 시작</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 설정 패널 - 오른쪽 사이드바 */}
      {showSettings && (
        <div className="w-80 bg-white border-l border-gray-200 flex flex-col h-screen">
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800">설정</h3>
            <button
              onClick={() => setShowSettings(false)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-gray-600" />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-6">
            {/* 모델 선택 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Brain className="w-4 h-4 inline mr-1" />
                AI 모델
              </label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-gray-500"
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
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <User className="w-4 h-4 inline mr-1" />
                페르소나
              </label>
              <select
                value={selectedPersona || ''}
                onChange={(e) => setSelectedPersona(e.target.value ? parseInt(e.target.value) : null)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-gray-500"
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
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Database className="w-4 h-4 inline mr-1" />
                데이터 소스
              </label>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {ragSources.map(source => (
                  <label key={source.id} className="flex items-center space-x-2">
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
                      className="w-4 h-4 text-gray-600 rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">{source.name}</span>
                    <span className="text-xs text-gray-500">({source.document_count})</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>
        )}
      </div>

      {/* 에러 토스트 */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-100 border border-red-300 text-red-700 px-4 py-3 rounded-lg shadow-lg">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-2 text-red-500 hover:text-red-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatPage; 