"""
Graph Builder for FlowRunner Pro

Flow JSON으로부터 실행 가능한 LangChain (LCEL) 체인을 만드는 핵심 엔진
노드들을 인스턴스화하고 연결하여 최종 실행 가능한 체인을 구성
"""

import logging
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, deque

try:
    from langchain_core.runnables.base import Runnable
    from langchain_core.runnables import RunnableLambda, RunnablePassthrough
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
        
        def __ror__(self, other):
            """역방향 파이프 연산자 지원"""
            return ChainedRunnable(other, self)
    
    class RunnableLambda(Runnable):
        """RunnableLambda 대체 구현"""
        def __init__(self, func):
            self.func = func
        
        def invoke(self, input_data: Any) -> Any:
            return self.func(input_data)
    
    class RunnablePassthrough(Runnable):
        """RunnablePassthrough 대체 구현"""
        def invoke(self, input_data: Any) -> Any:
            return input_data
    
    class ChainedRunnable(Runnable):
        """체인된 Runnable 대체 구현"""
        def __init__(self, first, second):
            self.first = first
            self.second = second
        
        def invoke(self, input_data: Any) -> Any:
            intermediate = self.first.invoke(input_data)
            return self.second.invoke(intermediate)

from .component_registry import get_component_class

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    그래프 빌더
    
    Flow JSON 데이터를 받아서 실행 가능한 LangChain 체인으로 변환하는 핵심 엔진
    노드 인스턴스화, 엣지 분석, 위상 정렬, 체인 연결을 담당
    """
    
    def __init__(self, flow_data: Dict[str, Any]):
        """
        GraphBuilder 초기화
        
        Args:
            flow_data: 데이터베이스에서 파싱된 Flow JSON 데이터
                      예상 구조: {
                          "nodes": [...],
                          "edges": [...],
                          "viewport": {...},
                          ...
                      }
        """
        self.flow_data = flow_data
        self.built_nodes: Dict[str, Runnable] = {}
        self.node_metadata: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.adjacency_list: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = defaultdict(int)
        
        logger.info(f"GraphBuilder 초기화: {len(self.flow_data.get('nodes', []))}개 노드, {len(self.flow_data.get('edges', []))}개 엣지")
    
    def build(self) -> Runnable:
        """
        Flow JSON으로부터 실행 가능한 체인을 빌드합니다.
        
        Returns:
            최종 실행 가능한 Runnable 체인
            
        Raises:
            ValueError: 플로우 데이터가 유효하지 않은 경우
            RuntimeError: 체인 빌드 과정에서 오류가 발생한 경우
        """
        try:
            logger.info("체인 빌드 프로세스 시작")
            
            # 1. 플로우 데이터 검증
            self._validate_flow_data()
            
            # 2. 노드 인스턴스화
            self._instantiate_nodes()
            
            # 3. 엣지 분석 및 그래프 구조 생성
            self._analyze_edges()
            
            # 4. 위상 정렬을 통한 실행 순서 결정
            execution_order = self._topological_sort()
            
            # 5. 체인 연결
            final_chain = self._build_chain(execution_order)
            
            logger.info("체인 빌드 완료")
            return final_chain
            
        except Exception as e:
            logger.error(f"체인 빌드 실패: {e}")
            raise RuntimeError(f"체인을 빌드할 수 없습니다: {e}") from e
    
    def _validate_flow_data(self) -> None:
        """플로우 데이터의 유효성을 검증합니다."""
        if not isinstance(self.flow_data, dict):
            raise ValueError("flow_data는 딕셔너리여야 합니다")
        
        if "nodes" not in self.flow_data:
            raise ValueError("flow_data에 'nodes' 키가 없습니다")
        
        if "edges" not in self.flow_data:
            raise ValueError("flow_data에 'edges' 키가 없습니다")
        
        nodes = self.flow_data["nodes"]
        if not isinstance(nodes, list) or len(nodes) == 0:
            raise ValueError("최소 하나 이상의 노드가 필요합니다")
        
        logger.info("플로우 데이터 검증 완료")
    
    def _instantiate_nodes(self) -> None:
        """모든 노드를 인스턴스화합니다."""
        nodes = self.flow_data["nodes"]
        
        for node_data in nodes:
            try:
                # 노드 기본 정보 추출
                node_id = node_data.get("id")
                if not node_id:
                    logger.warning("노드 ID가 없는 노드를 건너뜁니다")
                    continue
                
                # 노드 타입 추출 - data.type을 우선 사용 (이미 올바른 형식)
                node_data_obj = node_data.get("data", {})
                
                node_type = (
                    node_data_obj.get("type") or  # 컴포넌트 타입 (ChatInput, Ollama 등) - 우선 사용
                    node_data_obj.get("id") or  # 컴포넌트 ID (chat_input, ollama 등)
                    node_data.get("type")  # React Flow 노드 타입 (fallback)
                )
                
                # data.id를 사용하는 경우 PascalCase로 변환
                if node_type and node_type == node_data_obj.get("id"):
                    # 언더스코어를 제거하고 PascalCase로 변환 (chat_input -> ChatInput)
                    if "_" in node_type:
                        parts = node_type.split("_")
                        node_type = "".join(word.capitalize() for word in parts)
                        logger.info(f"노드 {node_id}: {node_data_obj.get('id')} -> {node_type}")
                
                if not node_type:
                    logger.warning(f"노드 {node_id}의 타입을 찾을 수 없습니다")
                    continue
                
                # 컴포넌트 클래스 가져오기
                try:
                    component_class = get_component_class(node_type)
                except (ValueError, ImportError, AttributeError) as e:
                    logger.error(f"노드 {node_id} (타입: {node_type}) 컴포넌트 로드 실패: {e}")
                    # 기본 패스스루 노드로 대체
                    self.built_nodes[node_id] = RunnablePassthrough()
                    continue
                
                # 컴포넌트 인스턴스 생성
                component_instance = component_class()
                
                # Runnable 객체 생성
                runnable = component_instance.get_runnable(node_data)
                
                # 빌드된 노드에 저장
                self.built_nodes[node_id] = runnable
                
                # 메타데이터 저장
                self.node_metadata[node_id] = {
                    "type": node_type,
                    "position": node_data.get("position", {}),
                    "data": node_data.get("data", {})
                }
                
                logger.info(f"노드 인스턴스화 완료: {node_id} ({node_type})")
                
            except Exception as e:
                logger.error(f"노드 인스턴스화 실패: {node_data.get('id', 'unknown')} - {e}")
                continue
        
        logger.info(f"총 {len(self.built_nodes)}개 노드 인스턴스화 완료")
    
    def _analyze_edges(self) -> None:
        """엣지를 분석하여 그래프 구조를 생성합니다."""
        edges = self.flow_data.get("edges", [])
        
        for edge in edges:
            try:
                source = edge.get("source")
                target = edge.get("target")
                
                if not source or not target:
                    logger.warning(f"엣지에 source 또는 target이 없습니다: {edge}")
                    continue
                
                # 그래프 구조 업데이트
                self.adjacency_list[source].append(target)
                self.in_degree[target] += 1
                
                # 진입 차수가 없는 노드들의 진입 차수를 0으로 초기화
                if source not in self.in_degree:
                    self.in_degree[source] = 0
                
                # 엣지 저장
                self.edges.append(edge)
                logger.debug(f"엣지 추가: {source} -> {target}")
                
            except Exception as e:
                logger.error(f"엣지 처리 실패: {edge} - {e}")
        
        logger.info(f"총 {len(self.edges)}개 엣지 분석 완료")
    
    def _topological_sort(self) -> List[str]:
        """
        위상 정렬을 통해 노드의 실행 순서를 결정합니다.
        
        Returns:
            위상 정렬된 노드 ID 리스트
            
        Raises:
            RuntimeError: 순환 참조가 있는 경우
        """
        # 칸의 위상 정렬 알고리즘 사용
        queue = deque()
        in_degree_copy = self.in_degree.copy()
        
        # 진입 차수가 0인 노드들을 큐에 추가
        for node_id, degree in in_degree_copy.items():
            if degree == 0:
                queue.append(node_id)
        
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # 현재 노드와 연결된 모든 노드의 진입 차수 감소
            for neighbor in self.adjacency_list[current]:
                in_degree_copy[neighbor] -= 1
                if in_degree_copy[neighbor] == 0:
                    queue.append(neighbor)
        
        # 순환 참조 검사
        if len(result) != len(self.built_nodes):
            missing_nodes = set(self.built_nodes.keys()) - set(result)
            raise RuntimeError(f"플로우에 순환 참조가 있습니다. 처리되지 않은 노드: {missing_nodes}")
        
        logger.info(f"위상 정렬 완료: {' -> '.join(result)}")
        return result
    
    def _build_chain(self, execution_order: List[str]) -> Runnable:
        """
        실행 순서에 따라 최종 체인을 빌드합니다.
        
        Args:
            execution_order: 위상 정렬된 노드 실행 순서
            
        Returns:
            최종 실행 가능한 체인
        """
        if not execution_order:
            logger.warning("실행할 노드가 없습니다. 패스스루 체인을 반환합니다")
            return RunnablePassthrough()
        
        # 🔍 데이터 흐름 추적 로그
        logger.info("=== 데이터 흐름 추적 시작 ===")
        logger.info(f"실행 순서: {' → '.join(execution_order)}")
        
        # 각 노드의 입력/출력 연결 정보 로깅
        for i, node_id in enumerate(execution_order):
            incoming_edges = [edge for edge in self.edges if edge.get('target') == node_id]
            outgoing_edges = [edge for edge in self.edges if edge.get('source') == node_id]
            
            logger.info(f"노드 {i+1}: {node_id}")
            input_connections = [f"{edge.get('source')}:{edge.get('sourceHandle', 'default')}" for edge in incoming_edges]
            output_connections = [f"{edge.get('target')}:{edge.get('targetHandle', 'default')}" for edge in outgoing_edges]
            logger.info(f"  ↳ 입력: {input_connections}")
            logger.info(f"  ↳ 출력: {output_connections}")
            
            # 노드 메타데이터 로깅
            node_meta = self.node_metadata.get(node_id, {})
            logger.info(f"  ↳ 타입: {node_meta.get('type', 'unknown')}")
            logger.info(f"  ↳ 위치: {node_meta.get('position', {})}")
        
        # 단일 노드인 경우
        if len(execution_order) == 1:
            node_id = execution_order[0]
            logger.info(f"단일 노드 체인: {node_id}")
            return self._create_instrumented_node(node_id, self.built_nodes[node_id])
        
        # 다중 노드 체인 빌드
        try:
            # 시작 노드 (진입 차수가 0인 노드들 중 첫 번째)
            start_nodes = [node_id for node_id in execution_order if self.in_degree[node_id] == 0]
            
            if not start_nodes:
                # 모든 노드가 연결된 경우, 첫 번째 노드를 시작점으로 사용
                start_node_id = execution_order[0]
            else:
                start_node_id = start_nodes[0]
            
            logger.info(f"시작 노드: {start_node_id}")
            
            # 체인 빌드: 선형 체인으로 단순화
            chain = self._create_instrumented_node(start_node_id, self.built_nodes[start_node_id])
            
            # 나머지 노드들을 순서대로 연결
            for node_id in execution_order[1:]:
                if node_id != start_node_id:
                    next_runnable = self._create_instrumented_node(node_id, self.built_nodes[node_id])
                    chain = chain | next_runnable
            
            logger.info(f"체인 빌드 완료: {len(execution_order)}개 노드 연결")
            logger.info("=== 데이터 흐름 추적 완료 ===")
            return chain
            
        except Exception as e:
            logger.error(f"체인 빌드 실패: {e}")
            # 폴백: 모든 노드를 단순 순차 실행
            return self._build_fallback_chain(execution_order)
    
    def _create_instrumented_node(self, node_id: str, runnable: Runnable) -> Runnable:
        """
        노드 실행을 계측하는 래퍼를 생성합니다.
        
        Args:
            node_id: 노드 ID
            runnable: 원본 Runnable
            
        Returns:
            계측된 Runnable
        """
        def instrumented_invoke(input_data: Any) -> Any:
            """계측된 노드 실행 함수"""
            try:
                # 🔍 노드 실행 시작 로그
                logger.info(f"🚀 노드 실행 시작: {node_id}")
                logger.info(f"  ↳ 입력 데이터 타입: {type(input_data).__name__}")
                
                # 입력 데이터 상세 로깅
                if isinstance(input_data, dict):
                    logger.info(f"  ↳ 입력 키: {list(input_data.keys())}")
                    for key, value in input_data.items():
                        if isinstance(value, str) and len(value) > 100:
                            logger.info(f"  ↳ {key}: {value[:100]}... ({len(value)} 문자)")
                        else:
                            logger.info(f"  ↳ {key}: {value}")
                else:
                    logger.info(f"  ↳ 입력 값: {str(input_data)[:200]}...")
                
                # 🔍 템플릿 바인딩 로그 (노드 메타데이터에서 템플릿 정보 추출)
                node_meta = self.node_metadata.get(node_id, {})
                node_data = node_meta.get('data', {})
                field_values = node_data.get('fieldValues', {})
                
                # 템플릿이 있는 필드들 검사
                template_fields = ['system_message', 'prompt', 'template', 'instruction']
                for field_name in template_fields:
                    if field_name in field_values:
                        template_value = field_values[field_name]
                        if isinstance(template_value, str) and '{' in template_value:
                            logger.info(f"📝 템플릿 바인딩 감지: {node_id}.{field_name}")
                            logger.info(f"  ↳ 원본 템플릿: {template_value}")
                            
                            # 변수 추출 (간단한 정규식 사용)
                            import re
                            variables = re.findall(r'{([^}]+)}', template_value)
                            logger.info(f"  ↳ 감지된 변수: {variables}")
                            
                            # 변수 바인딩 시도
                            if isinstance(input_data, dict):
                                bound_template = template_value
                                for var in variables:
                                    if var in input_data:
                                        value = input_data[var]
                                        var_placeholder = "{" + var + "}"
                                        bound_template = bound_template.replace(var_placeholder, str(value))
                                        logger.info(f"  ↳ {var} = {value}")
                                
                                logger.info(f"  ↳ 바인딩된 템플릿: {bound_template}")
                
                # 원본 Runnable 실행
                import time
                start_time = time.time()
                result = runnable.invoke(input_data)
                end_time = time.time()
                
                # 🔍 노드 실행 완료 로그
                execution_time_ms = int((end_time - start_time) * 1000)
                logger.info(f"✅ 노드 실행 완료: {node_id} ({execution_time_ms}ms)")
                logger.info(f"  ↳ 출력 데이터 타입: {type(result).__name__}")
                
                # 출력 데이터 상세 로깅
                if isinstance(result, dict):
                    logger.info(f"  ↳ 출력 키: {list(result.keys())}")
                    for key, value in result.items():
                        if isinstance(value, str) and len(value) > 100:
                            logger.info(f"  ↳ {key}: {value[:100]}... ({len(value)} 문자)")
                        else:
                            logger.info(f"  ↳ {key}: {value}")
                elif isinstance(result, str):
                    if len(result) > 200:
                        logger.info(f"  ↳ 출력: {result[:200]}... ({len(result)} 문자)")
                    else:
                        logger.info(f"  ↳ 출력: {result}")
                else:
                    logger.info(f"  ↳ 출력: {str(result)[:200]}...")
                
                return result
                
            except Exception as e:
                logger.error(f"❌ 노드 실행 실패: {node_id} - {e}")
                # 실행 실패 시 입력 데이터 그대로 반환
                return input_data
        
        return RunnableLambda(instrumented_invoke)
    
    def _build_fallback_chain(self, execution_order: List[str]) -> Runnable:
        """
        폴백 체인을 빌드합니다 (단순 순차 실행).
        
        Args:
            execution_order: 노드 실행 순서
            
        Returns:
            폴백 체인
        """
        logger.warning("폴백 체인 빌드 모드")
        
        def sequential_execution(input_data: Any) -> Any:
            """순차적으로 모든 노드를 실행"""
            current_data = input_data
            
            for node_id in execution_order:
                try:
                    runnable = self.built_nodes[node_id]
                    current_data = runnable.invoke(current_data)
                    logger.debug(f"노드 {node_id} 실행 완료")
                except Exception as e:
                    logger.error(f"노드 {node_id} 실행 실패: {e}")
                    # 실행 실패 시 이전 데이터 유지
                    pass
            
            return current_data
        
        return RunnableLambda(sequential_execution)
    
    def get_execution_plan(self) -> Dict[str, Any]:
        """
        실행 계획 정보를 반환합니다.
        
        Returns:
            실행 계획 딕셔너리
        """
        try:
            execution_order = self._topological_sort()
            
            return {
                "node_count": len(self.built_nodes),
                "edge_count": len(self.edges),
                "execution_order": execution_order,
                "start_nodes": [node_id for node_id in execution_order if self.in_degree[node_id] == 0],
                "end_nodes": [node_id for node_id in execution_order if not self.adjacency_list[node_id]],
                "node_types": {node_id: meta["type"] for node_id, meta in self.node_metadata.items()}
            }
        except Exception as e:
            logger.error(f"실행 계획 생성 실패: {e}")
            return {
                "error": str(e),
                "node_count": len(self.built_nodes),
                "edge_count": len(self.edges)
            }
    
    def validate_graph(self) -> Dict[str, Any]:
        """
        그래프의 유효성을 검증합니다.
        
        Returns:
            검증 결과 딕셔너리
        """
        issues = []
        warnings = []
        
        try:
            logger.info("🔍 그래프 위상 검증 시작")
            
            # 1. 기본 구조 검증
            if not self.built_nodes:
                issues.append("노드가 없습니다")
                return {
                    "valid": False,
                    "issues": issues,
                    "warnings": warnings,
                    "error": "빈 그래프"
                }
            
            # 2. 고립된 노드 검사
            isolated_nodes = []
            for node_id in self.built_nodes.keys():
                has_incoming = any(node_id in targets for targets in self.adjacency_list.values())
                has_outgoing = bool(self.adjacency_list[node_id])
                
                if not has_incoming and not has_outgoing:
                    isolated_nodes.append(node_id)
            
            if isolated_nodes:
                warnings.append(f"고립된 노드: {isolated_nodes}")
                logger.warning(f"고립된 노드 발견: {isolated_nodes}")
            
            # 3. 순환 참조 검사 (Kahn's Algorithm 기반)
            try:
                execution_order = self._topological_sort()
                logger.info(f"✅ 순환 참조 없음 - 실행 순서: {' → '.join(execution_order)}")
            except RuntimeError as e:
                issues.append(f"순환 참조 오류: {e}")
                logger.error(f"❌ 순환 참조 발견: {e}")
            
            # 4. 시작/끝 노드 검사
            start_nodes = [node_id for node_id in self.built_nodes.keys() if self.in_degree[node_id] == 0]
            end_nodes = [node_id for node_id in self.built_nodes.keys() if not self.adjacency_list[node_id]]
            
            if not start_nodes:
                issues.append("시작 노드가 없습니다 (모든 노드에 입력이 있음)")
                logger.error("❌ 시작 노드 없음")
            else:
                logger.info(f"✅ 시작 노드: {start_nodes}")
            
            if not end_nodes:
                warnings.append("끝 노드가 없습니다 (모든 노드에서 출력이 있음)")
                logger.warning("⚠️ 끝 노드 없음")
            else:
                logger.info(f"✅ 끝 노드: {end_nodes}")
            
            # 5. 노드 타입별 연결 규칙 검증
            type_validation_issues = self._validate_node_type_connections()
            if type_validation_issues:
                issues.extend(type_validation_issues)
            
            # 6. 핸들 연결 유효성 검사
            handle_validation_issues = self._validate_handle_connections()
            if handle_validation_issues:
                issues.extend(handle_validation_issues)
            
            # 7. 연결성 검사 (모든 노드가 연결되어 있는지)
            connectivity_issues = self._validate_connectivity()
            if connectivity_issues:
                warnings.extend(connectivity_issues)
            
            # 최종 결과
            is_valid = len(issues) == 0
            logger.info(f"🔍 그래프 위상 검증 완료 - 유효: {is_valid}")
            logger.info(f"  ↳ 이슈: {len(issues)}개, 경고: {len(warnings)}개")
            
            return {
                "valid": is_valid,
                "issues": issues,
                "warnings": warnings,
                "start_nodes": start_nodes,
                "end_nodes": end_nodes,
                "isolated_nodes": isolated_nodes,
                "node_count": len(self.built_nodes),
                "edge_count": len(self.edges),
                "validation_details": {
                    "has_cycles": len([issue for issue in issues if "순환" in issue]) > 0,
                    "has_isolated_nodes": len(isolated_nodes) > 0,
                    "has_start_nodes": len(start_nodes) > 0,
                    "has_end_nodes": len(end_nodes) > 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 그래프 검증 중 오류: {e}")
            return {
                "valid": False,
                "issues": [f"검증 과정에서 오류 발생: {e}"],
                "warnings": [],
                "error": str(e)
            }
    
    def _validate_node_type_connections(self) -> List[str]:
        """노드 타입별 연결 규칙을 검증합니다."""
        issues = []
        
        try:
            for edge in self.edges:
                source_id = edge.get("source")
                target_id = edge.get("target")
                
                if not source_id or not target_id:
                    continue
                
                source_meta = self.node_metadata.get(source_id, {})
                target_meta = self.node_metadata.get(target_id, {})
                
                source_type = source_meta.get("type", "unknown")
                target_type = target_meta.get("type", "unknown")
                
                # 입력 노드끼리 연결 금지
                if source_type == "input" and target_type == "input":
                    issues.append(f"입력 노드끼리 연결 불가: {source_id} -> {target_id}")
                
                # 출력 노드에서 다른 노드로 연결 금지 (출력은 끝점이어야 함)
                if source_type == "output":
                    issues.append(f"출력 노드에서 다른 노드로 연결 불가: {source_id} -> {target_id}")
                    
                logger.debug(f"연결 규칙 검증: {source_type}({source_id}) -> {target_type}({target_id})")
        
        except Exception as e:
            logger.error(f"노드 타입 연결 검증 실패: {e}")
            
        return issues
    
    def _validate_handle_connections(self) -> List[str]:
        """핸들 연결의 유효성을 검증합니다."""
        issues = []
        
        try:
            # 같은 타겟 핸들에 여러 연결이 있는지 검사
            target_handles = {}
            
            for edge in self.edges:
                target_id = edge.get("target")
                target_handle = edge.get("targetHandle", "default")
                
                if not target_id:
                    continue
                    
                handle_key = f"{target_id}:{target_handle}"
                
                if handle_key in target_handles:
                    target_handles[handle_key].append(edge)
                else:
                    target_handles[handle_key] = [edge]
            
            # 중복 연결 검사
            for handle_key, edges in target_handles.items():
                if len(edges) > 1:
                    source_info = [f"{e.get('source')}:{e.get('sourceHandle', 'default')}" for e in edges]
                    issues.append(f"핸들 {handle_key}에 중복 연결: {', '.join(source_info)}")
                    
        except Exception as e:
            logger.error(f"핸들 연결 검증 실패: {e}")
            
        return issues
    
    def _validate_connectivity(self) -> List[str]:
        """그래프 연결성을 검증합니다."""
        warnings = []
        
        try:
            if len(self.built_nodes) <= 1:
                return warnings
                
            # DFS로 모든 노드가 연결되어 있는지 확인
            visited = set()
            start_node = next(iter(self.built_nodes.keys()))
            
            def dfs(node_id: str):
                if node_id in visited:
                    return
                visited.add(node_id)
                
                # 나가는 연결
                for neighbor in self.adjacency_list.get(node_id, []):
                    dfs(neighbor)
                
                # 들어오는 연결 (역방향 탐색)
                for source, targets in self.adjacency_list.items():
                    if node_id in targets:
                        dfs(source)
            
            dfs(start_node)
            
            # 연결되지 않은 노드들
            disconnected_nodes = set(self.built_nodes.keys()) - visited
            if disconnected_nodes:
                warnings.append(f"연결되지 않은 노드 그룹: {list(disconnected_nodes)}")
                
        except Exception as e:
            logger.error(f"연결성 검증 실패: {e}")
            
        return warnings 