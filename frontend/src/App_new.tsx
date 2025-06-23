import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom'
import './App.css'
import MainPage from './pages/MotherPage'
import AdminPage from './pages/AdminPage'
import LoginPage from './pages/LoginPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import RegisterPage from './pages/RegisterPage'
import LLMOpsPage from './pages/LLMOpsPage'
import RAGDataSourcePage from './pages/RAGDataSourcePage'
import FlowStudioPage from './pages/FlowStudioPage'
import DashboardLayout from './components/Layout/DashboardLayout'
import DashboardPage from './pages/DashboardPage'
import { AuthProvider } from './contexts/AuthContext'

import WorkspacesPage from './pages/WorkspacesPage'

// 인증 체크 컴포넌트
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const navigate = useNavigate()
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      navigate('/login')
    } else {
      setIsChecking(false)
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
          <Routes>
            <Route path="/" element={<LoginPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            
            {/* Dashboard Layout Routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }>
              <Route index element={<DashboardPage />} />
            </Route>
            
            <Route path="/llmops" element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }>
              <Route index element={<LLMOpsPage />} />
            </Route>
            
            <Route path="/analytics" element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }>
              <Route index element={<div className="p-8 text-center text-gray-500">Analytics Page - Coming Soon</div>} />
            </Route>
            
            <Route path="/workspaces" element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }>
              <Route index element={<WorkspacesPage />} />
            </Route>
            
            <Route path="/admin" element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }>
              <Route index element={<AdminPage />} />
            </Route>
            
            {/* Legacy routes for backward compatibility */}
            <Route path="/main" element={<ProtectedRoute><MainPage /></ProtectedRoute>} />
            <Route path="/rag-datasources" element={<ProtectedRoute><RAGDataSourcePage /></ProtectedRoute>} />
            <Route path="/flow-studio" element={<ProtectedRoute><FlowStudioPage /></ProtectedRoute>} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  )
}

export default App 