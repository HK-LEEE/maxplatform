import React, { useState, useEffect, useRef } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { 
  User,
  Settings,
  LogOut,
  Bell,
  Search,
  Sparkles
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import SimpleLogoutModal from '../SimpleLogoutModal';
import { useSimpleLogout } from '../../hooks/useSimpleLogout';
import { useGlobalLogout } from '../GlobalLogoutModal';
import toast from 'react-hot-toast';

const MainLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const dropdownRef = useRef<HTMLDivElement>(null);
  
  // 간소화된 로그아웃 모달 관련
  const { executeLogout } = useSimpleLogout();
  
  // 전역 로그아웃 모달 관련
  const { showLogout, showError, hideModal, updateProgress } = useGlobalLogout();

  // 사용자가 로그인되지 않은 경우 로그인 페이지로 리다이렉트
  useEffect(() => {
    if (!user) {
      navigate('/login');
    }
  }, [user, navigate]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 로그아웃 모달 열기
  const handleLogoutClick = () => {
    setDropdownOpen(false); // 드롭다운 먼저 닫기
    setIsModalOpen(true); // 바로 모달 열기
  };

  // 간소화된 로그아웃 처리 (모달에서 호출)
  const handleLogout = async (logoutType: 'smart' | 'current' | 'all') => {
    try {
      console.log(`🔄 Starting ${logoutType} logout process...`);
      
      // Show loading modal instead of toast
      showLogout(
        'MAX Lab과 동기화하고 있습니다',
        '모든 관련 시스템에서 안전하게 로그아웃하는 중입니다.'
      );
      updateProgress(10);
      
      // 백엔드 세션 로그아웃 API 호출 (선택적)
      if (logoutType === 'all' || logoutType === 'smart') {
        try {
          console.log('🔄 Calling backend logout API...');
          updateProgress(30);
          await executeLogout(logoutType);
          console.log('✅ Backend logout API completed');
          updateProgress(60);
        } catch (error) {
          console.warn('⚠️ 백엔드 로그아웃 API 오류:', error);
          // 오류가 있어도 계속 진행
          updateProgress(50);
        }
      }
      
      // SSO 로그아웃 수행 (AuthContext의 logout 함수 사용)
      console.log('🔄 Performing SSO logout...');
      updateProgress(80);
      await logout(true);
      
      // Success - modal will be hidden by navigation
      updateProgress(100);
      hideModal();
      
    } catch (error) {
      console.error('❌ Logout error:', error);
      
      // Show error modal instead of toast
      showError(
        '로그아웃 중 오류가 발생했지만 계속 진행합니다',
        '일부 시스템에서 오류가 발생했지만 로그아웃을 완료합니다.'
      );
      
      try {
        // Force logout even on error
        await logout(true);
      } catch (secondError) {
        console.error('❌ Fallback logout also failed:', secondError);
        // Force redirect as last resort
        window.location.href = '/login?logout=error';
      }
    }
  };

  // 현재 페이지 제목 가져오기
  const getCurrentPageTitle = () => {
    const path = location.pathname;
    if (path === '/dashboard') return 'Dashboard';
    if (path.startsWith('/dashboard/chat')) return 'MAX LLM';
    if (path.startsWith('/dashboard/workspaces')) return 'MAX Workspace';
    if (path.startsWith('/dashboard/rag-datasources')) return 'MAX RAG';
    if (path.startsWith('/dashboard/llmops')) return 'LLMOps';
    if (path.startsWith('/dashboard/flow-studio')) return 'Flow Studio';
    return 'Dashboard';
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Top Navigation Bar */}
      <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div 
              onClick={() => navigate('/dashboard')}
              className="flex items-center space-x-4 cursor-pointer hover:opacity-80 transition-opacity"
            >
              <div className="relative">
                <div className="w-10 h-10 bg-gradient-to-br from-gray-900 to-gray-700 rounded-xl flex items-center justify-center shadow-lg">
                  <span className="text-white font-bold text-lg font-display">M</span>
                </div>
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full flex items-center justify-center">
                  <Sparkles className="w-2 h-2 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900 font-display">{getCurrentPageTitle()}</h1>
                <p className="text-xs text-gray-500">Manufacturing AI & DX</p>
              </div>
            </div>

            {/* Right Side */}
            <div className="flex items-center space-x-4">
              {/* Search */}
              <div className="relative hidden md:block">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="검색..."
                  className="w-64 pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all duration-200 bg-white text-sm"
                />
              </div>
              
              {/* Notifications */}
              <button className="relative w-10 h-10 bg-gray-50 hover:bg-gray-100 rounded-lg flex items-center justify-center transition-colors">
                <Bell className="w-5 h-5 text-gray-600" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"></div>
              </button>

              {/* User Menu */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="w-8 h-8 bg-gradient-to-br from-gray-700 to-gray-900 rounded-lg flex items-center justify-center">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  <div className="hidden md:block text-left">
                    <div className="text-sm font-medium text-gray-900">
                      {user?.display_name || user?.real_name || 'Unknown User'}
                    </div>
                    <div className="text-xs text-gray-500">
                      {user?.email || 'No email'}
                    </div>
                  </div>
                </button>

                {/* Dropdown Menu */}
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-100 py-1 z-50">
                    <button 
                      onClick={() => navigate('/profile')}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center space-x-2"
                    >
                      <Settings className="w-4 h-4" />
                      <span>설정</span>
                    </button>
                    <hr className="my-1 border-gray-100" />
                    <button 
                      onClick={handleLogoutClick}
                      className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>로그아웃</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* 간소화된 로그아웃 모달 */}
      <SimpleLogoutModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onLogout={handleLogout}
        userName={user?.display_name || user?.real_name || user?.username}
      />
    </div>
  );
};

export default MainLayout; 