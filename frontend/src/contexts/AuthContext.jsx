import React, { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // 로그인 시 토큰을 localStorage에서 확인
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      // TODO: 토큰 검증 API 호출
      setUser({ 
        id: '4d8ab9f7-25df-498b-a321-c217df1f181c', 
        username: 'testuser', 
        email: 'test@example.com' 
      })
    }
    setLoading(false)
  }, [])

  const login = async (email, password) => {
    try {
      // TODO: 실제 API 호출
      const response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      })

      if (!response.ok) {
        throw new Error('Login failed')
      }

      const data = await response.json()
      localStorage.setItem('token', data.access_token)
      setUser(data.user)
      return data
    } catch (error) {
      throw error
    }
  }

  const register = async (username, email, password) => {
    try {
      // TODO: 실제 API 호출
      const response = await fetch('http://localhost:8000/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, email, password })
      })

      if (!response.ok) {
        throw new Error('Registration failed')
      }

      const data = await response.json()
      localStorage.setItem('token', data.access_token)
      setUser(data.user)
      return data
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  const value = {
    user,
    loading,
    login,
    register,
    logout
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
} 