/**
 * Flow Studio 페이지 - Langflow 스타일 UI/UX
 * 
 * 고도화된 멀티테넌트 LLMOps 플랫폼 기능:
 * - 3단 레이아웃: Palette(좌측) + Canvas(중앙) + Settings Panel(우측)
 * - 버전 관리 및 히스토리
 * - 실행 기록 추적
 * - 노드 상태 시각화
 * - 시크릿 관리 통합
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from 'react-query';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  BackgroundVariant,
  Panel,
  NodeTypes,
  getIncomers,
  getOutgoers,
  getConnectedEdges
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Save,
  Play,
  Square,
  Database,
  MessageSquare,
  FileText,
  Settings,
  ArrowLeft,
  Trash2,
  Download,
  History,
  GitBranch,
  Eye,
  ChevronDown,
  ChevronRight,
  Key,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Layers,
  Palette,
  Settings2
} from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';

import ragDataSourceService from '../services/ragDataSourceService';
import { RAGDataSourceListItem } from '../types/ragDataSource';

// 커스텀 노드 컴포넌트들
const RAGNode: React.FC<{ data: any }> = ({ data }) => {
  const getStatusColor = () => {
    // 유효성 검사 결과에 따른 색상 결정
    if (data.isValid === false) return 'border-red-500 bg-red-50';
    if (data.isIsolated) return 'border-orange-500 bg-orange-50';
    
    switch (data.status) {
      case 'ok': return 'border-green-500 bg-green-50';
      case 'warning': return 'border-yellow-500 bg-yellow-50';
      case 'error': return 'border-red-500 bg-red-50';
      default: return 'border-gray-300 bg-white';
    }
  };

  const getValidationIcon = () => {
    if (data.isValid === false) return <XCircle className="h-3 w-3 text-red-500" />;
    if (data.isIsolated) return <AlertTriangle className="h-3 w-3 text-orange-500" />;
    return null;
  };

  return (
    <div className={`px-4 py-3 rounded-lg border-2 ${getStatusColor()} min-w-[180px] transition-colors`}>
      <div className="flex items-center gap-2 mb-2">
        <Database className="h-4 w-4 text-blue-600" />
        <span className="font-medium text-sm">RAG 데이터소스</span>
        {getValidationIcon()}
        {data.status === 'warning' && <AlertTriangle className="h-3 w-3 text-yellow-500" />}
        {data.status === 'error' && <XCircle className="h-3 w-3 text-red-500" />}
        {data.status === 'ok' && !data.isValid && !data.isIsolated && <CheckCircle className="h-3 w-3 text-green-500" />}
      </div>
      <div className="text-xs text-gray-600">
        {data.dataSourceName || '데이터소스 선택'}
      </div>
      {data.isIsolated && (
        <div className="text-xs text-orange-600 mt-1">
          ⚠️ 고립된 노드
        </div>
      )}
      {data.isValid === false && (
        <div className="text-xs text-red-600 mt-1">
          ❌ 연결 오류
        </div>
      )}
      {data.connectionCount !== undefined && (
        <div className="text-xs text-gray-500 mt-1">
          연결: {data.connectionCount}개
        </div>
      )}
    </div>
  );
};

const LLMNode: React.FC<{ data: any }> = ({ data }) => {
  const getStatusColor = () => {
    // 유효성 검사 결과에 따른 색상 결정
    if (data.isValid === false) return 'border-red-500 bg-red-50';
    if (data.isIsolated) return 'border-orange-500 bg-orange-50';
    
    switch (data.status) {
      case 'ok': return 'border-green-500 bg-green-50';
      case 'warning': return 'border-yellow-500 bg-yellow-50';
      case 'error': return 'border-red-500 bg-red-50';
      default: return 'border-gray-300 bg-white';
    }
  };

  const getValidationIcon = () => {
    if (data.isValid === false) return <XCircle className="h-3 w-3 text-red-500" />;
    if (data.isIsolated) return <AlertTriangle className="h-3 w-3 text-orange-500" />;
    return null;
  };

  return (
    <div className={`px-4 py-3 rounded-lg border-2 ${getStatusColor()} min-w-[180px] transition-colors`}>
      <div className="flex items-center gap-2 mb-2">
        <MessageSquare className="h-4 w-4 text-green-600" />
        <span className="font-medium text-sm">LLM 채팅</span>
        {getValidationIcon()}
        {data.status === 'warning' && <AlertTriangle className="h-3 w-3 text-yellow-500" />}
        {data.status === 'error' && <XCircle className="h-3 w-3 text-red-500" />}
        {data.status === 'ok' && !data.isValid && !data.isIsolated && <CheckCircle className="h-3 w-3 text-green-500" />}
      </div>
      <div className="text-xs text-gray-600">
        {data.model || 'gpt-3.5-turbo'}
      </div>
      {data.isIsolated && (
        <div className="text-xs text-orange-600 mt-1">
          ⚠️ 고립된 노드
        </div>
      )}
      {data.isValid === false && (
        <div className="text-xs text-red-600 mt-1">
          ❌ 연결 오류
        </div>
      )}
      {data.connectionCount !== undefined && (
        <div className="text-xs text-gray-500 mt-1">
          연결: {data.connectionCount}개
        </div>
      )}
    </div>
  );
};

// 노드 타입 정의
const nodeTypes: NodeTypes = {
  ragNode: RAGNode,
  llmNode: LLMNode,
};

// 초기 노드와 엣지
const initialNodes: Node[] = [
  {
    id: '1',
    type: 'input',
    position: { x: 250, y: 50 },
    data: { label: '시작' },
  }
];

const initialEdges: Edge[] = [];

// 인터페이스 정의
interface FlowVersion {
  id: number;
  version: number;
  name: string;
  created_at: string;
  is_latest: boolean;
}

interface ExecutionLog {
  id: string;
  status: 'SUCCESS' | 'FAILURE' | 'PENDING' | 'RUNNING';
  created_at: string;
  execution_time_ms?: number;
  inputs?: any;
  outputs?: any;
  error_message?: string;
}

interface Secret {
  id: number;
  name: string;
  description?: string;
  category?: string;
  created_at: string;
}

const FlowStudioPage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  // 상태 관리
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [isExecuting, setIsExecuting] = useState(false);
  const [flowName, setFlowName] = useState('새 워크플로우');
  const [selectedFlowId, setSelectedFlowId] = useState<number | null>(null);
  const [currentVersion, setCurrentVersion] = useState(1);
  
  // UI 상태
  const [rightPanelTab, setRightPanelTab] = useState<'settings' | 'history' | 'versions' | 'secrets'>('settings');
  const [leftPanelExpanded, setLeftPanelExpanded] = useState<string[]>(['datasources', 'ai-models']);
  const [showVersionModal, setShowVersionModal] = useState(false);
  
  // 버전 저장 모달 상태
  const [saveAsNewVersion, setSaveAsNewVersion] = useState(false);
  const [versionDescription, setVersionDescription] = useState('');

  // RAG 데이터소스 목록 조회
  const { data: dataSources } = useQuery<RAGDataSourceListItem[]>(
    'rag-datasources',
    ragDataSourceService.getDataSources,
    {
      onError: (error: any) => {
        console.error('Failed to fetch data sources:', error);
        toast.error('데이터소스 목록을 불러올 수 없습니다.');
      }
    }
  );

  // 플로우 버전 목록 조회 (Mock)
  const flowVersions: FlowVersion[] = useMemo(() => [
    { id: 1, version: 1, name: flowName, created_at: '2024-01-01T00:00:00Z', is_latest: false },
    { id: 2, version: 2, name: flowName, created_at: '2024-01-02T00:00:00Z', is_latest: false },
    { id: 3, version: 3, name: flowName, created_at: '2024-01-03T00:00:00Z', is_latest: true },
  ], [flowName]);

  // 실행 기록 조회 (Mock)
  const executionLogs: ExecutionLog[] = useMemo(() => [
    {
      id: '1',
      status: 'SUCCESS',
      created_at: '2024-01-03T10:30:00Z',
      execution_time_ms: 2500,
      inputs: { query: 'AI에 대해 설명해주세요' },
      outputs: { response: 'AI는...' }
    },
    {
      id: '2',
      status: 'FAILURE',
      created_at: '2024-01-03T10:25:00Z',
      execution_time_ms: 1200,
      error_message: 'API 키가 유효하지 않습니다'
    },
    {
      id: '3',
      status: 'SUCCESS',
      created_at: '2024-01-03T10:20:00Z',
      execution_time_ms: 3100,
    },
  ], []);

  // 시크릿 목록 조회 (Mock)
  const secrets: Secret[] = useMemo(() => [
    { id: 1, name: 'OPENAI_API_KEY', description: 'OpenAI API 키', category: 'api_key', created_at: '2024-01-01T00:00:00Z' },
    { id: 2, name: 'ANTHROPIC_API_KEY', description: 'Anthropic API 키', category: 'api_key', created_at: '2024-01-01T00:00:00Z' },
  ], []);

  // 위상검증 로직 - 연결 유효성 검사
  const isValidConnection = useCallback(
    (connection: Connection | Edge) => {
      // Edge 타입인 경우 Connection으로 변환
      const conn: Connection = 'sourceHandle' in connection && connection.sourceHandle !== undefined
        ? connection as Connection
        : {
          source: connection.source,
          target: connection.target,
          sourceHandle: connection.sourceHandle || null,
          targetHandle: connection.targetHandle || null
        };
             // 1. 자기 자신에게 연결하는 것 방지
       if (conn.source === conn.target) {
         console.warn("자기 자신에게 연결할 수 없습니다.");
         toast.error("자기 자신에게 연결할 수 없습니다.");
         return false;
       }

       // 2. 이미 연결된 핸들에 다시 연결하는 것 방지
       const isTargetHandleAlreadyConnected = edges.some(
         (edge) => 
           edge.target === conn.target && 
           edge.targetHandle === conn.targetHandle
       );
       
       if (isTargetHandleAlreadyConnected) {
         console.warn("이미 연결된 핸들입니다.");
         toast.error("이미 연결된 핸들입니다.");
         return false;
       }

       // 3. 순환 구조 검사
       const sourceNode = nodes.find((node) => node.id === conn.source);
       const targetNode = nodes.find((node) => node.id === conn.target);
      
      if (!sourceNode || !targetNode) {
        console.warn("연결하려는 노드를 찾을 수 없습니다.");
        return false;
      }

      // 4. 순환 참조 검사 (DFS 기반)
      const hasCycle = (targetId: string, sourceId: string): boolean => {
        const visited = new Set<string>();
        const stack = [targetId];
                 const tempEdges = [...edges, { 
           source: sourceId, 
           target: targetId, 
           id: 'temp',
           sourceHandle: conn.sourceHandle,
           targetHandle: conn.targetHandle
         }];

        while (stack.length > 0) {
          const currentNodeId = stack.pop()!;

          if (currentNodeId === sourceId) {
            return true; // 순환 발견
          }

          if (!visited.has(currentNodeId)) {
            visited.add(currentNodeId);
            const outgoingEdges = tempEdges.filter(edge => edge.source === currentNodeId);
            for (const edge of outgoingEdges) {
              stack.push(edge.target);
            }
          }
        }

        return false; // 순환 없음
      };

             if (hasCycle(conn.target, conn.source)) {
         console.warn("순환 구조는 허용되지 않습니다.");
         toast.error("순환 구조는 허용되지 않습니다.");
         return false;
       }

       // 5. 노드 타입 기반 연결 규칙 검사
       const sourceType = sourceNode.type || sourceNode.data?.type;
       const targetType = targetNode.type || targetNode.data?.type;

       // 입력 노드끼리 연결 방지
       if (sourceType === 'input' && targetType === 'input') {
         console.warn("입력 노드끼리는 연결할 수 없습니다.");
         toast.error("입력 노드끼리는 연결할 수 없습니다.");
         return false;
       }

       // 모든 검사를 통과하면 true 반환
       console.log(`연결 허용: ${conn.source} -> ${conn.target}`);
       return true;
    },
    [nodes, edges]
  );

  // 사후 검증 - 노드 상태 업데이트
  useEffect(() => {
    setNodes((currentNodes) =>
      currentNodes.map((node) => {
        const incomers = getIncomers(node, currentNodes, edges);
        const outgoers = getOutgoers(node, currentNodes, edges);
        const connectedEdges = getConnectedEdges([node], edges);

        // 고립된 노드 검사
        const isIsolated = incomers.length === 0 && outgoers.length === 0;
        
        // 프로세스 노드의 경우 입력과 출력이 모두 있어야 함
        let isValid = true;
        if (node.data?.category === 'model' || node.data?.category === 'processor') {
          isValid = incomers.length > 0 && outgoers.length > 0;
        }

        // 노드 데이터에 유효성 상태 추가
        return {
          ...node,
          data: { 
            ...node.data, 
            isValid,
            isIsolated,
            connectionCount: connectedEdges.length
          },
        };
      })
    );
  }, [nodes, edges, setNodes]);

  // 연결 처리
  const onConnect = useCallback(
    (params: Connection) => {
      console.log(`연결 시도: ${params.source} -> ${params.target}`);
      setEdges((eds) => addEdge(params, eds));
    },
    [setEdges]
  );

  // 새 노드 추가
  const addNode = useCallback((type: string, dataSourceId?: number) => {
    const id = `${Date.now()}`;
    const position = {
      x: Math.random() * 400 + 100,
      y: Math.random() * 400 + 200,
    };

    const nodeData = getDefaultNodeData(type, dataSourceId);
    const newNode: Node = {
      id,
      type: getNodeType(type),
      position,
      data: nodeData,
    };

    setNodes((nds) => nds.concat(newNode));
  }, [setNodes]);

  // 플로우 저장
  const saveFlow = useCallback(async () => {
    if (saveAsNewVersion) {
      setShowVersionModal(true);
      return;
    }

    try {
      const flowData = {
        name: flowName,
        description: versionDescription,
        flow_data: { nodes, edges },
        owner_type: 'GROUP',
        owner_id: workspaceId ? parseInt(workspaceId) : 1,
        workspace_id: workspaceId ? parseInt(workspaceId) : undefined,
        ...(selectedFlowId && { parent_flow_id: selectedFlowId })
      };

      console.log('Saving flow:', flowData);
      toast.success('워크플로우가 저장되었습니다.');
      setShowVersionModal(false);
      setSaveAsNewVersion(false);
      setVersionDescription('');
    } catch (error) {
      console.error('Failed to save flow:', error);
      toast.error('워크플로우 저장에 실패했습니다.');
    }
  }, [flowName, versionDescription, nodes, edges, workspaceId, selectedFlowId, saveAsNewVersion]);

  // 플로우 실행
  const executeFlow = useCallback(async () => {
    setIsExecuting(true);
    try {
      console.log('Executing flow:', { nodes, edges });
      
      // 시뮬레이션: 3초 후 완료
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      toast.success('워크플로우 실행이 완료되었습니다.');
      // 실행 후 쿼리 새로고침
      queryClient.invalidateQueries('execution-logs');
    } catch (error) {
      console.error('Failed to execute flow:', error);
      toast.error('워크플로우 실행에 실패했습니다.');
    } finally {
      setIsExecuting(false);
    }
  }, [nodes, edges, queryClient]);

  // 버전 로드
  const loadVersion = useCallback((version: FlowVersion) => {
    // Mock 데이터 로드
    setFlowName(version.name);
    setCurrentVersion(version.version);
    toast.success(`버전 ${version.version}을 로드했습니다.`);
  }, []);

  // 좌측 패널 토글
  const toggleLeftPanelSection = useCallback((section: string) => {
    setLeftPanelExpanded(prev => 
      prev.includes(section) 
        ? prev.filter(s => s !== section)
        : [...prev, section]
    );
  }, []);

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 헤더 */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={flowName}
                onChange={(e) => setFlowName(e.target.value)}
                className="text-lg font-semibold bg-transparent border-none outline-none focus:bg-gray-50 px-2 py-1 rounded"
              />
              <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                v{currentVersion}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSaveAsNewVersion(!saveAsNewVersion)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                saveAsNewVersion 
                  ? 'bg-blue-100 text-blue-700 border border-blue-300' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <GitBranch className="h-4 w-4 inline mr-1" />
              새 버전
            </button>
            <button
              onClick={saveFlow}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700 transition-colors"
            >
              <Save className="h-4 w-4" />
              저장
            </button>
            <button
              onClick={executeFlow}
              disabled={isExecuting}
              className="bg-green-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {isExecuting ? (
                <>
                  <Square className="h-4 w-4" />
                  실행 중...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  실행
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* 좌측 팔레트 패널 */}
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center gap-2 mb-3">
              <Palette className="h-5 w-5 text-gray-600" />
              <h3 className="font-semibold text-gray-900">컴포넌트 팔레트</h3>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* 데이터 소스 섹션 */}
            <div className="border border-gray-200 rounded-lg">
              <button
                onClick={() => toggleLeftPanelSection('datasources')}
                className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-blue-600" />
                  <span className="font-medium text-sm">데이터 소스</span>
                </div>
                {leftPanelExpanded.includes('datasources') ? 
                  <ChevronDown className="h-4 w-4" /> : 
                  <ChevronRight className="h-4 w-4" />
                }
              </button>
              
              {leftPanelExpanded.includes('datasources') && (
                <div className="p-3 pt-0 space-y-2">
                  <button
                    onClick={() => addNode('ragDataSource')}
                    className="w-full flex items-center gap-2 p-3 border-2 border-dashed border-blue-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
                  >
                    <Database className="h-4 w-4 text-blue-600" />
                    <span className="text-sm">RAG 데이터소스</span>
                  </button>
                  
                  {/* 사용 가능한 데이터소스 목록 */}
                  {dataSources && dataSources.length > 0 && (
                    <div className="mt-3">
                      <h5 className="text-xs font-medium text-gray-500 mb-2">사용 가능한 데이터소스</h5>
                      <div className="space-y-1 max-h-32 overflow-y-auto">
                        {dataSources.map((ds) => (
                          <button
                            key={ds.id}
                            onClick={() => addNode('ragDataSource', ds.id)}
                            className="w-full text-left p-2 bg-gray-50 rounded border hover:bg-blue-50 hover:border-blue-300 transition-colors"
                          >
                            <div className="font-medium text-xs truncate">{ds.name}</div>
                            <div className="text-gray-500 flex items-center gap-1 text-xs">
                              <FileText className="h-3 w-3" />
                              {ds.document_count}개 문서
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* AI 모델 섹션 */}
            <div className="border border-gray-200 rounded-lg">
              <button
                onClick={() => toggleLeftPanelSection('ai-models')}
                className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-green-600" />
                  <span className="font-medium text-sm">AI 모델</span>
                </div>
                {leftPanelExpanded.includes('ai-models') ? 
                  <ChevronDown className="h-4 w-4" /> : 
                  <ChevronRight className="h-4 w-4" />
                }
              </button>
              
              {leftPanelExpanded.includes('ai-models') && (
                <div className="p-3 pt-0 space-y-2">
                  <button
                    onClick={() => addNode('llmChat')}
                    className="w-full flex items-center gap-2 p-3 border-2 border-dashed border-green-300 rounded-lg hover:border-green-500 hover:bg-green-50 transition-colors"
                  >
                    <MessageSquare className="h-4 w-4 text-green-600" />
                    <span className="text-sm">LLM 채팅</span>
                  </button>
                </div>
              )}
            </div>

            {/* 처리 섹션 */}
            <div className="border border-gray-200 rounded-lg">
              <button
                onClick={() => toggleLeftPanelSection('processing')}
                className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-purple-600" />
                  <span className="font-medium text-sm">처리</span>
                </div>
                {leftPanelExpanded.includes('processing') ? 
                  <ChevronDown className="h-4 w-4" /> : 
                  <ChevronRight className="h-4 w-4" />
                }
              </button>
              
              {leftPanelExpanded.includes('processing') && (
                <div className="p-3 pt-0 space-y-2">
                  <button
                    onClick={() => addNode('textProcessor')}
                    className="w-full flex items-center gap-2 p-3 border-2 border-dashed border-purple-300 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition-colors"
                  >
                    <FileText className="h-4 w-4 text-purple-600" />
                    <span className="text-sm">텍스트 처리</span>
                  </button>
                </div>
              )}
            </div>

            {/* 출력 섹션 */}
            <div className="border border-gray-200 rounded-lg">
              <button
                onClick={() => toggleLeftPanelSection('output')}
                className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Download className="h-4 w-4 text-orange-600" />
                  <span className="font-medium text-sm">출력</span>
                </div>
                {leftPanelExpanded.includes('output') ? 
                  <ChevronDown className="h-4 w-4" /> : 
                  <ChevronRight className="h-4 w-4" />
                }
              </button>
              
              {leftPanelExpanded.includes('output') && (
                <div className="p-3 pt-0 space-y-2">
                  <button
                    onClick={() => addNode('output')}
                    className="w-full flex items-center gap-2 p-3 border-2 border-dashed border-orange-300 rounded-lg hover:border-orange-500 hover:bg-orange-50 transition-colors"
                  >
                    <Download className="h-4 w-4 text-orange-600" />
                    <span className="text-sm">결과 출력</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 중앙 캔버스 */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            isValidConnection={isValidConnection}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-left"
          >
            <Controls />
            <MiniMap />
            <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
            
            {/* 플로우 컨트롤 패널 */}
            <Panel position="top-right" className="bg-white rounded-lg shadow-lg p-3">
              <div className="flex gap-2">
                <button
                  onClick={() => setNodes([])}
                  className="p-2 hover:bg-gray-100 rounded transition-colors"
                  title="모든 노드 삭제"
                >
                  <Trash2 className="h-4 w-4 text-red-600" />
                </button>
                <button
                  onClick={() => console.log({ nodes, edges })}
                  className="p-2 hover:bg-gray-100 rounded transition-colors"
                  title="플로우 데이터 출력"
                >
                  <Settings className="h-4 w-4 text-gray-600" />
                </button>
              </div>
            </Panel>
          </ReactFlow>
        </div>

        {/* 우측 설정 패널 */}
        <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
          {/* 탭 헤더 */}
          <div className="border-b border-gray-200">
            <div className="flex">
              {[
                { key: 'settings', label: '설정', icon: Settings2 },
                { key: 'versions', label: '버전', icon: GitBranch },
                { key: 'history', label: '실행기록', icon: History },
                { key: 'secrets', label: '시크릿', icon: Key },
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setRightPanelTab(tab.key as any)}
                  className={`flex-1 flex items-center justify-center gap-1 px-3 py-3 text-sm font-medium border-b-2 transition-colors ${
                    rightPanelTab === tab.key
                      ? 'border-blue-500 text-blue-600 bg-blue-50'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <tab.icon className="h-4 w-4" />
                  <span className="hidden lg:inline">{tab.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 탭 컨텐츠 */}
          <div className="flex-1 overflow-y-auto p-4">
            {rightPanelTab === 'settings' && (
              <div className="space-y-4">
                <h4 className="font-semibold text-gray-900">플로우 설정</h4>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    플로우 이름
                  </label>
                  <input
                    type="text"
                    value={flowName}
                    onChange={(e) => setFlowName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    설명
                  </label>
                  <textarea
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="플로우에 대한 설명을 입력하세요..."
                  />
                </div>
              </div>
            )}

            {rightPanelTab === 'versions' && (
              <div className="space-y-4">
                <h4 className="font-semibold text-gray-900">버전 히스토리</h4>
                <div className="space-y-2">
                  {flowVersions.map((version) => (
                    <div
                      key={version.id}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        version.version === currentVersion
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => loadVersion(version)}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">
                          버전 {version.version}
                        </span>
                        {version.is_latest && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs font-medium rounded">
                            최신
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500">
                        {new Date(version.created_at).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {rightPanelTab === 'history' && (
              <div className="space-y-4">
                <h4 className="font-semibold text-gray-900">실행 기록</h4>
                <div className="space-y-2">
                  {executionLogs.map((log) => (
                    <div
                      key={log.id}
                      className="p-3 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {log.status === 'SUCCESS' && <CheckCircle className="h-4 w-4 text-green-500" />}
                          {log.status === 'FAILURE' && <XCircle className="h-4 w-4 text-red-500" />}
                          {log.status === 'RUNNING' && <Clock className="h-4 w-4 text-blue-500" />}
                          <span className="text-sm font-medium">
                            {log.status === 'SUCCESS' ? '성공' : 
                             log.status === 'FAILURE' ? '실패' : 
                             log.status === 'RUNNING' ? '실행중' : '대기중'}
                          </span>
                        </div>
                        {log.execution_time_ms && (
                          <span className="text-xs text-gray-500">
                            {log.execution_time_ms}ms
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500">
                        {new Date(log.created_at).toLocaleString()}
                      </div>
                      {log.error_message && (
                        <div className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded">
                          {log.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {rightPanelTab === 'secrets' && (
              <div className="space-y-4">
                <h4 className="font-semibold text-gray-900">시크릿 관리</h4>
                <div className="space-y-2">
                  {secrets.map((secret) => (
                    <div
                      key={secret.id}
                      className="p-3 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Key className="h-4 w-4 text-gray-600" />
                        <span className="font-medium text-sm">{secret.name}</span>
                      </div>
                      {secret.description && (
                        <div className="text-xs text-gray-500 mb-1">
                          {secret.description}
                        </div>
                      )}
                      <div className="text-xs text-gray-400">
                        {new Date(secret.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
                <button className="w-full px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                  새 시크릿 추가
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 버전 저장 모달 */}
      {showVersionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">새 버전으로 저장</h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                버전 설명
              </label>
              <textarea
                rows={3}
                value={versionDescription}
                onChange={(e) => setVersionDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="이 버전의 변경사항을 설명해주세요..."
              />
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => setShowVersionModal(false)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
              <button
                onClick={saveFlow}
                className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                저장
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast 알림 */}
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
        }}
      />
    </div>
  );
};

// 기본 노드 데이터 생성 함수
function getDefaultNodeData(type: string, dataSourceId?: number): any {
  switch (type) {
    case 'ragDataSource':
      return {
        label: '🗃️ RAG 데이터소스',
        dataSourceId: dataSourceId || null,
        dataSourceName: dataSourceId ? `데이터소스 ${dataSourceId}` : null,
        searchQuery: '',
        status: dataSourceId ? 'ok' : 'warning',
      };
    case 'llmChat':
      return {
        label: '🤖 LLM 채팅',
        model: 'gpt-3.5-turbo',
        temperature: 0.7,
        maxTokens: 1000,
        status: 'ok',
      };
    case 'textProcessor':
      return {
        label: '📝 텍스트 처리',
        operation: 'extract',
        parameters: {},
        status: 'ok',
      };
    case 'output':
      return {
        label: '📤 결과 출력',
        format: 'json',
        status: 'ok',
      };
    default:
      return { label: '노드', status: 'ok' };
  }
}

// 노드 타입 매핑 함수
function getNodeType(type: string): string {
  switch (type) {
    case 'ragDataSource':
      return 'ragNode';
    case 'llmChat':
      return 'llmNode';
    default:
      return 'default';
  }
}

export default FlowStudioPage; 