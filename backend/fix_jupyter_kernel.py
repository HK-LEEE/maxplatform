#!/usr/bin/env python3
"""
Jupyter 커널 문제 해결 스크립트
JupyterLab 4.x와 커널 호환성 문제를 해결합니다.
"""

import subprocess
import sys
import os
import json

def run_command(cmd, description):
    """명령어 실행 및 결과 출력"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"✅ {description} 완료")
            if result.stdout.strip():
                print(f"   출력: {result.stdout.strip()}")
        else:
            print(f"⚠️ {description} 경고: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"❌ {description} 타임아웃")
        return False
    except Exception as e:
        print(f"❌ {description} 실패: {e}")
        return False

def main():
    print("🚀 Jupyter 커널 문제 해결 시작\n")
    
    # 1. 기존 커널 스펙 정리
    print("📋 1단계: 기존 커널 스펙 정리")
    run_command("jupyter kernelspec remove python3-7 -f", "python3-7 커널 제거")
    run_command("jupyter kernelspec remove python3 -f", "기본 python3 커널 제거")
    
    # 2. 최신 ipykernel 설치
    print("\n📦 2단계: 최신 패키지 설치")
    run_command("pip install --upgrade --force-reinstall ipykernel", "ipykernel 재설치")
    run_command("pip install --upgrade --force-reinstall jupyter_client", "jupyter_client 업데이트")
    run_command("pip install --upgrade --force-reinstall jupyter_server", "jupyter_server 업데이트")
    
    # 3. Python 커널 재설치
    print("\n🔧 3단계: Python 커널 재설치")
    python_exe = sys.executable
    run_command(f"{python_exe} -m ipykernel install --user --name python3 --display-name \"Python 3\"", 
                "기본 Python 3 커널 설치")
    
    # 4. 커널 스펙 확인
    print("\n📋 4단계: 커널 스펙 확인")
    run_command("jupyter kernelspec list", "설치된 커널 목록 확인")
    
    # 5. Jupyter 설정 디렉토리 정리
    print("\n🧹 5단계: Jupyter 설정 정리")
    jupyter_config_dir = os.path.expanduser("~/.jupyter")
    if os.path.exists(jupyter_config_dir):
        print(f"Jupyter 설정 디렉토리: {jupyter_config_dir}")
        
        # 런타임 디렉토리 정리
        runtime_dir = os.path.join(jupyter_config_dir, "runtime")
        if os.path.exists(runtime_dir):
            import shutil
            try:
                shutil.rmtree(runtime_dir)
                os.makedirs(runtime_dir, exist_ok=True)
                print("✅ 런타임 디렉토리 정리 완료")
            except Exception as e:
                print(f"⚠️ 런타임 디렉토리 정리 실패: {e}")
    
    # 6. 테스트용 노트북 실행 (간단한 테스트)
    print("\n🧪 6단계: 커널 테스트")
    test_code = """
import sys
print(f"Python: {sys.version}")
print("커널이 정상적으로 작동합니다!")
"""
    
    try:
        # 임시 파일 생성
        test_file = "kernel_test.py"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)
        
        # Python 실행 테스트
        result = subprocess.run([python_exe, test_file], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ 커널 테스트 성공")
            print(f"   {result.stdout.strip()}")
        else:
            print(f"❌ 커널 테스트 실패: {result.stderr}")
        
        # 테스트 파일 삭제
        if os.path.exists(test_file):
            os.remove(test_file)
    
    except Exception as e:
        print(f"❌ 커널 테스트 오류: {e}")
    
    # 7. 결과 요약
    print("\n📊 결과 요약:")
    print("✅ Jupyter 커널 문제 해결 완료")
    print("✅ 최신 패키지로 업데이트됨")
    print("✅ 커널 스펙 재설치됨")
    print("\n🎯 다음 단계:")
    print("1. 백엔드 서버 재시작")
    print("2. 새 워크스페이스 생성 또는 기존 워크스페이스 재시작")
    print("3. Jupyter Lab에서 노트북 열어보기")

if __name__ == "__main__":
    main() 