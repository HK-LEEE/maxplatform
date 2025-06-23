"""
Azure OpenAI Component for FlowRunner Pro

Azure OpenAI 서비스와 연동하여 LLM 호출을 처리하는 컴포넌트
"""

import logging
from typing import Dict, Any, Optional

try:
    from langchain_openai import AzureChatOpenAI
    from langchain_core.runnables.base import Runnable
except ImportError:
    # langchain 라이브러리가 없는 경우 대체 구현
    logging.warning("langchain_openai를 가져올 수 없습니다. 대체 구현을 사용합니다.")
    
    class Runnable:
        """Runnable 기본 클래스 대체 구현"""
        def invoke(self, input_data: Any) -> Any:
            return input_data
        
        def __or__(self, other):
            """파이프 연산자 지원"""
            return ChainedRunnable(self, other)
    
    class AzureChatOpenAI(Runnable):
        """AzureChatOpenAI 대체 구현"""
        def __init__(self, **kwargs):
            self.config = kwargs
            self.model = kwargs.get("model", "gpt-3.5-turbo")
            self.temperature = kwargs.get("temperature", 0.7)
            self.max_tokens = kwargs.get("max_tokens", 1000)
        
        def invoke(self, input_data: Any) -> str:
            """시뮬레이션된 AI 응답"""
            if isinstance(input_data, dict):
                text = input_data.get("input", str(input_data))
            else:
                text = str(input_data)
            
            return f"[Azure OpenAI {self.model} 응답] 입력: '{text[:50]}...' 에 대한 처리된 응답입니다."
    
    class ChainedRunnable(Runnable):
        """체인된 Runnable 대체 구현"""
        def __init__(self, first, second):
            self.first = first
            self.second = second
        
        def invoke(self, input_data: Any) -> Any:
            intermediate = self.first.invoke(input_data)
            return self.second.invoke(intermediate)

logger = logging.getLogger(__name__)


class AzureOpenAIComponent:
    """
    Azure OpenAI 컴포넌트
    
    Azure OpenAI API를 사용하여 대화형 AI 모델을 호출
    """
    
    def get_runnable(self, node_data: Dict[str, Any]) -> Runnable:
        """
        노드 데이터로부터 AzureChatOpenAI Runnable을 생성합니다.
        
        Args:
            node_data: Flow JSON에서 특정 노드에 해당하는 데이터 딕셔너리
                      예상 구조: {
                          "data": {
                              "fieldValues": {
                                  "azure_endpoint": "https://your-resource.openai.azure.com/",
                                  "api_key": "your-api-key",
                                  "deployment_name": "gpt-35-turbo",
                                  "api_version": "2023-12-01-preview",
                                  "model": "gpt-3.5-turbo",
                                  "temperature": 0.7,
                                  "max_tokens": 1000,
                                  "stream": true
                              }
                          }
                      }
        
        Returns:
            AzureChatOpenAI 인스턴스
        """
        try:
            # 노드 데이터에서 Azure OpenAI 설정 추출
            field_values = node_data.get("data", {}).get("fieldValues", {})
            
            # 필수 설정값들
            azure_endpoint = field_values.get("azure_endpoint", "")
            api_key = field_values.get("api_key", "")
            deployment_name = field_values.get("deployment_name", "")
            api_version = field_values.get("api_version", "2023-12-01-preview")
            
            # 선택적 설정값들
            model = field_values.get("model", "gpt-3.5-turbo")
            temperature = float(field_values.get("temperature", 0.7))
            max_tokens = int(field_values.get("max_tokens", 1000))
            stream = field_values.get("stream", False)
            
            # 환경변수나 기본값으로 fallback
            if not azure_endpoint:
                import os
                azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            
            if not api_key:
                import os
                api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
            
            if not deployment_name:
                deployment_name = model  # 기본값으로 모델명 사용
            
            # 필수값 검증
            if not all([azure_endpoint, api_key, deployment_name]):
                logger.warning("Azure OpenAI 필수 설정값이 부족합니다. 시뮬레이션 모드로 실행됩니다.")
                return AzureChatOpenAI(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            
            # AzureChatOpenAI 인스턴스 생성
            azure_openai = AzureChatOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                azure_deployment=deployment_name,
                api_version=api_version,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=stream
            )
            
            logger.info(f"Azure OpenAI 컴포넌트 생성 완료: {deployment_name} (temp={temperature})")
            return azure_openai
            
        except ValueError as e:
            logger.error(f"Azure OpenAI 설정값 오류: {e}")
            # 기본 설정으로 fallback
            return AzureChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
            
        except Exception as e:
            logger.error(f"Azure OpenAI 컴포넌트 생성 실패: {e}")
            # 기본 설정으로 fallback
            return AzureChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
    
    def validate_node_data(self, node_data: Dict[str, Any]) -> bool:
        """
        노드 데이터의 유효성을 검사합니다.
        
        Args:
            node_data: 검사할 노드 데이터
            
        Returns:
            유효하면 True, 아니면 False
        """
        try:
            field_values = node_data.get("data", {}).get("fieldValues", {})
            
            # 최소한의 설정 확인 (환경변수로도 제공될 수 있으므로 엄격하지 않게)
            has_endpoint = bool(field_values.get("azure_endpoint"))
            has_key = bool(field_values.get("api_key"))
            has_deployment = bool(field_values.get("deployment_name"))
            
            # 환경변수 확인
            if not (has_endpoint and has_key):
                import os
                has_endpoint = has_endpoint or bool(os.getenv("AZURE_OPENAI_ENDPOINT"))
                has_key = has_key or bool(os.getenv("AZURE_OPENAI_API_KEY"))
            
            return has_endpoint or has_key  # 하나라도 있으면 유효한 것으로 간주
            
        except Exception:
            return False
    
    def get_supported_models(self) -> list[str]:
        """
        지원되는 모델 목록을 반환합니다.
        
        Returns:
            지원되는 모델명 리스트
        """
        return [
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-4",
            "gpt-4-32k",
            "gpt-4-turbo",
            "gpt-4o"
        ] 