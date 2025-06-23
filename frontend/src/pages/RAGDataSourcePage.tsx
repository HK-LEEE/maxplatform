/**
 * RAG 데이터소스 관리 페이지
 * 
 * 사용자가 RAG용 벡터 DB 데이터소스를 생성, 관리, 문서 업로드, 검색할 수 있는 페이지입니다.
 */

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { 
  Plus, 
  Upload, 
  Search, 
  Trash2, 
  Database, 
  FileText, 
  Users, 
  User,
  AlertCircle,
  CheckCircle,
  Loader,
  RefreshCw,
  Bell,
  Sparkles
} from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';

import CreateDataSourceModal from '../components/RAGDataSource/CreateDataSourceModal';
import UploadDocumentsModal from '../components/RAGDataSource/UploadDocumentsModal';
import DocumentListModal from '../components/RAGDataSource/DocumentListModal';
import ragDataSourceService from '../services/ragDataSourceService';
import {
  RAGDataSourceListItem,
  QueryResult,
  CreateDataSourceData
} from '../types/ragDataSource';

const RAGDataSourcePage: React.FC = () => {
  const [selectedDataSource, setSelectedDataSource] = useState<RAGDataSourceListItem | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isDocumentListModalOpen, setIsDocumentListModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<QueryResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [useHybridSearch, setUseHybridSearch] = useState(true);
  const [searchAnalytics, setSearchAnalytics] = useState(null);

  const queryClient = useQueryClient();

  // RAG 데이터소스 목록 조회
  const { 
    data: dataSources, 
    isLoading: isLoadingDataSources, 
    error,
    refetch: refetchDataSources
  } = useQuery<RAGDataSourceListItem[]>(
    'rag-datasources',
    ragDataSourceService.getDataSources,
    {
      onError: (error: any) => {
        console.error('Failed to fetch data sources:', error);
        toast.error('데이터소스 목록을 불러오는 중 오류가 발생했습니다.');
      }
    }
  );

  // 데이터소스 생성 뮤테이션
  const createDataSourceMutation = useMutation(
    ragDataSourceService.createDataSource,
    {
      onSuccess: (response) => {
        queryClient.invalidateQueries('rag-datasources');
        setIsCreateModalOpen(false);
        toast.success(`데이터소스 "${response.datasource?.name || '새 데이터소스'}"가 성공적으로 생성되었습니다.`);
      },
      onError: (error: any) => {
        console.error('Failed to create data source:', error);
        const errorMessage = error.response?.data?.detail || '데이터소스 생성 중 오류가 발생했습니다.';
        toast.error(errorMessage);
      }
    }
  );

  // 문서 업로드 뮤테이션
  const uploadDocumentsMutation = useMutation(
    ({ dataSourceId, files }: { dataSourceId: number; files: File[] }) => 
      ragDataSourceService.uploadDocuments(dataSourceId, files),
    {
      onSuccess: (response) => {
        queryClient.invalidateQueries('rag-datasources');
        setIsUploadModalOpen(false);
        toast.success(
          `${response.uploaded_files}개 파일이 업로드되어 ${response.processed_chunks}개 청크로 처리되었습니다.`
        );
        
        if (response.failed_files && response.failed_files.length > 0) {
          toast.error(`일부 파일 업로드 실패: ${response.failed_files.join(', ')}`);
        }
        
        // 선택된 데이터소스 정보도 새로고침
        if (selectedDataSource) {
          const updatedDataSource = dataSources?.find(ds => ds.id === selectedDataSource.id);
          if (updatedDataSource) {
            setSelectedDataSource(updatedDataSource);
          }
        }
      },
      onError: (error: any) => {
        console.error('Failed to upload documents:', error);
        const errorMessage = error.response?.data?.detail || '문서 업로드 중 오류가 발생했습니다.';
        toast.error(errorMessage);
      }
    }
  );

  // 데이터소스 삭제 뮤테이션
  const deleteDataSourceMutation = useMutation(
    ragDataSourceService.deleteDataSource,
    {
      onSuccess: (response) => {
        queryClient.invalidateQueries('rag-datasources');
        setSelectedDataSource(null);
        toast.success(response.message || '데이터소스가 성공적으로 삭제되었습니다.');
      },
      onError: (error: any) => {
        console.error('Failed to delete data source:', error);
        const errorMessage = error.response?.data?.detail || '데이터소스 삭제 중 오류가 발생했습니다.';
        toast.error(errorMessage);
      }
    }
  );

  // 고급 문서 검색 (하이브리드 + 분석)
  const handleAdvancedSearch = async () => {
    if (!selectedDataSource || !searchQuery.trim()) return;
    
    setIsSearching(true);
    try {
      const response = await ragDataSourceService.queryDataSourceAdvanced(
        selectedDataSource.id,
        {
          query: searchQuery,
          n_results: 5
        },
        useHybridSearch
      );
      setSearchResults(response.results);
      setSearchAnalytics(response);
      
      if (response.results.length === 0) {
        toast.info('검색 결과가 없습니다. 다른 키워드로 시도해보세요.');
      }
    } catch (error: any) {
      console.error('Advanced search error:', error);
      const errorMessage = error.response?.data?.detail || '고급 검색 중 오류가 발생했습니다.';
      toast.error(errorMessage);
    } finally {
      setIsSearching(false);
    }
  };

  // 데이터소스 선택 시 검색 결과 초기화
  useEffect(() => {
    setSearchResults([]);
    setSearchQuery('');
  }, [selectedDataSource]);

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <AlertCircle className="mx-auto h-16 w-16 text-red-500 mb-4" />
              <h3 className="text-xl font-medium text-gray-900 mb-2">데이터 로딩 오류</h3>
              <p className="text-gray-500 mb-4">RAG 데이터소스를 불러오는 중 오류가 발생했습니다.</p>
              <button
                onClick={() => refetchDataSources()}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700 mx-auto"
              >
                <RefreshCw className="h-4 w-4" />
                다시 시도
              </button>
            </div>
          </div>
        </div>
        <Toaster position="top-right" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* 액션 버튼들 */}
        <div className="flex items-center justify-end space-x-3 mb-6">
          <button
            onClick={() => refetchDataSources()}
            className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 rounded-xl hover:bg-gray-50 transition-colors shadow-sm"
          >
            <RefreshCw className="w-4 h-4" />
            <span>새로고침</span>
          </button>
          
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors shadow-sm hover:shadow-md"
          >
            <Plus className="w-4 h-4" />
            <span>새 데이터소스</span>
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 데이터소스 목록 */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="p-4 border-b">
                <h2 className="font-semibold text-gray-900">
                  데이터소스 목록 ({dataSources?.length || 0})
                </h2>
              </div>
              <div className="divide-y max-h-96 overflow-y-auto">
                {isLoadingDataSources ? (
                  <div className="p-6 text-center">
                    <Loader className="animate-spin h-8 w-8 mx-auto mb-2 text-blue-600" />
                    <p className="text-sm text-gray-500">로딩 중...</p>
                  </div>
                ) : dataSources?.length === 0 ? (
                  <div className="p-6 text-center">
                    <Database className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500 mb-2">생성된 데이터소스가 없습니다</p>
                    <button
                      onClick={() => setIsCreateModalOpen(true)}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                    >
                      첫 번째 데이터소스 생성하기
                    </button>
                  </div>
                ) : (
                  dataSources?.map((ds) => (
                    <div
                      key={ds.id}
                      onClick={() => setSelectedDataSource(ds)}
                      className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                        selectedDataSource?.id === ds.id ? 'bg-blue-50 border-r-2 border-blue-500' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-gray-900 truncate">{ds.name}</h3>
                          {ds.description && (
                            <p className="text-sm text-gray-500 mt-1 line-clamp-2">{ds.description}</p>
                          )}
                          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                            <div className="flex items-center gap-1">
                              {ds.owner.type === 'WORKSPACE' ? (
                                <Users className="h-3 w-3" />
                              ) : (
                                <User className="h-3 w-3" />
                              )}
                              <span className="truncate">{ds.owner.name}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <FileText className="h-3 w-3" />
                              {ds.document_count}개
                            </div>
                          </div>
                        </div>
                        {!ds.is_active && (
                          <div className="flex-shrink-0 w-2 h-2 bg-red-500 rounded-full" title="비활성" />
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* 상세 정보 및 검색 */}
          <div className="lg:col-span-2">
            {selectedDataSource ? (
              <div className="space-y-6">
                {/* 데이터소스 정보 */}
                <div className="bg-white rounded-lg shadow-sm border">
                  <div className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h2 className="text-xl font-semibold text-gray-900">
                            {selectedDataSource.name}
                          </h2>
                          {selectedDataSource.is_active ? (
                            <CheckCircle className="h-5 w-5 text-green-500" title="활성" />
                          ) : (
                            <AlertCircle className="h-5 w-5 text-red-500" title="비활성" />
                          )}
                        </div>
                        {selectedDataSource.description && (
                          <p className="text-gray-600">{selectedDataSource.description}</p>
                        )}
                      </div>
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setIsUploadModalOpen(true);
                          }}
                          className="bg-green-600 text-white px-3 py-2 rounded text-sm flex items-center gap-1 hover:bg-green-700"
                          disabled={!selectedDataSource.is_active}
                        >
                          <Upload className="h-4 w-4" />
                          문서 업로드
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setIsDocumentListModalOpen(true);
                          }}
                          className="bg-blue-600 text-white px-3 py-2 rounded text-sm flex items-center gap-1 hover:bg-blue-700"
                          disabled={!selectedDataSource.is_active}
                        >
                          <FileText className="h-4 w-4" />
                          문서 관리
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm(`"${selectedDataSource.name}" 데이터소스를 정말로 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없으며, 모든 문서와 벡터 데이터가 삭제됩니다.`)) {
                              deleteDataSourceMutation.mutate(selectedDataSource.id);
                            }
                          }}
                          className="bg-red-600 text-white px-3 py-2 rounded text-sm flex items-center gap-1 hover:bg-red-700"
                          disabled={deleteDataSourceMutation.isLoading}
                        >
                          {deleteDataSourceMutation.isLoading ? (
                            <Loader className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                          삭제
                        </button>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">소유자:</span>
                        <span className="ml-2 font-medium">{selectedDataSource.owner.name}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">문서 수:</span>
                        <span className="ml-2 font-medium">{selectedDataSource.document_count}개</span>
                      </div>
                      <div>
                        <span className="text-gray-500">생성일:</span>
                        <span className="ml-2 font-medium">
                          {new Date(selectedDataSource.created_at).toLocaleString('ko-KR')}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">마지막 업데이트:</span>
                        <span className="ml-2 font-medium">
                          {new Date(selectedDataSource.last_updated).toLocaleString('ko-KR')}
                        </span>
                      </div>
                    </div>

                    {selectedDataSource.tags && selectedDataSource.tags.length > 0 && (
                      <div className="mt-4">
                        <span className="text-gray-500 text-sm">태그:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {selectedDataSource.tags.map((tag, index) => (
                            <span
                              key={index}
                              className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* 문서 검색 */}
                <div className="bg-white rounded-lg shadow-sm border">
                  <div className="p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">문서 검색</h3>
                    <div className="flex gap-2 mb-4">
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="검색할 내용을 입력하세요... (예: 데이터베이스 설정 방법)"
                        className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        onKeyPress={(e) => e.key === 'Enter' && handleAdvancedSearch()}
                        disabled={!selectedDataSource.is_active}
                      />
                      <div className="flex items-center gap-2">
                        <label className="flex items-center gap-1 text-sm">
                          <input
                            type="checkbox"
                            checked={useHybridSearch}
                            onChange={(e) => setUseHybridSearch(e.target.checked)}
                            className="rounded"
                          />
                          하이브리드 검색
                        </label>
                      </div>
                      <button
                        onClick={handleAdvancedSearch}
                        disabled={isSearching || !searchQuery.trim() || !selectedDataSource.is_active}
                        className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700 disabled:opacity-50"
                      >
                        {isSearching ? (
                          <Loader className="h-4 w-4 animate-spin" />
                        ) : (
                          <Search className="h-4 w-4" />
                        )}
                        검색
                      </button>
                    </div>

                    {!selectedDataSource.is_active && (
                      <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <p className="text-yellow-800 text-sm">
                          ⚠️ 이 데이터소스는 현재 비활성 상태입니다. 검색 및 업로드가 제한됩니다.
                        </p>
                      </div>
                    )}

                    {/* 검색 분석 정보 */}
                    {searchAnalytics && (
                      <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                        <h4 className="font-medium text-gray-900 mb-2">검색 분석</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-gray-500">검색 방식:</span>
                            <span className="ml-2 font-medium">
                              {searchAnalytics.search_type === 'hybrid' ? '하이브리드' : '벡터'}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">검색 시간:</span>
                            <span className="ml-2 font-medium">
                              {searchAnalytics.performance_metrics?.search_time_ms}ms
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">품질 점수:</span>
                            <span className="ml-2 font-medium">
                              {searchAnalytics.quality_metrics?.quality_score}/100
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">다양성:</span>
                            <span className="ml-2 font-medium">
                              {searchAnalytics.quality_metrics?.diversity_score}/100
                            </span>
                          </div>
                        </div>
                        {searchAnalytics.quality_metrics?.recommendations && (
                          <div className="mt-2">
                            <span className="text-gray-500 text-sm">권장사항:</span>
                            <ul className="mt-1 text-sm text-gray-600">
                              {searchAnalytics.quality_metrics.recommendations.map((rec, index) => (
                                <li key={index} className="flex items-start gap-1">
                                  <span className="text-blue-500">•</span>
                                  {rec}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    {/* 검색 결과 */}
                    {searchResults.length > 0 && (
                      <div className="space-y-3">
                        <h4 className="font-medium text-gray-900">
                          검색 결과 ({searchResults.length}개)
                        </h4>
                        {searchResults.map((result, index) => (
                          <div key={result.id} className="border rounded-lg p-4 hover:bg-gray-50">
                            <div className="flex justify-between items-start mb-2">
                              <span className="text-sm font-medium text-blue-600">
                                #{index + 1}
                              </span>
                              <div className="text-xs text-gray-500 flex gap-2">
                                <span>유사도: {result.similarity?.toFixed(3)}</span>
                                {result.vector_score && (
                                  <>
                                    <span>벡터: {result.vector_score.toFixed(3)}</span>
                                    <span>키워드: {result.keyword_score.toFixed(3)}</span>
                                  </>
                                )}
                              </div>
                            </div>
                            <p className="text-gray-700 text-sm leading-relaxed mb-2">
                              {result.content}
                            </p>
                            {(result.metadata?.filename || result.metadata?.page_number) && (
                              <div className="text-xs text-gray-500 flex gap-4">
                                {result.metadata.filename && (
                                  <span>📄 {result.metadata.filename}</span>
                                )}
                                {result.metadata.page_number && (
                                  <span>📖 {result.metadata.page_number}페이지</span>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {searchQuery && searchResults.length === 0 && !isSearching && (
                      <div className="text-center py-8">
                        <Search className="h-12 w-12 text-gray-300 mx-auto mb-2" />
                        <p className="text-gray-500">검색 결과가 없습니다</p>
                        <p className="text-sm text-gray-400">다른 키워드로 검색해보세요</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
                <Database className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">데이터소스를 선택하세요</h3>
                <p className="text-gray-500">
                  왼쪽 목록에서 데이터소스를 선택하여 상세 정보를 확인하고 검색할 수 있습니다
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 모달들 */}
      <CreateDataSourceModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={(data: CreateDataSourceData) => createDataSourceMutation.mutate(data)}
        isLoading={createDataSourceMutation.isLoading}
      />

      <UploadDocumentsModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSubmit={(files: File[]) => {
          if (selectedDataSource) {
            uploadDocumentsMutation.mutate({
              dataSourceId: selectedDataSource.id,
              files
            });
          }
        }}
        isLoading={uploadDocumentsMutation.isLoading}
        dataSourceName={selectedDataSource?.name || ''}
      />

      {selectedDataSource && (
        <DocumentListModal
          isOpen={isDocumentListModalOpen}
          onClose={() => setIsDocumentListModalOpen(false)}
          dataSourceId={selectedDataSource.id}
          dataSourceName={selectedDataSource.name}
        />
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
          success: {
            iconTheme: {
              primary: '#10B981',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#EF4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </div>
  );
};

export default RAGDataSourcePage; 