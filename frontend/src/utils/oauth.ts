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
    
    const response = await fetch(`/api/oauth/token`, {
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