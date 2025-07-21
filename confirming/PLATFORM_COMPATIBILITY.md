# Platform Compatibility Guide

## Overview

The ipnyb_workspace project is designed to be cross-platform compatible, supporting Windows, macOS, and Linux. This guide outlines the platform-specific considerations and requirements.

## Quick Setup

### Automated Platform Setup

Run the platform setup script to automatically configure your environment:

```bash
cd backend
python setup_platform.py
```

This script will:
- Detect your operating system
- Check for required dependencies
- Configure platform-specific settings
- Create appropriate requirements file
- Install Python dependencies

## Platform-Specific Requirements

### Python Dependencies

#### Windows-Only Packages
- `pywinpty==2.0.15` - Windows pseudo terminal support
- `pyreadline3==3.5.4` - Enhanced readline for Windows

#### Cross-Platform Packages
- `pyodbc==4.0.39` - Requires platform-specific ODBC drivers

### System Dependencies

#### macOS
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install postgresql      # Database (recommended)
brew install poppler         # PDF processing
brew install tesseract       # OCR support
brew install tesseract-lang  # Additional languages for OCR

# For SQL Server support (optional)
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18
```

#### Windows
- PostgreSQL: Download from https://www.postgresql.org/download/windows/
- Poppler: See `WINDOWS_OCR_SETUP.md`
- Tesseract: See `WINDOWS_OCR_SETUP.md`
- SQL Server ODBC Driver: Usually pre-installed or download from Microsoft

#### Linux (Ubuntu/Debian)
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo apt-get install -y poppler-utils
sudo apt-get install -y tesseract-ocr tesseract-ocr-kor

# For SQL Server support (optional)
# Follow Microsoft's guide for Linux ODBC driver installation
```

## Database Configuration

### PostgreSQL (Recommended)
Works identically across all platforms:
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/platform_integration
```

### SQL Server
Requires different ODBC drivers:

**Windows:**
```
MSSQL_DATABASE_URL=mssql+pyodbc://sa:password@localhost:1433/jupyter_platform?driver=ODBC+Driver+17+for+SQL+Server
```

**macOS:**
```
MSSQL_DATABASE_URL=mssql+pyodbc://sa:password@localhost:1433/jupyter_platform?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

**Linux:**
```
MSSQL_DATABASE_URL=mssql+pyodbc://sa:password@localhost:1433/jupyter_platform?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

## File Path Handling

The project uses cross-platform path handling:
- Uses `os.path.join()` and `pathlib` for path construction
- No hardcoded Windows paths (C:\, etc.)
- All paths are relative or configurable via environment variables

## OCR Support

### Setup Guides
- Windows: See `WINDOWS_OCR_SETUP.md`
- macOS: See `MACOS_OCR_SETUP.md`

### Key Differences
- **Windows**: Manual installation and PATH configuration required
- **macOS**: Simple installation via Homebrew
- **Linux**: Installation via package manager (apt, yum, etc.)

## Development Environment

### Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Running the Application

Commands are identical across platforms:
```bash
# Backend
cd backend
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

## Known Platform-Specific Issues

### Windows
1. Long path names may cause issues - enable long path support in Windows
2. Case-insensitive filesystem - be careful with file naming
3. Different line endings (CRLF vs LF) - configure Git appropriately

### macOS
1. Apple Silicon (M1/M2) - Some packages may need Rosetta 2
2. Homebrew paths differ between Intel (/usr/local) and ARM (/opt/homebrew)
3. Security permissions may require allowing terminal access

### Linux
1. Different package managers (apt, yum, pacman) require different commands
2. May need to install Python development headers (python3-dev)
3. SELinux or AppArmor may require additional configuration

## Docker Support

For maximum compatibility, use Docker:

```yaml
# docker-compose.yml example
version: '3.8'
services:
  backend:
    build: ./backend
    platform: linux/amd64  # Ensures compatibility
    ports:
      - "8000:8000"
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
```

## Testing Platform Compatibility

Run platform-specific tests:
```bash
# Test OCR functionality
python backend/test_ocr.py

# Test database connectivity
python backend/test_db_connection.py

# Test file operations
python backend/test_file_operations.py
```

## Contributing

When contributing code:
1. Test on multiple platforms if possible
2. Use cross-platform libraries and approaches
3. Avoid platform-specific code unless necessary
4. Document any platform-specific requirements

## Support

For platform-specific issues:
- Check the troubleshooting section in this guide
- Review platform-specific setup guides
- Create an issue with platform details and error messages