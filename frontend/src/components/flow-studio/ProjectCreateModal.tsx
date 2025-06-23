import React, { useState } from 'react';
import { X, Folder, Users, User } from 'lucide-react';

interface ProjectCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (projectData: {
    name: string;
    description: string;
    owner_type: 'user' | 'group';
    is_default: boolean;
  }) => void;
  userInfo?: {
    group_id?: string;
    group_name?: string;
  };
}

const ProjectCreateModal: React.FC<ProjectCreateModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  userInfo
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    owner_type: 'user' as 'user' | 'group',
    is_default: false
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // 유효성 검사
    const newErrors: Record<string, string> = {};
    
    if (!formData.name.trim()) {
      newErrors.name = '프로젝트 이름을 입력해주세요.';
    }
    
    if (formData.owner_type === 'group' && !userInfo?.group_id) {
      newErrors.owner_type = '그룹 프로젝트를 생성하려면 그룹에 속해야 합니다.';
    }
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    
    onSubmit(formData);
    
    // 폼 초기화
    setFormData({
      name: '',
      description: '',
      owner_type: 'user',
      is_default: false
    });
    setErrors({});
  };

  const handleClose = () => {
    setFormData({
      name: '',
      description: '',
      owner_type: 'user',
      is_default: false
    });
    setErrors({});
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center">
            <Folder className="w-5 h-5 mr-2" />
            새 프로젝트 생성
          </h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* 프로젝트 이름 */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              프로젝트 이름 *
            </label>
            <input
              type="text"
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.name ? 'border-red-500' : 'border-gray-300'
              }`}
              placeholder="프로젝트 이름을 입력하세요"
            />
            {errors.name && (
              <p className="mt-1 text-sm text-red-600">{errors.name}</p>
            )}
          </div>

          {/* 프로젝트 설명 */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              프로젝트 설명
            </label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="프로젝트에 대한 설명을 입력하세요 (선택사항)"
            />
          </div>

          {/* 권한 설정 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              프로젝트 권한 *
            </label>
            <div className="space-y-2">
              {/* 개인 권한 */}
              <label className="flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50">
                <input
                  type="radio"
                  name="owner_type"
                  value="user"
                  checked={formData.owner_type === 'user'}
                  onChange={(e) => setFormData({ ...formData, owner_type: e.target.value as 'user' | 'group' })}
                  className="mr-3"
                />
                <User className="w-5 h-5 mr-2 text-blue-600" />
                <div>
                  <div className="font-medium text-gray-900">개인 프로젝트</div>
                  <div className="text-sm text-gray-500">나만 접근할 수 있는 프로젝트</div>
                </div>
              </label>

              {/* 그룹 권한 */}
              <label className={`flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50 ${
                !userInfo?.group_id ? 'opacity-50 cursor-not-allowed' : ''
              }`}>
                <input
                  type="radio"
                  name="owner_type"
                  value="group"
                  checked={formData.owner_type === 'group'}
                  onChange={(e) => setFormData({ ...formData, owner_type: e.target.value as 'user' | 'group' })}
                  disabled={!userInfo?.group_id}
                  className="mr-3"
                />
                <Users className="w-5 h-5 mr-2 text-green-600" />
                <div>
                  <div className="font-medium text-gray-900">
                    그룹 프로젝트
                    {userInfo?.group_name && (
                      <span className="text-sm text-gray-500 ml-1">({userInfo.group_name})</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500">
                    {userInfo?.group_id 
                      ? '그룹 멤버들이 함께 사용할 수 있는 프로젝트'
                      : '그룹에 속해야 생성할 수 있습니다'
                    }
                  </div>
                </div>
              </label>
            </div>
            {errors.owner_type && (
              <p className="mt-1 text-sm text-red-600">{errors.owner_type}</p>
            )}
          </div>

          {/* 기본 프로젝트 설정 */}
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.is_default}
                onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">기본 프로젝트로 설정</span>
            </label>
            <p className="text-xs text-gray-500 mt-1">
              기본 프로젝트는 새 플로우 생성 시 자동으로 선택됩니다.
            </p>
          </div>

          {/* 버튼 */}
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              프로젝트 생성
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProjectCreateModal; 