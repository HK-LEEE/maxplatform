import React, { useState } from 'react';
import { llmChatApi } from '../services/llmChatApi';
import { ModelType, OwnerType, LLMModelManagement, LLMModelCreate } from '../types/llmChat';

interface ModelModalProps {
  showModal: boolean;
  setShowModal: (show: boolean) => void;
  isEditing: boolean;
  selectedModel: LLMModelManagement | null;
  editedModelInfo: {
    model_name: string;
    model_type: ModelType;
    model_id: string;
    description: string;
    config: any;
    owner_type: OwnerType;
    owner_id: string;
    is_active: boolean;
  };
  setEditedModelInfo: (info: any) => void;
  onSave: () => void;
}

const ModelModal: React.FC<ModelModalProps> = ({
  showModal,
  setShowModal,
  isEditing,
  selectedModel,
  editedModelInfo,
  setEditedModelInfo,
  onSave
}) => {
  // Ollama 관련 상태
  const [ollamaModels, setOllamaModels] = useState<any[]>([]);
  const [ollamaLoading, setOllamaLoading] = useState(false);
  const [ollamaHost, setOllamaHost] = useState('localhost');
  const [ollamaPort, setOllamaPort] = useState(11434);

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

  if (!showModal) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl mx-4 border border-gray-100">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            {isEditing ? '모델 편집' : '새 모델 추가'}
          </h3>
        </div>
        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          {/* 기본 정보 */}
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
            <label className="block text-sm font-medium text-gray-700 mb-1">설명</label>
            <textarea
              value={editedModelInfo.description}
              onChange={(e) => setEditedModelInfo({...editedModelInfo, description: e.target.value})}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
              rows={2}
              placeholder="모델에 대한 설명을 입력하세요"
            />
          </div>

          {/* 소유자 정보 */}
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

            {/* 다른 모델 타입들도 비슷하게 구현 */}
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
            onClick={() => setShowModal(false)}
            className="px-4 py-2 text-gray-700 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
          >
            취소
          </button>
          <button
            onClick={onSave}
            className="px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
          >
            {isEditing ? '수정' : '생성'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModelModal; 