/**
 * OAuth 2.0 PKCE Helper Functions
 * Provides utilities for OAuth 2.0 Authorization Code Flow with PKCE
 */

import config from '../config/environment';

// Generate a random string for code verifier
export const generateCodeVerifier = (): string => {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
};

// Generate code challenge from verifier using SHA256
export const generateCodeChallenge = async (verifier: string): Promise<string> => {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return base64URLEncode(new Uint8Array(digest));
};

// Base64 URL encode (without padding)
const base64URLEncode = (array: Uint8Array): string => {
  return btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
};

// Generate random state parameter
export const generateState = (): string => {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
};

// OAuth client configuration for MAX platforms
export const OAUTH_CLIENTS = {
  maxlab: {
    client_id: 'maxlab',
    redirect_uri: `${config.maxLabUrl}/oauth/callback`,
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:experiments']
  },
  maxteamsync: {
    client_id: 'maxteamsync',
    redirect_uri: `${config.maxTeamSyncUrl}/oauth/callback`,
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:teams']
  },
  maxworkspace: {
    client_id: 'maxworkspace',
    redirect_uri: `${config.maxWorkspaceUrl}/oauth/callback`,
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:workspaces']
  },
  maxqueryhub: {
    client_id: 'maxqueryhub',
    redirect_uri: `${config.maxQueryHubUrl}/oauth/callback`,
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:queries']
  },
  maxllm: {
    client_id: 'maxllm',
    redirect_uri: `${config.maxLlmUrl}/oauth/callback`,
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:llm']
  },
  maxapa: {
    client_id: 'maxapa',
    redirect_uri: `${config.maxApaUrl}/oauth/callback`,
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:apis']
  },
  maxmlops: {
    client_id: 'maxmlops',
    redirect_uri: `${config.maxMlopsUrl}/oauth/callback`,
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:models']
  }
};

export type OAuthClientId = keyof typeof OAUTH_CLIENTS;

// Get client config by URL or client ID
export const getClientConfigByUrl = (url: string): typeof OAUTH_CLIENTS[OAuthClientId] | null => {
  // Create URL mapping based on environment config
  const urlToClientMap: { [key: string]: OAuthClientId } = {
    [config.maxLabUrl]: 'maxlab',
    [config.maxTeamSyncUrl]: 'maxteamsync',
    [config.maxWorkspaceUrl]: 'maxworkspace',
    [config.maxQueryHubUrl]: 'maxqueryhub',
    [config.maxLlmUrl]: 'maxllm',
    [config.maxApaUrl]: 'maxapa',
    [config.maxMlopsUrl]: 'maxmlops'
  };
  
  // Try to match the full URL or base URL
  for (const [baseUrl, clientId] of Object.entries(urlToClientMap)) {
    if (url.startsWith(baseUrl)) {
      return OAUTH_CLIENTS[clientId];
    }
  }
  
  return null;
};

// Build OAuth authorization URL
export const buildAuthorizationUrl = async (
  clientConfig: typeof OAUTH_CLIENTS[OAuthClientId],
  state?: string
): Promise<string> => {
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);
  
  // Generate state with origin information
  const stateData = {
    random: generateState(),
    origin: window.location.origin,
    timestamp: Date.now()
  };
  const authState = state || btoa(JSON.stringify(stateData));
  
  // Store PKCE parameters in sessionStorage for later use
  sessionStorage.setItem('oauth_code_verifier', codeVerifier);
  sessionStorage.setItem('oauth_state', authState);
  sessionStorage.setItem('oauth_client_id', clientConfig.client_id);
  
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: clientConfig.client_id,
    redirect_uri: clientConfig.redirect_uri,
    scope: clientConfig.scopes.join(' '),
    state: authState,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256'
  });
  
  // Determine OAuth server URL
  let authServer = config.oauthServerUrl || config.apiBaseUrl;
  
  // For dwchem.co.kr deployments, use central auth server if configured
  if (window.location.hostname.includes('dwchem.co.kr')) {
    if (config.oauthServerUrl) {
      // Use explicitly configured OAuth server (central auth)
      authServer = config.oauthServerUrl;
    } else {
      // Fallback to same-origin to avoid CORS issues
      authServer = window.location.origin;
    }
  }
  
  return `${authServer}/api/oauth/authorize?${params.toString()}`;
};

// Extract OAuth authorization code from callback URL
export const extractAuthorizationCode = (url: string): { code: string; state: string } | null => {
  const urlObj = new URL(url);
  const code = urlObj.searchParams.get('code');
  const state = urlObj.searchParams.get('state');
  const error = urlObj.searchParams.get('error');
  
  if (error) {
    console.error('OAuth authorization error:', error);
    const errorDescription = urlObj.searchParams.get('error_description');
    throw new Error(`OAuth authorization failed: ${error}${errorDescription ? ` - ${errorDescription}` : ''}`);
  }
  
  if (!code || !state) {
    return null;
  }
  
  return { code, state };
};

// Exchange authorization code for access token
export const exchangeCodeForToken = async (
  code: string,
  state: string
): Promise<{ access_token: string; token_type: string; expires_in: number; scope: string }> => {
  // Prevent duplicate token exchange requests
  const exchangeKey = `oauth_exchange_${code}`;
  if (sessionStorage.getItem(exchangeKey)) {
    throw new Error('Token exchange already in progress for this code');
  }
  
  try {
    // Mark this code as being exchanged
    sessionStorage.setItem(exchangeKey, 'true');
    
    // Verify state parameter
    const storedState = sessionStorage.getItem('oauth_state');
    if (state !== storedState) {
      throw new Error('OAuth state mismatch - possible CSRF attack');
    }
    
    // Get stored PKCE parameters
    const codeVerifier = sessionStorage.getItem('oauth_code_verifier');
    const clientId = sessionStorage.getItem('oauth_client_id');
    
    if (!codeVerifier || !clientId) {
      throw new Error('Missing OAuth PKCE parameters');
    }
    
    const client = OAUTH_CLIENTS[clientId as OAuthClientId];
    if (!client) {
      throw new Error('Invalid OAuth client');
    }
    
    // Exchange code for token
    console.log(`🔄 Exchanging authorization code for token (client: ${client.client_id})`);
    
    // Determine token endpoint URL
    let tokenUrl = '/api/oauth/token';
    
    // For cross-origin OAuth, use the OAuth server directly
    if (config.oauthServerUrl && config.oauthServerUrl !== window.location.origin) {
      tokenUrl = `${config.oauthServerUrl}/api/oauth/token`;
    }
    
    console.log(`🔗 Token exchange URL: ${tokenUrl}`);
    
    const response = await fetch(tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      credentials: 'omit', // Don't send cookies for cross-origin requests
      mode: tokenUrl.startsWith('http') ? 'cors' : 'same-origin',
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: client.redirect_uri,
        client_id: client.client_id,
        code_verifier: codeVerifier
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error(`❌ Token exchange failed (${response.status}):`, errorData);
      
      // Provide more specific error messages
      if (response.status === 400) {
        if (errorData.detail && errorData.detail.includes('expired')) {
          throw new Error('Authorization code has expired. Please try logging in again.');
        }
        if (errorData.detail && errorData.detail.includes('invalid_grant')) {
          throw new Error('Invalid authorization code. This may be due to a duplicate request.');
        }
      }
      
      throw new Error(`Token exchange failed: ${errorData.detail || response.statusText}`);
    }
    
    const tokenData = await response.json();
    
    console.log(`✅ Token exchange successful (client: ${client.client_id})`);
    
    // Clean up session storage
    sessionStorage.removeItem('oauth_code_verifier');
    sessionStorage.removeItem('oauth_state');
    sessionStorage.removeItem('oauth_client_id');
    sessionStorage.removeItem(exchangeKey);
    
    return tokenData;
  } catch (error) {
    console.error(`❌ Token exchange error (client: ${clientId}):`, error);
    
    // Clean up exchange key and session storage on error
    sessionStorage.removeItem(exchangeKey);
    sessionStorage.removeItem('oauth_code_verifier');
    sessionStorage.removeItem('oauth_state');
    sessionStorage.removeItem('oauth_client_id');
    
    throw error;
  }
};

// Initiate OAuth flow using popup window for cross-origin authentication
export const initiateOAuthPopupFlow = async (platformUrl: string): Promise<void> => {
  const clientConfig = getClientConfigByUrl(platformUrl);
  
  if (!clientConfig) {
    console.warn('No OAuth client configuration found for URL:', platformUrl);
    // Fallback to direct navigation for non-OAuth platforms
    window.open(platformUrl, '_blank');
    return;
  }
  
  try {
    const authUrl = await buildAuthorizationUrl(clientConfig);
    
    // Store the target platform URL to redirect after authentication
    sessionStorage.setItem('oauth_target_platform', platformUrl);
    
    console.log('🪟 Opening OAuth popup for:', authUrl);
    
    // Open OAuth flow in popup window for cross-origin support
    const popup = window.open(
      authUrl,
      'oauth_popup',
      'width=600,height=700,scrollbars=yes,resizable=yes,status=yes'
    );
    
    if (!popup) {
      throw new Error('Popup blocked. Please allow popups for this site.');
    }
    
    // Return promise that resolves when OAuth completes
    return new Promise((resolve, reject) => {
      const messageHandler = (event: MessageEvent) => {
        // Verify origin for security
        const allowedOrigins = [
          config.oauthServerUrl || config.apiBaseUrl,
          config.frontendUrl,
          window.location.origin
        ];
        
        if (!allowedOrigins.some(origin => event.origin === origin || event.origin.includes('.dwchem.co.kr'))) {
          console.warn('🚨 Ignoring message from untrusted origin:', event.origin);
          return;
        }
        
        if (event.data?.type === 'OAUTH_SUCCESS') {
          console.log('✅ OAuth popup success:', event.data);
          window.removeEventListener('message', messageHandler);
          
          // Handle the OAuth success
          handleOAuthPopupSuccess(event.data, platformUrl)
            .then(() => resolve())
            .catch(reject);
            
        } else if (event.data?.type === 'OAUTH_LOGIN_SUCCESS_CONTINUE') {
          console.log('🔄 OAuth login successful, continuing OAuth flow...', event.data);
          
          // 로그인 성공 후 OAuth 플로우 계속 진행
          const { oauthParams } = event.data;
          
          // prompt=login과 max_age 제거 (무한 루프 방지)
          delete oauthParams.prompt;
          delete oauthParams.max_age;
          
          // 팝업을 닫고 부모 창에서 직접 OAuth 토큰을 가져와서 플랫폼으로 이동
          if (!popup.closed) {
            popup.close();
          }
          window.removeEventListener('message', messageHandler);
          
          console.log('✅ Login successful in popup, navigating to platform with existing auth...');
          
          // 인증이 완료되었으므로 목적지 플랫폼으로 직접 이동
          window.location.href = platformUrl;
          resolve();
          
        } else if (event.data?.type === 'OAUTH_ALREADY_AUTHENTICATED') {
          console.log('✅ User already authenticated, navigating to platform...', event.data);
          
          // 이미 인증된 사용자 - 팝업 닫고 플랫폼으로 이동
          if (!popup.closed) {
            popup.close();
          }
          window.removeEventListener('message', messageHandler);
          
          // 목적지 플랫폼으로 직접 이동
          window.location.href = platformUrl;
          resolve();
          
        } else if (event.data?.type === 'OAUTH_ERROR') {
          console.error('❌ OAuth popup error:', event.data);
          window.removeEventListener('message', messageHandler);
          reject(new Error(event.data.error || 'OAuth authentication failed'));
        }
      };
      
      // Listen for messages from popup
      window.addEventListener('message', messageHandler);
      
      // Check if popup is closed without authentication
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          window.removeEventListener('message', messageHandler);
          reject(new Error('OAuth popup was closed without completing authentication'));
        }
      }, 1000);
      
      // Cleanup after 10 minutes timeout
      setTimeout(() => {
        clearInterval(checkClosed);
        window.removeEventListener('message', messageHandler);
        if (!popup.closed) {
          popup.close();
        }
        reject(new Error('OAuth authentication timeout'));
      }, 10 * 60 * 1000);
    });
    
  } catch (error) {
    console.error('Failed to initiate OAuth popup flow:', error);
    // Fallback to direct navigation
    window.open(platformUrl, '_blank');
  }
};

// Handle OAuth success from popup
const handleOAuthPopupSuccess = async (data: any, platformUrl: string): Promise<void> => {
  try {
    console.log('🔄 Processing OAuth popup success...');
    
    // Exchange code for token
    const tokenResult = await exchangeCodeForToken(data.code, data.state);
    
    // Store the access token
    localStorage.setItem('token', tokenResult.access_token);
    
    console.log('✅ OAuth token stored, redirecting to platform...');
    
    // Clean up session storage
    sessionStorage.removeItem('oauth_target_platform');
    
    // Navigate to the target platform
    window.location.href = platformUrl;
    
  } catch (error) {
    console.error('❌ Failed to handle OAuth popup success:', error);
    throw error;
  }
};

// Initiate OAuth flow for a specific platform (backward compatibility)
export const initiateOAuthFlow = async (platformUrl: string): Promise<void> => {
  // Use popup flow for cross-origin OAuth, fallback to redirect for same-origin
  if (config.oauthServerUrl && config.oauthServerUrl !== window.location.origin) {
    return initiateOAuthPopupFlow(platformUrl);
  }
  
  // Original redirect-based flow for same-origin OAuth
  const clientConfig = getClientConfigByUrl(platformUrl);
  
  if (!clientConfig) {
    console.warn('No OAuth client configuration found for URL:', platformUrl);
    window.open(platformUrl, '_blank');
    return;
  }
  
  try {
    const authUrl = await buildAuthorizationUrl(clientConfig);
    
    // Store the target platform URL to redirect after authentication
    sessionStorage.setItem('oauth_target_platform', platformUrl);
    
    // Redirect to OAuth authorization server
    window.location.href = authUrl;
  } catch (error) {
    console.error('Failed to initiate OAuth flow:', error);
    // Fallback to direct navigation
    window.open(platformUrl, '_blank');
  }
};

// Check if a URL is a MAX platform that supports OAuth
export const isOAuthSupportedPlatform = (url: string): boolean => {
  return getClientConfigByUrl(url) !== null;
};