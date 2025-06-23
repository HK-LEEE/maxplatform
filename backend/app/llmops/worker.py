"""
Stateful Worker for LLMOps

워커 프로세스로 실행되어 특정 플로우를 담당하는 독립적인 FastAPI 서버
표준 입력으로 플로우 JSON 데이터를 받아 로드하고 처리
"""

import sys
import json
import argparse
import logging
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .graph_builder import GraphBuilder

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FlowExecutionRequest(BaseModel):
    """플로우 실행 요청 모델"""
    input_data: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None

class FlowExecutionResponse(BaseModel):
    """플로우 실행 응답 모델"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None

class StatefulWorker:
    """
    독립적인 플로우 처리 워커
    FastAPI 서버를 내장하여 플로우 실행 요청을 처리
    """
    
    def __init__(self, project_id: str, flow_id: str, port: int = 0):
        """
        워커 초기화
        
        Args:
            project_id: 프로젝트 ID
            flow_id: 플로우 ID
            port: 서비스 포트 (0이면 자동 할당)
        """
        self.project_id = project_id
        self.flow_id = flow_id
        self.port = port
        self.flow_data = None
        self.flow_instance = None
        
        # FastAPI 앱 생성
        self.app = FastAPI(
            title=f"Flow Worker: {flow_id}",
            description=f"Worker for project {project_id}, flow {flow_id}",
            version="1.0.0"
        )
        
        # 라우트 설정
        self._setup_routes()
        
        logger.info(f"StatefulWorker 초기화 완료 - Project: {project_id}, Flow: {flow_id}")
    
    def load(self) -> bool:
        """
        표준 입력으로부터 플로우 JSON 데이터를 읽어서 로드
        
        Returns:
            로드 성공 여부
        """
        try:
            # 표준 입력에서 전체 JSON 문자열 읽기
            logger.info("표준 입력에서 플로우 데이터 읽기 시작...")
            flow_json_string = sys.stdin.read()
            
            if not flow_json_string.strip():
                logger.error("표준 입력에서 플로우 데이터를 읽을 수 없음")
                return False
            
            # JSON 파싱
            self.flow_data = json.loads(flow_json_string)
            logger.info(f"플로우 데이터 파싱 완료: {len(flow_json_string)} 문자")
            
            # 플로우 인스턴스 생성 (실제 langflow 연동 부분)
            self.flow_instance = self._create_flow_instance(self.flow_data)
            
            if self.flow_instance is None:
                logger.error("플로우 인스턴스 생성 실패")
                return False
                
            logger.info("플로우 로드 완료")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            return False
            
        except Exception as e:
            logger.error(f"플로우 로드 실패: {e}")
            return False
    
    def _create_flow_instance(self, flow_data: Dict[str, Any]) -> Optional[Any]:
        """
        플로우 데이터로부터 실행 가능한 LCEL 체인 생성
        
        Args:
            flow_data: 플로우 JSON 데이터
            
        Returns:
            실행 가능한 LCEL 체인 또는 None
        """
        try:
            # GraphBuilder를 사용하여 LCEL 체인 생성
            builder = GraphBuilder(flow_data)
            chain = builder.build()
            
            logger.info("LCEL 체인 생성 완료")
            return chain
            
        except Exception as e:
            logger.error(f"LCEL 체인 생성 실패: {e}")
            return None
    
    def _setup_routes(self):
        """FastAPI 라우트 설정"""
        
        @self.app.get("/health")
        async def health_check():
            """헬스 체크 엔드포인트"""
            return {
                "status": "healthy",
                "project_id": self.project_id,
                "flow_id": self.flow_id,
                "flow_loaded": self.flow_instance is not None
            }
        
        @self.app.post("/execute")
        async def execute_flow(request: FlowExecutionRequest):
            """플로우 실행 엔드포인트 (스트리밍 지원)"""
            import time
            start_time = time.time()
            
            try:
                if self.flow_instance is None:
                    raise HTTPException(
                        status_code=500, 
                        detail="플로우가 로드되지 않았습니다"
                    )
                
                # 스트리밍 요청 확인
                stream = request.parameters.get('stream', False) if request.parameters else False
                
                if stream:
                    # 스트리밍 응답
                    return StreamingResponse(
                        self._execute_flow_stream(request.input_data, request.parameters),
                        media_type="text/plain",
                        headers={"X-Flow-ID": self.flow_id}
                    )
                else:
                    # 일반 응답
                    result = await self._execute_flow_logic(
                        request.input_data, 
                        request.parameters
                    )
                    
                    execution_time = time.time() - start_time
                    
                    return FlowExecutionResponse(
                        success=True,
                        result=result,
                        execution_time=execution_time
                    )
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"플로우 실행 실패: {e}")
                
                return FlowExecutionResponse(
                    success=False,
                    error=str(e),
                    execution_time=execution_time
                )
        
        @self.app.get("/info")
        async def get_flow_info():
            """플로우 정보 조회 엔드포인트"""
            return {
                "project_id": self.project_id,
                "flow_id": self.flow_id,
                "flow_loaded": self.flow_instance is not None,
                "flow_data_size": len(json.dumps(self.flow_data)) if self.flow_data else 0
            }
    
    async def _execute_flow_logic(
        self, 
        input_data: Optional[Dict[str, Any]], 
        parameters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        실제 LCEL 체인 실행 로직
        
        Args:
            input_data: 입력 데이터
            parameters: 실행 파라미터
            
        Returns:
            실행 결과
        """
        try:
            # 입력 데이터 준비
            chain_input = input_data or {}
            
            # 텍스트 입력이 있는 경우 처리
            if isinstance(input_data, dict) and 'text' in input_data:
                chain_input = {"input": input_data['text']}
            elif isinstance(input_data, str):
                chain_input = {"input": input_data}
            elif not chain_input:
                chain_input = {"input": ""}
            
            # 파라미터 병합
            if parameters:
                chain_input.update(parameters)
            
            # LCEL 체인 실행
            try:
                # 비동기 invoke 시도 (ainvoke가 있는 경우)
                if hasattr(self.flow_instance, 'ainvoke'):
                    result = await self.flow_instance.ainvoke(chain_input)
                else:
                    # 동기 invoke 사용
                    result = self.flow_instance.invoke(chain_input)
            except AttributeError:
                # invoke 메서드가 없는 경우 직접 호출
                if callable(self.flow_instance):
                    result = self.flow_instance(chain_input)
                else:
                    raise ValueError("플로우 인스턴스를 실행할 수 없습니다")
            
            # 결과 포맷팅
            formatted_result = self._format_execution_result(result, input_data, parameters)
            
            logger.info(f"플로우 실행 완료: {self.flow_id}")
            return formatted_result
            
        except Exception as e:
            logger.error(f"플로우 실행 로직 실패: {e}")
            raise
    
    def _format_execution_result(
        self, 
        chain_result: Any, 
        original_input: Optional[Dict[str, Any]], 
        parameters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        체인 실행 결과를 포맷팅합니다.
        
        Args:
            chain_result: 체인 실행 결과
            original_input: 원본 입력 데이터
            parameters: 실행 파라미터
            
        Returns:
            포맷팅된 결과 딕셔너리
        """
        try:
            # 기본 결과 구조
            result = {
                "flow_id": self.flow_id,
                "project_id": self.project_id,
                "success": True,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # 체인 결과 처리
            if isinstance(chain_result, dict):
                # 딕셔너리 결과인 경우
                if 'content' in chain_result:
                    result["output"] = chain_result['content']
                    result["metadata"] = {k: v for k, v in chain_result.items() if k != 'content'}
                else:
                    result["output"] = chain_result
            elif isinstance(chain_result, str):
                # 문자열 결과인 경우
                result["output"] = chain_result
            else:
                # 기타 타입인 경우
                result["output"] = str(chain_result)
            
            # 디버그 정보 (선택적)
            if logger.level <= logging.DEBUG:
                result["debug"] = {
                    "input_received": original_input,
                    "parameters_received": parameters,
                    "chain_result_type": type(chain_result).__name__
                }
            
            return result
            
        except Exception as e:
            logger.error(f"결과 포맷팅 실패: {e}")
            return {
                "flow_id": self.flow_id,
                "project_id": self.project_id,
                "success": False,
                "error": f"결과 포맷팅 실패: {e}",
                "raw_result": str(chain_result)
            }
    
    async def _execute_flow_stream(
        self, 
        input_data: Optional[Dict[str, Any]], 
        parameters: Optional[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 방식으로 플로우를 실행합니다.
        
        Args:
            input_data: 입력 데이터
            parameters: 실행 파라미터
            
        Yields:
            실행 결과 청크들
        """
        try:
            # 시작 메시지
            yield f"data: {json.dumps({'type': 'start', 'flow_id': self.flow_id})}\n\n"
            
            # 입력 데이터 준비
            chain_input = input_data or {}
            
            if isinstance(input_data, dict) and 'text' in input_data:
                chain_input = {"input": input_data['text']}
            elif isinstance(input_data, str):
                chain_input = {"input": input_data}
            elif not chain_input:
                chain_input = {"input": ""}
            
            if parameters:
                chain_input.update(parameters)
            
            # 스트리밍 실행 시도
            try:
                # astream 메서드가 있는 경우 (LangChain 스트리밍)
                if hasattr(self.flow_instance, 'astream'):
                    async for chunk in self.flow_instance.astream(chain_input):
                        chunk_data = {
                            'type': 'chunk',
                            'data': chunk if isinstance(chunk, (str, dict)) else str(chunk)
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                
                # stream 메서드가 있는 경우 (동기 스트리밍)
                elif hasattr(self.flow_instance, 'stream'):
                    for chunk in self.flow_instance.stream(chain_input):
                        chunk_data = {
                            'type': 'chunk',
                            'data': chunk if isinstance(chunk, (str, dict)) else str(chunk)
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                        await asyncio.sleep(0)  # 비동기 처리를 위한 양보
                
                else:
                    # 스트리밍을 지원하지 않는 경우 일반 실행
                    result = await self._execute_flow_logic(input_data, parameters)
                    result_data = {
                        'type': 'result',
                        'data': result
                    }
                    yield f"data: {json.dumps(result_data)}\n\n"
            
            except Exception as execution_error:
                error_data = {
                    'type': 'error',
                    'error': str(execution_error)
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                raise
            
            # 완료 메시지
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"스트리밍 실행 실패: {e}")
            error_data = {
                'type': 'error',
                'error': str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    async def start_server(self):
        """FastAPI 서버 시작"""
        try:
            config = uvicorn.Config(
                self.app,
                host="127.0.0.1",
                port=self.port,
                log_level="info",
                access_log=True
            )
            
            server = uvicorn.Server(config)
            
            # 실제 포트 번호 확인 (0으로 설정한 경우 자동 할당)
            if self.port == 0:
                # 서버 시작 후 실제 포트 번호 가져오기
                await server.serve()
            else:
                logger.info(f"Worker 서버 시작: http://127.0.0.1:{self.port}")
                await server.serve()
                
        except Exception as e:
            logger.error(f"서버 시작 실패: {e}")
            raise

def main():
    """메인 함수 - 커맨드 라인에서 실행"""
    parser = argparse.ArgumentParser(description="LLMOps Stateful Worker")
    parser.add_argument("--project_id", required=True, help="프로젝트 ID")
    parser.add_argument("--flow_id", required=True, help="플로우 ID")
    parser.add_argument("--port", type=int, default=0, help="서비스 포트")
    
    args = parser.parse_args()
    
    # 워커 생성
    worker = StatefulWorker(
        project_id=args.project_id,
        flow_id=args.flow_id,
        port=args.port
    )
    
    # 플로우 로드
    if not worker.load():
        logger.error("플로우 로드 실패 - 워커 종료")
        sys.exit(1)
    
    # 서버 시작
    try:
        asyncio.run(worker.start_server())
    except KeyboardInterrupt:
        logger.info("워커 서버 종료")
    except Exception as e:
        logger.error(f"워커 실행 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 