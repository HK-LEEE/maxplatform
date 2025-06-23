# Cross-Platform Setup Guide for ipnyb_workspace

This guide provides instructions for setting up the ipnyb_workspace project on both Windows and macOS.

## Platform-Specific Dependencies

### Requirements.txt Differences

#### Windows-specific packages (remove on macOS):
- `pywinpty==2.0.15` - Windows terminal emulation
- `pyreadline3==3.5.4` - Windows readline implementation

#### macOS Installation:
```bash
# Remove Windows-specific packages from requirements.txt
pip install -r requirements.txt
```

### ODBC Driver for SQL Server

#### Windows:
- Uses: `ODBC Driver 17 for SQL Server`
- Pre-installed with SQL Server or download from Microsoft

#### macOS:
```bash
# Install ODBC Driver 18 for SQL Server
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18
```

Update connection string in `.env`:
```
# Windows
MSSQL_DATABASE_URL=mssql+pyodbc://sa:password@localhost:1433/jupyter_platform?driver=ODBC+Driver+17+for+SQL+Server

# macOS
MSSQL_DATABASE_URL=mssql+pyodbc://sa:password@localhost:1433/jupyter_platform?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

## OCR Setup

### Windows:
Follow `WINDOWS_OCR_SETUP.md`

### macOS:
Follow `MACOS_OCR_SETUP.md`

Key differences:
- Windows: Manual download and PATH configuration
- macOS: Simple `brew install poppler tesseract tesseract-lang`

## Database Recommendations

### For Cross-Platform Compatibility:
1. **PostgreSQL** (Recommended)
   - Works identically on both platforms
   - Better performance and features
   - Simple installation via Homebrew (macOS) or installer (Windows)

2. **MySQL**
   - Good cross-platform support
   - Consistent behavior across platforms

3. **SQL Server**
   - Requires different ODBC drivers per platform
   - More complex setup on macOS

## Environment Setup

### Using Platform-Specific .env Files:

```bash
# Windows
cp .env.example .env

# macOS
cp .env.macos .env
```

### Key Configuration Differences:

1. **ODBC Driver Names**:
   - Windows: `ODBC+Driver+17+for+SQL+Server`
   - macOS: `ODBC+Driver+18+for+SQL+Server`

2. **File Paths**:
   - Both platforms use relative paths (no changes needed)
   - Path separators handled automatically by Python

3. **Python Environment**:
   - Windows: Often uses `python` and `pip`
   - macOS: May use `python3` and `pip3`

## Installation Steps

### 1. Backend Setup

#### Both Platforms:
```bash
cd backend
python -m venv venv
```

#### Windows:
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

#### macOS:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend Setup

#### Both Platforms (identical):
```bash
cd frontend
npm install
```

### 3. Database Setup

#### PostgreSQL (Recommended for both):
```bash
# Windows: Download installer from postgresql.org
# macOS: brew install postgresql

# Create database
createdb platform_integration
```

### 4. Start Services

#### Backend:
```bash
# Both platforms
cd backend
python main.py
```

#### Frontend:
```bash
# Both platforms
cd frontend
npm run dev
```

## Troubleshooting

### Common Cross-Platform Issues:

1. **Port Already in Use**:
   - Check with `netstat -an | grep 8000` (macOS/Linux)
   - Check with `netstat -an | findstr 8000` (Windows)

2. **Python Version Conflicts**:
   - Use virtual environments consistently
   - Ensure Python 3.8+ on both platforms

3. **Node.js Version**:
   - Use Node.js 16+ on both platforms
   - Consider using `nvm` (macOS) or `nvm-windows`

4. **File Permissions**:
   - Windows: Run as Administrator if needed
   - macOS: Use `sudo` for system-level operations

## Development Tools

### Recommended IDE Setup:
- **VS Code**: Works identically on both platforms
- **PyCharm**: Cross-platform with same features

### Git Configuration:
```bash
# Prevent line ending issues
git config --global core.autocrlf true  # Windows
git config --global core.autocrlf input # macOS/Linux
```

## Deployment Considerations

### Docker (Recommended):
- Ensures consistent environment across platforms
- Eliminates platform-specific issues
- Use Linux-based images for production

### Platform-Specific Scripts:
- `.bat` files for Windows
- `.sh` files for macOS/Linux
- Consider using Python scripts for cross-platform automation

## Summary

The ipnyb_workspace project is designed to be cross-platform compatible with minimal changes:

1. Remove Windows-specific Python packages on macOS
2. Use appropriate ODBC drivers for each platform
3. Follow platform-specific OCR setup guides
4. Prefer PostgreSQL for database to avoid driver issues
5. Use virtual environments and consistent Python versions

Most of the codebase works identically on both platforms thanks to Python's cross-platform nature and careful use of path handling.