import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Settings, Eye, EyeOff, ChevronDown, ChevronUp, Copy, Trash2, MoreVertical, MessageSquare, FileText, Cpu, Database, Search, Bot, Cloud, Server, Wand2, Play } from 'lucide-react';
import PromptTemplateModal from './flow-studio/PromptTemplateModal';
import TestResultModal from './flow-studio/TestResultModal';
import { chromaDbApi, ChromaCollection } from '../services/chromaDbApi';
import { ollamaApi, OllamaModel } from '../services/ollamaApi';
import { useAuth } from '../contexts/AuthContext';

interface NodeFieldConfig {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'slider' | 'toggle' | 'password' | 'number';
  value?: any;
  placeholder?: string;
  options?: Array<{ value: string; label: string }>;
  min?: number;
  max?: number;
  step?: number;
  rows?: number;
  required?: boolean;
  sensitive?: boolean;
}

interface NodePort {
  id: string;
  name: string;
  type: string; // 더 유연한 타입으로 변경
  required?: boolean;
}

export interface FlowStudioNodeData {
  id: string;
  type: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  category: 'input' | 'prompt' | 'model' | 'output' | 'rag';
  inputs: NodePort[];
  outputs: NodePort[];
  fields: NodeFieldConfig[];
  color: string;
  fieldValues?: Record<string, any>; // 사용자가 입력한 필드 값들을 저장
  [key: string]: any; // Add index signature for React Flow compatibility
}

// React Flow 호환 타입 정의
interface FlowStudioNodeProps extends Partial<NodeProps> {
  id?: string; // React Flow에서 전달되는 실제 노드 ID
  data: FlowStudioNodeData;
  isConnectable?: boolean;
  selected?: boolean;
  onDelete?: () => void;
  onCopy?: () => void;
  onDataChange?: (nodeId: string, fieldName: string, value: any) => void;
}

const FlowStudioNode: React.FC<FlowStudioNodeProps> = ({ 
  id, // React Flow에서 전달되는 실제 노드 ID
  data, 
  isConnectable = true, 
  selected = false,
  onDelete,
  onCopy,
  onDataChange
}) => {
  const [showSensitiveFields, setShowSensitiveFields] = useState<Record<string, boolean>>({});
  const [showSettingsMenu, setShowSettingsMenu] = useState(false);
  const [testValue, setTestValue] = useState(''); // 테스트용 로컬 상태
  const [showTemplateModal, setShowTemplateModal] = useState(false); // Template Modal 상태
  const [showTestResultModal, setShowTestResultModal] = useState(false); // Test Result Modal 상태
  const [chromaCollections, setChromaCollections] = useState<ChromaCollection[]>([]);
  const [loadingCollections, setLoadingCollections] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [loadingOllamaModels, setLoadingOllamaModels] = useState(false);
  const [ollamaConnectionError, setOllamaConnectionError] = useState<string>('');
  const settingsMenuRef = useRef<HTMLDivElement>(null);

  // 실제 노드 ID 사용 (React Flow에서 전달되는 id 우선, 없으면 data.id 사용)
  const nodeId = id || data.id;

  // AuthContext를 사용하여 실제 사용자 정보를 가져옴
  const { user, isLoading = true } = useAuth();
  
  // 디버깅: 사용자 정보 상태 로그
  useEffect(() => {
    console.log('👤 Auth 상태:', { user: !!user, isLoading, userId: user?.id });
  }, [user, isLoading]);

  // RAG Collections 로드 (FlowStudio용)
  const loadChromaCollections = useCallback(async () => {
    console.log('🔄 loadChromaCollections 호출됨', { 
      type: data.type, 
      user: !!user, 
      isLoading,
      token: !!localStorage.getItem('token')
    });
    
    if (data.type !== 'RAGChroma') {
      console.log('❌ RAG 컴포넌트가 아님:', data.type);
      return;
    }
    
    // 사용자 정보가 있으면 바로 진행, 없으면 토큰으로 확인
    if (!user) {
      const token = localStorage.getItem('token');
      if (!token) {
        console.log('❌ 토큰이 없음 - 로그인이 필요합니다');
        return;
      }
      
      // 로딩 중이면 잠시 대기 (사용자 정보가 없을 때만)
      if (isLoading) {
        console.log('⏳ 사용자 정보 로딩 중, 잠시 대기');
        return;
      }
      
      console.log('⚠️ 사용자 정보는 없지만 토큰이 있음 - API 호출 시도');
    } else {
      console.log('✅ 사용자 정보 확인됨 - API 호출 진행');
    }
    
    console.log('🚀 RAG Collections API 호출 시작');
    setLoadingCollections(true);
    
    try {
      // FlowStudio용 RAG Collections API 호출
      const token = localStorage.getItem('token');
      console.log('🔑 토큰 확인:', !!token);
      
      // axios 인스턴스를 사용해서 자동으로 헤더가 설정되도록 함
      const api = (await import('../services/api')).default;
      const response = await api.get('/llmops/rag-collections');
      
      console.log('📡 API 응답:', { status: response.status, data: response.data });
      
      const responseData = response.data;
      console.log('📄 API 응답 데이터:', responseData);
      
      // API 응답을 ChromaCollection 형태로 변환
      const collections: ChromaCollection[] = responseData.collections.map((collection: any) => ({
        id: collection.value,
        name: collection.label,
        description: collection.description,
        document_count: collection.document_count,
        owner_type: collection.owner_type,
        owner_id: collection.owner_id,
        is_active: collection.is_active
      }));
      
      console.log('✅ Collections 변환 완료:', collections);
      setChromaCollections(collections);
    } catch (error) {
      console.error('💥 RAG Collections 로드 실패:', error);
      setChromaCollections([]);
    } finally {
      setLoadingCollections(false);
      console.log('🏁 RAG Collections 로드 완료');
    }
  }, [data.type, user, isLoading]);

  // Ollama Models 로드
  const loadOllamaModels = useCallback(async (baseUrl: string) => {
    if (data.type !== 'Ollama' || !baseUrl) return;
    
    setLoadingOllamaModels(true);
    setOllamaConnectionError('');
    
    try {
      const models = await ollamaApi.getModels(baseUrl);
      setOllamaModels(models);
      
      // 현재 선택된 모델이 로드된 모델 목록에 없는 경우 경고 표시
      const currentModel = data.fieldValues?.model;
      if (currentModel && !models.find(m => m.name === currentModel)) {
        setOllamaConnectionError(`선택된 모델 '${currentModel}'이 서버에서 찾을 수 없습니다.`);
      }
    } catch (error) {
      console.error('Failed to load Ollama models:', error);
      setOllamaModels([]);
      setOllamaConnectionError('Ollama 서버에 연결할 수 없습니다. URL을 확인해주세요.');
    } finally {
      setLoadingOllamaModels(false);
    }
  }, [data.type, data.fieldValues?.model]);

  // RAG 컴포넌트일 때 Collections 로드
  useEffect(() => {
    console.log('🎯 useEffect 트리거됨:', { 
      type: data.type, 
      isRAG: data.type === 'RAGChroma',
      user: !!user,
      isLoading
    });
    if (data.type === 'RAGChroma') {
      console.log('✅ RAG 컴포넌트 감지, Collections 로드 시작');
      loadChromaCollections();
    }
  }, [data.type, loadChromaCollections, user, isLoading]);

  // Ollama 컴포넌트일 때 base_url 변경 시 모델 로드
  useEffect(() => {
    if (data.type === 'Ollama') {
      const baseUrl = data.fieldValues?.base_url || 'http://localhost:11434';
      loadOllamaModels(baseUrl);
    }
  }, [data.type, data.fieldValues?.base_url, loadOllamaModels]);

  const handleFieldChange = useCallback((fieldName: string, value: any) => {
    // 즉시 부모에게 변경사항 알림 (debounce 없음)
    onDataChange?.(nodeId, fieldName, value);
    
    // Ollama 노드에서 base_url이 변경된 경우 모델 목록 다시 로드
    if (data.type === 'Ollama' && fieldName === 'base_url' && value) {
      // 약간의 지연을 두고 모델 로드 (URL 입력 완료 후)
      setTimeout(() => {
        loadOllamaModels(value);
      }, 500);
    }
  }, [nodeId, onDataChange, data.type, loadOllamaModels]);

  const toggleSensitiveField = useCallback((fieldName: string) => {
    setShowSensitiveFields(prev => ({
      ...prev,
      [fieldName]: !prev[fieldName]
    }));
  }, []);

  // 설정 메뉴 외부 클릭 감지
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (settingsMenuRef.current && !settingsMenuRef.current.contains(event.target as Node)) {
        setShowSettingsMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSettingsClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setShowSettingsMenu(!showSettingsMenu);
  }, [showSettingsMenu]);

  const handleDeleteClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setShowSettingsMenu(false);
    onDelete?.();
  }, [onDelete]);

  const handleCopyClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setShowSettingsMenu(false);
    onCopy?.();
  }, [onCopy]);

  const renderField = (field: NodeFieldConfig) => {
    // data.fieldValues에서 직접 값을 가져옴
    const value = data.fieldValues?.[field.name] ?? field.value ?? '';
    const showSensitive = showSensitiveFields[field.name];
    
    // 안정적인 key 생성
    const fieldKey = `field-${field.name}`;

    switch (field.type) {
      case 'text':
        return (
          <input
            key={fieldKey}
            type="text"
            value={value}
            onChange={(e) => {
              handleFieldChange(field.name, e.target.value);
            }}
            placeholder={field.placeholder}
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
          />
        );

      case 'password':
        return (
          <div key={fieldKey} className="relative">
            <input
              type={showSensitive ? 'text' : 'password'}
              value={value}
              onChange={(e) => {
                handleFieldChange(field.name, e.target.value);
              }}
              placeholder={field.placeholder}
              className="w-full px-2 py-1 pr-8 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
            />
            <button
              onClick={() => toggleSensitiveField(field.name)}
              className="absolute right-2 top-1 p-0.5 text-gray-400 hover:text-gray-600"
            >
              {showSensitive ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
            </button>
          </div>
        );

      case 'textarea':
        return (
          <textarea
            key={fieldKey}
            value={value}
            onChange={(e) => {
              handleFieldChange(field.name, e.target.value);
            }}
            placeholder={field.placeholder}
            rows={field.rows || 3}
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded resize-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
          />
        );

      case 'select':
         // RAG Collection Name 필드의 경우 동적으로 로드된 Collections 사용
        if (data.type === 'RAGChroma' && field.name === 'collection_name') {
          const collectionOptions = chromaCollections.map(collection => ({
            value: collection.id, // Collection ID (실제 Chroma collection name)
            label: collection.name // Collection 표시명
          }));

          return (
            <div key={fieldKey}>
              <select
                value={value || ''}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
                disabled={loadingCollections}
              >
                <option value="">
                  {loadingCollections ? 'Collection 로딩 중...' : 'Collection을 선택하세요'}
                </option>
                {collectionOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {chromaCollections.length === 0 && !loadingCollections && (
                <div className="space-y-1 mt-1">
                  <p className="text-xs text-gray-500">
                    사용 가능한 Collection이 없습니다.
                  </p>
                  <a 
                    href="/rag-datasource" 
                    className="text-xs text-blue-600 hover:text-blue-800 underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    RAG 데이터소스 생성하기
                  </a>
                </div>
              )}
                             {/* Collection 새로고침 버튼 */}
               <button
                 onClick={() => {
                   console.log('🔄 새로고침 버튼 클릭됨');
                   loadChromaCollections();
                 }}
                 className="text-xs text-blue-600 hover:text-blue-800 mt-1 underline"
                 disabled={loadingCollections}
               >
                 {loadingCollections ? '로딩 중...' : 'Collection 목록 새로고침'}
               </button>
            </div>
          );
        }

        // Ollama Model Name 필드의 경우 동적으로 로드된 Models 사용
        if (data.type === 'Ollama' && field.name === 'model') {
          const modelOptions = ollamaModels.map(model => ({
            value: model.name,
            label: ollamaApi.formatModelName(model.name)
          }));

          const currentModel = value || '';
          const isCurrentModelAvailable = ollamaModels.find(m => m.name === currentModel);

          return (
            <div key={fieldKey}>
              <select
                value={currentModel}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
                className={`w-full px-2 py-1 text-sm border rounded focus:ring-1 focus:ring-blue-400 focus:border-blue-400 ${
                  ollamaConnectionError ? 'border-red-300 bg-red-50' : 'border-gray-300'
                }`}
                disabled={loadingOllamaModels}
              >
                <option value="">
                  {loadingOllamaModels ? '모델 로딩 중...' : '모델을 선택하세요'}
                </option>
                {modelOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              
              {/* 연결 오류 또는 모델 불일치 경고 */}
              {ollamaConnectionError && (
                <p className="text-xs text-red-600 mt-1 flex items-center">
                  <span className="mr-1">⚠️</span>
                  {ollamaConnectionError}
                </p>
              )}
              
              {/* 저장된 모델이 서버에 없는 경우 경고 */}
              {currentModel && !isCurrentModelAvailable && !loadingOllamaModels && !ollamaConnectionError && (
                <p className="text-xs text-orange-600 mt-1 flex items-center">
                  <span className="mr-1">⚠️</span>
                  선택된 모델 '{currentModel}'이 서버에서 찾을 수 없습니다. 다른 모델을 선택해주세요.
                </p>
              )}
              
              {/* 사용 가능한 모델이 없는 경우 */}
              {ollamaModels.length === 0 && !loadingOllamaModels && !ollamaConnectionError && (
                <p className="text-xs text-gray-500 mt-1">
                  사용 가능한 모델이 없습니다. Ollama 서버에 모델을 설치해주세요.
                </p>
              )}
              
              {/* 모델 새로고침 버튼 */}
              <button
                onClick={() => {
                  const baseUrl = data.fieldValues?.base_url || 'http://localhost:11434';
                  loadOllamaModels(baseUrl);
                }}
                className="text-xs text-blue-600 hover:text-blue-800 mt-1 underline"
                disabled={loadingOllamaModels}
              >
                {loadingOllamaModels ? '로딩 중...' : '모델 목록 새로고침'}
              </button>
            </div>
          );
        }

        // 일반 select 필드
        return (
          <select
            key={fieldKey}
            value={value || ''}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
          >
            {field.options?.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );

      case 'slider':
        return (
          <div key={fieldKey} className="space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">Precise</span>
              <span className="text-sm font-mono">{value || field.min || 0}</span>
              <span className="text-xs text-gray-500">Wild</span>
            </div>
            <input
              type="range"
              min={field.min || 0}
              max={field.max || 1}
              step={field.step || 0.1}
              value={value || field.min || 0}
              onChange={(e) => handleFieldChange(field.name, parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider-pink"
            />
          </div>
        );

      case 'toggle':
        return (
          <label key={fieldKey} className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={value || false}
              onChange={(e) => handleFieldChange(field.name, e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        );

      case 'number':
        return (
          <input
            key={fieldKey}
            type="number"
            value={value || ''}
            onChange={(e) => handleFieldChange(field.name, parseFloat(e.target.value) || 0)}
            placeholder={field.placeholder}
            min={field.min}
            max={field.max}
            step={field.step}
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
          />
        );

      default:
        return null;
    }
  };

  if (!data) return null;

  // 아이콘 렌더링 함수
  const renderIcon = () => {
    if (typeof data.icon === 'string') {
      return <span className="text-white">{data.icon}</span>;
    }
    
    if (React.isValidElement(data.icon)) {
      return data.icon;
    }
    
    // 카테고리별 기본 아이콘
    switch (data.category) {
      case 'input':
        return <MessageSquare className="h-4 w-4 text-white" />;
      case 'prompt':
        return <FileText className="h-4 w-4 text-white" />;
      case 'model':
        return <Bot className="h-4 w-4 text-white" />;
      case 'output':
        return <Database className="h-4 w-4 text-white" />;
      case 'rag':
        return <Search className="h-4 w-4 text-white" />;
      default:
        return <Settings className="h-4 w-4 text-white" />;
    }
  };

  return (
    <div className={`bg-white rounded-lg border-2 shadow-lg min-w-[280px] max-w-[320px] flow-studio-node ${
      selected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-200'
    }`}>
      {/* Node Header */}
      <div className={`flex items-center justify-between p-3 border-b border-gray-200 ${data.color}`}>
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 flex items-center justify-center">
            {renderIcon()}
          </div>
          <span className="font-medium text-white text-sm">{data.title}</span>
        </div>
        
        {/* Settings Menu */}
        <div className="relative flex items-center space-x-1" ref={settingsMenuRef}>
          {/* Test Result Button */}
          <button
            onClick={() => setShowTestResultModal(true)}
            className="text-white opacity-75 hover:opacity-100 p-1 rounded transition-opacity"
            title="테스트 결과 보기"
          >
            <Play className="h-4 w-4" />
          </button>
          
          <button
            onClick={handleSettingsClick}
            className="text-white opacity-75 hover:opacity-100 p-1 rounded transition-opacity"
          >
            <MoreVertical className="h-4 w-4" />
          </button>
          
          {showSettingsMenu && (
            <div className="absolute right-0 top-8 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50 min-w-[120px]">
              <button
                onClick={handleCopyClick}
                className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
              >
                <Copy className="h-3 w-3" />
                <span>복사</span>
              </button>
              <button
                onClick={handleDeleteClick}
                className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
              >
                <Trash2 className="h-3 w-3" />
                <span>삭제</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Node Body */}
      <div className="p-3 space-y-3 relative">
        <p className="text-xs text-gray-600 mb-3">{data.description}</p>
        
        {/* Input Section - 위쪽에 배치 */}
        {data?.inputs && data.inputs.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-gray-700 mb-2">입력</div>
            {data.inputs.map((input: any, index: number) => {
              const field = data?.fields?.find((f: any) => f.name === input.id);
              const getPortColor = (type: string) => {
                switch (type) {
                  case 'text': return '#3b82f6'; // 파란색
                  case 'prompt': return '#10b981'; // 초록색
                  case 'response': return '#8b5cf6'; // 보라색
                  case 'data': return '#f59e0b'; // 주황색
                  default: return '#6b7280'; // 회색
                }
              };
              
              return (
                <div key={input.id} className="relative">
                  {/* Input Handle과 Label을 한 줄에 배치 */}
                  <div className="flex items-center mb-1 relative">
                    {/* Input Handle - 라벨 바로 옆에 위치 */}
                    <Handle
                      type="target"
                      position={Position.Left}
                      id={input.id}
                      style={{
                        position: 'absolute',
                        left: -8,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        border: `2px solid ${getPortColor(input.type)}`,
                        background: getPortColor(input.type),
                        zIndex: 10,
                        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                      }}
                      isConnectable={isConnectable}
                    />
                    
                    {/* Port Label */}
                    <div className="flex items-center ml-4">
                      <span className="text-xs text-gray-600 font-medium">{input.name}</span>
                      {input.required && <span className="text-red-500 ml-1">*</span>}
                    </div>
                  </div>
                  
                  {/* Field Input */}
                  {field && (
                    <div className="ml-6 mb-2">
                      {renderField(field)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Standalone Fields (fields without corresponding inputs) */}
        {data.fields
          .filter(field => !data.inputs.find(input => input.id === field.name))
          .map(field => (
            <div key={field.name} className="mt-3">
              <div className="flex items-center justify-between mb-1">
                <label className="flex items-center space-x-2 text-xs font-medium text-gray-700">
                  <span>{field.label}</span>
                  {field.required && <span className="text-red-500">*</span>}
                </label>
                
                {/* Template Generator Button for Prompt Component */}
                {data.type === 'Prompt' && field.name === 'template' && (
                  <button
                    onClick={() => setShowTemplateModal(true)}
                    className="flex items-center space-x-1 px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors"
                  >
                    <Wand2 className="h-3 w-3" />
                    <span>생성기</span>
                  </button>
                )}
              </div>
              {renderField(field)}
            </div>
          ))
        }

        {/* Output Section - 아래쪽에 배치 */}
        {data.outputs && data.outputs.length > 0 && (
          <div className="space-y-2 mt-4">
            <div className="text-xs font-semibold text-gray-700 mb-2">출력</div>
            {data.outputs.map((output, index) => {
              const getPortColor = (type: string) => {
                switch (type) {
                  case 'text': return '#3b82f6'; // 파란색
                  case 'prompt': return '#10b981'; // 초록색
                  case 'response': return '#8b5cf6'; // 보라색
                  case 'data': return '#f59e0b'; // 주황색
                  default: return '#6b7280'; // 회색
                }
              };
              
              return (
                <div key={output.id} className="relative">
                  {/* Output Handle과 Label을 한 줄에 배치 */}
                  <div className="flex items-center justify-end mb-1 relative">
                    {/* Port Label */}
                    <div className="flex items-center mr-4">
                      <span className="text-xs text-gray-600 font-medium mr-2">{output.name}</span>
                    </div>
                    
                    {/* Output Handle - 라벨 바로 옆에 위치 */}
                    <Handle
                      type="source"
                      position={Position.Right}
                      id={output.id}
                      style={{
                        position: 'absolute',
                        right: -8,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        border: `2px solid ${getPortColor(output.type)}`,
                        background: getPortColor(output.type),
                        zIndex: 10,
                        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                      }}
                      isConnectable={isConnectable}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Template Modal */}
      {showTemplateModal && (
        <PromptTemplateModal
          isOpen={showTemplateModal}
          onClose={() => setShowTemplateModal(false)}
          onSelectTemplate={(template) => {
            handleFieldChange('template', template);
          }}
          availableParameters={[
            'text', 'user_input', 'context', 'question', 'domain', 
            'language', 'style', 'source_language', 'target_language'
          ]}
          currentTemplate={data.fieldValues?.template || ''}
        />
      )}

      {/* Test Result Modal */}
      {showTestResultModal && (
        <TestResultModal
          isOpen={showTestResultModal}
          onClose={() => setShowTestResultModal(false)}
          nodeId={nodeId}
          nodeTitle={data.title}
          nodeType={data.type}
        />
      )}
    </div>
  );
};

export default React.memo(FlowStudioNode, (prevProps, nextProps) => {
  // 기본적인 props만 비교하여 불필요한 재렌더링 방지
  return (
    prevProps.id === nextProps.id &&
    prevProps.selected === nextProps.selected &&
    JSON.stringify(prevProps.data.fieldValues) === JSON.stringify(nextProps.data.fieldValues)
  );
});