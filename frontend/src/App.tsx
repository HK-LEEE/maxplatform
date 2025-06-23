import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, useNavigate, Navigate } from 'react-router-dom'
import './App.css'
import MainPage from './pages/MotherPage'
import AdminPage from './pages/AdminPage'
import LoginPage from './pages/LoginPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import RegisterPage from './pages/RegisterPage'
import LLMOpsPage from './pages/LLMOpsPage'
import RAGDataSourcePage from './pages/RAGDataSourcePage'
import FlowStudioPage from './pages/FlowStudioPage'
import MainLayout from './components/Layout/MainLayout'
import DashboardPage from './pages/DashboardPage'
import { AuthProvider } from './contexts/AuthContext'
import { Toaster } from 'react-hot-toast'
import FlowStudioProjectsPage from './pages/FlowStudioProjectsPage'
import FlowStudioWorkspacePage from './pages/FlowStudioWorkspacePage'
import WorkspacesPage from './pages/WorkspacesPage'
import ProfilePage from './pages/ProfilePage'
import ChatPage from './pages/ChatPage'



// 인증 체크 컴포넌트
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const navigate = useNavigate()
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      navigate('/login', { replace: true })
    } else {
      // 토큰이 있는 경우 유효성 검증
      fetch('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      .then(response => {
        if (!response.ok) {
          localStorage.removeItem('token')
          navigate('/login', { replace: true })
        } else {
          setIsChecking(false)
        }
      })
      .catch(() => {
        localStorage.removeItem('token')
        navigate('/login', { replace: true })
      })
    }
  }, [navigate])

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return <>{children}</>
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Toaster 
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#fff',
                color: '#374151',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1), 0 4px 10px rgba(0, 0, 0, 0.05)',
                padding: '16px',
                fontSize: '14px',
                maxWidth: '400px',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#fff',
                },
                style: {
                  background: '#f0fdf4',
                  color: '#166534',
                  border: '1px solid #bbf7d0',
                },
              },
              error: {
                duration: 5000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
                style: {
                  background: '#fef2f2',
                  color: '#991b1b',
                  border: '1px solid #fecaca',
                },
              },
              loading: {
                iconTheme: {
                  primary: '#3b82f6',
                  secondary: '#fff',
                },
                style: {
                  background: '#eff6ff',
                  color: '#1e40af',
                  border: '1px solid #bfdbfe',
                },
              },
            }}
          />
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            
            {/* Protected Routes with Main Layout */}
            <Route path="/dashboard" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
              <Route index element={<DashboardPage />} />
              <Route path="llmops" element={<LLMOpsPage />} />
              <Route path="rag-datasources" element={<RAGDataSourcePage />} />
              <Route path="flow-studio" element={<FlowStudioProjectsPage />} />
              <Route path="flow-studio/:projectId/workspace" element={<FlowStudioWorkspacePage />} />
              <Route path="flow-studio/:projectId/workspace/:flowId" element={<FlowStudioWorkspacePage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="workspaces" element={<WorkspacesPage />} />
              <Route path="workspaces/:id" element={<WorkspacesPage />} />
            </Route>
            
            {/* Profile Page */}
            <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
            
            {/* Standalone Protected Routes (without MainLayout) */}
            <Route path="/admin" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
            
            {/* Legacy Routes - Redirect to Dashboard */}
            <Route path="/main" element={<ProtectedRoute><MainPage /></ProtectedRoute>} />
            <Route path="/chat" element={<Navigate to="/dashboard/chat" replace />} />
            <Route path="/workspaces" element={<Navigate to="/dashboard/workspaces" replace />} />
            <Route path="/workspaces/:id" element={<Navigate to="/dashboard/workspaces/:id" replace />} />
            <Route path="/rag-datasources" element={<Navigate to="/dashboard/rag-datasources" replace />} />
            <Route path="/flow-studio" element={<Navigate to="/dashboard/flow-studio" replace />} />
            <Route path="/flow-studio/:projectId/workspace" element={<Navigate to="/dashboard/flow-studio/:projectId/workspace" replace />} />
            <Route path="/flow-studio/:projectId/workspace/:flowId" element={<Navigate to="/dashboard/flow-studio/:projectId/workspace/:flowId" replace />} />
            
            {/* Default Redirect */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            {/* Catch All */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  )
}

export default App 