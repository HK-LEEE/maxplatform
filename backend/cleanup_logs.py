#!/usr/bin/env python3
"""
Script to identify and optionally remove unnecessary print() statements
from test and initialization scripts
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

def find_print_statements(file_path: str) -> List[Tuple[int, str]]:
    """Find all print() statements in a file"""
    print_statements = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                if re.search(r'\bprint\s*\(', line):
                    print_statements.append((i, line.strip()))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return print_statements

def should_clean_file(file_path: str) -> bool:
    """Determine if a file should be cleaned based on its purpose"""
    path = Path(file_path)
    name = path.name.lower()
    
    # Files that should be cleaned (test, init, debug, migration scripts)
    clean_patterns = [
        'test_', 'debug_', 'init_', 'create_', 'setup_', 'migrate_',
        'fix_', 'run_', 'check_', 'add_', 'update_', 'restore_',
        'recreate_', 'generate_', 'simulate_', 'monitor_'
    ]
    
    # Files that should NOT be cleaned (core application files)
    preserve_patterns = [
        'app/main.py', 'app/models/', 'app/routers/', 
        'app/services/', 'app/utils/', 'app/api/'
    ]
    
    # Check if it's in a core app directory
    str_path = str(path)
    for preserve in preserve_patterns:
        if preserve in str_path:
            return False
    
    # Check if it's a script that should be cleaned
    for pattern in clean_patterns:
        if name.startswith(pattern):
            return True
    
    return False

def get_log_level_suggestion(line: str) -> str:
    """Suggest appropriate log level based on print content"""
    line_lower = line.lower()
    
    if any(word in line_lower for word in ['error', 'failed', 'exception', 'traceback']):
        return 'ERROR'
    elif any(word in line_lower for word in ['warning', 'warn', 'deprecated']):
        return 'WARN'
    elif any(word in line_lower for word in ['info', 'success', 'completed', 'created', 'updated']):
        return 'INFO'
    else:
        return 'DEBUG'

def analyze_project():
    """Analyze the entire project for print statements"""
    print("🔍 Analyzing Python files for print() statements...")
    print("=" * 60)
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', '.venv', 'venv', 'node_modules']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    # Analyze each file
    files_to_clean = []
    files_to_preserve = []
    
    for file_path in python_files:
        print_statements = find_print_statements(file_path)
        if print_statements:
            should_clean = should_clean_file(file_path)
            
            file_info = {
                'path': file_path,
                'prints': print_statements,
                'should_clean': should_clean
            }
            
            if should_clean:
                files_to_clean.append(file_info)
            else:
                files_to_preserve.append(file_info)
    
    # Report results
    print(f"\n📊 Analysis Results:")
    print(f"Total Python files: {len(python_files)}")
    print(f"Files with print(): {len(files_to_clean) + len(files_to_preserve)}")
    print(f"Files recommended for cleanup: {len(files_to_clean)}")
    print(f"Core files to preserve: {len(files_to_preserve)}")
    
    # Show files to clean
    if files_to_clean:
        print(f"\n🧹 Files recommended for cleanup:")
        print("-" * 40)
        for file_info in files_to_clean:
            print(f"\n📁 {file_info['path']} ({len(file_info['prints'])} prints)")
            for line_num, line in file_info['prints'][:3]:  # Show first 3
                level = get_log_level_suggestion(line)
                print(f"  L{line_num}: {line[:80]}{'...' if len(line) > 80 else ''}")
                print(f"         → Suggested: logger.{level.lower()}(...)")
            if len(file_info['prints']) > 3:
                print(f"  ... and {len(file_info['prints']) - 3} more")
    
    # Show core files with prints
    if files_to_preserve:
        print(f"\n🔒 Core application files with print() (review needed):")
        print("-" * 50)
        for file_info in files_to_preserve:
            print(f"📁 {file_info['path']} ({len(file_info['prints'])} prints)")
            for line_num, line in file_info['prints'][:2]:  # Show first 2
                level = get_log_level_suggestion(line)
                print(f"  L{line_num}: {line[:60]}{'...' if len(line) > 60 else ''}")
                print(f"         → Consider: logger.{level.lower()}(...)")
    
    return files_to_clean, files_to_preserve

def generate_cleanup_script():
    """Generate a shell script to remove print statements from test files"""
    print(f"\n📝 Generating cleanup suggestions...")
    
    cleanup_script = """#!/bin/bash
# Auto-generated cleanup script for removing print() statements
# Review each change before applying!

echo "🧹 Cleaning up print() statements from test and init scripts..."

"""
    
    files_to_clean, _ = analyze_project()
    
    for file_info in files_to_clean:
        if len(file_info['prints']) > 5:  # Only for files with many prints
            cleanup_script += f"""
# Clean {file_info['path']} ({len(file_info['prints'])} prints)
echo "Cleaning {file_info['path']}..."
sed -i '/^[[:space:]]*print(/d' "{file_info['path']}"
"""
    
    cleanup_script += """
echo "✅ Cleanup completed. Please review changes before committing."
"""
    
    with open('cleanup_prints.sh', 'w') as f:
        f.write(cleanup_script)
    
    print(f"Generated cleanup_prints.sh - Review before running!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--generate-script":
        generate_cleanup_script()
    else:
        analyze_project()
        print(f"\n💡 Next steps:")
        print(f"1. Review the analysis above")
        print(f"2. Run: python cleanup_logs.py --generate-script")
        print(f"3. Review and run the generated cleanup script")
        print(f"4. Replace remaining prints with appropriate logger calls")