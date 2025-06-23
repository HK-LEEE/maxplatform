#!/usr/bin/env python3
"""
크로스 플랫폼 환경 설정 유틸리티
Windows와 Mac OS 모두에서 동작하는 환경 설정 도구
"""

import os
import sys
import platform
import shutil
from pathlib import Path
import secrets
import string
from cryptography.fernet import Fernet

class EnvironmentSetup:
    def __init__(self):
        self.system = platform.system()
        self.is_windows = self.system == "Windows"
        self.is_mac = self.system == "Darwin"
        self.is_linux = self.system == "Linux"
        
        # 프로젝트 루트 디렉토리
        self.root_dir = Path(__file__).parent.parent
        self.backend_dir = self.root_dir / "backend"
        self.frontend_dir = self.root_dir / "frontend"
        
        # 환경 파일 경로
        self.env_template = self.root_dir / ".env.template"
        self.env_file = self.root_dir / ".env"
    
    def generate_secret_key(self, length=32):
        """보안 키 생성"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_encryption_key(self):
        """암호화 키 생성"""
        return Fernet.generate_key().decode()
    
    def detect_database_requirements(self):
        """설치된 데이터베이스 드라이버 감지"""
        db_info = {
            'postgresql': False,
            'mysql': False,
            'mssql': False
        }
        
        try:
            import psycopg2
            db_info['postgresql'] = True
            print("✓ PostgreSQL 드라이버 감지됨")
        except ImportError:
            print("- PostgreSQL 드라이버 없음 (pip install psycopg2-binary)")
        
        try:
            import pymysql
            db_info['mysql'] = True
            print("✓ MySQL 드라이버 감지됨")
        except ImportError:
            print("- MySQL 드라이버 없음 (pip install PyMySQL)")
        
        try:
            import pyodbc
            db_info['mssql'] = True
            print("✓ MSSQL 드라이버 감지됨")
        except ImportError:
            print("- MSSQL 드라이버 없음 (pip install pyodbc)")
        
        return db_info
    
    def get_default_database_config(self):
        """운영체제별 기본 데이터베이스 설정"""
        if self.is_windows:
            return {
                'type': 'postgresql',
                'url': 'postgresql://postgres:password@localhost:5432/genbax_platform'
            }
        elif self.is_mac:
            return {
                'type': 'postgresql',
                'url': 'postgresql://postgres:@localhost:5432/genbax_platform'
            }
        else:  # Linux
            return {
                'type': 'postgresql',
                'url': 'postgresql://postgres:@localhost:5432/genbax_platform'
            }
    
    def get_platform_specific_paths(self):
        """운영체제별 기본 경로 설정"""
        if self.is_windows:
            return {
                'data_dir': './data',
                'chroma_path': './chroma_data'
            }
        else:  # Mac/Linux
            return {
                'data_dir': './data',
                'chroma_path': './chroma_data'
            }
    
    def create_env_file(self):
        """환경 파일 생성"""
        print("환경 파일 생성 중...")
        
        if not self.env_template.exists():
            print("❌ .env.template 파일이 없습니다.")
            return False
        
        # 기존 .env 파일 백업
        if self.env_file.exists():
            backup_file = self.root_dir / ".env.backup"
            shutil.copy2(self.env_file, backup_file)
            print(f"기존 .env 파일을 {backup_file}로 백업했습니다.")
        
        # 템플릿 읽기
        with open(self.env_template, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 보안 키 생성 및 교체
        secret_key = self.generate_secret_key()
        encryption_key = self.generate_encryption_key()
        
        content = content.replace('your-secret-key-change-this-in-production', secret_key)
        content = content.replace('ENCRYPTION_KEY=', f'ENCRYPTION_KEY={encryption_key}')
        
        # 데이터베이스 설정
        db_config = self.get_default_database_config()
        content = content.replace('DATABASE_TYPE=postgresql', f'DATABASE_TYPE={db_config["type"]}')
        content = content.replace(
            'DATABASE_URL=postgresql://postgres:2300@localhost:5432/platform_integration',
            f'DATABASE_URL={db_config["url"]}'
        )
        
        # 경로 설정
        paths = self.get_platform_specific_paths()
        content = content.replace('DATA_DIR=./data', f'DATA_DIR={paths["data_dir"]}')
        content = content.replace('CHROMA_PERSIST_PATH=./chroma_data', f'CHROMA_PERSIST_PATH={paths["chroma_path"]}')
        
        # .env 파일 저장
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 환경 파일이 생성되었습니다: {self.env_file}")
        return True
    
    def create_directories(self):
        """필요한 디렉토리 생성"""
        print("필요한 디렉토리 생성 중...")
        
        directories = [
            self.root_dir / "data",
            self.root_dir / "data" / "users",
            self.root_dir / "chroma_data",
            self.root_dir / "file_storage",
            self.root_dir / "file_storage" / "users",
            self.root_dir / "file_storage" / "groups",
            self.root_dir / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✓ 디렉토리 생성: {directory}")
    
    def check_system_requirements(self):
        """시스템 요구사항 확인"""
        print("시스템 요구사항 확인 중...")
        
        # Python 버전 확인
        python_version = sys.version_info
        if python_version >= (3, 8):
            print(f"✓ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            print(f"❌ Python 3.8 이상이 필요합니다. 현재: {python_version.major}.{python_version.minor}")
            return False
        
        # Node.js 확인
        try:
            import subprocess
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ Node.js {result.stdout.strip()}")
            else:
                print("❌ Node.js가 설치되어 있지 않습니다.")
                return False
        except FileNotFoundError:
            print("❌ Node.js가 설치되어 있지 않습니다.")
            return False
        
        # npm 확인
        try:
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ npm {result.stdout.strip()}")
            else:
                print("❌ npm이 설치되어 있지 않습니다.")
                return False
        except FileNotFoundError:
            print("❌ npm이 설치되어 있지 않습니다.")
            return False
        
        return True
    
    def setup_environment(self):
        """전체 환경 설정"""
        print("=" * 60)
        print("GenbaX Platform 크로스 플랫폼 환경 설정")
        print("=" * 60)
        print(f"운영체제: {self.system}")
        print(f"Python: {sys.version}")
        print()
        
        # 시스템 요구사항 확인
        if not self.check_system_requirements():
            print("❌ 시스템 요구사항을 만족하지 않습니다.")
            return False
        
        print()
        
        # 데이터베이스 요구사항 확인
        print("데이터베이스 드라이버 확인:")
        self.detect_database_requirements()
        print()
        
        # 디렉토리 생성
        self.create_directories()
        print()
        
        # 환경 파일 생성
        if not self.create_env_file():
            return False
        
        print()
        print("=" * 60)
        print("환경 설정 완료!")
        print("=" * 60)
        print()
        print("다음 단계:")
        print("1. .env 파일을 확인하고 필요에 따라 수정하세요")
        print("2. 데이터베이스를 설정하고 연결 정보를 .env에 업데이트하세요")
        print("3. python scripts/start_services.py all 명령으로 서비스를 시작하세요")
        print()
        
        return True

def main():
    """메인 함수"""
    setup = EnvironmentSetup()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        # 강제 재설정
        setup.setup_environment()
    else:
        # .env 파일이 이미 있는 경우 확인
        if setup.env_file.exists():
            response = input(".env 파일이 이미 존재합니다. 다시 생성하시겠습니까? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("환경 설정을 취소했습니다.")
                return
        
        setup.setup_environment()

if __name__ == "__main__":
    main() 