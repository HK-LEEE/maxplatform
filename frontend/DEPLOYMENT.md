# MAX Platform Frontend Deployment Instructions

## OAuth Cookie Transmission Fix - 2025-08-08

### Problem Solved
The OAuth popup was failing to transmit authentication cookies when redirecting to the OAuth authorize endpoint.

### Solution Implemented
Changed from `window.location.href` to `form.submit()` method to ensure cookies are properly transmitted in cross-origin contexts.

### Files Modified
- `/src/pages/LoginPage.jsx` - Lines 86-104 and 213-228
  - Replaced direct URL navigation with form submission
  - This ensures browser automatically includes cookies

### Build Information
- **Old Build**: `index-Bo_g6srw.js` (cached version with bug)
- **New Build**: `index-CgtAsFYR.js` (fixed version with form.submit)
- **Build Date**: 2025-08-08
- **Build Command**: `npm run build`

### Deployment Steps

1. **Build Verification**
   ```bash
   # Verify the new build has form.submit() code
   grep -c ".submit()" dist/assets/index-CgtAsFYR.js
   # Should output: 2
   ```

2. **Deploy to Production**
   The `dist` folder contents need to be deployed to your web server hosting https://max.dwchem.co.kr

   ```bash
   # Example deployment (adjust based on your setup):
   # rsync -avz dist/ user@production-server:/path/to/web/root/
   # OR
   # scp -r dist/* user@production-server:/path/to/web/root/
   ```

3. **Clear CDN Cache (if applicable)**
   If using a CDN, clear the cache for:
   - `/assets/index-*.js`
   - `/index.html`

4. **Browser Testing**
   After deployment, users should:
   - Hard refresh (Ctrl+F5 or Cmd+Shift+R)
   - OR Clear browser cache
   - The new JS file (index-CgtAsFYR.js) should load automatically

### Verification
1. Open browser DevTools Network tab
2. Verify loading `index-CgtAsFYR.js` (not the old `index-Bo_g6srw.js`)
3. Test OAuth login flow - should complete successfully

### Rollback (if needed)
Keep the previous build files as backup. To rollback:
1. Restore the old `dist` folder
2. Redeploy
3. Clear cache

### Technical Details
The issue was that `window.location.href` doesn't reliably transmit cookies in cross-origin popup contexts. Using form submission ensures the browser handles cookie transmission properly according to its security policies.