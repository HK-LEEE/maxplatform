/**
 * Frontend 환경 설정
 * 환경 변수를 중앙에서 관리하는 설정 파일
 */

// 환경 변수 기본값
const defaultConfig = {
  // 공통 설정
  environment: 'production',
  apiBaseUrl: 'https://max.dwchem.co.kr',
  frontendUrl: 'https://max.dwchem.co.kr',
  
  // MAX Platform 서비스 URL
  maxFlowStudioUrl: 'http://localhost:3005',
  maxTeamSyncUrl: 'http://localhost:3015',
  maxLabUrl: 'https://maxlab.dwchem.co.kr',
  maxWorkspaceUrl: 'http://localhost:3020',
  maxApaUrl: 'http://localhost:3035',
  maxMlopsUrl: 'http://localhost:3040',
  maxQueryHubUrl: 'http://localhost:3025',
  maxLlmUrl: 'http://localhost:3030',
  
  // 외부 서비스
  ollamaBaseUrl: 'http://localhost:11434',
  jupyterBaseUrl: 'http://localhost',
  
  // OAuth 설정
  oauthClientId: 'maxplatform',
  oauthScope: 'read:profile read:groups read:features',
  
  // 개발 설정
  debugMode: false,
  apiTimeout: 30000,
};

// 환경 변수에서 설정 읽기 (Vite 환경 변수 시스템 사용)
const config = {
  // 공통 설정
  environment: import.meta.env.VITE_ENVIRONMENT || defaultConfig.environment,
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || defaultConfig.apiBaseUrl,
  frontendUrl: import.meta.env.VITE_FRONTEND_URL || defaultConfig.frontendUrl,
  
  // MAX Platform 서비스 URL
  maxFlowStudioUrl: import.meta.env.VITE_MAX_FLOWSTUDIO_URL || defaultConfig.maxFlowStudioUrl,
  maxTeamSyncUrl: import.meta.env.VITE_MAX_TEAMSYNC_URL || defaultConfig.maxTeamSyncUrl,
  maxLabUrl: import.meta.env.VITE_MAX_LAB_URL || defaultConfig.maxLabUrl,
  maxWorkspaceUrl: import.meta.env.VITE_MAX_WORKSPACE_URL || defaultConfig.maxWorkspaceUrl,
  maxApaUrl: import.meta.env.VITE_MAX_APA_URL || defaultConfig.maxApaUrl,
  maxMlopsUrl: import.meta.env.VITE_MAX_MLOPS_URL || defaultConfig.maxMlopsUrl,
  maxQueryHubUrl: import.meta.env.VITE_MAX_QUERYHUB_URL || defaultConfig.maxQueryHubUrl,
  maxLlmUrl: import.meta.env.VITE_MAX_LLM_URL || defaultConfig.maxLlmUrl,
  
  // 외부 서비스
  ollamaBaseUrl: import.meta.env.VITE_OLLAMA_BASE_URL || defaultConfig.ollamaBaseUrl,
  jupyterBaseUrl: import.meta.env.VITE_JUPYTER_BASE_URL || defaultConfig.jupyterBaseUrl,
  
  // OAuth 설정
  oauthServerUrl: import.meta.env.VITE_OAUTH_SERVER_URL || defaultConfig.oauthServerUrl,
  oauthClientId: import.meta.env.VITE_OAUTH_CLIENT_ID || defaultConfig.oauthClientId,
  oauthScope: import.meta.env.VITE_OAUTH_SCOPE || defaultConfig.oauthScope,
  
  // 개발 설정
  debugMode: import.meta.env.VITE_DEBUG_MODE === 'true' || 
             (import.meta.env.VITE_ENVIRONMENT === 'development' && defaultConfig.debugMode),
  apiTimeout: parseInt(import.meta.env.VITE_API_TIMEOUT || defaultConfig.apiTimeout),
};

// 환경별 검증
if (config.environment === 'production') {
  // Production 환경에서는 HTTPS 사용 강제
  if (!config.apiBaseUrl.startsWith('https://')) {
    console.warn('⚠️  Production 환경에서는 HTTPS를 사용해야 합니다.');
  }
  
  // Production에서 디버그 모드 비활성화
  if (config.debugMode) {
    console.warn('⚠️  Production 환경에서는 디버그 모드를 비활성화해야 합니다.');
    config.debugMode = false;
  }
}

// 개발 환경에서 설정 정보 출력
if (config.debugMode) {
  console.log('🔧 MAX Platform Frontend 설정:', {
    environment: config.environment,
    apiBaseUrl: config.apiBaseUrl,
    frontendUrl: config.frontendUrl,
    debugMode: config.debugMode,
  });
}

export default config;

// 유틸리티 함수들
export const utils = {
  /**
   * API URL 생성
   * @param {string} endpoint - API 엔드포인트
   * @returns {string} - 완전한 API URL
   */
  getApiUrl: (endpoint) => {
    const baseUrl = config.apiBaseUrl.endsWith('/') 
      ? config.apiBaseUrl.slice(0, -1) 
      : config.apiBaseUrl;
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${baseUrl}${cleanEndpoint}`;
  },

  /**
   * OAuth 인증 URL 생성
   * @param {Object} params - OAuth 파라미터
   * @returns {string} - OAuth 인증 URL
   */
  getOAuthUrl: (params = {}) => {
    const defaultParams = {
      response_type: 'code',
      client_id: config.oauthClientId,
      redirect_uri: `${config.frontendUrl}/oauth/callback`,
      scope: config.oauthScope,
    };
    
    const allParams = { ...defaultParams, ...params };
    const queryString = new URLSearchParams(allParams).toString();
    
    return `/api/oauth/authorize?${queryString}`;
  },

  /**
   * 서비스별 URL 가져오기
   * @param {string} serviceName - 서비스 이름 (flowstudio, teamsync, lab 등)
   * @returns {string} - 서비스 URL
   */
  getServiceUrl: (serviceName) => {
    const serviceMap = {
      flowstudio: config.maxFlowStudioUrl,
      teamsync: config.maxTeamSyncUrl,
      lab: config.maxLabUrl,
      workspace: config.maxWorkspaceUrl,
      apa: config.maxApaUrl,
      mlops: config.maxMlopsUrl,
      queryhub: config.maxQueryHubUrl,
      llm: config.maxLlmUrl,
    };

    return serviceMap[serviceName.toLowerCase()] || null;
  },

  /**
   * 환경이 개발 환경인지 확인
   * @returns {boolean}
   */
  isDevelopment: () => config.environment === 'development',

  /**
   * 환경이 운영 환경인지 확인
   * @returns {boolean}
   */
  isProduction: () => config.environment === 'production',
};