import React, { useState } from 'react';
import { X, Save, Users, User } from 'lucide-react';
import { showToast } from '../../utils/toast';

interface FlowSaveModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (flowData: {
    name: string;
    description: string;
    owner_type: 'user' | 'group';
    project_id: string;
    flow_data: any;
    flow_id?: string; // 기존 플로우 업데이트용
  }) => void;
  userInfo: {
    user_id: string;
    group_id?: string;
    group_name?: string;
    username: string;
  };
  currentFlowData: any;
  defaultProject?: {
    id: string;
    name: string;
    owner_type: 'user' | 'group';
  };
  currentFlow?: {
    id: string;
    name: string;
    description: string;
    owner_type: 'user' | 'group';
  };
}

const FlowSaveModal: React.FC<FlowSaveModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  userInfo,
  currentFlowData,
  defaultProject,
  currentFlow
}) => {
  const [flowName, setFlowName] = useState('');
  const [flowDescription, setFlowDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saveAsNew, setSaveAsNew] = useState(false);

  // 기존 플로우 정보 로드
  React.useEffect(() => {
    if (isOpen && currentFlow) {
      setFlowName(currentFlow.name);
      setFlowDescription(currentFlow.description);
      setSaveAsNew(false);
    } else if (isOpen && !currentFlow) {
      setFlowName('');
      setFlowDescription('');
      setSaveAsNew(false);
    }
  }, [isOpen, currentFlow]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!flowName.trim()) {
      showToast.error('플로우 이름을 입력해주세요.');
      return;
    }

    // 프로젝트가 없으면 기본 프로젝트 정보 생성
    const projectInfo = defaultProject || {
      id: '', // 빈 ID는 백엔드에서 새 프로젝트 생성을 의미
      name: 'Default Project',
      owner_type: 'user' as const
    };

    setIsSubmitting(true);
    try {
      const flowData = {
        name: flowName.trim(),
        description: flowDescription.trim(),
        owner_type: projectInfo.owner_type,
        project_id: projectInfo.id,
        flow_data: currentFlowData,
        flow_id: (currentFlow && !saveAsNew) ? currentFlow.id : undefined
      };

      await onSubmit(flowData);
      
      // 성공 시 모달 초기화 및 닫기
      setFlowName('');
      setFlowDescription('');
      setSaveAsNew(false);
      onClose();
    } catch (error) {
      console.error('Flow save error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setFlowName('');
      setFlowDescription('');
      setSaveAsNew(false);
      onClose();
    }
  };

  const getOwnerTypeText = (ownerType: 'user' | 'group') => {
    return ownerType === 'group' ? '그룹' : '개인';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center">
            <Save className="w-5 h-5 mr-2" />
            {currentFlow ? (saveAsNew ? '다른 이름으로 저장' : '플로우 업데이트') : '플로우 저장'}
          </h2>
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* 플로우 이름 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              플로우 이름 *
            </label>
            <input
              type="text"
              value={flowName}
              onChange={(e) => setFlowName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="플로우 이름을 입력하세요"
              required
              disabled={isSubmitting}
            />
          </div>

          {/* 플로우 설명 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              플로우 설명
            </label>
            <textarea
              value={flowDescription}
              onChange={(e) => setFlowDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="플로우에 대한 설명을 입력하세요 (선택사항)"
              disabled={isSubmitting}
            />
          </div>

          {/* 다른 이름으로 저장 옵션 (기존 플로우인 경우만) */}
          {currentFlow && (
            <div>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={saveAsNew}
                  onChange={(e) => setSaveAsNew(e.target.checked)}
                  disabled={isSubmitting}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">다른 이름으로 저장 (새 플로우 생성)</span>
              </label>
              <p className="text-xs text-gray-500 mt-1">
                체크하면 기존 플로우를 수정하지 않고 새로운 플로우를 생성합니다.
              </p>
            </div>
          )}

          {/* 권한 정보 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              플로우 권한
            </label>
            
            <div className="w-full px-3 py-2 border border-gray-200 rounded-md bg-gray-50">
              <div className="flex items-center">
                {(defaultProject?.owner_type || 'user') === 'user' ? (
                  <User className="w-5 h-5 mr-2 text-blue-600" />
                ) : (
                  <Users className="w-5 h-5 mr-2 text-green-600" />
                )}
                <div className="flex-1">
                  <div className="font-medium text-gray-900">
                    {(defaultProject?.owner_type || 'user') === 'user' ? '개인 플로우' : '그룹 플로우'}
                    {(defaultProject?.owner_type || 'user') === 'group' && userInfo.group_name && (
                      <span className="text-sm text-gray-500 ml-1">({userInfo.group_name})</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500">
                    {(defaultProject?.owner_type || 'user') === 'user' 
                      ? '나만 접근할 수 있는 플로우' 
                      : '그룹 멤버들이 함께 사용할 수 있는 플로우'
                    }
                  </div>
                </div>
              </div>
            </div>
            
            <p className="text-sm text-gray-500 mt-1">
              플로우 권한은 프로젝트 권한과 동일하게 설정됩니다.
            </p>
          </div>

          {/* 현재 프로젝트 정보 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              저장될 프로젝트
            </label>
            
            <div className="w-full px-3 py-2 border border-gray-200 rounded-md bg-gray-50">
              <div className="flex items-center">
                <div className="flex-1">
                  <div className="font-medium text-gray-900">
                    {defaultProject?.name || 'Default Project'}
                  </div>
                  <div className="text-sm text-gray-500">
                    {getOwnerTypeText(defaultProject?.owner_type || 'user')} 프로젝트
                    {!defaultProject && ' (자동 생성)'}
                  </div>
                </div>
                <div className="text-sm text-blue-600">
                  {defaultProject ? '현재 프로젝트' : '새 프로젝트'}
                </div>
              </div>
            </div>
            
            <p className="text-sm text-gray-500 mt-1">
              플로우는 현재 작업 중인 프로젝트에 저장됩니다.
            </p>
          </div>

          {/* 버튼 */}
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !defaultProject}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
            >
              {isSubmitting && (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              )}
              <span>
                {isSubmitting 
                  ? '저장 중...' 
                  : currentFlow 
                    ? (saveAsNew ? '새 플로우로 저장' : '플로우 업데이트')
                    : '플로우 저장'
                }
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FlowSaveModal; 