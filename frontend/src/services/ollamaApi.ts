interface OllamaModel {
  name: string;
  model: string;
  modified_at: string;
  size: number;
  digest: string;
  details?: {
    parent_model?: string;
    format?: string;
    family?: string;
    families?: string[];
    parameter_size?: string;
    quantization_level?: string;
  };
}

interface OllamaModelsResponse {
  models: OllamaModel[];
}

class OllamaApiService {
  /**
   * Ollama 서버에서 사용 가능한 모델 목록을 가져옵니다.
   */
  async getModels(baseUrl: string): Promise<OllamaModel[]> {
    try {
      // URL 정규화 (끝에 슬래시 제거)
      const normalizedUrl = baseUrl.replace(/\/$/, '');
      
      const response = await fetch(`${normalizedUrl}/api/tags`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: OllamaModelsResponse = await response.json();
      return data.models || [];
    } catch (error) {
      console.error('Failed to fetch Ollama models:', error);
      throw error;
    }
  }

  /**
   * Ollama 서버 연결 상태를 확인합니다.
   */
  async checkConnection(baseUrl: string): Promise<boolean> {
    try {
      const normalizedUrl = baseUrl.replace(/\/$/, '');
      const response = await fetch(`${normalizedUrl}/api/tags`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      return response.ok;
    } catch (error) {
      console.error('Ollama connection check failed:', error);
      return false;
    }
  }

  /**
   * 모델 이름을 사용자 친화적인 형태로 변환합니다.
   */
  formatModelName(modelName: string): string {
    // 모델 이름에서 태그 제거 (예: llama3.2:latest -> llama3.2)
    const baseName = modelName.split(':')[0];
    
    // 일반적인 모델 이름 매핑
    const modelNameMap: Record<string, string> = {
      'llama3.2': 'Llama 3.2',
      'llama3.1': 'Llama 3.1', 
      'llama3': 'Llama 3',
      'llama2': 'Llama 2',
      'mistral': 'Mistral',
      'codellama': 'Code Llama',
      'gemma2': 'Gemma 2',
      'gemma': 'Gemma',
      'qwen2.5': 'Qwen 2.5',
      'qwen2': 'Qwen 2',
      'qwen': 'Qwen',
      'phi3': 'Phi-3',
      'phi': 'Phi',
      'deepseek-coder': 'DeepSeek Coder',
      'deepseek': 'DeepSeek',
      'nomic-embed-text': 'Nomic Embed Text',
      'all-minilm': 'All-MiniLM'
    };

    return modelNameMap[baseName] || baseName.charAt(0).toUpperCase() + baseName.slice(1);
  }
}

export const ollamaApi = new OllamaApiService();
export type { OllamaModel }; 