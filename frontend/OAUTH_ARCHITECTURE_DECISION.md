# OAuth Architecture Decision

## Current Issue
The OAuth popup was trying to redirect to `max.dwchem.co.kr`, but the application is configured for `maxlab.dwchem.co.kr`. This suggests a mismatch in OAuth server configuration.

## Two Architecture Options

### Option 1: Centralized OAuth Server (RECOMMENDED)
**Configuration**: Use `max.dwchem.co.kr` as central authentication server for all MAX Platform services.

**Benefits**:
- Single sign-on across all MAX Platform services
- Consistent user experience
- Centralized user management
- Better security through centralized auth

**Implementation**:
- Set `VITE_OAUTH_SERVER_URL=https://max.dwchem.co.kr`
- Configure CORS on max.dwchem.co.kr to allow maxlab.dwchem.co.kr
- Update OAuth redirect URIs to use cross-origin callbacks

**CORS Configuration Required on max.dwchem.co.kr**:
```python
# Backend CORS configuration
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

### Option 2: Same-Origin OAuth (CURRENT)
**Configuration**: Each service (maxlab.dwchem.co.kr) handles its own OAuth.

**Benefits**:
- No CORS issues
- Each service is independent
- Simpler deployment

**Drawbacks**:
- Users must authenticate separately for each service
- No single sign-on
- More complex user management

**Implementation**:
- Keep `authServer = window.location.origin`
- Ensure each service has its own OAuth endpoints
- Remove references to central auth server

## Recommendation

**Use Option 1 (Centralized OAuth)** because:
1. Your logs show OAuth was already trying to use `max.dwchem.co.kr`
2. Multi-service architecture benefits from centralized auth
3. Better user experience with SSO
4. The configuration I implemented supports both options

## Current Implementation

The updated code now supports both architectures:

1. **If `VITE_OAUTH_SERVER_URL` is set**: Uses centralized OAuth server
2. **If not set**: Falls back to same-origin OAuth

Choose your architecture by setting or not setting `VITE_OAUTH_SERVER_URL` in your environment files.

## Next Steps

1. Decide which architecture you want
2. If centralized: Configure CORS on max.dwchem.co.kr
3. If same-origin: Remove `VITE_OAUTH_SERVER_URL` from .env.dwchem
4. Test OAuth flow with chosen configuration