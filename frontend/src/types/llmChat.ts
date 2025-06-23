/**
 * LLM 채팅 서비스 타입 정의
 */

export type OwnerType = 'USER' | 'GROUP';
export type SenderType = 'USER' | 'AI';
export type FeedbackRating = 'LIKE' | 'DISLIKE';
export type PublishScope = 'EVERYONE' | 'GROUP' | 'USER';
export type ModelType = 'AZURE_OPENAI' | 'AZURE_CLAUDE' | 'AZURE_DEEPSEEK' | 'OLLAMA' | 'FLOWSTUDIO';

// 페르소나 관련
export interface Persona {
  id: number;
  persona_name: string;
  system_prompt: string;
  owner_type: OwnerType;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface PersonaCreate {
  persona_name: string;
  system_prompt: string;
  owner_type?: OwnerType;
  owner_id?: string;
}

export interface PersonaUpdate {
  persona_name?: string;
  system_prompt?: string;
}

// 프롬프트 템플릿 관련
export interface PromptTemplate {
  id: number;
  template_title: string;
  template_content: string;
  owner_type: OwnerType;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface PromptTemplateCreate {
  template_title: string;
  template_content: string;
  owner_type?: OwnerType;
  owner_id?: string;
}

// 채팅 관련
export interface Chat {
  id: string;
  user_id: string;
  model_id: string;
  persona_id?: number;
  title: string;
  created_at: string;
  updated_at: string;
  persona?: Persona;
}

export interface ChatCreateRequest {
  title: string;
  model_id: string;
  persona_id?: number;
  initial_message?: string;
}

export interface Message {
  id: string;
  chat_id: string;
  sender_type: SenderType;
  content: string;
  message_metadata?: any;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_cost?: number;
  created_at: string;
}

export interface MessageSendRequest {
  content: string;
  rag_datasource_ids?: number[];
}

// 피드백 관련
export interface MessageFeedback {
  rating: FeedbackRating;
  comment?: string;
}

// 검색 관련
export interface ChatSearchResult {
  message_id: string;
  chat_id: string;
  chat_title: string;
  content_snippet: string;
  created_at: string;
}

// 공유 관련
export interface ChatShare {
  share_id: string;
  chat_id: string;
  created_by_user_id: string;
  expires_at?: string;
  created_at: string;
  share_url: string;
}

export interface ChatShareCreate {
  expires_at?: string;
}

// 리소스 정보
export interface LLMModel {
  id: string;
  name: string;
  provider: string;
  description?: string;
  is_available: boolean;
}

export interface RAGDataSource {
  id: number;
  name: string;
  description?: string;
  document_count: number;
  owner_type: OwnerType;
  created_at: string;
}

// UI 상태 관련
// LLM 모델 관리 관련
export interface LLMModelManagement {
  id: number;
  model_name: string;
  model_type: ModelType;
  model_id: string;
  description?: string;
  config: { [key: string]: any };
  owner_type: OwnerType;
  owner_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMModelCreate {
  model_name: string;
  model_type: ModelType;
  model_id: string;
  description?: string;
  config: { [key: string]: any };
  owner_type?: OwnerType;
  owner_id?: string;
}

export interface LLMModelUpdate {
  model_name?: string;
  model_type?: ModelType;
  model_id?: string;
  description?: string;
  config?: { [key: string]: any };
  is_active?: boolean;
}

// UI 상태 관련
export interface ChatUIState {
  selectedChatId?: string;
  isLoading: boolean;
  error?: string;
  searchQuery?: string;
  selectedRAGSources: number[];
  selectedPersona?: number;
  isTyping: boolean;
} 