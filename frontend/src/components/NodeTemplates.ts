import React from 'react';
import { MessageSquare, FileText, Cpu, Database, Search, Bot, Cloud, Server } from 'lucide-react';

export interface NodeTemplate {
  id: string;
  type: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  category: 'input' | 'prompt' | 'model' | 'output' | 'rag';
  inputs: Array<{
    id: string;
    name: string;
    type: string;
    required?: boolean;
  }>;
  outputs: Array<{
    id: string;
    name: string;
    type: string;
  }>;
  fields: Array<{
    name: string;
    label: string;
    type: 'text' | 'textarea' | 'select' | 'slider' | 'toggle' | 'password' | 'number';
    value?: any;
    placeholder?: string;
    options?: Array<{ value: string; label: string }>;
    min?: number;
    max?: number;
    step?: number;
    rows?: number;
    required?: boolean;
    sensitive?: boolean;
  }>;
  color: string;
}

export const nodeTemplates: NodeTemplate[] = [
  // Chat Input
  {
    id: 'chat_input',
    type: 'ChatInput',
    title: 'Chat Input',
    description: 'Handles user chat input and conversation management',
    icon: React.createElement(MessageSquare, { className: 'h-4 w-4' }),
    category: 'input',
    inputs: [],
    outputs: [
      { id: 'text', name: 'Text', type: 'text' },
      { id: 'sender_name', name: 'Sender Name', type: 'text' }
    ],
    fields: [
      {
        name: 'placeholder',
        label: 'Placeholder',
        type: 'text',
        placeholder: 'Type your message...',
        value: 'Type your message...'
      },
      {
        name: 'sender_name',
        label: 'Sender Name',
        type: 'text',
        placeholder: 'User',
        value: 'User'
      }
    ],
    color: 'bg-blue-500'
  },

  // Prompt Template
  {
    id: 'prompt',
    type: 'Prompt',
    title: 'Prompt',
    description: 'Template for structuring prompts with variable interpolation',
    icon: React.createElement(FileText, { className: 'h-4 w-4' }),
    category: 'prompt',
    inputs: [
      { id: 'text', name: 'Text', type: 'text', required: true }
    ],
    outputs: [
      { id: 'prompt', name: 'Prompt', type: 'text' }
    ],
    fields: [
      {
        name: 'text',
        label: 'Input',
        type: 'textarea',
        placeholder: 'Enter input text...',
        rows: 2
      },
      {
        name: 'template',
        label: 'Template',
        type: 'textarea',
        placeholder: 'You are a helpful assistant. User: {text}\nAssistant:',
        value: 'You are a helpful assistant. User: {text}\nAssistant:',
        rows: 4,
        required: true
      }
    ],
    color: 'bg-purple-500'
  },

  // Azure OpenAI Model
  {
    id: 'azure_openai',
    type: 'AzureOpenAI',
    title: 'Azure OpenAI',
    description: 'Azure OpenAI GPT models for text generation',
    icon: React.createElement(Cloud, { className: 'h-4 w-4' }),
    category: 'model',
    inputs: [
      { id: 'prompt', name: 'Prompt', type: 'text', required: true },
      { id: 'system_message', name: 'System Message', type: 'text' }
    ],
    outputs: [
      { id: 'response', name: 'Response', type: 'text' },
      { id: 'usage', name: 'Usage', type: 'object' }
    ],
    fields: [
      {
        name: 'prompt',
        label: 'Input',
        type: 'textarea',
        placeholder: 'Enter your prompt...',
        rows: 2
      },
      {
        name: 'system_message',
        label: 'System Message',
        type: 'textarea',
        placeholder: 'You are a helpful assistant...',
        rows: 3
      },
      {
        name: 'stream',
        label: 'Stream',
        type: 'toggle',
        value: false
      },
      {
        name: 'model',
        label: 'Model Name',
        type: 'select',
        value: 'gpt-4o',
        options: [
          { value: 'gpt-4o', label: 'GPT-4o' },
          { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
          { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
          { value: 'gpt-35-turbo', label: 'GPT-3.5 Turbo' }
        ],
        required: true
      },
      {
        name: 'api_key',
        label: 'Azure OpenAI API Key',
        type: 'password',
        placeholder: 'Enter your Azure OpenAI API key',
        sensitive: true,
        required: true
      },
      {
        name: 'endpoint',
        label: 'Azure Endpoint',
        type: 'text',
        placeholder: 'https://your-resource.openai.azure.com',
        required: true
      },
      {
        name: 'temperature',
        label: 'Temperature',
        type: 'slider',
        value: 0.7,
        min: 0,
        max: 2,
        step: 0.1
      },
      {
        name: 'max_tokens',
        label: 'Max Tokens',
        type: 'number',
        value: 1000,
        min: 1,
        max: 4000
      }
    ],
    color: 'bg-green-500'
  },

  // DeepSeek R1 Model
  {
    id: 'deepseek_r1',
    type: 'DeepSeekR1',
    title: 'DeepSeek R1',
    description: 'DeepSeek R1 reasoning model for complex problem solving',
    icon: React.createElement(Bot, { className: 'h-4 w-4' }),
    category: 'model',
    inputs: [
      { id: 'prompt', name: 'Prompt', type: 'text', required: true },
      { id: 'system_message', name: 'System Message', type: 'text' }
    ],
    outputs: [
      { id: 'response', name: 'Response', type: 'text' },
      { id: 'reasoning', name: 'Reasoning', type: 'text' }
    ],
    fields: [
      {
        name: 'prompt',
        label: 'Input',
        type: 'textarea',
        placeholder: 'Enter your prompt...',
        rows: 2
      },
      {
        name: 'system_message',
        label: 'System Message',
        type: 'textarea',
        placeholder: 'You are a helpful reasoning assistant...',
        rows: 3
      },
      {
        name: 'api_key',
        label: 'DeepSeek API Key',
        type: 'password',
        placeholder: 'Enter your DeepSeek API key',
        sensitive: true,
        required: true
      },
      {
        name: 'temperature',
        label: 'Temperature',
        type: 'slider',
        value: 0.7,
        min: 0,
        max: 2,
        step: 0.1
      },
      {
        name: 'show_reasoning',
        label: 'Show Reasoning',
        type: 'toggle',
        value: true
      }
    ],
    color: 'bg-indigo-500'
  },

  // Anthropic Claude
  {
    id: 'anthropic_claude',
    type: 'AnthropicClaude',
    title: 'Anthropic Claude',
    description: 'Anthropic Claude models for intelligent conversations',
    icon: React.createElement(Cpu, { className: 'h-4 w-4' }),
    category: 'model',
    inputs: [
      { id: 'prompt', name: 'Prompt', type: 'text', required: true },
      { id: 'system_message', name: 'System Message', type: 'text' }
    ],
    outputs: [
      { id: 'response', name: 'Response', type: 'text' },
      { id: 'usage', name: 'Usage', type: 'object' }
    ],
    fields: [
      {
        name: 'prompt',
        label: 'Input',
        type: 'textarea',
        placeholder: 'Enter your prompt...',
        rows: 2
      },
      {
        name: 'system_message',
        label: 'System Message',
        type: 'textarea',
        placeholder: 'You are Claude, an AI assistant...',
        rows: 3
      },
      {
        name: 'model',
        label: 'Model Name',
        type: 'select',
        value: 'claude-3-5-sonnet-20241022',
        options: [
          { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
          { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' },
          { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' }
        ],
        required: true
      },
      {
        name: 'api_key',
        label: 'Anthropic API Key',
        type: 'password',
        placeholder: 'Enter your Anthropic API key',
        sensitive: true,
        required: true
      },
      {
        name: 'temperature',
        label: 'Temperature',
        type: 'slider',
        value: 0.7,
        min: 0,
        max: 1,
        step: 0.1
      },
      {
        name: 'max_tokens',
        label: 'Max Tokens',
        type: 'number',
        value: 1000,
        min: 1,
        max: 4000
      }
    ],
    color: 'bg-orange-500'
  },

  // Ollama Local Model
  {
    id: 'ollama',
    type: 'Ollama',
    title: 'Ollama',
    description: 'Local Ollama models for private AI inference',
    icon: React.createElement(Server, { className: 'h-4 w-4' }),
    category: 'model',
    inputs: [
      { id: 'prompt', name: 'Prompt', type: 'text', required: true },
      { id: 'system_message', name: 'System Message', type: 'text' }
    ],
    outputs: [
      { id: 'response', name: 'Response', type: 'text' }
    ],
    fields: [
      {
        name: 'prompt',
        label: 'Input',
        type: 'textarea',
        placeholder: 'Enter your prompt...',
        rows: 2
      },
      {
        name: 'system_message',
        label: 'System Message',
        type: 'textarea',
        placeholder: 'You are a helpful assistant...',
        rows: 3
      },
      {
        name: 'base_url',
        label: 'Ollama Base URL',
        type: 'text',
        value: 'http://localhost:11434',
        placeholder: 'http://localhost:11434',
        required: true
      },
      {
        name: 'model',
        label: 'Model Name',
        type: 'select',
        value: '',
        options: [],
        required: true
      },
      {
        name: 'temperature',
        label: 'Temperature',
        type: 'slider',
        value: 0.7,
        min: 0,
        max: 2,
        step: 0.1
      },
      {
        name: 'stream',
        label: 'Stream',
        type: 'toggle',
        value: false
      }
    ],
    color: 'bg-gray-600'
  },

  // Chat Output
  {
    id: 'chat_output',
    type: 'ChatOutput',
    title: 'Chat Output',
    description: 'Displays chat messages and conversation output',
    icon: React.createElement(MessageSquare, { className: 'h-4 w-4' }),
    category: 'output',
    inputs: [
      { id: 'text', name: 'Text', type: 'text', required: true },
      { id: 'sender_name', name: 'Sender Name', type: 'text' }
    ],
    outputs: [],
    fields: [
      {
        name: 'text',
        label: 'Input',
        type: 'textarea',
        placeholder: 'Message to display...',
        rows: 3
      },
      {
        name: 'sender_name',
        label: 'Sender Name',
        type: 'text',
        placeholder: 'Assistant',
        value: 'Assistant'
      },
      {
        name: 'show_timestamp',
        label: 'Show Timestamp',
        type: 'toggle',
        value: true
      },
      {
        name: 'auto_scroll',
        label: 'Auto Scroll',
        type: 'toggle',
        value: true
      }
    ],
    color: 'bg-blue-500'
  },

  // RAG (Chroma DB)
  {
    id: 'rag_chroma',
    type: 'RAGChroma',
    title: 'RAG (Chroma DB)',
    description: 'Retrieval-Augmented Generation using Chroma vector database',
    icon: React.createElement(Database, { className: 'h-4 w-4' }),
    category: 'rag',
    inputs: [
      { id: 'query', name: 'Query', type: 'text', required: true }
    ],
    outputs: [
      { id: 'context', name: 'Context', type: 'text' },
      { id: 'documents', name: 'Documents', type: 'array' },
      { id: 'metadata', name: 'Metadata', type: 'object' }
    ],
    fields: [
      {
        name: 'query',
        label: 'Query',
        type: 'textarea',
        placeholder: 'Enter search query...',
        rows: 2
      },
      {
        name: 'collection_name',
        label: 'Collection Name',
        type: 'select',
        placeholder: 'Select RAG collection...',
        options: [
          { value: 'user_documents', label: 'My Documents' },
          { value: 'shared_knowledge', label: 'Shared Knowledge Base' },
          { value: 'company_docs', label: 'Company Documents' }
        ],
        required: true
      },
      {
        name: 'n_results',
        label: 'Number of Results',
        type: 'number',
        value: 5,
        min: 1,
        max: 20
      },
      {
        name: 'similarity_threshold',
        label: 'Similarity Threshold',
        type: 'slider',
        value: 0.7,
        min: 0,
        max: 1,
        step: 0.1
      },
      {
        name: 'include_metadata',
        label: 'Include Metadata',
        type: 'toggle',
        value: true
      }
    ],
    color: 'bg-emerald-500'
  }
];

export const getNodeTemplateById = (id: string): NodeTemplate | undefined => {
  return nodeTemplates.find(template => template.id === id);
}; 