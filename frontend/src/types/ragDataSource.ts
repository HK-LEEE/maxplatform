/**
 * RAG 데이터소스 관련 타입 정의
 */

export interface RAGDataSource {
  id: number;
  name: string;
  description?: string;
  owner_type: 'USER' | 'GROUP';
  owner_id: string;
  chroma_collection_name: string;
  document_count: number;
  is_active: boolean;
  created_at: string;
  last_updated: string;
  embedding_config?: any;
  tags?: string[];
}

export interface RAGDataSourceStats {
  total_datasources: number;
  user_datasources: number;
  group_datasources: number;
  total_documents: number;
  active_datasources: number;
}

export interface RAGDataSourceListItem {
  id: number;
  name: string;
  description?: string;
  owner: {
    type: string;
    id: string;
    name: string;
  };
  document_count: number;
  is_active: boolean;
  created_at: string;
  last_updated: string;
  tags: string[];
}

export interface CreateDataSourceData {
  name: string;
  description?: string;
  owner_type: 'USER' | 'GROUP';
  group_id?: number;
  embedding_config?: any;
}

export interface QueryResult {
  id: string;
  content: string;
  metadata: {
    filename?: string;
    page_number?: number;
    chunk_index?: number;
    [key: string]: any;
  };
  distance: number;
}

export interface QueryRequest {
  query: string;
  n_results?: number;
}

export interface QueryResponse {
  results: QueryResult[];
  query: string;
  total_results: number;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  uploaded_files: number;
  processed_chunks: number;
  failed_files?: string[];
}

export interface Workspace {
  id: number;
  name: string;
  description?: string;
} 