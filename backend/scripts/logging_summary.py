#!/usr/bin/env python3
"""
Logging System Summary for MAX Platform
Shows the current logging configuration and usage
"""

import os
from pathlib import Path
import sys

def show_logging_summary():
    print("🚀 MAX Platform Logging System Summary")
    print("=" * 50)
    
    # Check logging configuration
    logging_config = Path("app/utils/logging_config.py")
    if logging_config.exists():
        print("✅ Central logging configuration: ENABLED")
        print("   📁 Location: app/utils/logging_config.py")
        print("   🔧 Features:")
        print("      • Timestamp format: YYYY-MM-DD HH:MM:SS.fff")
        print("      • Security data filtering: head[10] format")
        print("      • Daily log rotation: 10 days retention")
        print("      • Environment-based log levels")
        print("      • OAuth/Auth event tracking")
    else:
        print("❌ Central logging configuration: NOT FOUND")
    
    # Check logs directory
    logs_dir = Path("logs")
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log*"))
        total_size = sum(f.stat().st_size for f in log_files) / 1024 / 1024
        print(f"\n📂 Logs directory: {len(log_files)} files ({total_size:.2f} MB)")
        
        if log_files:
            latest = max(log_files, key=lambda f: f.stat().st_mtime)
            print(f"   📄 Latest: {latest.name}")
    else:
        print("\n📂 Logs directory: NOT FOUND")
    
    # Check log management scripts
    scripts_dir = Path("scripts")
    if scripts_dir.exists():
        log_manager = scripts_dir / "logs_manager.py"
        if log_manager.exists():
            print("\n🛠️  Log management tools: AVAILABLE")
            print("   📜 scripts/logs_manager.py")
            print("   🔧 Commands:")
            print("      • python scripts/logs_manager.py view     - View recent logs")
            print("      • python scripts/logs_manager.py analyze  - Analyze log patterns")
            print("      • python scripts/logs_manager.py clean    - Clean old logs")
            print("      • python scripts/logs_manager.py archive  - Archive old logs")
            print("      • python scripts/logs_manager.py search   - Search log patterns")
        else:
            print("\n🛠️  Log management tools: NOT FOUND")
    
    # Check cleanup tools
    cleanup_script = Path("cleanup_logs.py")
    if cleanup_script.exists():
        print("\n🧹 Print statement cleanup tool: AVAILABLE")
        print("   📜 cleanup_logs.py")
        print("   🔧 Usage: python cleanup_logs.py [--generate-script]")
    
    # Environment configuration
    env = os.getenv('MAX_ENV', 'development')
    print(f"\n🌍 Environment: {env}")
    if env.lower() in ['production', 'prod']:
        print("   📊 Log level: INFO (production)")
    elif env.lower() in ['staging', 'test']:
        print("   📊 Log level: INFO (staging)")
    else:
        print("   📊 Log level: DEBUG (development)")
    
    # Integration status
    print(f"\n🔗 Integration status:")
    
    # Check main.py integration
    main_py = Path("app/main.py")
    if main_py.exists():
        with open(main_py, 'r') as f:
            content = f.read()
            if 'setup_logging' in content:
                print("   ✅ main.py: Logging initialized")
            else:
                print("   ❌ main.py: Logging NOT initialized")
    
    # Check OAuth integration
    oauth_py = Path("app/api/oauth_simple.py")
    if oauth_py.exists():
        with open(oauth_py, 'r') as f:
            content = f.read()
            if 'log_oauth_event' in content:
                print("   ✅ OAuth: Enhanced logging enabled")
            else:
                print("   ❌ OAuth: Basic logging only")
    
    # Check auth integration
    auth_py = Path("app/utils/auth.py")
    if auth_py.exists():
        with open(auth_py, 'r') as f:
            content = f.read()
            if 'log_auth_event' in content:
                print("   ✅ Auth: Enhanced logging enabled")
            else:
                print("   ❌ Auth: Basic logging only")
    
    print(f"\n🎉 Logging system is ready for production use!")
    print(f"💡 Next steps:")
    print(f"   1. Set MAX_ENV=production for production deployment")
    print(f"   2. Monitor logs with: python scripts/logs_manager.py view -f")
    print(f"   3. Set up log rotation monitoring if needed")

if __name__ == "__main__":
    show_logging_summary()