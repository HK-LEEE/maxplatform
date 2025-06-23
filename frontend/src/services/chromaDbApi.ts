interface ChromaCollection {
  id: string;
  name: string;
  display_name?: string;
  description?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  owner_type: 'user' | 'group';
  owner_id: string;
  is_active: boolean;
}



class ChromaDbApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';
  }

  private getAuthToken(): string | null {
    return localStorage.getItem('token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    try {
      const token = this.getAuthToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...options.headers as Record<string, string>,
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        headers,
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('ChromaDB API request failed:', error);
      throw error;
    }
  }

  /**
   * 사용자/그룹 권한에 따른 Collection 목록 조회
   */
  async getCollections(userInfo: {
    user_id: string;
    group_id?: string;
    owner_type: 'user' | 'group';
  }): Promise<ChromaCollection[]> {
    const params = new URLSearchParams({
      owner_type: userInfo.owner_type,
      owner_id: userInfo.owner_type === 'user' ? userInfo.user_id : (userInfo.group_id || ''),
    });

    const response = await this.request<ChromaCollection[]>(
      `/api/chroma/collections?${params.toString()}`
    );

    return response;
  }

  /**
   * Collection 상세 정보 조회
   */
  async getCollection(collectionId: string): Promise<ChromaCollection> {
    const response = await this.request<ChromaCollection>(
      `/api/chroma/collections/${collectionId}`
    );

    return response;
  }

  /**
   * Collection 생성
   */
  async createCollection(collectionData: {
    name: string;
    metadata?: Record<string, any>;
    owner_type: 'user' | 'group';
    owner_id: string;
  }): Promise<ChromaCollection> {
    const response = await this.request<ChromaCollection>(
      '/api/chroma/collections',
      {
        method: 'POST',
        body: JSON.stringify(collectionData),
      }
    );

    return response;
  }

  /**
   * Collection 삭제
   */
  async deleteCollection(collectionId: string): Promise<void> {
    await this.request<void>(`/api/chroma/collections/${collectionId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Collection에 문서 추가
   */
  async addDocuments(collectionId: string, documents: {
    documents: string[];
    metadatas?: Record<string, any>[];
    ids?: string[];
  }): Promise<void> {
    await this.request<void>(`/api/chroma/collections/${collectionId}/documents`, {
      method: 'POST',
      body: JSON.stringify(documents),
    });
  }

  /**
   * Collection에서 문서 검색
   */
  async queryDocuments(collectionId: string, query: {
    query_texts: string[];
    n_results?: number;
    where?: Record<string, any>;
    include?: string[];
  }): Promise<any> {
    const response = await this.request<any>(
      `/api/chroma/collections/${collectionId}/query`,
      {
        method: 'POST',
        body: JSON.stringify(query),
      }
    );

    return response;
  }
}

export const chromaDbApi = new ChromaDbApiService();
export type { ChromaCollection }; 