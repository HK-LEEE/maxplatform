import React, { useState } from 'react';
import { LogOut, X } from 'lucide-react';

interface SimpleLogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLogout: (logoutType: 'smart' | 'current' | 'all') => Promise<void>;
  userName?: string;
}

const SimpleLogoutModal: React.FC<SimpleLogoutModalProps> = ({
  isOpen,
  onClose,
  onLogout,
  userName
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleLogout = async () => {
    setIsLoading(true);
    try {
      // Always use 'smart' logout (same as 'all' but with better UX naming)
      await onLogout('smart');
      onClose();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* 모달 오버레이 */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />
      
      {/* 모달 컨텐츠 */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div 
          className="relative bg-white rounded-lg shadow-xl max-w-sm w-full"
          onClick={(e) => e.stopPropagation()}
        >
          {/* 모달 헤더 */}
          <div className="flex items-center justify-between p-4">
            <h2 className="text-lg font-semibold text-gray-900">로그아웃</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 모달 바디 */}
          <div className="p-6">
            <div className="text-center">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <LogOut className="w-6 h-6 text-red-600" />
              </div>
              <p className="text-base font-medium text-gray-900">
                {userName ? `${userName}님, 로그아웃하시겠습니까?` : '로그아웃하시겠습니까?'}
              </p>
              <p className="text-sm text-gray-500 mt-2">
                모든 연결된 서비스에서 로그아웃됩니다
              </p>
            </div>
          </div>

          {/* 모달 푸터 */}
          <div className="flex items-center justify-end p-4 space-x-3">
            <button
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              취소
            </button>
            <button
              onClick={handleLogout}
              disabled={isLoading}
              className="px-5 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '로그아웃 중...' : '로그아웃'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleLogoutModal;