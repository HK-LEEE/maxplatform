import React, { useState } from 'react';
import { Smartphone, Monitor, Tablet, LogOut, Shield, X, AlertTriangle, Info } from 'lucide-react';
import toast from 'react-hot-toast';

interface SessionInfo {
  session_id: string;
  client_name: string;
  device_info?: {
    device_type: string;
    browser: string;
    os: string;
  };
  location?: {
    country: string;
    city: string;
  };
  created_at: string;
  last_used_at?: string;
  is_current_session: boolean;
  is_suspicious: boolean;
}

interface SessionLogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentSession?: SessionInfo;
  otherSessions?: SessionInfo[];
  totalSessions: number;
  suspiciousSessions: number;
  onLogout: (logoutType: 'current' | 'all', reason?: string) => Promise<void>;
}

const SessionLogoutModal: React.FC<SessionLogoutModalProps> = ({
  isOpen,
  onClose,
  currentSession,
  otherSessions = [],
  totalSessions,
  suspiciousSessions,
  onLogout
}) => {
  const [logoutType, setLogoutType] = useState<'current' | 'all'>('current');
  const [isLoading, setIsLoading] = useState(false);

  const handleLogout = async () => {
    setIsLoading(true);
    try {
      await onLogout(logoutType);
      // 성공 메시지와 리다이렉트는 MainLayout에서 처리
      onClose();
    } catch (error) {
      // 에러 처리도 MainLayout에서 처리하므로 여기서는 조용히 넘어감
      console.error('Modal logout error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getDeviceIcon = (deviceType?: string) => {
    switch (deviceType?.toLowerCase()) {
      case 'mobile':
        return Smartphone;
      case 'tablet':
        return Tablet;
      case 'desktop':
      default:
        return Monitor;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const SessionItem: React.FC<{ session: SessionInfo; isCurrent?: boolean }> = ({ 
    session, 
    isCurrent = false 
  }) => {
    const DeviceIcon = getDeviceIcon(session.device_info?.device_type);
    
    return (
      <div className={`p-3 border rounded-md ${isCurrent ? 'border-blue-200 bg-blue-50' : 'border-gray-200 bg-white'}`}>
        <div className="flex items-start space-x-3">
          <DeviceIcon className="w-5 h-5 text-gray-600 mt-0.5" />
          <div className="flex-1 space-y-1">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-semibold text-gray-900">
                {session.client_name}
              </span>
              {isCurrent && (
                <span className="text-xs text-blue-600 font-medium">
                  (현재 세션)
                </span>
              )}
              {session.is_suspicious && (
                <div className="flex items-center space-x-1">
                  <Shield className="w-3 h-3 text-red-500" />
                  <span className="text-xs text-red-600">
                    의심스러운 활동
                  </span>
                </div>
              )}
            </div>
            <p className="text-xs text-gray-600">
              {session.device_info ? 
                `${session.device_info.browser} • ${session.device_info.os}` : 
                '알 수 없는 디바이스'
              }
            </p>
            <p className="text-xs text-gray-500">
              {session.location ? 
                `${session.location.city}, ${session.location.country}` : 
                '위치 정보 없음'
              }
            </p>
            <p className="text-xs text-gray-500">
              마지막 사용: {session.last_used_at ? 
                formatDate(session.last_used_at) : 
                formatDate(session.created_at)
              }
            </p>
          </div>
        </div>
      </div>
    );
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
          className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* 모달 헤더 */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <LogOut className="w-5 h-5 text-gray-700" />
              <h2 className="text-lg font-semibold text-gray-900">로그아웃 옵션 선택</h2>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 모달 바디 */}
          <div className="p-6 max-h-[60vh] overflow-y-auto">
            <div className="space-y-6">
              {/* 세션 요약 정보 */}
              <div>
                <p className="text-sm text-gray-600 mb-2">
                  {totalSessions > 0 ? (
                    <>
                      총 {totalSessions}개의 활성 세션이 있습니다.
                      {suspiciousSessions > 0 && (
                        <span className="text-red-600 font-medium">
                          {' '}({suspiciousSessions}개의 의심스러운 세션 포함)
                        </span>
                      )}
                    </>
                  ) : (
                    '로그아웃 옵션을 선택하세요.'
                  )}
                </p>
                
                {suspiciousSessions > 0 && (
                  <div className="flex items-start space-x-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                    <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5" />
                    <p className="text-sm text-yellow-800">
                      의심스러운 세션이 감지되었습니다. 보안을 위해 모든 세션에서 로그아웃하는 것을 권장합니다.
                    </p>
                  </div>
                )}
              </div>

              {/* 로그아웃 옵션 선택 */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">로그아웃 옵션:</h3>
                <div className="space-y-3">
                  <label className="flex items-start space-x-3 cursor-pointer">
                    <input
                      type="radio"
                      name="logoutType"
                      value="current"
                      checked={logoutType === 'current'}
                      onChange={(e) => setLogoutType(e.target.value as 'current' | 'all')}
                      className="mt-1 w-4 h-4 text-blue-600"
                    />
                    <div>
                      <div className="font-medium text-gray-900">현재 세션만 로그아웃</div>
                      <p className="text-sm text-gray-600 mt-1">
                        이 디바이스/브라우저에서만 로그아웃됩니다. 다른 디바이스의 세션은 유지됩니다.
                      </p>
                    </div>
                  </label>
                  
                  <label className="flex items-start space-x-3 cursor-pointer">
                    <input
                      type="radio"
                      name="logoutType"
                      value="all"
                      checked={logoutType === 'all'}
                      onChange={(e) => setLogoutType(e.target.value as 'current' | 'all')}
                      className="mt-1 w-4 h-4 text-blue-600"
                    />
                    <div>
                      <div className="font-medium text-gray-900">모든 세션에서 로그아웃</div>
                      <p className="text-sm text-gray-600 mt-1">
                        모든 디바이스와 브라우저에서 로그아웃됩니다. 다시 로그인해야 합니다.
                      </p>
                    </div>
                  </label>
                </div>
              </div>

              <div className="border-t border-gray-200 pt-6">
                {/* 현재 세션 정보 */}
                {currentSession && (
                  <div className="mb-6">
                    <h4 className="font-semibold text-gray-900 mb-2">현재 세션:</h4>
                    <SessionItem session={currentSession} isCurrent={true} />
                  </div>
                )}

                {/* 다른 세션 목록 */}
                {otherSessions.length > 0 && (
                  <div className="mb-6">
                    <h4 className="font-semibold text-gray-900 mb-2">
                      다른 활성 세션 ({otherSessions.length}개):
                    </h4>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {otherSessions.map((session) => (
                        <SessionItem key={session.session_id} session={session} />
                      ))}
                    </div>
                  </div>
                )}

                {/* 보안 권고사항 */}
                <div className="flex items-start space-x-3 p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <Info className="w-4 h-4 text-blue-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-blue-900 mb-1">보안 권고사항:</p>
                    <ul className="text-sm text-blue-800 space-y-1">
                      <li>• 공용 컴퓨터나 의심스러운 디바이스에서 로그인한 경우 모든 세션에서 로그아웃하세요.</li>
                      <li>• 정기적으로 활성 세션을 확인하고 인식하지 못하는 세션을 제거하세요.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 모달 푸터 */}
          <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 bg-gray-50">
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
              className={`px-4 py-2 text-sm font-medium text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 ${
                logoutType === 'all' 
                  ? 'bg-red-600 hover:bg-red-700' 
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>로그아웃 중...</span>
                </>
              ) : (
                <>
                  <LogOut className="w-4 h-4" />
                  <span>{logoutType === 'current' ? '현재 세션 로그아웃' : '모든 세션 로그아웃'}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SessionLogoutModal;