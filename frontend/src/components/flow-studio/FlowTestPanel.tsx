import React, { useState, useRef, useEffect } from 'react';
import {
  X,
  Play,
  Send,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  MessageSquare,
  Bot,
  User,
  Zap,
  ArrowRight,
  Copy,
  Download,
  Settings
} from 'lucide-react';
import toast from 'react-hot-toast';

interface FlowTestPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onExecute: (input: string, stream: boolean) => Promise<any>;
  isExecuting: boolean;
  nodes: any[];
  edges: any[];
}

interface ExecutionStep {
  id: string;
  nodeId: string;
  nodeName: string;
  nodeType: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  input?: any;
  output?: any;
  duration?: number;
  timestamp: Date;
  startTime?: Date;
  endTime?: Date;
}

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  executionSteps?: ExecutionStep[];
}

const FlowTestPanel: React.FC<FlowTestPanelProps> = ({
  isOpen,
  onClose,
  onExecute,
  isExecuting,
  nodes,
  edges
}) => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [executionSteps, setExecutionSteps] = useState<ExecutionStep[]>([]);
  const [streamMode, setStreamMode] = useState(true);
  const [showSteps, setShowSteps] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages, executionSteps]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const getNodeTypeIcon = (nodeType: string) => {
    switch (nodeType) {
      case 'input':
        return <MessageSquare className="h-4 w-4" />;
      case 'model':
        return <Bot className="h-4 w-4" />;
      case 'output':
        return <Zap className="h-4 w-4" />;
      default:
        return <CheckCircle className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'text-gray-400';
      case 'running':
        return 'text-blue-500';
      case 'completed':
        return 'text-green-500';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4" />;
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4" />;
      case 'error':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const formatDuration = (startTime?: Date, endTime?: Date, duration?: number) => {
    // duration이 있으면 우선 사용
    if (duration !== undefined) {
      if (duration < 1000) {
        return `${duration}ms`;
      } else {
        return `${(duration / 1000).toFixed(1)}s`;
      }
    }
    
    // duration이 없으면 기존 로직 사용
    if (!startTime) return '';
    if (!endTime) return '실행중...';
    
    const calculatedDuration = endTime.getTime() - startTime.getTime();
    if (calculatedDuration < 1000) {
      return `${calculatedDuration}ms`;
    } else {
      return `${(calculatedDuration / 1000).toFixed(1)}s`;
    }
  };

  const handleExecute = async () => {
    if (!input.trim() || isExecuting) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    
    // 실행 단계 초기화
    const initialSteps: ExecutionStep[] = nodes.map((node, index) => ({
      id: `step-${node.id}`,
      nodeId: node.id,
      nodeName: node.data?.title || node.data?.name || `Node ${index + 1}`,
      nodeType: node.data?.category || 'unknown',
      status: 'pending',
      timestamp: new Date()
    }));
    
    setExecutionSteps(initialSteps);
    const userInput = input.trim();
    setInput('');

    try {
      if (streamMode) {
        // 스트리밍 모드 처리
        await handleStreamingExecution(userInput);
      } else {
        // 일반 모드 처리 - 단계별 시간 추적
        const startTime = new Date();
        
        // 첫 번째 단계 시작
        if (initialSteps.length > 0) {
          setExecutionSteps(prev => prev.map((step, index) => 
            index === 0 
              ? { ...step, status: 'running', startTime: new Date() }
              : step
          ));
        }
        
        const result = await onExecute(userInput, false);
        
        // 모든 단계 완료 처리
        const endTime = new Date();
        setExecutionSteps(prev => prev.map((step, index) => ({
          ...step,
          status: 'completed',
          startTime: step.startTime || new Date(startTime.getTime() + (index * 100)),
          endTime: new Date(startTime.getTime() + ((index + 1) * 500))
        })));
        
        // 결과에서 실제 콘텐츠 추출
        let content = '';
        if (typeof result === 'string') {
          content = result;
        } else if (result && typeof result === 'object') {
          // 백엔드 응답에서 실제 콘텐츠 추출
          if (result.result && typeof result.result === 'object' && result.result.content) {
            content = result.result.content;
          } else if (result.result) {
            content = typeof result.result === 'string' ? result.result : JSON.stringify(result.result, null, 2);
          } else {
            content = JSON.stringify(result, null, 2);
          }
        }
        
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: content,
          timestamp: new Date(),
          executionSteps: executionSteps.map(step => ({ ...step, status: 'completed' }))
        };

        setMessages(prev => [...prev, assistantMessage]);
         
        // 스크롤을 맨 아래로 이동
        setTimeout(scrollToBottom, 0);
      }
      
    } catch (error) {
      console.error('Execution error:', error);
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'system',
        content: `실행 중 오류가 발생했습니다: ${error instanceof Error ? error.message : '알 수 없는 오류'}`,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
      setExecutionSteps(prev => prev.map(step => ({ ...step, status: 'error', endTime: new Date() })));
    }
  };

  const handleStreamingExecution = async (userInput: string) => {
    // 임시 AI 메시지 생성 (스트리밍 중 업데이트됨)
    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      type: 'assistant',
      content: '',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      // 스트리밍 요청
      const response = await fetch('/api/llmops/test-flow', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          flow_data: {
            nodes: nodes.map((node: any) => ({
              id: node.id,
              type: node.type,
              position: node.position,
              data: node.data,
            })),
            edges: edges.map((edge: any) => ({
              id: edge.id,
              source: edge.source,
              target: edge.target,
              sourceHandle: edge.sourceHandle,
              targetHandle: edge.targetHandle,
            })),
          },
          input_data: { text: userInput },
          stream: true,
          parameters: {}
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'steps') {
                  // 백엔드에서 전송된 단계 정보로 실행 단계 초기화
                  const backendSteps: ExecutionStep[] = data.steps.map((step: any) => ({
                    id: `step-${step.node_id}`,
                    nodeId: step.node_id,
                    nodeName: step.node_name,
                    nodeType: step.node_type,
                    status: 'pending',
                    timestamp: new Date()
                  }));
                  setExecutionSteps(backendSteps);
                  
                } else if (data.type === 'step_start') {
                  // 특정 단계 시작
                  const step = data.step;
                  setExecutionSteps(prev => prev.map(s => 
                    s.nodeId === step.node_id 
                      ? { 
                          ...s, 
                          status: 'running', 
                          startTime: step.start_time ? new Date(step.start_time) : new Date()
                        }
                      : s
                  ));
                  
                } else if (data.type === 'step_complete') {
                  // 특정 단계 완료
                  const step = data.step;
                  setExecutionSteps(prev => prev.map(s => 
                    s.nodeId === step.node_id 
                      ? { 
                          ...s, 
                          status: 'completed', 
                          endTime: step.end_time ? new Date(step.end_time) : new Date(),
                          duration: step.duration_ms || undefined
                        }
                      : s
                  ));
                  
                } else if (data.type === 'chunk' && data.data) {
                  // 실제 콘텐츠 추출
                  let chunkContent = '';
                  if (typeof data.data === 'string') {
                    chunkContent = data.data;
                  } else if (data.data && data.data.content) {
                    chunkContent = data.data.content;
                  }
                  
                  if (chunkContent) {
                    accumulatedContent += chunkContent;
                    
                    // 메시지 업데이트
                    setMessages(prev => prev.map(msg => 
                      msg.id === assistantMessageId 
                        ? { ...msg, content: accumulatedContent }
                        : msg
                    ));
                     
                    // 스크롤을 맨 아래로 이동
                    setTimeout(scrollToBottom, 0);
                  }
                } else if (data.type === 'complete') {
                  // 스트리밍 완료 - 모든 단계 완료 처리
                  setExecutionSteps(prev => prev.map(step => ({
                    ...step,
                    status: 'completed',
                    endTime: step.endTime || new Date()
                  })));
                  break;
                } else if (data.type === 'error') {
                  throw new Error(data.error || '스트리밍 중 오류 발생');
                }
              } catch (parseError) {
                console.warn('스트리밍 데이터 파싱 오류:', parseError);
              }
            }
          }
        }
      }

    } catch (error) {
      console.error('스트리밍 실행 오류:', error);
      
      // 오류 메시지로 업데이트
      setMessages(prev => prev.map(msg => 
        msg.id === assistantMessageId 
          ? { 
              ...msg, 
              type: 'system' as const,
              content: `스트리밍 실행 중 오류가 발생했습니다: ${error instanceof Error ? error.message : '알 수 없는 오류'}`
            }
          : msg
      ));
      
      setExecutionSteps(prev => prev.map(step => ({ ...step, status: 'error', endTime: new Date() })));
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleExecute();
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('클립보드에 복사되었습니다');
  };

  const clearMessages = () => {
    setMessages([]);
    setExecutionSteps([]);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-[480px] bg-white border-l border-gray-200 shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-in-out">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Play className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Flow Test</h2>
            <p className="text-sm text-gray-500">실시간 플로우 테스트</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowSteps(!showSteps)}
            className={`p-2 rounded-lg transition-colors ${
              showSteps ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
            }`}
            title="실행 단계 표시/숨김"
          >
            <Settings className="h-4 w-4" />
          </button>
          
          <button
            onClick={clearMessages}
            className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
            title="대화 기록 지우기"
          >
            <Download className="h-4 w-4" />
          </button>
          
          <button
            onClick={onClose}
            className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Settings Bar */}
      <div className="p-3 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={streamMode}
                onChange={(e) => setStreamMode(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">스트리밍 모드</span>
            </label>
          </div>
          
          <div className="text-xs text-gray-500">
            {nodes.length}개 노드, {edges.length}개 연결
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="p-4 bg-blue-50 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              <MessageSquare className="h-8 w-8 text-blue-500" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">플로우 테스트 시작</h3>
            <p className="text-gray-500 text-sm">
              아래 입력창에 메시지를 입력하여<br />
              플로우를 테스트해보세요.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className="space-y-3">
              {/* Message */}
              <div className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] ${
                  message.type === 'user' 
                    ? 'bg-blue-500 text-white' 
                    : message.type === 'system'
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : 'bg-gray-100 text-gray-900'
                } rounded-2xl px-4 py-3 relative group`}>
                  
                  {/* Message Header */}
                  <div className="flex items-center space-x-2 mb-2">
                    {message.type === 'user' ? (
                      <User className="h-4 w-4" />
                    ) : message.type === 'system' ? (
                      <AlertCircle className="h-4 w-4" />
                    ) : (
                      <Bot className="h-4 w-4" />
                    )}
                    <span className="text-xs font-medium">
                      {message.type === 'user' ? '사용자' : message.type === 'system' ? '시스템' : 'AI'}
                    </span>
                    <span className="text-xs opacity-70">
                      {message.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                  
                  {/* Message Content */}
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {message.content}
                  </div>
                  
                  {/* Copy Button */}
                  <button
                    onClick={() => copyToClipboard(message.content)}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-black/10"
                  >
                    <Copy className="h-3 w-3" />
                  </button>
                </div>
              </div>

              {/* Execution Steps */}
              {showSteps && message.type === 'user' && executionSteps.length > 0 && (
                <div className="ml-4 space-y-2">
                  <div className="text-xs font-medium text-gray-500 mb-3">실행 단계</div>
                  {executionSteps.map((step, index) => (
                    <div key={step.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-2 flex-1">
                        <div className={`${getStatusColor(step.status)}`}>
                          {getStatusIcon(step.status)}
                        </div>
                        <div className={`${getStatusColor(step.nodeType)}`}>
                          {getNodeTypeIcon(step.nodeType)}
                        </div>
                        <span className="text-sm font-medium text-gray-900">
                          {step.nodeName}
                        </span>
                        <span className="text-xs text-gray-500">
                          ({step.nodeType})
                        </span>
                      </div>
                      
                      {index < executionSteps.length - 1 && (
                        <ArrowRight className="h-3 w-3 text-gray-400" />
                      )}
                      
                      <div className="flex items-center space-x-2">
                        <div className={`text-xs font-medium ${getStatusColor(step.status)}`}>
                          {step.status === 'pending' && '대기중'}
                          {step.status === 'running' && '실행중'}
                          {step.status === 'completed' && '완료'}
                          {step.status === 'error' && '오류'}
                        </div>
                        
                        {/* 실행 시간 표시 */}
                        {(step.startTime || step.endTime || step.duration) && (
                          <div className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
                            <Clock className="h-3 w-3 inline mr-1" />
                            {formatDuration(step.startTime, step.endTime, step.duration)}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <div className="flex space-x-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="플로우를 테스트할 메시지를 입력하세요..."
              className="w-full px-4 py-3 border border-gray-300 rounded-xl resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              rows={2}
              disabled={isExecuting}
            />
            
            {/* Character Count */}
            <div className="absolute bottom-2 right-2 text-xs text-gray-400">
              {input.length}/1000
            </div>
          </div>
          
          <button
            onClick={handleExecute}
            disabled={!input.trim() || isExecuting}
            className={`px-4 py-3 rounded-xl flex items-center space-x-2 transition-all ${
              !input.trim() || isExecuting
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600 shadow-lg hover:shadow-xl'
            }`}
          >
            {isExecuting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
        
        {/* Quick Actions */}
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
          <div className="flex space-x-2">
            <button
              onClick={() => setInput('안녕하세요! 테스트 메시지입니다.')}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors"
            >
              샘플 메시지
            </button>
            <button
              onClick={() => setInput('이 플로우의 기능을 설명해주세요.')}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors"
            >
              기능 설명
            </button>
          </div>
          
          <div className="text-xs text-gray-500">
            Enter로 전송, Shift+Enter로 줄바꿈
          </div>
        </div>
      </div>
    </div>
  );
};

export default FlowTestPanel; 
