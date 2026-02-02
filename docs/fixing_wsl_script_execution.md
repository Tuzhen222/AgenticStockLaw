# Fixing WSL Script Execution Issues

**Date:** 2026-02-02  
**Issue:** "cannot execute: required file not found" when running shell scripts in WSL

## Problem

When running `./entrypoint.sh` in WSL, you may encounter this error:
```
-bash: ./entrypoint.sh: cannot execute: required file not found
```

This error occurs even though the file exists! The issue is that the file has **Windows line endings (CRLF)** instead of **Unix line endings (LF)**.

## Root Cause

- **Windows**: Uses `\r\n` (Carriage Return + Line Feed) for line endings
- **Unix/Linux/WSL**: Uses `\n` (Line Feed only) for line endings

When a shell script has CRLF endings, the shebang (`#!/bin/bash`) becomes `#!/bin/bash\r`, and WSL looks for a file called `bash\r` which doesn't exist - hence "required file not found".

## Solution

### Fixed Files

I've fixed [ai/entrypoint.sh](file:///d:/code/AgenticStockLaw/ai/entrypoint.sh) to use Unix line endings (LF).

### How to Run

```bash
cd d:/code/AgenticStockLaw/ai

# Make executable (if needed)
chmod +x entrypoint.sh

# Run the script
./entrypoint.sh
```

## Prevention - Git Configuration

To prevent this issue in the future, configure Git to auto-convert line endings:

```bash
# Global configuration (recommended)
git config --global core.autocrlf true

# Repository-specific (in project root)
cd d:/code/AgenticStockLaw
git config core.autocrlf true
```

### .gitattributes File

You can also add a `.gitattributes` file to enforce line endings:

```gitattributes
# Shell scripts must use LF
*.sh text eol=lf

# Python files can use LF
*.py text eol=lf

# Windows batch files use CRLF
*.bat text eol=crlf
*.cmd text eol=crlf
```

## Manual Conversion (if needed)

If you encounter this issue with other files:

### Using dos2unix (install first)
```bash
# Install dos2unix
sudo apt-get install dos2unix

# Convert file
dos2unix filename.sh
```

### Using sed
```bash
# Convert CRLF to LF
sed -i 's/\r$//' filename.sh
```

### Using Visual Studio Code
1. Open the file
2. Click "CRLF" in the bottom-right status bar
3. Select "LF"
4. Save the file

## Common Files That Need LF

- `*.sh` - Shell scripts
- `Dockerfile` - Docker build files
- `Makefile` - Make build files
- `.env` - Environment files (if used in containers)

## Summary

✅ **Fixed** [ai/entrypoint.sh](file:///d:/code/AgenticStockLaw/ai/entrypoint.sh) - Now uses LF line endings  
✅ Script should now execute properly in WSL

**Next steps:**
1. Try running `./entrypoint.sh` again
2. Add `.gitattributes` to prevent future issues
