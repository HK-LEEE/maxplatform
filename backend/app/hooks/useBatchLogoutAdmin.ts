import { useState, useCallback } from 'react';
import { useToast } from '@chakra-ui/react';

interface BatchLogoutJob {
  job_id: string;
  type: string;
  status: string;
  priority: string;
  dry_run: boolean;
  progress: number;
  initiated_by: {
    id: string;
    email: string;
    name: string;
  };
  reason: string;
  conditions: any;
  statistics?: any;
  error_details?: any;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  cancelled_at?: string;
}

interface BatchLogoutStatistics {
  total_jobs: number;
  processing_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  emergency_jobs: number;
  total_users_affected: number;
  total_tokens_revoked: number;
}

interface GroupLogoutData {
  group_id: string;
  include_subgroups: boolean;
  exclude_admin_users: boolean;
  reason: string;
  notify_users: boolean;
  dry_run: boolean;
}

interface ClientLogoutData {
  client_id: string;
  revoke_refresh_tokens: boolean;
  reason: string;
  created_before?: string;
  dry_run: boolean;
}

interface TimeBasedLogoutData {
  created_before?: string;
  last_used_before?: string;
  token_types: string[];
  reason: string;
  dry_run: boolean;
}

interface EmergencyLogoutData {
  confirm: string;
  exclude_admin_sessions: boolean;
  preserve_service_tokens: boolean;
  reason: string;
  authorized_by: string;
}

export const useBatchLogoutAdmin = () => {
  const [jobs, setJobs] = useState<BatchLogoutJob[]>([]);
  const [statistics, setStatistics] = useState<BatchLogoutStatistics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  // API 호출 헬퍼 함수
  const apiCall = useCallback(async (
    url: string, 
    options: RequestInit = {}
  ): Promise<any> => {
    const defaultOptions: RequestInit = {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    const response = await fetch(url, defaultOptions);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }, []);

  // 일괄 로그아웃 작업 목록 조회
  const fetchJobs = useCallback(async (filters?: {
    status?: string;
    job_type?: string;
    limit?: number;
    skip?: number;
  }) => {
    setIsLoading(true);
    try {
      const queryParams = new URLSearchParams();
      if (filters?.status) queryParams.append('status', filters.status);
      if (filters?.job_type) queryParams.append('job_type', filters.job_type);
      if (filters?.limit) queryParams.append('limit', filters.limit.toString());
      if (filters?.skip) queryParams.append('skip', filters.skip.toString());

      const url = `/api/admin/oauth/batch-logout/jobs${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      const data = await apiCall(url);
      setJobs(data);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      toast({
        title: '작업 목록 조회 실패',
        description: error instanceof Error ? error.message : '작업 목록을 가져올 수 없습니다.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  }, [apiCall, toast]);

  // 통계 정보 조회
  const fetchStatistics = useCallback(async () => {
    try {
      // 현재 작업들에서 통계 계산
      const totalJobs = jobs.length;
      const processingJobs = jobs.filter(job => job.status === 'processing').length;
      const completedJobs = jobs.filter(job => job.status === 'completed').length;
      const failedJobs = jobs.filter(job => job.status === 'failed').length;
      const emergencyJobs = jobs.filter(job => job.type === 'emergency').length;

      // 통계 집계
      const totalUsersAffected = jobs.reduce((sum, job) => {
        return sum + (job.statistics?.total_users_affected || 0);
      }, 0);

      const totalTokensRevoked = jobs.reduce((sum, job) => {
        const accessTokens = job.statistics?.total_access_tokens_revoked || 0;
        const refreshTokens = job.statistics?.total_refresh_tokens_revoked || 0;
        return sum + accessTokens + refreshTokens;
      }, 0);

      setStatistics({
        total_jobs: totalJobs,
        processing_jobs: processingJobs,
        completed_jobs: completedJobs,
        failed_jobs: failedJobs,
        emergency_jobs: emergencyJobs,
        total_users_affected: totalUsersAffected,
        total_tokens_revoked: totalTokensRevoked,
      });
    } catch (error) {
      console.error('Failed to calculate statistics:', error);
    }
  }, [jobs]);

  // 특정 작업 상세 조회
  const fetchJobDetails = useCallback(async (jobId: string): Promise<BatchLogoutJob | null> => {
    try {
      const data = await apiCall(`/api/admin/oauth/batch-logout/jobs/${jobId}`);
      return data;
    } catch (error) {
      console.error('Failed to fetch job details:', error);
      toast({
        title: '작업 상세 조회 실패',
        description: error instanceof Error ? error.message : '작업 상세 정보를 가져올 수 없습니다.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      return null;
    }
  }, [apiCall, toast]);

  // 작업 취소
  const cancelJob = useCallback(async (jobId: string, reason: string): Promise<void> => {
    try {
      await apiCall(`/api/admin/oauth/batch-logout/jobs/${jobId}`, {
        method: 'DELETE',
        body: JSON.stringify({ reason }),
      });

      // 작업 목록 새로고침
      await fetchJobs();
    } catch (error) {
      console.error('Failed to cancel job:', error);
      throw error;
    }
  }, [apiCall, fetchJobs]);

  // 그룹 기반 로그아웃 생성
  const createGroupLogout = useCallback(async (data: GroupLogoutData): Promise<void> => {
    try {
      await apiCall('/api/admin/oauth/batch-logout/group', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      // 작업 목록 새로고침
      await fetchJobs();
    } catch (error) {
      console.error('Failed to create group logout:', error);
      throw error;
    }
  }, [apiCall, fetchJobs]);

  // 클라이언트 기반 로그아웃 생성
  const createClientLogout = useCallback(async (data: ClientLogoutData): Promise<void> => {
    try {
      await apiCall('/api/admin/oauth/batch-logout/client', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      await fetchJobs();
    } catch (error) {
      console.error('Failed to create client logout:', error);
      throw error;
    }
  }, [apiCall, fetchJobs]);

  // 시간 기반 로그아웃 생성
  const createTimeBasedLogout = useCallback(async (data: TimeBasedLogoutData): Promise<void> => {
    try {
      await apiCall('/api/admin/oauth/batch-logout/time-based', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      await fetchJobs();
    } catch (error) {
      console.error('Failed to create time-based logout:', error);
      throw error;
    }
  }, [apiCall, fetchJobs]);

  // 긴급 로그아웃 생성
  const createEmergencyLogout = useCallback(async (
    data: EmergencyLogoutData,
    emergencyKey: string
  ): Promise<void> => {
    try {
      await apiCall('/api/admin/oauth/batch-logout/emergency', {
        method: 'POST',
        headers: {
          'X-Emergency-Key': emergencyKey,
        },
        body: JSON.stringify(data),
      });

      await fetchJobs();
    } catch (error) {
      console.error('Failed to create emergency logout:', error);
      throw error;
    }
  }, [apiCall, fetchJobs]);

  // 긴급 키 요청
  const requestEmergencyKey = useCallback(async (): Promise<string> => {
    try {
      const result = await apiCall('/api/admin/oauth/batch-logout/request-emergency-key', {
        method: 'POST',
      });
      return result.message || '긴급 키가 전송되었습니다.';
    } catch (error) {
      console.error('Failed to request emergency key:', error);
      throw error;
    }
  }, [apiCall]);

  // 시스템 통계 조회 (긴급 로그아웃용)
  const fetchSystemStats = useCallback(async () => {
    try {
      // 실제 구현에서는 별도의 시스템 통계 API 호출
      // 현재는 더미 데이터 반환
      return {
        total_active_users: 1250,
        total_active_sessions: 3780,
        total_active_tokens: 7560
      };
    } catch (error) {
      console.error('Failed to fetch system stats:', error);
      return {
        total_active_users: '추정 불가',
        total_active_sessions: '추정 불가',
        total_active_tokens: '추정 불가'
      };
    }
  }, []);

  // 그룹 목록 조회
  const fetchGroups = useCallback(async () => {
    try {
      return await apiCall('/api/admin/groups');
    } catch (error) {
      console.error('Failed to fetch groups:', error);
      throw error;
    }
  }, [apiCall]);

  // OAuth 클라이언트 목록 조회
  const fetchClients = useCallback(async () => {
    try {
      return await apiCall('/api/admin/oauth/clients');
    } catch (error) {
      console.error('Failed to fetch clients:', error);
      throw error;
    }
  }, [apiCall]);

  // 작업 실시간 상태 업데이트 (WebSocket 대신 polling 사용)
  const startPolling = useCallback((intervalMs: number = 30000) => {
    const interval = setInterval(() => {
      fetchJobs();
    }, intervalMs);

    return () => clearInterval(interval);
  }, [fetchJobs]);

  return {
    // State
    jobs,
    statistics,
    isLoading,

    // Actions
    fetchJobs,
    fetchStatistics,
    fetchJobDetails,
    cancelJob,
    
    // Logout operations
    createGroupLogout,
    createClientLogout,
    createTimeBasedLogout,
    createEmergencyLogout,
    
    // Utility functions
    requestEmergencyKey,
    fetchSystemStats,
    fetchGroups,
    fetchClients,
    startPolling,
  };
};

export default useBatchLogoutAdmin;