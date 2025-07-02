import React, { useState, useEffect } from 'react';
import {
  Globe, Users, Trash2, Search, RefreshCw, Clock, User,
  CheckCircle, AlertTriangle, Calendar
} from 'lucide-react';

interface OAuthSession {
  id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  client_id: string;
  client_name: string;
  granted_scopes: string[];
  last_used_at: string;
  created_at: string;
}

const OAuthSessionManager: React.FC = () => {
  const [sessions, setSessions] = useState<OAuthSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterClient, setFilterClient] = useState<string>('');
  const [showRevokeModal, setShowRevokeModal] = useState(false);
  const [selectedSession, setSelectedSession] = useState<OAuthSession | null>(null);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/admin/oauth/sessions', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (error) {
      console.error('Failed to fetch OAuth sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/admin/oauth/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        await fetchSessions();
        setShowRevokeModal(false);
        setSelectedSession(null);
      }
    } catch (error) {
      console.error('Failed to revoke session:', error);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getTimeSince = (dateString: string) => {
    const now = new Date();
    const date = new Date(dateString);
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) {
      return `${diffDays}일 전`;
    } else if (diffHours > 0) {
      return `${diffHours}시간 전`;
    } else {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return `${diffMinutes}분 전`;
    }
  };

  const uniqueClients = [...new Set(sessions.map(s => s.client_name))];

  const filteredSessions = sessions.filter(session => {
    const matchesSearch = 
      session.user_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.user_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.client_name.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesClient = !filterClient || session.client_name === filterClient;
    
    return matchesSearch && matchesClient;
  });

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
            <h2 className="text-xl font-semibold text-gray-900">OAuth 세션 관리</h2>
            <p className="text-sm text-gray-600 mt-1">
              사용자별 OAuth 2.0 인증 세션을 모니터링하고 관리합니다
            </p>
          </div>
          
          <div className="flex space-x-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="사용자 또는 클라이언트 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
              />
            </div>
            
            <select
              value={filterClient}
              onChange={(e) => setFilterClient(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-200"
            >
              <option value="">모든 클라이언트</option>
              {uniqueClients.map(client => (
                <option key={client} value={client}>{client}</option>
              ))}
            </select>
            
            <button
              onClick={fetchSessions}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              <span>새로고침</span>
            </button>
          </div>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-blue-50 rounded-xl">
              <Globe className="w-6 h-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">총 세션</p>
              <p className="text-2xl font-bold text-gray-900">{sessions.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-green-50 rounded-xl">
              <Users className="w-6 h-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">활성 사용자</p>
              <p className="text-2xl font-bold text-gray-900">
                {new Set(sessions.map(s => s.user_id)).size}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-purple-50 rounded-xl">
              <CheckCircle className="w-6 h-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">활성 클라이언트</p>
              <p className="text-2xl font-bold text-gray-900">
                {new Set(sessions.map(s => s.client_id)).size}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Sessions Table */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">사용자</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">클라이언트</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">스코프</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">마지막 사용</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">생성일</th>
                <th className="text-right px-6 py-4 text-sm font-medium text-gray-600">작업</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredSessions.map((session) => (
                <tr key={session.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-gray-100 rounded-full">
                        <User className="w-4 h-4 text-gray-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{session.user_name}</p>
                        <p className="text-sm text-gray-500">{session.user_email}</p>
                      </div>
                    </div>
                  </td>
                  
                  <td className="px-6 py-4">
                    <div>
                      <p className="font-medium text-gray-900">{session.client_name}</p>
                      <p className="text-sm text-gray-500">{session.client_id}</p>
                    </div>
                  </td>
                  
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1 max-w-xs">
                      {session.granted_scopes.slice(0, 3).map((scope) => (
                        <span
                          key={scope}
                          className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full"
                        >
                          {scope}
                        </span>
                      ))}
                      {session.granted_scopes.length > 3 && (
                        <span className="px-2 py-1 bg-gray-50 text-gray-700 text-xs rounded-full">
                          +{session.granted_scopes.length - 3}
                        </span>
                      )}
                    </div>
                  </td>
                  
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <div>
                        <p className="text-sm text-gray-900">{getTimeSince(session.last_used_at)}</p>
                        <p className="text-xs text-gray-500">{formatDate(session.last_used_at)}</p>
                      </div>
                    </div>
                  </td>
                  
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-600">{formatDate(session.created_at)}</span>
                    </div>
                  </td>
                  
                  <td className="px-6 py-4">
                    <div className="flex justify-end">
                      <button
                        onClick={() => {
                          setSelectedSession(session);
                          setShowRevokeModal(true);
                        }}
                        className="flex items-center space-x-1 px-3 py-1 text-xs bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>해지</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {filteredSessions.length === 0 && (
          <div className="text-center py-12">
            <Globe className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">
              {sessions.length === 0 ? '활성 OAuth 세션이 없습니다' : '검색 결과가 없습니다'}
            </p>
          </div>
        )}
      </div>

      {/* Revoke Modal */}
      {showRevokeModal && selectedSession && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-gray-900">세션 해지</h3>
              <button
                onClick={() => setShowRevokeModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start space-x-2">
                  <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
                  <div className="text-sm text-red-800">
                    <p className="font-medium">세션 해지 확인</p>
                    <p>
                      이 작업은 되돌릴 수 없으며, 사용자는 다시 로그인해야 합니다.
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <p><span className="font-medium">사용자:</span> {selectedSession.user_name}</p>
                <p><span className="font-medium">이메일:</span> {selectedSession.user_email}</p>
                <p><span className="font-medium">클라이언트:</span> {selectedSession.client_name}</p>
                <p><span className="font-medium">마지막 사용:</span> {getTimeSince(selectedSession.last_used_at)}</p>
              </div>
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowRevokeModal(false)}
                className="px-4 py-2 text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
              <button
                onClick={() => handleRevokeSession(selectedSession.id)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                해지하기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OAuthSessionManager;