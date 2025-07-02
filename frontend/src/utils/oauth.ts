/**
 * OAuth 2.0 PKCE Helper Functions
 * Provides utilities for OAuth 2.0 Authorization Code Flow with PKCE
 */

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
    redirect_uri: 'http://localhost:3010/oauth/callback',
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:experiments']
  },
  maxteamsync: {
    client_id: 'maxteamsync',
    redirect_uri: 'http://localhost:3015/oauth/callback',
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:teams']
  },
  maxworkspace: {
    client_id: 'maxworkspace',
    redirect_uri: 'http://localhost:3020/oauth/callback',
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:workspaces']
  },
  maxqueryhub: {
    client_id: 'maxqueryhub',
    redirect_uri: 'http://localhost:3025/oauth/callback',
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:queries']
  },
  maxllm: {
    client_id: 'maxllm',
    redirect_uri: 'http://localhost:3030/oauth/callback',
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:llm']
  },
  maxapa: {
    client_id: 'maxapa',
    redirect_uri: 'http://localhost:3035/oauth/callback',
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:apis']
  },
  maxmlops: {
    client_id: 'maxmlops',
    redirect_uri: 'http://localhost:3040/oauth/callback',
    scopes: ['read:profile', 'read:features', 'read:groups', 'manage:models']
  }
};

export type OAuthClientId = keyof typeof OAUTH_CLIENTS;

// Get client config by URL or client ID
export const getClientConfigByUrl = (url: string): typeof OAUTH_CLIENTS[OAuthClientId] | null => {
  // Extract port from URL
  const match = url.match(/localhost:(\d+)/);
  if (!match) return null;
  
  const port = match[1];
  const portToClientMap: { [key: string]: OAuthClientId } = {
    '3010': 'maxlab',
    '3015': 'maxteamsync',
    '3020': 'maxworkspace',
    '3025': 'maxqueryhub',
    '3030': 'maxllm',
    '3035': 'maxapa',
    '3040': 'maxmlops'
  };
  
  const clientId = portToClientMap[port];
  return clientId ? OAUTH_CLIENTS[clientId] : null;
};

// Build OAuth authorization URL
export const buildAuthorizationUrl = async (
  clientConfig: typeof OAUTH_CLIENTS[OAuthClientId],
  state?: string
): Promise<string> => {
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);
  const authState = state || generateState();
  
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
  
  const authServer = 'http://localhost:8000'; // MAX Platform OAuth server
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
  const response = await fetch('http://localhost:8000/api/oauth/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
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
    throw new Error(`Token exchange failed: ${errorData.detail || response.statusText}`);
  }
  
  const tokenData = await response.json();
  
  // Clean up session storage
  sessionStorage.removeItem('oauth_code_verifier');
  sessionStorage.removeItem('oauth_state');
  sessionStorage.removeItem('oauth_client_id');
  
  return tokenData;
};

// Initiate OAuth flow for a specific platform
export const initiateOAuthFlow = async (platformUrl: string): Promise<void> => {
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