#!/usr/bin/env python3
"""
MAX Platform 데드 코드 및 미사용 의존성 분석 스크립트

사용법:
python scripts/analyze_dead_code.py --all
python scripts/analyze_dead_code.py --deps-only
python scripts/analyze_dead_code.py --imports-only
"""

import os
import json
import re
import ast
import argparse
from pathlib import Path
from collections import defaultdict

class DeadCodeAnalyzer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.frontend_src = self.project_root / "frontend/src"
        self.backend_src = self.project_root / "backend"
        
    def analyze_frontend_dependencies(self):
        """Frontend 패키지 의존성 분석"""
        print("🔍 Frontend 의존성 분석...")
        
        package_json = self.project_root / "frontend/package.json"
        if not package_json.exists():
            print("❌ package.json을 찾을 수 없습니다")
            return
            
        with open(package_json) as f:
            package_data = json.load(f)
            
        dependencies = package_data.get("dependencies", {})
        
        # 실제 사용되는 패키지 찾기
        used_packages = set()
        unused_packages = []
        
        # 모든 JS/TS 파일에서 import 구문 찾기
        for file_path in self.frontend_src.rglob("*.{js,jsx,ts,tsx}"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # import 구문 패턴 매칭
                import_patterns = [
                    r"import.*from\s+['\"]([^'\"]+)['\"]",
                    r"import\s+['\"]([^'\"]+)['\"]",
                    r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
                ]
                
                for pattern in import_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        # 상대 경로가 아닌 패키지명만 추출
                        if not match.startswith('.'):
                            package_name = match.split('/')[0]
                            used_packages.add(package_name)
                            
            except Exception as e:
                print(f"⚠️  {file_path} 분석 실패: {e}")
                
        # 미사용 패키지 찾기
        for package in dependencies:
            if package not in used_packages:
                # 특별한 케이스들 체크
                special_cases = {
                    'typescript': 'TypeScript 컴파일러',
                    'tailwindcss': 'CSS 프레임워크 (설정 파일에서 사용)',
                    'autoprefixer': 'PostCSS 플러그인',
                    'postcss': 'CSS 후처리기'
                }
                
                if package in special_cases:
                    print(f"🔧 {package}: {special_cases[package]} (설정에서 사용)")
                else:
                    unused_packages.append(package)
                    
        print(f"\n📊 Frontend 의존성 분석 결과:")
        print(f"   전체 의존성: {len(dependencies)}개")
        print(f"   사용 중: {len(used_packages)}개")
        print(f"   미사용 의심: {len(unused_packages)}개")
        
        if unused_packages:
            print(f"\n🗑️  미사용 의심 패키지:")
            for package in unused_packages:
                version = dependencies[package]
                print(f"   {package}: {version}")
                
        return unused_packages
        
    def analyze_unused_imports(self):
        """미사용 import 분석"""
        print("\n🔍 미사용 import 분석...")
        
        unused_imports = []
        
        # Python 파일들 분석
        for file_path in self.backend_src.rglob("*.py"):
            if "test" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # AST로 파싱
                tree = ast.parse(content)
                
                # import 구문들 찾기
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            for alias in node.names:
                                imports.append(f"{node.module}.{alias.name}")
                                
                # 실제 사용 여부 체크 (간단한 패턴 매칭)
                for imported in imports:
                    simple_name = imported.split('.')[-1]
                    if simple_name not in content.replace(f"import {imported}", ""):
                        unused_imports.append((file_path, imported))
                        
            except Exception as e:
                continue  # 파싱 에러는 무시
                
        print(f"📊 미사용 import 분석 결과: {len(unused_imports)}개 발견")
        
        if unused_imports:
            print("\n🗑️  미사용 import 목록 (일부):")
            for file_path, imported in unused_imports[:10]:  # 상위 10개만 표시
                rel_path = file_path.relative_to(self.project_root)
                print(f"   {rel_path}: {imported}")
                
            if len(unused_imports) > 10:
                print(f"   ... 및 {len(unused_imports) - 10}개 더")
                
        return unused_imports
        
    def analyze_unused_components(self):
        """미사용 React 컴포넌트 분석"""
        print("\n🔍 미사용 React 컴포넌트 분석...")
        
        # 모든 컴포넌트 파일 찾기
        component_files = []
        for file_path in self.frontend_src.rglob("*.{jsx,tsx}"):
            if file_path.name != "App.tsx" and file_path.name != "main.tsx":
                component_files.append(file_path)
                
        # 각 컴포넌트의 사용 여부 체크
        unused_components = []
        
        for comp_file in component_files:
            comp_name = comp_file.stem
            is_used = False
            
            # 다른 파일들에서 이 컴포넌트를 import하는지 체크
            for check_file in self.frontend_src.rglob("*.{js,jsx,ts,tsx}"):
                if check_file == comp_file:
                    continue
                    
                try:
                    with open(check_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # import 패턴들 체크
                    import_patterns = [
                        rf"import.*{comp_name}.*from",
                        rf"import\s+\{{[^}}]*{comp_name}[^}}]*\}}",
                        rf"<{comp_name}[>\s]"
                    ]
                    
                    for pattern in import_patterns:
                        if re.search(pattern, content):
                            is_used = True
                            break
                            
                    if is_used:
                        break
                        
                except Exception:
                    continue
                    
            if not is_used:
                unused_components.append(comp_file)
                
        print(f"📊 컴포넌트 분석 결과:")
        print(f"   전체 컴포넌트: {len(component_files)}개")
        print(f"   미사용 의심: {len(unused_components)}개")
        
        if unused_components:
            print(f"\n🗑️  미사용 의심 컴포넌트:")
            for comp_file in unused_components:
                rel_path = comp_file.relative_to(self.frontend_src)
                print(f"   {rel_path}")
                
        return unused_components
        
    def analyze_duplicate_utilities(self):
        """중복 유틸리티 함수 분석"""
        print("\n🔍 중복 유틸리티 함수 분석...")
        
        # 유틸리티 디렉토리들 스캔
        util_dirs = [
            self.frontend_src / "utils",
            self.backend_src / "app/utils"
        ]
        
        function_signatures = defaultdict(list)
        
        for util_dir in util_dirs:
            if not util_dir.exists():
                continue
                
            for file_path in util_dir.rglob("*.{py,js,ts}"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # 함수 정의 패턴 찾기
                    patterns = [
                        r"def\s+(\w+)\s*\(",  # Python
                        r"function\s+(\w+)\s*\(",  # JavaScript
                        r"const\s+(\w+)\s*=.*=>",  # Arrow function
                        r"export\s+const\s+(\w+)\s*="  # Export const
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            function_signatures[match].append(file_path)
                            
                except Exception:
                    continue
                    
        # 중복 함수들 찾기
        duplicates = {name: files for name, files in function_signatures.items() 
                     if len(files) > 1}
                     
        print(f"📊 유틸리티 함수 중복 분석:")
        print(f"   중복 함수명: {len(duplicates)}개")
        
        if duplicates:
            print(f"\n🔄 중복된 함수들:")
            for func_name, files in list(duplicates.items())[:5]:  # 상위 5개만
                print(f"   {func_name}:")
                for file_path in files:
                    rel_path = file_path.relative_to(self.project_root)
                    print(f"     - {rel_path}")
                    
        return duplicates
        
    def generate_optimization_recommendations(self, analysis_results):
        """최적화 권장사항 생성"""
        print("\n" + "="*60)
        print("💡 프로젝트 최적화 권장사항")
        print("="*60)
        
        unused_deps = analysis_results.get('unused_dependencies', [])
        unused_components = analysis_results.get('unused_components', [])
        duplicates = analysis_results.get('duplicates', {})
        
        recommendations = []
        
        if unused_deps:
            recommendations.append({
                'priority': 'HIGH',
                'category': '의존성 정리',
                'action': f'{len(unused_deps)}개 미사용 패키지 제거',
                'command': f'npm uninstall {" ".join(unused_deps)}',
                'impact': '번들 크기 감소, 보안 위험 감소'
            })
            
        if unused_components:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': '컴포넌트 정리',
                'action': f'{len(unused_components)}개 미사용 컴포넌트 제거',
                'command': '수동 검토 후 삭제',
                'impact': '코드베이스 단순화'
            })
            
        if duplicates:
            recommendations.append({
                'priority': 'MEDIUM', 
                'category': '중복 제거',
                'action': f'{len(duplicates)}개 중복 함수 통합',
                'command': '수동 리팩토링',
                'impact': '유지보수성 향상'
            })
            
        # 권장사항 출력
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. [{rec['priority']}] {rec['category']}")
            print(f"   📋 작업: {rec['action']}")
            print(f"   💻 명령어: {rec['command']}")
            print(f"   🎯 효과: {rec['impact']}")
            
        return recommendations

def main():
    parser = argparse.ArgumentParser(description='MAX Platform 데드 코드 분석 도구')
    parser.add_argument('--all', action='store_true', default=True,
                       help='전체 분석 (기본값)')
    parser.add_argument('--deps-only', action='store_true',
                       help='의존성만 분석')
    parser.add_argument('--imports-only', action='store_true',
                       help='import만 분석')
    parser.add_argument('--components-only', action='store_true',
                       help='컴포넌트만 분석')
    
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
        return
        
    analyzer = DeadCodeAnalyzer(project_root)
    
    print(f"🚀 MAX Platform 데드 코드 분석 시작")
    print(f"📁 프로젝트 경로: {project_root}")
    
    analysis_results = {}
    
    # 분석 실행
    if args.deps_only or args.all:
        analysis_results['unused_dependencies'] = analyzer.analyze_frontend_dependencies()
        
    if args.imports_only or args.all:
        analysis_results['unused_imports'] = analyzer.analyze_unused_imports()
        
    if args.components_only or args.all:
        analysis_results['unused_components'] = analyzer.analyze_unused_components()
        
    if args.all:
        analysis_results['duplicates'] = analyzer.analyze_duplicate_utilities()
        
    # 권장사항 생성
    if args.all:
        analyzer.generate_optimization_recommendations(analysis_results)

if __name__ == "__main__":
    main()