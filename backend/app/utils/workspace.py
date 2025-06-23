import os
import socket
import secrets
from pathlib import Path
from ..config import settings

def create_workspace_directory(user_id: str, workspace_id: int) -> str:
    """사용자 워크스페이스 디렉토리 생성 (UUID/워크스페이스 ID 기반)"""
    workspace_path = settings.get_workspace_path(user_id, workspace_id)
    Path(workspace_path).mkdir(parents=True, exist_ok=True)
    
    # 기본 폴더 생성
    notebooks_path = os.path.join(workspace_path, "notebooks")
    data_path = os.path.join(workspace_path, "data")
    outputs_path = os.path.join(workspace_path, "outputs")
    
    Path(notebooks_path).mkdir(exist_ok=True)
    Path(data_path).mkdir(exist_ok=True)
    Path(outputs_path).mkdir(exist_ok=True)
    
    # 시작 가이드 노트북 생성
    create_welcome_notebook(notebooks_path)
    
    # Jupyter 커널 설정 확인 및 설치
    print(f"워크스페이스 {workspace_id}에 대한 커널 설정 중...")
    kernel_setup_success = ensure_jupyter_kernel(workspace_path)
    if not kernel_setup_success:
        print(f"경고: 워크스페이스 {workspace_id}의 커널 설정에 문제가 있을 수 있습니다.")
    
    return workspace_path

def create_welcome_notebook(notebooks_path: str):
    """환영 노트북 생성"""
    welcome_content = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# Welcome to Your Jupyter Data Platform!\n",
                    "\n",
                    "이곳은 여러분의 개인 워크스페이스입니다. 다음과 같은 기능들을 활용하실 수 있습니다:\n",
                    "\n",
                    "## 주요 기능\n",
                    "- 데이터 분석 및 시각화\n",
                    "- 머신러닝 모델 개발\n",
                    "- 단계별 결과 저장 및 재사용\n",
                    "\n",
                    "## 폴더 구조\n",
                    "- `notebooks/`: 노트북 파일 저장\n",
                    "- `data/`: 데이터 파일 저장\n",
                    "- `outputs/`: 결과 파일 저장"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 기본 라이브러리 import\n",
                    "import pandas as pd\n",
                    "import numpy as np\n",
                    "import matplotlib.pyplot as plt\n",
                    "import seaborn as sns\n",
                    "\n",
                    "print('환영합니다! 모든 라이브러리가 정상적으로 로드되었습니다.')"
                ]
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.8.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    import json
    welcome_path = os.path.join(notebooks_path, "Welcome.ipynb")
    with open(welcome_path, 'w', encoding='utf-8') as f:
        json.dump(welcome_content, f, ensure_ascii=False, indent=2)

def find_available_port(db_session=None) -> int:
    """사용 가능한 포트 찾기 (데이터베이스 기반 중복 체크 포함)"""
    import time
    import random
    
    # 데이터베이스에서 현재 사용 중인 포트 목록 가져오기
    used_ports = set()
    if db_session:
        try:
            from ..models.workspace import Workspace
            active_workspaces = db_session.query(Workspace).filter(
                Workspace.is_active == True,
                Workspace.jupyter_port.isnot(None),
                Workspace.jupyter_status == "running"
            ).all()
            used_ports = {ws.jupyter_port for ws in active_workspaces if ws.jupyter_port}
            print(f"데이터베이스에서 사용 중인 포트: {used_ports}")
        except Exception as e:
            print(f"데이터베이스 포트 조회 중 오류: {e}")
    
    # 포트 범위 내에서 순차적으로 확인
    port_range = list(range(settings.jupyter_port_start, settings.jupyter_port_end + 1))
    
    # 랜덤하게 섞어서 충돌 가능성 줄이기
    random.shuffle(port_range)
    
    for port in port_range:
        # 데이터베이스에서 사용 중인 포트는 건너뛰기
        if port in used_ports:
            continue
            
        try:
            # 소켓 바인드 테스트
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('localhost', port))
                
                # 짧은 대기 후 다시 한 번 확인 (이중 체크)
                time.sleep(0.1)
                
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
                    s2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s2.bind(('localhost', port))
                    print(f"사용 가능한 포트 발견: {port}")
                    return port
                    
        except OSError as e:
            print(f"포트 {port} 사용 불가: {e}")
            continue
    
    # 모든 포트가 사용 중이면 예외 발생
    raise Exception(f"사용 가능한 포트를 찾을 수 없습니다. 포트 범위: {settings.jupyter_port_start}-{settings.jupyter_port_end}")

def generate_jupyter_token() -> str:
    """Jupyter 토큰 생성"""
    return secrets.token_urlsafe(32)

def ensure_jupyter_kernel(workspace_path: str) -> bool:
    """워크스페이스에 Python 커널이 설치되어 있는지 확인하고 없으면 설치"""
    try:
        import subprocess
        import sys
        
        # 현재 Python 실행 파일 경로
        python_exe = sys.executable
        
        print(f"커널스펙 확인 중... Python: {python_exe}")
        
        # ipykernel이 설치되어 있는지 확인
        try:
            result = subprocess.run([python_exe, "-c", "import ipykernel"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print("ipykernel이 설치되지 않음 - 설치 시도 중...")
                # ipykernel 설치
                subprocess.run([python_exe, "-m", "pip", "install", "ipykernel"], 
                             check=True, timeout=60)
                print("ipykernel 설치 완료")
        except subprocess.TimeoutExpired:
            print("ipykernel 설치 타임아웃")
            return False
        except subprocess.CalledProcessError as e:
            print(f"ipykernel 설치 실패: {e}")
            return False
        
        # 커널스펙 설치 (워크스페이스별로 고유한 이름 사용)
        workspace_name = os.path.basename(workspace_path)
        kernel_name = f"python3-{workspace_name}"
        
        try:
            # 기존 커널스펙이 있는지 확인
            result = subprocess.run([python_exe, "-m", "jupyter", "kernelspec", "list"], 
                                  capture_output=True, text=True, timeout=10)
            
            if kernel_name not in result.stdout:
                print(f"커널스펙 설치 중: {kernel_name}")
                # 커널스펙 설치
                subprocess.run([
                    python_exe, "-m", "ipykernel", "install", 
                    "--user", 
                    "--name", kernel_name,
                    "--display-name", f"Python 3 ({workspace_name})"
                ], check=True, timeout=30)
                print(f"커널스펙 설치 완료: {kernel_name}")
            else:
                print(f"커널스펙 이미 존재: {kernel_name}")
                
        except subprocess.TimeoutExpired:
            print("커널스펙 설치 타임아웃")
            return False
        except subprocess.CalledProcessError as e:
            print(f"커널스펙 설치 실패: {e}")
            # 기본 커널스펙 설치 시도
            try:
                subprocess.run([python_exe, "-m", "ipykernel", "install", "--user"], 
                             check=True, timeout=30)
                print("기본 커널스펙 설치 완료")
            except:
                return False
        
        return True
        
    except Exception as e:
        print(f"커널 설정 오류: {e}")
        return False 