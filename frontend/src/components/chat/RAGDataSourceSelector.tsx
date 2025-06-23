import React, { useState, useEffect, useRef } from 'react';
import { Database, X } from 'lucide-react';
import { RAGDataSource } from '../../types/llmChat';

interface RAGDataSourceSelectorProps {
  ragSources: RAGDataSource[];
  selectedSources: number[];
  onSourcesChange: (sources: number[]) => void;
  inputValue: string;
  onInputChange: (value: string) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  inputRef: React.RefObject<HTMLTextAreaElement>;
}

interface SelectedSourceTagProps {
  source: RAGDataSource;
  onRemove: () => void;
}

const SelectedSourceTag: React.FC<SelectedSourceTagProps> = ({ source, onRemove }) => (
  <div className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 px-2 py-1 rounded-full text-sm border border-blue-200">
    <Database className="w-3 h-3" />
    <span>{source.name}</span>
    <button
      onClick={onRemove}
      className="hover:bg-blue-100 rounded-full p-0.5 transition-colors"
    >
      <X className="w-3 h-3" />
    </button>
  </div>
);

const RAGDataSourceSelector: React.FC<RAGDataSourceSelectorProps> = ({
  ragSources,
  selectedSources,
  onSourcesChange,
  inputValue,
  onInputChange,
  onKeyDown,
  inputRef
}) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [atPosition, setAtPosition] = useState(-1);
  const [searchQuery, setSearchQuery] = useState('');
  
  const dropdownRef = useRef<HTMLDivElement>(null);

  // @ 키워드 감지
  useEffect(() => {
    const lastAtIndex = inputValue.lastIndexOf('@');
    const cursorPosition = inputRef.current?.selectionStart || 0;
    
    if (lastAtIndex !== -1 && cursorPosition > lastAtIndex) {
      const textAfterAt = inputValue.slice(lastAtIndex + 1, cursorPosition);
      
      // @ 뒤에 공백이 없고 현재 커서가 @ 뒤에 있으면 드롭다운 표시
      if (!textAfterAt.includes(' ') && textAfterAt.length >= 0) {
        setAtPosition(lastAtIndex);
        setSearchQuery(textAfterAt);
        setShowDropdown(true);
        setHighlightedIndex(0);
      } else {
        setShowDropdown(false);
      }
    } else {
      setShowDropdown(false);
    }
  }, [inputValue, inputRef]);

  // 필터링된 데이터소스 목록
  const filteredSources = ragSources.filter(source => 
    !selectedSources.includes(source.id) &&
    source.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 키보드 이벤트 처리
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showDropdown && filteredSources.length > 0) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          if (highlightedIndex < filteredSources.length - 1) {
            setHighlightedIndex(prev => prev + 1);
          } else {
            // 맨 아래에서 아래로 가면 드롭다운을 닫고 입력창으로 포커스 이동
            setShowDropdown(false);
            setHighlightedIndex(-1);
            setTimeout(() => {
              if (inputRef.current) {
                inputRef.current.focus();
                // 커서를 맨 끝으로 이동
                const length = inputRef.current.value.length;
                inputRef.current.setSelectionRange(length, length);
              }
            }, 0);
          }
          break;
        case 'ArrowUp':
          e.preventDefault();
          setHighlightedIndex(prev => 
            prev > 0 ? prev - 1 : filteredSources.length - 1
          );
          break;
        case 'Enter':
          if (highlightedIndex >= 0 && highlightedIndex < filteredSources.length) {
            e.preventDefault();
            selectSource(filteredSources[highlightedIndex]);
            return;
          }
          break;
        case 'Escape':
          e.preventDefault();
          setShowDropdown(false);
          break;
      }
    }
    
    onKeyDown(e);
  };

  // 데이터소스 선택
  const selectSource = (source: RAGDataSource) => {
    // @ 부분을 제거하고 선택된 소스 추가
    const beforeAt = inputValue.slice(0, atPosition);
    const afterQuery = inputValue.slice(atPosition + 1 + searchQuery.length);
    
    onInputChange(beforeAt + afterQuery);
    onSourcesChange([...selectedSources, source.id]);
    setShowDropdown(false);
    setHighlightedIndex(-1);
    
    // 입력창에 포커스 유지
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  // 선택된 소스 제거
  const removeSource = (sourceId: number) => {
    onSourcesChange(selectedSources.filter(id => id !== sourceId));
  };

  // 선택된 소스들 가져오기
  const getSelectedSourcesData = () => {
    return ragSources.filter(source => selectedSources.includes(source.id));
  };

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative">
      {/* 선택된 데이터소스 태그들 */}
      {selectedSources.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2 p-2 bg-gray-50 rounded-lg border">
          {getSelectedSourcesData().map(source => (
            <SelectedSourceTag
              key={source.id}
              source={source}
              onRemove={() => removeSource(source.id)}
            />
          ))}
        </div>
      )}

      {/* 드롭다운 */}
      {showDropdown && (
        <div
          ref={dropdownRef}
          className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto"
        >
          <div className="p-2 border-b border-gray-100 bg-gray-50">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Database className="w-4 h-4" />
              <span>RAG 데이터소스 선택</span>
            </div>
          </div>
          
          {filteredSources.length > 0 ? (
            <div className="py-1">
              {filteredSources.map((source, index) => (
                <button
                  key={source.id}
                  onClick={() => selectSource(source)}
                  className={`w-full px-3 py-2 text-left hover:bg-blue-50 transition-colors ${
                    index === highlightedIndex ? 'bg-blue-50 border-l-2 border-blue-500' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-blue-600" />
                    <div>
                      <div className="font-medium text-gray-900">{source.name}</div>
                      {source.description && (
                        <div className="text-sm text-gray-500 truncate">
                          {source.description}
                        </div>
                      )}
                      <div className="text-xs text-gray-400">
                        문서 {source.document_count}개
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="p-4 text-center text-gray-500">
              <Database className="w-8 h-8 mx-auto mb-2 text-gray-300" />
              <p>검색 결과가 없습니다</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RAGDataSourceSelector; 