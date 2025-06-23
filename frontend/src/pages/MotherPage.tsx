import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import FeatureLogo from '../components/common/FeatureLogo';

interface UserInfo {
  id: string;
  real_name: string;
  display_name: string;
  email: string;
  department?: string;
  position?: string;
  role?: string;
}

interface UserDetail {
  id: string;
  real_name: string;
  display_name: string;
  email: string;
  phone_number: string;
  department: string;
  position: string;
  bio: string;
  is_active: boolean;
  is_admin: boolean;
  approval_status: string;
  approval_note: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  last_login_at: string | null;
  login_count: number;
  role: any;
  group: any;
}

interface Group {
  id: number;
  name: string;
  description: string;
}

interface Service {
  service_id: number;
  service_name: string;
  service_display_name: string;
  description?: string;
  url: string;
  icon_url?: string;
  thumbnail_url?: string;
  is_external: boolean;
  open_in_new_tab: boolean;
  category?: string;
  sort_order: number;
}

interface Category {
  name: string;
  display_name: string;
  description?: string;
  sort_order: number;
}

interface MainPageData {
  user_info: UserInfo;
  services: Service[];
  categories: Category[];
}

const MainPage: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<MainPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [userDetail, setUserDetail] = useState<UserDetail | null>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [isEditingInfo, setIsEditingInfo] = useState(false);
  const [editedUserInfo, setEditedUserInfo] = useState({
    real_name: '',
    display_name: '',
    phone_number: '',
    department: '',
    position: '',
    bio: ''
  });
  const [availableGroups, setAvailableGroups] = useState<Group[]>([]);
  
  // 비밀번호 변경 관련 상태
  const [showPasswordSection, setShowPasswordSection] = useState(false);
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  useEffect(() => {
    // 인증 체크
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/');
      return;
    }
    
    fetchMainPageData();
  }, [navigate]);

  const fetchMainPageData = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/services/mother-page', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const result = await response.json();
        setData(result);
      } else if (response.status === 401) {
        // 토큰 만료 또는 인증 실패시 로그인 페이지로 리다이렉트
        localStorage.removeItem('token');
        navigate('/login');
        return;
      } else {
        console.error('Main page 데이터 로드 실패');
      }
    } catch (error) {
      console.error('Main page 데이터 로드 중 오류:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleServiceClick = (service: Service) => {
    if (service.is_external || service.open_in_new_tab) {
      window.open(service.url, '_blank');
    } else {
      if (service.url.startsWith('http')) {
        window.location.href = service.url;
      } else {
        navigate(service.url);
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  const openAccountModal = async () => {
    if (!data?.user_info?.id) return;
    
    setShowAccountModal(true);
    setModalLoading(true);
    
    try {
      const token = localStorage.getItem('token');
      
      // 사용자 상세 정보 조회
      const userResponse = await fetch(`/admin/users/${data.user_info.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (userResponse.ok) {
        const userData = await userResponse.json();
        setUserDetail(userData);
        setEditedUserInfo({
          real_name: userData.real_name || '',
          display_name: userData.display_name || '',
          phone_number: userData.phone_number || '',
          department: userData.department || '',
          position: userData.position || '',
          bio: userData.bio || ''
        });
      } else if (userResponse.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }
      
      // 사용 가능한 그룹 목록 조회
      const groupsResponse = await fetch('/admin/groups', {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (groupsResponse.ok) {
        const groupsData = await groupsResponse.json();
        setAvailableGroups(groupsData);
      } else if (groupsResponse.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }
      
    } catch (error) {
      console.error('사용자 상세 정보 로드 실패:', error);
    } finally {
      setModalLoading(false);
    }
  };

  const closeAccountModal = () => {
    setShowAccountModal(false);
    setUserDetail(null);
    setModalLoading(false);
    setIsEditingInfo(false);
    setShowPasswordSection(false);
    setEditedUserInfo({
      real_name: '',
      display_name: '',
      phone_number: '',
      department: '',
      position: '',
      bio: ''
    });
    setPasswordData({
      current_password: '',
      new_password: '',
      confirm_password: ''
    });
  };

  const updateUserInfo = async () => {
    if (!userDetail) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/admin/users/${userDetail.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(editedUserInfo),
      });

      if (response.ok) {
        alert('사용자 정보가 업데이트되었습니다.');
        setIsEditingInfo(false);
        // 사용자 상세 정보 다시 로드
        await openAccountModal();
        // Main Page 데이터도 새로고침
        await fetchMainPageData();
      } else {
        alert('사용자 정보 업데이트 중 오류가 발생했습니다.');
      }
    } catch (error) {
      console.error('사용자 정보 업데이트 실패:', error);
      alert('사용자 정보 업데이트 중 오류가 발생했습니다.');
    }
  };

  const changePassword = async () => {
    if (!passwordData.current_password || !passwordData.new_password || !passwordData.confirm_password) {
      alert('모든 비밀번호 필드를 입력해주세요.');
      return;
    }
    
    if (passwordData.new_password !== passwordData.confirm_password) {
      alert('새 비밀번호가 일치하지 않습니다.');
      return;
    }
    
    if (passwordData.new_password.length < 6) {
      alert('새 비밀번호는 최소 6자 이상이어야 합니다.');
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: passwordData.current_password,
          new_password: passwordData.new_password
        }),
      });

      if (response.ok) {
        alert('비밀번호가 성공적으로 변경되었습니다.');
        setShowPasswordSection(false);
        setPasswordData({
          current_password: '',
          new_password: '',
          confirm_password: ''
        });
      } else {
        const errorData = await response.json();
        alert(errorData.detail || '비밀번호 변경 중 오류가 발생했습니다.');
      }
    } catch (error) {
      console.error('비밀번호 변경 실패:', error);
      alert('비밀번호 변경 중 오류가 발생했습니다.');
    }
  };

  const getServiceIcon = (service: Service) => {
    // 이미지 URL인 경우
    if (service.icon_url && (service.icon_url.startsWith('http') || service.icon_url.startsWith('/'))) {
      return <img src={service.icon_url} alt={service.service_display_name} className="w-8 h-8" />;
    }
    
    // FeatureLogo 컴포넌트 사용
    return (
      <FeatureLogo 
        displayName={service.service_display_name}
        size="small"
      />
    );
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderAccountModal = () => {
    if (!userDetail) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold text-gray-900">계정 편집</h3>
            <button
              onClick={closeAccountModal}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          {modalLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* 기본 정보 (편집 가능) */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-md font-semibold text-gray-900">기본 정보</h4>
                  <button
                    onClick={() => {
                      if (isEditingInfo) {
                        updateUserInfo();
                      } else {
                        setIsEditingInfo(true);
                      }
                    }}
                    className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
                  >
                    {isEditingInfo ? '저장' : '편집'}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-500">실명</label>
                    {isEditingInfo ? (
                      <input
                        type="text"
                        value={editedUserInfo.real_name}
                        onChange={(e) => setEditedUserInfo({...editedUserInfo, real_name: e.target.value})}
                        className="w-full text-sm text-gray-900 border rounded px-2 py-1 mt-1"
                      />
                    ) : (
                      <p className="text-sm text-gray-900">{userDetail.real_name || '-'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">표시명</label>
                    {isEditingInfo ? (
                      <input
                        type="text"
                        value={editedUserInfo.display_name}
                        onChange={(e) => setEditedUserInfo({...editedUserInfo, display_name: e.target.value})}
                        className="w-full text-sm text-gray-900 border rounded px-2 py-1 mt-1"
                      />
                    ) : (
                      <p className="text-sm text-gray-900">{userDetail.display_name || '-'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">이메일</label>
                    <p className="text-sm text-gray-900">{userDetail.email}</p>
                    <span className="text-xs text-gray-400">(변경불가)</span>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">전화번호</label>
                    {isEditingInfo ? (
                      <input
                        type="text"
                        value={editedUserInfo.phone_number}
                        onChange={(e) => setEditedUserInfo({...editedUserInfo, phone_number: e.target.value})}
                        className="w-full text-sm text-gray-900 border rounded px-2 py-1 mt-1"
                      />
                    ) : (
                      <p className="text-sm text-gray-900">{userDetail.phone_number || '-'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">부서</label>
                    {isEditingInfo ? (
                      <input
                        type="text"
                        value={editedUserInfo.department}
                        onChange={(e) => setEditedUserInfo({...editedUserInfo, department: e.target.value})}
                        className="w-full text-sm text-gray-900 border rounded px-2 py-1 mt-1"
                      />
                    ) : (
                      <p className="text-sm text-gray-900">{userDetail.department || '-'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">직책</label>
                    {isEditingInfo ? (
                      <input
                        type="text"
                        value={editedUserInfo.position}
                        onChange={(e) => setEditedUserInfo({...editedUserInfo, position: e.target.value})}
                        className="w-full text-sm text-gray-900 border rounded px-2 py-1 mt-1"
                      />
                    ) : (
                      <p className="text-sm text-gray-900">{userDetail.position || '-'}</p>
                    )}
                  </div>
                  <div className="col-span-2">
                    <label className="text-sm font-medium text-gray-500">자기소개</label>
                    {isEditingInfo ? (
                      <textarea
                        value={editedUserInfo.bio}
                        onChange={(e) => setEditedUserInfo({...editedUserInfo, bio: e.target.value})}
                        className="w-full text-sm text-gray-900 border rounded px-2 py-1 mt-1"
                        rows={3}
                      />
                    ) : (
                      <p className="text-sm text-gray-900">{userDetail.bio || '-'}</p>
                    )}
                  </div>
                </div>
              </div>

              {/* 그룹 관리 (읽기 전용) */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-md font-semibold text-gray-900">그룹 관리</h4>
                  <button
                    disabled
                    className="px-3 py-1 bg-gray-300 text-gray-500 text-sm rounded cursor-not-allowed"
                  >
                    그룹 변경 (비활성)
                  </button>
                </div>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-500 mb-2 block">현재 그룹</label>
                    <div>
                      {userDetail.group ? (
                        <span className="px-3 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">
                          {userDetail.group.name}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-500">할당된 그룹이 없습니다.</span>
                      )}
                    </div>
                  </div>
                  
                  <div>
                    <label className="text-sm font-medium text-gray-500 mb-2 block">그룹 선택 (비활성)</label>
                    <select
                      disabled
                      value={userDetail.group ? userDetail.group.id : ''}
                      className="w-full text-sm border rounded px-2 py-1 bg-gray-100 text-gray-500 cursor-not-allowed"
                    >
                      <option value="">그룹 없음</option>
                      {availableGroups.map((group) => (
                        <option key={group.id} value={group.id}>
                          {group.name} ({group.description})
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-400 mt-1">그룹 변경은 관리자에게 문의하세요.</p>
                  </div>
                </div>
              </div>

              {/* 비밀번호 변경 */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-md font-semibold text-gray-900">비밀번호 변경</h4>
                  <button
                    onClick={() => setShowPasswordSection(!showPasswordSection)}
                    className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
                  >
                    {showPasswordSection ? '취소' : '비밀번호 변경'}
                  </button>
                </div>
                
                {showPasswordSection && (
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-500 mb-1 block">현재 비밀번호</label>
                      <input
                        type="password"
                        value={passwordData.current_password}
                        onChange={(e) => setPasswordData({...passwordData, current_password: e.target.value})}
                        className="w-full text-sm border rounded px-2 py-1"
                        placeholder="현재 비밀번호를 입력하세요"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-500 mb-1 block">새 비밀번호</label>
                      <input
                        type="password"
                        value={passwordData.new_password}
                        onChange={(e) => setPasswordData({...passwordData, new_password: e.target.value})}
                        className="w-full text-sm border rounded px-2 py-1"
                        placeholder="새 비밀번호를 입력하세요 (최소 6자)"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-500 mb-1 block">새 비밀번호 확인</label>
                      <input
                        type="password"
                        value={passwordData.confirm_password}
                        onChange={(e) => setPasswordData({...passwordData, confirm_password: e.target.value})}
                        className="w-full text-sm border rounded px-2 py-1"
                        placeholder="새 비밀번호를 다시 입력하세요"
                      />
                    </div>
                    <div className="flex justify-end">
                      <button
                        onClick={changePassword}
                        className="px-4 py-2 bg-green-500 text-white text-sm rounded hover:bg-green-600"
                      >
                        비밀번호 변경
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* 계정 상태 (읽기 전용) */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="text-md font-semibold text-gray-900 mb-3">계정 상태</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-500">승인 상태</label>
                    <p className="text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        userDetail.approval_status === 'approved' ? 'bg-green-100 text-green-800' :
                        userDetail.approval_status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {userDetail.approval_status === 'approved' ? '승인됨' :
                         userDetail.approval_status === 'pending' ? '승인 대기' : '거절됨'}
                      </span>
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">활성 상태</label>
                    <p className="text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        userDetail.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {userDetail.is_active ? '활성' : '비활성'}
                      </span>
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">관리자</label>
                    <p className="text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        userDetail.is_admin ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {userDetail.is_admin ? '관리자' : '일반사용자'}
                      </span>
                    </p>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <label className="text-sm font-medium text-gray-500">가입일시</label>
                    <p className="text-sm text-gray-900">{formatDate(userDetail.created_at)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">최근 로그인</label>
                    <p className="text-sm text-gray-900">{formatDate(userDetail.last_login_at)}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen relative overflow-hidden">
        {/* 애니메이션 배경 */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
          <div className="absolute top-0 left-0 w-72 h-72 bg-blue-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob"></div>
          <div className="absolute top-0 right-0 w-72 h-72 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob animation-delay-2000"></div>
          <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob animation-delay-4000"></div>
        </div>
        
        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6 animate-pulse">
              <span className="text-white text-2xl font-bold">G</span>
            </div>
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600 font-medium">MAX 로딩 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen relative overflow-hidden">
        {/* 애니메이션 배경 */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
          <div className="absolute top-0 left-0 w-72 h-72 bg-blue-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob"></div>
          <div className="absolute top-0 right-0 w-72 h-72 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob animation-delay-2000"></div>
        </div>
        
        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-r from-red-500 to-orange-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <span className="text-white text-2xl">⚠️</span>
            </div>
            <p className="text-gray-600 mb-4">데이터를 불러올 수 없습니다.</p>
            <button 
              onClick={fetchMainPageData}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all transform hover:scale-105"
            >
              다시 시도
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 카테고리별로 서비스 그룹화
  const servicesByCategory = data.services.reduce((acc, service) => {
    const category = service.category || 'uncategorized';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(service);
    return acc;
  }, {} as Record<string, Service[]>);

  // 카테고리 정렬
  const sortedCategories = data.categories.sort((a, b) => a.sort_order - b.sort_order);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* 애니메이션 배경 */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
        {/* 부드러운 애니메이션 원들 */}
        <div className="absolute top-0 left-0 w-72 h-72 bg-blue-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob"></div>
        <div className="absolute top-0 right-0 w-72 h-72 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob animation-delay-4000"></div>
        <div className="absolute bottom-0 right-0 w-72 h-72 bg-indigo-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob animation-delay-6000"></div>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="relative z-10">
        {/* 헤더 */}
        <header className="bg-white/80 backdrop-blur-md shadow-lg border-b border-white/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              {/* 타이틀과 사용자 정보 */}
              <div className="flex items-center space-x-6">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                    <span className="text-white text-xl font-bold">G</span>
                  </div>
                  <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    MAX
                  </h1>
                </div>
                
                {/* 사용자 정보 */}
                <div className="hidden md:flex items-center space-x-4 pl-6 border-l border-gray-200">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full flex items-center justify-center">
                      <span className="text-white text-sm font-medium">
                        {(data.user_info.display_name || data.user_info.real_name).charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {data.user_info.display_name || data.user_info.real_name}
                      </div>
                      <div className="text-xs text-gray-500 flex items-center space-x-2">
                        <span>{data.user_info.department || '부서 미정'}</span>
                        {data.user_info.department && data.user_info.position && <span>•</span>}
                        <span>{data.user_info.position || '직책 미정'}</span>
                        {data.user_info.role && (
                          <>
                            <span>•</span>
                            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs">
                              {data.user_info.role}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 액션 버튼들 */}
              <div className="flex items-center space-x-3">
                {/* LLMOps 버튼 */}
                <button
                  onClick={() => navigate('/llmops')}
                  className="p-2.5 text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-all duration-200 group"
                  title="LLMOps Platform"
                >
                  <svg className="w-5 h-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </button>

                {/* 계정 설정 */}
                <button
                  onClick={openAccountModal}
                  className="p-2.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all duration-200 group"
                  title="계정 설정"
                >
                  <svg className="w-5 h-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </button>

                {/* 로그아웃 */}
                <button
                  onClick={handleLogout}
                  className="p-2.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200 group"
                  title="로그아웃"
                >
                  <svg className="w-5 h-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* 메인 콘텐츠 */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* 카테고리 필터 */}
          <div className="mb-8">
            <div className="flex flex-wrap gap-3 justify-center md:justify-start">
              <button
                onClick={() => setSelectedCategory('all')}
                className={`px-6 py-3 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 ${
                  selectedCategory === 'all'
                    ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                    : 'bg-white/80 text-gray-700 hover:bg-white/90 hover:shadow-md border border-gray-200'
                }`}
              >
                전체 ({data.services.length})
              </button>
              {data.categories
                .sort((a, b) => a.sort_order - b.sort_order)
                .map((category) => {
                  const categoryServices = data.services.filter(service => service.category === category.name);
                  if (categoryServices.length === 0) return null;
                  
                  return (
                    <button
                      key={category.name}
                      onClick={() => setSelectedCategory(category.name)}
                      className={`px-6 py-3 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 ${
                        selectedCategory === category.name
                          ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                          : 'bg-white/80 text-gray-700 hover:bg-white/90 hover:shadow-md border border-gray-200'
                      }`}
                    >
                      {category.display_name} ({categoryServices.length})
                    </button>
                  );
                })}
            </div>
          </div>

          {/* 선택된 카테고리의 설명 */}
          {selectedCategory !== 'all' && (
            <div className="mb-8 text-center">
              {(() => {
                const category = data.categories.find(cat => cat.name === selectedCategory);
                return category?.description && (
                  <p className="text-gray-600 text-lg max-w-2xl mx-auto leading-relaxed">
                    {category.description}
                  </p>
                );
              })()}
            </div>
          )}

          {/* 서비스 그리드 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {(() => {
              const filteredServices = selectedCategory === 'all' 
                ? data.services 
                : data.services.filter(service => service.category === selectedCategory);
              
              return filteredServices
                .sort((a, b) => a.sort_order - b.sort_order)
                .map((service) => (
                  <div
                    key={service.service_id}
                    className="group bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-500 cursor-pointer transform hover:scale-105 hover:-translate-y-2 border border-white/50"
                    onClick={() => handleServiceClick(service)}
                  >
                    <div className="p-6">
                      <div className="flex items-start mb-4">
                        <div className="w-14 h-14 bg-gradient-to-br from-blue-100 to-purple-100 rounded-xl flex items-center justify-center mr-4 group-hover:scale-110 transition-transform duration-300">
                          <span className="text-2xl" style={{ fontFamily: 'Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji, sans-serif' }}>
                            {getServiceIcon(service)}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition-colors duration-300 leading-tight">
                            {service.service_display_name}
                          </h3>
                          <div className="flex items-center mt-1 space-x-2">
                            {service.is_external && (
                              <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
                                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" />
                                </svg>
                                External
                              </span>
                            )}
                            {service.open_in_new_tab && (
                              <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">
                                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                </svg>
                                새 탭
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      {service.description && (
                        <p className="text-gray-600 text-sm mb-4 line-clamp-3 leading-relaxed">
                          {service.description}
                        </p>
                      )}
                      
                      {service.thumbnail_url && (
                        <div className="mb-4 rounded-lg overflow-hidden">
                          <img
                            src={service.thumbnail_url}
                            alt={service.service_display_name}
                            className="w-full h-32 object-cover group-hover:scale-110 transition-transform duration-500"
                          />
                        </div>
                      )}
                      
                      <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                        <span className="text-xs text-gray-500 font-medium bg-gray-50 px-2 py-1 rounded-full">
                          {service.service_name}
                        </span>
                        <div className="flex items-center space-x-1">
                          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                          <span className="text-xs text-gray-400">활성</span>
                        </div>
                      </div>
                    </div>
                    
                    {/* 호버 효과 */}
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-400/0 via-purple-400/0 to-pink-400/0 group-hover:from-blue-400/5 group-hover:via-purple-400/5 group-hover:to-pink-400/5 rounded-2xl transition-all duration-500"></div>
                  </div>
                ));
            })()}
          </div>

          {/* 필터링된 서비스가 없는 경우 */}
          {(() => {
            const filteredServices = selectedCategory === 'all' 
              ? data.services 
              : data.services.filter(service => service.category === selectedCategory);
            
            return filteredServices.length === 0 && (
              <div className="text-center py-24">
                <div className="w-24 h-24 bg-gradient-to-r from-blue-400 to-purple-500 rounded-3xl flex items-center justify-center mx-auto mb-8 animate-bounce">
                  <span className="text-4xl" style={{ fontFamily: 'Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji, sans-serif' }}>🔍</span>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">
                  {selectedCategory === 'all' ? '아직 사용 가능한 서비스가 없습니다' : '이 카테고리에 서비스가 없습니다'}
                </h3>
                <p className="text-gray-600 text-lg mb-8 max-w-md mx-auto leading-relaxed">
                  {selectedCategory === 'all' 
                    ? '관리자에게 문의하여 새로운 기능과 서비스를 추가해 보세요!' 
                    : '다른 카테고리를 선택하거나 "전체"를 확인해 보세요.'}
                </p>
                <div className="flex items-center justify-center space-x-4">
                  <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse"></div>
                  <div className="w-3 h-3 bg-purple-400 rounded-full animate-pulse animation-delay-200"></div>
                  <div className="w-3 h-3 bg-pink-400 rounded-full animate-pulse animation-delay-400"></div>
                </div>
              </div>
            );
          })()}
      </main>

        {/* 계정 모달 */}
        {showAccountModal && renderAccountModal()}
      </div>
    </div>
  );
};

export default MainPage; 