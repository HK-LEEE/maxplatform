/**
 * Cross-Domain Logout Utility for MAX Platform
 * 
 * Handles synchronized logout across max.dwchem.co.kr and maxlab.dwchem.co.kr
 * with proper timing and error handling.
 */

interface LogoutOptions {
  maxLabUrl?: string;
  timeout?: number;
  retryCount?: number;
}

interface LogoutResult {
  success: boolean;
  maxLabSynced: boolean;
  error?: string;
}

export class CrossDomainLogoutManager {
  private readonly defaultOptions: Required<LogoutOptions> = {
    maxLabUrl: process.env.NODE_ENV === 'production' 
      ? 'https://maxlab.dwchem.co.kr'
      : 'http://localhost:3010',
    timeout: 3000,     // 🔥 30000 → 3000 (3초)
    retryCount: 1      // 🔥 2 → 1 (재시도 1회만)
  };

  /**
   * Execute cross-domain logout with synchronization
   */
  async executeLogout(options: LogoutOptions = {}): Promise<LogoutResult> {
    const config = { ...this.defaultOptions, ...options };
    
    console.log('🔄 Starting cross-domain logout process...');
    
    try {
      // Step 1: Clear local cookies and storage first
      this.clearLocalStorage();
      this.clearCookies();
      
      // Step 2: Notify MAX Lab with iframe and wait for confirmation
      const maxLabSynced = await this.syncLogoutToMaxLab(config);
      
      // Step 3: Send broadcast event for any other tabs
      this.broadcastLogout();
      
      console.log('✅ Cross-domain logout completed', { maxLabSynced });
      
      return {
        success: true,
        maxLabSynced
      };
      
    } catch (error) {
      console.error('❌ Cross-domain logout failed:', error);
      
      return {
        success: false,
        maxLabSynced: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Synchronize logout with MAX Lab
   */
  private async syncLogoutToMaxLab(config: Required<LogoutOptions>): Promise<boolean> {
    return new Promise((resolve) => {
      let resolved = false;
      let retryCount = 0;
      
      const attemptSync = () => {
        if (resolved || retryCount >= config.retryCount) {
          if (!resolved) {
            console.warn('⚠️ MAX Lab logout sync failed after retries');
            resolve(false);
          }
          return;
        }
        
        retryCount++;
        console.log(`🔄 Attempting MAX Lab logout sync (attempt ${retryCount}/${config.retryCount})`);
        
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = `${config.maxLabUrl}/oauth/logout-sync`;
        
        // Set up timeout
        const timeoutId = setTimeout(() => {
          if (!resolved) {
            console.warn('⚠️ MAX Lab logout sync timeout');
            iframe.remove();
            // Try again if we have retries left
            if (retryCount < config.retryCount) {
              setTimeout(attemptSync, 100); // 🔥 1000 → 100ms
            } else {
              resolved = true;
              resolve(false);
            }
          }
        }, config.timeout);
        
        // Listen for postMessage from iframe
        const messageListener = (event: MessageEvent) => {
          // More flexible origin check for production/development
          const allowedOrigins = [
            'https://maxlab.dwchem.co.kr',
            'http://localhost:3010',
            'http://localhost:8100'
          ];
          
          if (!allowedOrigins.includes(event.origin)) return;
          
          if (event.data?.type === 'SSO_LOGOUT_SYNC' && 
              event.data?.source === 'maxlab' && // Fixed: source should be 'maxlab'
              event.data?.success === true) {
            console.log('✅ MAX Lab logout sync confirmed from', event.origin);
            clearTimeout(timeoutId);
            window.removeEventListener('message', messageListener);
            iframe.remove();
            
            if (!resolved) {
              resolved = true;
              resolve(true);
            }
          }
        };
        
        window.addEventListener('message', messageListener);
        
        iframe.onload = () => {
          console.log('📡 MAX Lab logout sync iframe loaded');
        };
        
        iframe.onerror = () => {
          console.warn('❌ MAX Lab logout sync iframe failed to load');
          clearTimeout(timeoutId);
          window.removeEventListener('message', messageListener);
          iframe.remove();
          
          // Try again if we have retries left
          if (retryCount < config.retryCount) {
            setTimeout(attemptSync, 100); // 🔥 1000 → 100ms
          } else if (!resolved) {
            resolved = true;
            resolve(false);
          }
        };
        
        document.body.appendChild(iframe);
      };
      
      attemptSync();
    });
  }

  /**
   * Clear local storage
   */
  private clearLocalStorage(): void {
    try {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('id_token');
      localStorage.removeItem('user');
      
      // 🔥 즉시 로그아웃 트리거 추가
      localStorage.setItem('logout_trigger', JSON.stringify({
        timestamp: Date.now(),
        source: 'maxplatform'
      }));
      
      // 1초 후 정리
      setTimeout(() => {
        localStorage.removeItem('logout_trigger');
      }, 1000);
      
      console.log('✅ Local storage cleared');
    } catch (error) {
      console.error('❌ Failed to clear local storage:', error);
    }
  }

  /**
   * Clear cookies for .dwchem.co.kr domain
   */
  private clearCookies(): void {
    try {
      const cookiesToClear = [
        'access_token',
        'session_id',
        'session_token', 
        'user_id',
        'refresh_token'
      ];
      
      const isProduction = window.location.hostname.includes('dwchem.co.kr');
      
      cookiesToClear.forEach(cookieName => {
        // Clear for current domain (works on localhost and production)
        document.cookie = `${cookieName}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;`;
        
        // Only set domain cookies in production
        if (isProduction) {
          // Clear for .dwchem.co.kr domain
          document.cookie = `${cookieName}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; domain=.dwchem.co.kr;`;
          
          // Clear for specific subdomains
          document.cookie = `${cookieName}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; domain=max.dwchem.co.kr;`;
          document.cookie = `${cookieName}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; domain=maxlab.dwchem.co.kr;`;
        } else {
          // For localhost, just clear without domain
          document.cookie = `${cookieName}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; domain=localhost;`;
        }
      });
      
      console.log('✅ Cookies cleared');
    } catch (error) {
      console.error('❌ Failed to clear cookies:', error);
    }
  }

  /**
   * Broadcast logout event to other tabs
   */
  private broadcastLogout(): void {
    try {
      // BroadcastChannel for same-origin tabs
      if ('BroadcastChannel' in window) {
        const channel = new BroadcastChannel('max_platform_auth');
        channel.postMessage({ 
          type: 'logout', 
          timestamp: Date.now(),
          source: 'cross_domain_logout'
        });
        channel.close();
      }
      
      // localStorage event for cross-tab communication
      const logoutEvent = JSON.stringify({
        type: 'logout',
        timestamp: Date.now(),
        source: 'cross_domain_logout'
      });
      
      localStorage.setItem('logout_event', logoutEvent);
      
      // Clean up after broadcast
      setTimeout(() => {
        localStorage.removeItem('logout_event');
      }, 1000);
      
      console.log('📡 Logout event broadcasted');
    } catch (error) {
      console.error('❌ Failed to broadcast logout:', error);
    }
  }
}

// Export singleton instance
export const crossDomainLogout = new CrossDomainLogoutManager();