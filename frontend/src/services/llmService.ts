// LLM Service for handling multiple AI providers
export interface LLMMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface LLMResponse {
  content: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  model: string;
  provider: string;
}

export interface LLMConfig {
  provider: 'openai' | 'azure_openai' | 'deepseek' | 'anthropic' | 'ollama';
  model: string;
  apiKey?: string;
  baseURL?: string;
  temperature?: number;
  maxTokens?: number;
  [key: string]: any;
}

class LLMService {
  private configs: Map<string, LLMConfig> = new Map();

  // 모델 설정 등록
  registerModel(id: string, config: LLMConfig) {
    this.configs.set(id, config);
  }

  // OpenAI API 호출
  private async callOpenAI(config: LLMConfig, messages: LLMMessage[]): Promise<LLMResponse> {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`
      },
      body: JSON.stringify({
        model: config.model,
        messages,
        temperature: config.temperature || 0.7,
        max_tokens: config.maxTokens || 1000
      })
    });

    if (!response.ok) {
      throw new Error(`OpenAI API 오류: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return {
      content: data.choices[0].message.content,
      usage: data.usage,
      model: config.model,
      provider: 'openai'
    };
  }

  // Azure OpenAI API 호출
  private async callAzureOpenAI(config: LLMConfig, messages: LLMMessage[]): Promise<LLMResponse> {
    const { endpoint, apiVersion = '2024-02-15-preview' } = config;
    const url = `${endpoint}/openai/deployments/${config.model}/chat/completions?api-version=${apiVersion}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'api-key': config.apiKey!
      },
      body: JSON.stringify({
        messages,
        temperature: config.temperature || 0.7,
        max_tokens: config.maxTokens || 1000
      })
    });

    if (!response.ok) {
      throw new Error(`Azure OpenAI API 오류: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return {
      content: data.choices[0].message.content,
      usage: data.usage,
      model: config.model,
      provider: 'azure_openai'
    };
  }

  // DeepSeek API 호출
  private async callDeepSeek(config: LLMConfig, messages: LLMMessage[]): Promise<LLMResponse> {
    const response = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`
      },
      body: JSON.stringify({
        model: config.model,
        messages,
        temperature: config.temperature || 0.7,
        max_tokens: config.maxTokens || 1000,
        stream: false
      })
    });

    if (!response.ok) {
      throw new Error(`DeepSeek API 오류: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return {
      content: data.choices[0].message.content,
      usage: data.usage,
      model: config.model,
      provider: 'deepseek'
    };
  }

  // Anthropic API 호출
  private async callAnthropic(config: LLMConfig, messages: LLMMessage[]): Promise<LLMResponse> {
    // Anthropic은 메시지 형식이 다름
    const systemMessage = messages.find(m => m.role === 'system');
    const conversationMessages = messages.filter(m => m.role !== 'system');

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': config.apiKey!,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: config.model,
        max_tokens: config.maxTokens || 1000,
        system: systemMessage?.content,
        messages: conversationMessages.map(m => ({
          role: m.role === 'assistant' ? 'assistant' : 'user',
          content: m.content
        }))
      })
    });

    if (!response.ok) {
      throw new Error(`Anthropic API 오류: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return {
      content: data.content[0].text,
      usage: {
        prompt_tokens: data.usage.input_tokens,
        completion_tokens: data.usage.output_tokens,
        total_tokens: data.usage.input_tokens + data.usage.output_tokens
      },
      model: config.model,
      provider: 'anthropic'
    };
  }

  // Ollama API 호출
  private async callOllama(config: LLMConfig, messages: LLMMessage[]): Promise<LLMResponse> {
    const baseURL = config.baseURL || 'http://localhost:11434';
    
    const response = await fetch(`${baseURL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: config.model,
        messages,
        stream: false,
        options: {
          temperature: config.temperature || 0.7,
          num_predict: config.maxTokens || 1000
        }
      })
    });

    if (!response.ok) {
      throw new Error(`Ollama API 오류: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return {
      content: data.message.content,
      model: config.model,
      provider: 'ollama'
    };
  }

  // 통합 LLM 호출 메서드
  async generateResponse(modelId: string, messages: LLMMessage[]): Promise<LLMResponse> {
    const config = this.configs.get(modelId);
    if (!config) {
      throw new Error(`모델 설정을 찾을 수 없습니다: ${modelId}`);
    }

    try {
      switch (config.provider) {
        case 'openai':
          return await this.callOpenAI(config, messages);
        case 'azure_openai':
          return await this.callAzureOpenAI(config, messages);
        case 'deepseek':
          return await this.callDeepSeek(config, messages);
        case 'anthropic':
          return await this.callAnthropic(config, messages);
        case 'ollama':
          return await this.callOllama(config, messages);
        default:
          throw new Error(`지원하지 않는 프로바이더: ${config.provider}`);
      }
    } catch (error) {
      console.error(`LLM 호출 실패 (${modelId}):`, error);
      throw error;
    }
  }

  // 사용 가능한 모델 목록 반환
  getAvailableModels(): Array<{ id: string; config: LLMConfig }> {
    return Array.from(this.configs.entries()).map(([id, config]) => ({ id, config }));
  }

  // 모델 설정 업데이트
  updateModelConfig(modelId: string, updates: Partial<LLMConfig>) {
    const existing = this.configs.get(modelId);
    if (existing) {
      this.configs.set(modelId, { ...existing, ...updates });
    }
  }

  // 모델 제거
  removeModel(modelId: string) {
    this.configs.delete(modelId);
  }

  // 모델 연결 테스트
  async testConnection(modelId: string): Promise<boolean> {
    try {
      const testMessages: LLMMessage[] = [
        { role: 'user', content: '안녕하세요. 연결 테스트입니다.' }
      ];
      
      await this.generateResponse(modelId, testMessages);
      return true;
    } catch (error) {
      console.error(`연결 테스트 실패 (${modelId}):`, error);
      return false;
    }
  }
}

// 싱글톤 인스턴스
export const llmService = new LLMService();

// 기본 모델 설정들
export const defaultModelConfigs = {
  'gpt-4o': {
    provider: 'openai' as const,
    model: 'gpt-4o',
    temperature: 0.7,
    maxTokens: 2000
  },
  'gpt-4o-mini': {
    provider: 'openai' as const,
    model: 'gpt-4o-mini',
    temperature: 0.7,
    maxTokens: 2000
  },
  'deepseek-r1': {
    provider: 'deepseek' as const,
    model: 'deepseek-r1',
    temperature: 0.7,
    maxTokens: 2000
  },
  'claude-3-5-sonnet': {
    provider: 'anthropic' as const,
    model: 'claude-3-5-sonnet-20241022',
    temperature: 0.7,
    maxTokens: 2000
  },
  'llama3.2': {
    provider: 'ollama' as const,
    model: 'llama3.2',
    temperature: 0.7,
    maxTokens: 2000,
    baseURL: 'http://localhost:11434'
  }
};

// 플로우 실행 엔진
export class FlowExecutionEngine {
  private llmService: LLMService;

  constructor(llmService: LLMService) {
    this.llmService = llmService;
  }

  // 플로우 실행
  async executeFlow(nodes: any[], edges: any[], input: string): Promise<{
    result: string;
    steps: Array<{ nodeId: string; output: string; model?: string }>;
  }> {
    const steps: Array<{ nodeId: string; output: string; model?: string }> = [];
    
    // 노드별 출력 데이터 저장
    const nodeOutputs = new Map<string, any>();
    
    // 노드를 실행 순서대로 정렬
    const sortedNodes = this.topologicalSort(nodes, edges);

    for (const node of sortedNodes) {
      const nodeData = node.data;
      
      // 현재 노드의 입력 데이터 수집
      const nodeInputs = this.collectNodeInputs(node.id, edges, nodeOutputs);
      
      switch (nodeData.category) {
        case 'input':
          // 입력 노드: 초기 입력값 설정
          const inputValue = nodeData.fieldValues?.default_value || input;
          nodeOutputs.set(node.id, { text: inputValue });
          
          steps.push({
            nodeId: node.id,
            output: `입력 수신: "${inputValue}"`
          });
          break;

        case 'prompt':
          // 프롬프트 노드: 템플릿 처리
          const promptTemplate = nodeData.fieldValues?.template || '';
          const promptInput = nodeInputs.text || nodeInputs.prompt || '';
          const processedPrompt = this.processPromptTemplate(promptTemplate, { 
            input: promptInput,
            text: promptInput 
          });
          
          nodeOutputs.set(node.id, { text: processedPrompt });
          
          steps.push({
            nodeId: node.id,
            output: `프롬프트 처리 완료: "${processedPrompt}"`
          });
          break;

        case 'model':
          try {
            const modelId = this.getModelIdFromNode(nodeData);
            
            // 모델 입력 데이터 준비
            const promptInput = nodeInputs.prompt || nodeInputs.text || '';
            const systemMessage = nodeData.fieldValues?.system_message || '';
            
            // 동적으로 모델 설정 생성 및 등록
            if (nodeData.type === 'Ollama') {
              const baseUrl = nodeData.fieldValues?.base_url || 'http://localhost:11434';
              const temperature = nodeData.fieldValues?.temperature || 0.7;
              const model = nodeData.fieldValues?.model;
              
              if (!model) {
                throw new Error('Ollama 모델이 선택되지 않았습니다');
              }
              
              const ollamaConfig: LLMConfig = {
                provider: 'ollama',
                model: model,
                baseURL: baseUrl,
                temperature: temperature,
                maxTokens: 1000
              };
              
              this.llmService.registerModel(modelId, ollamaConfig);
              
            } else if (nodeData.type === 'AzureOpenAI') {
              const endpoint = nodeData.fieldValues?.endpoint;
              const apiKey = nodeData.fieldValues?.api_key;
              const model = nodeData.fieldValues?.model || 'gpt-4o';
              const temperature = nodeData.fieldValues?.temperature || 0.7;
              
              if (!endpoint || !apiKey) {
                throw new Error('Azure OpenAI 엔드포인트와 API 키가 필요합니다');
              }
              
              const azureConfig: LLMConfig = {
                provider: 'azure_openai',
                model: model,
                apiKey: apiKey,
                baseURL: endpoint,
                temperature: temperature,
                maxTokens: 2000
              };
              
              this.llmService.registerModel(modelId, azureConfig);
              
            } else if (nodeData.type === 'AnthropicClaude') {
              const apiKey = nodeData.fieldValues?.api_key;
              const model = nodeData.fieldValues?.model || 'claude-3-5-sonnet-20241022';
              const temperature = nodeData.fieldValues?.temperature || 0.7;
              const maxTokens = nodeData.fieldValues?.max_tokens || 1000;
              
              if (!apiKey) {
                throw new Error('Anthropic API 키가 필요합니다');
              }
              
              const anthropicConfig: LLMConfig = {
                provider: 'anthropic',
                model: model,
                apiKey: apiKey,
                temperature: temperature,
                maxTokens: maxTokens
              };
              
              this.llmService.registerModel(modelId, anthropicConfig);
            }
            
            // 메시지 구성
            const messages: LLMMessage[] = [];
            if (systemMessage) {
              messages.push({ role: 'system', content: systemMessage });
            }
            messages.push({ role: 'user', content: promptInput });

            const response = await this.llmService.generateResponse(modelId, messages);
            
            // 모델 출력 저장
            nodeOutputs.set(node.id, { 
              response: response.content,
              text: response.content,
              usage: response.usage 
            });
            
            steps.push({
              nodeId: node.id,
              output: `AI 응답: "${response.content}"`,
              model: `${response.provider}/${response.model}`
            });
          } catch (error) {
            const errorMsg = `모델 실행 오류: ${error instanceof Error ? error.message : '알 수 없는 오류'}`;
            nodeOutputs.set(node.id, { 
              response: errorMsg,
              text: errorMsg,
              error: true 
            });
            
            steps.push({
              nodeId: node.id,
              output: errorMsg
            });
          }
          break;

        case 'rag':
          // RAG 처리
          const queryInput = nodeInputs.query || nodeInputs.text || '';
          const ragResult = await this.processRAG(nodeData, queryInput);
          
          nodeOutputs.set(node.id, { 
            context: ragResult,
            text: ragResult,
            documents: [],
            metadata: {}
          });
          
          steps.push({
            nodeId: node.id,
            output: `RAG 검색 완료: "${ragResult}"`
          });
          break;

        case 'output':
          // 출력 노드: 최종 결과
          const outputValue = nodeInputs.text || nodeInputs.response || '';
          nodeOutputs.set(node.id, { text: outputValue });
          
          steps.push({
            nodeId: node.id,
            output: `최종 출력: "${outputValue}"`
          });
          break;
      }
    }

    // 최종 결과 찾기 (output 카테고리 노드 또는 마지막 노드)
    const outputNode = sortedNodes.find(node => node.data.category === 'output');
    const finalNodeId = outputNode?.id || sortedNodes[sortedNodes.length - 1]?.id;
    const finalResult = nodeOutputs.get(finalNodeId)?.text || '';

    return {
      result: finalResult,
      steps
    };
  }

  // 노드의 입력 데이터 수집
  private collectNodeInputs(nodeId: string, edges: any[], nodeOutputs: Map<string, any>): any {
    const inputs: any = {};
    
    // 현재 노드로 들어오는 엣지들 찾기
    const incomingEdges = edges.filter(edge => edge.target === nodeId);
    
    console.log(`[FlowEngine] 노드 ${nodeId}의 입력 수집:`, {
      incomingEdges: incomingEdges.length,
      edges: incomingEdges.map(e => ({ from: e.source, to: e.target, sourceHandle: e.sourceHandle, targetHandle: e.targetHandle }))
    });
    
    for (const edge of incomingEdges) {
      const sourceNodeId = edge.source;
      const sourceOutput = nodeOutputs.get(sourceNodeId);
      
      console.log(`[FlowEngine] 엣지 처리: ${sourceNodeId} -> ${nodeId}`, {
        sourceOutput,
        sourceHandle: edge.sourceHandle,
        targetHandle: edge.targetHandle
      });
      
      if (sourceOutput) {
        // 엣지의 sourceHandle과 targetHandle을 고려하여 데이터 매핑
        const sourceHandle = edge.sourceHandle || 'text';
        const targetHandle = edge.targetHandle || 'text';
        
        if (sourceOutput[sourceHandle] !== undefined) {
          inputs[targetHandle] = sourceOutput[sourceHandle];
          console.log(`[FlowEngine] 데이터 매핑: ${sourceHandle} -> ${targetHandle}`, sourceOutput[sourceHandle]);
        } else {
          // 기본값으로 text 또는 response 사용
          const fallbackValue = sourceOutput.text || sourceOutput.response || '';
          inputs[targetHandle] = fallbackValue;
          console.log(`[FlowEngine] 기본값 사용: ${targetHandle}`, fallbackValue);
        }
      }
    }
    
    console.log(`[FlowEngine] 노드 ${nodeId}의 최종 입력:`, inputs);
    return inputs;
  }

  // 토폴로지 정렬 (노드 실행 순서 결정)
  private topologicalSort(nodes: any[], edges: any[]): any[] {
    const inDegree = new Map<string, number>();
    const graph = new Map<string, string[]>();
    const nodeMap = new Map<string, any>();

    // 초기화
    nodes.forEach(node => {
      inDegree.set(node.id, 0);
      graph.set(node.id, []);
      nodeMap.set(node.id, node);
    });

    // 그래프 구성
    edges.forEach(edge => {
      const from = edge.source;
      const to = edge.target;
      
      graph.get(from)?.push(to);
      inDegree.set(to, (inDegree.get(to) || 0) + 1);
    });

    // 토폴로지 정렬
    const queue: string[] = [];
    const result: any[] = [];

    // 진입 차수가 0인 노드들을 큐에 추가
    inDegree.forEach((degree, nodeId) => {
      if (degree === 0) {
        queue.push(nodeId);
      }
    });

    while (queue.length > 0) {
      const current = queue.shift()!;
      result.push(nodeMap.get(current));

      // 인접 노드들의 진입 차수 감소
      graph.get(current)?.forEach(neighbor => {
        const newDegree = (inDegree.get(neighbor) || 0) - 1;
        inDegree.set(neighbor, newDegree);
        
        if (newDegree === 0) {
          queue.push(neighbor);
        }
      });
    }

    // 사이클이 있는 경우 원래 순서 반환
    if (result.length !== nodes.length) {
      console.warn('플로우에 사이클이 감지되었습니다. 원래 순서로 실행합니다.');
      return nodes;
    }

    return result;
  }

  // 프롬프트 템플릿 처리
  private processPromptTemplate(template: string, variables: Record<string, any>): string {
    let processed = template;
    
    Object.entries(variables).forEach(([key, value]) => {
      const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g');
      processed = processed.replace(regex, String(value));
    });

    return processed;
  }

  // 노드에서 모델 ID 추출
  private getModelIdFromNode(nodeData: any): string {
    // fieldValues에서 먼저 확인, 없으면 fields에서 확인
    const modelValue = nodeData.fieldValues?.model || 
                      nodeData.fields?.find((f: any) => f.name === 'model')?.value;
    return modelValue || nodeData.id;
  }

  // RAG 처리 (시뮬레이션)
  private async processRAG(nodeData: any, query: string): Promise<string> {
    // 실제 구현에서는 Chroma DB나 다른 벡터 DB와 연동
    const collection = nodeData.fieldValues?.collection || 
                      nodeData.fields?.find((f: any) => f.name === 'collection')?.value || 'default';
    const topK = nodeData.fieldValues?.top_k || 
                nodeData.fields?.find((f: any) => f.name === 'top_k')?.value || 3;
    
    // 시뮬레이션된 검색 결과
    const mockResults = [
      `[문서 1] ${query}와 관련된 정보입니다.`,
      `[문서 2] ${query}에 대한 추가 컨텍스트입니다.`,
      `[문서 3] ${query}와 연관된 참고 자료입니다.`
    ].slice(0, topK);

    return `RAG 검색 결과 (컬렉션: ${collection}):\n${mockResults.join('\n')}`;
  }
} 