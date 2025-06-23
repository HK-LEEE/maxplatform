import React, { useState, useEffect } from 'react';
import { X, Play, CheckCircle, XCircle, Clock, AlertCircle, Copy, Download } from 'lucide-react';

interface TestResultModalProps {
  isOpen: boolean;
  onClose: () => void;
  nodeId: string;
  nodeTitle: string;
  nodeType: string;
}

interface TestResult {
  id: string;
  timestamp: string;
  status: 'success' | 'error' | 'running' | 'pending';
  input: any;
  output: any;
  error?: string;
  duration?: number;
  metadata?: Record<string, any>;
}

const TestResultModal: React.FC<TestResultModalProps> = ({
  isOpen,
  onClose,
  nodeId,
  nodeTitle,
  nodeType
}) => {
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [selectedResult, setSelectedResult] = useState<TestResult | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadTestResults();
    }
  }, [isOpen, nodeId]);

  const loadTestResults = async () => {
    // Mock 테스트 결과 데이터
    const mockResults: TestResult[] = [
      {
        id: 'test_1',
        timestamp: new Date(Date.now() - 300000).toISOString(),
        status: 'success',
        input: { text: 'Hello, world!' },
        output: { response: 'Hello! How can I help you today?' },
        duration: 1250,
        metadata: { model: 'gpt-4', tokens: 45 }
      },
      {
        id: 'test_2',
        timestamp: new Date(Date.now() - 600000).toISOString(),
        status: 'error',
        input: { text: 'Test input with error' },
        output: null,
        error: 'API rate limit exceeded',
        duration: 500
      },
      {
        id: 'test_3',
        timestamp: new Date(Date.now() - 900000).toISOString(),
        status: 'success',
        input: { text: 'Another test message' },
        output: { response: 'This is a test response from the AI model.' },
        duration: 2100,
        metadata: { model: 'gpt-4', tokens: 67 }
      }
    ];
    setTestResults(mockResults);
  };

  const runTest = async () => {
    setIsRunningTest(true);
    
    // Mock 테스트 실행
    const newTest: TestResult = {
      id: `test_${Date.now()}`,
      timestamp: new Date().toISOString(),
      status: 'running',
      input: { text: 'Test input from manual run' },
      output: null
    };

    setTestResults(prev => [newTest, ...prev]);

    // 2초 후 결과 업데이트 (Mock)
    setTimeout(() => {
      const updatedTest: TestResult = {
        ...newTest,
        status: Math.random() > 0.3 ? 'success' : 'error',
        output: Math.random() > 0.3 ? { response: 'Test completed successfully!' } : null,
        error: Math.random() > 0.3 ? undefined : 'Random test error occurred',
        duration: Math.floor(Math.random() * 3000) + 500
      };

      setTestResults(prev => prev.map(test => 
        test.id === newTest.id ? updatedTest : test
      ));
      setIsRunningTest(false);
    }, 2000);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-6 w-6 text-green-600" />;
      case 'error':
        return <XCircle className="h-6 w-6 text-red-600" />;
      case 'running':
        return <Clock className="h-6 w-6 text-blue-600 animate-spin" />;
      default:
        return <AlertCircle className="h-6 w-6 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'error':
        return 'bg-red-50 border-red-200';
      case 'running':
        return 'bg-blue-50 border-blue-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const exportResults = () => {
    const dataStr = JSON.stringify(testResults, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `test-results-${nodeId}-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-[80vw] h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-8 border-b border-gray-200">
          <div className="flex items-center space-x-4">
            <Play className="h-8 w-8 text-blue-600" />
            <div>
              <h2 className="text-3xl font-bold text-gray-900">테스트 결과</h2>
              <p className="text-lg text-gray-600 mt-1">{nodeTitle} ({nodeType})</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={exportResults}
              className="flex items-center space-x-2 px-6 py-3 text-base font-semibold bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors shadow-sm"
            >
              <Download className="h-5 w-5" />
              <span>내보내기</span>
            </button>
            <button
              onClick={runTest}
              disabled={isRunningTest}
              className="flex items-center space-x-2 px-6 py-3 text-base font-semibold bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-lg"
            >
              <Play className="h-5 w-5" />
              <span>{isRunningTest ? '실행 중...' : '테스트 실행'}</span>
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors p-2 hover:bg-gray-100 rounded-full"
            >
              <X className="h-8 w-8" />
            </button>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Test Results List */}
          <div className="w-1/2 border-r border-gray-200 flex flex-col">
            <div className="p-8 border-b border-gray-200">
              <h3 className="text-2xl font-semibold text-gray-900 mb-2">테스트 기록</h3>
              <p className="text-lg text-gray-600">{testResults.length}개의 테스트 결과</p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-8 space-y-4">
              {testResults.map((result) => (
                <div
                  key={result.id}
                  onClick={() => setSelectedResult(result)}
                  className={`p-6 border-2 rounded-xl cursor-pointer transition-all ${
                    selectedResult?.id === result.id
                      ? 'border-blue-300 bg-blue-50 shadow-lg transform scale-[1.02]'
                      : `${getStatusColor(result.status)} hover:border-gray-300 hover:shadow-md`
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(result.status)}
                      <span className="text-base font-semibold text-gray-900">
                        {new Date(result.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {result.duration && (
                      <span className="text-sm text-gray-500 font-medium">{result.duration}ms</span>
                    )}
                  </div>
                  
                  <div className="text-base text-gray-600">
                    {result.status === 'success' && '✅ 성공'}
                    {result.status === 'error' && `❌ 오류: ${result.error}`}
                    {result.status === 'running' && '🔄 실행 중...'}
                  </div>
                </div>
              ))}
              
              {testResults.length === 0 && (
                <div className="text-center py-16 text-gray-500">
                  <AlertCircle className="h-16 w-16 mx-auto mb-4" />
                  <p className="text-xl mb-2">아직 테스트 결과가 없습니다.</p>
                  <p className="text-lg">테스트 실행 버튼을 클릭해보세요.</p>
                </div>
              )}
            </div>
          </div>

          {/* Test Result Detail */}
          <div className="w-1/2 flex flex-col">
            {selectedResult ? (
              <>
                <div className="p-8 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <h3 className="text-2xl font-semibold text-gray-900">테스트 상세</h3>
                    <button
                      onClick={() => copyToClipboard(JSON.stringify(selectedResult, null, 2))}
                      className="flex items-center space-x-2 px-4 py-2 text-base bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      <Copy className="h-4 w-4" />
                      <span>복사</span>
                    </button>
                  </div>
                </div>
                
                <div className="flex-1 overflow-y-auto p-8 space-y-6">
                  {/* Status */}
                  <div>
                    <label className="block text-lg font-semibold text-gray-700 mb-3">상태</label>
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(selectedResult.status)}
                      <span className="text-base font-medium">{selectedResult.status}</span>
                      {selectedResult.duration && (
                        <span className="text-sm text-gray-500">({selectedResult.duration}ms)</span>
                      )}
                    </div>
                  </div>

                  {/* Input */}
                  <div>
                    <label className="block text-lg font-semibold text-gray-700 mb-3">입력</label>
                    <pre className="bg-gray-50 p-6 rounded-xl text-sm font-mono overflow-x-auto border-2 border-gray-200 leading-relaxed">
                      {JSON.stringify(selectedResult.input, null, 2)}
                    </pre>
                  </div>

                  {/* Output */}
                  {selectedResult.output && (
                    <div>
                      <label className="block text-lg font-semibold text-gray-700 mb-3">출력</label>
                      <pre className="bg-gray-50 p-6 rounded-xl text-sm font-mono overflow-x-auto border-2 border-gray-200 leading-relaxed">
                        {JSON.stringify(selectedResult.output, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Error */}
                  {selectedResult.error && (
                    <div>
                      <label className="block text-lg font-semibold text-red-700 mb-3">오류</label>
                      <div className="bg-red-50 border-2 border-red-200 p-6 rounded-xl text-base text-red-800">
                        {selectedResult.error}
                      </div>
                    </div>
                  )}

                  {/* Metadata */}
                  {selectedResult.metadata && (
                    <div>
                      <label className="block text-lg font-semibold text-gray-700 mb-3">메타데이터</label>
                      <pre className="bg-gray-50 p-6 rounded-xl text-sm font-mono overflow-x-auto border-2 border-gray-200 leading-relaxed">
                        {JSON.stringify(selectedResult.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <AlertCircle className="h-16 w-16 mx-auto mb-4" />
                  <p className="text-xl">테스트 결과를 선택하세요</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TestResultModal; 