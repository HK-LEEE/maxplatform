/**
 * User Switch Security Utilities
 * Handles client-side security cleanup when users switch accounts
 */

interface UserSwitchCleanupOptions {
  preserveTheme?: boolean;
  preserveLanguage?: boolean;
  clearCookies?: boolean;
  clearIndexedDB?: boolean;
  reloadPage?: boolean;
  debugMode?: boolean;
}

interface StorageCleanupResult {
  localStorage: number;
  sessionStorage: number;
  cookies: number;
  indexedDB: boolean;
  success: boolean;
  errors: string[];
}

class UserSwitchSecurityManager {
  private readonly SECURITY_NAMESPACE = 'max_platform_security';
  private readonly USER_CONTEXT_KEYS = [
    'access_token',
    'refresh_token',
    'id_token',
    'user_id',
    'user_email',
    'user_profile',
    'user_permissions',
    'user_groups',
    'user_roles',
    'workspace_data',
    'recent_files',
    'bookmarks',
    'preferences',
    'session_data',
    'oauth_state',
    'oauth_nonce',
    'auth_redirect',
    'current_user'
  ];

  private readonly PRESERVE_KEYS = [
    'theme',
    'language',
    'locale',
    'color_scheme',
    'font_size',
    'accessibility_settings'
  ];

  /**
   * Detect potential user switch by comparing stored user context
   */
  detectUserSwitch(newUserId: string): {
    isUserSwitch: boolean;
    previousUserId: string | null;
    riskLevel: 'low' | 'medium' | 'high';
    recommendations: string[];
  } {
    try {
      const storedUserId = localStorage.getItem('user_id') || sessionStorage.getItem('user_id');
      const storedUserContext = this.getCurrentUserContext();
      
      if (!storedUserId) {
        return {
          isUserSwitch: false,
          previousUserId: null,
          riskLevel: 'low',
          recommendations: []
        };
      }

      if (storedUserId === newUserId) {
        return {
          isUserSwitch: false,
          previousUserId: storedUserId,
          riskLevel: 'low',
          recommendations: []
        };
      }

      // This is a user switch - assess risk
      const riskFactors: string[] = [];
      let riskScore = 0;

      // Check for admin privileges in stored context
      if (storedUserContext.isAdmin || storedUserContext.permissions?.includes('admin')) {
        riskFactors.push('Previous user had admin privileges');
        riskScore += 3;
      }

      // Check for active tokens
      if (storedUserContext.hasTokens) {
        riskFactors.push('Active authentication tokens found');
        riskScore += 2;
      }

      // Check for sensitive data
      if (storedUserContext.hasSensitiveData) {
        riskFactors.push('Sensitive user data in browser storage');
        riskScore += 1;
      }

      const riskLevel = riskScore >= 4 ? 'high' : riskScore >= 2 ? 'medium' : 'low';

      return {
        isUserSwitch: true,
        previousUserId: storedUserId,
        riskLevel,
        recommendations: [
          'Clear all browser storage',
          'Revoke previous user tokens',
          'Clear browser cache',
          ...(riskLevel === 'high' ? ['Consider closing all browser tabs', 'Clear browser cookies'] : [])
        ]
      };

    } catch (error) {
      console.error('🔒 Error detecting user switch:', error);
      return {
        isUserSwitch: true, // Fail secure
        previousUserId: null,
        riskLevel: 'high',
        recommendations: ['Complete browser state cleanup due to detection error']
      };
    }
  }

  /**
   * Perform comprehensive cleanup of user-specific browser state
   */
  async performSecurityCleanup(options: UserSwitchCleanupOptions = {}): Promise<StorageCleanupResult> {
    const result: StorageCleanupResult = {
      localStorage: 0,
      sessionStorage: 0,
      cookies: 0,
      indexedDB: false,
      success: false,
      errors: []
    };

    try {
      console.log('🔒 Starting user switch security cleanup...');

      // 1. Clean localStorage
      result.localStorage = this.cleanStorage('localStorage', options.preserveTheme, options.preserveLanguage);

      // 2. Clean sessionStorage
      result.sessionStorage = this.cleanStorage('sessionStorage', false, false);

      // 3. Clean cookies if requested
      if (options.clearCookies) {
        result.cookies = await this.cleanCookies();
      }

      // 4. Clean IndexedDB if requested
      if (options.clearIndexedDB) {
        result.indexedDB = await this.cleanIndexedDB();
      }

      // 5. Clear service worker caches
      await this.clearServiceWorkerCaches();

      // 6. Clear browser storage APIs
      await this.clearBrowserStorage();

      // 7. Log security cleanup
      this.logSecurityCleanup(result);

      result.success = true;
      console.log('✅ User switch security cleanup completed', result);

      // 8. Reload page if requested
      if (options.reloadPage) {
        setTimeout(() => {
          window.location.reload();
        }, 500);
      }

    } catch (error) {
      console.error('❌ Security cleanup failed:', error);
      result.errors.push(error instanceof Error ? error.message : String(error));
    }

    return result;
  }

  /**
   * Clean specific storage (localStorage or sessionStorage)
   */
  private cleanStorage(storageType: 'localStorage' | 'sessionStorage', preserveTheme: boolean = false, preserveLanguage: boolean = false): number {
    const storage = window[storageType];
    let cleanedCount = 0;

    try {
      const keysToPreserve = new Set<string>();
      
      if (preserveTheme) {
        this.PRESERVE_KEYS.filter(key => key.includes('theme') || key.includes('color')).forEach(key => keysToPreserve.add(key));
      }
      
      if (preserveLanguage) {
        this.PRESERVE_KEYS.filter(key => key.includes('language') || key.includes('locale')).forEach(key => keysToPreserve.add(key));
      }

      // Get all keys to process
      const allKeys = Object.keys(storage);
      
      for (const key of allKeys) {
        const shouldClean = this.shouldCleanStorageKey(key) && !keysToPreserve.has(key);
        
        if (shouldClean) {
          storage.removeItem(key);
          cleanedCount++;
        }
      }

    } catch (error) {
      console.error(`Failed to clean ${storageType}:`, error);
    }

    return cleanedCount;
  }

  /**
   * Determine if a storage key should be cleaned
   */
  private shouldCleanStorageKey(key: string): boolean {
    // Check against user context keys
    if (this.USER_CONTEXT_KEYS.some(contextKey => 
      key.toLowerCase().includes(contextKey.toLowerCase())
    )) {
      return true;
    }

    // Check for MAX Platform specific keys
    if (key.startsWith('max_') || key.includes('maxplatform') || key.includes('oauth')) {
      return true;
    }

    // Check for token-like keys
    if (key.includes('token') || key.includes('auth') || key.includes('session')) {
      return true;
    }

    return false;
  }

  /**
   * Clean cookies
   */
  private async cleanCookies(): Promise<number> {
    let cleanedCount = 0;

    try {
      const cookies = document.cookie.split(';');
      
      for (const cookie of cookies) {
        const [name] = cookie.split('=');
        const cookieName = name.trim();
        
        if (this.shouldCleanStorageKey(cookieName)) {
          // Clear for current domain
          document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
          document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; domain=${window.location.hostname}`;
          
          cleanedCount++;
        }
      }

    } catch (error) {
      console.error('Failed to clean cookies:', error);
    }

    return cleanedCount;
  }

  /**
   * Clean IndexedDB
   */
  private async cleanIndexedDB(): Promise<boolean> {
    try {
      if (!('indexedDB' in window)) {
        return false;
      }

      const databases = await indexedDB.databases();
      
      for (const db of databases) {
        if (db.name && this.shouldCleanStorageKey(db.name)) {
          const deleteRequest = indexedDB.deleteDatabase(db.name);
          await new Promise((resolve, reject) => {
            deleteRequest.onsuccess = () => resolve(true);
            deleteRequest.onerror = () => reject(deleteRequest.error);
          });
        }
      }

      return true;

    } catch (error) {
      console.error('Failed to clean IndexedDB:', error);
      return false;
    }
  }

  /**
   * Clear service worker caches
   */
  private async clearServiceWorkerCaches(): Promise<void> {
    try {
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        
        for (const cacheName of cacheNames) {
          if (this.shouldCleanStorageKey(cacheName)) {
            await caches.delete(cacheName);
          }
        }
      }
    } catch (error) {
      console.error('Failed to clear service worker caches:', error);
    }
  }

  /**
   * Clear other browser storage APIs
   */
  private async clearBrowserStorage(): Promise<void> {
    try {
      // Clear Web SQL (deprecated but may still exist)
      if ('openDatabase' in window) {
        // Web SQL cleanup would go here
      }

      // Clear any other storage mechanisms
      
    } catch (error) {
      console.error('Failed to clear browser storage:', error);
    }
  }

  /**
   * Get current user context from storage
   */
  private getCurrentUserContext(): {
    isAdmin: boolean;
    permissions: string[] | null;
    hasTokens: boolean;
    hasSensitiveData: boolean;
  } {
    try {
      const hasTokens = !!(
        localStorage.getItem('access_token') ||
        sessionStorage.getItem('access_token') ||
        localStorage.getItem('refresh_token') ||
        sessionStorage.getItem('refresh_token')
      );

      const permissions = this.getStoredPermissions();
      const isAdmin = this.getStoredAdminStatus();
      
      const hasSensitiveData = !!(
        localStorage.getItem('user_profile') ||
        localStorage.getItem('workspace_data') ||
        sessionStorage.getItem('user_profile')
      );

      return {
        isAdmin,
        permissions,
        hasTokens,
        hasSensitiveData
      };

    } catch (error) {
      console.error('Failed to get user context:', error);
      return {
        isAdmin: false,
        permissions: null,
        hasTokens: false,
        hasSensitiveData: false
      };
    }
  }

  /**
   * Get stored permissions
   */
  private getStoredPermissions(): string[] | null {
    try {
      const permsStr = localStorage.getItem('user_permissions') || sessionStorage.getItem('user_permissions');
      return permsStr ? JSON.parse(permsStr) : null;
    } catch {
      return null;
    }
  }

  /**
   * Get stored admin status
   */
  private getStoredAdminStatus(): boolean {
    try {
      const adminStr = localStorage.getItem('is_admin') || sessionStorage.getItem('is_admin');
      return adminStr === 'true';
    } catch {
      return false;
    }
  }

  /**
   * Log security cleanup for audit
   */
  private logSecurityCleanup(result: StorageCleanupResult): void {
    try {
      const cleanupEvent = {
        type: 'user_switch_cleanup',
        timestamp: new Date().toISOString(),
        result,
        userAgent: navigator.userAgent,
        url: window.location.href
      };

      // Store in a separate namespace for security audit
      const auditKey = `${this.SECURITY_NAMESPACE}_cleanup_${Date.now()}`;
      sessionStorage.setItem(auditKey, JSON.stringify(cleanupEvent));

      // Clean old audit records (keep only last 10)
      this.cleanOldAuditRecords();

    } catch (error) {
      console.error('Failed to log security cleanup:', error);
    }
  }

  /**
   * Clean old audit records
   */
  private cleanOldAuditRecords(): void {
    try {
      const auditKeys = Object.keys(sessionStorage).filter(key => 
        key.startsWith(`${this.SECURITY_NAMESPACE}_cleanup_`)
      ).sort();

      // Keep only the last 10 records
      if (auditKeys.length > 10) {
        const keysToRemove = auditKeys.slice(0, auditKeys.length - 10);
        keysToRemove.forEach(key => sessionStorage.removeItem(key));
      }

    } catch (error) {
      console.error('Failed to clean old audit records:', error);
    }
  }

  /**
   * Get security cleanup history
   */
  getCleanupHistory(): any[] {
    try {
      const auditKeys = Object.keys(sessionStorage).filter(key => 
        key.startsWith(`${this.SECURITY_NAMESPACE}_cleanup_`)
      );

      return auditKeys.map(key => {
        try {
          return JSON.parse(sessionStorage.getItem(key) || '{}');
        } catch {
          return null;
        }
      }).filter(Boolean);

    } catch (error) {
      console.error('Failed to get cleanup history:', error);
      return [];
    }
  }
}

// Export singleton instance
export const userSwitchSecurity = new UserSwitchSecurityManager();

// Export types
export type { UserSwitchCleanupOptions, StorageCleanupResult };

// Utility functions for React components
export const useUserSwitchSecurity = () => {
  return {
    detectUserSwitch: userSwitchSecurity.detectUserSwitch.bind(userSwitchSecurity),
    performCleanup: userSwitchSecurity.performSecurityCleanup.bind(userSwitchSecurity),
    getCleanupHistory: userSwitchSecurity.getCleanupHistory.bind(userSwitchSecurity)
  };
};

// Auto-cleanup on page load if user switch detected
if (typeof window !== 'undefined') {
  window.addEventListener('load', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const userSwitchFlag = urlParams.get('user_switch_cleanup');
    
    if (userSwitchFlag === 'true') {
      console.log('🔒 Auto-triggering user switch cleanup from URL parameter');
      userSwitchSecurity.performSecurityCleanup({
        clearCookies: true,
        clearIndexedDB: true,
        reloadPage: false
      });
    }
  });
}