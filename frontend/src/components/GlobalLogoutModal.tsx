import React, { useEffect, useState } from 'react';
import { AlertCircle, LogOut, RefreshCw, X } from 'lucide-react';

export interface GlobalLogoutState {
  isVisible: boolean;
  type: 'loading' | 'error' | 'success';
  message: string;
  progress?: number;
  details?: string;
}

interface GlobalLogoutModalProps {
  state: GlobalLogoutState;
  onClose?: () => void;
}

export const GlobalLogoutModal: React.FC<GlobalLogoutModalProps> = ({ 
  state, 
  onClose 
}) => {
  const [dots, setDots] = useState('');

  // 로딩 애니메이션 (점 3개)
  useEffect(() => {
    if (state.type === 'loading') {
      const interval = setInterval(() => {
        setDots(prev => prev.length >= 3 ? '' : prev + '.');
      }, 500);
      return () => clearInterval(interval);
    }
  }, [state.type]);

  if (!state.isVisible) return null;

  const getIcon = () => {
    switch (state.type) {
      case 'loading':
        return <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-8 h-8 text-red-600" />;
      case 'success':
        return <LogOut className="w-8 h-8 text-green-600" />;
      default:
        return null;
    }
  };

  const getProgressColor = () => {
    switch (state.type) {
      case 'loading':
        return 'bg-blue-600';
      case 'error':
        return 'bg-red-600';
      case 'success':
        return 'bg-green-600';
      default:
        return 'bg-gray-400';
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    // 로딩 중일 때는 클릭으로 닫기 불가
    if (state.type === 'loading') {
      e.preventDefault();
      return;
    }
    if (e.target === e.currentTarget && onClose) {
      onClose();
    }
  };

  const handleEscapeKey = (e: React.KeyboardEvent) => {
    // 로딩 중일 때는 ESC로 닫기 불가
    if (state.type === 'loading') {
      e.preventDefault();
      return;
    }
    if (e.key === 'Escape' && onClose) {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black bg-opacity-75"
      onClick={handleBackdropClick}
      onKeyDown={handleEscapeKey}
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-labelledby="logout-modal-title"
      aria-describedby="logout-modal-description"
    >
      <div className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 transform transition-all duration-300 scale-100">
        {/* 닫기 버튼 (로딩 중이 아닐 때만) */}
        {state.type !== 'loading' && onClose && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="닫기"
          >
            <X className="w-5 h-5" />
          </button>
        )}

        {/* 콘텐츠 */}
        <div className="flex flex-col items-center text-center">
          {/* 아이콘 */}
          <div className="mb-6">
            {getIcon()}
          </div>

          {/* 제목 */}
          <h2 
            id="logout-modal-title"
            className="text-xl font-semibold text-gray-900 mb-3"
          >
            {state.type === 'loading' && '관련 시스템 로그아웃 처리 중'}
            {state.type === 'error' && '로그아웃 처리 중 오류 발생'}
            {state.type === 'success' && '로그아웃 완료'}
          </h2>

          {/* 메시지 */}
          <p 
            id="logout-modal-description"
            className="text-gray-600 mb-4"
          >
            {state.type === 'loading' && `${state.message}${dots}`}
            {state.type !== 'loading' && state.message}
          </p>

          {/* 세부사항 (있는 경우) */}
          {state.details && (
            <p className="text-sm text-gray-500 mb-4">
              {state.details}
            </p>
          )}

          {/* 진행률 표시 (있는 경우) */}
          {state.progress !== undefined && (
            <div className="w-full mb-4">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>진행률</span>
                <span>{state.progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full transition-all duration-300 ${getProgressColor()}`}
                  style={{ width: `${state.progress}%` }}
                />
              </div>
            </div>
          )}

          {/* 상태별 추가 정보 */}
          {state.type === 'loading' && (
            <div className="text-sm text-gray-500 space-y-1">
              <p>• MAX Platform 세션 종료</p>
              <p>• MAX Lab 동기화</p>
              <p>• 관련 서비스 정리</p>
            </div>
          )}

          {state.type === 'error' && onClose && (
            <button
              onClick={onClose}
              className="mt-4 px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              확인
            </button>
          )}

          {state.type === 'success' && onClose && (
            <button
              onClick={onClose}
              className="mt-4 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              확인
            </button>
          )}
        </div>
      </div>

      {/* 로딩 중일 때 전체 UI 차단을 명시하는 스타일 */}
      {state.type === 'loading' && (
        <style jsx>{`
          .fixed.inset-0 {
            pointer-events: all !important;
            user-select: none !important;
          }
          
          /* 전체 페이지 스크롤 방지 */
          body {
            overflow: hidden !important;
          }
          
          /* 모든 하위 요소 비활성화 (모달 제외) */
          body > *:not([role="dialog"]) {
            pointer-events: none !important;
            user-select: none !important;
          }
        `}</style>
      )}
    </div>
  );
};

// 전역 상태 관리를 위한 Context (선택사항)
export const GlobalLogoutContext = React.createContext<{
  state: GlobalLogoutState;
  showLogout: (message: string, details?: string) => void;
  showError: (message: string, details?: string) => void;
  showSuccess: (message: string, details?: string) => void;
  hideModal: () => void;
  updateProgress: (progress: number) => void;
} | null>(null);

export const GlobalLogoutProvider: React.FC<{ children: React.ReactNode }> = ({ 
  children 
}) => {
  const [state, setState] = useState<GlobalLogoutState>({
    isVisible: false,
    type: 'loading',
    message: '',
  });

  const showLogout = (message: string, details?: string) => {
    setState({
      isVisible: true,
      type: 'loading',
      message,
      details,
      progress: 0,
    });
  };

  const showError = (message: string, details?: string) => {
    setState({
      isVisible: true,
      type: 'error',
      message,
      details,
    });
  };

  const showSuccess = (message: string, details?: string) => {
    setState({
      isVisible: true,
      type: 'success',
      message,
      details,
    });
  };

  const hideModal = () => {
    setState(prev => ({ ...prev, isVisible: false }));
  };

  const updateProgress = (progress: number) => {
    setState(prev => ({ ...prev, progress }));
  };

  return (
    <GlobalLogoutContext.Provider value={{
      state,
      showLogout,
      showError,
      showSuccess,
      hideModal,
      updateProgress,
    }}>
      {children}
      <GlobalLogoutModal 
        state={state} 
        onClose={state.type !== 'loading' ? hideModal : undefined}
      />
    </GlobalLogoutContext.Provider>
  );
};

// Hook for using the context
export const useGlobalLogout = () => {
  const context = React.useContext(GlobalLogoutContext);
  if (!context) {
    throw new Error('useGlobalLogout must be used within GlobalLogoutProvider');
  }
  return context;
};