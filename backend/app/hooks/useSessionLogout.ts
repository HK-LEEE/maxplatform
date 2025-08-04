import { useState, useCallback } from 'react';
import { useToast } from '@chakra-ui/react';

interface SessionInfo {
  session_id: string;
  client_id: string;
  client_name: string;
  created_at: string;
  last_used_at?: string;
  ip_address?: string;
  user_agent?: string;
  device_info?: {
    device_type: string;
    browser: string;
    os: string;
  };
  location?: {
    country: string;
    city: string;
  };
  is_current_session: boolean;
  is_suspicious: boolean;
}

interface SessionsData {
  current_session: SessionInfo;
  other_sessions: SessionInfo[];
  total_sessions: number;
  suspicious_sessions: number;
}

interface LogoutResponse {
  message: string;
  logout_type: string;
  sessions_terminated: number;
  tokens_revoked: number;
}

export const useSessionLogout = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [sessionsData, setSessionsData] = useState<SessionsData | null>(null);
  const toast = useToast();

  // 활성 세션 목록 조회
  const fetchActiveSessions = useCallback(async (): Promise<SessionsData> => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/user/sessions/active', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.status}`);
      }

      const data: SessionsData = await response.json();
      setSessionsData(data);
      return data;
    } catch (error) {
      console.error('Error fetching active sessions:', error);
      toast({
        title: '세션 조회 실패',
        description: '활성 세션 정보를 가져오는 중 오류가 발생했습니다.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  // 로그아웃 실행
  const executeLogout = useCallback(async (
    logoutType: 'current' | 'all',
    reason?: string
  ): Promise<LogoutResponse> => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/user/sessions/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logout_type: logoutType,
          reason: reason || `User requested ${logoutType} logout`
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Logout failed: ${response.status}`);
      }

      const data: LogoutResponse = await response.json();

      // 성공 토스트
      toast({
        title: '로그아웃 성공',
        description: data.message,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      // 모든 세션 로그아웃 시 페이지 리로드 또는 로그인 페이지로 리다이렉트
      if (logoutType === 'all') {
        setTimeout(() => {
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          window.location.href = '/login';
        }, 1000);
      } else if (logoutType === 'current') {
        // 현재 세션 로그아웃 시에도 토큰 제거 및 리다이렉트
        setTimeout(() => {
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          window.location.href = '/login';
        }, 1000);
      }

      return data;
    } catch (error) {
      console.error('Error during logout:', error);
      toast({
        title: '로그아웃 실패',
        description: error instanceof Error ? error.message : '로그아웃 중 오류가 발생했습니다.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  // 특정 세션들 로그아웃
  const logoutSpecificSessions = useCallback(async (
    sessionIds: string[],
    reason?: string
  ): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/user/sessions/logout-sessions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_ids: sessionIds,
          reason: reason || 'User requested specific session logout'
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Session logout failed: ${response.status}`);
      }

      const data = await response.json();

      toast({
        title: '세션 로그아웃 성공',
        description: data.message,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      // 세션 목록 새로고침
      await fetchActiveSessions();
    } catch (error) {
      console.error('Error during specific session logout:', error);
      toast({
        title: '세션 로그아웃 실패',
        description: error instanceof Error ? error.message : '세션 로그아웃 중 오류가 발생했습니다.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [toast, fetchActiveSessions]);

  // 세션 활동 기록 조회
  const fetchSessionActivity = useCallback(async (days: number = 30) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/user/sessions/activity?days=${days}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch activity: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching session activity:', error);
      toast({
        title: '활동 기록 조회 실패',
        description: '세션 활동 기록을 가져오는 중 오류가 발생했습니다.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  return {
    isLoading,
    sessionsData,
    fetchActiveSessions,
    executeLogout,
    logoutSpecificSessions,
    fetchSessionActivity,
  };
};

export default useSessionLogout;