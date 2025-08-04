import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';

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

  // 활성 세션 목록 조회
  const fetchActiveSessions = useCallback(async (): Promise<SessionsData> => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/user/sessions/active', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
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
      // 세션 정보 조회 실패는 조용히 처리 (사용자에게 오류 표시 안함)
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

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
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
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
      toast.success(data.message);

      return data;
    } catch (error) {
      console.error('Error during logout:', error);
      // 에러를 부모 컴포넌트에서 처리하도록 던지기만 함 (토스트 메시지 제거)
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

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
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
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

      toast.success(data.message);

      // 세션 목록 새로고침
      await fetchActiveSessions();
    } catch (error) {
      console.error('Error during specific session logout:', error);
      toast.error(
        error instanceof Error ? error.message : '세션 로그아웃 중 오류가 발생했습니다.'
      );
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [fetchActiveSessions]);

  // 세션 활동 기록 조회
  const fetchSessionActivity = useCallback(async (days: number = 30) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/user/sessions/activity?days=${days}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
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
      toast.error('세션 활동 기록을 가져오는 중 오류가 발생했습니다.');
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

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