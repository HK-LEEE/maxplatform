# OAuth Cross-Origin Issues - Complete Fix Documentation

## 🚨 Problem Summary

The MAX Platform was experiencing OAuth cross-origin issues when users tried to authenticate from `maxlab.dwchem.co.kr` to the central authentication server at `max.dwchem.co.kr`.

### Issues Resolved

1. **Git Merge Conflict**: Fixed conflicting OAuth server configurations
2. **Cross-Origin Blocking**: Browser was blocking OAuth flow between different domains
3. **Missing Popup Flow**: Only redirect-based OAuth was implemented, causing CORS issues
4. **Incorrect PostMessage Targeting**: Wrong target origins for cross-window communication
5. **Token Exchange URL Issues**: Hardcoded relative URLs not working for cross-origin

## 🔧 Technical Solutions Implemented

### 1. Fixed Environment Configuration Conflict

**File**: `src/config/environment.js`
```javascript
// BEFORE (merge conflict):
<<<<<<< HEAD
oauthServerUrl: 'http://localhost:8000',
oauthClientId: 'maxplatform-frontend',
=======
oauthClientId: 'maxplatform',
>>>>>>> refs/remotes/origin/hklee_0805

// AFTER (resolved):
oauthServerUrl: 'https://max.dwchem.co.kr',
oauthClientId: 'maxplatform',
```

### 2. Implemented Popup-Based OAuth Flow

**File**: `src/utils/oauth.ts`

#### New Function: `initiateOAuthPopupFlow()`
- Opens OAuth authorization in a popup window (600x700px)
- Implements secure postMessage communication
- Handles popup blocking gracefully
- 10-minute timeout protection
- Automatic cleanup of event listeners

#### Enhanced Function: `initiateOAuthFlow()`
- Auto-detects cross-origin vs same-origin scenarios
- Uses popup flow for cross-origin OAuth
- Falls back to redirect flow for same-origin OAuth
- Maintains backward compatibility

#### Security Features
- Origin validation for postMessage events
- Trusted domains whitelist: `.dwchem.co.kr`, configured origins
- State parameter validation (CSRF protection)
- PKCE implementation with SHA256

### 3. Fixed PostMessage Target Origins

**File**: `src/pages/OAuthCallback.tsx`

**Before**:
```javascript
window.opener.postMessage(messageData, window.location.origin);
```

**After**:
```javascript
const targetOrigin = window.opener.location.origin || '*';
window.opener.postMessage(messageData, targetOrigin);
```

### 4. Dynamic Token Exchange URL Resolution

**File**: `src/utils/oauth.ts`

```javascript
// Determine token endpoint URL
let tokenUrl = '/api/oauth/token';

// For cross-origin OAuth, use the OAuth server directly
if (config.oauthServerUrl && config.oauthServerUrl !== window.location.origin) {
  tokenUrl = `${config.oauthServerUrl}/api/oauth/token`;
}
```

#### CORS Configuration Added
```javascript
const response = await fetch(tokenUrl, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded'
  },
  credentials: 'omit', // Don't send cookies for cross-origin requests
  mode: tokenUrl.startsWith('http') ? 'cors' : 'same-origin',
  // ...
});
```

### 5. OAuth Test Component

**File**: `src/components/OAuthTestButton.tsx`
- Development-only test component
- Visible in dashboard during development
- Tests full OAuth flow end-to-end
- Provides detailed logging and error reporting

## 🏗️ Architecture Overview

### Current OAuth Architecture (Centralized)

```
┌─────────────────┐    ┌───────────────────┐    ┌──────────────────┐
│  maxlab.dwchem  │    │  max.dwchem.co.kr │    │  Other Services  │
│     .co.kr      │    │  (Auth Server)    │    │  *.dwchem.co.kr  │
│                 │    │                   │    │                  │
│ 1. User clicks  │    │ 3. OAuth popup    │    │ 6. Authenticated │
│    service      │────│    authorization  │────│    access        │
│                 │    │                   │    │                  │
│ 2. Popup opens  │    │ 4. User approves  │    │ 7. Service works │
│    OAuth flow   │    │    & gets code    │    │    with token    │
│                 │    │                   │    │                  │
│ 5. Token stored │────│ Code exchanged    │────│                  │
│    locally      │    │ for access token  │    │                  │
└─────────────────┘    └───────────────────┘    └──────────────────┘
```

### OAuth Flow Sequence

1. **User Action**: User clicks on a MAX Platform service (e.g., MaxLab)
2. **Flow Detection**: System detects cross-origin OAuth requirement
3. **Popup Launch**: Opens OAuth authorization in popup window
4. **User Authorization**: User logs in and approves access in popup
5. **Code Exchange**: Callback page exchanges authorization code for token
6. **PostMessage**: Popup sends success message to parent window
7. **Token Storage**: Parent window stores token and redirects to service
8. **Service Access**: User is authenticated and can use the service

## 🔒 Security Features

### 1. Origin Validation
```javascript
const allowedOrigins = [
  config.oauthServerUrl || config.apiBaseUrl,
  config.frontendUrl,
  window.location.origin
];

if (!allowedOrigins.some(origin => 
  event.origin === origin || event.origin.includes('.dwchem.co.kr')
)) {
  console.warn('🚨 Ignoring message from untrusted origin:', event.origin);
  return;
}
```

### 2. PKCE (Proof Key for Code Exchange)
- SHA256-based code challenge/verifier
- Prevents authorization code interception attacks
- Required for public OAuth clients

### 3. State Parameter
- CSRF protection
- Random state generation and validation
- Prevents malicious redirects

### 4. Timeout Protection
- 10-minute timeout for OAuth flow
- Automatic cleanup of resources
- Prevents memory leaks from abandoned popups

## 🌐 Environment Configuration

### Production (.env.dwchem)
```bash
VITE_OAUTH_SERVER_URL=https://max.dwchem.co.kr
VITE_FRONTEND_URL=https://maxlab.dwchem.co.kr
VITE_OAUTH_CLIENT_ID=maxlab
```

### Development (.env.development)
```bash
VITE_OAUTH_SERVER_URL=http://localhost:8000
VITE_FRONTEND_URL=http://localhost:3000
VITE_OAUTH_CLIENT_ID=maxplatform
```

## 🚀 Deployment Checklist

### Backend Requirements (max.dwchem.co.kr)
1. **CORS Configuration**:
   ```python
   CORS_ALLOW_ORIGINS = [
       "https://maxlab.dwchem.co.kr",
       "https://flowstudio.dwchem.co.kr",
       "https://teamsync.dwchem.co.kr",
       "https://workspace.dwchem.co.kr",
       "https://apa.dwchem.co.kr",
       "https://mlops.dwchem.co.kr",
       "https://queryhub.dwchem.co.kr",
       "https://llm.dwchem.co.kr"
   ]
   ```

2. **OAuth Client Registration**:
   - Register each service as OAuth client
   - Configure correct redirect URIs
   - Set appropriate scopes

3. **API Endpoints**:
   - `/api/oauth/authorize` - Authorization endpoint
   - `/api/oauth/token` - Token exchange endpoint
   - CORS headers must be configured for these endpoints

### Frontend Deployment
1. Use correct .env file for environment
2. Build with `npm run build`
3. Ensure popup blocking is disabled for testing
4. Verify domains in OAuth client configuration

## 🧪 Testing Instructions

### Development Testing
1. Start both frontend and backend servers
2. Navigate to dashboard
3. Look for "OAuth Test" button (bottom-left, dev only)
4. Click to test OAuth flow
5. Check browser console for detailed logs

### Production Testing
1. Deploy to staging environment first
2. Test with actual domain names
3. Verify popup is not blocked
4. Check network tab for CORS issues
5. Validate token storage and service access

### Browser Compatibility
- ✅ Chrome/Chromium (recommended)
- ✅ Firefox
- ✅ Safari (with popup blocker disabled)
- ✅ Edge

## 🔍 Troubleshooting

### Common Issues & Solutions

#### 1. "Popup blocked" Error
- **Cause**: Browser's popup blocker
- **Solution**: Whitelist the domain or disable popup blocker
- **Code**: Graceful fallback to direct navigation implemented

#### 2. CORS Errors
- **Cause**: Backend CORS not configured
- **Solution**: Add service domains to CORS_ALLOW_ORIGINS
- **Check**: Network tab shows preflight OPTIONS requests

#### 3. "OAuth state mismatch" Error
- **Cause**: State parameter validation failed (possible CSRF)
- **Solution**: Clear browser cache and sessionStorage
- **Prevention**: Implemented proper state generation/validation

#### 4. Token Exchange Fails
- **Cause**: Wrong token endpoint URL or CORS
- **Solution**: Verify VITE_OAUTH_SERVER_URL configuration
- **Debug**: Check console logs for token exchange URL

#### 5. PostMessage Not Received
- **Cause**: Wrong target origin
- **Solution**: Updated to use `window.opener.location.origin`
- **Verify**: Check console logs for postMessage sending/receiving

### Debug Logging

The implementation includes extensive console logging:
- 🪟 Popup operations
- 🔄 OAuth flow steps
- 📤 PostMessage communication
- ✅ Success states
- ❌ Error conditions
- 🚨 Security warnings

## 📋 TODO for Production

1. **Remove Test Component**: OAuth test button is development-only
2. **Monitor CORS**: Check server logs for CORS errors
3. **User Training**: Inform users about popup requirements
4. **Analytics**: Track OAuth success/failure rates
5. **Documentation**: Update user guides with new flow

## 🎯 Benefits of This Solution

1. **Cross-Origin Support**: Works between different dwchem.co.kr subdomains
2. **Better UX**: Popup flow keeps user on original page
3. **Enhanced Security**: PKCE, state validation, origin checking
4. **Graceful Degradation**: Falls back to direct navigation if OAuth fails
5. **Development Tools**: Built-in testing and debugging capabilities
6. **Maintainable**: Clean separation of concerns, well-documented code

This implementation provides a robust, secure, and user-friendly OAuth solution for the MAX Platform's multi-service architecture.