import React, { useState } from 'react';
import { initiateOAuthFlow } from '../utils/oauth';
import config from '../config/environment';

/**
 * Test component for OAuth flow
 * Use this to test cross-origin OAuth authentication
 */
const OAuthTestButton: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  const handleTestOAuth = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      console.log('🧪 Testing OAuth flow...');
      console.log('Config:', {
        oauthServerUrl: config.oauthServerUrl,
        maxLabUrl: config.maxLabUrl,
        frontendUrl: config.frontendUrl
      });
      
      // Test OAuth flow with MaxLab URL
      await initiateOAuthFlow(config.maxLabUrl);
      
      setSuccess('OAuth flow initiated successfully! Check console for details.');
    } catch (err) {
      console.error('OAuth test failed:', err);
      setError(err instanceof Error ? err.message : 'OAuth test failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 border border-gray-200 rounded-lg bg-yellow-50">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        OAuth Test
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Test the cross-origin OAuth flow between max.dwchem.co.kr and maxlab.dwchem.co.kr
      </p>
      
      <div className="space-y-2 mb-4">
        <div className="text-xs">
          <strong>OAuth Server:</strong> {config.oauthServerUrl || 'Not configured'}
        </div>
        <div className="text-xs">
          <strong>Target Platform:</strong> {config.maxLabUrl}
        </div>
        <div className="text-xs">
          <strong>Frontend URL:</strong> {config.frontendUrl}
        </div>
      </div>
      
      <button
        onClick={handleTestOAuth}
        disabled={loading}
        className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
          loading
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700'
        }`}
      >
        {loading ? 'Testing OAuth...' : 'Test OAuth Flow'}
      </button>
      
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">
            <strong>Error:</strong> {error}
          </p>
        </div>
      )}
      
      {success && (
        <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-700">
            <strong>Success:</strong> {success}
          </p>
        </div>
      )}
    </div>
  );
};

export default OAuthTestButton;