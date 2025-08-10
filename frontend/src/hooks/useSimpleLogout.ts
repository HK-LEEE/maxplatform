import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';

interface SimpleLogoutResponse {
  message: string;
  logout_type: string;
  sessions_terminated: number;
  tokens_revoked: number;
}

export const useSimpleLogout = () => {
  const [isLoading, setIsLoading] = useState(false);

  // 통합 로그아웃 함수
  const executeLogout = useCallback(async (
    logoutType: 'smart' | 'current' | 'all'
  ): Promise<SimpleLogoutResponse> => {
    setIsLoading(true);
    try {
      // 'smart' 로그아웃은 기본적으로 'all'과 동일하게 처리 (가장 안전한 옵션)
      const actualLogoutType = logoutType === 'smart' ? 'all' : logoutType;
      
      // 백엔드 세션 로그아웃 API 호출
      const response = await fetch('/api/user/sessions/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logout_type: actualLogoutType,
          reason: `User requested ${actualLogoutType} logout via simplified UI`
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Logout failed: ${response.status}`);
      }

      const data: SimpleLogoutResponse = await response.json();

      // 성공 메시지 (토스트는 여기서 표시하지 않고 호출한 곳에서 처리)
      return data;
    } catch (error) {
      console.error('Error during logout:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    isLoading,
    executeLogout,
  };
};