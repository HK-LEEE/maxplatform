import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface LLMOpsStatus {
  status: string;
  port: number;
  pid?: number;
  message: string;
}

interface Flow {
  id: string;
  name: string;
  description: string;
  created_at: number;
  modified_at: number;
}

const LLMOpsPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [status, setStatus] = useState<LLMOpsStatus | null>(null);
  const [flows, setFlows] = useState<Flow[]>([]);
  const [error, setError] = useState('');
  const [showFlowList, setShowFlowList] = useState(false);
  const navigate = useNavigate();

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const token = localStorage.getItem('token');

  // API 호출을 위한 헤더
  const getHeaders = () => ({
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  });

  // LLMOps 상태 확인
  const checkStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/llmops/status');
      
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      } else {
        throw new Error('상태 확인 실패');
      }
    } catch (err) {
      console.error('상태 확인 오류:', err);
      setError('상태 확인에 실패했습니다.');
    }
  };

  // Langflow 인스턴스 시작
  const startLangflow = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await fetch('http://localhost:8000/api/llmops/start', {
        method: 'POST',
      });
      
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
        // 시작 후 잠시 대기하고 상태 다시 확인
        setTimeout(() => {
          checkStatus();
        }, 3000);
      } else {
        throw new Error('Langflow 시작 실패');
      }
    } catch (err) {
      console.error('Langflow 시작 오류:', err);
      setError('Langflow 시작에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  // Langflow 인스턴스 중지
  const stopLangflow = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await fetch('http://localhost:8000/api/llmops/stop', {
        method: 'POST',
      });
      
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      } else {
        throw new Error('Langflow 중지 실패');
      }
    } catch (err) {
      console.error('Langflow 중지 오류:', err);
      setError('Langflow 중지에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  // 플로우 목록 조회
  const fetchFlows = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/llmops/flows', {
        headers: getHeaders(),
      });
      
      if (response.ok) {
        const data = await response.json();
        setFlows(Array.isArray(data) ? data : []);
      } else if (response.status === 401) {
        // 토큰 만료 처리
        console.warn('토큰이 만료되었습니다. 로그인이 필요합니다.');
        setError('로그인이 필요합니다. 다시 로그인해주세요.');
        // 자동으로 로그인 페이지로 이동
        setTimeout(() => {
          handleLogout();
        }, 2000);
      } else {
        throw new Error('플로우 목록 조회 실패');
      }
    } catch (err) {
      console.error('플로우 목록 조회 오류:', err);
      setError('플로우 목록 조회에 실패했습니다.');
    }
  };

  // 로그아웃
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/');
  };

  // 컴포넌트 마운트 시 상태 확인
  useEffect(() => {
    if (!token) {
      navigate('/');
      return;
    }
    
    checkStatus();
    fetchFlows();
    
    // 5초마다 상태 확인
    const interval = setInterval(checkStatus, 5000);
    
    return () => clearInterval(interval);
  }, [token, navigate]);

  // 메인 페이지로 이동
  const goToMain = () => {
    navigate('/main');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={goToMain}
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                ← 메인으로
              </button>
              <h1 className="text-2xl font-bold text-gray-900">
                LLMOps Platform
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                {user.display_name || user.real_name}
              </span>
              <button
                onClick={handleLogout}
                className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                로그아웃
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 상태 및 제어 패널 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Langflow 인스턴스 관리
            </h2>
            
            <div className="flex items-center space-x-3">
              {status && (
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  status.status === 'running' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {status.status === 'running' ? '실행 중' : '중지됨'}
                  {status.port && ` (포트: ${status.port})`}
                </span>
              )}
              
              {status?.status === 'running' ? (
                <button
                  onClick={stopLangflow}
                  disabled={isLoading}
                  className="bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white px-4 py-2 rounded-md text-sm font-medium"
                >
                  {isLoading ? '중지 중...' : '인스턴스 중지'}
                </button>
              ) : (
                <button
                  onClick={startLangflow}
                  disabled={isLoading}
                  className="bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white px-4 py-2 rounded-md text-sm font-medium"
                >
                  {isLoading ? '시작 중...' : '인스턴스 시작'}
                </button>
              )}
              
              <button
                onClick={() => setShowFlowList(!showFlowList)}
                className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                플로우 목록 {showFlowList ? '숨기기' : '보기'}
              </button>
            </div>
          </div>
          
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
              <div className="text-sm text-red-600">{error}</div>
            </div>
          )}
          
          {status && (
            <div className="text-sm text-gray-600">
              상태: {status.message}
              {status.pid && ` (PID: ${status.pid})`}
            </div>
          )}
        </div>

        {/* 플로우 목록 */}
        {showFlowList && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              저장된 플로우 ({flows.length}개)
            </h3>
            
            {flows.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                저장된 플로우가 없습니다. Langflow에서 플로우를 생성해보세요.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {flows.map((flow) => (
                  <div key={flow.id} className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">{flow.name}</h4>
                    <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                      {flow.description || '설명 없음'}
                    </p>
                    <div className="text-xs text-gray-500">
                      수정일: {new Date(flow.modified_at * 1000).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Langflow UI 임베딩 */}
        {status?.status === 'running' && (
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="bg-gray-50 px-6 py-3 border-b">
              <h3 className="text-lg font-semibold text-gray-900">
                Langflow 워크스페이스
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                아래에서 드래그 앤 드롭으로 LLM 워크플로우를 구성하세요.
              </p>
            </div>
            
            <div className="relative">
              <iframe
                src={`http://localhost:${status.port}`}
                className="w-full h-screen border-none"
                title="Langflow Interface"
                onLoad={() => setIsLoading(false)}
                onError={() => setError('Langflow UI 로딩에 실패했습니다.')}
              />
            </div>
          </div>
        )}

        {/* 시작 안내 메시지 */}
        {(!status || status.status !== 'running') && !isLoading && (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <div className="mx-auto w-24 h-24 bg-blue-100 rounded-full flex items-center justify-center mb-6">
              <svg className="w-12 h-12 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              LLMOps 워크스페이스를 시작하세요
            </h3>
            <p className="text-gray-600 mb-6">
              Langflow를 사용하여 시각적으로 LLM 파이프라인을 구성하고 실행할 수 있습니다.
            </p>
            <button
              onClick={startLangflow}
              disabled={isLoading}
              className="bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white px-6 py-3 rounded-md font-medium"
            >
              {isLoading ? '시작 중...' : 'Langflow 시작하기'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default LLMOpsPage; 
