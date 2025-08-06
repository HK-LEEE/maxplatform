# OAuth URL Fix - DWChem Deployment Issue

## Problem Description

The OAuth redirect URL was incorrectly pointing to `https://api.maxplatform.com/api/oauth/authorize` instead of `https://maxlab.dwchem.co.kr/api/oauth/authorize`, causing CORS issues and request abortions during login.

### Error Symptoms
- "🚀 Popup redirecting to OAuth URL: https://api.maxplatform.com/api/oauth/authorize..."
- "❌ 인증 초기화 실패: Request aborted, AxiosError: ECONNABORTED"

## Root Cause

The issue was in the build process. Even though the correct environment variables were set in `.env.dwchem`, Vite was not properly reading these environment variables during the build process, causing it to fall back to the default values in `src/config/environment.js`.

## Files Affected

1. **LoginPage.jsx** - Uses `config.apiBaseUrl` for OAuth URL construction
2. **src/config/environment.js** - Environment configuration with fallback to defaults
3. **build-dwchem.sh** - Build script that wasn't exporting environment variables
4. **`.env.dwchem`** - Environment variables for DWChem deployment

## Fix Applied

### 1. Updated build-dwchem.sh

Added environment variable export before building:

```bash
# Export environment variables so Vite can access them
set -a
source .env
set +a
```

### 2. Fixed OAuth Scope Quoting

Fixed environment variable with spaces to prevent bash interpretation errors:

```bash
# Before
VITE_OAUTH_SCOPE=openid profile email offline_access read:profile read:groups manage:workflows

# After  
VITE_OAUTH_SCOPE="openid profile email offline_access read:profile read:groups manage:workflows"
```

## Verification

### Before Fix
- Built assets contained: `https://api.maxplatform.com`
- OAuth redirect failed with CORS errors

### After Fix  
- Built assets contain: `https://maxlab.dwchem.co.kr`
- All service URLs correctly point to `*.dwchem.co.kr` domains
- No remaining `maxplatform.com` references

## URLs Now Correctly Set

All service URLs now point to the correct DWChem domains:

- API Base: `https://maxlab.dwchem.co.kr`
- Frontend: `https://maxlab.dwchem.co.kr`
- Flow Studio: `https://flowstudio.dwchem.co.kr`
- Team Sync: `https://teamsync.dwchem.co.kr`
- Workspace: `https://workspace.dwchem.co.kr`
- APA: `https://apa.dwchem.co.kr`
- MLOps: `https://mlops.dwchem.co.kr`
- Query Hub: `https://queryhub.dwchem.co.kr`
- LLM: `https://llm.dwchem.co.kr`
- Ollama: `https://ollama.dwchem.co.kr`
- Jupyter: `https://jupyter.dwchem.co.kr`

## Build Instructions

To build the frontend for DWChem deployment:

```bash
./build-dwchem.sh
```

The script will:
1. Copy `.env.dwchem` to `.env`
2. Export all environment variables
3. Run `npm run build`
4. Clean up the temporary `.env` file

## Deployment

Deploy the generated `dist/` directory to `https://maxlab.dwchem.co.kr`.