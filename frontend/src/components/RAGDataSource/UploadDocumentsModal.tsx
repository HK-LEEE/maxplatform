/**
 * 문서 업로드 모달 컴포넌트
 */

import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, Trash2, Loader, AlertCircle, CheckCircle, Clock } from 'lucide-react';

interface UploadDocumentsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (files: File[]) => void;
  isLoading: boolean;
  dataSourceName: string;
}

const UploadDocumentsModal: React.FC<UploadDocumentsModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
  dataSourceName
}) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState<'준비' | '업로드' | '처리' | '완료'>('준비');

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'application/pdf': ['.pdf'],
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    onDrop: (acceptedFiles, rejectedFiles) => {
      if (rejectedFiles.length > 0) {
        const errorMessage = rejectedFiles.map(file => 
          `${file.file.name}: ${file.errors.map(e => e.message).join(', ')}`
        ).join('\n');
        setError(errorMessage);
      } else {
        setError(null);
      }
      
      setSelectedFiles(prev => [...prev, ...acceptedFiles]);
    },
    onDropRejected: () => {
      setError('지원하지 않는 파일 형식이거나 파일 크기가 너무 큽니다. (최대 10MB)');
    }
  });

  const handleSubmit = () => {
    if (selectedFiles.length === 0) return;
    
    // 진행률 시뮬레이션 시작
    setUploadProgress(0);
    setUploadStage('업로드');
    
    // 실제 업로드 진행률을 시뮬레이션
    const progressInterval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev < 30) {
          return prev + Math.random() * 10;
        } else if (prev < 60) {
          setUploadStage('처리');
          return prev + Math.random() * 5;
        } else if (prev < 90) {
          return prev + Math.random() * 3;
        } else if (prev < 95) {
          return prev + 0.5;
        }
        return prev;
      });
    }, 200);

    // 실제 업로드 실행
    onSubmit(selectedFiles);

    // 업로드 완료 후 정리 (실제로는 onSubmit의 성공/실패 콜백에서 처리해야 함)
    setTimeout(() => {
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadStage('완료');
    }, 3000);
  };

  const handleClose = () => {
    setSelectedFiles([]);
    setError(null);
    setUploadProgress(0);
    setUploadStage('준비');
    onClose();
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    setError(null);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStageIcon = () => {
    switch (uploadStage) {
      case '준비':
        return <Upload className="h-4 w-4" />;
      case '업로드':
        return <Upload className="h-4 w-4 animate-bounce" />;
      case '처리':
        return <Clock className="h-4 w-4 animate-spin" />;
      case '완료':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      default:
        return <Upload className="h-4 w-4" />;
    }
  };

  const getStageMessage = () => {
    switch (uploadStage) {
      case '준비':
        return '업로드 준비 중...';
      case '업로드':
        return '파일을 서버로 전송 중...';
      case '처리':
        return '문서를 분석하고 벡터화 중...';
      case '완료':
        return '업로드가 완료되었습니다!';
      default:
        return '';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-semibold mb-4">
          문서 업로드 - {dataSourceName}
        </h2>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-800 text-sm font-medium">업로드 오류</p>
              <p className="text-red-700 text-sm whitespace-pre-line">{error}</p>
            </div>
          </div>
        )}

        {/* 업로드 진행률 표시 */}
        {isLoading && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center gap-3 mb-3">
              {getStageIcon()}
              <div className="flex-1">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-blue-900">{getStageMessage()}</span>
                  <span className="text-sm text-blue-700">{Math.round(uploadProgress)}%</span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            </div>
            <div className="text-xs text-blue-700">
              {uploadStage === '업로드' && '📤 파일 전송 중...'}
              {uploadStage === '처리' && '🔄 텍스트 추출 및 벡터 변환 중...'}
              {uploadStage === '완료' && '✅ 모든 작업이 완료되었습니다!'}
            </div>
          </div>
        )}

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive 
              ? 'border-blue-500 bg-blue-50' 
              : 'border-gray-300 hover:border-gray-400'
          } ${isLoading ? 'opacity-50 pointer-events-none' : ''}`}
        >
          <input {...getInputProps()} />
          <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          {isDragActive ? (
            <p className="text-blue-600 font-medium">파일을 여기에 놓으세요...</p>
          ) : (
            <div>
              <p className="text-gray-600 mb-2 font-medium">
                파일을 드래그하여 놓거나 클릭하여 선택하세요
              </p>
              <p className="text-sm text-gray-500 mb-1">
                지원 형식: TXT, MD, PDF, CSV, DOC, DOCX
              </p>
              <p className="text-xs text-gray-400">
                최대 파일 크기: 10MB
              </p>
            </div>
          )}
        </div>

        {selectedFiles.length > 0 && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-900">
                선택된 파일 ({selectedFiles.length}개)
              </h3>
              <button
                onClick={() => setSelectedFiles([])}
                className="text-sm text-red-600 hover:text-red-800"
                disabled={isLoading}
              >
                모두 제거
              </button>
            </div>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {selectedFiles.map((file, index) => (
                <div 
                  key={`${file.name}-${index}`} 
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <FileText className="h-5 w-5 text-gray-500 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatFileSize(file.size)} • {file.type || '알 수 없는 형식'}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="text-red-500 hover:text-red-700 p-1 flex-shrink-0"
                    title="파일 제거"
                    disabled={isLoading}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
            
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                💡 <strong>팁:</strong> 파일들은 자동으로 청크 단위로 분할되어 벡터화됩니다. 
                더 정확한 검색을 위해 관련 문서들을 함께 업로드하세요.
              </p>
            </div>
          </div>
        )}

        <div className="flex gap-3 pt-6">
          <button
            onClick={handleClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            disabled={isLoading}
          >
            {isLoading ? '업로드 중...' : '취소'}
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || selectedFiles.length === 0}
            className="flex-1 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader className="h-4 w-4 animate-spin" />
                {uploadStage} 중...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                업로드 ({selectedFiles.length}개 파일)
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UploadDocumentsModal; 