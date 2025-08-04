#!/usr/bin/env python3
"""
MAX Platform 프로젝트 자동 정리 스크립트
불필요한 파일, 더티 파일, 미사용 코드 정리

사용법:
python scripts/cleanup_project.py --dry-run    # 미리보기
python scripts/cleanup_project.py --execute    # 실제 실행
python scripts/cleanup_project.py --logs-only  # 로그 파일만 정리
"""

import os
import sys
import glob
import shutil
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta

class ProjectCleaner:
    def __init__(self, project_root, dry_run=True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.deleted_files = []
        self.saved_space = 0
        
    def log_action(self, action, file_path, reason=""):
        if self.dry_run:
            print(f"[DRY-RUN] {action}: {file_path} {reason}")
        else:
            print(f"[EXECUTED] {action}: {file_path} {reason}")
            
    def get_file_size(self, file_path):
        try:
            return os.path.getsize(file_path)
        except:
            return 0
            
    def delete_file(self, file_path, reason=""):
        file_size = self.get_file_size(file_path)
        self.log_action("DELETE", file_path, f"({reason})")
        
        if not self.dry_run:
            try:
                os.remove(file_path)
                self.deleted_files.append(str(file_path))
                self.saved_space += file_size
            except Exception as e:
                print(f"ERROR deleting {file_path}: {e}")
                
    def cleanup_zone_identifier_files(self):
        """Windows Zone.Identifier 파일 정리"""
        print("\n🔍 Zone.Identifier 파일 정리...")
        
        zone_files = list(self.project_root.rglob("*:Zone.Identifier"))
        for file_path in zone_files:
            self.delete_file(file_path, "Windows Zone.Identifier 파일")
            
        return len(zone_files)
        
    def cleanup_backup_files(self):
        """백업 및 임시 파일 정리"""
        print("\n🔍 백업 및 임시 파일 정리...")
        
        patterns = [
            "*_backup*",
            "*_new*", 
            "*_old*",
            "*_temp*",
            "*.tmp",
            "*.bak"
        ]
        
        deleted_count = 0
        for pattern in patterns:
            for file_path in self.project_root.rglob(pattern):
                if file_path.is_file():
                    # .venv, node_modules 등 제외
                    if any(exclude in str(file_path) for exclude in ['.venv', 'node_modules', '__pycache__']):
                        continue
                    self.delete_file(file_path, f"백업/임시 파일 ({pattern})")
                    deleted_count += 1
                    
        # 특정 파일들
        specific_files = [
            "backend/test/jupyter_platform.db",
            "frontend/src/App_backup.tsx",
            "frontend/src/App_new.tsx"
        ]
        
        for file_rel_path in specific_files:
            file_path = self.project_root / file_rel_path
            if file_path.exists():
                self.delete_file(file_path, "미사용 백업 파일")
                deleted_count += 1
                
        return deleted_count
        
    def cleanup_duplicate_components(self):
        """중복 컴포넌트 정리"""
        print("\n🔍 중복 컴포넌트 정리...")
        
        # ProtectedRoute 중복 제거 (JSX 버전 삭제, TSX 유지)
        jsx_file = self.project_root / "frontend/src/components/ProtectedRoute.jsx"
        if jsx_file.exists():
            self.delete_file(jsx_file, "TSX 버전으로 통합")
            return 1
            
        return 0
        
    def cleanup_old_logs(self, days_to_keep=7):
        """오래된 로그 파일 정리"""
        print(f"\n🔍 {days_to_keep}일 이전 로그 파일 정리...")
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        log_patterns = [
            "backend/logs/*.log.*",
            "backend/logs/*_2025_*",
            "backend/logs/test_*.log"
        ]
        
        for pattern in log_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    # 파일 수정 시간 확인
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        self.delete_file(file_path, f"{days_to_keep}일 이전 로그")
                        deleted_count += 1
                        
        return deleted_count
        
    def cleanup_redundant_docs(self):
        """중복 문서 정리 (수동 확인 필요)"""
        print("\n🔍 중복 문서 분석 (수동 확인 권장)...")
        
        oauth_docs = [
            "MAX_Platform_OAuth_Integration_Guide_imp(real).md",
            "docs/MAX_Platform_OAuth2_Integration_Guide.md", 
            "backend/docs/MAX_Platform_OAuth_Integration_Guide_imp(real).md",
            "backend/docs/MAX_Platform_OAuth_2.0_Complete_Developer_Guide.md"
        ]
        
        print("📋 발견된 OAuth 문서들:")
        for doc in oauth_docs:
            full_path = self.project_root / doc
            if full_path.exists():
                size = self.get_file_size(full_path)
                print(f"   {doc} ({size:,} bytes)")
                
        print("⚠️  수동 검토 후 불필요한 문서 제거 권장")
        return 0
        
    def analyze_unused_dependencies(self):
        """미사용 의존성 분석"""
        print("\n🔍 미사용 의존성 분석...")
        
        package_json = self.project_root / "frontend/package.json"
        if package_json.exists():
            with open(package_json) as f:
                package_data = json.load(f)
                
            deps_to_check = ["react-hook-form"]
            
            print("📋 의심되는 미사용 의존성:")
            for dep in deps_to_check:
                if dep in package_data.get("dependencies", {}):
                    print(f"   {dep}: {package_data['dependencies'][dep]}")
                    print(f"      프로젝트 내 사용처 검색 권장")
                    
        return 0
        
    def cleanup_test_files(self, aggressive=False):
        """테스트 파일 정리 (조심스럽게)"""
        print("\n🔍 테스트 파일 분석...")
        
        test_dir = self.project_root / "backend/test"
        if test_dir.exists():
            test_files = list(test_dir.glob("*.py"))
            print(f"📋 테스트 디렉토리에 {len(test_files)}개 파일 발견")
            
            if aggressive:
                # 명백히 임시/디버그용인 파일들만 삭제
                temp_patterns = [
                    "debug_*",
                    "test_*_debug*", 
                    "*_temp*"
                ]
                
                deleted_count = 0
                for pattern in temp_patterns:
                    for file_path in test_dir.glob(pattern):
                        self.delete_file(file_path, "임시 디버그 파일")
                        deleted_count += 1
                        
                return deleted_count
            else:
                print("⚠️  수동 검토 권장 (--aggressive 플래그로 임시 파일만 삭제 가능)")
                
        return 0
        
    def generate_cleanup_report(self):
        """정리 결과 보고서 생성"""
        print("\n" + "="*60)
        print("📊 프로젝트 정리 결과 보고서")
        print("="*60)
        
        if self.dry_run:
            print("🔍 DRY RUN 모드 - 실제 파일은 삭제되지 않았습니다")
        else:
            print(f"✅ {len(self.deleted_files)}개 파일 삭제 완료")
            print(f"💾 절약된 공간: {self.saved_space:,} bytes ({self.saved_space/1024/1024:.2f} MB)")
            
        print("\n📋 수동 검토 권장 항목:")
        print("   1. OAuth 문서 중복 확인")
        print("   2. react-hook-form 의존성 제거 여부")
        print("   3. backend/test 디렉토리 정리")
        print("   4. 새 폴더/ 내용 확인")
        
    def run_cleanup(self, options):
        """전체 정리 프로세스 실행"""
        print(f"🚀 MAX Platform 프로젝트 정리 시작")
        print(f"📁 프로젝트 경로: {self.project_root}")
        print(f"🔧 모드: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        
        total_cleaned = 0
        
        if options.get('zone_files', True):
            total_cleaned += self.cleanup_zone_identifier_files()
            
        if options.get('backup_files', True):
            total_cleaned += self.cleanup_backup_files()
            
        if options.get('duplicates', True):
            total_cleaned += self.cleanup_duplicate_components()
            
        if options.get('logs', True):
            total_cleaned += self.cleanup_old_logs(options.get('log_days', 7))
            
        if options.get('docs', True):
            total_cleaned += self.cleanup_redundant_docs()
            
        if options.get('deps', True):
            total_cleaned += self.analyze_unused_dependencies()
            
        if options.get('tests', True):
            total_cleaned += self.cleanup_test_files(options.get('aggressive', False))
            
        self.generate_cleanup_report()
        return total_cleaned

def main():
    parser = argparse.ArgumentParser(description='MAX Platform 프로젝트 정리 도구')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='미리보기 모드 (기본값)')
    parser.add_argument('--execute', action='store_true',
                       help='실제 삭제 실행')
    parser.add_argument('--logs-only', action='store_true',
                       help='로그 파일만 정리')
    parser.add_argument('--aggressive', action='store_true',
                       help='임시 테스트 파일도 삭제')
    parser.add_argument('--log-days', type=int, default=7,
                       help='보관할 로그 파일 일수 (기본: 7일)')
    
    args = parser.parse_args()
    
    # 프로젝트 루트 경로 자동 감지
    current_dir = Path.cwd()
    if current_dir.name == 'maxplatform':
        project_root = current_dir
    elif (current_dir.parent / 'maxplatform').exists():
        project_root = current_dir.parent / 'maxplatform'
    else:
        project_root = Path('/home/lee/proejct/maxplatform')
        
    if not project_root.exists():
        print(f"❌ 프로젝트 경로를 찾을 수 없습니다: {project_root}")
        sys.exit(1)
        
    # 실행 모드 설정
    dry_run = not args.execute
    
    cleaner = ProjectCleaner(project_root, dry_run=dry_run)
    
    # 정리 옵션 설정
    if args.logs_only:
        options = {
            'zone_files': False,
            'backup_files': False,
            'duplicates': False,
            'logs': True,
            'docs': False,
            'deps': False,
            'tests': False,
            'log_days': args.log_days
        }
    else:
        options = {
            'zone_files': True,
            'backup_files': True, 
            'duplicates': True,
            'logs': True,
            'docs': True,
            'deps': True,
            'tests': True,
            'aggressive': args.aggressive,
            'log_days': args.log_days
        }
    
    # 정리 실행
    try:
        cleaned_count = cleaner.run_cleanup(options)
        print(f"\n✨ 정리 완료! 총 {cleaned_count}개 항목 처리됨")
        
        if dry_run:
            print("\n💡 실제 삭제하려면 --execute 플래그를 사용하세요")
            
    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()