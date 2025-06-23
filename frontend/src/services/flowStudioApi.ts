import axios from 'axios';

// API 클라이언트 설정
const apiClient = axios.create({
  baseURL: '/api',
});

// 토큰 인터셉터
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ==================== 타입 정의 ====================

export interface Project {
  id: string;
  name: string;
  description?: string;
  user_id: string;
  group_id?: string;
  owner_type: 'user' | 'group';
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface Flow {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  flow_data: any;
  user_id: string;
  group_id?: string;
  owner_type: 'user' | 'group';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FlowSaveData {
  name: string;
  description?: string;
  owner_type: 'user' | 'group';
  project_id: string;
  flow_data: any;
}

export interface FlowSaveResponse {
  flow: Flow;
  project: Project;
  message: string;
}

export interface FlowPublishRequest {
  version?: string;
  publish_message?: string;
  target_environment?: string;
  deployment_config?: any;
}

export interface FlowPublishResponse {
  id: string;
  flow_id: string;
  version: string;
  publish_status: 'DRAFT' | 'PUBLISHED' | 'DEPRECATED' | 'ARCHIVED';
  published_by: string;
  publish_message?: string;
  target_environment: string;
  webhook_called: boolean;
  webhook_response?: any;
  published_at: string;
}

export interface ComponentTemplate {
  id: string;
  name: string;
  category: string;
  description?: string;
  template_data: any;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FlowStudioStats {
  total_projects: number;
  active_flows: number;
  total_executions: number;
}

// ==================== API 서비스 클래스 ====================

class FlowStudioApiService {
  private baseUrl = '/flow-studio';

  // ==================== 프로젝트 관련 ====================
  
  async getProjects(): Promise<Project[]> {
    const response = await apiClient.get(`${this.baseUrl}/projects`);
    return response.data;
  }

  async getProject(projectId: string): Promise<Project> {
    const response = await apiClient.get(`${this.baseUrl}/projects/${projectId}`);
    return response.data;
  }

  async createProject(projectData: {
    name: string;
    description?: string;
    owner_type: 'user' | 'group';
    is_default?: boolean;
  }): Promise<Project> {
    const response = await apiClient.post(`${this.baseUrl}/projects`, projectData);
    return response.data;
  }

  async updateProject(projectId: string, projectData: Partial<Project>): Promise<Project> {
    const response = await apiClient.put(`${this.baseUrl}/projects/${projectId}`, projectData);
    return response.data;
  }

  async deleteProject(projectId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/projects/${projectId}`);
  }

  // ==================== 플로우 관련 ====================
  
  async saveFlow(flowData: FlowSaveData): Promise<FlowSaveResponse> {
    const response = await apiClient.post(`${this.baseUrl}/flows/save`, flowData);
    return response.data;
  }

  async getFlows(projectId: string): Promise<Flow[]> {
    const response = await apiClient.get(`${this.baseUrl}/projects/${projectId}/flows`);
    return response.data;
  }

  async getFlow(flowId: string): Promise<Flow> {
    const response = await apiClient.get(`${this.baseUrl}/flows/${flowId}`);
    return response.data;
  }

  async updateFlow(flowId: string, flowData: Partial<Flow>): Promise<Flow> {
    const response = await apiClient.put(`${this.baseUrl}/flows/${flowId}`, flowData);
    return response.data;
  }

  async deleteFlow(flowId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/flows/${flowId}`);
  }

  // ==================== 컴포넌트 템플릿 관련 ====================
  
  async getComponentTemplates(): Promise<ComponentTemplate[]> {
    const response = await apiClient.get(`${this.baseUrl}/component-templates`);
    return response.data;
  }

  async createComponentTemplate(templateData: Partial<ComponentTemplate>): Promise<ComponentTemplate> {
    const response = await apiClient.post(`${this.baseUrl}/component-templates`, templateData);
    return response.data;
  }

  async updateComponentTemplate(templateId: string, templateData: Partial<ComponentTemplate>): Promise<ComponentTemplate> {
    const response = await apiClient.put(`${this.baseUrl}/component-templates/${templateId}`, templateData);
    return response.data;
  }

  async deleteComponentTemplate(templateId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/component-templates/${templateId}`);
  }

  // ==================== RAG 데이터소스 관련 ====================
  
  async getAccessibleRagDatasources(): Promise<any[]> {
    const response = await apiClient.get(`${this.baseUrl}/rag-datasources`);
    return response.data;
  }

  // ==================== 통계 관련 ====================
  
  async getStats(): Promise<FlowStudioStats> {
    const response = await apiClient.get(`${this.baseUrl}/stats`);
    return response.data;
  }

  // ==================== 플로우 실행 관련 ====================
  
  async executeFlow(flowId: string, inputData?: any): Promise<any> {
    const response = await apiClient.post(`${this.baseUrl}/flows/${flowId}/execute`, {
      input_data: inputData
    });
    return response.data;
  }

  // ==================== 플로우 배포 관련 ====================
  
  async publishFlow(flowId: string, publishData: FlowPublishRequest): Promise<FlowPublishResponse> {
    const response = await apiClient.post(`${this.baseUrl}/flows/${flowId}/publish`, publishData);
    return response.data;
  }

  async unpublishFlow(flowId: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/flows/${flowId}/unpublish`);
  }

  async getPublishHistory(flowId: string, skip: number = 0, limit: number = 20): Promise<{
    flow_id: string;
    total_count: number;
    history: any[];
  }> {
    const response = await apiClient.get(`${this.baseUrl}/flows/${flowId}/publish-history`, {
      params: { skip, limit }
    });
    return response.data;
  }
}

// 싱글톤 인스턴스 생성 및 내보내기
export const flowStudioApi = new FlowStudioApiService();
export default flowStudioApi; 