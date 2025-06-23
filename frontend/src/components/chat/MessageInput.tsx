import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, Paperclip, Image, FileText, Loader2 } from 'lucide-react';
import { RAGDataSource } from '../../types/llmChat';
import RAGDataSourceSelector from './RAGDataSourceSelector';

interface MessageInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop?: () => void;
  disabled?: boolean;
  isTyping?: boolean;
  ragSources: RAGDataSource[];
  selectedRAGSources: number[];
  onRAGSourcesChange: (sources: number[]) => void;
  placeholder?: string;
  maxLength?: number;
}

const MessageInput: React.FC<MessageInputProps> = ({
  value,
  onChange,
  onSend,
  onStop,
  disabled = false,
  isTyping = false,
  ragSources,
  selectedRAGSources,
  onRAGSourcesChange,
  placeholder = "메시지를 입력하세요... (@를 입력하여 RAG 데이터소스 선택)",
  maxLength = 4000
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  // 텍스트 영역 높이 자동 조절
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [value]);

  // 키보드 이벤트 처리
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim() && !isTyping) {
        onSend();
      }
    }
  };

  // 파일 드래그 앤 드롭 처리
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  // 파일 처리
  const handleFiles = (files: File[]) => {
    // TODO: 파일 업로드 로직 구현
    console.log('Files dropped:', files);
    // 여기서 파일 타입 검증, 업로드 등 처리
  };

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      handleFiles(files);
    }
  };

  const canSend = !disabled && value.trim() && !isTyping;

  return (
    <div className="border-t border-gray-200 bg-white">
      {/* RAG 데이터소스 선택기 */}
      <RAGDataSourceSelector
        ragSources={ragSources}
        selectedSources={selectedRAGSources}
        onSourcesChange={onRAGSourcesChange}
        inputValue={value}
        onInputChange={onChange}
        onKeyDown={handleKeyDown}
        inputRef={textareaRef}
      />

      {/* 메시지 입력 영역 */}
      <div 
        className={`relative p-4 ${isDragOver ? 'bg-gray-50 border-blue-500' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* 드래그 오버레이 */}
        {isDragOver && (
          <div className="absolute inset-0 bg-gray-50 bg-opacity-90 flex items-center justify-center z-10 rounded-lg border-2 border-dashed border-blue-400">
            <div className="text-center">
              <FileText className="w-12 h-12 text-blue-400 mx-auto mb-2" />
              <p className="text-blue-600 font-medium">파일을 여기에 드롭하세요</p>
              <p className="text-blue-500 text-sm">이미지, 문서 등을 업로드할 수 있습니다</p>
            </div>
          </div>
        )}

        <div className="flex items-end gap-3">
          {/* 파일 첨부 버튼 */}
          <button
            onClick={handleFileSelect}
            disabled={disabled}
            className="flex-shrink-0 p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="파일 첨부"
          >
            <Paperclip className="w-5 h-5" />
          </button>

          {/* 텍스트 입력 */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              maxLength={maxLength}
              className="w-full p-3 pr-12 bg-white border border-gray-300 text-gray-900 placeholder-gray-500 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              style={{ minHeight: '44px', maxHeight: '200px' }}
            />
            
            {/* 글자 수 표시 */}
            <div className="absolute bottom-1 right-1 text-xs text-gray-400">
              {value.length}/{maxLength}
            </div>
          </div>

          {/* 전송/중지 버튼 */}
          <div className="flex-shrink-0">
            {isTyping ? (
              <button
                onClick={onStop}
                className="p-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center gap-2"
                title="응답 중지"
              >
                <Square className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={onSend}
                disabled={!canSend}
                className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
                title="메시지 전송"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* 파일 입력 (숨김) */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,.pdf,.doc,.docx,.txt,.md"
          onChange={handleFileChange}
          className="hidden"
        />

        {/* 입력 도움말 */}
        <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
          <span>Enter로 전송, Shift+Enter로 줄바꿈</span>
          {selectedRAGSources.length > 0 && (
            <span className="text-blue-600">
              RAG 데이터소스 {selectedRAGSources.length}개 선택됨
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageInput; 