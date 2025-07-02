import React, { useState, useEffect } from 'react';
import {
  Lock, Edit3, Trash2, Plus, Search, RefreshCw, Key, Eye, EyeOff,
  Globe, CheckCircle, XCircle, Clock, AlertCircle, Copy, ExternalLink
} from 'lucide-react';

interface OAuthClient {
  id: string;
  client_id: string;
  client_name: string;
  description?: string;
  redirect_uris: string[];
  allowed_scopes: string[];
  is_confidential: boolean;
  is_active: boolean;
  logo_url?: string;
  homepage_url?: string;
  created_at: string;
  updated_at: string;
}

interface OAuthClientUpdate {
  client_name?: string;
  description?: string;
  redirect_uris?: string[];
  allowed_scopes?: string[];
  is_active?: boolean;
  logo_url?: string;
  homepage_url?: string;
}

const OAuthClientManager: React.FC = () => {
  const [clients, setClients] = useState<OAuthClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedClient, setSelectedClient] = useState<OAuthClient | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showSecretModal, setShowSecretModal] = useState(false);
  const [newSecret, setNewSecret] = useState<string>('');
  const [editData, setEditData] = useState<OAuthClientUpdate>({});

  const availableScopes = [
    'read:profile',
    'read:features', 
    'read:groups',
    'manage:workflows',
    'manage:teams',
    'manage:experiments',
    'manage:workspaces',
    'manage:apis',
    'manage:models',
    'manage:queries',
    'manage:llm',
    'admin:full'
  ];

  useEffect(() => {
    fetchClients();
  }, []);

  const fetchClients = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/admin/oauth/clients', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setClients(data);
      }
    } catch (error) {
      console.error('Failed to fetch OAuth clients:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateClient = async (clientId: string, updateData: OAuthClientUpdate) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/admin/oauth/clients/${clientId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updateData)
      });

      if (response.ok) {
        await fetchClients();
        setShowEditModal(false);
        setSelectedClient(null);
        setEditData({});
      }
    } catch (error) {
      console.error('Failed to update client:', error);
    }
  };

  const handleRegenerateSecret = async (clientId: string) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/admin/oauth/clients/${clientId}/regenerate-secret`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setNewSecret(data.client_secret);
        setShowSecretModal(true);
      }
    } catch (error) {
      console.error('Failed to regenerate secret:', error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // You might want to show a toast notification here
  };

  const filteredClients = clients.filter(client =>
    client.client_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    client.client_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const openEditModal = (client: OAuthClient) => {
    setSelectedClient(client);
    setEditData({
      client_name: client.client_name,
      description: client.description,
      redirect_uris: client.redirect_uris,
      allowed_scopes: client.allowed_scopes,
      is_active: client.is_active,
      logo_url: client.logo_url,
      homepage_url: client.homepage_url
    });
    setShowEditModal(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">OAuth 클라이언트 관리</h2>
            <p className="text-sm text-gray-600 mt-1">
              MAX 플랫폼 OAuth 2.0 클라이언트를 관리합니다
            </p>
          </div>
          
          <div className="flex space-x-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="클라이언트 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
              />
            </div>
            <button
              onClick={fetchClients}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              <span>새로고침</span>
            </button>
          </div>
        </div>
      </div>

      {/* Client Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredClients.map((client) => (
          <div key={client.id} className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${client.is_active ? 'bg-green-50' : 'bg-gray-50'}`}>
                  <Lock className={`w-5 h-5 ${client.is_active ? 'text-green-600' : 'text-gray-400'}`} />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{client.client_name}</h3>
                  <p className="text-sm text-gray-500">{client.client_id}</p>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                {client.is_active ? (
                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                    활성
                  </span>
                ) : (
                  <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs font-medium rounded-full">
                    비활성
                  </span>
                )}
                
                <button
                  onClick={() => openEditModal(client)}
                  className="p-1 hover:bg-gray-100 rounded transition-colors"
                >
                  <Edit3 className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            </div>

            {client.description && (
              <p className="text-sm text-gray-600 mb-4">{client.description}</p>
            )}

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Redirect URIs
                </label>
                <div className="mt-1 space-y-1">
                  {client.redirect_uris.map((uri, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-700 flex-1">
                        {uri}
                      </code>
                      <button
                        onClick={() => copyToClipboard(uri)}
                        className="p-1 hover:bg-gray-100 rounded transition-colors"
                      >
                        <Copy className="w-3 h-3 text-gray-400" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                  허용된 스코프
                </label>
                <div className="mt-1 flex flex-wrap gap-1">
                  {client.allowed_scopes.map((scope) => (
                    <span
                      key={scope}
                      className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full"
                    >
                      {scope}
                    </span>
                  ))}
                </div>
              </div>

              {client.homepage_url && (
                <div className="flex items-center space-x-2">
                  <Globe className="w-4 h-4 text-gray-400" />
                  <a
                    href={client.homepage_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:text-blue-800 flex items-center space-x-1"
                  >
                    <span>{client.homepage_url}</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}

              <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                <span className="text-xs text-gray-500">
                  {client.is_confidential ? 'Confidential' : 'Public'} Client
                </span>
                
                {client.is_confidential && (
                  <button
                    onClick={() => handleRegenerateSecret(client.client_id)}
                    className="flex items-center space-x-1 px-3 py-1 text-xs bg-yellow-50 text-yellow-700 rounded-lg hover:bg-yellow-100 transition-colors"
                  >
                    <Key className="w-3 h-3" />
                    <span>시크릿 재생성</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredClients.length === 0 && (
        <div className="text-center py-12">
          <Lock className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">검색 결과가 없습니다</p>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedClient && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-gray-900">
                클라이언트 수정: {selectedClient.client_name}
              </h3>
              <button
                onClick={() => setShowEditModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  클라이언트 이름
                </label>
                <input
                  type="text"
                  value={editData.client_name || ''}
                  onChange={(e) => setEditData({ ...editData, client_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  설명
                </label>
                <textarea
                  value={editData.description || ''}
                  onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Redirect URIs (각 줄마다 하나씩)
                </label>
                <textarea
                  value={editData.redirect_uris?.join('\n') || ''}
                  onChange={(e) => setEditData({ 
                    ...editData, 
                    redirect_uris: e.target.value.split('\n').filter(uri => uri.trim()) 
                  })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  허용된 스코프
                </label>
                <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3">
                  {availableScopes.map((scope) => (
                    <label key={scope} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={editData.allowed_scopes?.includes(scope) || false}
                        onChange={(e) => {
                          const currentScopes = editData.allowed_scopes || [];
                          if (e.target.checked) {
                            setEditData({
                              ...editData,
                              allowed_scopes: [...currentScopes, scope]
                            });
                          } else {
                            setEditData({
                              ...editData,
                              allowed_scopes: currentScopes.filter(s => s !== scope)
                            });
                          }
                        }}
                        className="rounded border-gray-300"
                      />
                      <span className="text-sm text-gray-700">{scope}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  홈페이지 URL
                </label>
                <input
                  type="url"
                  value={editData.homepage_url || ''}
                  onChange={(e) => setEditData({ ...editData, homepage_url: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200"
                />
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={editData.is_active !== false}
                  onChange={(e) => setEditData({ ...editData, is_active: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <label className="text-sm text-gray-700">활성 상태</label>
              </div>
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowEditModal(false)}
                className="px-4 py-2 text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
              <button
                onClick={() => handleUpdateClient(selectedClient.client_id, editData)}
                className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                저장
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Secret Modal */}
      {showSecretModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-gray-900">새 클라이언트 시크릿</h3>
              <button
                onClick={() => setShowSecretModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-start space-x-2">
                  <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
                  <div className="text-sm text-yellow-800">
                    <p className="font-medium">중요한 보안 정보</p>
                    <p>이 시크릿은 다시 표시되지 않습니다. 안전한 곳에 저장해주세요.</p>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  클라이언트 시크릿
                </label>
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={newSecret}
                    readOnly
                    className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg font-mono text-sm"
                  />
                  <button
                    onClick={() => copyToClipboard(newSecret)}
                    className="px-3 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={() => setShowSecretModal(false)}
                className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OAuthClientManager;