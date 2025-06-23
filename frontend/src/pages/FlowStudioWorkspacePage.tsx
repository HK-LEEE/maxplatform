import React, { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  ReactFlowProvider,
  NodeTypes,
  EdgeTypes,
  ReactFlowInstance,
  getStraightPath
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  ArrowLeft,
  Play,
  Save,
  MessageSquare,
  Database,
  Cpu,
  FileText,
  Search,
  Copy,
  Trash2,
  Cloud,
  Bot,
  Server,
  Users,
  User,
  X,
  Upload,
  CheckCircle,
  Clock,
  AlertCircle
} from 'lucide-react';
import toast from 'react-hot-toast';
import FlowStudioNode, { FlowStudioNodeData } from '../components/FlowStudioNode';
import { nodeTemplates, NodeTemplate } from '../components/NodeTemplates';
import { llmService, FlowExecutionEngine, defaultModelConfigs } from '../services/llmService';
import FlowSaveModal from '../components/flow-studio/FlowSaveModal';
import FlowTestPanel from '../components/flow-studio/FlowTestPanel';
import { flowStudioApi } from '../services/flowStudioApi';

// 커스텀 노드 타입 정의
interface CustomNode extends Node {
  data: FlowStudioNodeData;
}

// 노드 타입 정의는 컴포넌트 내부에서 동적으로 생성

// 커스텀 엣지 컴포넌트
interface CustomEdgeProps {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  style?: React.CSSProperties;
  markerEnd?: string;
}

const CustomEdge: React.FC<CustomEdgeProps> = ({ 
  id, 
  sourceX, 
  sourceY, 
  targetX, 
  targetY, 
  style = {}, 
  markerEnd 
}) => {
  const [edgePath] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });

  return (
    <>
      <path
        id={id}
        style={style}
        className="react-flow__edge-path"
        d={edgePath}
        markerEnd={markerEnd}
      />
    </>
  );
};

// nodeTypes와 edgeTypes를 컴포넌트 외부에서 정의
const createNodeTypes = (
  handleDeleteNodeById: (nodeId: string) => void,
  handleCopyNodeById: (nodeId: string) => void,
  handleNodeDataChange: (nodeId: string, fieldName: string, value: any) => void
): NodeTypes => ({
  flowstudionode: (props: any) => (
    <FlowStudioNode
      {...props}
      onDelete={() => handleDeleteNodeById(props.id)}
      onCopy={() => handleCopyNodeById(props.id)}
      onDataChange={handleNodeDataChange}
    />
  ),
});

// 전역 nodeTypes 캐시
let globalNodeTypes: NodeTypes | null = null;
let globalHandleNodeDataChange: ((nodeId: string, fieldName: string, value: any) => void) | null = null;

const edgeTypes = {
  custom: CustomEdge,
};

const FlowStudioWorkspace: React.FC = () => {
  const { projectId, flowId } = useParams<{ projectId: string; flowId?: string }>();
  const navigate = useNavigate();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedComponent, setSelectedComponent] = useState<NodeTemplate | null>(null);
  const [showPlayground, setShowPlayground] = useState(false);
  const [playgroundInput, setPlaygroundInput] = useState('');
  const [executionResult, setExecutionResult] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [currentProject, setCurrentProject] = useState<any>(null);
  const [currentFlow, setCurrentFlow] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishStatus, setPublishStatus] = useState<'DRAFT' | 'PUBLISHED' | 'DEPRECATED' | 'ARCHIVED'>('DRAFT');
  const [contextMenu, setContextMenu] = useState<{
    show: boolean;
    x: number;
    y: number;
    nodeId: string | null;
  }>({ show: false, x: 0, y: 0, nodeId: null });

  // Mock user info - 실제로는 AuthContext에서 가져와야 함
  const mockUserInfo = {
    user_id: 'current-user-id',
    group_id: 'test-group-id',
    group_name: '개발팀',
    username: 'testuser'
  };

  // Flow execution engine 초기화
  const flowExecutionEngine = useMemo(() => new FlowExecutionEngine(llmService), []);

  useEffect(() => {
    // 프로젝트 목록 로드
    loadProjects();
  }, []);

  useEffect(() => {
    // 현재 프로젝트 정보 로드
    if (projectId) {
      loadCurrentProject();
    }
  }, [projectId]);

  const loadProjects = async () => {
    try {
      console.log('Loading projects...');
      const projectList = await flowStudioApi.getProjects();
      console.log('Projects loaded:', projectList);
      setProjects(projectList);
    } catch (error) {
      console.error('Failed to load projects:', error);
      toast('프로젝트 목록을 불러오는데 실패했습니다.', { icon: '⚠️' });
    }
  };

  const loadCurrentProject = async () => {
    if (!projectId) return;
    
    try {
      const project = await flowStudioApi.getProject(projectId);
      setCurrentProject(project);
    } catch (error) {
      console.error('Failed to load current project:', error);
      toast('현재 프로젝트 정보를 불러오는데 실패했습니다.', { icon: '⚠️' });
    }
  };

  const loadCurrentFlow = async () => {
    const flowId = location.pathname.split('/').pop();
    if (!flowId || flowId === 'workspace') return;
    
    try {
      console.log('Loading flow with ID:', flowId);
      const flow = await flowStudioApi.getFlow(flowId);
      console.log('Flow data received:', flow);
      
      setCurrentFlow(flow);
      
      // 플로우 데이터가 있으면 노드와 엣지를 복원
      if (flow.flow_data) {
        console.log('Flow data structure:', flow.flow_data);
        
        if (flow.flow_data.nodes && Array.isArray(flow.flow_data.nodes)) {
          console.log('Loading nodes:', flow.flow_data.nodes);
          // 기존 'langflow' 타입을 'flowstudionode'로 변환 (호환성 유지)
          const migratedNodes = flow.flow_data.nodes.map((node: any) => ({
            ...node,
            type: node.type === 'langflow' ? 'flowstudionode' : node.type
          }));
          setNodes(migratedNodes);
        } else {
          console.log('No nodes found in flow data');
        }
        
        if (flow.flow_data.edges && Array.isArray(flow.flow_data.edges)) {
          console.log('Loading edges:', flow.flow_data.edges);
          setEdges(flow.flow_data.edges);
        } else {
          console.log('No edges found in flow data');
        }
      } else {
        console.log('No flow_data found in flow');
      }
      
      toast.success(`플로우 "${flow.name}"을(를) 불러왔습니다.`);
    } catch (error) {
      console.error('Failed to load current flow:', error);
      toast.error('플로우를 불러오는데 실패했습니다.');
    }
  };

  // 기본 모델 설정 등록
  useEffect(() => {
    Object.entries(defaultModelConfigs).forEach(([id, config]) => {
      llmService.registerModel(id, config);
    });
  }, []);

  // 프로젝트와 플로우 로드
  useEffect(() => {
    loadCurrentProject();
  }, [projectId]);

  // 플로우 로드는 별도로 처리
  useEffect(() => {
    loadCurrentFlow();
  }, []); // 빈 배열로 한 번만 실행

  // 카테고리별 컴포넌트 그룹핑
  const componentsByCategory = useMemo(() => {
    const filtered = nodeTemplates.filter(template =>
      template.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      template.description.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return {
      input: filtered.filter(t => t.category === 'input'),
      prompt: filtered.filter(t => t.category === 'prompt'),
      model: filtered.filter(t => t.category === 'model'),
      output: filtered.filter(t => t.category === 'output'),
      rag: filtered.filter(t => t.category === 'rag')
    };
  }, [searchTerm]);

  // 노드 삭제 핸들러 (ID로 삭제)
  const handleDeleteNodeById = useCallback((nodeId: string) => {
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
    setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    toast.success('컴포넌트가 삭제되었습니다.');
  }, [setNodes, setEdges]);

  // 노드 복사 핸들러 (ID로 복사)
  const handleCopyNodeById = useCallback((nodeId: string) => {
    const nodeToCopy = nodes.find((node) => node.id === nodeId);
    if (!nodeToCopy) return;

    const newNode = {
      ...nodeToCopy,
      id: `${nodeToCopy.id}_copy_${Date.now()}`,
      position: {
        x: nodeToCopy.position.x + 50,
        y: nodeToCopy.position.y + 50,
      },
    };

    setNodes((nds) => [...nds, newNode]);
    toast.success('컴포넌트가 복사되었습니다.');
  }, [nodes, setNodes]);

  // 노드 데이터 변경 핸들러 - 단순화
  const handleNodeDataChange = useCallback((nodeId: string, fieldName: string, value: any) => {
    // 즉시 노드 데이터 업데이트 - 함수형 업데이트로 안정화
    setNodes((prevNodes: any) => {
      // 이미 업데이트된 노드가 있는지 확인
      const targetNode = prevNodes.find((node: any) => node.id === nodeId);
      if (!targetNode) {
        return prevNodes;
      }
      
      // 현재 값과 새 값이 같으면 업데이트하지 않음
      const currentValue = targetNode.data.fieldValues?.[fieldName];
      if (currentValue === value) {
        return prevNodes;
      }
      
      // 노드 업데이트
      const updatedNodes = prevNodes.map((node: any) => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              fieldValues: {
                ...node.data.fieldValues,
                [fieldName]: value
              }
            }
          };
        }
        return node;
      });
      
      return updatedNodes;
    });
  }, [setNodes]);

  // nodeTypes를 전역 캐시로 안정화
  const nodeTypes = useMemo(() => {
    if (!globalNodeTypes || globalHandleNodeDataChange !== handleNodeDataChange) {
      globalHandleNodeDataChange = handleNodeDataChange;
      globalNodeTypes = {
        flowstudionode: (props: any) => (
          <FlowStudioNode
            {...props}
            onDelete={() => handleDeleteNodeById(props.id)}
            onCopy={() => handleCopyNodeById(props.id)}
            onDataChange={handleNodeDataChange}
          />
        ),
      };
    }
    return globalNodeTypes;
  }, [handleNodeDataChange, handleDeleteNodeById, handleCopyNodeById]);

  const onConnect = useCallback(
    (params: Connection) => {
      // 연결 유효성 검사
      if (!params.source || !params.target || !params.sourceHandle || !params.targetHandle) {
        toast.error('연결에 필요한 정보가 부족합니다.');
        return;
      }

      // 소스와 타겟 노드 찾기
      const sourceNode = nodes.find(node => node.id === params.source);
      const targetNode = nodes.find(node => node.id === params.target);

      if (!sourceNode || !targetNode) {
        toast.error('연결할 노드를 찾을 수 없습니다.');
        return;
      }

      // 포트 타입 확인
      const sourceOutput = (sourceNode.data as any)?.outputs?.find((output: any) => output.id === params.sourceHandle);
      const targetInput = (targetNode.data as any)?.inputs?.find((input: any) => input.id === params.targetHandle);

      if (!sourceOutput || !targetInput) {
        toast.error('연결할 포트를 찾을 수 없습니다.');
        return;
      }

      // 타입 호환성 검사
      if (sourceOutput.type !== targetInput.type) {
        toast.error(`포트 타입이 일치하지 않습니다. (${sourceOutput.type} → ${targetInput.type})`);
        return;
      }

      const edge: Edge = {
        ...params,
        id: `edge-${Date.now()}`,
        type: 'custom',
        animated: true,
        style: { stroke: '#6366f1', strokeWidth: 2 }
      };
      setEdges((eds) => addEdge(edge, eds));
      toast.success('컴포넌트가 연결되었습니다.');
    },
    [setEdges, nodes]
  );

  // 엣지 클릭 핸들러 - 엣지 삭제 기능
  const onEdgeClick = useCallback((event: React.MouseEvent, edge: Edge) => {
    event.stopPropagation();
    
    const confirmDelete = window.confirm('이 연결선을 삭제하시겠습니까?');
    if (confirmDelete) {
      setEdges((eds) => eds.filter((e) => e.id !== edge.id));
      toast.success('연결선이 삭제되었습니다.');
    }
  }, [setEdges]);

  // 키보드 이벤트 핸들러 - 삭제 기능 제거
  const onKeyDown = useCallback((event: KeyboardEvent) => {
    // 삭제 기능을 제거했습니다
    // 필요한 경우 다른 키보드 단축키를 여기에 추가할 수 있습니다
  }, []);

  // 키보드 이벤트 리스너 추가
  useEffect(() => {
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [onKeyDown]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
      const templateId = event.dataTransfer.getData('application/reactflow');
      const template = nodeTemplates.find(t => t.id === templateId);

      if (!template || !reactFlowInstance || !reactFlowBounds) {
        console.log('Drop failed:', { template: !!template, reactFlowInstance: !!reactFlowInstance, reactFlowBounds: !!reactFlowBounds });
        return;
      }

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const newNode: Node = {
        id: `${template.id}_${Date.now()}`,
        type: 'flowstudionode',
        position,
        data: { ...template } as any,
      };

      setNodes((nds) => [...nds, newNode]);
      toast.success(`${template.title} 컴포넌트가 추가되었습니다.`);
    },
    [reactFlowInstance, setNodes]
  );

  const onDragStart = (event: React.DragEvent, templateId: string) => {
    event.dataTransfer.setData('application/reactflow', templateId);
    event.dataTransfer.effectAllowed = 'move';
  };

  const handleSaveFlow = () => {
    if (nodes.length === 0) {
      toast.error('저장할 플로우가 없습니다. 컴포넌트를 추가해주세요.');
      return;
    }
    setShowSaveModal(true);
  };

  const handleFlowSave = async (flowData: {
    name: string;
    description: string;
    owner_type: 'user' | 'group';
    project_id?: string;
    flow_data: any;
    flow_id?: string;
  }) => {
    try {
      const saveData = {
        ...flowData,
        project_id: flowData.project_id || currentProject?.id || '',
        flow_data: {
          nodes: nodes.map((node) => ({
            id: node.id,
            type: node.type,
            position: node.position,
            data: node.data,
          })),
          edges: edges.map((edge) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            sourceHandle: edge.sourceHandle,
            targetHandle: edge.targetHandle,
          })),
        }
      };

      let result;
      if (flowData.flow_id) {
        // 기존 플로우 업데이트
        result = await flowStudioApi.updateFlow(flowData.flow_id, {
          name: flowData.name,
          description: flowData.description,
          flow_data: saveData.flow_data
        });
        toast.success(`플로우 "${flowData.name}"이(가) 성공적으로 업데이트되었습니다!`);
      } else {
        // 새 플로우 생성
        result = await flowStudioApi.saveFlow(saveData);
        toast.success(`플로우 "${flowData.name}"이(가) 성공적으로 저장되었습니다!`);
      }
      
      // 현재 플로우 정보 업데이트
      setCurrentFlow({
        id: (result as any).flow?.id || (result as any).id,
        name: flowData.name,
        description: flowData.description,
        owner_type: flowData.owner_type
      });
      
      // 모달 닫기
      setShowSaveModal(false);
      
    } catch (error) {
      console.error('Save flow error:', error);
      toast.error('플로우 저장에 실패했습니다.');
    }
  };

  const handleExecuteFlow = async () => {
    if (nodes.length === 0) {
      toast.error('실행할 플로우가 없습니다. 컴포넌트를 추가해주세요.');
      return;
    }

    setIsExecuting(true);
    try {
      const input = playgroundInput || '안녕하세요! 테스트 메시지입니다.';
      
      // 실제 LLM 서비스를 사용한 플로우 실행
      const execution = await flowExecutionEngine.executeFlow(nodes, edges, input);
      
      // 실행 결과를 포맷팅
      const formattedResult = execution.steps
        .map(step => `🔹 [${step.nodeId}] ${step.output}${step.model ? ` (모델: ${step.model})` : ''}`)
        .join('\n');
      
      setExecutionResult(`플로우 실행 결과:\n\n${formattedResult}\n\n✅ 최종 결과: ${execution.result}`);
      toast.success('플로우가 성공적으로 실행되었습니다.');
      setShowPlayground(true);
    } catch (error) {
      console.error('Execute flow error:', error);
      const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류';
      toast.error(`플로우 실행에 실패했습니다: ${errorMessage}`);
      setExecutionResult(`❌ 플로우 실행 중 오류가 발생했습니다:\n${errorMessage}`);
    } finally {
      setIsExecuting(false);
    }
  };

  // 새로운 테스트 실행 함수 (백엔드 API 사용)
  const handleTestFlow = async (input: string, stream: boolean = false) => {
    if (nodes.length === 0) {
      throw new Error('실행할 플로우가 없습니다. 컴포넌트를 추가해주세요.');
    }

    setIsExecuting(true);
    try {
      // 플로우 데이터 준비
      const flowData = {
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
      };

      // 백엔드 테스트 API 호출
      const response = await fetch('/api/llmops/test-flow', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          flow_data: flowData,
          input_data: { text: input },
          stream: stream,
          parameters: {}
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      if (stream) {
        // 스트리밍 응답 처리 (향후 구현)
        const result = await response.text();
        return result;
      } else {
        // 일반 응답 처리
        const result = await response.json();
        return result.result || result;
      }
    } catch (error) {
      console.error('Test flow error:', error);
      throw error;
    } finally {
      setIsExecuting(false);
    }
  };

  const handlePublishFlow = async () => {
    if (!currentFlow) {
      toast.error('저장된 플로우가 없습니다. 먼저 플로우를 저장해주세요.');
      return;
    }

    if (nodes.length === 0) {
      toast.error('배포할 노드가 없습니다.');
      return;
    }

    setIsPublishing(true);
    try {
      const publishData = {
        publish_message: `플로우 배포 - ${new Date().toLocaleString()}`,
        target_environment: 'production'
      };

      const result = await flowStudioApi.publishFlow(currentFlow.id, publishData);
      console.log('Publish result:', result);
      
              setPublishStatus('PUBLISHED');
      toast.success('플로우가 성공적으로 배포되었습니다! 🚀');
      
      // 현재 플로우 정보 새로고침
      await loadCurrentFlow();
      
    } catch (error) {
      console.error('Flow publish failed:', error);
      const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.';
      toast.error(`플로우 배포 실패: ${errorMessage}`);
    } finally {
      setIsPublishing(false);
    }
  };

  const handleDeleteNode = useCallback(() => {
    if (selectedComponent) {
      setNodes((nds) => nds.filter((node) => node.id !== (selectedComponent as any).id));
      setSelectedComponent(null);
      toast.success('컴포넌트가 삭제되었습니다.');
    }
  }, [selectedComponent, setNodes]);

  const handleCopyNode = useCallback(() => {
    if (selectedComponent) {
      const template = selectedComponent as any;
      const newNode: Node = {
        id: `${template.id || template.data?.id}_${Date.now()}`,
        type: 'flowstudionode',
        position: {
          x: (template.position?.x || 0) + 50,
          y: (template.position?.y || 0) + 50,
        },
        data: { ...(template.data || template) } as any,
      };
      setNodes((nds) => [...nds, newNode]);
      toast.success('컴포넌트가 복사되었습니다.');
    }
  }, [selectedComponent, setNodes]);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'input': return <MessageSquare className="h-4 w-4" />;
      case 'prompt': return <FileText className="h-4 w-4" />;
      case 'model': return <Cpu className="h-4 w-4" />;
      case 'output': return <Database className="h-4 w-4" />;
      case 'rag': return <Search className="h-4 w-4" />;
      default: return <Cpu className="h-4 w-4" />;
    }
  };



  return (
    <div className="h-screen flex bg-surface-light">
      {/* Left Sidebar - Component Palette */}
      <div className="w-80 bg-white border-r border-neutral-200 flex flex-col shadow-soft">
        <div className="p-4 border-b border-neutral-200">
          <div className="flex items-center space-x-2 mb-3">
            <button
              onClick={() => navigate('/dashboard/flow-studio')}
              className="p-1 hover:bg-neutral-100 rounded"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <h2 className="text-lg font-semibold text-neutral-900">컴포넌트</h2>
          </div>
          
          <div className="relative mb-3">
            <input
              type="text"
              placeholder="컴포넌트 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <Search className="absolute left-2.5 top-2.5 h-3 w-3 text-neutral-400" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            {/* Inputs */}
            {componentsByCategory.input.length > 0 && (
              <div>
                <h3 className="font-medium text-sm mb-2 flex items-center">
                  {getCategoryIcon('input')}
                  <span className="ml-2">입력</span>
                </h3>
                <div className="space-y-2">
                  {componentsByCategory.input.map((template) => (
                    <div
                      key={template.id}
                      draggable
                      onDragStart={(e) => onDragStart(e, template.id)}
                      className="p-3 bg-blue-50 border border-blue-200 rounded-lg cursor-grab hover:bg-blue-100 active:cursor-grabbing component-card"
                    >
                      <div className="flex items-center space-x-2">
                        {template.icon}
                        <span className="font-medium text-sm">{template.title}</span>
                      </div>
                      <p className="text-xs text-gray-600 mt-1">{template.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Prompts */}
            {componentsByCategory.prompt.length > 0 && (
              <div>
                <h3 className="font-medium text-sm mb-2 flex items-center">
                  {getCategoryIcon('prompt')}
                  <span className="ml-2">프롬프트</span>
                </h3>
                <div className="space-y-2">
                  {componentsByCategory.prompt.map((template) => (
                    <div
                      key={template.id}
                      draggable
                      onDragStart={(e) => onDragStart(e, template.id)}
                      className="p-3 bg-purple-50 border border-purple-200 rounded-lg cursor-grab hover:bg-purple-100 active:cursor-grabbing component-card"
                    >
                      <div className="flex items-center space-x-2">
                        {template.icon}
                        <span className="font-medium text-sm">{template.title}</span>
                      </div>
                      <p className="text-xs text-gray-600 mt-1">{template.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Models */}
            {componentsByCategory.model.length > 0 && (
              <div>
                <h3 className="font-medium text-sm mb-2 flex items-center">
                  {getCategoryIcon('model')}
                  <span className="ml-2">모델</span>
                </h3>
                <div className="space-y-2">
                  {componentsByCategory.model.map((template) => (
                    <div
                      key={template.id}
                      draggable
                      onDragStart={(e) => onDragStart(e, template.id)}
                      className="p-3 bg-green-50 border border-green-200 rounded-lg cursor-grab hover:bg-green-100 active:cursor-grabbing component-card"
                    >
                      <div className="flex items-center space-x-2">
                        {template.icon}
                        <span className="font-medium text-sm">{template.title}</span>
                      </div>
                      <p className="text-xs text-gray-600 mt-1">{template.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* RAG */}
            {componentsByCategory.rag.length > 0 && (
              <div>
                <h3 className="font-medium text-sm mb-2 flex items-center">
                  {getCategoryIcon('rag')}
                  <span className="ml-2">RAG</span>
                </h3>
                <div className="space-y-2">
                  {componentsByCategory.rag.map((template) => (
                    <div
                      key={template.id}
                      draggable
                      onDragStart={(e) => onDragStart(e, template.id)}
                      className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg cursor-grab hover:bg-emerald-100 active:cursor-grabbing component-card"
                    >
                      <div className="flex items-center space-x-2">
                        {template.icon}
                        <span className="font-medium text-sm">{template.title}</span>
                      </div>
                      <p className="text-xs text-gray-600 mt-1">{template.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Outputs */}
            {componentsByCategory.output.length > 0 && (
              <div>
                <h3 className="font-medium text-sm mb-2 flex items-center">
                  {getCategoryIcon('output')}
                  <span className="ml-2">출력</span>
                </h3>
                <div className="space-y-2">
                  {componentsByCategory.output.map((template) => (
                    <div
                      key={template.id}
                      draggable
                      onDragStart={(e) => onDragStart(e, template.id)}
                      className="p-3 bg-orange-50 border border-orange-200 rounded-lg cursor-grab hover:bg-orange-100 active:cursor-grabbing component-card"
                    >
                      <div className="flex items-center space-x-2">
                        {template.icon}
                        <span className="font-medium text-sm">{template.title}</span>
                      </div>
                      <p className="text-xs text-gray-600 mt-1">{template.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 flex flex-col">
        {/* Top Toolbar */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold">
                Flow Studio
                {currentFlow && (
                  <span className="text-blue-600 ml-2">- {currentFlow.name}</span>
                )}
              </h1>
              <p className="text-sm text-gray-600">
                {currentFlow ? (
                  <>
                    {currentFlow.description || 'AI 워크플로우'}
                    <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      {currentFlow.owner_type === 'group' ? '그룹' : '개인'}
                    </span>
                  </>
                ) : (
                  'AI 워크플로우 구축'
                )}
              </p>
            </div>
            
            <div className="flex items-center space-x-2">
              {selectedComponent && (
                <>
                  <button
                    onClick={handleCopyNode}
                    className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center space-x-1"
                  >
                    <Copy className="h-4 w-4" />
                    <span>복사</span>
                  </button>
                </>
              )}
              
              <button
                onClick={() => setShowPlayground(!showPlayground)}
                className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center space-x-1"
              >
                <MessageSquare className="h-4 w-4" />
                <span>Test</span>
              </button>
              
              <button
                onClick={handleSaveFlow}
                className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center space-x-1"
              >
                <Save className="h-4 w-4" />
                <span>Save</span>
              </button>

              <button
                onClick={() => setShowPlayground(true)}
                disabled={isExecuting}
                className={`px-3 py-2 rounded-lg flex items-center space-x-1 ${
                  isExecuting 
                    ? 'bg-gray-400 text-white cursor-not-allowed' 
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                <Play className="h-4 w-4" />
                <span>{isExecuting ? 'Running...' : 'Run'}</span>
              </button>

              <button
                onClick={handlePublishFlow}
                disabled={isPublishing || !currentFlow}
                className={`px-3 py-2 rounded-lg flex items-center space-x-1 ${
                  isPublishing || !currentFlow
                    ? 'bg-gray-400 text-white cursor-not-allowed' 
                    : publishStatus === 'PUBLISHED'
                    ? 'bg-purple-600 text-white hover:bg-purple-700'
                    : 'bg-orange-600 text-white hover:bg-orange-700'
                }`}
                title={!currentFlow ? '먼저 플로우를 저장해주세요' : '플로우를 LLMOps 시스템에 배포'}
              >
                {isPublishing ? (
                  <>
                    <Clock className="h-4 w-4 animate-spin" />
                    <span>Publishing...</span>
                  </>
                ) : publishStatus === 'PUBLISHED' ? (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    <span>Published</span>
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4" />
                    <span>Publish</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* React Flow Canvas */}
        <div className="flex-1 relative" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodeClick={(_, node) => setSelectedComponent(node.data as any)}
            onNodeContextMenu={(event, node) => {
              event.preventDefault();
              setContextMenu({
                show: true,
                x: event.clientX,
                y: event.clientY,
                nodeId: node.id
              });
            }}
            onPaneClick={() => {
              setSelectedComponent(null);
              setContextMenu({ show: false, x: 0, y: 0, nodeId: null });
            }}
            onEdgeClick={onEdgeClick}
            defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
            minZoom={0.2}
            maxZoom={2}
            attributionPosition="bottom-left"
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
            <Controls />
            <MiniMap 
              nodeColor={(node) => {
                const template = node.data;
                switch (template?.category) {
                  case 'input': return '#3b82f6';
                  case 'prompt': return '#8b5cf6';
                  case 'model': return '#10b981';
                  case 'output': return '#f97316';
                  case 'rag': return '#059669';
                  default: return '#6b7280';
                }
              }}
              className="!bg-white !border !border-gray-300"
            />
          </ReactFlow>
        </div>
      </div>

      {/* Flow Test Panel */}
      <FlowTestPanel
        isOpen={showPlayground}
        onClose={() => setShowPlayground(false)}
        onExecute={handleTestFlow}
        isExecuting={isExecuting}
        nodes={nodes}
        edges={edges}
      />

      {/* Flow Save Modal */}
      <FlowSaveModal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        onSubmit={handleFlowSave}
        userInfo={mockUserInfo}
        defaultProject={currentProject ? {
          id: currentProject.id,
          name: currentProject.name,
          owner_type: currentProject.owner_type
        } : projects.length > 0 ? {
          id: projects[0].id,
          name: projects[0].name,
          owner_type: projects[0].owner_type
        } : undefined}
        currentFlow={currentFlow ? {
          id: currentFlow.id,
          name: currentFlow.name,
          description: currentFlow.description,
          owner_type: currentFlow.owner_type
        } : undefined}
        currentFlowData={{
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
        }}
      />

      {/* Context Menu */}
      {contextMenu.show && contextMenu.nodeId && (
        <div
          className="fixed bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50"
          style={{
            left: contextMenu.x,
            top: contextMenu.y,
          }}
          onMouseLeave={() => setContextMenu({ show: false, x: 0, y: 0, nodeId: null })}
        >
          <button
            onClick={() => {
              if (contextMenu.nodeId) {
                handleCopyNodeById(contextMenu.nodeId);
              }
              setContextMenu({ show: false, x: 0, y: 0, nodeId: null });
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center space-x-2"
          >
            <Copy className="h-4 w-4" />
            <span>복사</span>
          </button>
        </div>
      )}
    </div>
  );
};

const FlowStudioWorkspacePage: React.FC = () => {
  return (
    <ReactFlowProvider>
      <FlowStudioWorkspace />
    </ReactFlowProvider>
  );
};

export default FlowStudioWorkspacePage; 