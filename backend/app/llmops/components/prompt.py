"""
Prompt Component for FlowRunner Pro

프롬프트 템플릿을 관리하고 LangChain ChatPromptTemplate으로 변환하는 컴포넌트
"""

import logging
from typing import Dict, Any, Union

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnableLambda
    from langchain_core.runnables.base import Runnable
except ImportError:
    # langchain 라이브러리가 없는 경우 대체 구현
    logging.warning("langchain_core를 가져올 수 없습니다. 대체 구현을 사용합니다.")
    
    class Runnable:
        """Runnable 기본 클래스 대체 구현"""
        def invoke(self, input_data: Any) -> Any:
            return input_data
    
    class RunnableLambda(Runnable):
        """RunnableLambda 대체 구현"""
        def __init__(self, func):
            self.func = func
        
        def invoke(self, input_data: Any) -> Any:
            return self.func(input_data)
    
    class ChatPromptTemplate(Runnable):
        """ChatPromptTemplate 대체 구현"""
        def __init__(self, template: str):
            self.template = template
        
        @classmethod
        def from_template(cls, template: str):
            return cls(template)
        
        def invoke(self, inputs: Dict[str, Any]) -> str:
            """간단한 템플릿 처리"""
            result = self.template
            for key, value in inputs.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result

logger = logging.getLogger(__name__)


class PromptComponent:
    """
    프롬프트 컴포넌트
    
    Flow JSON의 프롬프트 노드 데이터를 받아서 ChatPromptTemplate으로 변환
    """
    
    def get_runnable(self, node_data: Dict[str, Any]) -> Union[RunnableLambda, ChatPromptTemplate, Runnable]:
        """
        노드 데이터로부터 ChatPromptTemplate을 생성합니다.
        
        Args:
            node_data: Flow JSON에서 특정 노드에 해당하는 데이터 딕셔너리
                      예상 구조: {
                          "data": {
                              "fieldValues": {
                                  "template": "프롬프트 템플릿 문자열"
                              }
                          }
                      }
        
        Returns:
            ChatPromptTemplate 인스턴스
            
        Raises:
            ValueError: 필수 데이터가 없는 경우
            KeyError: 예상된 키가 node_data에 없는 경우
        """
        try:
            # node_data에서 템플릿 추출
            data = node_data.get("data", {})
            field_values = data.get("fieldValues", {})
            fields = data.get("fields", [])
            
            # 여러 위치에서 템플릿 찾기
            template = None
            
            # 1. fieldValues에서 찾기
            template = field_values.get("template")
            
            # 2. 템플릿이 없으면 fields 배열에서 기본값 찾기
            if not template:
                for field in fields:
                    if field.get("name") == "template":
                        template = field.get("value") or field.get("placeholder")
                        break
            
            # 3. 그래도 없으면 기본 템플릿 사용
            if not template:
                template = field_values.get("prompt", "")
            
            # 4. 최종적으로 없으면 기본 템플릿 제공
            if not template:
                template = "You are a helpful assistant. User: {text}\nAssistant:"
                logger.warning("템플릿이 비어있어 기본 템플릿을 사용합니다")
            
            # RunnableLambda를 사용하여 템플릿 처리 함수 생성
            def prompt_process(input_data: Dict[str, Any]) -> Dict[str, Any]:
                """템플릿에 변수를 바인딩하는 함수"""
                try:
                    # 입력 데이터에서 변수 추출
                    if isinstance(input_data, str):
                        variables = {"text": input_data}
                    elif isinstance(input_data, dict):
                        variables = input_data.copy()
                        # 일반적인 변수명들 매핑
                        if "input" in variables and "text" not in variables:
                            variables["text"] = variables["input"]
                        if "query" in variables and "text" not in variables:
                            variables["text"] = variables["query"]
                    else:
                        variables = {"text": str(input_data)}
                    
                    # 템플릿에 변수 바인딩 (대소문자 구분 없이)
                    result_prompt = template
                    for key, value in variables.items():
                        # 소문자 버전
                        placeholder_lower = f"{{{key.lower()}}}"
                        if placeholder_lower in result_prompt.lower():
                            # 실제 템플릿에서 대소문자 구분 없이 찾아서 교체
                            import re
                            pattern = re.compile(re.escape(f"{{{key}}}"), re.IGNORECASE)
                            result_prompt = pattern.sub(str(value), result_prompt)
                        
                        # 정확한 매치도 시도
                        placeholder = f"{{{key}}}"
                        if placeholder in result_prompt:
                            result_prompt = result_prompt.replace(placeholder, str(value))
                    
                    # 추가로 일반적인 변수명들도 시도
                    common_mappings = {
                        'text': ['Text', 'TEXT', 'input', 'Input', 'INPUT', 'query', 'Query', 'QUERY'],
                        'context': ['Context', 'CONTEXT', 'content', 'Content', 'CONTENT']
                    }
                    
                    for var_name, var_value in variables.items():
                        if var_name.lower() in common_mappings:
                            for variant in common_mappings[var_name.lower()]:
                                placeholder = f"{{{variant}}}"
                                if placeholder in result_prompt:
                                    result_prompt = result_prompt.replace(placeholder, str(var_value))
                    
                    # 결과 구성
                    result = variables.copy()
                    result["prompt"] = result_prompt
                    result["_component_type"] = "Prompt"
                    result["_template"] = template
                    
                    logger.info(f"프롬프트 바인딩 완료: {result_prompt[:100]}...")
                    return result
                    
                except Exception as e:
                    logger.error(f"프롬프트 처리 실패: {e}")
                    return {
                        "prompt": template,
                        "_error": str(e),
                        "_component_type": "Prompt"
                    }
            
            # RunnableLambda로 래핑
            prompt_runnable = RunnableLambda(prompt_process)
            
            logger.info(f"프롬프트 컴포넌트 생성 완료: {template[:100]}...")
            return prompt_runnable
            
        except KeyError as e:
            logger.error(f"프롬프트 노드 데이터에서 필수 키를 찾을 수 없음: {e}")
            raise KeyError(f"프롬프트 노드 데이터 구조가 올바르지 않습니다: {e}") from e
            
        except Exception as e:
            logger.error(f"프롬프트 컴포넌트 생성 실패: {e}")
            raise ValueError(f"프롬프트 컴포넌트를 생성할 수 없습니다: {e}") from e
    
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
            template = field_values.get("template") or field_values.get("prompt")
            return bool(template and isinstance(template, str))
        except Exception:
            return False 