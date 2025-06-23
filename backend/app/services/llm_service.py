"""
LLM 서비스 - Azure OpenAI와 Ollama 지원
Jupyter 노트북 분석 및 수정 지원
"""

import json
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.azure_available = False
        self.ollama_available = False
        self._check_availability()
    
    def _check_availability(self):
        """LLM 서비스 가용성 확인"""
        # Azure OpenAI 설정 확인
        if (settings.azure_openai_endpoint and 
            settings.azure_openai_api_key and 
            settings.azure_openai_deployment_name):
            self.azure_available = True
            logger.info("Azure OpenAI 설정 확인됨")
        else:
            logger.warning("Azure OpenAI 설정이 불완전합니다")
        
        # Ollama 설정 확인 (기본값이라도 체크)
        if settings.ollama_base_url:
            self.ollama_available = True
            logger.info(f"Ollama 설정 확인됨: {settings.ollama_base_url}")
        else:
            logger.warning("Ollama 설정이 없습니다")
    
    def parse_notebook_content(self, notebook_json: str) -> Dict[str, Any]:
        """노트북 JSON을 파싱하여 구조화된 정보 반환"""
        try:
            notebook = json.loads(notebook_json) if isinstance(notebook_json, str) else notebook_json
            
            cells_info = []
            code_cells = []
            markdown_cells = []
            
            for i, cell in enumerate(notebook.get('cells', [])):
                cell_info = {
                    'index': i,
                    'cell_type': cell.get('cell_type', ''),
                    'source': ''.join(cell.get('source', [])),
                    'execution_count': cell.get('execution_count'),
                    'outputs': []
                }
                
                # 셀 출력 정보 추가
                if 'outputs' in cell:
                    for output in cell['outputs']:
                        if output.get('output_type') == 'execute_result':
                            if 'data' in output and 'text/plain' in output['data']:
                                cell_info['outputs'].append({
                                    'type': 'result',
                                    'data': ''.join(output['data']['text/plain'])
                                })
                        elif output.get('output_type') == 'stream':
                            cell_info['outputs'].append({
                                'type': 'stream',
                                'name': output.get('name', 'stdout'),
                                'text': ''.join(output.get('text', []))
                            })
                        elif output.get('output_type') == 'error':
                            cell_info['outputs'].append({
                                'type': 'error',
                                'ename': output.get('ename', ''),
                                'evalue': output.get('evalue', ''),
                                'traceback': output.get('traceback', [])
                            })
                
                cells_info.append(cell_info)
                
                if cell.get('cell_type') == 'code':
                    code_cells.append(cell_info)
                elif cell.get('cell_type') == 'markdown':
                    markdown_cells.append(cell_info)
            
            return {
                'total_cells': len(cells_info),
                'code_cells_count': len(code_cells),
                'markdown_cells_count': len(markdown_cells),
                'cells': cells_info,
                'code_cells': code_cells,
                'markdown_cells': markdown_cells,
                'metadata': notebook.get('metadata', {})
            }
            
        except Exception as e:
            logger.error(f"노트북 파싱 오류: {e}")
            return {
                'total_cells': 0,
                'code_cells_count': 0,
                'markdown_cells_count': 0,
                'cells': [],
                'code_cells': [],
                'markdown_cells': [],
                'metadata': {},
                'error': str(e)
            }
    
    def extract_cell_context(self, parsed_notebook: Dict[str, Any], cell_indices: List[int] = None) -> str:
        """특정 셀들의 컨텍스트를 추출하여 LLM에 전달할 형태로 구성"""
        if not parsed_notebook.get('cells'):
            return "빈 노트북입니다."
        
        context_parts = []
        cells_to_include = parsed_notebook['cells']
        
        # 특정 셀 인덱스가 지정된 경우 해당 셀들만 포함
        if cell_indices is not None:
            cells_to_include = [cell for cell in parsed_notebook['cells'] 
                             if cell['index'] in cell_indices]
        
        for cell in cells_to_include:
            if cell['cell_type'] == 'code':
                context_parts.append(f"[코드 셀 {cell['index'] + 1}]")
                context_parts.append(f"```python\n{cell['source']}\n```")
                
                # 실행 결과가 있다면 포함
                if cell['execution_count'] is not None:
                    context_parts.append(f"실행 횟수: {cell['execution_count']}")
                
                if cell['outputs']:
                    context_parts.append("출력:")
                    for output in cell['outputs']:
                        if output['type'] == 'result':
                            context_parts.append(f"  결과: {output['data']}")
                        elif output['type'] == 'stream':
                            context_parts.append(f"  {output['name']}: {output['text']}")
                        elif output['type'] == 'error':
                            context_parts.append(f"  오류 ({output['ename']}): {output['evalue']}")
                            if output['traceback']:
                                context_parts.append(f"  트레이스백: {' '.join(output['traceback'][:3])}")
                
            elif cell['cell_type'] == 'markdown':
                context_parts.append(f"[마크다운 셀 {cell['index'] + 1}]")
                context_parts.append(cell['source'])
            
            context_parts.append("")  # 셀 간 구분을 위한 빈 줄
        
        return "\n".join(context_parts)
    
    async def analyze_notebook_cells(self, notebook_content: str, user_message: str, 
                                   cell_indices: List[int] = None, provider: str = None) -> Dict[str, Any]:
        """특정 셀들을 분석하고 수정 제안 제공"""
        if provider is None:
            provider = settings.default_llm_provider
        
        # 연결 상태 확인
        connection_status = await self.check_connection(provider)
        
        if provider == "azure" and not connection_status["azure"]:
            return {"error": "Azure OpenAI에 연결할 수 없습니다"}
        elif provider == "ollama" and not connection_status["ollama"]:
            return {"error": "Ollama에 연결할 수 없습니다"}
        
        # 노트북 내용 파싱
        parsed_notebook = self.parse_notebook_content(notebook_content)
        
        if 'error' in parsed_notebook:
            return {"error": f"노트북 파싱 실패: {parsed_notebook['error']}"}
        
        # 컨텍스트 추출
        if cell_indices:
            context = self.extract_cell_context(parsed_notebook, cell_indices)
            context_description = f"선택된 {len(cell_indices)}개 셀"
        else:
            context = self.extract_cell_context(parsed_notebook)
            context_description = f"전체 노트북 ({parsed_notebook['total_cells']}개 셀)"
        
        # 시스템 메시지 구성
        system_message = """당신은 Jupyter 노트북 분석 및 코드 개선 전문가입니다.
제공된 노트북 셀들을 분석하고 다음과 같은 도움을 제공하세요:

1. **코드 분석**: 오류, 성능 이슈, 개선점 분석
2. **코드 최적화**: 더 효율적이고 읽기 쉬운 코드 제안
3. **버그 수정**: 발견된 오류에 대한 구체적인 수정 방안
4. **기능 확장**: 추가할 수 있는 유용한 기능 제안
5. **베스트 프랙티스**: Python/데이터 분석 모범 사례 적용

응답은 한국어로 제공하고, 구체적이고 실행 가능한 코드 예시를 포함해주세요.
코드 블록은 ```python으로 감싸서 명확하게 표시해주세요."""
        
        # 사용자 메시지 구성
        user_prompt = f"""
분석 대상: {context_description}

노트북 내용:
{context}

사용자 요청: {user_message}

위의 노트북 내용을 분석하고 사용자의 요청에 답변해주세요.
"""
        
        try:
            if provider == "azure":
                result = await self._call_azure_api(system_message, user_prompt)
            elif provider == "ollama":
                result = await self._call_ollama_api(system_message, user_prompt)
            else:
                return {"error": f"지원하지 않는 LLM 제공자: {provider}"}
            
            # 분석 결과에 추가 정보 포함
            result['analysis_info'] = {
                'total_cells_analyzed': len(cell_indices) if cell_indices else parsed_notebook['total_cells'],
                'cell_indices': cell_indices,
                'notebook_summary': {
                    'total_cells': parsed_notebook['total_cells'],
                    'code_cells': parsed_notebook['code_cells_count'],
                    'markdown_cells': parsed_notebook['markdown_cells_count']
                }
            }
            
            return result
        
        except Exception as e:
            logger.error(f"LLM API 호출 실패: {e}")
            return {"error": f"LLM API 호출 실패: {str(e)}"}

    async def check_connection(self, provider: str = None) -> Dict[str, bool]:
        """LLM 연결 상태 확인"""
        status = {
            "azure": False,
            "ollama": False
        }
        
        # Azure OpenAI 연결 확인
        if self.azure_available and (provider is None or provider == "azure"):
            try:
                status["azure"] = await self._check_azure_connection()
            except Exception as e:
                logger.error(f"Azure 연결 확인 실패: {e}")
        
        # Ollama 연결 확인
        if self.ollama_available and (provider is None or provider == "ollama"):
            try:
                status["ollama"] = await self._check_ollama_connection()
            except Exception as e:
                logger.error(f"Ollama 연결 확인 실패: {e}")
        
        return status
    
    async def _check_azure_connection(self) -> bool:
        """Azure OpenAI 연결 확인"""
        try:
            headers = {
                "Content-Type": "application/json",
                "api-key": settings.azure_openai_api_key
            }
            
            url = f"{settings.azure_openai_endpoint}/openai/deployments/{settings.azure_openai_deployment_name}/chat/completions?api-version={settings.azure_openai_api_version}"
            
            payload = {
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1,
                "temperature": 0
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=10) as response:
                    return response.status in [200, 400]  # 400도 연결은 성공
        except Exception as e:
            logger.error(f"Azure 연결 확인 오류: {e}")
            return False
    
    async def _check_ollama_connection(self) -> bool:
        """Ollama 연결 확인"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{settings.ollama_base_url}/api/tags", timeout=5) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Ollama 연결 확인 오류: {e}")
            return False
    
    async def analyze_notebook(self, notebook_content: str, user_message: str, provider: str = None) -> Dict[str, Any]:
        """노트북 내용 분석 및 수정 제안 (기존 호환성을 위한 메서드)"""
        return await self.analyze_notebook_cells(notebook_content, user_message, None, provider)
    
    async def _call_azure_api(self, system_message: str, user_message: str) -> Dict[str, Any]:
        """Azure OpenAI API 호출"""
        headers = {
            "Content-Type": "application/json",
            "api-key": settings.azure_openai_api_key
        }
        
        url = f"{settings.azure_openai_endpoint}/openai/deployments/{settings.azure_openai_deployment_name}/chat/completions?api-version={settings.azure_openai_api_version}"
        
        payload = {
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=60) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "response": result["choices"][0]["message"]["content"],
                        "provider": "azure",
                        "model": settings.azure_openai_deployment_name
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Azure API 오류 ({response.status}): {error_text}")
    
    async def _call_ollama_api(self, system_message: str, user_message: str) -> Dict[str, Any]:
        """Ollama API 호출"""
        payload = {
            "model": settings.ollama_default_model,
            "prompt": f"System: {system_message}\n\nUser: {user_message}\n\nAssistant:",
            "stream": False,
            "options": {
                "temperature": settings.temperature,
                "num_predict": settings.max_tokens
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{settings.ollama_base_url}/api/generate", 
                                  json=payload, timeout=120) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "response": result["response"],
                        "provider": "ollama",
                        "model": settings.ollama_default_model
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Ollama API 오류 ({response.status}): {error_text}")
    
    async def get_available_models(self) -> Dict[str, List[str]]:
        """사용 가능한 모델 목록 조회"""
        models = {
            "azure": [],
            "ollama": []
        }
        
        # Azure 모델 (설정에서 가져옴)
        if self.azure_available:
            models["azure"].append(settings.azure_openai_deployment_name)
        
        # Ollama 모델 목록 조회
        if self.ollama_available:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{settings.ollama_base_url}/api/tags", timeout=10) as response:
                        if response.status == 200:
                            result = await response.json()
                            models["ollama"] = [model["name"] for model in result.get("models", [])]
            except Exception as e:
                logger.error(f"Ollama 모델 목록 조회 실패: {e}")
        
        return models

    async def generate_response(self, messages: List[Dict[str, str]], model: str = None, 
                              stream: bool = False, **kwargs) -> Dict[str, Any]:
        """LLM 채팅을 위한 응답 생성 메서드"""
        try:
            # 모델이 지정되지 않은 경우 기본 모델 사용
            if not model:
                model = settings.azure_openai_deployment_name if self.azure_available else settings.ollama_default_model
            
            # 메시지 형식 검증
            if not messages or not isinstance(messages, list):
                raise ValueError("messages는 비어있지 않은 리스트여야 합니다")
            
            # 시스템 메시지와 일반 메시지 분리
            system_messages = [msg["content"] for msg in messages if msg.get("role") == "system"]
            user_messages = [msg for msg in messages if msg.get("role") in ["user", "assistant"]]
            
            # 시스템 메시지 결합
            system_message = "\n\n".join(system_messages) if system_messages else "당신은 도움이 되는 AI 어시스턴트입니다."
            
            # 대화 히스토리 구성
            conversation_history = []
            for msg in user_messages:
                if msg.get("role") == "user":
                    conversation_history.append(f"User: {msg['content']}")
                elif msg.get("role") == "assistant":
                    conversation_history.append(f"Assistant: {msg['content']}")
            
            # 마지막 사용자 메시지 추출
            last_user_message = None
            for msg in reversed(user_messages):
                if msg.get("role") == "user":
                    last_user_message = msg["content"]
                    break
            
            if not last_user_message:
                raise ValueError("사용자 메시지가 없습니다")
            
            # 대화 컨텍스트 구성
            if len(conversation_history) > 1:
                conversation_context = "\n".join(conversation_history[:-1])  # 마지막 메시지 제외
                user_prompt = f"대화 히스토리:\n{conversation_context}\n\n현재 사용자 메시지: {last_user_message}"
            else:
                user_prompt = last_user_message
            
            # 모델 타입에 따라 적절한 API 호출
            result = None
            if model.startswith("gpt-") or "azure" in model.lower():
                # Azure OpenAI API 호출
                result = await self._call_azure_api_chat(system_message, user_prompt, model)
            else:
                # Ollama API 호출
                result = await self._call_ollama_api_chat(system_message, user_prompt, model)
            
            if not result:
                raise Exception("LLM 응답 생성 실패")
            
            return {
                "content": result.get("response", ""),
                "usage": result.get("usage", {}),
                "model": model,
                "provider": result.get("provider", "unknown")
            }
            
        except Exception as e:
            logger.error(f"generate_response 실패: {e}")
            return {
                "content": "죄송합니다. 응답 생성 중 오류가 발생했습니다.",
                "error": str(e)
            }
    
    async def _call_azure_api_chat(self, system_message: str, user_message: str, model: str = None) -> Dict[str, Any]:
        """Azure OpenAI Chat API 호출 (채팅용)"""
        headers = {
            "Content-Type": "application/json",
            "api-key": settings.azure_openai_api_key
        }
        
        deployment_name = model or settings.azure_openai_deployment_name
        url = f"{settings.azure_openai_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={settings.azure_openai_api_version}"
        
        payload = {
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=60) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "response": result["choices"][0]["message"]["content"],
                        "provider": "azure",
                        "model": deployment_name,
                        "usage": result.get("usage", {})
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Azure API 오류 ({response.status}): {error_text}")
    
    async def _call_ollama_api_chat(self, system_message: str, user_message: str, model: str = None) -> Dict[str, Any]:
        """Ollama Chat API 호출 (채팅용)"""
        model_name = model or settings.ollama_default_model
        
        payload = {
            "model": model_name,
            "prompt": f"System: {system_message}\n\nUser: {user_message}\n\nAssistant:",
            "stream": False,
            "options": {
                "temperature": settings.temperature,
                "num_predict": settings.max_tokens
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{settings.ollama_base_url}/api/generate", 
                                  json=payload, timeout=120) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "response": result.get("response", ""),
                        "provider": "ollama",
                        "model": model_name,
                        "usage": {
                            "prompt_tokens": result.get("prompt_eval_count", 0),
                            "completion_tokens": result.get("eval_count", 0),
                            "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                        }
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Ollama API 오류 ({response.status}): {error_text}")

# 전역 LLM 서비스 인스턴스
llm_service = LLMService() 