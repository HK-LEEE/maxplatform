import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  User, 
  Lock, 
  Edit, 
  Save, 
  X, 
  Eye, 
  EyeOff,
  Mail,
  Phone,
  Building,
  Briefcase,
  FileText,
  ArrowLeft
} from 'lucide-react';

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
  created_at: string;
  last_login_at: string | null;
  login_count: number;
  role: any;
  group: any;
}

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const [userDetail, setUserDetail] = useState<UserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditingInfo, setIsEditingInfo] = useState(false);
  const [showPasswordSection, setShowPasswordSection] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  const [editedUserInfo, setEditedUserInfo] = useState({
    real_name: '',
    display_name: '',
    phone_number: '',
    department: '',
    position: '',
    bio: ''
  });

  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  useEffect(() => {
    fetchUserProfile();
  }, []);

  const fetchUserProfile = async () => {
    try {
      const token = localStorage.getItem('token');
      
      // 먼저 현재 사용자 정보 가져오기
      const authResponse = await fetch('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (authResponse.ok) {
        const currentUser = await authResponse.json();
        
        // 사용자 상세 정보 가져오기
        const detailResponse = await fetch(`/admin/users/${currentUser.id}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (detailResponse.ok) {
          const detail = await detailResponse.json();
          setUserDetail(detail);
          setEditedUserInfo({
            real_name: detail.real_name || '',
            display_name: detail.display_name || '',
            phone_number: detail.phone_number || '',
            department: detail.department || '',
            position: detail.position || '',
            bio: detail.bio || ''
          });
        }
      }
    } catch (error) {
      console.error('사용자 프로필 로드 실패:', error);
    } finally {
      setLoading(false);
    }
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
        await fetchUserProfile();
      } else {
        const error = await response.json();
        alert(`사용자 정보 업데이트 중 오류가 발생했습니다: ${error.detail}`);
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
        const error = await response.json();
        alert(`비밀번호 변경 실패: ${error.detail}`);
      }
    } catch (error) {
      console.error('비밀번호 변경 실패:', error);
      alert('비밀번호 변경 중 오류가 발생했습니다.');
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('ko-KR');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!userDetail) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500">사용자 정보를 불러올 수 없습니다.</p>
          <button 
            onClick={() => navigate('/dashboard')}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            대시보드로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">프로필 설정</h1>
                <p className="text-sm text-gray-500">개인정보 및 계정 설정</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* 기본 정보 섹션 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <User className="w-5 h-5 text-gray-500" />
                  <h2 className="text-lg font-medium text-gray-900">기본 정보</h2>
                </div>
                <button
                  onClick={() => {
                    if (isEditingInfo) {
                      updateUserInfo();
                    } else {
                      setIsEditingInfo(true);
                    }
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  {isEditingInfo ? <Save className="w-4 h-4" /> : <Edit className="w-4 h-4" />}
                  <span>{isEditingInfo ? '저장' : '편집'}</span>
                </button>
              </div>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <User className="w-4 h-4 inline mr-1" />
                    실명
                  </label>
                  {isEditingInfo ? (
                    <input
                      type="text"
                      value={editedUserInfo.real_name}
                      onChange={(e) => setEditedUserInfo({...editedUserInfo, real_name: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  ) : (
                    <p className="text-gray-900">{userDetail.real_name || '-'}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <User className="w-4 h-4 inline mr-1" />
                    표시명
                  </label>
                  {isEditingInfo ? (
                    <input
                      type="text"
                      value={editedUserInfo.display_name}
                      onChange={(e) => setEditedUserInfo({...editedUserInfo, display_name: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  ) : (
                    <p className="text-gray-900">{userDetail.display_name || '-'}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <Mail className="w-4 h-4 inline mr-1" />
                    이메일
                  </label>
                  <p className="text-gray-900">{userDetail.email}</p>
                  <span className="text-xs text-gray-400">(변경불가)</span>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <Phone className="w-4 h-4 inline mr-1" />
                    전화번호
                  </label>
                  {isEditingInfo ? (
                    <input
                      type="text"
                      value={editedUserInfo.phone_number}
                      onChange={(e) => setEditedUserInfo({...editedUserInfo, phone_number: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  ) : (
                    <p className="text-gray-900">{userDetail.phone_number || '-'}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <Building className="w-4 h-4 inline mr-1" />
                    부서
                  </label>
                  {isEditingInfo ? (
                    <input
                      type="text"
                      value={editedUserInfo.department}
                      onChange={(e) => setEditedUserInfo({...editedUserInfo, department: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  ) : (
                    <p className="text-gray-900">{userDetail.department || '-'}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <Briefcase className="w-4 h-4 inline mr-1" />
                    직책
                  </label>
                  {isEditingInfo ? (
                    <input
                      type="text"
                      value={editedUserInfo.position}
                      onChange={(e) => setEditedUserInfo({...editedUserInfo, position: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  ) : (
                    <p className="text-gray-900">{userDetail.position || '-'}</p>
                  )}
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <FileText className="w-4 h-4 inline mr-1" />
                    자기소개
                  </label>
                  {isEditingInfo ? (
                    <textarea
                      value={editedUserInfo.bio}
                      onChange={(e) => setEditedUserInfo({...editedUserInfo, bio: e.target.value})}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  ) : (
                    <p className="text-gray-900">{userDetail.bio || '-'}</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* 비밀번호 변경 섹션 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Lock className="w-5 h-5 text-gray-500" />
                  <h2 className="text-lg font-medium text-gray-900">비밀번호 변경</h2>
                </div>
                <button
                  onClick={() => setShowPasswordSection(!showPasswordSection)}
                  className="flex items-center space-x-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  {showPasswordSection ? <X className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                  <span>{showPasswordSection ? '취소' : '변경'}</span>
                </button>
              </div>
            </div>

            {showPasswordSection && (
              <div className="p-6">
                <div className="space-y-4 max-w-md">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">현재 비밀번호</label>
                    <div className="relative">
                      <input
                        type={showCurrentPassword ? "text" : "password"}
                        value={passwordData.current_password}
                        onChange={(e) => setPasswordData({...passwordData, current_password: e.target.value})}
                        className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="현재 비밀번호를 입력하세요"
                      />
                      <button
                        type="button"
                        onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      >
                        {showCurrentPassword ? <EyeOff className="w-4 h-4 text-gray-400" /> : <Eye className="w-4 h-4 text-gray-400" />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">새 비밀번호</label>
                    <div className="relative">
                      <input
                        type={showNewPassword ? "text" : "password"}
                        value={passwordData.new_password}
                        onChange={(e) => setPasswordData({...passwordData, new_password: e.target.value})}
                        className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="새 비밀번호를 입력하세요"
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      >
                        {showNewPassword ? <EyeOff className="w-4 h-4 text-gray-400" /> : <Eye className="w-4 h-4 text-gray-400" />}
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">최소 6자 이상 입력해주세요</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">새 비밀번호 확인</label>
                    <div className="relative">
                      <input
                        type={showConfirmPassword ? "text" : "password"}
                        value={passwordData.confirm_password}
                        onChange={(e) => setPasswordData({...passwordData, confirm_password: e.target.value})}
                        className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="새 비밀번호를 다시 입력하세요"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      >
                        {showConfirmPassword ? <EyeOff className="w-4 h-4 text-gray-400" /> : <Eye className="w-4 h-4 text-gray-400" />}
                      </button>
                    </div>
                  </div>

                  <button
                    onClick={changePassword}
                    className="w-full bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 transition-colors"
                  >
                    비밀번호 변경
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* 계정 정보 섹션 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">계정 정보</h2>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">계정 상태</label>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                    userDetail.is_active 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {userDetail.is_active ? '활성' : '비활성'}
                  </span>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">권한</label>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                    userDetail.is_admin 
                      ? 'bg-purple-100 text-purple-800' 
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {userDetail.is_admin ? '관리자' : '일반 사용자'}
                  </span>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">가입일</label>
                  <p className="text-gray-900">{formatDate(userDetail.created_at)}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">마지막 로그인</label>
                  <p className="text-gray-900">{formatDate(userDetail.last_login_at)}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">로그인 횟수</label>
                  <p className="text-gray-900">{userDetail.login_count}회</p>
                </div>

                {userDetail.group && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">그룹</label>
                    <p className="text-gray-900">{userDetail.group.name}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage; 