import axios from 'axios'
import { User, Workspace, FileItem, JupyterStatus } from '../types'
import config from '../config/environment'

const API_BASE_URL = `/api`

const api = axios.create({
  baseURL: API_BASE_URL,
})

// 토큰 인터셉터
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 토큰 갱신 중인지 확인하는 플래그
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value?: any) => void
  reject: (reason?: any) => void
}> = []
let consecutiveFailures = 0
let lastError: string | null = null

// 차등적 재시도 정책: 오류 유형에 따른 maxRetries 결정
const getMaxRetries = (errorType: string, errorMessage?: string): number => {
  let maxRetries = 3; // 기본값
  let reason = 'default policy';
  
  if (errorType === 'NETWORK_ERROR' || 
      errorMessage?.includes('Network Error') ||
      errorMessage?.includes('ERR_NETWORK') ||
      errorMessage?.includes('timeout') ||
      errorMessage?.includes('connection') ||
      errorMessage?.includes('fetch')) {
    maxRetries = 5; // 네트워크 오류는 더 관대하게
    reason = 'network error - more tolerant retry policy';
  } else if (errorType === 'INVALID_REFRESH_TOKEN' ||
             errorMessage?.includes('refresh_token_invalid') ||
             errorMessage?.includes('refresh_token_expired') ||
             errorMessage?.includes('invalid_token') ||
             errorMessage?.includes('401') ||
             errorMessage?.includes('unauthorized')) {
    maxRetries = 1; // 토큰 오류는 즉시 처리
    reason = 'token error - immediate failure policy';
  } else if (errorMessage?.includes('403') || 
             errorMessage?.includes('forbidden') ||
             errorMessage?.includes('access_denied')) {
    maxRetries = 1; // 권한 오류는 즉시 처리
    reason = 'permission error - immediate failure policy';
  } else if (errorMessage?.includes('500') || 
             errorMessage?.includes('502') || 
             errorMessage?.includes('503') ||
             errorMessage?.includes('server') ||
             errorMessage?.includes('internal')) {
    maxRetries = 4; // 서버 오류는 중간 정도
    reason = 'server error - moderate retry policy';
  }
  
  console.log(`📋 MAX Platform API: Max retries set to ${maxRetries} (${reason}) for error: ${errorMessage || errorType}`);
  return maxRetries;
};

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token)
    }
  })
  
  failedQueue = []
}

// 응답 인터셉터 - 401 오류 시 토큰 갱신 시도
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // 이미 토큰 갱신 중이면 대기열에 추가
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        }).catch(err => {
          return Promise.reject(err)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = localStorage.getItem('refreshToken')
      
      if (refreshToken) {
        try {
          console.log('🔄 MAX Platform: Attempting token refresh...');
          const response = await api.post('/auth/refresh', {
            refresh_token: refreshToken
          })
          console.log("✅ MAX Platform: refresh token successful")
          console.log(response)
          
          const { access_token } = response.data
          localStorage.setItem('token', access_token)
          
          // 성공 시 실패 카운터 리셋
          if (consecutiveFailures > 0) {
            console.log(`✅ MAX Platform refresh token successful, resetting failure counter (was ${consecutiveFailures})`);
            consecutiveFailures = 0;
            lastError = null;
          }
          
          // 대기 중인 요청들 처리
          processQueue(null, access_token)
          
          // 원래 요청 재시도
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
          
        } catch (refreshError) {
          // axios 에러 객체에서 상세 정보 추출
          let errorMessage = 'Unknown refresh error';
          if (refreshError?.response) {
            // HTTP 응답이 있는 경우 (4xx, 5xx 에러)
            const status = refreshError.response.status;
            const statusText = refreshError.response.statusText;
            const responseData = refreshError.response.data;
            errorMessage = `${status} ${statusText}`;
            if (responseData?.detail) {
              errorMessage += ` - ${responseData.detail}`;
            }
          } else if (refreshError?.request) {
            // 요청은 보냈지만 응답을 받지 못한 경우 (네트워크 에러)
            errorMessage = 'Network Error: No response received';
          } else {
            // 요청 설정 중 에러 발생
            errorMessage = refreshError?.message || String(refreshError);
          }
          
          lastError = errorMessage;
          consecutiveFailures++;
          
          // 차등적 재시도 정책 적용
          const maxRetries = getMaxRetries('REFRESH_TOKEN_ERROR', errorMessage);
          
          console.log(`❌ MAX Platform refresh token failed (attempt ${consecutiveFailures}/${maxRetries}):`, errorMessage);
          console.log(`📊 Error analysis: ${maxRetries} retries allowed for this error type`);
          console.log(`🔍 Refresh error details:`, refreshError);
          
          // 동적 실패 임계값에 도달 시에만 로그아웃
          if (consecutiveFailures >= maxRetries) {
            console.log(`❌ Reached maximum retries (${maxRetries}) for refresh token error, logging out user`);
            console.log(`📊 Failure pattern: ${maxRetries} consecutive failures with error: ${errorMessage}`);
            
            // 리프레시 토큰도 만료된 경우
            processQueue(refreshError, null)
            localStorage.removeItem('token')
            localStorage.removeItem('refreshToken')
            
            // 현재 페이지 정보를 저장하여 로그인 후 돌아올 수 있도록 함
            const currentPath = window.location.pathname
            const authPaths = ['/login', '/register', '/reset-password', '/']
            
            if (!authPaths.includes(currentPath)) {
              localStorage.setItem('redirectAfterLogin', currentPath)
              console.warn('Session expired. Redirecting to login...')
              window.location.href = '/login'
            }
            
            // 실패 카운터 리셋
            consecutiveFailures = 0;
            lastError = null;
          } else {
            // 아직 재시도 가능한 경우 실패를 전파하지만 로그아웃하지 않음
            console.log(`⚠️ Refresh token failed but still have ${maxRetries - consecutiveFailures} retries left`);
            processQueue(refreshError, null);
          }
          
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      } else {
        // 리프레시 토큰이 없는 경우
        localStorage.removeItem('token')
        
        const currentPath = window.location.pathname
        const authPaths = ['/login', '/register', '/reset-password', '/']
        
        if (!authPaths.includes(currentPath)) {
          localStorage.setItem('redirectAfterLogin', currentPath)
          console.warn('No valid session found. Redirecting to login...')
          window.location.href = '/login'
        }
      }
    }
    
    return Promise.reject(error)
  }
)

// 인증 API
export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', {
      email: email,
      password: password,
    })
    return response.data
  },

  register: async (username: string, email: string, password: string) => {
    const response = await api.post('/auth/register', {
      username,
      email,
      password,
    })
    return response.data
  },

  getMe: async (): Promise<User> => {
    const response = await api.get('/auth/me')
    return response.data
  },
}

// authApi alias for compatibility with LoginPage
export const authApi = authAPI

// Services API for mother page
export const servicesApi = {
  getMotherPageServices: async () => {
    const response = await api.get('/services/mother-page')
    return response
  },
}

// 워크스페이스 API
export const workspaceAPI = {
  getWorkspaces: async () => {
    const response = await api.get('/workspaces/')
    return response
  },

  createWorkspace: async (data: { name: string; description?: string }) => {
    const response = await api.post('/workspaces/', data)
    return response
  },

  getWorkspace: async (id: number) => {
    const response = await api.get(`/workspaces/${id}`)
    return response
  },

  startWorkspace: async (id: number) => {
    const response = await api.post(`/workspaces/${id}/start`)
    return response
  },

  stopWorkspace: async (id: number) => {
    const response = await api.post(`/workspaces/${id}/stop`)
    return response
  },

  deleteWorkspace: async (id: number) => {
    const response = await api.delete(`/workspaces/${id}`)
    return response
  },

  // Legacy support
  list: async (): Promise<Workspace[]> => {
    const response = await api.get('/workspaces/')
    return response.data
  },

  create: async (name: string, description?: string): Promise<Workspace> => {
    const response = await api.post('/workspaces/', {
      name,
      description,
    })
    return response.data
  },

  get: async (id: number): Promise<Workspace> => {
    const response = await api.get(`/workspaces/${id}`)
    return response.data
  },

  delete: async (id: number) => {
    const response = await api.delete(`/workspaces/${id}`)
    return response.data
  },
}

// Jupyter API
export const jupyterAPI = {
  start: async (workspaceId: number) => {
    const response = await api.post(`/jupyter/start/${workspaceId}`)
    return response.data
  },

  stop: async (workspaceId: number) => {
    const response = await api.post(`/jupyter/stop/${workspaceId}`)
    return response.data
  },

  getStatus: async (workspaceId: number): Promise<JupyterStatus> => {
    const response = await api.get(`/jupyter/status/${workspaceId}`)
    return response.data
  },
}

// 파일 API
export const fileAPI = {
  list: async (workspaceId: number, path: string = ''): Promise<{ files: FileItem[], current_path: string }> => {
    const response = await api.get(`/files/${workspaceId}/list`, {
      params: { path },
    })
    return response.data
  },

  upload: async (workspaceId: number, files: FileList, path: string = '') => {
    const formData = new FormData()
    Array.from(files).forEach((file) => {
      formData.append('files', file)
    })
    
    const response = await api.post(`/files/${workspaceId}/upload`, formData, {
      params: { path },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  download: async (workspaceId: number, filePath: string) => {
    const response = await api.get(`/files/${workspaceId}/download`, {
      params: { file_path: filePath },
      responseType: 'blob',
    })
    return response.data
  },

  delete: async (workspaceId: number, filePath: string) => {
    const response = await api.delete(`/files/${workspaceId}/delete`, {
      params: { file_path: filePath },
    })
    return response.data
  },

  createFolder: async (workspaceId: number, folderName: string, path: string = '') => {
    const response = await api.post(`/files/${workspaceId}/create-folder`, null, {
      params: { folder_name: folderName, path },
    })
    return response.data
  },
}

// 테스트 유틸리티 함수들 - 차등적 재시도 정책 디버깅용
export const testUtils = {
  // 토큰 리프레시 실패 시뮬레이션
  simulateRefreshFailure: (errorType: 'network' | 'token' | 'server' | 'permission') => {
    const errors = {
      network: new Error('Network Error: fetch failed'),
      token: new Error('401 unauthorized - invalid_token'),
      server: new Error('500 internal server error'),
      permission: new Error('403 forbidden - access_denied')
    };
    
    const error = errors[errorType];
    const errorMessage = error.message;
    
    // 에러 타입별 예상 재시도 정책 표시
    const maxRetries = getMaxRetries('TEST_ERROR', errorMessage);
    console.log(`🧪 MAX Platform Test: Simulating ${errorType} error`);
    console.log(`🧪 Error message: ${errorMessage}`);
    console.log(`🧪 Expected max retries: ${maxRetries}`);
    
    // localStorage에 테스트 에러 정보 저장
    localStorage.setItem('last_refresh_error_test', errorMessage);
    
    return { error, maxRetries, errorMessage };
  },

  // 현재 상태 확인
  showCurrentState: () => {
    const token = localStorage.getItem('token');
    const refreshToken = localStorage.getItem('refreshToken');
    const lastError = localStorage.getItem('last_refresh_error_test');
    
    console.log('🔍 MAX Platform Current State:');
    console.log('- Access Token:', token ? 'Present' : 'Missing');
    console.log('- Refresh Token:', refreshToken ? 'Present' : 'Missing');
    console.log('- Consecutive Failures:', consecutiveFailures);
    console.log('- Last Error:', lastError || 'None');
    console.log('- Is Refreshing:', isRefreshing);
    
    return {
      hasToken: !!token,
      hasRefreshToken: !!refreshToken,
      consecutiveFailures,
      lastError,
      isRefreshing
    };
  },

  // 토큰 만료 강제 실행 (실제 401 에러 발생시키기)
  triggerActualRefresh: async () => {
    console.log('🔄 MAX Platform: Triggering actual refresh by making API call with expired token');
    
    // 현재 토큰을 잘못된 값으로 변경하여 401 에러 유발
    const originalToken = localStorage.getItem('token');
    localStorage.setItem('token', 'invalid_token_for_testing');
    
    try {
      // 실제 API 호출을 통해 401 에러 발생
      await api.get('/auth/me');
    } catch (error) {
      console.log('🧪 Expected 401 error triggered:', error.message);
    } finally {
      // 원래 토큰 복원 (있었다면)
      if (originalToken) {
        localStorage.setItem('token', originalToken);
      }
    }
  },

  // 현재 차등적 재시도 정책 테스트
  testRetryPolicy: () => {
    console.log('🧪 MAX Platform Retry Policy Test:');
    
    const testCases = [
      { type: 'NETWORK_ERROR', message: 'Network Error: fetch failed' },
      { type: 'TOKEN_ERROR', message: '401 unauthorized - invalid_token' },
      { type: 'SERVER_ERROR', message: '500 internal server error' },
      { type: 'PERMISSION_ERROR', message: '403 forbidden - access_denied' }
    ];
    
    testCases.forEach(testCase => {
      const maxRetries = getMaxRetries(testCase.type, testCase.message);
      console.log(`- ${testCase.type}: ${maxRetries} retries`);
    });
  }
};

// 전역에서 접근 가능하도록 설정
if (typeof window !== 'undefined') {
  window.maxPlatformTestUtils = testUtils;
}

export default api

// Flow Studio API
export const flowStudioAPI = {
  // 프로젝트 관련 API
  getProjects: async (skip: number = 0, limit: number = 100) => {
    const response = await api.get('/flow-studio/projects', {
      params: { skip, limit }
    })
    return response.data
  },

  getProject: async (projectId: string) => {
    const response = await api.get(`/flow-studio/projects/${projectId}`)
    return response.data
  },

  createProject: async (projectData: { name: string; description: string }) => {
    const response = await api.post('/flow-studio/projects', projectData)
    return response.data
  },

  updateProject: async (projectId: string, projectData: { name?: string; description?: string }) => {
    const response = await api.put(`/flow-studio/projects/${projectId}`, projectData)
    return response.data
  },

  deleteProject: async (projectId: string) => {
    const response = await api.delete(`/flow-studio/projects/${projectId}`)
    return response.data
  },

  // 플로우 관련 API
  getFlows: async (projectId: string, skip: number = 0, limit: number = 100) => {
    const response = await api.get(`/flow-studio/projects/${projectId}/flows`, {
      params: { skip, limit }
    })
    return response.data
  },

  getFlow: async (flowId: string) => {
    const response = await api.get(`/flow-studio/flows/${flowId}`)
    return response.data
  },

  createFlow: async (flowData: { name: string; description: string; project_id: string }) => {
    const response = await api.post('/flow-studio/flows', flowData)
    return response.data
  },

  updateFlow: async (flowId: string, flowData: { name?: string; description?: string; flow_data?: any }) => {
    const response = await api.put(`/flow-studio/flows/${flowId}`, flowData)
    return response.data
  },

  deleteFlow: async (flowId: string) => {
    const response = await api.delete(`/flow-studio/flows/${flowId}`)
    return response.data
  },

  // 컴포넌트 템플릿 관련 API
  getComponentTemplates: async (category?: string, skip: number = 0, limit: number = 100) => {
    const response = await api.get('/flow-studio/component-templates', {
      params: { category, skip, limit }
    })
    return response.data
  },

  createComponentTemplate: async (templateData: any) => {
    const response = await api.post('/flow-studio/component-templates', templateData)
    return response.data
  },

  // 통계 API
  getStats: async () => {
    const response = await api.get('/flow-studio/stats')
    return response.data
  }
} 