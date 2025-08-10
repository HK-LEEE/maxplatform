import React, { useState } from 'react';
import { LogOut, Shield, X } from 'lucide-react';

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
          className="relative bg-white rounded-lg shadow-xl max-w-md w-full"
          onClick={(e) => e.stopPropagation()}
        >
          {/* 모달 헤더 */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <LogOut className="w-5 h-5 text-gray-700" />
              <h2 className="text-lg font-semibold text-gray-900">로그아웃</h2>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 모달 바디 */}
          <div className="p-6">
            <div className="space-y-4">
              <div className="text-center">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Shield className="w-8 h-8 text-blue-600" />
                </div>
                {userName && (
                  <p className="text-lg font-medium text-gray-900 mb-2">
                    안녕히가세요, {userName}님
                  </p>
                )}
                <p className="text-gray-600 leading-relaxed">
                  모든 디바이스에서 안전하게 로그아웃하고<br/>
                  MAX Lab과 연동된 서비스에서도 함께<br/>
                  로그아웃됩니다.
                </p>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                <div className="flex items-center space-x-2">
                  <Shield className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-900">보안 권장</span>
                </div>
                <p className="text-sm text-blue-800 mt-1">
                  공용 컴퓨터나 다른 사람과 공유하는 디바이스에서는 항상 모든 세션에서 로그아웃하는 것이 안전합니다.
                </p>
              </div>
            </div>
          </div>

          {/* 모달 푸터 */}
          <div className="flex items-center justify-end p-6 border-t border-gray-200 bg-gray-50">
            {/* Advanced options disabled - always use smart logout */}

            <div className="flex items-center space-x-3">
              <button
                onClick={onClose}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleLogout}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>로그아웃 중...</span>
                  </>
                ) : (
                  <>
                    <LogOut className="w-4 h-4" />
                    <span>로그아웃하기</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleLogoutModal;