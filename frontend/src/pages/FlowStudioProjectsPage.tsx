import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Grid3X3,
  List,
  Plus,
  MoreHorizontal,
  Play,
  Edit,
  Trash2,
  Copy,
  Calendar,
  User,
  Clock,
  ChevronRight,
  Users,
  X,
  Folder
} from 'lucide-react';
import toast from 'react-hot-toast';
import { flowStudioAPI } from '../services/api';

interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  user_id: string;
  group_id?: string;
  owner_type: 'user' | 'group';
  flows: Flow[];
}

interface Flow {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  project_id: string;
  user_id: string;
  group_id?: string;
  owner_type: 'user' | 'group';
}

// Mock user info - 실제로는 AuthContext에서 가져와야 함
const mockUserInfo = {
  user_id: 'current-user-id',
  group_id: 'test-group-id',
  group_name: '개발팀',
  username: 'testuser'
};

// API 클라이언트
const apiClient = {
  async getProjects(): Promise<Project[]> {
    try {
      const data = await flowStudioAPI.getProjects();
      return Array.isArray(data) ? data : [];
    } catch (error: any) {
      console.error('Error fetching projects:', error);
      
      if (error.response?.status === 401) {
        toast.error('로그인이 필요합니다.');
        return [];
      }
      
      toast.error('프로젝트를 불러오는데 실패했습니다.');
      return [];
    }
  },

  async createProject(projectData: {
    name: string;
    description: string;
    owner_type: 'user' | 'group';
    is_default?: boolean;
  }): Promise<Project> {
    try {
      const newProject = await flowStudioAPI.createProject(projectData);
      toast.success(`${projectData.owner_type === 'group' ? '그룹' : '개인'} 프로젝트가 생성되었습니다.`);
      return newProject;
    } catch (error: any) {
      console.error('Error creating project:', error);
      
      if (error.response?.status === 401) {
        toast.error('로그인이 필요합니다.');
        throw new Error('Authentication required');
      }
      
      toast.error('프로젝트 생성에 실패했습니다.');
      throw error;
    }
  },

  async deleteProject(projectId: string): Promise<void> {
    try {
      await flowStudioAPI.deleteProject(projectId);
      toast.success('프로젝트가 삭제되었습니다.');
    } catch (error: any) {
      console.error('Error deleting project:', error);
      
              if (error.response?.status === 401) {
          toast.error('로그인이 필요합니다.');
          throw new Error('Authentication required');
        }
      
      toast.error('프로젝트 삭제에 실패했습니다.');
      throw error;
    }
  },

  async deleteFlow(flowId: string): Promise<void> {
    try {
      await flowStudioAPI.deleteFlow(flowId);
      toast.success('플로우가 삭제되었습니다.');
    } catch (error: any) {
      console.error('Error deleting flow:', error);
      
      if (error.response?.status === 401) {
        toast.error('로그인이 필요합니다.');
        throw new Error('Authentication required');
      }
      
      if (error.response?.status === 403) {
        toast.error('플로우 삭제 권한이 없습니다.');
        throw new Error('Permission denied');
      }
      
      toast.error('플로우 삭제에 실패했습니다.');
      throw error;
    }
  }
};

const FlowStudioProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [newProjectOwnerType, setNewProjectOwnerType] = useState<'user' | 'group'>('user');
  const [newProjectIsDefault, setNewProjectIsDefault] = useState(false);
  const [creating, setCreating] = useState(false);

  // 프로젝트 데이터 로드
  useEffect(() => {
    const loadProjects = async () => {
      try {
        setLoading(true);
        const data = await apiClient.getProjects();
        setProjects(data);
      } catch (error) {
        console.error('Failed to load projects:', error);
        toast.error('프로젝트를 불러오는데 실패했습니다.');
      } finally {
        setLoading(false);
      }
    };

    loadProjects();
  }, []);

  // 검색 필터링
  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    project.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    project.flows.some(flow => 
      flow.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      flow.description.toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) {
      toast.error('프로젝트 이름을 입력해주세요.');
      return;
    }

    if (newProjectOwnerType === 'group' && !mockUserInfo.group_id) {
      toast.error('그룹 프로젝트를 생성하려면 그룹에 속해야 합니다.');
      return;
    }

    setCreating(true);
    try {
      const projectData = {
        name: newProjectName.trim(),
        description: newProjectDescription.trim(),
        owner_type: newProjectOwnerType,
        is_default: newProjectIsDefault
      };
      
      const newProject = await apiClient.createProject(projectData);
      setProjects([...projects, newProject]);
      setShowCreateModal(false);
      setNewProjectName('');
      setNewProjectDescription('');
      setNewProjectOwnerType('user');
      setNewProjectIsDefault(false);
    } catch (error) {
      console.error('Project creation failed:', error);
      if (error instanceof Error && !error.message.includes('Authentication')) {
        toast.error('프로젝트 생성에 실패했습니다.');
      }
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (!confirm('정말로 이 프로젝트를 삭제하시겠습니까?')) return;

    try {
      await apiClient.deleteProject(projectId);
      setProjects(projects.filter(p => p.id !== projectId));
    } catch (error) {
      console.error('Project deletion failed:', error);
      if (error instanceof Error && !error.message.includes('Authentication')) {
        toast.error('프로젝트 삭제에 실패했습니다.');
      }
    }
  };

  const handleDeleteFlow = async (flowId: string, projectId: string) => {
    if (!confirm('정말로 이 플로우를 삭제하시겠습니까?')) return;

    try {
      await apiClient.deleteFlow(flowId);
      setProjects(prev => prev.map(project => 
        project.id === projectId 
          ? { ...project, flows: project.flows.filter(flow => flow.id !== flowId) }
          : project
      ));
    } catch (error) {
      console.error('Flow deletion failed:', error);
      if (error instanceof Error && !error.message.includes('Authentication')) {
        toast.error('플로우 삭제에 실패했습니다.');
      }
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getOwnerTypeIcon = (ownerType: 'user' | 'group') => {
    return ownerType === 'group' ? (
      <Users className="h-4 w-4 text-green-600" />
    ) : (
      <User className="h-4 w-4 text-blue-600" />
    );
  };

  const getOwnerTypeText = (ownerType: 'user' | 'group') => {
    return ownerType === 'group' ? '그룹' : '개인';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">플로우 스튜디오를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-light">
      {/* Header */}
      <div className="bg-white border-b border-neutral-200 shadow-soft">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div>
              <h1 className="text-3xl font-bold text-neutral-900">Flow Studio</h1>
              <p className="text-neutral-600 mt-1">AI 워크플로우 프로젝트 관리</p>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 rounded-lg transition-colors ${
                    viewMode === 'grid' 
                      ? 'bg-primary-100 text-primary-700' 
                      : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100'
                  }`}
                >
                  <Grid3X3 className="h-5 w-5" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-2 rounded-lg transition-colors ${
                    viewMode === 'list' 
                      ? 'bg-primary-100 text-primary-700' 
                      : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100'
                  }`}
                >
                  <List className="h-5 w-5" />
                </button>
              </div>
              
              <button
                onClick={() => setShowCreateModal(true)}
                className="bg-gradient-primary text-white px-4 py-2 rounded-lg hover:shadow-medium transition-all duration-200 flex items-center space-x-2"
              >
                <Plus className="h-5 w-5" />
                <span>새 프로젝트</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search and View Controls */}
        <div className="flex items-center justify-between mb-6">
          <div className="relative flex-1 max-w-md">
            <input
              type="text"
              placeholder="프로젝트 또는 플로우 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          </div>
        </div>

        {/* Projects */}
        {filteredProjects.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-24 h-24 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <Grid3X3 className="h-12 w-12 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">프로젝트가 없습니다</h3>
            <p className="text-gray-500 mb-6">첫 번째 프로젝트를 만들어 플로우 구축을 시작해보세요.</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
            >
              프로젝트 만들기
            </button>
          </div>
        ) : (
          <div className="space-y-8">
            {filteredProjects.map((project) => (
              <div key={project.id} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                {/* Project Header */}
                <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">{project.name}</h2>
                      <p className="text-gray-600 mt-1">{project.description}</p>
                      <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-4 w-4" />
                          <span>생성: {formatDate(project.created_at)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Clock className="h-4 w-4" />
                          <span>수정: {formatDate(project.updated_at)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          {getOwnerTypeIcon(project.owner_type)}
                          <span>{getOwnerTypeText(project.owner_type)} 플로우 {project.flows.length}개</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleDeleteProject(project.id)}
                        className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                      <button className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                        <MoreHorizontal className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Flows */}
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-medium text-gray-900">플로우</h3>
                    <button
                      onClick={() => navigate(`/dashboard/flow-studio/${project.id}/workspace`)}
                      className="bg-blue-600 text-white px-3 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2 text-sm"
                    >
                      <Plus className="h-4 w-4" />
                      <span>새 플로우</span>
                    </button>
                  </div>
                  
                  {project.flows.length === 0 ? (
                    <div className="text-center py-8">
                      <p className="text-gray-500 mb-4">이 프로젝트에는 아직 플로우가 없습니다.</p>
                      <button
                        onClick={() => navigate(`/dashboard/flow-studio/${project.id}/workspace`)}
                        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                      >
                        첫 번째 플로우 만들기
                      </button>
                    </div>
                  ) : viewMode === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {project.flows.map((flow) => (
                        <div
                          key={flow.id}
                          className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer group"
                          onClick={() => navigate(`/dashboard/flow-studio/${project.id}/workspace/${flow.id}`)}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                                <span className="text-blue-600 text-sm">🔄</span>
                              </div>
                              <h3 className="font-medium text-gray-900 group-hover:text-blue-600">
                                {flow.name}
                              </h3>
                            </div>
                            
                            <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigate(`/dashboard/flow-studio/${project.id}/workspace/${flow.id}`);
                                }}
                                className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                                title="실행"
                              >
                                <Play className="h-3 w-3" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigate(`/dashboard/flow-studio/${project.id}/workspace/${flow.id}`);
                                }}
                                className="p-1 text-gray-600 hover:bg-gray-50 rounded"
                                title="편집"
                              >
                                <Edit className="h-3 w-3" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  // 복사 로직
                                }}
                                className="p-1 text-gray-600 hover:bg-gray-50 rounded"
                                title="복사"
                              >
                                <Copy className="h-3 w-3" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteFlow(flow.id, project.id);
                                }}
                                className="p-1 text-red-600 hover:bg-red-50 rounded"
                                title="삭제"
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </div>
                          </div>
                          
                          <p className="text-sm text-gray-600 mb-3">{flow.description}</p>
                          
                          <div className="flex items-center justify-between text-xs text-gray-500">
                            <span>수정: {formatTime(flow.updated_at)}</span>
                            <ChevronRight className="h-3 w-3" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {project.flows.map((flow) => (
                        <div
                          key={flow.id}
                          className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer group"
                          onClick={() => navigate(`/dashboard/flow-studio/${project.id}/workspace/${flow.id}`)}
                        >
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                              <span className="text-blue-600 text-sm">🔄</span>
                            </div>
                            <div>
                              <h3 className="font-medium text-gray-900 group-hover:text-blue-600">
                                {flow.name}
                              </h3>
                              <p className="text-sm text-gray-600">{flow.description}</p>
                            </div>
                          </div>
                          
                          <div className="flex items-center space-x-2 text-sm text-gray-500">
                            <span>수정: {formatTime(flow.updated_at)}</span>
                            <ChevronRight className="h-4 w-4" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                <Folder className="w-5 h-5 mr-2" />
                새 프로젝트 만들기
              </h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <form onSubmit={handleCreateProject} className="p-6 space-y-4">
              {/* 프로젝트 이름 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  프로젝트 이름 *
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="프로젝트 이름을 입력하세요"
                  required
                />
              </div>

              {/* 프로젝트 설명 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  프로젝트 설명
                </label>
                <textarea
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="프로젝트에 대한 설명을 입력하세요 (선택사항)"
                />
              </div>

              {/* 권한 설정 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  프로젝트 권한 *
                </label>
                <div className="space-y-2">
                  {/* 개인 권한 */}
                  <label className="flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50">
                    <input
                      type="radio"
                      name="owner_type"
                      value="user"
                      checked={newProjectOwnerType === 'user'}
                      onChange={(e) => setNewProjectOwnerType(e.target.value as 'user' | 'group')}
                      className="mr-3"
                    />
                    <User className="w-5 h-5 mr-2 text-blue-600" />
                    <div>
                      <div className="font-medium text-gray-900">개인 프로젝트</div>
                      <div className="text-sm text-gray-500">나만 접근할 수 있는 프로젝트</div>
                    </div>
                  </label>

                  {/* 그룹 권한 */}
                  <label className={`flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50 ${
                    !mockUserInfo.group_id ? 'opacity-50 cursor-not-allowed' : ''
                  }`}>
                    <input
                      type="radio"
                      name="owner_type"
                      value="group"
                      checked={newProjectOwnerType === 'group'}
                      onChange={(e) => setNewProjectOwnerType(e.target.value as 'user' | 'group')}
                      disabled={!mockUserInfo.group_id}
                      className="mr-3"
                    />
                    <Users className="w-5 h-5 mr-2 text-green-600" />
                    <div>
                      <div className="font-medium text-gray-900">
                        그룹 프로젝트
                        {mockUserInfo.group_name && (
                          <span className="text-sm text-gray-500 ml-1">({mockUserInfo.group_name})</span>
                        )}
                      </div>
                      <div className="text-sm text-gray-500">
                        {mockUserInfo.group_id 
                          ? '그룹 멤버들이 함께 사용할 수 있는 프로젝트'
                          : '그룹에 속해야 생성할 수 있습니다'
                        }
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              {/* 기본 프로젝트 설정 */}
              <div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={newProjectIsDefault}
                    onChange={(e) => setNewProjectIsDefault(e.target.checked)}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">기본 프로젝트로 설정</span>
                </label>
                <p className="text-xs text-gray-500 mt-1">
                  기본 프로젝트는 새 플로우 생성 시 자동으로 선택됩니다.
                </p>
              </div>

              {/* 버튼 */}
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {creating ? '생성 중...' : '프로젝트 생성'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default FlowStudioProjectsPage; 