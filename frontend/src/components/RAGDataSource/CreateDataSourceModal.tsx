/**
 * RAG 데이터소스 생성 모달 컴포넌트
 */

import React, { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import { X, User, Users, AlertCircle } from 'lucide-react';
import axios from 'axios';
import { CreateDataSourceData } from '../../types/ragDataSource';

// 그룹 타입 정의
interface Group {
  id: number;
  name: string;
  description?: string;
}

interface CreateDataSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateDataSourceData) => void;
  isLoading: boolean;
}

const CreateDataSourceModal: React.FC<CreateDataSourceModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [ownerType, setOwnerType] = useState<'USER' | 'GROUP'>('USER');
  const [selectedGroupId, setSelectedGroupId] = useState<number | undefined>();
  const [nameError, setNameError] = useState<string>('');

  // 영어 이름 검증 함수
  const validateEnglishName = (value: string): string => {
    if (!value.trim()) {
      return '';
    }
    
    // 영어, 숫자, 공백, 하이픈, 밑줄만 허용
    const englishPattern = /^[a-zA-Z0-9\s\-_]+$/;
    
    if (!englishPattern.test(value)) {
      return '데이터소스 이름은 영어, 숫자, 공백, 하이픈(-), 밑줄(_)만 사용할 수 있습니다.';
    }
    
    if (value.length < 2) {
      return '데이터소스 이름은 최소 2자 이상이어야 합니다.';
    }
    
    if (value.length > 50) {
      return '데이터소스 이름은 최대 50자까지 입력할 수 있습니다.';
    }
    
    return '';
  };

  // 이름 변경 핸들러
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setName(value);
    setNameError(validateEnglishName(value));
  };

  // 그룹 목록 조회
  const { data: groups } = useQuery<Group[]>(
    'groups',
    async () => {
      try {
        const response = await axios.get('/admin/groups');
        return response.data;
      } catch (error) {
        console.error('Failed to fetch groups:', error);
        return [];
      }
    },
    {
      enabled: isOpen && ownerType === 'GROUP'
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // 최종 검증
    const error = validateEnglishName(name);
    if (error) {
      setNameError(error);
      return;
    }
    
    onSubmit({
      name,
      description: description || undefined,
      owner_type: ownerType,
      group_id: ownerType === 'GROUP' ? selectedGroupId : undefined
    });
  };

  const handleClose = () => {
    setName('');
    setDescription('');
    setOwnerType('USER');
    setSelectedGroupId(undefined);
    setNameError('');
    onClose();
  };

  useEffect(() => {
    if (groups && groups.length > 0 && !selectedGroupId) {
      setSelectedGroupId(groups[0].id);
    }
  }, [groups, selectedGroupId]);

  if (!isOpen) return null;

  const isFormValid = name.trim() && !nameError && (ownerType === 'USER' || selectedGroupId);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">새 RAG 데이터소스 생성</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={isLoading}
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              데이터소스 이름 *
            </label>
            <input
              type="text"
              value={name}
              onChange={handleNameChange}
              required
              className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                nameError 
                  ? 'border-red-300 focus:ring-red-500' 
                  : 'border-gray-300 focus:ring-blue-500'
              }`}
              placeholder="예: Customer Support Documents"
              disabled={isLoading}
            />
            
            {/* 힌트 메시지 */}
            <div className="mt-1 text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                <span>영어, 숫자, 공백, 하이픈(-), 밑줄(_)만 사용 가능</span>
              </div>
              <div className="ml-4 mt-0.5">
                예시: "Product Manual", "FAQ_Database", "Support-Docs"
              </div>
            </div>
            
            {/* 오류 메시지 */}
            {nameError && (
              <div className="mt-1 text-sm text-red-600 flex items-center gap-1">
                <AlertCircle className="h-4 w-4" />
                <span>{nameError}</span>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              설명 (선택사항)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="데이터소스에 대한 간단한 설명을 입력하세요 (한글 가능)"
              disabled={isLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              소유자 타입 *
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  value="USER"
                  checked={ownerType === 'USER'}
                  onChange={(e) => setOwnerType(e.target.value as 'USER')}
                  className="mr-2"
                  disabled={isLoading}
                />
                <User className="h-4 w-4 mr-1" />
                개인 전용 (나만 사용)
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="GROUP"
                  checked={ownerType === 'GROUP'}
                  onChange={(e) => setOwnerType(e.target.value as 'GROUP')}
                  className="mr-2"
                  disabled={isLoading}
                />
                <Users className="h-4 w-4 mr-1" />
                그룹 공유 (팀원과 공유)
              </label>
            </div>
          </div>

          {ownerType === 'GROUP' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                그룹 선택 *
              </label>
              <select
                value={selectedGroupId || ''}
                onChange={(e) => setSelectedGroupId(Number(e.target.value))}
                required
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isLoading}
              >
                <option value="">그룹을 선택하세요</option>
                {groups?.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                    {group.description && ` - ${group.description}`}
                  </option>
                ))}
              </select>
              {groups && groups.length === 0 && (
                <p className="text-sm text-gray-500 mt-1">
                  사용 가능한 그룹이 없습니다. 관리자에게 문의하세요.
                </p>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              disabled={isLoading}
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isLoading || !isFormValid}
              className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isLoading ? '생성 중...' : '생성'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateDataSourceModal; 