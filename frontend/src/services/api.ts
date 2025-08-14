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
          const response = await api.post('/auth/refresh', {
            refresh_token: refreshToken
          })
          console.log("refresh token get")
          console.log(response)
          
          const { access_token } = response.data
          localStorage.setItem('token', access_token)
          
          // 대기 중인 요청들 처리
          processQueue(null, access_token)
          
          // 원래 요청 재시도
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
          
        } catch (refreshError: any) {
          // 리프레시 토큰도 만료된 경우 - 상세 로깅 추가
          console.error('🔴 [MAX Platform] Refresh token failed:', {
            error: refreshError?.response?.data || refreshError?.message || refreshError,
            status: refreshError?.response?.status,
            timestamp: new Date().toISOString(),
            currentUrl: window.location.href,
            hasRefreshToken: !!refreshToken,
            sessionInfo: {
              userId: localStorage.getItem('userId'),
              authMethod: localStorage.getItem('authMethod'),
              lastActivity: localStorage.getItem('lastActivity')
            }
          })
          
          processQueue(refreshError, null)
          
          // 토큰 정리
          localStorage.removeItem('token')
          localStorage.removeItem('refreshToken')
          localStorage.removeItem('userId')
          localStorage.removeItem('authMethod')
          
          // 세션 스토리지 정리
          sessionStorage.clear()
          
          // 현재 페이지 정보를 저장하여 로그인 후 돌아올 수 있도록 함
          const currentPath = window.location.pathname
          const authPaths = ['/login', '/register', '/reset-password', '/']
          
          if (!authPaths.includes(currentPath)) {
            localStorage.setItem('redirectAfterLogin', currentPath)
          }
          
          console.warn('🔓 [MAX Platform] Session expired. Redirecting to login page...')
          
          // 도메인에 관계없이 max.dwchem.co.kr 로그인 페이지로 리다이렉트
          const loginUrl = window.location.hostname.includes('dwchem.co.kr') 
            ? 'https://max.dwchem.co.kr/login' 
            : '/login'
          
          window.location.href = loginUrl
          
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      } else {
        // 리프레시 토큰이 없는 경우 - 상세 로깅 추가
        console.error('🔴 [MAX Platform] No refresh token available:', {
          timestamp: new Date().toISOString(),
          currentUrl: window.location.href,
          sessionInfo: {
            hasToken: !!localStorage.getItem('token'),
            userId: localStorage.getItem('userId'),
            authMethod: localStorage.getItem('authMethod'),
            lastActivity: localStorage.getItem('lastActivity')
          }
        })
        
        // 토큰 정리
        localStorage.removeItem('token')
        localStorage.removeItem('userId')
        localStorage.removeItem('authMethod')
        
        // 세션 스토리지 정리
        sessionStorage.clear()
        
        const currentPath = window.location.pathname
        const authPaths = ['/login', '/register', '/reset-password', '/']
        
        if (!authPaths.includes(currentPath)) {
          localStorage.setItem('redirectAfterLogin', currentPath)
        }
        
        console.warn('🔓 [MAX Platform] No valid session found. Redirecting to login...')
        
        // 도메인에 관계없이 max.dwchem.co.kr 로그인 페이지로 리다이렉트
        const loginUrl = window.location.hostname.includes('dwchem.co.kr') 
          ? 'https://max.dwchem.co.kr/login' 
          : '/login'
        
        window.location.href = loginUrl
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