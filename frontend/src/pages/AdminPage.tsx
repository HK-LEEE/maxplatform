import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Users, Settings, Shield, Database, UserPlus, UserCheck, UserX, 
  Edit3, Trash2, Download, Upload, Search, RefreshCw, Plus,
  ChevronRight, AlertCircle, CheckCircle, XCircle, Clock,
  Eye, EyeOff, Key, Filter, Grid, List, MoreVertical,
  ArrowRight, ArrowLeft, User, Phone, Building, Briefcase,
  Calendar, Activity, Mail, MapPin, Brain, Server
} from 'lucide-react';
import FeatureLogo from '../components/common/FeatureLogo';
import { llmChatApi } from '../services/llmChatApi';
import { LLMModelManagement, LLMModelCreate, ModelType, OwnerType } from '../types/llmChat';

interface User {
  id: string;
  real_name: string;
  display_name?: string;
  email: string;
  phone_number?: string;
  department?: string;
  position?: string;
  bio?: string;
  is_active: boolean;
  is_admin: boolean;
  approval_status: string;
  approval_note?: string;
  approved_by?: string;
  approved_at?: string;
  created_at: string;
  last_login_at?: string;
  login_count: number;
  role?: any;
  group?: {
    id: number;
    name: string;
    description?: string;
  };
  permissions?: any[];
  features?: any[];
}

interface GroupUser {
  id: string;
  real_name: string;
  display_name?: string;
  email: string;
  phone_number?: string;
  department?: string;
  position?: string;
  is_active: boolean;
  is_admin: boolean;
  is_verified: boolean;
  approval_status: string;
  created_at: string;
  last_login_at?: string;
  login_count: number;
  role_name?: string;
}

interface Group {
  id: number;
  name: string;
  description: string;
  users_count?: number;
  features?: Feature[];
  permissions?: any[];
  users?: GroupUser[];
  created_by?: string;
  created_at?: string;
}

interface Feature {
  id: number;
  name: string;
  display_name: string;
  description: string;
  category: string;
  category_id?: number;
  icon: string;
  url_path: string;
  is_active: boolean;
  requires_approval: boolean;
  is_external?: boolean;
  open_in_new_tab?: boolean;
  category_name?: string;
  category_display_name?: string;
}

interface FeatureCategory {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  icon?: string;
  color?: string;
  sort_order: number;
  is_active: boolean;
}

const AdminPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'dashboard' | 'users' | 'features' | 'groups' | 'models'>('dashboard');
  const [users, setUsers] = useState<User[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [featureCategories, setFeatureCategories] = useState<FeatureCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive' | 'pending'>('all');
  const [showUserModal, setShowUserModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [isEditingUserInfo, setIsEditingUserInfo] = useState(false);
  const [passwordData, setPasswordData] = useState({
    user_id: '',
    new_password: ''
  });
  const [editedUserInfo, setEditedUserInfo] = useState({
    real_name: '',
    display_name: '',
    phone_number: '',
    department: '',
    position: '',
    bio: ''
  });
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [showFeatureModal, setShowFeatureModal] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState<Feature | null>(null);
  const [isEditingFeature, setIsEditingFeature] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [editedFeatureInfo, setEditedFeatureInfo] = useState({
    name: '',
    display_name: '',
    description: '',
    category_id: null as number | null,
    icon: '',
    url_path: '',
    is_active: true,
    requires_approval: false,
    is_external: false,
    open_in_new_tab: false
  });
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
  const [isEditingGroup, setIsEditingGroup] = useState(false);
  const [editedGroupInfo, setEditedGroupInfo] = useState({
    name: '',
    description: ''
  });
  const [selectedGroupFeatures, setSelectedGroupFeatures] = useState<number[]>([]);
  const [availableFeatures, setAvailableFeatures] = useState<Feature[]>([]);
  const [unassignedFeatures, setUnassignedFeatures] = useState<Feature[]>([]);
  const [assignedFeatures, setAssignedFeatures] = useState<Feature[]>([]);
  const [groupUsers, setGroupUsers] = useState<GroupUser[]>([]);
  
  // 새로운 사용자 추가를 위한 상태
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newUserInfo, setNewUserInfo] = useState({
    real_name: '',
    display_name: '',
    email: '',
    phone_number: '',
    department: '',
    position: '',
    bio: '',
    password: '',
    is_admin: false,
    group_id: null as number | null
  });

  // LLM 모델 관리를 위한 상태
  const [llmModels, setLlmModels] = useState<LLMModelManagement[]>([]);
  const [showModelModal, setShowModelModal] = useState(false);
  const [selectedModel, setSelectedModel] = useState<LLMModelManagement | null>(null);
  const [isEditingModel, setIsEditingModel] = useState(false);
  const [editedModelInfo, setEditedModelInfo] = useState({
    model_name: '',
    model_type: 'AZURE_OPENAI' as ModelType,
    model_id: '',
    description: '',
    config: {} as any,
    owner_type: 'USER' as OwnerType,
    owner_id: '',
    is_active: true
  });
  
  // Ollama 관련 상태
  const [ollamaModels, setOllamaModels] = useState<any[]>([]);
  const [ollamaLoading, setOllamaLoading] = useState(false);
  const [ollamaHost, setOllamaHost] = useState('localhost');
  const [ollamaPort, setOllamaPort] = useState(11434);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/');
      return;
    }
    
    fetchData();
  }, [navigate]);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const [usersRes, groupsRes, featuresRes, categoriesRes] = await Promise.all([
        fetch('/admin/users', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/admin/groups', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/admin/features', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/admin/feature-categories', { headers: { Authorization: `Bearer ${token}` } })
      ]);

      if (usersRes.ok) {
        const usersData = await usersRes.json();
        setUsers(usersData);
      }

      if (groupsRes.ok) {
        const groupsData = await groupsRes.json();
        setGroups(groupsData);
      }

      if (featuresRes.ok) {
        const featuresData = await featuresRes.json();
        setFeatures(featuresData);
        setAvailableFeatures(featuresData);
      }

      if (categoriesRes.ok) {
        const categoriesData = await categoriesRes.json();
        setFeatureCategories(categoriesData);
      }

      // LLM 모델 가져오기
      try {
        const modelsData = await llmChatApi.getLLMModels();
        setLlmModels(modelsData);
      } catch (error) {
        console.error('LLM 모델 로드 실패:', error);
      }
    } catch (error) {
      console.error('데이터 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('ko-KR');
  };

  const deleteUser = async (userId: string) => {
    if (!confirm('정말로 이 사용자를 삭제하시겠습니까?')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        await fetchData();
        alert('사용자가 삭제되었습니다.');
      } else {
        const error = await response.json();
        alert(`사용자 삭제 실패: ${error.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('사용자 삭제 실패:', error);
      alert('사용자 삭제 중 오류가 발생했습니다.');
    }
  };

  const openUserModal = async (user: User) => {
    setSelectedUser(user);
    setEditedUserInfo({
      real_name: user.real_name,
      display_name: user.display_name || '',
      phone_number: user.phone_number || '',
      department: user.department || '',
      position: user.position || '',
      bio: user.bio || ''
    });
    setSelectedGroupId(user.group?.id || null);
    // 바로 편집 모드로 시작
    setIsEditingUserInfo(true);
    setShowUserModal(true);
  };

  const saveUserInfo = async () => {
    if (!selectedUser) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/admin/users/${selectedUser.id}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...editedUserInfo,
          group_id: selectedGroupId
        })
      });

      if (response.ok) {
        await fetchData();
        setShowUserModal(false);
        setIsEditingUserInfo(false);
        alert('사용자 정보가 업데이트되었습니다.');
      } else {
        const error = await response.json();
        alert(`업데이트 실패: ${error.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('사용자 정보 업데이트 실패:', error);
      alert('사용자 정보 업데이트 중 오류가 발생했습니다.');
    }
  };

  const updateUserStatus = async (userId: string, status: string, isActive: boolean) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/admin/users/${userId}/status`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          approval_status: status,
          is_active: isActive
        })
      });

      if (response.ok) {
        await fetchData();
        alert('사용자 상태가 업데이트되었습니다.');
      } else {
        const error = await response.json();
        alert(`상태 업데이트 실패: ${error.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('사용자 상태 업데이트 실패:', error);
      alert('사용자 상태 업데이트 중 오류가 발생했습니다.');
    }
  };

  const openAddUserModal = () => {
    setNewUserInfo({
      real_name: '',
      display_name: '',
      email: '',
      phone_number: '',
      department: '',
      position: '',
      bio: '',
      password: '',
      is_admin: false,
      group_id: null
    });
    setShowAddUserModal(true);
  };

  const createUser = async () => {
    if (!newUserInfo.real_name || !newUserInfo.email || !newUserInfo.password) {
      alert('필수 항목을 모두 입력해주세요.');
      return;
    }

    if (newUserInfo.password.length < 6) {
      alert('비밀번호는 최소 6자 이상이어야 합니다.');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      
      // 먼저 사용자 생성
      const registerResponse = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          real_name: newUserInfo.real_name,
          display_name: newUserInfo.display_name,
          email: newUserInfo.email,
          phone_number: newUserInfo.phone_number,
          department: newUserInfo.department,
          position: newUserInfo.position,
          bio: newUserInfo.bio,
          password: newUserInfo.password,
          is_admin: newUserInfo.is_admin
        })
      });

      if (registerResponse.ok) {
        const userData = await registerResponse.json();
        
        // 그룹이 선택되었다면 그룹 할당
        if (newUserInfo.group_id) {
          const groupResponse = await fetch('/admin/users/group', {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              user_id: userData.user.id,
              group_id: newUserInfo.group_id
            })
          });

          if (!groupResponse.ok) {
            const groupError = await groupResponse.json();
            console.error('그룹 할당 실패:', groupError);
          }
        }

        await fetchData();
        setShowAddUserModal(false);
        alert('새 사용자가 생성되었습니다.');
      } else {
        const error = await registerResponse.json();
        alert(`사용자 생성 실패: ${error.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('사용자 생성 실패:', error);
      alert('사용자 생성 중 오류가 발생했습니다.');
    }
  };

  const openFeatureModal = (feature: Feature | null = null) => {
    if (feature) {
      setSelectedFeature(feature);
      setEditedFeatureInfo({
        name: feature.name,
        display_name: feature.display_name,
        description: feature.description || '',
        category_id: feature.category_id || null,
        icon: feature.icon || '',
        url_path: feature.url_path || '',
        is_active: feature.is_active,
        requires_approval: feature.requires_approval,
        is_external: feature.is_external || false,
        open_in_new_tab: feature.open_in_new_tab || false
      });
      setIsEditingFeature(true);
    } else {
      setSelectedFeature(null);
      setEditedFeatureInfo({
        name: '',
        display_name: '',
        description: '',
        category_id: null,
        icon: '',
        url_path: '',
        is_active: true,
        requires_approval: false,
        is_external: false,
        open_in_new_tab: false
      });
      setIsEditingFeature(false);
    }
    setShowPreview(false);
    setShowFeatureModal(true);
  };

  const saveFeature = async () => {
    if (!editedFeatureInfo.name || !editedFeatureInfo.display_name) {
      alert('기능명과 표시명은 필수 항목입니다.');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const url = selectedFeature ? `/admin/features/${selectedFeature.id}` : '/admin/features';
      const method = selectedFeature ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editedFeatureInfo)
      });

      if (response.ok) {
        await fetchData();
        setShowFeatureModal(false);
        alert(selectedFeature ? '기능이 업데이트되었습니다.' : '새 기능이 생성되었습니다.');
      } else {
        const error = await response.json();
        alert(`기능 저장 실패: ${error.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('기능 저장 실패:', error);
      alert('기능 저장 중 오류가 발생했습니다.');
    }
  };

  const deleteFeature = async (featureId: number) => {
    if (!confirm('정말로 이 기능을 삭제하시겠습니까?')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/admin/features/${featureId}`, {
        method: 'DELETE',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        await fetchData();
        alert('기능이 삭제되었습니다.');
      } else {
        const error = await response.json();
        alert(`기능 삭제 실패: ${error.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('기능 삭제 실패:', error);
      alert('기능 삭제 중 오류가 발생했습니다.');
    }
  };

  const exportUsersToCSV = () => {
    const headers = ['ID', '실명', '표시명', '이메일', '전화번호', '부서', '직급', 
                     '활성화 상태', '관리자 여부', '승인 상태', '가입일', '마지막 로그인', '로그인 횟수'];
    
    const csvData = users.map(user => [
      user.id,
      user.real_name,
      user.display_name || '',
      user.email,
      user.phone_number || '',
      user.department || '',
      user.position || '',
      user.is_active ? '활성' : '비활성',
      user.is_admin ? '관리자' : '일반',
      user.approval_status === 'approved' ? '승인됨' : 
      user.approval_status === 'rejected' ? '거부됨' : '대기중',
      formatDate(user.created_at),
      formatDate(user.last_login_at),
      user.login_count
    ]);

    const csvContent = [headers, ...csvData]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n');

    // UTF-8 BOM 추가로 한글 깨짐 방지
    const BOM = '\uFEFF';
    const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `users_${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const resetPassword = async () => {
    if (!passwordData.user_id || !passwordData.new_password) {
      alert('모든 필드를 입력해주세요.');
      return;
    }

    if (passwordData.new_password.length < 6) {
      alert('비밀번호는 최소 6자 이상이어야 합니다.');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/admin/users/change-password', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: passwordData.user_id,
          new_password: passwordData.new_password
        })
      });

      if (response.ok) {
        alert('비밀번호가 성공적으로 변경되었습니다.');
        setShowPasswordModal(false);
        setPasswordData({ user_id: '', new_password: '' });
      } else {
        const error = await response.json();
        alert(`비밀번호 변경 실패: ${error.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('비밀번호 변경 실패:', error);
      alert('비밀번호 변경 중 오류가 발생했습니다.');
    }
  };

  const openGroupModal = async (group: Group | null = null) => {
    if (group) {
      setSelectedGroup(group);
      setEditedGroupInfo({
        name: group.name,
        description: group.description || ''
      });
      setIsEditingGroup(true);
      
      // 그룹의 기능들을 assigned와 unassigned로 분리
      const groupFeatureIds = group.features?.map(f => f.id) || [];
      setAssignedFeatures(group.features || []);
      setUnassignedFeatures(availableFeatures.filter(f => !groupFeatureIds.includes(f.id)));
      setSelectedGroupFeatures(groupFeatureIds);
      
      // 그룹 사용자 정보 로드
      setGroupUsers(group.users || []);
    } else {
      setSelectedGroup(null);
      setEditedGroupInfo({
        name: '',
        description: ''
      });
      setIsEditingGroup(false);
      setAssignedFeatures([]);
      setUnassignedFeatures(availableFeatures);
      setSelectedGroupFeatures([]);
      setGroupUsers([]);
    }
    setShowGroupModal(true);
  };

  const saveGroup = async () => {
    if (!editedGroupInfo.name) {
      alert('그룹명은 필수 항목입니다.');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const url = selectedGroup ? `/admin/groups/${selectedGroup.id}` : '/admin/groups';
      const method = selectedGroup ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editedGroupInfo)
      });

      if (response.ok) {
        const groupData = await response.json();
        
        // 기능 할당 업데이트
        if (selectedGroupFeatures.length > 0) {
          await fetch('/admin/groups/features', {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              group_id: groupData.id,
              feature_ids: selectedGroupFeatures
            })
          });
        }

        await fetchData();
        setShowGroupModal(false);
        alert(selectedGroup ? '그룹이 업데이트되었습니다.' : '새 그룹이 생성되었습니다.');
      } else {
        const error = await response.json();
        alert(`그룹 저장 실패: ${error.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('그룹 저장 실패:', error);
      alert('그룹 저장 중 오류가 발생했습니다.');
    }
  };

  const deleteGroup = async (groupId: number) => {
    if (!confirm('정말로 이 그룹을 삭제하시겠습니까?')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/admin/groups/${groupId}`, {
        method: 'DELETE',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        await fetchData();
        alert('그룹이 삭제되었습니다.');
      } else {
        const error = await response.json();
        alert(`그룹 삭제 실패: ${error.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('그룹 삭제 실패:', error);
      alert('그룹 삭제 중 오류가 발생했습니다.');
    }
  };

  // 기능을 오른쪽(할당됨)으로 이동
  const moveFeatureToAssigned = (featureId: number) => {
    const feature = unassignedFeatures.find(f => f.id === featureId);
    if (feature) {
      setUnassignedFeatures(prev => prev.filter(f => f.id !== featureId));
      setAssignedFeatures(prev => [...prev, feature]);
      setSelectedGroupFeatures(prev => [...prev, featureId]);
    }
  };

  // 기능을 왼쪽(할당안됨)으로 이동
  const moveFeatureToUnassigned = (featureId: number) => {
    const feature = assignedFeatures.find(f => f.id === featureId);
    if (feature) {
      setAssignedFeatures(prev => prev.filter(f => f.id !== featureId));
      setUnassignedFeatures(prev => [...prev, feature]);
      setSelectedGroupFeatures(prev => prev.filter(id => id !== featureId));
    }
  };

  // ==================== LLM 모델 관리 함수들 ====================

  const openModelModal = (model: LLMModelManagement | null = null) => {
    if (model) {
      setSelectedModel(model);
      setEditedModelInfo({
        model_name: model.model_name,
        model_type: model.model_type,
        model_id: model.model_id,
        description: model.description || '',
        config: model.config,
        owner_type: model.owner_type,
        owner_id: model.owner_id,
        is_active: model.is_active
      });
      setIsEditingModel(true);
    } else {
      setSelectedModel(null);
      const defaultConfig = getDefaultConfig('AZURE_OPENAI');
      setEditedModelInfo({
        model_name: '',
        model_type: 'AZURE_OPENAI',
        model_id: '',
        description: '',
        config: defaultConfig,
        owner_type: 'USER',
        owner_id: '',
        is_active: true
      });
      setIsEditingModel(false);
    }
    setShowModelModal(true);
  };

  const saveModel = async () => {
    try {
      if (isEditingModel && selectedModel) {
        await llmChatApi.updateLLMModel(selectedModel.id, editedModelInfo);
        alert('모델이 업데이트되었습니다.');
      } else {
        const createData: LLMModelCreate = {
          model_name: editedModelInfo.model_name,
          model_type: editedModelInfo.model_type,
          model_id: editedModelInfo.model_id,
          description: editedModelInfo.description,
          config: editedModelInfo.config,
          owner_type: editedModelInfo.owner_type,
          owner_id: editedModelInfo.owner_id || undefined
        };
        await llmChatApi.createLLMModel(createData);
        alert('모델이 생성되었습니다.');
      }
      
      await fetchData();
      setShowModelModal(false);
    } catch (error) {
      console.error('모델 저장 실패:', error);
      alert('모델 저장 중 오류가 발생했습니다.');
    }
  };

  const deleteModel = async (modelId: number) => {
    if (!confirm('정말로 이 모델을 삭제하시겠습니까?')) {
      return;
    }

    try {
      await llmChatApi.deleteLLMModel(modelId);
      await fetchData();
      alert('모델이 삭제되었습니다.');
    } catch (error) {
      console.error('모델 삭제 실패:', error);
      alert('모델 삭제 중 오류가 발생했습니다.');
    }
  };

  // Ollama 모델 목록 가져오기
  const fetchOllamaModels = async () => {
    setOllamaLoading(true);
    try {
      const response = await llmChatApi.getOllamaModels(ollamaHost, ollamaPort);
      if (response.success) {
        setOllamaModels(response.models);
      } else {
        alert('Ollama 모델 목록을 가져올 수 없습니다.');
      }
    } catch (error) {
      console.error('Ollama 모델 조회 실패:', error);
      alert('Ollama 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.');
    } finally {
      setOllamaLoading(false);
    }
  };

  // 모델 타입별 기본 설정 가져오기
  const getDefaultConfig = (modelType: ModelType) => {
    switch (modelType) {
      case 'AZURE_OPENAI':
        return {
          api_key: '',
          endpoint: '',
          api_version: '2024-02-01',
          deployment_name: '',
          temperature: 0.7,
          max_tokens: 1000
        };
      case 'AZURE_CLAUDE':
        return {
          api_key: '',
          endpoint: '',
          api_version: '2024-02-01',
          model_version: 'claude-3-sonnet-20240229',
          temperature: 0.7,
          max_tokens: 1000
        };
      case 'AZURE_DEEPSEEK':
        return {
          api_key: '',
          endpoint: '',
          api_version: '2024-02-01',
          deployment_name: '',
          temperature: 0.7,
          max_tokens: 1000
        };
      case 'OLLAMA':
        return {
          host: 'localhost',
          port: 11434,
          model_name: '',
          temperature: 0.7,
          num_predict: 1000
        };
      case 'FLOWSTUDIO':
        return {
          flow_id: '',
          endpoint: '',
          timeout: 30
        };
      default:
        return {};
    }
  };

  // 모델 타입 변경 시 기본 설정 적용
  const handleModelTypeChange = (newType: ModelType) => {
    const defaultConfig = getDefaultConfig(newType);
    setEditedModelInfo({
      ...editedModelInfo,
      model_type: newType,
      config: defaultConfig
    });
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.real_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         user.department?.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (!matchesSearch) return false;

    switch (filterStatus) {
      case 'active':
        return user.is_active && user.approval_status === 'approved';
      case 'inactive':
        return !user.is_active;
      case 'pending':
        return user.approval_status === 'pending';
      default:
        return true;
    }
  });

  const stats = {
    total: users.length,
    active: users.filter(u => u.is_active && u.approval_status === 'approved').length,
    pending: users.filter(u => u.approval_status === 'pending').length,
    inactive: users.filter(u => !u.is_active).length
  };

  const getStatusBadge = (user: User) => {
    if (user.approval_status === 'pending') {
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 border border-yellow-200">대기중</span>;
    } else if (!user.is_active) {
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800 border border-red-200">비활성</span>;
    } else {
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800 border border-green-200">활성</span>;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-2 border-gray-200 border-t-gray-900 mx-auto mb-4"></div>
          <p className="text-gray-600">관리자 페이지를 로딩하는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="bg-gradient-to-br from-gray-50 to-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div 
                onClick={() => navigate('/dashboard')}
                className="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center cursor-pointer hover:opacity-80 transition-opacity"
              >
                <span className="text-white font-bold text-lg">M</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 font-display">
                  시스템 관리
                </h1>
                <p className="text-gray-600 mt-1">
                  사용자, 기능, 그룹을 관리하고 시스템을 모니터링합니다
                </p>
              </div>
            </div>
            
            <button
              onClick={() => fetchData()}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors duration-200 shadow-sm hover:shadow-md"
            >
              <RefreshCw className="w-4 h-4" />
              <span>새로고침</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* 통계 카드 */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center">
                  <div className="p-3 bg-blue-50 rounded-xl">
                    <Users className="w-6 h-6 text-blue-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">전체 사용자</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center">
                  <div className="p-3 bg-green-50 rounded-xl">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">활성 사용자</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.active}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center">
                  <div className="p-3 bg-yellow-50 rounded-xl">
                    <Clock className="w-6 h-6 text-yellow-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">승인 대기</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.pending}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center">
                  <div className="p-3 bg-red-50 rounded-xl">
                    <XCircle className="w-6 h-6 text-red-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">비활성</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.inactive}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* 빠른 액션 */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">빠른 액션</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={() => setActiveTab('users')}
                  className="flex items-center p-4 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
                >
                  <Users className="w-5 h-5 text-gray-600 mr-3" />
                  <span className="text-gray-900 font-medium">사용자 관리</span>
                  <ChevronRight className="w-4 h-4 text-gray-400 ml-auto" />
                </button>

                <button
                  onClick={() => setActiveTab('features')}
                  className="flex items-center p-4 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
                >
                  <Settings className="w-5 h-5 text-gray-600 mr-3" />
                  <span className="text-gray-900 font-medium">기능 관리</span>
                  <ChevronRight className="w-4 h-4 text-gray-400 ml-auto" />
                </button>

                <button
                  onClick={() => setActiveTab('groups')}
                  className="flex items-center p-4 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
                >
                  <Shield className="w-5 h-5 text-gray-600 mr-3" />
                  <span className="text-gray-900 font-medium">그룹 관리</span>
                  <ChevronRight className="w-4 h-4 text-gray-400 ml-auto" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="bg-white rounded-2xl border border-gray-100 mb-6">
          <div className="flex space-x-1 p-2">
            {[
              { key: 'dashboard', label: '대시보드', icon: Database },
              { key: 'users', label: '사용자 관리', icon: Users },
              { key: 'features', label: '기능 관리', icon: Settings },
              { key: 'groups', label: '그룹 관리', icon: Shield },
              { key: 'models', label: 'LLM 모델', icon: Brain }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key as any)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition-all duration-200 ${
                  activeTab === key
                    ? 'bg-gray-900 text-white shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="font-medium">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="space-y-6">
            {/* 검색 및 필터 */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
                <div className="flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      placeholder="사용자 검색..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    />
                  </div>

                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value as any)}
                    className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-200"
                  >
                    <option value="all">전체 상태</option>
                    <option value="active">활성</option>
                    <option value="pending">승인 대기</option>
                    <option value="inactive">비활성</option>
                  </select>
                </div>

                <div className="flex space-x-2">
                  <button 
                    onClick={exportUsersToCSV}
                    className="flex items-center space-x-2 px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    <span>내보내기</span>
                  </button>
                  <button 
                    onClick={openAddUserModal}
                    className="flex items-center space-x-2 px-3 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span>사용자 추가</span>
                  </button>
                </div>
              </div>
            </div>

            {/* 사용자 목록 */}
            <div className="bg-white rounded-2xl border border-gray-100">
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr>
                      <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">사용자</th>
                      <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">연락처</th>
                      <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">부서/직책</th>
                      <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
                      <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">가입일</th>
                      <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">액션</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredUsers.map((user) => (
                      <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center">
                            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                              <span className="text-sm font-medium text-gray-600">
                                {user.real_name?.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <div className="ml-4">
                              <div className="flex items-center space-x-2">
                                <div className="text-sm font-medium text-gray-900">{user.real_name}</div>
                                {user.is_admin && (
                                  <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800">관리자</span>
                                )}
                              </div>
                              <div className="text-sm text-gray-500">{user.email}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {user.phone_number || '-'}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          <div>{user.department || '-'}</div>
                          <div className="text-gray-500">{user.position || '-'}</div>
                        </td>
                        <td className="px-6 py-4">
                          {getStatusBadge(user)}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {formatDate(user.created_at)}
                        </td>
                        <td className="px-6 py-4 text-sm font-medium">
                          <div className="flex items-center space-x-1">
                            <button
                              onClick={() => openUserModal(user)}
                              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                              title="편집"
                            >
                              <Edit3 className="w-4 h-4 text-gray-500" />
                            </button>
                            
                            <button
                              onClick={() => {
                                setPasswordData({user_id: user.id, new_password: ''});
                                setShowPasswordModal(true);
                              }}
                              className="p-1.5 hover:bg-blue-100 rounded-lg transition-colors"
                              title="비밀번호 재설정"
                            >
                              <Key className="w-4 h-4 text-blue-600" />
                            </button>
                            
                            {user.approval_status === 'pending' && (
                              <>
                                <button
                                  onClick={() => updateUserStatus(user.id, 'approved', true)}
                                  className="p-1.5 hover:bg-green-100 rounded-lg transition-colors"
                                  title="승인"
                                >
                                  <UserCheck className="w-4 h-4 text-green-600" />
                                </button>
                                <button
                                  onClick={() => updateUserStatus(user.id, 'rejected', false)}
                                  className="p-1.5 hover:bg-red-100 rounded-lg transition-colors"
                                  title="거부"
                                >
                                  <UserX className="w-4 h-4 text-red-600" />
                                </button>
                              </>
                            )}
                            
                            {user.is_active ? (
                              <button
                                onClick={() => updateUserStatus(user.id, user.approval_status, false)}
                                className="p-1.5 hover:bg-yellow-100 rounded-lg transition-colors"
                                title="비활성화"
                              >
                                <EyeOff className="w-4 h-4 text-yellow-600" />
                              </button>
                            ) : (
                              <button
                                onClick={() => updateUserStatus(user.id, 'approved', true)}
                                className="p-1.5 hover:bg-green-100 rounded-lg transition-colors"
                                title="활성화"
                              >
                                <Eye className="w-4 h-4 text-green-600" />
                              </button>
                            )}
                            
                            <button
                              onClick={() => deleteUser(user.id)}
                              className="p-1.5 hover:bg-red-100 rounded-lg transition-colors"
                              title="삭제"
                            >
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Features Tab */}
        {activeTab === 'features' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-900">기능 관리</h2>
              <button 
                onClick={() => openFeatureModal()}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>기능 추가</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {features.map((feature) => (
                <div key={feature.id} className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center">
                      <FeatureLogo 
                        displayName={feature.display_name} 
                        size="small"
                      />
                      <div className="ml-3">
                        <h3 className="text-sm font-medium text-gray-900">{feature.display_name}</h3>
                        <p className="text-xs text-gray-500">{feature.category_display_name || feature.category}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-1">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        feature.is_active 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {feature.is_active ? '활성' : '비활성'}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mb-4">{feature.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">{feature.url_path}</span>
                    <div className="flex space-x-1">
                      <button 
                        onClick={() => openFeatureModal(feature)}
                        className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                        title="편집"
                      >
                        <Edit3 className="w-3.5 h-3.5 text-gray-500" />
                      </button>
                      <button 
                        onClick={() => deleteFeature(feature.id)}
                        className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                        title="삭제"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-red-500" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Groups Tab */}
        {activeTab === 'groups' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-900">그룹 관리</h2>
              <button 
                onClick={() => openGroupModal()}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>그룹 추가</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {groups.map((group) => (
                <div key={group.id} className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">{group.name}</h3>
                      <p className="text-sm text-gray-500 mt-1">{group.description}</p>
                    </div>
                    <div className="flex space-x-1">
                      <button 
                        onClick={() => openGroupModal(group)}
                        className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                        title="편집"
                      >
                        <Edit3 className="w-4 h-4 text-gray-500" />
                      </button>
                      <button 
                        onClick={() => deleteGroup(group.id)}
                        className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                        title="삭제"
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">사용자 수</span>
                    <span className="font-medium text-gray-900">{group.users_count || 0}명</span>
                  </div>
                  
                  <div className="flex items-center justify-between text-sm mt-2">
                    <span className="text-gray-600">기능 수</span>
                    <span className="font-medium text-gray-900">{group.features?.length || 0}개</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 기존 모달들은 유지 */}
      {/* User Modal - Enhanced UI */}
      {showUserModal && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl mx-4 border border-gray-100 max-h-[90vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-gray-900 rounded-full flex items-center justify-center">
                    <User className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">{selectedUser.real_name}</h3>
                    <p className="text-sm text-gray-500">{selectedUser.email}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {selectedUser.is_admin && (
                    <span className="px-3 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">관리자</span>
                  )}
                  {getStatusBadge(selectedUser)}
                </div>
              </div>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* 기본 정보 */}
                <div className="space-y-6">
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                      <User className="w-5 h-5 mr-2" />
                      기본 정보
                    </h4>
                    <div className="space-y-4 bg-gray-50 p-4 rounded-xl">
                      <div className="grid grid-cols-1 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">실명</label>
                          <input
                            type="text"
                            value={editedUserInfo.real_name}
                            onChange={(e) => setEditedUserInfo({...editedUserInfo, real_name: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">표시명</label>
                          <input
                            type="text"
                            value={editedUserInfo.display_name}
                            onChange={(e) => setEditedUserInfo({...editedUserInfo, display_name: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                            placeholder="표시명을 입력하세요"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 연락처 정보 */}
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                      <Phone className="w-5 h-5 mr-2" />
                      연락처 정보
                    </h4>
                    <div className="space-y-4 bg-gray-50 p-4 rounded-xl">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center">
                          <Phone className="w-4 h-4 mr-1" />
                          전화번호
                        </label>
                        <input
                          type="text"
                          value={editedUserInfo.phone_number}
                          onChange={(e) => setEditedUserInfo({...editedUserInfo, phone_number: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                          placeholder="전화번호를 입력하세요"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center">
                          <Mail className="w-4 h-4 mr-1" />
                          이메일
                        </label>
                        <div className="px-3 py-2 bg-gray-100 border border-gray-200 rounded-lg text-gray-600">
                          {selectedUser.email}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 조직 정보 & 계정 상태 */}
                <div className="space-y-6">
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                      <Building className="w-5 h-5 mr-2" />
                      조직 정보
                    </h4>
                    <div className="space-y-4 bg-gray-50 p-4 rounded-xl">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">부서</label>
                        <input
                          type="text"
                          value={editedUserInfo.department}
                          onChange={(e) => setEditedUserInfo({...editedUserInfo, department: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                          placeholder="부서를 입력하세요"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">직책</label>
                        <input
                          type="text"
                          value={editedUserInfo.position}
                          onChange={(e) => setEditedUserInfo({...editedUserInfo, position: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                          placeholder="직책을 입력하세요"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">그룹</label>
                        <select
                          value={selectedGroupId || ''}
                          onChange={(e) => setSelectedGroupId(e.target.value ? parseInt(e.target.value) : null)}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                        >
                          <option value="">그룹 선택</option>
                          {groups.map(group => (
                            <option key={group.id} value={group.id}>{group.name}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* 계정 통계 */}
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                      <Activity className="w-5 h-5 mr-2" />
                      계정 통계
                    </h4>
                    <div className="space-y-3 bg-gray-50 p-4 rounded-xl">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 flex items-center">
                          <Calendar className="w-4 h-4 mr-2" />
                          가입일
                        </span>
                        <span className="text-sm font-medium">{formatDate(selectedUser.created_at)}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 flex items-center">
                          <Activity className="w-4 h-4 mr-2" />
                          마지막 로그인
                        </span>
                        <span className="text-sm font-medium">{formatDate(selectedUser.last_login_at) || '없음'}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">로그인 횟수</span>
                        <span className="text-sm font-medium">{selectedUser.login_count}회</span>
                      </div>
                    </div>
                  </div>

                  {/* 추가 정보 */}
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-4">추가 정보</h4>
                    <div className="bg-gray-50 p-4 rounded-xl">
                      <label className="block text-sm font-medium text-gray-700 mb-1">소개</label>
                      <textarea
                        value={editedUserInfo.bio}
                        onChange={(e) => setEditedUserInfo({...editedUserInfo, bio: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                        rows={3}
                        placeholder="사용자 소개를 입력하세요"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="p-6 border-t border-gray-200 bg-gray-50 flex justify-end space-x-3">
              <button
                onClick={() => setShowUserModal(false)}
                className="px-6 py-2 text-gray-700 border border-gray-200 rounded-xl hover:bg-gray-100 transition-colors"
              >
                취소
              </button>
              <button
                onClick={saveUserInfo}
                className="px-6 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
              >
                저장
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 border border-gray-100">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">새 사용자 추가</h3>
            </div>
            <div className="p-6 space-y-4 max-h-96 overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">실명 *</label>
                  <input
                    type="text"
                    value={newUserInfo.real_name}
                    onChange={(e) => setNewUserInfo({...newUserInfo, real_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="실명을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">표시명</label>
                  <input
                    type="text"
                    value={newUserInfo.display_name}
                    onChange={(e) => setNewUserInfo({...newUserInfo, display_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="표시명을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">이메일 *</label>
                  <input
                    type="email"
                    value={newUserInfo.email}
                    onChange={(e) => setNewUserInfo({...newUserInfo, email: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="이메일을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">비밀번호 *</label>
                  <input
                    type="password"
                    value={newUserInfo.password}
                    onChange={(e) => setNewUserInfo({...newUserInfo, password: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="비밀번호를 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">전화번호</label>
                  <input
                    type="text"
                    value={newUserInfo.phone_number}
                    onChange={(e) => setNewUserInfo({...newUserInfo, phone_number: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="전화번호를 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">부서</label>
                  <input
                    type="text"
                    value={newUserInfo.department}
                    onChange={(e) => setNewUserInfo({...newUserInfo, department: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="부서를 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">직책</label>
                  <input
                    type="text"
                    value={newUserInfo.position}
                    onChange={(e) => setNewUserInfo({...newUserInfo, position: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="직책을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">그룹</label>
                  <select
                    value={newUserInfo.group_id || ''}
                    onChange={(e) => setNewUserInfo({...newUserInfo, group_id: e.target.value ? parseInt(e.target.value) : null})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                  >
                    <option value="">그룹 선택</option>
                    {groups.map(group => (
                      <option key={group.id} value={group.id}>{group.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">소개</label>
                <textarea
                  value={newUserInfo.bio}
                  onChange={(e) => setNewUserInfo({...newUserInfo, bio: e.target.value})}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                  placeholder="사용자 소개를 입력하세요"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_admin"
                  checked={newUserInfo.is_admin}
                  onChange={(e) => setNewUserInfo({...newUserInfo, is_admin: e.target.checked})}
                  className="h-4 w-4 text-gray-600 focus:ring-gray-500 border-gray-300 rounded"
                />
                <label htmlFor="is_admin" className="ml-2 block text-sm text-gray-900">
                  관리자 권한 부여
                </label>
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={() => setShowAddUserModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
              <button
                onClick={createUser}
                className="px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
              >
                사용자 생성
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Password Reset Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 border border-gray-100">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">비밀번호 재설정</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">새 비밀번호</label>
                <input
                  type="password"
                  value={passwordData.new_password}
                  onChange={(e) => setPasswordData({...passwordData, new_password: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                  placeholder="새 비밀번호를 입력하세요"
                  autoFocus
                />
                <p className="text-xs text-gray-500 mt-1">최소 6자 이상 입력해주세요.</p>
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowPasswordModal(false);
                  setPasswordData({ user_id: '', new_password: '' });
                }}
                className="px-4 py-2 text-gray-700 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
              <button
                onClick={resetPassword}
                className="px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
              >
                비밀번호 재설정
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Feature Modal */}
      {showFeatureModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 border border-gray-100">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">
                {selectedFeature ? '기능 편집' : '새 기능 추가'}
              </h3>
            </div>
            <div className="p-6 space-y-4 max-h-96 overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">기능명 *</label>
                  <input
                    type="text"
                    value={editedFeatureInfo.name}
                    onChange={(e) => setEditedFeatureInfo({...editedFeatureInfo, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="기능명을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">표시명 *</label>
                  <input
                    type="text"
                    value={editedFeatureInfo.display_name}
                    onChange={(e) => setEditedFeatureInfo({...editedFeatureInfo, display_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="표시명을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">카테고리</label>
                  <select
                    value={editedFeatureInfo.category_id || ''}
                    onChange={(e) => setEditedFeatureInfo({...editedFeatureInfo, category_id: e.target.value ? parseInt(e.target.value) : null})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                  >
                    <option value="">카테고리 선택</option>
                    {featureCategories.map(category => (
                      <option key={category.id} value={category.id}>
                        {category.icon && `${category.icon} `}{category.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">아이콘 미리보기</label>
                  <div className="flex items-center space-x-3">
                    <div className="flex-1">
                      <input
                        type="text"
                        value={editedFeatureInfo.icon}
                        onChange={(e) => setEditedFeatureInfo({...editedFeatureInfo, icon: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                        placeholder="아이콘 (예: 🚀) - 자동 생성됩니다"
                        disabled
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        표시명에서 자동으로 약어가 생성됩니다 (예: "MAX FlowStudio" → "MF")
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-600">미리보기:</span>
                                             <FeatureLogo 
                         displayName={editedFeatureInfo.display_name || "기능명"}
                         size="small"
                       />
                    </div>
                  </div>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">URL 경로</label>
                  <input
                    type="text"
                    value={editedFeatureInfo.url_path}
                    onChange={(e) => setEditedFeatureInfo({...editedFeatureInfo, url_path: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="URL 경로를 입력하세요 (예: /dashboard)"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">설명</label>
                <textarea
                  value={editedFeatureInfo.description}
                  onChange={(e) => setEditedFeatureInfo({...editedFeatureInfo, description: e.target.value})}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                  placeholder="기능 설명을 입력하세요"
                />
              </div>
              <div className="space-y-3">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={editedFeatureInfo.is_active}
                    onChange={(e) => setEditedFeatureInfo({...editedFeatureInfo, is_active: e.target.checked})}
                    className="h-4 w-4 text-gray-600 focus:ring-gray-500 border-gray-300 rounded"
                  />
                  <label htmlFor="is_active" className="ml-2 block text-sm text-gray-900">
                    활성화
                  </label>
                </div>
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="requires_approval"
                    checked={editedFeatureInfo.requires_approval}
                    onChange={(e) => setEditedFeatureInfo({...editedFeatureInfo, requires_approval: e.target.checked})}
                    className="h-4 w-4 text-gray-600 focus:ring-gray-500 border-gray-300 rounded"
                  />
                  <label htmlFor="requires_approval" className="ml-2 block text-sm text-gray-900">
                    승인 필요
                  </label>
                </div>
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="is_external"
                    checked={editedFeatureInfo.is_external}
                    onChange={(e) => setEditedFeatureInfo({...editedFeatureInfo, is_external: e.target.checked})}
                    className="h-4 w-4 text-gray-600 focus:ring-gray-500 border-gray-300 rounded"
                  />
                  <label htmlFor="is_external" className="ml-2 block text-sm text-gray-900">
                    외부 링크
                  </label>
                </div>
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="open_in_new_tab"
                    checked={editedFeatureInfo.open_in_new_tab}
                    onChange={(e) => setEditedFeatureInfo({...editedFeatureInfo, open_in_new_tab: e.target.checked})}
                    className="h-4 w-4 text-gray-600 focus:ring-gray-500 border-gray-300 rounded"
                  />
                  <label htmlFor="open_in_new_tab" className="ml-2 block text-sm text-gray-900">
                    새 탭에서 열기
                  </label>
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={() => setShowFeatureModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
              <button
                onClick={saveFeature}
                className="px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
              >
                {selectedFeature ? '수정' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Group Modal */}
      {showGroupModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl mx-4 border border-gray-100">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">
                {selectedGroup ? '그룹 편집' : '새 그룹 추가'}
              </h3>
            </div>
            <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">그룹명 *</label>
                  <input
                    type="text"
                    value={editedGroupInfo.name}
                    onChange={(e) => setEditedGroupInfo({...editedGroupInfo, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="그룹명을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">설명</label>
                  <input
                    type="text"
                    value={editedGroupInfo.description}
                    onChange={(e) => setEditedGroupInfo({...editedGroupInfo, description: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="그룹 설명을 입력하세요"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">그룹 기능 관리</label>
                <div className="grid grid-cols-2 gap-4">
                  {/* 미할당 기능 리스트 */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                      <ArrowLeft className="w-4 h-4 mr-1" />
                      미할당 기능 ({unassignedFeatures.length}개)
                    </h4>
                    <div className="border border-gray-200 rounded-lg h-48 overflow-y-auto bg-gray-50">
                      {unassignedFeatures.length === 0 ? (
                        <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                          모든 기능이 할당되었습니다
                        </div>
                      ) : (
                        <div className="p-2 space-y-1">
                          {unassignedFeatures.map((feature) => (
                            <div
                              key={feature.id}
                              className="flex items-center justify-between p-2 bg-white rounded border border-gray-100 hover:border-gray-300 transition-colors cursor-pointer"
                              onClick={() => moveFeatureToAssigned(feature.id)}
                            >
                              <div className="flex items-center">
                                <FeatureLogo 
                                  displayName={feature.display_name} 
                                  size="small"
                                  className="mr-2"
                                />
                                <span className="text-sm">{feature.display_name}</span>
                              </div>
                              <ArrowRight className="w-4 h-4 text-gray-400" />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 할당된 기능 리스트 */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                      <ArrowRight className="w-4 h-4 mr-1" />
                      할당된 기능 ({assignedFeatures.length}개)
                    </h4>
                    <div className="border border-gray-200 rounded-lg h-48 overflow-y-auto bg-green-50">
                      {assignedFeatures.length === 0 ? (
                        <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                          할당된 기능이 없습니다
                        </div>
                      ) : (
                        <div className="p-2 space-y-1">
                          {assignedFeatures.map((feature) => (
                            <div
                              key={feature.id}
                              className="flex items-center justify-between p-2 bg-white rounded border border-green-200 hover:border-green-300 transition-colors cursor-pointer"
                              onClick={() => moveFeatureToUnassigned(feature.id)}
                            >
                              <div className="flex items-center">
                                <ArrowLeft className="w-4 h-4 text-gray-400" />
                                                                 <FeatureLogo 
                                   displayName={feature.display_name} 
                                   size="small"
                                   className="mr-2 ml-2"
                                 />
                                <span className="text-sm">{feature.display_name}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  좌측 기능을 클릭하여 할당하거나, 우측 기능을 클릭하여 해제할 수 있습니다.
                </p>
              </div>

              {/* 그룹 사용자 목록 */}
              {selectedGroup && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    그룹 소속 사용자 ({groupUsers.length}명)
                  </label>
                  <div className="border border-gray-200 rounded-lg max-h-48 overflow-y-auto">
                    {groupUsers.length === 0 ? (
                      <div className="p-4 text-center text-gray-500 text-sm">
                        이 그룹에 속한 사용자가 없습니다.
                      </div>
                    ) : (
                      <div className="divide-y divide-gray-100">
                        {groupUsers.map((user) => (
                          <div key={user.id} className="p-3 flex items-center justify-between hover:bg-gray-50">
                            <div className="flex items-center space-x-3">
                              <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                                <User className="w-4 h-4 text-gray-600" />
                              </div>
                              <div>
                                <p className="text-sm font-medium text-gray-900">{user.real_name}</p>
                                <p className="text-xs text-gray-500">{user.email}</p>
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              {user.department && (
                                <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                                  {user.department}
                                </span>
                              )}
                              {user.is_admin && (
                                <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                                  관리자
                                </span>
                              )}
                              <span className={`text-xs px-2 py-1 rounded ${
                                user.is_active && user.approval_status === 'approved'
                                  ? 'bg-green-100 text-green-800'
                                  : user.approval_status === 'pending'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {user.is_active && user.approval_status === 'approved' ? '활성' : 
                                 user.approval_status === 'pending' ? '대기' : '비활성'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            <div className="p-6 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={() => setShowGroupModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
              <button
                onClick={saveGroup}
                className="px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
              >
                {selectedGroup ? '수정' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Models Tab */}
      {activeTab === 'models' && (
        <div className="space-y-6">
          {/* 헤더 */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">LLM 모델 관리</h2>
                <p className="text-gray-600 mt-1">AI 모델 설정을 관리하고 권한을 제어합니다.</p>
              </div>
              <button 
                onClick={() => openModelModal()}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>모델 추가</span>
              </button>
            </div>
          </div>

          {/* 모델 목록 */}
          <div className="bg-white rounded-2xl border border-gray-100">
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">모델</th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">타입</th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">모델 ID</th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">소유자</th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">생성일</th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">액션</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {llmModels.map((model) => (
                    <tr key={model.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <div className="w-10 h-10 bg-blue-50 rounded-full flex items-center justify-center">
                            <Brain className="w-5 h-5 text-blue-600" />
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">{model.model_name}</div>
                            <div className="text-sm text-gray-500">{model.description}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800">
                          {model.model_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {model.model_id}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        <div>
                          <span className={`px-2 py-1 text-xs font-medium rounded ${
                            model.owner_type === 'USER' ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'
                          }`}>
                            {model.owner_type}
                          </span>
                          <div className="text-xs text-gray-500 mt-1">{model.owner_id}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${
                          model.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {model.is_active ? '활성' : '비활성'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {formatDate(model.created_at)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex space-x-2">
                          <button
                            onClick={() => openModelModal(model)}
                            className="p-1 text-gray-600 hover:text-blue-600 transition-colors"
                            title="편집"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => deleteModel(model.id)}
                            className="p-1 text-gray-600 hover:text-red-600 transition-colors"
                            title="삭제"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {llmModels.length === 0 && (
              <div className="text-center py-12">
                <Brain className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">등록된 모델이 없습니다</h3>
                <p className="text-gray-600 mb-4">새로운 LLM 모델을 추가해보세요.</p>
                <button
                  onClick={() => openModelModal()}
                  className="inline-flex items-center px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  모델 추가
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Model Modal */}
      {showModelModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl mx-4 border border-gray-100">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">
                {isEditingModel ? '모델 편집' : '새 모델 추가'}
              </h3>
            </div>
            <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">모델명 *</label>
                  <input
                    type="text"
                    value={editedModelInfo.model_name}
                    onChange={(e) => setEditedModelInfo({...editedModelInfo, model_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="모델명을 입력하세요"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">모델 타입 *</label>
                  <select
                    value={editedModelInfo.model_type}
                    onChange={(e) => handleModelTypeChange(e.target.value as ModelType)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                  >
                    <option value="AZURE_OPENAI">Azure OpenAI</option>
                    <option value="AZURE_CLAUDE">Azure Claude</option>
                    <option value="AZURE_DEEPSEEK">Azure DeepSeek</option>
                    <option value="OLLAMA">Ollama</option>
                    <option value="FLOWSTUDIO">FlowStudio</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">모델 ID *</label>
                <input
                  type="text"
                  value={editedModelInfo.model_id}
                  onChange={(e) => setEditedModelInfo({...editedModelInfo, model_id: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                  placeholder="실제 모델 식별자를 입력하세요"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">설명</label>
                <textarea
                  value={editedModelInfo.description}
                  onChange={(e) => setEditedModelInfo({...editedModelInfo, description: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                  rows={3}
                  placeholder="모델에 대한 설명을 입력하세요"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">소유자 타입</label>
                  <select
                    value={editedModelInfo.owner_type}
                    onChange={(e) => setEditedModelInfo({...editedModelInfo, owner_type: e.target.value as OwnerType})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                  >
                    <option value="USER">사용자</option>
                    <option value="GROUP">그룹</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">소유자 ID</label>
                  <input
                    type="text"
                    value={editedModelInfo.owner_id}
                    onChange={(e) => setEditedModelInfo({...editedModelInfo, owner_id: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                    placeholder="소유자 ID (선택사항)"
                  />
                </div>
              </div>

              {/* 모델 타입별 설정 폼 */}
              <div className="border-t pt-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">모델 설정</h4>
                
                {/* Azure OpenAI 설정 */}
                {editedModelInfo.model_type === 'AZURE_OPENAI' && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">API Key *</label>
                        <input
                          type="password"
                          value={editedModelInfo.config.api_key || ''}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, api_key: e.target.value}
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                          placeholder="Azure OpenAI API Key"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Endpoint *</label>
                        <input
                          type="url"
                          value={editedModelInfo.config.endpoint || ''}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, endpoint: e.target.value}
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                          placeholder="https://your-resource.openai.azure.com/"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">API Version</label>
                        <input
                          type="text"
                          value={editedModelInfo.config.api_version || '2024-02-01'}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, api_version: e.target.value}
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Deployment Name *</label>
                        <input
                          type="text"
                          value={editedModelInfo.config.deployment_name || ''}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, deployment_name: e.target.value},
                            model_id: e.target.value
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                          placeholder="gpt-4"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
                        <input
                          type="number"
                          min="0"
                          max="2"
                          step="0.1"
                          value={editedModelInfo.config.temperature || 0.7}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, temperature: parseFloat(e.target.value)}
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
                      <input
                        type="number"
                        min="1"
                        max="4000"
                        value={editedModelInfo.config.max_tokens || 1000}
                        onChange={(e) => setEditedModelInfo({
                          ...editedModelInfo,
                          config: {...editedModelInfo.config, max_tokens: parseInt(e.target.value)}
                        })}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                      />
                    </div>
                  </div>
                )}

                {/* Ollama 설정 */}
                {editedModelInfo.model_type === 'OLLAMA' && (
                  <div className="space-y-4">
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <h5 className="text-sm font-medium text-blue-900 mb-2">Ollama 서버 연결</h5>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <label className="block text-xs font-medium text-blue-700 mb-1">Host</label>
                          <input
                            type="text"
                            value={ollamaHost}
                            onChange={(e) => setOllamaHost(e.target.value)}
                            className="w-full px-2 py-1 text-sm border border-blue-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-300"
                            placeholder="localhost"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-blue-700 mb-1">Port</label>
                          <input
                            type="number"
                            value={ollamaPort}
                            onChange={(e) => setOllamaPort(parseInt(e.target.value) || 11434)}
                            className="w-full px-2 py-1 text-sm border border-blue-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-300"
                            placeholder="11434"
                          />
                        </div>
                        <div className="flex items-end">
                          <button
                            onClick={fetchOllamaModels}
                            disabled={ollamaLoading}
                            className="w-full px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {ollamaLoading ? '조회중...' : '모델 조회'}
                          </button>
                        </div>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Host *</label>
                        <input
                          type="text"
                          value={editedModelInfo.config.host || 'localhost'}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, host: e.target.value}
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                          placeholder="localhost"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Port *</label>
                        <input
                          type="number"
                          value={editedModelInfo.config.port || 11434}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, port: parseInt(e.target.value) || 11434}
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                          placeholder="11434"
                        />
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">모델 선택 *</label>
                      {ollamaModels.length > 0 ? (
                        <select
                          value={editedModelInfo.config.model_name || ''}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, model_name: e.target.value},
                            model_id: e.target.value
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                        >
                          <option value="">모델을 선택하세요</option>
                          {ollamaModels.map((model, index) => (
                            <option key={index} value={model.name}>
                              {model.name} ({(model.size / 1024 / 1024 / 1024).toFixed(1)}GB)
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="text"
                          value={editedModelInfo.config.model_name || ''}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, model_name: e.target.value},
                            model_id: e.target.value
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                          placeholder="llama2, gemma:7b 등"
                        />
                      )}
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
                        <input
                          type="number"
                          min="0"
                          max="2"
                          step="0.1"
                          value={editedModelInfo.config.temperature || 0.7}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, temperature: parseFloat(e.target.value)}
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Num Predict</label>
                        <input
                          type="number"
                          min="1"
                          max="4000"
                          value={editedModelInfo.config.num_predict || 1000}
                          onChange={(e) => setEditedModelInfo({
                            ...editedModelInfo,
                            config: {...editedModelInfo.config, num_predict: parseInt(e.target.value)}
                          })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* 다른 모델 타입들의 기본 JSON 편집기 */}
                {!['AZURE_OPENAI', 'OLLAMA'].includes(editedModelInfo.model_type) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">모델 설정 (JSON)</label>
                    <textarea
                      value={JSON.stringify(editedModelInfo.config, null, 2)}
                      onChange={(e) => {
                        try {
                          const config = JSON.parse(e.target.value);
                          setEditedModelInfo({...editedModelInfo, config});
                        } catch (error) {
                          // JSON 파싱 오류는 무시하고 계속 입력 허용
                        }
                      }}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300 font-mono text-sm"
                      rows={6}
                      placeholder='{"api_key": "your-key", "endpoint": "https://..."}'
                    />
                  </div>
                )}
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={editedModelInfo.is_active}
                  onChange={(e) => setEditedModelInfo({...editedModelInfo, is_active: e.target.checked})}
                  className="rounded border-gray-300 text-gray-900 focus:ring-gray-200"
                />
                <label htmlFor="is_active" className="ml-2 text-sm font-medium text-gray-700">
                  모델 활성화
                </label>
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={() => setShowModelModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
              <button
                onClick={saveModel}
                className="px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
              >
                {isEditingModel ? '수정' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPage; 