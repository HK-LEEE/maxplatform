"""
Chat Input Component for FlowRunner Pro

사용자 채팅 입력을 처리하고 다음 컴포넌트로 전달하는 컴포넌트
"""

import logging
from typing import Dict, Any

try:
    from langchain_core.runnables import RunnableLambda
    from langchain_core.runnables.base import Runnable
except ImportError:
    # langchain 라이브러리가 없는 경우 대체 구현
    logging.warning("langchain_core.runnables를 가져올 수 없습니다. 대체 구현을 사용합니다.")
    
    class Runnable:
        """Runnable 기본 클래스 대체 구현"""
        def invoke(self, input_data: Any) -> Any:
            return input_data
        
        def __or__(self, other):
            """파이프 연산자 지원"""
            return ChainedRunnable(self, other)
    
    class RunnableLambda(Runnable):
        """RunnableLambda 대체 구현"""
        def __init__(self, func):
            self.func = func
        
        def invoke(self, input_data: Any) -> Any:
            return self.func(input_data)
    
    class ChainedRunnable(Runnable):
        """체인된 Runnable 대체 구현"""
        def __init__(self, first, second):
            self.first = first
            self.second = second
        
        def invoke(self, input_data: Any) -> Any:
            intermediate = self.first.invoke(input_data)
            return self.second.invoke(intermediate)

logger = logging.getLogger(__name__)


class ChatInputComponent:
    """
    채팅 입력 컴포넌트
    
    사용자의 채팅 입력을 받아서 다음 컴포넌트로 전달
    입력 데이터를 정규화하고 필요한 변환을 수행
    """
    
    def get_runnable(self, node_data: Dict[str, Any]) -> Runnable:
        """
        노드 데이터로부터 ChatInput Runnable을 생성합니다.
        
        Args:
            node_data: Flow JSON에서 특정 노드에 해당하는 데이터 딕셔너리
                      예상 구조: {
                          "data": {
                              "fieldValues": {
                                  "input_key": "user_input",
                                  "placeholder": "메시지를 입력하세요...",
                                  "multiline": true
                              }
                          }
                      }
        
        Returns:
            RunnableLambda 인스턴스
        """
        try:
            # 노드 데이터에서 설정값 추출
            field_values = node_data.get("data", {}).get("fieldValues", {})
            input_key = field_values.get("input_key", "input")
            placeholder = field_values.get("placeholder", "")
            multiline = field_values.get("multiline", False)
            
            def process_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
                """
                입력 데이터를 처리하는 내부 함수
                
                Args:
                    input_data: 입력 데이터 딕셔너리
                    
                Returns:
                    처리된 입력 데이터
                """
                try:
                    logger.info(f"ChatInput 입력 데이터 처리 시작: {input_data}")
                    
                    # 사용자 입력을 우선적으로 처리
                    user_input = ""
                    
                    if isinstance(input_data, str):
                        # 문자열인 경우 직접 사용
                        user_input = input_data
                    elif isinstance(input_data, dict):
                        # 딕셔너리인 경우 사용자 입력을 우선 순위로 찾기
                        # 1. 'input' 키 (백엔드에서 전송하는 사용자 입력)
                        if "input" in input_data and input_data["input"]:
                            user_input = str(input_data["input"])
                        # 2. 'text' 키 (프론트엔드에서 전송하는 텍스트)
                        elif "text" in input_data and input_data["text"]:
                            user_input = str(input_data["text"])
                        # 3. 'message' 키
                        elif "message" in input_data and input_data["message"]:
                            user_input = str(input_data["message"])
                        # 4. input_key로 지정된 키
                        elif input_key in input_data and input_data[input_key]:
                            user_input = str(input_data[input_key])
                        # 5. placeholder는 사용자 입력이 없을 때만 사용
                        elif not any(input_data.values()) and placeholder:
                            user_input = placeholder
                            logger.info(f"사용자 입력이 없어 placeholder 사용: {placeholder}")
                        else:
                            # 첫 번째 비어있지 않은 값을 사용
                            for value in input_data.values():
                                if value and str(value).strip():
                                    user_input = str(value)
                                    break
                    else:
                        # 기타 타입인 경우 문자열로 변환
                        user_input = str(input_data)
                    
                    # 처리된 데이터 구성
                    processed_data = {
                        input_key: user_input,
                        "text": user_input,  # 다음 컴포넌트를 위한 표준 키
                        "prompt": user_input  # Ollama 등 모델 컴포넌트를 위한 키
                    }
                    
                    # 메타데이터 추가
                    processed_data["_component_type"] = "ChatInput"
                    processed_data["_placeholder"] = placeholder
                    processed_data["_multiline"] = multiline
                    
                    logger.info(f"채팅 입력 처리 완료: '{user_input}' ({len(user_input)} 문자)")
                    return processed_data
                    
                except Exception as e:
                    logger.error(f"채팅 입력 처리 실패: {e}")
                    # 에러 발생 시 기본값 반환
                    return {input_key: "", "text": "", "prompt": "", "_error": str(e)}
            
            # RunnableLambda로 처리 함수를 래핑
            runnable = RunnableLambda(process_input)
            
            logger.info(f"ChatInput 컴포넌트 생성 완료: input_key={input_key}")
            return runnable
            
        except Exception as e:
            logger.error(f"ChatInput 컴포넌트 생성 실패: {e}")
            # 기본 처리 함수를 반환
            return RunnableLambda(lambda x: {"input": str(x)} if x else {"input": ""})
    
    def validate_node_data(self, node_data: Dict[str, Any]) -> bool:
        """
        노드 데이터의 유효성을 검사합니다.
        
        Args:
            node_data: 검사할 노드 데이터
            
        Returns:
            유효하면 True, 아니면 False
        """
        try:
            # ChatInput은 특별한 필수 필드가 없으므로 기본 구조만 확인
            return "data" in node_data
        except Exception:
            return False 