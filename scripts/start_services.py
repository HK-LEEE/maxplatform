#!/usr/bin/env python3
"""
크로스 플랫폼 서비스 시작 스크립트
Windows와 Mac OS 모두에서 동작하는 서비스 시작 도구
"""

import os
import sys
import subprocess
import platform
import time
from pathlib import Path

class ServiceManager:
    def __init__(self):
        self.system = platform.system()
        self.is_windows = self.system == "Windows"
        self.is_mac = self.system == "Darwin"
        self.is_linux = self.system == "Linux"
        
        # 프로젝트 루트 디렉토리
        self.root_dir = Path(__file__).parent.parent
        self.backend_dir = self.root_dir / "backend"
        self.frontend_dir = self.root_dir / "frontend"
        
    def get_python_executable(self):
        """Python 실행 파일 경로 반환"""
        if self.is_windows:
            return "python"
        else:
            return "python3"
    
    def get_venv_path(self):
        """가상환경 경로 반환"""
        if self.is_windows:
            return self.backend_dir / "venv" / "Scripts"
        else:
            return self.backend_dir / "venv" / "bin"
    
    def get_activate_command(self):
        """가상환경 활성화 명령어 반환"""
        venv_path = self.get_venv_path()
        if self.is_windows:
            return str(venv_path / "activate.bat")
        else:
            return f"source {venv_path / 'activate'}"
    
    def run_command(self, command, cwd=None, shell=True, env=None):
        """운영체제에 관계없이 명령어 실행"""
        try:
            if isinstance(command, list):
                cmd = command
            else:
                cmd = command
            
            print(f"실행 중: {cmd}")
            
            if cwd:
                print(f"작업 디렉토리: {cwd}")
            
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                shell=shell,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"오류 발생: {stderr}")
                return False, stderr
            else:
                print(f"성공: {stdout}")
                return True, stdout
                
        except Exception as e:
            print(f"명령어 실행 실패: {e}")
            return False, str(e)
    
    def create_virtual_environment(self):
        """가상환경 생성"""
        print("가상환경 확인 중...")
        
        venv_dir = self.backend_dir / "venv"
        if venv_dir.exists():
            print("가상환경이 이미 존재합니다.")
            return True
        
        print("가상환경 생성 중...")
        python_cmd = self.get_python_executable()
        success, output = self.run_command(
            f"{python_cmd} -m venv venv",
            cwd=self.backend_dir
        )
        
        if success:
            print("가상환경 생성 완료")
            return True
        else:
            print(f"가상환경 생성 실패: {output}")
            return False
    
    def install_backend_dependencies(self):
        """백엔드 의존성 설치"""
        print("백엔드 의존성 설치 중...")
        
        # 가상환경 생성
        if not self.create_virtual_environment():
            return False
        
        # pip 실행 경로
        if self.is_windows:
            pip_path = self.get_venv_path() / "pip.exe"
            python_path = self.get_venv_path() / "python.exe"
        else:
            pip_path = self.get_venv_path() / "pip"
            python_path = self.get_venv_path() / "python"
        
        # pip 업그레이드
        success, _ = self.run_command(
            f"{python_path} -m pip install --upgrade pip",
            cwd=self.backend_dir
        )
        
        if not success:
            print("pip 업그레이드 실패")
            return False
        
        # 충돌하는 패키지 제거
        self.run_command(
            f"{pip_path} uninstall -y databases",
            cwd=self.backend_dir
        )
        
        # 의존성 설치
        success, output = self.run_command(
            f"{pip_path} install -r requirements.txt",
            cwd=self.backend_dir
        )
        
        if success:
            print("백엔드 의존성 설치 완료")
            return True
        else:
            print(f"백엔드 의존성 설치 실패: {output}")
            return False
    
    def install_frontend_dependencies(self):
        """프론트엔드 의존성 설치"""
        print("프론트엔드 의존성 설치 중...")
        
        success, output = self.run_command(
            "npm install",
            cwd=self.frontend_dir
        )
        
        if success:
            print("프론트엔드 의존성 설치 완료")
            return True
        else:
            print(f"프론트엔드 의존성 설치 실패: {output}")
            return False
    
    def start_backend(self):
        """백엔드 서버 시작"""
        print("백엔드 서버 시작 중...")
        
        # 의존성 설치
        if not self.install_backend_dependencies():
            return False
        
        # uvicorn 실행 경로
        if self.is_windows:
            uvicorn_path = self.get_venv_path() / "uvicorn.exe"
        else:
            uvicorn_path = self.get_venv_path() / "uvicorn"
        
        # FastAPI 서버 시작
        print("FastAPI 서버 시작 중... (http://localhost:8000)")
        print("API 문서: http://localhost:8000/docs")
        
        if self.is_windows:
            # Windows에서는 별도 창에서 실행
            cmd = f'start "Backend Server" cmd /k "{uvicorn_path} app.main:app --reload --host 0.0.0.0 --port 8000"'
            os.system(cmd)
        else:
            # Mac/Linux에서는 백그라운드에서 실행
            subprocess.Popen([
                str(uvicorn_path), "app.main:app", 
                "--reload", "--host", "0.0.0.0", "--port", "8000"
            ], cwd=self.backend_dir)
        
        return True
    
    def start_frontend(self):
        """프론트엔드 서버 시작"""
        print("프론트엔드 서버 시작 중...")
        
        # 의존성 설치
        if not self.install_frontend_dependencies():
            return False
        
        print("개발 서버 시작 중... (http://localhost:3000)")
        
        if self.is_windows:
            # Windows에서는 별도 창에서 실행
            cmd = f'start "Frontend Server" cmd /k "npm start"'
            os.chdir(self.frontend_dir)
            os.system(cmd)
        else:
            # Mac/Linux에서는 백그라운드에서 실행
            subprocess.Popen(["npm", "start"], cwd=self.frontend_dir)
        
        return True
    
    def start_all_services(self):
        """모든 서비스 시작"""
        print("=" * 50)
        print("GenbaX Platform 서비스 시작")
        print("=" * 50)
        print()
        
        print("다음 서비스들이 시작됩니다:")
        print("- 백엔드 API 서버 (포트 8000)")
        print("- 프론트엔드 서버 (포트 3000)")
        print()
        
        # 백엔드 서버 시작
        if not self.start_backend():
            print("백엔드 서버 시작 실패")
            return False
        
        print("백엔드 서버 시작 대기 중... (5초)")
        time.sleep(5)
        
        # 프론트엔드 서버 시작
        if not self.start_frontend():
            print("프론트엔드 서버 시작 실패")
            return False
        
        print()
        print("=" * 50)
        print("서비스 시작 완료!")
        print("=" * 50)
        print()
        print("접속 URL:")
        print("- 웹 애플리케이션: http://localhost:3000")
        print("- API 문서: http://localhost:8000/docs")
        print()
        
        return True

def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python start_services.py [all|backend|frontend]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    manager = ServiceManager()
    
    print(f"운영체제: {manager.system}")
    print(f"Python 실행파일: {manager.get_python_executable()}")
    print()
    
    if command == "all":
        manager.start_all_services()
    elif command == "backend":
        manager.start_backend()
    elif command == "frontend":
        manager.start_frontend()
    else:
        print("잘못된 명령어입니다. all, backend, frontend 중 하나를 선택하세요.")
        sys.exit(1)

if __name__ == "__main__":
    main() 