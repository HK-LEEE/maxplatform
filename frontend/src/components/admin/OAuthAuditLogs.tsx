import React, { useState, useEffect } from 'react';
import {
  FileText, Search, RefreshCw, Filter, CheckCircle, XCircle,
  AlertTriangle, Calendar, User, Globe, Eye, Download
} from 'lucide-react';

interface OAuthAuditLog {
  id: string;
  action: string;
  client_id?: string;
  client_name?: string;
  user_id?: string;
  user_email?: string;
  ip_address?: string;
  user_agent?: string;
  success: boolean;
  error_code?: string;
  error_description?: string;
  created_at: string;
}

const OAuthAuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<OAuthAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAction, setFilterAction] = useState<string>('');
  const [filterSuccess, setFilterSuccess] = useState<string>('');
  const [selectedLog, setSelectedLog] = useState<OAuthAuditLog | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  const actionTypes = ['authorize', 'token', 'revoke', 'introspect'];

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        limit: '100'
      });

      if (filterAction) params.append('action', filterAction);
      if (filterSuccess !== '') params.append('success', filterSuccess);

      const response = await fetch(`/api/admin/oauth/audit-logs?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (error) {
      console.error('Failed to fetch OAuth audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getActionLabel = (action: string) => {
    const labels: { [key: string]: string } = {
      'authorize': '인증 요청',
      'token': '토큰 발급',
      'revoke': '토큰 해지',
      'introspect': '토큰 검증'
    };
    return labels[action] || action;
  };

  const getActionColor = (action: string) => {
    const colors: { [key: string]: string } = {
      'authorize': 'bg-blue-50 text-blue-700',
      'token': 'bg-green-50 text-green-700',
      'revoke': 'bg-red-50 text-red-700',
      'introspect': 'bg-yellow-50 text-yellow-700'
    };
    return colors[action] || 'bg-gray-50 text-gray-700';
  };

  const filteredLogs = logs.filter(log => {
    const matchesSearch = 
      (log.client_name?.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (log.user_email?.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (log.ip_address?.includes(searchQuery)) ||
      (log.error_code?.toLowerCase().includes(searchQuery.toLowerCase()));
    
    return matchesSearch;
  });

  const successCount = logs.filter(log => log.success).length;
  const failureCount = logs.filter(log => !log.success).length;

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
            <h2 className="text-xl font-semibold text-gray-900">OAuth 감사 로그</h2>
            <p className="text-sm text-gray-600 mt-1">
              OAuth 2.0 인증 활동을 모니터링하고 분석합니다
            </p>
          </div>
          
          <div className="flex space-x-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="클라이언트, 사용자, IP 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
              />
            </div>
            
            <select
              value={filterAction}
              onChange={(e) => setFilterAction(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-200"
            >
              <option value="">모든 액션</option>
              {actionTypes.map(action => (
                <option key={action} value={action}>{getActionLabel(action)}</option>
              ))}
            </select>
            
            <select
              value={filterSuccess}
              onChange={(e) => setFilterSuccess(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-200"
            >
              <option value="">모든 상태</option>
              <option value="true">성공</option>
              <option value="false">실패</option>
            </select>
            
            <button
              onClick={fetchLogs}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              <span>새로고침</span>
            </button>
          </div>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-blue-50 rounded-xl">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">총 로그</p>
              <p className="text-2xl font-bold text-gray-900">{logs.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-green-50 rounded-xl">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">성공</p>
              <p className="text-2xl font-bold text-gray-900">{successCount}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-red-50 rounded-xl">
              <XCircle className="w-6 h-6 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">실패</p>
              <p className="text-2xl font-bold text-gray-900">{failureCount}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-yellow-50 rounded-xl">
              <AlertTriangle className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">실패율</p>
              <p className="text-2xl font-bold text-gray-900">
                {logs.length > 0 ? Math.round((failureCount / logs.length) * 100) : 0}%
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">시간</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">액션</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">상태</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">사용자</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">클라이언트</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-600">IP 주소</th>
                <th className="text-right px-6 py-4 text-sm font-medium text-gray-600">상세</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-900">{formatDate(log.created_at)}</span>
                    </div>
                  </td>
                  
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getActionColor(log.action)}`}>
                      {getActionLabel(log.action)}
                    </span>
                  </td>
                  
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      {log.success ? (
                        <>
                          <CheckCircle className="w-4 h-4 text-green-600" />
                          <span className="text-sm text-green-700 font-medium">성공</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="w-4 h-4 text-red-600" />
                          <span className="text-sm text-red-700 font-medium">실패</span>
                        </>
                      )}
                    </div>
                    {!log.success && log.error_code && (
                      <p className="text-xs text-red-600 mt-1">{log.error_code}</p>
                    )}
                  </td>
                  
                  <td className="px-6 py-4">
                    {log.user_email ? (
                      <div className="flex items-center space-x-2">
                        <User className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-900">{log.user_email}</span>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </td>
                  
                  <td className="px-6 py-4">
                    {log.client_name ? (
                      <div className="flex items-center space-x-2">
                        <Globe className="w-4 h-4 text-gray-400" />
                        <div>
                          <p className="text-sm text-gray-900">{log.client_name}</p>
                          <p className="text-xs text-gray-500">{log.client_id}</p>
                        </div>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </td>
                  
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600 font-mono">
                      {log.ip_address || '-'}
                    </span>
                  </td>
                  
                  <td className="px-6 py-4">
                    <div className="flex justify-end">
                      <button
                        onClick={() => {
                          setSelectedLog(log);
                          setShowDetailModal(true);
                        }}
                        className="flex items-center space-x-1 px-3 py-1 text-xs bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        <Eye className="w-3 h-3" />
                        <span>상세</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {filteredLogs.length === 0 && (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">
              {logs.length === 0 ? '감사 로그가 없습니다' : '검색 결과가 없습니다'}
            </p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {showDetailModal && selectedLog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-gray-900">로그 상세 정보</h3>
              <button
                onClick={() => setShowDetailModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>

            <div className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">액션</label>
                  <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${getActionColor(selectedLog.action)}`}>
                    {getActionLabel(selectedLog.action)}
                  </span>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">상태</label>
                  <div className="flex items-center space-x-2">
                    {selectedLog.success ? (
                      <>
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span className="text-sm text-green-700 font-medium">성공</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-4 h-4 text-red-600" />
                        <span className="text-sm text-red-700 font-medium">실패</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Timestamp */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">시간</label>
                <p className="text-sm text-gray-900">{formatDate(selectedLog.created_at)}</p>
              </div>

              {/* User Info */}
              {selectedLog.user_email && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">사용자</label>
                  <p className="text-sm text-gray-900">{selectedLog.user_email}</p>
                  {selectedLog.user_id && (
                    <p className="text-xs text-gray-500">ID: {selectedLog.user_id}</p>
                  )}
                </div>
              )}

              {/* Client Info */}
              {selectedLog.client_name && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">클라이언트</label>
                  <p className="text-sm text-gray-900">{selectedLog.client_name}</p>
                  <p className="text-xs text-gray-500">ID: {selectedLog.client_id}</p>
                </div>
              )}

              {/* Network Info */}
              <div className="grid grid-cols-1 gap-4">
                {selectedLog.ip_address && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">IP 주소</label>
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded text-gray-700">
                      {selectedLog.ip_address}
                    </code>
                  </div>
                )}
                
                {selectedLog.user_agent && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">User Agent</label>
                    <code className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-700 block">
                      {selectedLog.user_agent}
                    </code>
                  </div>
                )}
              </div>

              {/* Error Info */}
              {!selectedLog.success && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <h4 className="font-medium text-red-900 mb-2">오류 정보</h4>
                  {selectedLog.error_code && (
                    <p className="text-sm text-red-800">
                      <span className="font-medium">코드:</span> {selectedLog.error_code}
                    </p>
                  )}
                  {selectedLog.error_description && (
                    <p className="text-sm text-red-800">
                      <span className="font-medium">설명:</span> {selectedLog.error_description}
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={() => setShowDetailModal(false)}
                className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OAuthAuditLogs;