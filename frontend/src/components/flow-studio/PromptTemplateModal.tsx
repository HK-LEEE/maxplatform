import React, { useState, useEffect } from 'react';
import { X, Wand2, Copy, Check } from 'lucide-react';

interface PromptTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTemplate: (template: string) => void;
  availableParameters: string[];
  currentTemplate?: string;
}

interface TemplateOption {
  id: string;
  name: string;
  description: string;
  template: string;
  category: string;
}

const templateOptions: TemplateOption[] = [
  {
    id: 'assistant',
    name: '기본 어시스턴트',
    description: '일반적인 AI 어시스턴트 역할',
    template: 'You are a helpful AI assistant. Please respond to the user\'s question clearly and accurately.\n\nUser: {text}\nAssistant:',
    category: 'general'
  },
  {
    id: 'expert',
    name: '전문가 역할',
    description: '특정 분야의 전문가로 답변',
    template: 'You are an expert in {domain}. Please provide detailed and professional advice on the following topic.\n\nQuestion: {text}\nExpert Response:',
    category: 'professional'
  },
  {
    id: 'translator',
    name: '번역가',
    description: '언어 번역 전문',
    template: 'You are a professional translator. Translate the following text from {source_language} to {target_language}. Maintain the original meaning and tone.\n\nText to translate: {text}\nTranslation:',
    category: 'language'
  },
  {
    id: 'summarizer',
    name: '요약 전문가',
    description: '텍스트 요약 및 핵심 추출',
    template: 'You are a text summarization expert. Please provide a concise summary of the following content, highlighting the key points.\n\nContent: {text}\nSummary:',
    category: 'analysis'
  },
  {
    id: 'coder',
    name: '코딩 어시스턴트',
    description: '프로그래밍 도움',
    template: 'You are an experienced software developer. Help the user with their coding question or problem. Provide clear explanations and working code examples.\n\nProgramming Language: {language}\nQuestion: {text}\nSolution:',
    category: 'technical'
  },
  {
    id: 'creative',
    name: '창작 도우미',
    description: '창의적 글쓰기 지원',
    template: 'You are a creative writing assistant. Help the user create engaging and original content based on their request.\n\nGenre/Style: {style}\nRequest: {text}\nCreative Response:',
    category: 'creative'
  }
];

const PromptTemplateModal: React.FC<PromptTemplateModalProps> = ({
  isOpen,
  onClose,
  onSelectTemplate,
  availableParameters,
  currentTemplate = ''
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateOption | null>(null);
  const [customTemplate, setCustomTemplate] = useState(currentTemplate);
  const [copiedTemplate, setCopiedTemplate] = useState<string | null>(null);

  useEffect(() => {
    setCustomTemplate(currentTemplate);
  }, [currentTemplate]);

  if (!isOpen) return null;

  const categories = [
    { id: 'all', name: '전체' },
    { id: 'general', name: '일반' },
    { id: 'professional', name: '전문가' },
    { id: 'language', name: '언어' },
    { id: 'analysis', name: '분석' },
    { id: 'technical', name: '기술' },
    { id: 'creative', name: '창작' }
  ];

  const filteredTemplates = selectedCategory === 'all' 
    ? templateOptions 
    : templateOptions.filter(t => t.category === selectedCategory);

  const handleTemplateSelect = (template: TemplateOption) => {
    setSelectedTemplate(template);
    setCustomTemplate(template.template);
  };

  const handleCopyTemplate = (template: string, templateId: string) => {
    setCustomTemplate(template);
    setCopiedTemplate(templateId);
    setTimeout(() => setCopiedTemplate(null), 2000);
  };

  const handleApplyTemplate = () => {
    onSelectTemplate(customTemplate);
    onClose();
  };

  const insertParameter = (parameter: string) => {
    const textarea = document.getElementById('custom-template') as HTMLTextAreaElement;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newValue = customTemplate.substring(0, start) + `{${parameter}}` + customTemplate.substring(end);
      setCustomTemplate(newValue);
      
      // 커서 위치 조정
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(start + parameter.length + 2, start + parameter.length + 2);
      }, 0);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-[80vw] h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-8 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <Wand2 className="h-8 w-8 text-purple-600" />
            <h2 className="text-3xl font-bold text-gray-900">프롬프트 템플릿 생성기</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors p-2 hover:bg-gray-100 rounded-full"
          >
            <X className="h-8 w-8" />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Left Panel - Template Library */}
          <div className="w-2/5 border-r border-gray-200 flex flex-col">
            <div className="p-8 border-b border-gray-200">
              <h3 className="text-2xl font-semibold text-gray-900 mb-6">템플릿 라이브러리</h3>
              
              {/* Category Filter */}
              <div className="flex flex-wrap gap-3 mb-6">
                {categories.map(category => (
                  <button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    className={`px-6 py-3 rounded-full text-base font-semibold transition-all ${
                      selectedCategory === category.id
                        ? 'bg-purple-100 text-purple-700 border-2 border-purple-300 shadow-md'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border-2 border-transparent'
                    }`}
                  >
                    {category.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Template List */}
            <div className="flex-1 overflow-y-auto p-8 space-y-6">
              {filteredTemplates.map(template => (
                <div
                  key={template.id}
                  className={`p-6 border-2 rounded-xl cursor-pointer transition-all ${
                    selectedTemplate?.id === template.id
                      ? 'border-purple-300 bg-purple-50 shadow-lg transform scale-[1.02]'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 hover:shadow-md'
                  }`}
                  onClick={() => handleTemplateSelect(template)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-bold text-gray-900 text-xl mb-3">{template.name}</h4>
                      <p className="text-base text-gray-600 leading-relaxed">{template.description}</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCopyTemplate(template.template, template.id);
                      }}
                      className="ml-4 p-3 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                    >
                      {copiedTemplate === template.id ? (
                        <Check className="h-6 w-6 text-green-600" />
                      ) : (
                        <Copy className="h-6 w-6" />
                      )}
                    </button>
                  </div>
                  
                  {/* Template Preview */}
                  <div className="mt-5 p-4 bg-gray-100 rounded-lg text-base text-gray-700 font-mono leading-relaxed">
                    {template.template.substring(0, 200)}...
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Panel - Template Editor */}
          <div className="w-3/5 flex flex-col">
            <div className="p-8 border-b border-gray-200">
              <h3 className="text-2xl font-semibold text-gray-900 mb-6">템플릿 편집기</h3>
              
              {/* Available Parameters */}
              {availableParameters.length > 0 && (
                <div className="mb-6">
                  <label className="block text-lg font-semibold text-gray-700 mb-4">
                    사용 가능한 파라미터 (클릭하여 삽입)
                  </label>
                  <div className="flex flex-wrap gap-3">
                    {availableParameters.map(param => (
                      <button
                        key={param}
                        onClick={() => insertParameter(param)}
                        className="px-4 py-3 bg-blue-100 text-blue-700 rounded-lg text-base font-semibold hover:bg-blue-200 transition-colors shadow-sm"
                      >
                        {param}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Template Editor */}
            <div className="flex-1 p-8">
              <label className="block text-lg font-semibold text-gray-700 mb-4">
                커스텀 템플릿
              </label>
              <textarea
                id="custom-template"
                value={customTemplate}
                onChange={(e) => setCustomTemplate(e.target.value)}
                placeholder="여기에 프롬프트 템플릿을 작성하세요..."
                className="w-full h-full resize-none border-2 border-gray-300 rounded-xl p-6 text-base font-mono leading-relaxed focus:ring-4 focus:ring-purple-500 focus:border-purple-500 transition-all"
              />
            </div>

            {/* Footer */}
            <div className="p-8 border-t border-gray-200 flex justify-end space-x-4">
              <button
                onClick={onClose}
                className="px-8 py-3 text-lg font-semibold text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleApplyTemplate}
                className="px-8 py-3 text-lg font-semibold bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-colors shadow-lg"
              >
                템플릿 적용
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PromptTemplateModal; 