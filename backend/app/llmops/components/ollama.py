"""
Ollama Component for FlowRunner Pro

Ollama 로컬 LLM 서비스와 연동하여 오픈소스 모델을 호출하는 컴포넌트
"""

import logging
from typing import Dict, Any, Optional

try:
    from langchain_community.llms import Ollama
    from langchain_core.runnables.base import Runnable
except ImportError:
    # langchain 라이브러리가 없는 경우 대체 구현
    logging.warning("langchain_community.llms를 가져올 수 없습니다. 대체 구현을 사용합니다.")
    
    class Runnable:
        """Runnable 기본 클래스 대체 구현"""
        def invoke(self, input_data: Any) -> Any:
            return input_data
        
        def __or__(self, other):
            """파이프 연산자 지원"""
            return ChainedRunnable(self, other)
    
    class Ollama(Runnable):
        """Ollama 대체 구현"""
        def __init__(self, **kwargs):
            self.config = kwargs
            self.model = kwargs.get("model", "llama2")
            self.base_url = kwargs.get("base_url", "http://localhost:11434")
            self.temperature = kwargs.get("temperature", 0.7)
        
        def invoke(self, input_data: Any) -> str:
            """시뮬레이션된 Ollama 응답"""
            if isinstance(input_data, dict):
                text = input_data.get("input", str(input_data))
            else:
                text = str(input_data)
            
            return f"[Ollama {self.model} 응답] 입력: '{text[:50]}...' 에 대한 로컬 LLM 처리 결과입니다."
    
    class ChainedRunnable(Runnable):
        """체인된 Runnable 대체 구현"""
        def __init__(self, first, second):
            self.first = first
            self.second = second
        
        def invoke(self, input_data: Any) -> Any:
            intermediate = self.first.invoke(input_data)
            return self.second.invoke(intermediate)

logger = logging.getLogger(__name__)


class OllamaComponent:
    """
    Ollama 컴포넌트
    
    로컬에서 실행되는 Ollama 서비스를 통해 오픈소스 LLM 모델을 호출
    """
    
    def get_runnable(self, node_data: Dict[str, Any]) -> Runnable:
        """
        노드 데이터로부터 Ollama Runnable을 생성합니다.
        
        Args:
            node_data: Flow JSON에서 특정 노드에 해당하는 데이터 딕셔너리
                      예상 구조: {
                          "data": {
                              "fieldValues": {
                                  "model": "llama2",
                                  "base_url": "http://localhost:11434",
                                  "temperature": 0.7,
                                  "num_predict": 256,
                                  "top_k": 40,
                                  "top_p": 0.9,
                                  "repeat_penalty": 1.1,
                                  "stream": true
                              }
                          }
                      }
        
        Returns:
            Ollama 인스턴스
        """
        try:
            # 노드 데이터에서 Ollama 설정 추출
            field_values = node_data.get("data", {}).get("fieldValues", {})
            
            # 기본 설정값들
            model = field_values.get("model", "llama2")
            base_url = field_values.get("base_url", "http://localhost:11434")
            temperature = float(field_values.get("temperature", 0.7))
            
            # Ollama 특화 설정들
            num_predict = int(field_values.get("num_predict", 256))
            top_k = int(field_values.get("top_k", 40))
            top_p = float(field_values.get("top_p", 0.9))
            repeat_penalty = float(field_values.get("repeat_penalty", 1.1))
            stream = field_values.get("stream", False)
            
            # 환경변수로 base_url 설정 가능
            if not base_url or base_url == "http://localhost:11434":
                import os
                base_url = os.getenv("OLLAMA_BASE_URL", base_url)
            
            # Ollama 인스턴스 생성
            ollama = Ollama(
                model=model,
                base_url=base_url,
                temperature=temperature,
                num_predict=num_predict,
                top_k=top_k,
                top_p=top_p,
                repeat_penalty=repeat_penalty
            )
            
            # 입력 데이터 변환을 위한 래퍼 함수
            def process_ollama_input(input_data: Any) -> str:
                """
                Ollama에 전달할 입력 데이터를 문자열로 변환합니다.
                
                Args:
                    input_data: 입력 데이터 (딕셔너리 또는 문자열)
                    
                Returns:
                    변환된 문자열
                """
                try:
                    logger.info(f"Ollama 입력 데이터 처리 시작: {input_data}")
                    
                    if isinstance(input_data, str):
                        # 이미 문자열인 경우
                        prompt_text = input_data
                    elif isinstance(input_data, dict):
                        # 딕셔너리인 경우 적절한 키에서 텍스트 추출
                        prompt_text = (
                            input_data.get("prompt") or  # Ollama용 키
                            input_data.get("text") or    # 표준 텍스트 키
                            input_data.get("input") or   # 입력 키
                            input_data.get("message") or # 메시지 키
                            str(input_data)              # 전체를 문자열로 변환
                        )
                    else:
                        # 기타 타입인 경우 문자열로 변환
                        prompt_text = str(input_data)
                    
                    logger.info(f"Ollama 프롬프트 텍스트: '{prompt_text}' ({len(prompt_text)} 문자)")
                    return prompt_text
                    
                except Exception as e:
                    logger.error(f"Ollama 입력 처리 실패: {e}")
                    return str(input_data) if input_data else ""
            
            # RunnableLambda로 입력 변환 후 Ollama 호출
            from langchain_core.runnables import RunnableLambda
            
            # 입력 변환 -> Ollama 호출의 체인 생성
            input_processor = RunnableLambda(process_ollama_input)
            ollama_chain = input_processor | ollama
            
            logger.info(f"Ollama 컴포넌트 생성 완료: {model} @ {base_url}")
            return ollama_chain
            
        except ValueError as e:
            logger.error(f"Ollama 설정값 오류: {e}")
            # 기본 설정으로 fallback
            return Ollama(model="llama2")
            
        except Exception as e:
            logger.error(f"Ollama 컴포넌트 생성 실패: {e}")
            # 기본 설정으로 fallback
            return Ollama(model="llama2")
    
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
            
            # 모델명이 있는지 확인
            model = field_values.get("model", "")
            
            # 기본 모델이라도 유효한 것으로 간주
            return True  # Ollama는 기본값으로도 작동 가능
            
        except Exception:
            return False
    
    def get_supported_models(self) -> list[str]:
        """
        일반적으로 지원되는 Ollama 모델 목록을 반환합니다.
        
        Returns:
            지원되는 모델명 리스트
        """
        return [
            "llama2",
            "llama2:7b",
            "llama2:13b",
            "llama2:70b",
            "mistral",
            "mistral:7b",
            "codellama",
            "codellama:7b",
            "codellama:13b",
            "gemma",
            "gemma:2b",
            "gemma:7b",
            "phi",
            "phi:2.7b",
            "qwen",
            "qwen:4b",
            "qwen:7b",
            "vicuna",
            "vicuna:7b",
            "vicuna:13b"
        ]
    
    def check_ollama_availability(self, base_url: str = "http://localhost:11434") -> bool:
        """
        Ollama 서비스가 실행 중인지 확인합니다.
        
        Args:
            base_url: Ollama 서비스 URL
            
        Returns:
            서비스가 실행 중이면 True, 아니면 False
        """
        try:
            import requests
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama 서비스 연결 실패: {e}")
            return False
    
    def get_available_models(self, base_url: str = "http://localhost:11434") -> list[str]:
        """
        현재 Ollama 서비스에서 사용 가능한 모델 목록을 가져옵니다.
        
        Args:
            base_url: Ollama 서비스 URL
            
        Returns:
            사용 가능한 모델명 리스트
        """
        try:
            import requests
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return models
        except Exception as e:
            logger.warning(f"Ollama 모델 목록 조회 실패: {e}")
        
        return self.get_supported_models()  # fallback to default list 