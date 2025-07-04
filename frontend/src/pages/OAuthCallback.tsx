import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { extractAuthorizationCode, exchangeCodeForToken } from '../utils/oauth';

const OAuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    // Prevent duplicate token requests
    const processedKey = 'oauth_callback_processed';
    if (sessionStorage.getItem(processedKey)) {
      console.log('OAuth callback already processed, skipping...');
      return;
    }
    
    const handleOAuthCallback = async () => {
      try {
        // Mark as processing to prevent duplicates
        sessionStorage.setItem(processedKey, 'true');
        
        // Extract authorization code and state from URL
        const currentUrl = window.location.href;
        const authResult = extractAuthorizationCode(currentUrl);
        
        if (!authResult) {
          throw new Error('Missing authorization code or state parameter');
        }
        
        const { code, state } = authResult;
        
        // Exchange code for token
        const tokenResult = await exchangeCodeForToken(code, state);
        
        // Store the access token
        localStorage.setItem('token', tokenResult.access_token);
        
        // Get the target platform URL from session storage
        const targetPlatform = sessionStorage.getItem('oauth_target_platform');
        
        setStatus('success');
        
        // Redirect to target platform or dashboard after success
        setTimeout(() => {
          if (targetPlatform) {
            sessionStorage.removeItem('oauth_target_platform');
            window.location.href = targetPlatform;
          } else {
            navigate('/dashboard');
          }
          // Clean up processed flag after successful redirect
          sessionStorage.removeItem(processedKey);
        }, 2000);
        
      } catch (error) {
        console.error('OAuth callback error:', error);
        setError(error instanceof Error ? error.message : 'OAuth authentication failed');
        setStatus('error');
        
        // Clean up processed flag on error
        sessionStorage.removeItem(processedKey);
        
        // Redirect to dashboard after error
        setTimeout(() => {
          navigate('/dashboard');
        }, 5000);
      }
    };
    
    handleOAuthCallback();
  }, []); // Empty dependency array to run only once

  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="max-w-md w-full mx-auto p-6">
        <div className="text-center">
          {status === 'processing' && (
            <>
              <div className="p-4 bg-blue-50 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                인증 처리 중...
              </h2>
              <p className="text-gray-600">
                OAuth 인증을 완료하고 있습니다. 잠시만 기다려주세요.
              </p>
            </>
          )}
          
          {status === 'success' && (
            <>
              <div className="p-4 bg-green-50 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                인증 성공!
              </h2>
              <p className="text-gray-600 mb-4">
                OAuth 인증이 성공적으로 완료되었습니다.
              </p>
              <p className="text-sm text-gray-500">
                목적지 플랫폼으로 이동합니다...
              </p>
            </>
          )}
          
          {status === 'error' && (
            <>
              <div className="p-4 bg-red-50 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                <XCircle className="w-8 h-8 text-red-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                인증 실패
              </h2>
              <p className="text-gray-600 mb-4">
                OAuth 인증 중 오류가 발생했습니다:
              </p>
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg mb-4">
                <p className="text-sm text-red-800 font-medium">{error}</p>
              </div>
              <p className="text-sm text-gray-500">
                대시보드로 돌아갑니다...
              </p>
            </>
          )}
        </div>
        
        {/* Loading indicator */}
        {status === 'processing' && (
          <div className="mt-6">
            <div className="bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
            </div>
          </div>
        )}
        
        {/* Manual navigation fallback */}
        {status === 'error' && (
          <div className="mt-6 text-center">
            <button
              onClick={() => navigate('/dashboard')}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
            >
              대시보드로 돌아가기
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default OAuthCallback;