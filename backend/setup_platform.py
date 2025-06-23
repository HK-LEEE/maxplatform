#!/usr/bin/env python3
"""
Platform-specific setup script for ipnyb_workspace
Automatically configures the project based on the operating system
"""

import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path

def detect_platform():
    """Detect the current operating system"""
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'windows':
        return 'windows'
    elif system == 'linux':
        return 'linux'
    else:
        return 'unknown'

def check_dependencies():
    """Check if required system dependencies are installed"""
    current_platform = detect_platform()
    missing_deps = []
    
    if current_platform == 'macos':
        # Check for Homebrew
        if subprocess.run(['which', 'brew'], capture_output=True).returncode != 0:
            print("❌ Homebrew is not installed. Please install it first:")
            print('   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
            missing_deps.append('homebrew')
        
        # Check for OCR dependencies
        if subprocess.run(['which', 'pdftoppm'], capture_output=True).returncode != 0:
            print("❌ Poppler is not installed. Run: brew install poppler")
            missing_deps.append('poppler')
        
        if subprocess.run(['which', 'tesseract'], capture_output=True).returncode != 0:
            print("❌ Tesseract is not installed. Run: brew install tesseract tesseract-lang")
            missing_deps.append('tesseract')
    
    elif current_platform == 'windows':
        # Check for OCR dependencies
        poppler_check = subprocess.run(['where', 'pdftoppm'], capture_output=True, shell=True)
        if poppler_check.returncode != 0:
            print("❌ Poppler is not installed. Please follow WINDOWS_OCR_SETUP.md")
            missing_deps.append('poppler')
        
        tesseract_check = subprocess.run(['where', 'tesseract'], capture_output=True, shell=True)
        if tesseract_check.returncode != 0:
            print("❌ Tesseract is not installed. Please follow WINDOWS_OCR_SETUP.md")
            missing_deps.append('tesseract')
    
    return missing_deps

def setup_environment():
    """Setup platform-specific environment configuration"""
    current_platform = detect_platform()
    env_file = Path('.env')
    
    print(f"🔍 Detected platform: {current_platform}")
    
    # Backup existing .env if it exists
    if env_file.exists():
        backup_file = env_file.with_suffix('.env.backup')
        shutil.copy(env_file, backup_file)
        print(f"📋 Backed up existing .env to {backup_file}")
    
    # Copy platform-specific .env file
    if current_platform == 'macos':
        if Path('.env.macos').exists():
            shutil.copy('.env.macos', '.env')
            print("✅ Copied .env.macos to .env")
        else:
            print("⚠️  .env.macos not found, using .env.example")
            if Path('.env.example').exists():
                shutil.copy('.env.example', '.env')
    
    elif current_platform == 'windows':
        if Path('.env.example').exists():
            shutil.copy('.env.example', '.env')
            print("✅ Copied .env.example to .env")
    
    # Update ODBC driver in .env for macOS
    if current_platform == 'macos' and env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Replace Windows ODBC driver with macOS version
        content = content.replace(
            'driver=ODBC+Driver+17+for+SQL+Server',
            'driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes'
        )
        
        with open(env_file, 'w') as f:
            f.write(content)
        print("✅ Updated ODBC driver configuration for macOS")

def create_platform_requirements():
    """Create platform-specific requirements file"""
    current_platform = detect_platform()
    
    with open('requirements.txt', 'r') as f:
        requirements = f.readlines()
    
    # Filter out Windows-specific packages for non-Windows platforms
    if current_platform != 'windows':
        windows_packages = ['pywinpty', 'pyreadline3']
        filtered_requirements = []
        
        for line in requirements:
            package_name = line.strip().split('==')[0].lower()
            if package_name not in windows_packages:
                filtered_requirements.append(line)
        
        # Write platform-specific requirements
        platform_req_file = f'requirements_{current_platform}.txt'
        with open(platform_req_file, 'w') as f:
            f.writelines(filtered_requirements)
        
        print(f"✅ Created {platform_req_file} without Windows-specific packages")
        return platform_req_file
    
    return 'requirements.txt'

def install_python_dependencies():
    """Install Python dependencies"""
    current_platform = detect_platform()
    req_file = create_platform_requirements()
    
    print("\n📦 Installing Python dependencies...")
    
    # Create virtual environment if it doesn't exist
    if not Path('venv').exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, '-m', 'venv', 'venv'])
    
    # Determine pip path
    if current_platform == 'windows':
        pip_path = Path('venv/Scripts/pip')
    else:
        pip_path = Path('venv/bin/pip')
    
    # Install requirements
    if pip_path.exists():
        subprocess.run([str(pip_path), 'install', '-r', req_file])
        print(f"✅ Installed dependencies from {req_file}")
    else:
        print("❌ Could not find pip in virtual environment")
        print("   Please activate the virtual environment and run: pip install -r", req_file)

def print_next_steps():
    """Print next steps for the user"""
    current_platform = detect_platform()
    
    print("\n" + "="*50)
    print("🎉 Platform setup complete!")
    print("="*50)
    print("\nNext steps:")
    
    if current_platform == 'windows':
        print("1. Activate virtual environment: venv\\Scripts\\activate")
    else:
        print("1. Activate virtual environment: source venv/bin/activate")
    
    print("2. Set up the database (PostgreSQL recommended)")
    print("3. Update .env with your configuration")
    print("4. Run database migrations: python init_db.py")
    print("5. Start the backend: python main.py")
    print("\nFor frontend setup:")
    print("1. cd ../frontend")
    print("2. npm install")
    print("3. npm run dev")
    
    if current_platform == 'macos':
        print("\nFor OCR support, see MACOS_OCR_SETUP.md")
    elif current_platform == 'windows':
        print("\nFor OCR support, see WINDOWS_OCR_SETUP.md")

def main():
    """Main setup function"""
    print("🚀 ipnyb_workspace Platform Setup")
    print("="*50)
    
    # Check platform
    current_platform = detect_platform()
    if current_platform == 'unknown':
        print("❌ Unsupported platform detected")
        return 1
    
    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
        print("Please install the missing dependencies before continuing.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return 1
    
    # Setup environment
    setup_environment()
    
    # Install Python dependencies
    response = input("\nInstall Python dependencies? (Y/n): ")
    if response.lower() != 'n':
        install_python_dependencies()
    
    # Print next steps
    print_next_steps()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())