import React, { useState, useEffect } from 'react';
import {
  Users, Settings, Check, X, Plus, Minus, Grid, 
  AlertCircle, RefreshCw, Save, Filter, Search
} from 'lucide-react';
import AdminLayout from './AdminLayout';
import AdminSectionHeader from './AdminSectionHeader';

interface User {
  id: string;
  real_name: string;
  email: string;
  group_id?: string;
  group_name?: string;
}

interface Group {
  id: string;
  name: string;
  description?: string;
  users_count: number;
}

interface LLMModel {
  id: string;
  model_name: string;
  model_type: string;
  owner_type: string;
  owner_id: string;
  is_active: boolean;
}

interface Permission {
  id: string;
  model_id: string;
  grantee_type: 'USER' | 'GROUP';
  grantee_id: string;
  grantee_name: string;
}

interface PermissionChange {
  model_id: string;
  grantee_type: 'USER' | 'GROUP';
  grantee_id: string;
  action: 'grant' | 'revoke';
}

const PermissionMatrix: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [changes, setChanges] = useState<PermissionChange[]>([]);
  const [viewMode, setViewMode] = useState<'users' | 'groups'>('groups');
  const [searchQuery, setSearchQuery] = useState('');
  const [modelFilter, setModelFilter] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      const [usersRes, groupsRes, modelsRes, permissionsRes] = await Promise.all([
        fetch('/api/admin/users', {
          headers: { Authorization: `Bearer ${token}` }
        }),
        fetch('/api/admin/groups', {
          headers: { Authorization: `Bearer ${token}` }
        }),
        fetch('/api/llm-models?accessible_only=false', {
          headers: { Authorization: `Bearer ${token}` }
        }),
        fetch('/api/admin/permissions/matrix', {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      if (usersRes.ok) setUsers(await usersRes.json());
      if (groupsRes.ok) setGroups(await groupsRes.json());
      if (modelsRes.ok) setModels(await modelsRes.json());
      if (permissionsRes.ok) setPermissions(await permissionsRes.json());
      
    } catch (error) {
      console.error('데이터 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const hasPermission = (modelId: string, granteeType: 'USER' | 'GROUP', granteeId: string): boolean => {
    // 기존 권한 확인
    const existingPermission = permissions.some(p => 
      p.model_id === modelId && 
      p.grantee_type === granteeType && 
      p.grantee_id === granteeId
    );

    // 변경사항 적용
    const change = changes.find(c => 
      c.model_id === modelId && 
      c.grantee_type === granteeType && 
      c.grantee_id === granteeId
    );

    if (change) {
      return change.action === 'grant';
    }

    return existingPermission;
  };

  const togglePermission = (modelId: string, granteeType: 'USER' | 'GROUP', granteeId: string) => {
    const currentHasPermission = hasPermission(modelId, granteeType, granteeId);
    const newAction = currentHasPermission ? 'revoke' : 'grant';

    setChanges(prev => {
      // 기존 변경사항 제거
      const filtered = prev.filter(c => 
        !(c.model_id === modelId && c.grantee_type === granteeType && c.grantee_id === granteeId)
      );

      // 원래 상태와 다른 경우에만 변경사항 추가
      const originalPermission = permissions.some(p => 
        p.model_id === modelId && 
        p.grantee_type === granteeType && 
        p.grantee_id === granteeId
      );

      if ((originalPermission && newAction === 'revoke') || (!originalPermission && newAction === 'grant')) {
        return [...filtered, { model_id: modelId, grantee_type: granteeType, grantee_id: granteeId, action: newAction }];
      }

      return filtered;
    });
  };

  const saveChanges = async () => {
    if (changes.length === 0) return;

    try {
      setSaving(true);
      const token = localStorage.getItem('token');

      for (const change of changes) {
        if (change.action === 'grant') {
          await fetch(`/api/llm-models/${change.model_id}/permissions`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              model_id: change.model_id,
              grantee_type: change.grantee_type,
              grantee_id: change.grantee_id
            })
          });
        } else {
          // 권한 취소 - 권한 ID를 찾아서 삭제
          const permission = permissions.find(p => 
            p.model_id === change.model_id && 
            p.grantee_type === change.grantee_type && 
            p.grantee_id === change.grantee_id
          );
          
          if (permission) {
            await fetch(`/api/llm-models/${change.model_id}/permissions/${permission.id}`, {
              method: 'DELETE',
              headers: { Authorization: `Bearer ${token}` }
            });
          }
        }
      }

      setChanges([]);
      await loadData();
      alert('권한 변경사항이 저장되었습니다.');
      
    } catch (error) {
      console.error('권한 저장 실패:', error);
      alert('권한 저장 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const filteredModels = models.filter(model =>
    model.model_name.toLowerCase().includes(modelFilter.toLowerCase())
  );

  const filteredGrantees = viewMode === 'groups' 
    ? groups.filter(group => group.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : users.filter(user => 
        user.real_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.email.toLowerCase().includes(searchQuery.toLowerCase())
      );

  if (loading) {
    return (
      <AdminLayout maxWidth="wide">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout maxWidth="wide">
      <AdminSectionHeader
        title="권한 매트릭스"
        description="그룹 및 사용자별 LLM 모델 권한을 한눈에 보고 관리합니다"
        icon={Grid}
        searchable={true}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder={viewMode === 'groups' ? '그룹 검색...' : '사용자 검색...'}
        actions={
          <div className="flex space-x-3">
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('groups')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'groups' 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                그룹별
              </button>
              <button
                onClick={() => setViewMode('users')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'users' 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                사용자별
              </button>
            </div>
            
            <input
              type="text"
              placeholder="모델 필터..."
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            {changes.length > 0 && (
              <button
                onClick={saveChanges}
                disabled={saving}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                <span>{saving ? '저장 중...' : `변경사항 저장 (${changes.length})`}</span>
              </button>
            )}

            <button
              onClick={loadData}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              <span>새로고침</span>
            </button>
          </div>
        }
      />

      {/* 통계 정보 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-blue-50 rounded-xl">
              <Users className="w-6 h-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">전체 사용자</p>
              <p className="text-2xl font-bold text-gray-900">{users.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-green-50 rounded-xl">
              <Users className="w-6 h-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">전체 그룹</p>
              <p className="text-2xl font-bold text-gray-900">{groups.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-purple-50 rounded-xl">
              <Settings className="w-6 h-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">활성 모델</p>
              <p className="text-2xl font-bold text-gray-900">{models.filter(m => m.is_active).length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-orange-50 rounded-xl">
              <Grid className="w-6 h-6 text-orange-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">총 권한</p>
              <p className="text-2xl font-bold text-gray-900">{permissions.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* 권한 매트릭스 */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="sticky left-0 bg-gray-50 px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-200">
                  {viewMode === 'groups' ? '그룹' : '사용자'}
                </th>
                {filteredModels.map(model => (
                  <th key={model.id} className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-200">
                    <div className="max-w-24 mx-auto">
                      <div className="truncate" title={model.model_name}>{model.model_name}</div>
                      <div className="text-gray-400 text-[10px] mt-1">{model.model_type}</div>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredGrantees.map((grantee) => (
                <tr key={grantee.id} className="hover:bg-gray-50">
                  <td className="sticky left-0 bg-white px-6 py-4 whitespace-nowrap border-r border-gray-200">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                          <Users className="h-5 w-5 text-gray-500" />
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">{grantee.name || grantee.real_name}</div>
                        {viewMode === 'users' && (
                          <div className="text-sm text-gray-500">{grantee.email}</div>
                        )}
                        {viewMode === 'groups' && (
                          <div className="text-sm text-gray-500">{grantee.users_count}명</div>
                        )}
                      </div>
                    </div>
                  </td>
                  {filteredModels.map(model => {
                    const hasPerms = hasPermission(model.id, viewMode === 'groups' ? 'GROUP' : 'USER', grantee.id);
                    const hasChange = changes.some(c => 
                      c.model_id === model.id && 
                      c.grantee_type === (viewMode === 'groups' ? 'GROUP' : 'USER') && 
                      c.grantee_id === grantee.id
                    );
                    
                    return (
                      <td key={model.id} className="px-3 py-4 text-center border-r border-gray-200">
                        <button
                          onClick={() => togglePermission(model.id, viewMode === 'groups' ? 'GROUP' : 'USER', grantee.id)}
                          className={`w-8 h-8 rounded-full transition-colors ${
                            hasPerms 
                              ? 'bg-green-100 text-green-600 hover:bg-green-200' 
                              : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                          } ${
                            hasChange ? 'ring-2 ring-blue-500' : ''
                          }`}
                        >
                          {hasPerms ? <Check className="w-4 h-4 mx-auto" /> : <X className="w-4 h-4 mx-auto" />}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {filteredGrantees.length === 0 && (
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">검색 결과가 없습니다.</p>
        </div>
      )}
    </AdminLayout>
  );
};

export default PermissionMatrix;