"""
Chat Output Component for FlowRunner Pro

플로우의 최종 출력을 포맷팅하고 사용자에게 전달하는 컴포넌트
"""

import logging
from typing import Dict, Any, Optional, Union
import json
from datetime import datetime

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


class ChatOutputComponent:
    """
    채팅 출력 컴포넌트
    
    플로우의 최종 결과를 받아서 사용자에게 전달할 수 있는 형태로 포맷팅
    """
    
    def get_runnable(self, node_data: Dict[str, Any]) -> Runnable:
        """
        노드 데이터로부터 ChatOutput Runnable을 생성합니다.
        
        Args:
            node_data: Flow JSON에서 특정 노드에 해당하는 데이터 딕셔너리
        
        Returns:
            RunnableLambda 인스턴스
        """
        try:
            # 노드 데이터에서 출력 설정 추출
            field_values = node_data.get("data", {}).get("fieldValues", {})
            
            # 출력 포맷 설정
            output_format = field_values.get("output_format", "text")
            include_metadata = field_values.get("include_metadata", False)
            include_timestamps = field_values.get("include_timestamps", True)
            
            def format_output(input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
                """출력 데이터를 포맷팅하는 내부 함수"""
                try:
                    # 현재 시간
                    current_time = datetime.now()
                    
                    # 기본 출력 구조
                    output_result = {
                        "content": "",
                        "format": output_format,
                        "_component_type": "ChatOutput"
                    }
                    
                    # 타임스탬프 추가
                    if include_timestamps:
                        output_result["timestamp"] = current_time.isoformat()
                    
                    # 데이터 타입별 처리
                    if isinstance(input_data, str):
                        content = input_data
                    elif isinstance(input_data, dict):
                        content = self._extract_main_content(input_data)
                        if include_metadata:
                            output_result["metadata"] = self._extract_metadata(input_data)
                    else:
                        content = str(input_data)
                    
                    output_result["content"] = content
                    
                    logger.info(f"출력 포맷팅 완료: {output_format} 형식")
                    return output_result
                    
                except Exception as e:
                    logger.error(f"출력 포맷팅 실패: {e}")
                    return {
                        "content": str(input_data) if input_data else "출력 데이터가 없습니다.",
                        "format": "text",
                        "_component_type": "ChatOutput",
                        "_error": str(e)
                    }
            
            # RunnableLambda로 포맷팅 함수를 래핑
            runnable = RunnableLambda(format_output)
            
            logger.info(f"ChatOutput 컴포넌트 생성 완료: {output_format} 형식")
            return runnable
            
        except Exception as e:
            logger.error(f"ChatOutput 컴포넌트 생성 실패: {e}")
            return RunnableLambda(lambda x: {
                "content": str(x) if x else "출력이 없습니다.",
                "format": "text",
                "_error": str(e)
            })
    
    def _extract_main_content(self, data: Dict[str, Any]) -> str:
        """딕셔너리 데이터에서 주요 콘텐츠를 추출합니다."""
        content_keys = ["content", "response", "output", "result", "answer", "text", "message"]
        
        for key in content_keys:
            if key in data and data[key]:
                return str(data[key])
        
        # 기본적으로 전체 딕셔너리를 문자열로 변환
        filtered_data = {k: v for k, v in data.items() if not k.startswith("_")}
        return str(filtered_data)
    
    def _extract_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """딕셔너리 데이터에서 메타데이터를 추출합니다."""
        return {k: v for k, v in data.items() if k.startswith("_")}
    
    def validate_node_data(self, node_data: Dict[str, Any]) -> bool:
        """노드 데이터의 유효성을 검사합니다."""
        try:
            return "data" in node_data
        except Exception:
            return False
    
    def get_supported_formats(self) -> list[str]:
        """
        지원되는 출력 포맷 목록을 반환합니다.
        
        Returns:
            지원되는 포맷 리스트
        """
        return ["text", "json", "markdown"] 