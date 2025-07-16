#!/usr/bin/env python3
"""
Log Management Utility for MAX Platform
Provides tools for cleaning, viewing, and analyzing logs
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import glob
import gzip

def clean_logs(days_to_keep: int = 10):
    """Clean old log files"""
    logs_dir = Path("./logs")
    if not logs_dir.exists():
        print("📁 No logs directory found")
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cleaned_count = 0
    
    print(f"🧹 Cleaning logs older than {days_to_keep} days...")
    
    for log_file in logs_dir.glob("*.log*"):
        try:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                print(f"  🗑️  Removing: {log_file.name}")
                log_file.unlink()
                cleaned_count += 1
        except Exception as e:
            print(f"  ❌ Error removing {log_file.name}: {e}")
    
    print(f"✅ Cleaned {cleaned_count} old log files")

def view_logs(follow: bool = False, lines: int = 50):
    """View recent logs"""
    logs_dir = Path("./logs")
    if not logs_dir.exists():
        print("📁 No logs directory found")
        return
    
    # Find the most recent log file
    log_files = list(logs_dir.glob("backend*.log"))
    if not log_files:
        print("📝 No log files found")
        return
    
    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
    print(f"📖 Viewing: {latest_log.name}")
    
    if follow:
        # Follow mode (like tail -f)
        try:
            subprocess.run(["tail", "-f", str(latest_log)])
        except KeyboardInterrupt:
            print("\n👋 Stopped following logs")
    else:
        # Show last N lines
        try:
            result = subprocess.run(["tail", f"-{lines}", str(latest_log)], 
                                  capture_output=True, text=True)
            print(result.stdout)
        except Exception as e:
            print(f"❌ Error reading log: {e}")

def analyze_logs():
    """Analyze log patterns and statistics"""
    logs_dir = Path("./logs")
    if not logs_dir.exists():
        print("📁 No logs directory found")
        return
    
    log_files = list(logs_dir.glob("backend*.log"))
    if not log_files:
        print("📝 No log files found")
        return
    
    print("📊 Log Analysis")
    print("=" * 40)
    
    # File statistics
    total_size = sum(f.stat().st_size for f in log_files)
    print(f"Total log files: {len(log_files)}")
    print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
    
    # Analyze latest log for patterns
    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
    print(f"\nAnalyzing: {latest_log.name}")
    
    log_levels = {"ERROR": 0, "WARN": 0, "INFO": 0, "DEBUG": 0}
    oauth_events = 0
    auth_events = 0
    
    try:
        with open(latest_log, 'r') as f:
            for line in f:
                # Count log levels
                for level in log_levels:
                    if f"[{level}]" in line:
                        log_levels[level] += 1
                        break
                
                # Count OAuth events
                if "OAuth event:" in line or "oauth" in line.lower():
                    oauth_events += 1
                
                # Count Auth events
                if "Auth event:" in line or "auth" in line.lower():
                    auth_events += 1
        
        print(f"\nLog Level Distribution:")
        for level, count in log_levels.items():
            print(f"  {level}: {count}")
        
        print(f"\nEvent Counts:")
        print(f"  OAuth events: {oauth_events}")
        print(f"  Auth events: {auth_events}")
        
    except Exception as e:
        print(f"❌ Error analyzing log: {e}")

def archive_logs():
    """Archive old logs by compressing them"""
    logs_dir = Path("./logs")
    if not logs_dir.exists():
        print("📁 No logs directory found")
        return
    
    cutoff_date = datetime.now() - timedelta(days=3)
    archived_count = 0
    
    print("📦 Archiving old logs...")
    
    for log_file in logs_dir.glob("backend*.log"):
        try:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_date and not log_file.name.endswith('.gz'):
                # Compress the file
                with open(log_file, 'rb') as f_in:
                    with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                        f_out.write(f_in.read())
                
                # Remove original
                log_file.unlink()
                archived_count += 1
                print(f"  📦 Archived: {log_file.name}")
                
        except Exception as e:
            print(f"  ❌ Error archiving {log_file.name}: {e}")
    
    print(f"✅ Archived {archived_count} log files")

def search_logs(pattern: str, context: int = 3):
    """Search for patterns in logs"""
    logs_dir = Path("./logs")
    if not logs_dir.exists():
        print("📁 No logs directory found")
        return
    
    log_files = list(logs_dir.glob("backend*.log"))
    if not log_files:
        print("📝 No log files found")
        return
    
    print(f"🔍 Searching for pattern: '{pattern}'")
    print("=" * 50)
    
    for log_file in sorted(log_files, key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            result = subprocess.run([
                "grep", "-n", "-C", str(context), pattern, str(log_file)
            ], capture_output=True, text=True)
            
            if result.stdout:
                print(f"\n📁 {log_file.name}:")
                print("-" * 30)
                print(result.stdout)
                
        except Exception as e:
            print(f"❌ Error searching {log_file.name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="MAX Platform Log Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean old log files')
    clean_parser.add_argument('--days', type=int, default=10, 
                             help='Keep logs newer than N days (default: 10)')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View recent logs')
    view_parser.add_argument('-f', '--follow', action='store_true',
                            help='Follow log output (like tail -f)')
    view_parser.add_argument('-n', '--lines', type=int, default=50,
                            help='Number of lines to show (default: 50)')
    
    # Analyze command
    subparsers.add_parser('analyze', help='Analyze log patterns')
    
    # Archive command
    subparsers.add_parser('archive', help='Archive old logs')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search logs for patterns')
    search_parser.add_argument('pattern', help='Pattern to search for')
    search_parser.add_argument('-C', '--context', type=int, default=3,
                              help='Lines of context around matches (default: 3)')
    
    args = parser.parse_args()
    
    if args.command == 'clean':
        clean_logs(args.days)
    elif args.command == 'view':
        view_logs(args.follow, args.lines)
    elif args.command == 'analyze':
        analyze_logs()
    elif args.command == 'archive':
        archive_logs()
    elif args.command == 'search':
        search_logs(args.pattern, args.context)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()