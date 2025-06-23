"""
Worker Pool Manager for LLMOps

워커 풀을 관리하고, FlowProvider와 연동하여 동적으로 플로우를 로드하는 워커를 생성/관리
핫 리로딩 기능을 통해 무중단 플로우 업데이트 지원
"""

import os
import sys
import json
import time
import asyncio
import subprocess
import threading
import logging
from typing import Dict, Optional, Any, Tuple, List
from pathlib import Path
import psutil

from .flow_provider import flow_provider

logger = logging.getLogger(__name__)

class WorkerInfo:
    """워커 정보를 담는 클래스"""
    
    def __init__(self, process: subprocess.Popen, port: int, project_id: str, flow_id: str):
        self.process = process
        self.port = port
        self.project_id = project_id
        self.flow_id = flow_id
        self.created_at = time.time()
        self.last_used = time.time()
        self.status = "starting"  # starting, ready, error, terminated
        
    def update_last_used(self):
        """마지막 사용 시간 업데이트"""
        self.last_used = time.time()
        
    def get_age(self) -> float:
        """워커 생성 후 경과 시간 (초)"""
        return time.time() - self.created_at
        
    def get_idle_time(self) -> float:
        """마지막 사용 후 유휴 시간 (초)"""
        return time.time() - self.last_used

class WorkerPoolManager:
    """
    워커 풀을 관리하는 매니저 클래스
    FlowProvider와 연동하여 동적으로 플로우를 로드하고 워커를 관리
    """
    
    def __init__(self, max_workers: int = 10, worker_timeout: int = 1800):
        """
        WorkerPoolManager 초기화
        
        Args:
            max_workers: 최대 워커 수
            worker_timeout: 워커 유휴 타임아웃 (초)
        """
        self.max_workers = max_workers
        self.worker_timeout = worker_timeout
        self.workers: Dict[str, WorkerInfo] = {}  # key: f"{project_id}:{flow_id}"
        self.port_pool = list(range(8100, 8100 + max_workers * 2))  # 사용 가능한 포트 풀
        self.used_ports = set()
        self.lock = threading.Lock()
        
        # 워커 정리 태스크
        self._cleanup_task = None
        self._shutdown = False
        
        logger.info(f"WorkerPoolManager 초기화 완료 - 최대 워커: {max_workers}, 타임아웃: {worker_timeout}초")
    
    async def get_or_create_worker(
        self, 
        project_id: str, 
        flow_id: str, 
        user_id: str, 
        user_groups: List[str]
    ) -> Optional[Tuple[str, int]]:
        """
        워커를 가져오거나 새로 생성 (권한 검사 포함)
        
        Args:
            project_id: 프로젝트 ID
            flow_id: 플로우 ID
            user_id: 사용자 ID
            user_groups: 사용자 그룹 목록
            
        Returns:
            (worker_url, port) 또는 None (실패 시)
        """
        worker_key = f"{project_id}:{flow_id}"
        
        with self.lock:
            # 기존 워커 확인
            if worker_key in self.workers:
                worker_info = self.workers[worker_key]
                
                # 워커 프로세스가 살아있는지 확인
                if worker_info.process.poll() is None:
                    worker_info.update_last_used()
                    
                    # 워커 상태 확인 (헬스 체크)
                    if await self._health_check_worker(worker_info):
                        logger.debug(f"기존 워커 재사용: {worker_key} (port: {worker_info.port})")
                        return f"http://127.0.0.1:{worker_info.port}", worker_info.port
                
                # 죽은 워커 제거
                logger.warning(f"죽은 워커 제거: {worker_key}")
                self._remove_worker(worker_key)
        
        # 새 워커 생성 (Cold Start)
        return await self._create_new_worker(project_id, flow_id, user_id, user_groups)
    
    async def _create_new_worker(
        self, 
        project_id: str, 
        flow_id: str, 
        user_id: str, 
        user_groups: List[str]
    ) -> Optional[Tuple[str, int]]:
        """
        새 워커 생성
        
        Args:
            project_id: 프로젝트 ID
            flow_id: 플로우 ID
            
        Returns:
            (worker_url, port) 또는 None
        """
        worker_key = f"{project_id}:{flow_id}"
        
        try:
            # 워커 수 제한 확인
            if len(self.workers) >= self.max_workers:
                # 가장 오래된 유휴 워커 제거
                await self._cleanup_oldest_worker()
            
            # FlowProvider로부터 권한 검사 후 플로우 데이터 가져오기
            logger.info(f"FlowProvider에서 게시된 플로우 데이터 요청: {worker_key}, 사용자: {user_id}")
            flow_data = await flow_provider.get_published_flow(flow_id, user_id, user_groups)
            
            if flow_data is None:
                logger.error(f"플로우 데이터를 가져올 수 없음: {worker_key}")
                return None
            
            # 사용 가능한 포트 할당
            port = self._allocate_port()
            if port is None:
                logger.error("사용 가능한 포트가 없음")
                return None
            
            # 워커 프로세스 시작
            worker_process = await self._start_worker_process(
                project_id, flow_id, port, flow_data
            )
            
            if worker_process is None:
                self._release_port(port)
                return None
            
            # 워커 정보 등록
            worker_info = WorkerInfo(worker_process, port, project_id, flow_id)
            
            with self.lock:
                self.workers[worker_key] = worker_info
            
            # 워커 준비 대기
            if await self._wait_for_worker_ready(worker_info):
                logger.info(f"새 워커 생성 완료: {worker_key} (port: {port})")
                return f"http://127.0.0.1:{port}", port
            else:
                # 워커 시작 실패
                await self._remove_failed_worker(worker_key)
                return None
                
        except Exception as e:
            logger.error(f"워커 생성 실패: {worker_key} - {e}")
            return None
    
    async def _start_worker_process(
        self, 
        project_id: str, 
        flow_id: str, 
        port: int, 
        flow_data: Dict[str, Any]
    ) -> Optional[subprocess.Popen]:
        """
        워커 프로세스 시작
        
        Args:
            project_id: 프로젝트 ID
            flow_id: 플로우 ID
            port: 워커 포트
            flow_data: 플로우 JSON 데이터
            
        Returns:
            subprocess.Popen 객체 또는 None
        """
        try:
            # 워커 스크립트 경로
            worker_script = Path(__file__).parent / "worker.py"
            
            # 워커 프로세스 명령
            cmd = [
                sys.executable,
                str(worker_script),
                "--project_id", project_id,
                "--flow_id", flow_id,
                "--port", str(port)
            ]
            
            logger.debug(f"워커 프로세스 시작: {' '.join(cmd)}")
            
            # 플로우 데이터를 JSON 문자열로 변환
            flow_json_string = json.dumps(flow_data, ensure_ascii=False)
            
            # subprocess.Popen으로 워커 프로세스 시작 (stdin=PIPE 옵션 포함)
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # 버퍼링 비활성화
            )
            
            # 플로우 데이터를 워커의 표준 입력으로 전달 (비동기 처리)
            await asyncio.to_thread(
                self._send_flow_data_to_worker,
                process,
                flow_json_string
            )
            
            logger.info(f"워커 프로세스 시작됨: PID {process.pid}, Port {port}")
            return process
            
        except Exception as e:
            logger.error(f"워커 프로세스 시작 실패: {e}")
            return None
    
    def _send_flow_data_to_worker(
        self, 
        process: subprocess.Popen, 
        flow_json_string: str
    ):
        """
        워커 프로세스에 플로우 데이터 전송 (동기 함수)
        
        Args:
            process: 워커 프로세스
            flow_json_string: 플로우 JSON 문자열
        """
        try:
            # 표준 입력으로 플로우 데이터 전송
            process.stdin.write(flow_json_string)
            process.stdin.close()  # EOF 전송
            
            logger.debug(f"플로우 데이터 전송 완료: {len(flow_json_string)} 문자")
            
        except Exception as e:
            logger.error(f"플로우 데이터 전송 실패: {e}")
            try:
                process.terminate()
            except:
                pass
    
    async def _wait_for_worker_ready(self, worker_info: WorkerInfo, timeout: int = 30) -> bool:
        """
        워커가 준비될 때까지 대기
        
        Args:
            worker_info: 워커 정보
            timeout: 타임아웃 (초)
            
        Returns:
            워커 준비 여부
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 프로세스가 종료되었는지 확인
            if worker_info.process.poll() is not None:
                logger.error(f"워커 프로세스가 종료됨: {worker_info.project_id}:{worker_info.flow_id}")
                return False
            
            # 헬스 체크
            if await self._health_check_worker(worker_info):
                worker_info.status = "ready"
                return True
            
            await asyncio.sleep(1)
        
        logger.error(f"워커 준비 타임아웃: {worker_info.project_id}:{worker_info.flow_id}")
        return False
    
    async def _health_check_worker(self, worker_info: WorkerInfo) -> bool:
        """
        워커 헬스 체크
        
        Args:
            worker_info: 워커 정보
            
        Returns:
            헬스 체크 성공 여부
        """
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:{worker_info.port}/health",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("status") == "healthy"
                
        except Exception as e:
            logger.debug(f"워커 헬스 체크 실패: {worker_info.port} - {e}")
        
        return False
    
    def _allocate_port(self) -> Optional[int]:
        """사용 가능한 포트 할당"""
        for port in self.port_pool:
            if port not in self.used_ports:
                self.used_ports.add(port)
                return port
        return None
    
    def _release_port(self, port: int):
        """포트 해제"""
        self.used_ports.discard(port)
    
    def _remove_worker(self, worker_key: str):
        """워커 제거 (락 안에서 호출)"""
        if worker_key in self.workers:
            worker_info = self.workers[worker_key]
            
            # 프로세스 종료
            try:
                if worker_info.process.poll() is None:
                    worker_info.process.terminate()
                    # 강제 종료 대기
                    try:
                        worker_info.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        worker_info.process.kill()
            except Exception as e:
                logger.warning(f"워커 프로세스 종료 실패: {e}")
            
            # 포트 해제
            self._release_port(worker_info.port)
            
            # 워커 풀에서 제거
            del self.workers[worker_key]
            
            logger.info(f"워커 제거 완료: {worker_key}")
    
    async def _remove_failed_worker(self, worker_key: str):
        """실패한 워커 제거"""
        with self.lock:
            self._remove_worker(worker_key)
    
    async def _cleanup_oldest_worker(self):
        """가장 오래된 유휴 워커 제거"""
        oldest_worker_key = None
        oldest_idle_time = 0
        
        with self.lock:
            for worker_key, worker_info in self.workers.items():
                idle_time = worker_info.get_idle_time()
                if idle_time > oldest_idle_time:
                    oldest_idle_time = idle_time
                    oldest_worker_key = worker_key
        
        if oldest_worker_key:
            logger.info(f"가장 오래된 유휴 워커 제거: {oldest_worker_key} (유휴시간: {oldest_idle_time:.1f}초)")
            with self.lock:
                self._remove_worker(oldest_worker_key)
    
    async def reload_worker(self, project_id: str, flow_id: str) -> bool:
        """
        워커 핫 리로딩
        
        Args:
            project_id: 프로젝트 ID
            flow_id: 플로우 ID
            
        Returns:
            리로딩 성공 여부
        """
        worker_key = f"{project_id}:{flow_id}"
        
        try:
            # 1. FlowProvider 캐시 무효화 (현재는 캐시가 없으므로 스킵)
            logger.info(f"플로우 캐시 무효화 (스킵): {worker_key}")
            
            # 2. 기존 워커 제거
            with self.lock:
                if worker_key in self.workers:
                    logger.info(f"기존 워커 종료: {worker_key}")
                    self._remove_worker(worker_key)
                else:
                    logger.info(f"리로딩할 워커가 없음: {worker_key}")
            
            logger.info(f"워커 리로딩 완료: {worker_key}")
            return True
            
        except Exception as e:
            logger.error(f"워커 리로딩 실패: {worker_key} - {e}")
            return False
    
    async def get_worker_stats(self) -> Dict[str, Any]:
        """워커 풀 통계 정보 반환"""
        with self.lock:
            stats = {
                "total_workers": len(self.workers),
                "max_workers": self.max_workers,
                "used_ports": len(self.used_ports),
                "available_ports": len(self.port_pool) - len(self.used_ports),
                "workers": []
            }
            
            for worker_key, worker_info in self.workers.items():
                worker_stats = {
                    "key": worker_key,
                    "project_id": worker_info.project_id,
                    "flow_id": worker_info.flow_id,
                    "port": worker_info.port,
                    "status": worker_info.status,
                    "age_seconds": worker_info.get_age(),
                    "idle_seconds": worker_info.get_idle_time(),
                    "process_alive": worker_info.process.poll() is None
                }
                stats["workers"].append(worker_stats)
        
        return stats
    
    async def shutdown(self):
        """워커 매니저 종료"""
        self._shutdown = True
        
        with self.lock:
            logger.info(f"전체 워커 종료 시작: {len(self.workers)}개")
            
            for worker_key in list(self.workers.keys()):
                self._remove_worker(worker_key)
        
        logger.info("WorkerPoolManager 종료 완료")


# 싱글턴 인스턴스 생성
worker_manager = WorkerPoolManager() 