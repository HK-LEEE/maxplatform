import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Workflow, 
  Database, 
  Brain, 
  Settings, 
  BarChart3, 
  Users, 
  Shield, 
  Zap,
  ArrowRight,
  Sparkles,
  ExternalLink,
  Grid3X3,
  Layers,
  Code,
  FileText,
  Monitor,
  Filter,
  X,
  Maximize,
  Minimize,
  MessageCircle,
  Plus
} from 'lucide-react';
import FeatureLogo from '../components/common/FeatureLogo';
import MiniLLMChat from '../components/chat/MiniLLMChat';
import { servicesApi } from '../services/api';

interface Feature {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  icon: string;
  url_path: string;
  is_external: boolean;
  open_in_new_tab: boolean;
  is_active: boolean;
}

interface User {
  id: string;
  email: string;
  groups: Array<{ id: string; name: string }>;
}

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [features, setFeatures] = useState<Feature[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [compactMode, setCompactMode] = useState(false);
  const [floatingMenuPosition, setFloatingMenuPosition] = useState({ top: 80, right: 20 });
  const [miniChatOpen, setMiniChatOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  // 플로팅 메뉴 위치 업데이트
  useEffect(() => {
    const handleScroll = () => {
      if (containerRef.current) {
        const scrollTop = window.scrollY;
        const windowHeight = window.innerHeight;
        
        // 스크롤 비율 계산
        const scrollRatio = scrollTop / Math.max(document.body.scrollHeight - windowHeight, 1);
        
        // 메뉴 위치 계산
        const newTop = Math.max(80, Math.min(80 + (scrollRatio * 100), windowHeight - 200));
        
        setFloatingMenuPosition({ top: newTop, right: 20 });
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [featuresResponse, userResponse] = await Promise.all([
        servicesApi.getMotherPageServices(),
        getCurrentUser()
      ]);
      
      // API 응답 구조에 따라 안전하게 처리
      const featuresData = featuresResponse.data?.services || [];
      console.log('Features response:', featuresResponse.data);
      console.log('Features data:', featuresData);
      
      // 배열인지 확인하고 설정
      if (Array.isArray(featuresData)) {
        // 백엔드 서비스 데이터를 프론트엔드 Feature 형식으로 변환
        const transformedFeatures = featuresData.map(service => ({
          id: service.service_id.toString(),
          name: service.service_name,
          display_name: service.service_display_name,
          description: service.description || '',
          category: service.category || 'general',
          icon: service.service_name.toLowerCase().replace(/-/g, ''),
          url_path: service.url,
          is_external: service.is_external || false,
          open_in_new_tab: service.open_in_new_tab || false,
          is_active: true
        }));
        setFeatures(transformedFeatures);
      } else {
        console.warn('Features data is not an array:', featuresData);
        setFeatures([]);
      }
      
      setUser(userResponse);
    } catch (error) {
      console.error('대시보드 데이터 로드 실패:', error);
      setFeatures([]); // 오류 시 빈 배열로 설정
    } finally {
      setLoading(false);
    }
  };

  const getCurrentUser = async (): Promise<User> => {
    // 실제 구현에서는 auth API를 호출
    return {
      id: '1',
      email: 'admin@test.com',
      groups: [{ id: '1', name: 'admin' }]
    };
  };

  const getIconComponent = (iconName: string) => {
    const iconMap: { [key: string]: React.ComponentType<any> } = {
      'workflow': Workflow,
      'flowstudio': Workflow,
      'database': Database,
      'ragdatasources': Database,
      'brain': Brain,
      'llmops': Brain,
      'settings': Settings,
      'admin': Settings,
      'barchart': BarChart3,
      'analytics': BarChart3,
      'users': Users,
      'shield': Shield,
      'security': Shield,
      'zap': Zap,
      'jupyter': Code,
      'notebook': FileText,
      'monitor': Monitor,
      'grid': Grid3X3,
      'layers': Layers,
    };
    return iconMap[iconName] || Grid3X3;
  };

  const getCategoryColor = (category: string) => {
    const colorMap: { [key: string]: string } = {
      'ai': 'from-blue-50 to-blue-100 border-blue-200',
      'data': 'from-green-50 to-green-100 border-green-200',
      'analysis': 'from-purple-50 to-purple-100 border-purple-200',
      'admin': 'from-red-50 to-red-100 border-red-200',
      'development': 'from-yellow-50 to-yellow-100 border-yellow-200',
      'collaboration': 'from-pink-50 to-pink-100 border-pink-200',
      'core': 'from-gray-50 to-gray-100 border-gray-200',
      'general': 'from-gray-50 to-gray-100 border-gray-200'
    };
    return colorMap[category] || 'from-gray-50 to-gray-100 border-gray-200';
  };

  const getCategoryDisplayName = (category: string) => {
    const nameMap: { [key: string]: string } = {
      'ai': 'AI/ML',
      'data': '데이터',
      'analysis': '분석',
      'admin': '관리',
      'development': '개발',
      'collaboration': '협업',
      'core': '핵심',
      'general': '일반'
    };
    return nameMap[category] || category;
  };

  // 카테고리 목록 생성
  const categories = Array.from(new Set(features.map(f => f.category))).sort();

  const filteredFeatures = Array.isArray(features) 
    ? features.filter(feature => 
        feature.is_active && 
        (selectedCategory === 'all' || feature.category === selectedCategory)
      )
    : [];

  const handleFeatureClick = (feature: Feature) => {
    console.log('Feature clicked:', feature);
    console.log('Feature URL path:', feature.url_path);
    
    if (feature.url_path) {
      // 워크스페이스 관련 경로 처리
      if (feature.name === 'jupyter_workspace' || feature.url_path === '/workspace') {
        console.log('Navigating to workspaces page');
        navigate('/workspaces');
        return;
      }
      
      if (feature.is_external || feature.open_in_new_tab) {
        window.open(feature.url_path, '_blank');
      } else {
        if (feature.url_path.startsWith('http')) {
          window.location.href = feature.url_path;
        } else {
          console.log('Navigating to:', feature.url_path);
          navigate(feature.url_path);
        }
      }
    } else {
      console.warn('No URL path found for feature:', feature);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-2 border-gray-200 border-t-gray-900 mx-auto mb-4"></div>
          <p className="text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="min-h-screen bg-white">
      {/* 플로팅 메뉴 */}
      <div 
        className="fixed z-50 flex flex-col gap-2 transition-all duration-200"
        style={{ 
          top: `${floatingMenuPosition.top}px`, 
          right: `${floatingMenuPosition.right}px` 
        }}
      >
        <button
          onClick={() => setCompactMode(!compactMode)}
          className="bg-gray-800 text-white p-3 rounded-full shadow-lg hover:bg-gray-700 transition-colors hover:scale-110"
          title={compactMode ? "확장 모드" : "컴팩트 모드"}
        >
          {compactMode ? <Maximize className="w-5 h-5" /> : <Minimize className="w-5 h-5" />}
        </button>
        <button
          onClick={() => setMiniChatOpen(true)}
          className="bg-blue-500 text-white p-3 rounded-full shadow-lg hover:bg-blue-600 transition-colors hover:scale-110"
          title="AI 채팅"
        >
          <MessageCircle className="w-5 h-5" />
        </button>
        <button
          onClick={() => navigate('/flow-studio')}
          className="bg-purple-500 text-white p-3 rounded-full shadow-lg hover:bg-purple-600 transition-colors hover:scale-110"
          title="플로우 스튜디오"
        >
          <Workflow className="w-5 h-5" />
        </button>
      </div>

      {compactMode ? (
        /* 컴팩트 모드 - 모바일 버전 스타일 */
        <div className="min-h-screen bg-gray-50 p-4">
          <div className="max-w-md mx-auto">
            {/* 컴팩트 헤더 */}
            <div className="bg-white rounded-2xl p-6 mb-6 shadow-sm border border-gray-100">
              <div className="text-center">
                <div className="w-12 h-12 bg-gradient-to-br from-gray-900 to-gray-700 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <span className="text-white font-bold text-lg">M</span>
                </div>
                <h1 className="text-xl font-bold text-gray-900 mb-1">MAX Platform</h1>
                <p className="text-sm text-gray-600">Manufacturing AI & DX</p>
              </div>
            </div>

            {/* 컴팩트 서비스 목록 */}
            <div className="space-y-3">
              {filteredFeatures.map((feature) => {
                const IconComponent = getIconComponent(feature.icon);
                
                return (
                  <div
                    key={feature.id}
                    className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 hover:shadow-md transition-all duration-200 cursor-pointer"
                    onClick={() => handleFeatureClick(feature)}
                  >
                    <div className="flex items-center space-x-3">
                      <FeatureLogo 
                        displayName={feature.display_name}
                        size="small"
                      />
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-gray-900 truncate">{feature.display_name}</h3>
                        <p className="text-sm text-gray-500 truncate">{getCategoryDisplayName(feature.category)}</p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-gray-400" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        /* 일반 모드 */
        <>
          {/* Hero Section */}
          <div className="bg-gradient-to-br from-gray-50 to-white border-b border-gray-100">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
              <div className="text-center">
                <div className="flex justify-center mb-6">
                  <div className="relative">
                    <div className="w-16 h-16 bg-gradient-to-br from-gray-900 to-gray-700 rounded-2xl flex items-center justify-center shadow-lg">
                      <span className="text-white font-bold text-2xl font-display">M</span>
                    </div>
                    <div className="absolute -top-1 -right-1 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                      <Sparkles className="w-2.5 h-2.5 text-white" />
                    </div>
                  </div>
                </div>
                
                <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3 font-display">
                  MAX Platform
                </h1>
                <p className="text-lg text-gray-600 mb-8">
                  Manufacturing Artificial Intelligence & Digital Transformation
                </p>
              </div>
            </div>
          </div>

          {/* Category Filter */}
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900 font-display">
                플랫폼 서비스
              </h2>
              <div className="flex items-center space-x-2">
                <Filter className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-500">카테고리:</span>
              </div>
            </div>
            
            <div className="flex flex-wrap gap-2 mb-8">
              <button
                onClick={() => setSelectedCategory('all')}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                  selectedCategory === 'all'
                    ? 'bg-gray-900 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                전체
              </button>
              {categories.map(category => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                    selectedCategory === category
                      ? 'bg-gray-900 text-white shadow-md'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {getCategoryDisplayName(category)}
                </button>
              ))}
              {selectedCategory !== 'all' && (
                <button
                  onClick={() => setSelectedCategory('all')}
                  className="px-3 py-2 rounded-full text-sm font-medium bg-red-100 text-red-700 hover:bg-red-200 transition-all duration-200 flex items-center space-x-1"
                >
                  <X className="w-3 h-3" />
                  <span>필터 해제</span>
                </button>
              )}
            </div>
          </div>

          {/* Features Grid */}
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
            {filteredFeatures.length === 0 ? (
              <div className="text-center py-20">
                <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-gray-100">
                  <Settings className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {selectedCategory === 'all' ? '사용 가능한 서비스가 없습니다' : `${getCategoryDisplayName(selectedCategory)} 카테고리에 서비스가 없습니다`}
                </h3>
                <p className="text-gray-600">
                  {selectedCategory === 'all' ? '관리자에게 권한을 요청하세요.' : '다른 카테고리를 선택해보세요.'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {filteredFeatures.map((feature, index) => {
                  const IconComponent = getIconComponent(feature.icon);
                  const categoryColor = getCategoryColor(feature.category);
                  
                  return (
                    <div
                      key={feature.id}
                      className={`group relative bg-gradient-to-br ${categoryColor} rounded-2xl p-6 shadow-sm hover:shadow-lg transition-all duration-300 cursor-pointer border hover:border-gray-300 animate-fade-in`}
                      style={{ animationDelay: `${index * 50}ms` }}
                      onClick={() => handleFeatureClick(feature)}
                    >
                      {/* Background Pattern */}
                      <div className="absolute inset-0 bg-white/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                      
                      {/* Content */}
                                              <div className="relative">
                        <div className="flex items-start justify-between mb-4">
                          <div className="group-hover:scale-110 transition-transform duration-300">
                                                         <FeatureLogo 
                               displayName={feature.display_name}
                               size="medium"
                             />
                          </div>
                          <div className="flex items-center space-x-1">
                            {(feature.is_external || feature.open_in_new_tab) && (
                              <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
                            )}
                            <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 group-hover:translate-x-1 transition-all duration-300" />
                          </div>
                        </div>
                        
                        <h3 className="text-lg font-bold text-gray-900 mb-2 font-display group-hover:text-gray-800 transition-colors">
                          {feature.display_name}
                        </h3>
                        <p className="text-gray-600 text-sm leading-relaxed group-hover:text-gray-700 transition-colors line-clamp-2">
                          {feature.description || '서비스 설명이 없습니다.'}
                        </p>
                        
                        <div className="mt-4 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-white/50 text-gray-700 group-hover:bg-white/70 transition-colors">
                          {getCategoryDisplayName(feature.category)}
                        </div>
                      </div>
                      
                      {/* Hover Effect */}
                      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-transparent to-gray-900/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}

      {/* 미니 LLM 채팅 */}
      <MiniLLMChat
        isOpen={miniChatOpen}
        onClose={() => setMiniChatOpen(false)}
        onExpand={(chatId) => {
          setMiniChatOpen(false);
          if (chatId) {
            navigate(`/dashboard/chat?chatId=${chatId}`);
          } else {
            navigate('/dashboard/chat');
          }
        }}
      />
    </div>
  );
};

export default DashboardPage; 