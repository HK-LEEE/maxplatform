/**
 * LLM 채팅 서비스 API 클라이언트
 */
import apiClient from './api';
import {
  Persona, PersonaCreate, PersonaUpdate,
  PromptTemplate, PromptTemplateCreate,
  Chat, ChatCreateRequest, Message, MessageSendRequest,
  MessageFeedback, ChatSearchResult, ChatShare, ChatShareCreate,
  LLMModel, RAGDataSource, LLMModelManagement, LLMModelCreate, LLMModelUpdate
} from '../types/llmChat';

const BASE_URL = '/chat';

export class LLMChatApiService {
  // ==================== 페르소나 관리 ====================
  
  async createPersona(data: PersonaCreate): Promise<Persona> {
    const response = await apiClient.post(`${BASE_URL}/personas`, data);
    return response.data;
  }
  
  async getPersonas(): Promise<Persona[]> {
    const response = await apiClient.get(`${BASE_URL}/personas`);
    return response.data;
  }
  
  async updatePersona(id: number, data: PersonaUpdate): Promise<Persona> {
    const response = await apiClient.put(`${BASE_URL}/personas/${id}`, data);
    return response.data;
  }
  
  async deletePersona(id: number): Promise<void> {
    await apiClient.delete(`${BASE_URL}/personas/${id}`);
  }
  
  // ==================== 프롬프트 템플릿 관리 ====================
  
  async createPromptTemplate(data: PromptTemplateCreate): Promise<PromptTemplate> {
    const response = await apiClient.post(`${BASE_URL}/prompt-templates`, data);
    return response.data;
  }
  
  async getPromptTemplates(): Promise<PromptTemplate[]> {
    const response = await apiClient.get(`${BASE_URL}/prompt-templates`);
    return response.data;
  }
  
  // ==================== 채팅 관리 ====================
  
  async createChat(data: ChatCreateRequest): Promise<Chat> {
    const response = await apiClient.post(`${BASE_URL}/chats`, data);
    return response.data;
  }
  
  async getChats(skip = 0, limit = 20): Promise<Chat[]> {
    const response = await apiClient.get(`${BASE_URL}/chats`, {
      params: { skip, limit }
    });
    return response.data;
  }
  
  async getChatMessages(chatId: string): Promise<Message[]> {
    const response = await apiClient.get(`${BASE_URL}/chats/${chatId}/messages`);
    return response.data;
  }
  
  async sendMessage(chatId: string, data: MessageSendRequest): Promise<Message> {
    const response = await apiClient.post(`${BASE_URL}/chats/${chatId}/messages`, data);
    return response.data;
  }

  async deleteChat(chatId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete(`${BASE_URL}/chats/${chatId}`);
    return response.data;
  }
  
  // ==================== 피드백 관리 ====================
  
  async addMessageFeedback(messageId: string, feedback: MessageFeedback): Promise<void> {
    await apiClient.post(`${BASE_URL}/messages/${messageId}/feedback`, feedback);
  }
  
  // ==================== 검색 기능 ====================
  
  async searchMessages(query: string): Promise<ChatSearchResult[]> {
    const response = await apiClient.get(`${BASE_URL}/search`, {
      params: { q: query }
    });
    return response.data;
  }
  
  // ==================== 공유 기능 ====================
  
  async createChatShare(chatId: string, data: ChatShareCreate = {}): Promise<ChatShare> {
    const response = await apiClient.post(`${BASE_URL}/chats/${chatId}/share`, data);
    return response.data;
  }
  
  async getSharedChat(shareId: string): Promise<any> {
    const response = await apiClient.get(`${BASE_URL}/share/${shareId}`);
    return response.data;
  }
  
  // ==================== 리소스 조회 ====================
  
  async getAvailableModels(): Promise<LLMModel[]> {
    const response = await apiClient.get(`${BASE_URL}/models`);
    return response.data;
  }
  
  async getRAGDataSources(): Promise<RAGDataSource[]> {
    const response = await apiClient.get(`${BASE_URL}/rag-datasources`);
    return response.data;
  }
  
  // ==================== LLM 모델 관리 ====================
  
  async createLLMModel(data: LLMModelCreate): Promise<LLMModelManagement> {
    const response = await apiClient.post(`${BASE_URL}/admin/models`, data);
    return response.data;
  }
  
  async getLLMModels(): Promise<LLMModelManagement[]> {
    const response = await apiClient.get(`${BASE_URL}/admin/models`);
    return response.data;
  }
  
  async updateLLMModel(id: number, data: LLMModelUpdate): Promise<LLMModelManagement> {
    const response = await apiClient.put(`${BASE_URL}/admin/models/${id}`, data);
    return response.data;
  }
  
  async deleteLLMModel(id: number): Promise<void> {
    await apiClient.delete(`${BASE_URL}/admin/models/${id}`);
  }
  
  // ==================== Ollama 관련 ====================
  
  async getOllamaModels(host: string = 'localhost', port: number = 11434): Promise<any> {
    const response = await apiClient.get(`${BASE_URL}/ollama/models`, {
      params: { host, port }
    });
    return response.data;
  }
}

// 싱글톤 인스턴스 export
export const llmChatApi = new LLMChatApiService(); 