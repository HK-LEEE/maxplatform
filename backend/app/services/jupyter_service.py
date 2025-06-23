import subprocess
import signal
import os
import sys
import psutil
import json
from typing import Dict, Optional
from ..models.workspace import Workspace
from ..utils.workspace import find_available_port, generate_jupyter_token
from ..config import settings
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class JupyterService:
    def __init__(self):
        self.processes: Dict[int, subprocess.Popen] = {}  # workspace_id -> process
    
    def _get_python_command(self):
        """현재 Python 실행 파일 경로 반환"""
        return sys.executable
    
    def _create_jupyter_ai_config(self, workspace_path: str, workspace_id: int) -> str:
        """사용자별 Jupyter AI 설정 파일 생성"""
        jupyter_config_dir = Path(workspace_path) / ".jupyter"
        jupyter_config_dir.mkdir(parents=True, exist_ok=True)
        
        # 사용 가능한 프로바이더 목록 생성
        allowed_providers = []
        model_parameters = {}
        
        # GPT4All (API 키 불필요 - 로컬 모델)
        allowed_providers.append("gpt4all")
        
        # OpenAI (API 키가 있는 경우만)
        if settings.openai_api_key and settings.openai_api_key != "your-openai-api-key-here":
            allowed_providers.append("openai")
            allowed_providers.append("openai-chat")
            # OpenAI 모델별 설정
            for model in settings.ai_openai_models.split(","):
                model = model.strip()
                if model:
                    model_parameters[f"openai-chat:{model}"] = {
                        "temperature": settings.ai_temperature,
                        "max_tokens": settings.ai_max_tokens
                    }
        
        # Anthropic (API 키가 있는 경우만)
        if settings.anthropic_api_key and settings.anthropic_api_key != "your-anthropic-api-key-here":
            allowed_providers.append("anthropic")
            allowed_providers.append("anthropic-chat")
            # Anthropic 모델별 설정
            for model in settings.ai_anthropic_models.split(","):
                model = model.strip()
                if model:
                    model_parameters[f"anthropic-chat:{model}"] = {
                        "temperature": settings.ai_temperature,
                        "max_tokens": settings.ai_max_tokens
                    }
        
        # Google Gemini (API 키가 있는 경우만)
        if settings.google_api_key and settings.google_api_key != "your-google-api-key-here":
            allowed_providers.append("gemini")
            # Gemini 모델별 설정
            for model in settings.ai_google_models.split(","):
                model = model.strip()
                if model:
                    model_parameters[f"gemini:{model}"] = {
                        "temperature": settings.ai_temperature,
                        "max_tokens": settings.ai_max_tokens
                    }
        
        # Ollama (로컬 설치되어 있는 경우)
        try:
            import requests
            ollama_response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=2)
            if ollama_response.status_code == 200:
                allowed_providers.append("ollama")
                model_parameters[f"ollama:{settings.ollama_default_model}"] = {
                    "temperature": settings.ai_temperature,
                    "max_tokens": settings.ai_max_tokens
                }
        except Exception:
            pass  # Ollama가 설치되지 않은 경우 무시
        
        # Jupyter AI 설정 생성
        ai_config = {
            "AiExtension": {
                "default_language_model": settings.ai_default_model,
                "allowed_providers": allowed_providers,
                "default_max_chat_history": settings.ai_max_chat_history,
                "model_parameters": model_parameters,
                # API 키는 환경변수에서 자동으로 로드됨
            }
        }
        
        # 설정 파일 저장
        config_file = jupyter_config_dir / "jupyter_jupyter_ai_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(ai_config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Jupyter AI 설정 파일 생성: {config_file}")
        logger.info(f"사용 가능한 프로바이더: {allowed_providers}")
        
        return str(config_file)
    
    def _ensure_jupyter_ai_installed(self, python_exe: str) -> bool:
        """Jupyter AI가 설치되어 있는지 확인하고 필요시 설치"""
        try:
            # Jupyter AI 설치 확인
            result = subprocess.run([
                python_exe, "-c", "import jupyter_ai; print('Jupyter AI 설치됨')"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("Jupyter AI가 이미 설치되어 있습니다.")
                return True
            
            # 설치되지 않은 경우 설치 시도
            logger.info("Jupyter AI 설치 중...")
            install_result = subprocess.run([
                python_exe, "-m", "pip", "install", "jupyter-ai[all]", "--quiet"
            ], capture_output=True, text=True, timeout=300)
            
            if install_result.returncode == 0:
                logger.info("Jupyter AI 설치 완료")
                return True
            else:
                logger.error(f"Jupyter AI 설치 실패: {install_result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Jupyter AI 설치 확인 중 오류: {e}")
            return False
    
    def start_jupyter_lab(self, workspace: Workspace, db_session=None) -> tuple[int, str]:
        """Jupyter Lab 인스턴스 시작"""
        print(f"=== Jupyter Lab 시작 요청 ===")
        print(f"워크스페이스 ID: {workspace.id}")
        print(f"워크스페이스 이름: {workspace.name}")
        print(f"현재 포트: {workspace.jupyter_port}")
        print(f"현재 상태: {workspace.jupyter_status}")
        
        # 이미 실행 중인 경우 확인
        if workspace.id in self.processes and self.is_process_running(workspace.id):
            if workspace.jupyter_port and workspace.jupyter_status == "running":
                print(f"이미 실행 중인 Jupyter Lab 발견 - 포트: {workspace.jupyter_port}")
                return workspace.jupyter_port, workspace.jupyter_token or "noauth"
            else:
                # 프로세스는 있지만 상태가 일치하지 않는 경우 정리
                print("프로세스 상태 불일치 - 정리 중...")
                del self.processes[workspace.id]
        
        # 기존 포트가 있지만 프로세스가 죽었을 수 있으므로 확인
        if workspace.jupyter_port:
            print(f"기존 포트 {workspace.jupyter_port} 상태 확인 중...")
            import socket
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = test_sock.connect_ex(('localhost', workspace.jupyter_port))
            test_sock.close()
            
            if result == 0:
                print(f"포트 {workspace.jupyter_port}가 여전히 사용 중 - 새 포트 할당")
            else:
                print(f"포트 {workspace.jupyter_port}가 해제됨")
        
        # 데이터베이스 세션을 사용하여 사용 가능한 포트 찾기
        try:
            port = find_available_port(db_session)
            print(f"할당된 새 포트: {port}")
        except Exception as e:
            print(f"포트 할당 실패: {e}")
            raise Exception(f"사용 가능한 포트를 찾을 수 없습니다: {e}")
        
        # 토큰 생성 (간단한 고정 토큰 사용)
        token = "simple123"
        
        # 워크스페이스 디렉토리 확인 및 생성
        if not os.path.exists(workspace.path):
            os.makedirs(workspace.path, exist_ok=True)
            print(f"워크스페이스 디렉토리 생성: {workspace.path}")
        
        # Python 실행 파일 경로
        python_exe = self._get_python_command()
        
        # 커널 설정 확인 및 설치
        print("Jupyter 커널 설정 확인 중...")
        kernel_ready = self._ensure_python_kernel(workspace.id, python_exe)
        if not kernel_ready:
            print("경고: 커널 설정에 문제가 있을 수 있습니다. 계속 진행합니다.")
        
        # Jupyter AI 설정
        print("Jupyter AI 설정 중...")
        ai_installed = self._ensure_jupyter_ai_installed(python_exe)
        ai_config_file = None
        if ai_installed:
            try:
                ai_config_file = self._create_jupyter_ai_config(workspace.path, workspace.id)
                print(f"Jupyter AI 설정 완료: {ai_config_file}")
            except Exception as e:
                print(f"Jupyter AI 설정 실패: {e}")
        else:
            print("Jupyter AI 설치 실패 - AI 기능 없이 진행합니다.")
        
        # Jupyter Lab 명령어 구성 (단순화된 안정적인 설정)
        cmd = [
            python_exe, "-m", "jupyterlab",
            "--port", str(port),
            "--no-browser",
            "--ip", "0.0.0.0",
            f"--notebook-dir={workspace.path}",
            "--ServerApp.token=''",  # 토큰 비활성화
            "--ServerApp.password=''",  # 패스워드도 비활성화  
            "--ServerApp.disable_check_xsrf=True",
            "--ServerApp.allow_origin='*'",
            "--ServerApp.allow_remote_access=True",
            "--ServerApp.port_retries=0",  # 포트 재시도 비활성화 (지정된 포트만 사용)
            "--ServerApp.allow_credentials=True",
            "--ServerApp.log_level=INFO",  # 로그 레벨
            # 커널 기본 설정만 유지
            "--MappingKernelManager.default_kernel_name=python3",
            "--ServerApp.terminals_enabled=True",
        ]
        
        # 빈 문자열 제거
        cmd = [arg for arg in cmd if arg]
        
        try:
            # 환경변수 설정
            env = os.environ.copy()
            env['PYTHONPATH'] = workspace.path
            env['JUPYTER_PORT'] = str(port)  # 환경변수로도 포트 설정
            
            # Python 실행 경로 설정 (커널이 올바른 Python을 사용하도록)
            env['JUPYTER_RUNTIME_DIR'] = os.path.join(workspace.path, '.jupyter', 'runtime')
            env['JUPYTER_DATA_DIR'] = os.path.join(workspace.path, '.jupyter', 'data')
            env['JUPYTER_CONFIG_DIR'] = os.path.join(workspace.path, '.jupyter', 'config')
            
            # Jupyter AI 환경변수 설정
            if ai_config_file:
                env['JUPYTER_CONFIG_PATH'] = os.path.dirname(ai_config_file)
            
            # AI API 키 환경변수 설정 (사용 가능한 경우만)
            if settings.openai_api_key and settings.openai_api_key != "your-openai-api-key-here":
                env['OPENAI_API_KEY'] = settings.openai_api_key
                print("OpenAI API 키 설정됨")
            
            if settings.anthropic_api_key and settings.anthropic_api_key != "your-anthropic-api-key-here":
                env['ANTHROPIC_API_KEY'] = settings.anthropic_api_key
                print("Anthropic API 키 설정됨")
            
            if settings.google_api_key and settings.google_api_key != "your-google-api-key-here":
                env['GOOGLE_API_KEY'] = settings.google_api_key
                print("Google API 키 설정됨")
            
            # Ollama 설정
            env['OLLAMA_BASE_URL'] = settings.ollama_base_url
            
            # 커널이 현재 Python 환경을 사용하도록 설정
            python_dir = os.path.dirname(python_exe)
            if 'PATH' in env:
                env['PATH'] = f"{python_dir}{os.pathsep}{env['PATH']}"
            else:
                env['PATH'] = python_dir
            
            # Jupyter 디렉토리 생성
            for jupyter_dir in [env['JUPYTER_RUNTIME_DIR'], env['JUPYTER_DATA_DIR'], env['JUPYTER_CONFIG_DIR']]:
                Path(jupyter_dir).mkdir(parents=True, exist_ok=True)
            
            print(f"Jupyter Lab 시작 명령어: {' '.join(cmd)}")
            print(f"작업 디렉토리: {workspace.path}")
            print(f"Python 실행 파일: {python_exe}")
            print(f"할당된 포트: {port}")
            print(f"Python PATH: {env.get('PATH', 'Not set')[:100]}...")  # PATH 일부만 출력
            
            # Jupyter Lab 프로세스 시작
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=workspace.path,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            self.processes[workspace.id] = process
            
            # 프로세스 시작 확인 (더 길게 대기)
            import time
            print("프로세스 시작 대기 중...")
            time.sleep(8)  # 8초 대기
            
            if process.poll() is not None:
                # 프로세스가 종료됨
                stdout, stderr = process.communicate()
                stdout_msg = stdout.decode('utf-8', errors='ignore') if stdout else ""
                stderr_msg = stderr.decode('utf-8', errors='ignore') if stderr else ""
                
                print(f"=== Jupyter Lab 프로세스 즉시 종료 ===")
                print(f"반환 코드: {process.returncode}")
                print(f"STDOUT:\n{stdout_msg}")
                print(f"STDERR:\n{stderr_msg}")
                print("=" * 50)
                
                # 프로세스 목록에서 제거
                if workspace.id in self.processes:
                    del self.processes[workspace.id]
                
                # 오류 메시지 개선
                error_details = []
                if "ModuleNotFoundError" in stderr_msg:
                    error_details.append("필요한 Python 모듈이 설치되지 않았습니다.")
                if "jupyter" not in stderr_msg and "jupyter" not in stdout_msg:
                    error_details.append("Jupyter가 올바르게 설치되지 않았을 수 있습니다.")
                if "Permission denied" in stderr_msg:
                    error_details.append("권한 문제가 발생했습니다.")
                if "Port" in stderr_msg and "already in use" in stderr_msg:
                    error_details.append(f"포트 {port}가 이미 사용 중입니다.")
                
                error_summary = " ".join(error_details) if error_details else "알 수 없는 오류"
                raise Exception(f"Jupyter Lab 시작 실패: {error_summary}\n\nSTDOUT: {stdout_msg[:500]}\nSTDERR: {stderr_msg[:500]}")
            
            # 프로세스가 실행 중인지 추가 확인
            print(f"프로세스 ID: {process.pid}")
            print(f"프로세스 상태: {'실행 중' if process.poll() is None else '종료됨'}")
            
            # 포트가 실제로 열렸는지 여러 번 확인
            port_ready = False
            for attempt in range(3):  # 15번 시도로 증가
                import socket
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = test_sock.connect_ex(('localhost', port))
                test_sock.close()
                
                if result == 0:
                    port_ready = True
                    print(f"포트 {port} 연결 확인됨 (시도 {attempt + 1})")
                    break
                else:
                    print(f"포트 {port} 연결 대기 중... (시도 {attempt + 1}/3)")
                    time.sleep(3)  # 대기 시간 증가
            
            if not port_ready:
                print(f"포트 {port}가 타임아웃 내에 열리지 않음")
                # 프로세스 로그 확인
                try:
                    stdout, stderr = process.communicate(timeout=3)
                    stdout_msg = stdout.decode('utf-8', errors='ignore') if stdout else ""
                    stderr_msg = stderr.decode('utf-8', errors='ignore') if stderr else ""
                    print(f"프로세스 출력:\nSTDOUT: {stdout_msg}\nSTDERR: {stderr_msg}")
                except subprocess.TimeoutExpired:
                    print("프로세스가 여전히 실행 중이지만 포트가 열리지 않음")
                
                # 그래도 성공으로 처리 (일부 환경에서는 바로 연결되지 않을 수 있음)
                print("경고: 포트 연결 확인 실패했지만 프로세스는 실행 중")
            
            print(f"Jupyter Lab 성공적으로 시작됨 - 포트: {port}, 워크스페이스 ID: {workspace.id}")
            return port, "noauth"
            
        except FileNotFoundError as e:
            error_msg = f"Python 실행 파일을 찾을 수 없습니다: {python_exe}"
            print(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Jupyter Lab 시작 실패: {str(e)}"
            print(error_msg)
            # 프로세스 목록에서 제거
            if workspace.id in self.processes:
                del self.processes[workspace.id]
            raise Exception(error_msg)
    
    def stop_jupyter_lab(self, workspace_id: int) -> bool:
        """Jupyter Lab 인스턴스 중지"""
        if workspace_id not in self.processes:
            return False
        
        try:
            process = self.processes[workspace_id]
            
            # 크로스 플랫폼 프로세스 종료
            try:
                # 먼저 우아한 종료 시도
                if os.name == 'nt':
                    # Windows에서는 CTRL_BREAK_EVENT 사용
                    try:
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                    except OSError:
                        # CTRL_BREAK_EVENT가 실패하면 SIGTERM으로 대체
                        process.terminate()
                else:
                    # Unix 계열(Linux/Mac)에서는 SIGTERM 사용
                    process.send_signal(signal.SIGTERM)
                
                # 프로세스 종료 대기
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # 우아한 종료가 실패하면 강제 종료
                    process.kill()
                    process.wait()
                    
            except (OSError, subprocess.SubprocessError) as e:
                logger.warning(f"프로세스 종료 중 오류 발생: {e}")
                # 최후의 수단으로 강제 종료
                try:
                    process.kill()
                    process.wait()
                except:
                    pass
            
            del self.processes[workspace_id]
            print(f"Jupyter Lab 정상 종료 - workspace_id: {workspace_id}")
            return True
            
        except Exception as e:
            print(f"Jupyter Lab 중지 실패: {str(e)}")
            return False
    
    def is_process_running(self, workspace_id: int) -> bool:
        """프로세스 실행 상태 확인"""
        if workspace_id not in self.processes:
            return False
        
        process = self.processes[workspace_id]
        return process.poll() is None
    
    def get_jupyter_url(self, workspace: Workspace) -> Optional[str]:
        """Jupyter Lab URL 생성"""
        if not workspace.jupyter_port:
            return None
        
        # 토큰 없이 직접 접속할 수 있는 URL
        return f"{settings.jupyter_base_url}:{workspace.jupyter_port}/lab"
    
    def cleanup_zombie_processes(self):
        """좀비 프로세스 정리"""
        to_remove = []
        for workspace_id, process in self.processes.items():
            if not self.is_process_running(workspace_id):
                to_remove.append(workspace_id)
        
        for workspace_id in to_remove:
            del self.processes[workspace_id]

    def _ensure_python_kernel(self, workspace_id: int, python_exe: str) -> bool:
        """Python 커널이 사용 가능한지 확인하고 필요시 설치"""
        try:
            logger.info("커널스펙 확인 중...")
            
            # Python 실행 파일 확인
            if not os.path.exists(python_exe):
                logger.error(f"Python 실행 파일을 찾을 수 없음: {python_exe}")
                return False
                
            logger.info(f"Python: {python_exe}")
            
            # 커널스펙 이름을 워크스페이스 ID 기반으로 생성
            kernel_name = f"python3-{workspace_id}"
            
            try:
                # 기존 커널스펙 제거 (오류가 있을 수 있는 것들)
                subprocess.run([
                    python_exe, "-m", "ipykernel", "uninstall", kernel_name, "-f"
                ], capture_output=True, timeout=30)
                
                # 새 커널스펙 설치 (더 안정적인 설정으로)
                logger.info(f"커널스펙 설치 중: {kernel_name}")
                result = subprocess.run([
                    python_exe, "-m", "ipykernel", "install",
                    "--user",  # 사용자 디렉토리에 설치
                    "--name", kernel_name,
                    "--display-name", f"Python 3 (Workspace {workspace_id})"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    logger.info(f"커널스펙 설치 완료: {kernel_name}")
                    return True
                else:
                    logger.error(f"커널스펙 설치 실패: {result.stderr}")
                    
                    # 기본 커널이라도 사용할 수 있는지 확인
                    try:
                        # 기본 python3 커널 설치 시도
                        result = subprocess.run([
                            python_exe, "-m", "ipykernel", "install", "--user"
                        ], capture_output=True, text=True, timeout=60)
                        
                        if result.returncode == 0:
                            logger.info("기본 python3 커널 설치 완료")
                            return True
                    except Exception as e:
                        logger.error(f"기본 커널 설치도 실패: {e}")
                    
                    return False
                    
            except subprocess.TimeoutExpired:
                logger.error("커널스펙 설치 타임아웃")
                return False
            except Exception as e:
                logger.error(f"커널스펙 설치 중 오류: {e}")
                return False
                
        except Exception as e:
            logger.error(f"커널 확인 중 오류: {e}")
            return False

# 전역 Jupyter 서비스 인스턴스
jupyter_service = JupyterService() 