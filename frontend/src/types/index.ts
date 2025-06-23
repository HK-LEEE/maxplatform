export interface User {
  id: string
  username: string
  email: string
  real_name?: string
  display_name?: string
  phone_number?: string
  department?: string
  position?: string
  is_active: boolean
  is_admin: boolean
  created_at: string
}

export interface Workspace {
  id: number
  name: string
  description?: string
  path: string
  is_active: boolean
  jupyter_port?: number
  jupyter_token?: string
  owner_id: number
  created_at: string
}

export interface FileItem {
  name: string
  is_directory: boolean
  size: number
  path: string
}

export interface AuthContextType {
  user: User | null
  token: string | null
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

export interface JupyterStatus {
  workspace_id: number
  status: string  // 'stopped', 'starting', 'running', 'error'
  is_running: boolean
  port?: number
  url?: string
  last_updated?: string
} 