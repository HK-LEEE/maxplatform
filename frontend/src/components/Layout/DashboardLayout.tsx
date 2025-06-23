import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { 
  Menu, 
  X, 
  Home, 
  Settings, 
  LogOut, 
  User,
  Sparkles,
  ChevronRight,
  Bell,
  Search,
  Workflow,
  Database,
  Brain
} from 'lucide-react';

interface UserInfo {
  name: string;
  email: string;
  avatar?: string | null;
}

const DashboardLayout: React.FC = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // 사용자 정보 로드
    loadUserInfo();
  }, []);

  const loadUserInfo = async () => {
    // 실제 구현에서는 API 호출
    setUser({
      name: 'Admin User',
      email: 'admin@test.com',
      avatar: null
    });
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const navigationItems = [
    { 
      name: '대시보드', 
      path: '/dashboard', 
      icon: Home,
      description: '메인 대시보드'
    },
    { 
      name: 'Flow Studio', 
      path: '/dashboard/flow-studio', 
      icon: Workflow,
      description: 'AI 워크플로우'
    },
    { 
      name: 'RAG 데이터소스', 
      path: '/dashboard/rag-datasources', 
      icon: Database,
      description: '벡터 데이터베이스'
    },
    { 
      name: 'LLMOps', 
      path: '/dashboard/llmops', 
      icon: Brain,
      description: 'AI 모델 관리'
    },
  ];

  const isActivePath = (path: string) => {
    if (path === '/dashboard') {
      return location.pathname === '/dashboard';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="h-screen flex bg-surface-light">
      {/* Sidebar */}
      <div className={`${sidebarCollapsed ? 'w-20' : 'w-80'} bg-white border-r border-neutral-200 flex flex-col transition-all duration-300 shadow-soft relative`}>
        {/* Header */}
        <div className="p-6 border-b border-neutral-100">
          {!sidebarCollapsed && (
            <div 
              onClick={() => navigate('/dashboard')}
              className="flex items-center space-x-4 mb-6 cursor-pointer hover:opacity-80 transition-opacity"
            >
              <div className="relative">
                <div className="w-12 h-12 bg-gradient-to-br from-neutral-900 to-neutral-700 rounded-2xl flex items-center justify-center shadow-glow">
                  <span className="text-white font-bold text-xl font-display">M</span>
                </div>
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-accent-500 rounded-full flex items-center justify-center">
                  <Sparkles className="w-2 h-2 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-bold text-neutral-900 font-display">MAX</h1>
                <p className="text-xs text-neutral-500">Manufacturing AI & DX</p>
              </div>
            </div>
          )}
          
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="w-10 h-10 bg-neutral-100 hover:bg-neutral-200 rounded-xl flex items-center justify-center transition-colors group"
          >
            {sidebarCollapsed ? (
              <Menu className="w-5 h-5 text-neutral-600 group-hover:text-neutral-900 transition-colors" />
            ) : (
              <X className="w-5 h-5 text-neutral-600 group-hover:text-neutral-900 transition-colors" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <div className="flex-1 p-4 space-y-2">
          {navigationItems.map((item) => {
            const IconComponent = item.icon;
            const isActive = isActivePath(item.path);
            
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-2xl transition-all duration-200 group ${
                  isActive
                    ? 'bg-neutral-900 text-white shadow-medium'
                    : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'
                }`}
              >
                <IconComponent className={`w-5 h-5 ${isActive ? 'text-white' : 'text-neutral-500 group-hover:text-neutral-700'} transition-colors`} />
                {!sidebarCollapsed && (
                  <>
                    <div className="flex-1 text-left">
                      <div className={`font-medium ${isActive ? 'text-white' : 'text-neutral-900'}`}>
                        {item.name}
                      </div>
                      <div className={`text-xs ${isActive ? 'text-neutral-300' : 'text-neutral-500'}`}>
                        {item.description}
                      </div>
                    </div>
                    <ChevronRight className={`w-4 h-4 ${isActive ? 'text-white' : 'text-neutral-400 group-hover:text-neutral-600'} transition-colors`} />
                  </>
                )}
              </button>
            );
          })}
        </div>

        {/* User Profile */}
        <div className="p-4 border-t border-neutral-100">
          {!sidebarCollapsed && user && (
            <div className="bg-neutral-50 rounded-2xl p-4 mb-4">
              <div className="flex items-center space-x-3 mb-3">
                <div className="w-10 h-10 bg-gradient-to-br from-neutral-700 to-neutral-900 rounded-xl flex items-center justify-center">
                  <User className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-neutral-900 truncate">{user.name}</div>
                  <div className="text-xs text-neutral-500 truncate">{user.email}</div>
                </div>
              </div>
              
              <div className="flex space-x-2">
                <button 
                  onClick={() => navigate('/profile')}
                  className="flex-1 bg-white hover:bg-neutral-100 text-neutral-700 px-3 py-2 rounded-xl text-xs font-medium transition-colors flex items-center justify-center space-x-1"
                >
                  <Settings className="w-3 h-3" />
                  <span>설정</span>
                </button>
                <button 
                  onClick={handleLogout}
                  className="flex-1 bg-neutral-900 hover:bg-neutral-800 text-white px-3 py-2 rounded-xl text-xs font-medium transition-colors flex items-center justify-center space-x-1"
                >
                  <LogOut className="w-3 h-3" />
                  <span>로그아웃</span>
                </button>
              </div>
            </div>
          )}
          
          {sidebarCollapsed && (
            <div className="space-y-2">
              <button className="w-full h-10 bg-neutral-100 hover:bg-neutral-200 rounded-xl flex items-center justify-center transition-colors">
                <User className="w-5 h-5 text-neutral-600" />
              </button>
              <button 
                onClick={handleLogout}
                className="w-full h-10 bg-neutral-900 hover:bg-neutral-800 rounded-xl flex items-center justify-center transition-colors"
              >
                <LogOut className="w-5 h-5 text-white" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <div className="bg-white border-b border-neutral-100 px-6 py-4 flex items-center justify-between shadow-minimal">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-semibold text-neutral-900 font-display">
              {navigationItems.find(item => isActivePath(item.path))?.name || '대시보드'}
            </h2>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Search */}
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-neutral-400" />
              </div>
              <input
                type="text"
                placeholder="검색..."
                className="w-64 pl-10 pr-4 py-2 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-all duration-200 bg-white text-sm"
              />
            </div>
            
            {/* Notifications */}
            <button className="relative w-10 h-10 bg-neutral-100 hover:bg-neutral-200 rounded-xl flex items-center justify-center transition-colors">
              <Bell className="w-5 h-5 text-neutral-600" />
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-accent-500 rounded-full"></div>
            </button>
          </div>
        </div>

        {/* Page Content */}
        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default DashboardLayout; 