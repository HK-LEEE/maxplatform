/**
 * 문서 목록 및 관리 모달 컴포넌트
 */

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { 
  X, 
  FileText, 
  File, 
  Search, 
  Trash2, 
  HardDrive, 
  Clock, 
  User, 
  Folder,
  AlertTriangle
} from 'lucide-react';
import ragDataSourceService from '../../services/ragDataSourceService';

// 백엔드에서 실제로 반환하는 문서 구조에 맞게 수정
interface Document {
  id: string;
  content: string;      // 미리보기 콘텐츠
  full_content: string; // 전체 콘텐츠
  metadata: {
    filename?: string;
    file_size?: number;
    upload_time?: string;
    uploaded_by?: string;
    chunk_index?: number;
    total_chunks?: number;
    [key: string]: any;
  };
}

interface DocumentListResponse {
  documents: Document[];
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

interface StoredFile {
  filename: string;
  file_path: string;
  file_size: number;
  created_time: string;
  modified_time: string;
  relative_path: string;
}

interface StorageStats {
  owner_type: string;
  owner_id: string;
  total_size_bytes: number;
  total_size_mb: number;
  file_count: number;
  storage_path: string;
}

interface DocumentListModalProps {
  isOpen: boolean;
  onClose: () => void;
  dataSourceId: number;
  dataSourceName: string;
}

const DocumentListModal: React.FC<DocumentListModalProps> = ({
  isOpen,
  onClose,
  dataSourceId,
  dataSourceName
}) => {
  const [activeTab, setActiveTab] = useState<'documents' | 'files'>('documents');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 상태 관리
  const [documents, setDocuments] = useState<Document[]>([]);
  const [pagination, setPagination] = useState<any>(null);
  const [storedFiles, setStoredFiles] = useState<StoredFile[]>([]);
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);

  const queryClient = useQueryClient();

  // 파일 목록 조회 쿼리
  const { data: storedFilesData, isLoading, error: queryError } = useQuery(
    ['ragDataSource', dataSourceId, 'storedFiles'],
    () => ragDataSourceService.getStoredFiles(dataSourceId),
    {
      enabled: isOpen && activeTab === 'files',
      onSuccess: (data) => {
        setStoredFiles(data.stored_files || []);
        setStorageStats(data.storage_stats || null);
      },
      onError: (err: any) => {
        console.error('Failed to fetch stored files:', err);
        setError('파일 목록을 불러오는데 실패했습니다.');
      }
    }
  );

  // 문서 삭제 mutation
  const deleteDocumentMutation = useMutation(
    (documentId: string) => ragDataSourceService.deleteDocument(dataSourceId, documentId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['ragDataSource', dataSourceId]);
        fetchDocuments(); // 문서 목록 새로고침
      },
      onError: (error: any) => {
        console.error('Failed to delete document:', error);
        alert('문서 삭제에 실패했습니다.');
      }
    }
  );

  // 저장된 파일 삭제 mutation
  const deleteStoredFileMutation = useMutation(
    (filePath: string) => ragDataSourceService.deleteStoredFile(dataSourceId, filePath),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['ragDataSource', dataSourceId, 'storedFiles']);
      },
      onError: (error: any) => {
        console.error('Failed to delete stored file:', error);
        alert('파일 삭제에 실패했습니다.');
      }
    }
  );

  // 문서 목록 조회 함수
  const fetchDocuments = async () => {
    if (!isOpen || activeTab !== 'documents') return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await ragDataSourceService.getDocuments(dataSourceId, currentPage, 20);
      
      // 백엔드 응답 구조에 맞게 처리
      if (response.documents) {
        setDocuments(response.documents);
      } else {
        setDocuments([]);
      }
      
      if (response.pagination) {
        setPagination(response.pagination);
      } else {
        // 구버전 응답 구조 호환성
        setPagination({
          page: response.page || currentPage,
          page_size: response.page_size || 20,
          total_count: response.total_count || 0,
          total_pages: response.total_pages || 1,
          has_next: (response.page || currentPage) < (response.total_pages || 1),
          has_prev: (response.page || currentPage) > 1
        });
      }
    } catch (err: any) {
      console.error('Failed to fetch documents:', err);
      setError('문서 목록을 불러오는데 실패했습니다.');
      setDocuments([]);
      setPagination(null);
    } finally {
      setLoading(false);
    }
  };

  // 저장된 파일 목록 조회 함수
  const fetchStoredFiles = async () => {
    if (!isOpen || activeTab !== 'files') return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await ragDataSourceService.getStoredFiles(dataSourceId);
      setStoredFiles(response.stored_files || []);
      setStorageStats(response.storage_stats || null);
    } catch (err: any) {
      console.error('Failed to fetch stored files:', err);
      setError('파일 목록을 불러오는데 실패했습니다.');
      setStoredFiles([]);
      setStorageStats(null);
    } finally {
      setLoading(false);
    }
  };

  // 문서 삭제
  const deleteDocument = async (documentId: string) => {
    if (!window.confirm('이 문서를 삭제하시겠습니까?')) {
      return;
    }

    try {
      await deleteDocumentMutation.mutateAsync(documentId);
      
      // 선택된 문서에서 제거
      const newSelected = new Set(selectedDocuments);
      newSelected.delete(documentId);
      setSelectedDocuments(newSelected);
      
    } catch (error) {
      console.error('Document deletion failed:', error);
    }
  };

  // 저장된 파일 삭제
  const deleteStoredFile = async (filePath: string) => {
    if (!window.confirm('이 파일을 삭제하시겠습니까?')) {
      return;
    }

    try {
      await deleteStoredFileMutation.mutateAsync(filePath);
    } catch (error) {
      console.error('Stored file deletion failed:', error);
    }
  };

  // 선택된 문서들 일괄 삭제
  const handleBulkDelete = async () => {
    if (selectedDocuments.size === 0) return;
    
    if (!window.confirm(`선택된 ${selectedDocuments.size}개의 문서를 삭제하시겠습니까?`)) {
      return;
    }

    try {
      for (const documentId of selectedDocuments) {
        await ragDataSourceService.deleteDocument(dataSourceId, documentId);
      }
      
      setSelectedDocuments(new Set());
      fetchDocuments(); // 목록 새로고침
      queryClient.invalidateQueries(['ragDataSource', dataSourceId]);
      
    } catch (error) {
      console.error('Bulk deletion failed:', error);
      alert('일부 문서 삭제에 실패했습니다.');
    }
  };

  // 파일 크기 포맷팅
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 날짜 포맷팅
  const formatDate = (dateString: string) => {
    if (!dateString) return '알 수 없음';
    return new Date(dateString).toLocaleString('ko-KR');
  };

  // 필터링된 문서 목록 - null 체크 추가
  const filteredDocuments = documents?.filter(doc => {
    const filename = doc.metadata?.filename || '';
    const content = doc.content || '';
    const searchLower = searchTerm.toLowerCase();
    
    return filename.toLowerCase().includes(searchLower) ||
           content.toLowerCase().includes(searchLower);
  }) || [];

  const filteredFiles = storedFiles.filter(file => {
    const filename = file?.filename || '';
    return filename.toLowerCase().includes(searchTerm.toLowerCase());
  });

  // 페이지 변경 시 문서 새로고침
  useEffect(() => {
    if (isOpen && activeTab === 'documents') {
      fetchDocuments();
    }
  }, [isOpen, currentPage, activeTab]);

  // 탭 변경 시 데이터 로드
  useEffect(() => {
    if (isOpen) {
      if (activeTab === 'documents') {
        fetchDocuments();
      } else if (activeTab === 'files') {
        fetchStoredFiles();
      }
    }
  }, [isOpen, activeTab]);

  // 모달이 닫힐 때 상태 초기화
  useEffect(() => {
    if (!isOpen) {
      setSearchTerm('');
      setSelectedDocuments(new Set());
      setCurrentPage(1);
      setError(null);
      setDocuments([]);
      setPagination(null);
      setStoredFiles([]);
      setStorageStats(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl h-5/6 flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              {dataSourceName} - 콘텐츠 관리
            </h2>
            {storageStats && (
              <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                <div className="flex items-center gap-1">
                  <HardDrive className="w-4 h-4" />
                  <span>저장소 사용량: {formatFileSize(storageStats.total_size_bytes)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Folder className="w-4 h-4" />
                  <span>파일 수: {storageStats.file_count}개</span>
                </div>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab('documents')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'documents'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              문서 청크
            </div>
          </button>
          <button
            onClick={() => setActiveTab('files')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'files'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <File className="w-4 h-4" />
              원본 파일
            </div>
          </button>
        </div>

        {/* 검색 및 액션 바 */}
        <div className="p-4 border-b bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder={activeTab === 'documents' ? "문서 검색..." : "파일 검색..."}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            {selectedDocuments.size > 0 && (
              <button
                onClick={handleBulkDelete}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                선택 삭제 ({selectedDocuments.size})
              </button>
            )}
          </div>
        </div>

        {/* 문서 목록 */}
        <div className="flex-1 overflow-auto">
          {(loading || isLoading) ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-600">
                  {activeTab === 'documents' ? '문서 목록을 불러오는 중...' : '파일 목록을 불러오는 중...'}
                </p>
              </div>
            </div>
          ) : (error || queryError) ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-red-600">
                <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
                <p>{error || '데이터를 불러오는데 실패했습니다.'}</p>
              </div>
            </div>
          ) : activeTab === 'documents' ? (
            filteredDocuments.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-gray-500">
                  <FileText className="w-8 h-8 mx-auto mb-2" />
                  <p>문서가 없습니다.</p>
                </div>
              </div>
            ) : (
              <div className="p-4">
                <div className="grid gap-4">
                  {filteredDocuments.map((doc) => (
                    <div
                      key={doc.id}
                      className={`border rounded-lg p-4 hover:shadow-md transition-shadow ${
                        selectedDocuments.has(doc.id) ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3 flex-1">
                          <input
                            type="checkbox"
                            checked={selectedDocuments.has(doc.id)}
                            onChange={(e) => {
                              const newSelected = new Set(selectedDocuments);
                              if (e.target.checked) {
                                newSelected.add(doc.id);
                              } else {
                                newSelected.delete(doc.id);
                              }
                              setSelectedDocuments(newSelected);
                            }}
                            className="mt-1"
                          />
                          
                          <FileText className="w-5 h-5 text-blue-600 mt-1 flex-shrink-0" />
                          
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium text-gray-900 truncate">
                              {doc.metadata?.filename || `문서 ${doc.id}`}
                            </h3>
                            
                            <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                              {doc.metadata?.file_size && (
                                <span className="flex items-center gap-1">
                                  <HardDrive className="w-3 h-3" />
                                  {formatFileSize(doc.metadata.file_size)}
                                </span>
                              )}
                              {doc.metadata?.upload_time && (
                                <span className="flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  {formatDate(doc.metadata.upload_time)}
                                </span>
                              )}
                              {doc.metadata?.uploaded_by && (
                                <span className="flex items-center gap-1">
                                  <User className="w-3 h-3" />
                                  {doc.metadata.uploaded_by}
                                </span>
                              )}
                            </div>
                            
                            <div className="mt-2 text-sm text-gray-600">
                              <p className="line-clamp-2">{doc.content || '내용이 없습니다.'}</p>
                            </div>
                            
                            <div className="mt-2 text-xs text-gray-400">
                              {doc.metadata?.chunk_index !== undefined && doc.metadata?.total_chunks && (
                                <span>청크 {doc.metadata.chunk_index + 1}/{doc.metadata.total_chunks} • </span>
                              )}
                              내용 길이: {(doc.full_content?.length || doc.content?.length || 0).toLocaleString()}자
                            </div>
                          </div>
                        </div>
                        
                        <button
                          onClick={() => deleteDocument(doc.id)}
                          disabled={deleteDocumentMutation.isLoading}
                          className="ml-4 p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                          title="문서 삭제"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 페이지네이션 */}
                {pagination && pagination.total_pages > 1 && (
                  <div className="mt-6 flex items-center justify-between">
                    <div className="text-sm text-gray-700">
                      총 {pagination.total_count}개 문서 중 {((pagination.page - 1) * pagination.page_size) + 1}-
                      {Math.min(pagination.page * pagination.page_size, pagination.total_count)}개 표시
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {pagination.has_prev && (
                        <button
                          onClick={() => setCurrentPage(currentPage - 1)}
                          className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50"
                        >
                          이전
                        </button>
                      )}
                      
                      <span className="px-3 py-1">
                        {pagination.page} / {pagination.total_pages}
                      </span>
                      
                      {pagination.has_next && (
                        <button
                          onClick={() => setCurrentPage(currentPage + 1)}
                          className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50"
                        >
                          다음
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          ) : (
            // 파일 목록 탭
            filteredFiles.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-gray-500">
                  <File className="w-8 h-8 mx-auto mb-2" />
                  <p>저장된 파일이 없습니다.</p>
                </div>
              </div>
            ) : (
              <div className="p-4">
                <div className="grid gap-4">
                  {filteredFiles.map((file) => (
                    <div
                      key={file.file_path}
                      className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3 flex-1">
                          <File className="w-5 h-5 text-green-600 mt-1 flex-shrink-0" />
                          
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium text-gray-900 truncate">
                              {file.filename}
                            </h3>
                            
                            <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                              <span className="flex items-center gap-1">
                                <HardDrive className="w-3 h-3" />
                                {formatFileSize(file.file_size)}
                              </span>
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {formatDate(file.created_time)}
                              </span>
                            </div>
                            
                            <div className="mt-2 text-xs text-gray-400">
                              경로: {file.relative_path}
                            </div>
                          </div>
                        </div>
                        
                        <button
                          onClick={() => deleteStoredFile(file.file_path)}
                          disabled={deleteStoredFileMutation.isLoading}
                          className="ml-4 p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                          title="파일 삭제"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
};

export default DocumentListModal; 