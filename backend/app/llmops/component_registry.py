"""
Component Registry for LLMOps

모든 커스텀 컴포넌트를 관리하는 중앙화된 레지스트리
동적으로 컴포넌트 클래스를 로드하고 인스턴스화하는 기능을 제공
"""

import importlib
import logging
from typing import Dict, Type, Any

logger = logging.getLogger(__name__)

# 컴포넌트 타입 문자열과 클래스 경로를 매핑하는 레지스트리
COMPONENT_REGISTRY: Dict[str, str] = {
    "ChatInput": "app.llmops.components.chat_input.ChatInputComponent",
    "Prompt": "app.llmops.components.prompt.PromptComponent",
    "AzureOpenAI": "app.llmops.components.azure_openai.AzureOpenAIComponent",
    "Ollama": "app.llmops.components.ollama.OllamaComponent",
    "RAGChroma": "app.llmops.components.rag_chroma.RAGChromaComponent",
    "ChatOutput": "app.llmops.components.chat_output.ChatOutputComponent"
}


def get_component_class(component_type: str) -> Type[Any]:
    """
    컴포넌트 타입 문자열로부터 해당 컴포넌트 클래스를 동적으로 로드합니다.
    
    Args:
        component_type: 컴포넌트 타입 문자열 (예: "AzureOpenAI", "Prompt")
        
    Returns:
        해당 컴포넌트의 클래스 객체 (인스턴스가 아닌 클래스 자체)
        
    Raises:
        ValueError: 지원하지 않는 컴포넌트 타입인 경우
        ImportError: 컴포넌트 모듈을 가져올 수 없는 경우
        AttributeError: 컴포넌트 클래스가 모듈에 존재하지 않는 경우
        
    Examples:
        >>> prompt_class = get_component_class("Prompt")
        >>> prompt_instance = prompt_class()
        >>> runnable = prompt_instance.get_runnable(node_data)
    """
    if component_type not in COMPONENT_REGISTRY:
        available_types = ", ".join(COMPONENT_REGISTRY.keys())
        raise ValueError(
            f"지원하지 않는 컴포넌트 타입: '{component_type}'. "
            f"지원되는 타입: {available_types}"
        )
    
    class_path = COMPONENT_REGISTRY[component_type]
    
    try:
        # 클래스 경로를 모듈 경로와 클래스 이름으로 분리
        module_path, class_name = class_path.rsplit('.', 1)
        
        # 모듈 동적 임포트
        module = importlib.import_module(module_path)
        
        # 클래스 객체 가져오기
        component_class = getattr(module, class_name)
        
        logger.info(f"컴포넌트 클래스 로드 완료: {component_type} -> {class_path}")
        return component_class
        
    except ImportError as e:
        logger.error(f"컴포넌트 모듈 임포트 실패: {class_path} - {e}")
        raise ImportError(f"컴포넌트 모듈을 가져올 수 없습니다: {class_path}") from e
        
    except AttributeError as e:
        logger.error(f"컴포넌트 클래스를 찾을 수 없음: {class_name} in {module_path} - {e}")
        raise AttributeError(f"컴포넌트 클래스가 모듈에 존재하지 않습니다: {class_name}") from e


def register_component(component_type: str, class_path: str) -> None:
    """
    새로운 컴포넌트 타입을 레지스트리에 등록합니다.
    
    Args:
        component_type: 컴포넌트 타입 문자열
        class_path: 컴포넌트 클래스의 전체 경로
        
    Examples:
        >>> register_component("CustomLLM", "llmops.components.custom_llm.CustomLLMComponent")
    """
    COMPONENT_REGISTRY[component_type] = class_path
    logger.info(f"새로운 컴포넌트 등록: {component_type} -> {class_path}")


def get_registered_components() -> Dict[str, str]:
    """
    등록된 모든 컴포넌트 타입과 클래스 경로를 반환합니다.
    
    Returns:
        컴포넌트 타입과 클래스 경로의 매핑 딕셔너리
    """
    return COMPONENT_REGISTRY.copy()


def is_component_registered(component_type: str) -> bool:
    """
    특정 컴포넌트 타입이 레지스트리에 등록되어 있는지 확인합니다.
    
    Args:
        component_type: 확인할 컴포넌트 타입
        
    Returns:
        등록되어 있으면 True, 아니면 False
    """
    return component_type in COMPONENT_REGISTRY 