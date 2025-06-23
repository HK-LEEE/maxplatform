import api from '../services/api'

interface TokenPayload {
  exp: number
  sub: string
  type: string
}

/**
 * JWT 토큰을 디코딩하여 페이로드를 반환
 */
export const decodeToken = (token: string): TokenPayload | null => {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch (error) {
    console.error('토큰 디코딩 실패:', error)
    return null
  }
}

/**
 * 토큰이 만료되었는지 확인
 */
export const isTokenExpired = (token: string): boolean => {
  const payload = decodeToken(token)
  if (!payload) return true
  
  const currentTime = Math.floor(Date.now() / 1000)
  return payload.exp < currentTime
}

/**
 * 토큰이 곧 만료될지 확인 (5분 전)
 */
export const isTokenExpiringSoon = (token: string): boolean => {
  const payload = decodeToken(token)
  if (!payload) return true
  
  const currentTime = Math.floor(Date.now() / 1000)
  const fiveMinutesFromNow = currentTime + (5 * 60) // 5분
  
  return payload.exp < fiveMinutesFromNow
}

/**
 * 토큰 자동 갱신
 */
export const refreshTokenIfNeeded = async (): Promise<boolean> => {
  const token = localStorage.getItem('token')
  const refreshToken = localStorage.getItem('refreshToken')
  
  if (!token || !refreshToken) {
    return false
  }
  
  // 토큰이 곧 만료되거나 이미 만료된 경우 갱신
  if (isTokenExpiringSoon(token)) {
    try {
      const response = await api.post('/auth/refresh', {
        refresh_token: refreshToken
      })
      
      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      
      console.log('토큰이 자동으로 갱신되었습니다.')
      return true
    } catch (error) {
      console.error('토큰 갱신 실패:', error)
      // 리프레시 토큰도 만료된 경우
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      return false
    }
  }
  
  return true
}

/**
 * 주기적으로 토큰 상태를 확인하고 갱신
 */
export const startTokenRefreshTimer = (): number => {
  return setInterval(async () => {
    const success = await refreshTokenIfNeeded()
    if (!success) {
      // 토큰 갱신 실패 시 로그인 페이지로 리다이렉트
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
  }, 4 * 60 * 1000) // 4분마다 체크
}

/**
 * 토큰 정보 조회
 */
export const getTokenInfo = (token: string) => {
  const payload = decodeToken(token)
  if (!payload) return null
  
  return {
    userId: payload.sub,
    expiresAt: new Date(payload.exp * 1000),
    type: payload.type,
    isExpired: isTokenExpired(token),
    isExpiringSoon: isTokenExpiringSoon(token)
  }
} 