/**
 * RAG 데이터소스 API 서비스
 */

import axios from 'axios';
import {
  RAGDataSource,
  RAGDataSourceListItem,
  CreateDataSourceData,
  QueryRequest,
  QueryResponse,
  UploadResponse,
  Workspace
} from '../types/ragDataSource';

const API_BASE_URL = '/api/llmops';

// axios 인터셉터 설정 - 모든 요청에 자동으로 토큰 포함
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 401 오류 시 로그인 페이지로 리다이렉트
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 토큰이 만료되었거나 유효하지 않음
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

class RAGDataSourceService {
  /**
   * RAG 데이터소스 목록 조회
   */
  async getDataSources(): Promise<RAGDataSourceListItem[]> {
    try {
      const response = await axios.get(`${API_BASE_URL}/rag-datasources`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch RAG data sources:', error);
      throw error;
    }
  }

  /**
   * 특정 RAG 데이터소스 상세 정보 조회
   */
  async getDataSource(id: number): Promise<RAGDataSource> {
    try {
      const response = await axios.get(`${API_BASE_URL}/rag-datasources/${id}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch RAG data source ${id}:`, error);
      throw error;
    }
  }

  /**
   * 새 RAG 데이터소스 생성
   */
  async createDataSource(data: CreateDataSourceData): Promise<{ success: boolean; message: string; datasource: any }> {
    try {
      const response = await axios.post(`${API_BASE_URL}/rag-datasources`, data);
      return response.data;
    } catch (error) {
      console.error('Failed to create RAG data source:', error);
      throw error;
    }
  }

  /**
   * RAG 데이터소스 삭제
   */
  async deleteDataSource(id: number): Promise<{ success: boolean; message: string }> {
    try {
      const response = await axios.delete(`${API_BASE_URL}/rag-datasources/${id}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to delete RAG data source ${id}:`, error);
      throw error;
    }
  }

  /**
   * 문서 업로드
   */
  async uploadDocuments(dataSourceId: number, files: File[]): Promise<UploadResponse> {
    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));
      
      const response = await axios.post(
        `${API_BASE_URL}/rag-datasources/${dataSourceId}/documents`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      return response.data;
    } catch (error) {
      console.error(`Failed to upload documents to data source ${dataSourceId}:`, error);
      throw error;
    }
  }

  /**
   * 문서 검색
   */
  async queryDataSource(dataSourceId: number, query: QueryRequest): Promise<QueryResponse> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/rag-datasources/${dataSourceId}/query`,
        query
      );
      return response.data;
    } catch (error) {
      console.error(`Failed to query data source ${dataSourceId}:`, error);
      throw error;
    }
  }

  /**
   * 워크스페이스 목록 조회
   */
  async getWorkspaces(): Promise<Workspace[]> {
    try {
      const response = await axios.get('/api/workspaces');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch workspaces:', error);
      // 실패 시 빈 배열 반환
      return [];
    }
  }

  /**
   * 헬스 체크
   */
  async healthCheck(): Promise<{ status: string; message: string }> {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      return response.data;
    } catch (error) {
      console.error('RAG service health check failed:', error);
      throw error;
    }
  }

  /**
   * 문서 목록 조회
   */
  async getDocuments(dataSourceId: number, page: number = 1, pageSize: number = 20) {
    try {
      const response = await axios.get(`${API_BASE_URL}/rag-datasources/${dataSourceId}/documents`, {
        params: { page, page_size: pageSize }
      });
      return response.data;
    } catch (error) {
      console.error(`Failed to get documents from data source ${dataSourceId}:`, error);
      throw error;
    }
  }

  /**
   * 개별 문서 삭제
   */
  async deleteDocument(dataSourceId: number, documentId: string) {
    try {
      const response = await axios.delete(`${API_BASE_URL}/rag-datasources/${dataSourceId}/documents/${documentId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to delete document ${documentId} from data source ${dataSourceId}:`, error);
      throw error;
    }
  }

  /**
   * 고급 문서 검색 (하이브리드 검색 + 분석)
   */
  async queryDataSourceAdvanced(dataSourceId: number, query: QueryRequest, useHybrid: boolean = true): Promise<any> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/rag-datasources/${dataSourceId}/query-advanced?use_hybrid=${useHybrid}`,
        query
      );
      return response.data;
    } catch (error) {
      console.error(`Failed to perform advanced query on data source ${dataSourceId}:`, error);
      throw error;
    }
  }

  /**
   * 저장된 파일 목록 조회
   */
  async getStoredFiles(dataSourceId: number): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE_URL}/rag-datasources/${dataSourceId}/stored-files`);
      return response.data;
    } catch (error) {
      console.error(`Failed to get stored files from data source ${dataSourceId}:`, error);
      throw error;
    }
  }

  /**
   * 저장된 파일 삭제
   */
  async deleteStoredFile(dataSourceId: number, filePath: string): Promise<any> {
    try {
      const response = await axios.delete(`${API_BASE_URL}/rag-datasources/${dataSourceId}/stored-files`, {
        params: { file_path: filePath }
      });
      return response.data;
    } catch (error) {
      console.error(`Failed to delete stored file ${filePath} from data source ${dataSourceId}:`, error);
      throw error;
    }
  }

  /**
   * 데이터소스의 모든 문서 삭제
   */
  async clearDataSourceDocuments(dataSourceId: number): Promise<any> {
    try {
      const response = await axios.delete(`${API_BASE_URL}/rag-datasources/${dataSourceId}/documents`);
      return response.data;
    } catch (error) {
      console.error(`Failed to clear documents from data source ${dataSourceId}:`, error);
      throw error;
    }
  }
}

// 싱글톤 인스턴스 생성
const ragDataSourceService = new RAGDataSourceService();

export default ragDataSourceService; 