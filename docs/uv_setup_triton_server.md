# UV Package Manager Setup for Triton Server

**Created:** 2026-02-02  
**Purpose:** Documentation for UV package manager setup in the triton_server project

## Overview

This document describes the setup of [UV](https://github.com/astral-sh/uv), a fast Python package installer and resolver written in Rust, for the BGE-M3 Triton Server project.

## What is UV?

UV is a modern Python package manager that provides:
- **Fast**: 10-100x faster than pip
- **Reliable**: Uses a deterministic resolver
- **Compatible**: Works with existing pip/PyPI ecosystem
- **Convenient**: Manages Python versions and virtual environments

## Files Created

### 1. [pyproject.toml](file:///d:/code/AgenticStockLaw/triton_server/pyproject.toml)

Modern Python project configuration file that replaces `requirements.txt`. Contains:
- Project metadata (name, version, description)
- Python version requirement (>=3.10)
- All dependencies from requirements.txt
- Build system configuration
- UV-specific settings

### 2. [.python-version](file:///d:/code/AgenticStockLaw/triton_server/.python-version)

Specifies Python 3.11 as the project's Python version. UV will automatically use this version when creating virtual environments.

## Installation & Usage

### Install UV

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Initialize Project

```bash
cd d:\code\AgenticStockLaw\triton_server

# Create virtual environment
uv venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\activate
# WSL/Linux/macOS:
source .venv/bin/activate

# Install core dependencies (recommended for development)
uv pip install -e .

# Install with TensorRT support (requires CUDA toolkit + build tools)
uv pip install -e ".[tensorrt]"
```

> [!IMPORTANT]
> TensorRT and PyCUDA require:
> - NVIDIA CUDA Toolkit (nvcc compiler)
> - C++ build tools (gcc/g++)
> - NVIDIA GPU
> 
> For local development without GPU, install only core dependencies. TensorRT conversion is typically done in Docker with the official NVIDIA image.

### Common Commands

```bash
# Add a new dependency
uv pip install <package-name>

# Install from pyproject.toml
uv pip install -e .

# Update dependencies
uv pip install --upgrade -e .

# Sync exact dependencies
uv pip sync

# Run Python with UV
uv run python script.py
```

## Migration from requirements.txt

All dependencies from `requirements.txt` have been migrated to `pyproject.toml`:

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| transformers | >=4.35.0 | HuggingFace model loading |
| torch | >=2.0.0 | PyTorch framework |
| numpy | >=1.24.0 | Numerical operations |
| onnx | >=1.14.0 | ONNX format support |
| onnxruntime | >=1.16.0 | ONNX runtime |
| tritonclient[all] | >=2.40.0 | Triton client library |

### Optional Dependencies (TensorRT)

| Package | Version | Purpose |
|---------|---------|---------|
| tensorrt | >=8.6.0 | TensorRT engine (requires CUDA) |
| pycuda | >=2022.2 | CUDA bindings (requires CUDA toolkit) |

## Benefits for This Project

1. **Faster installs**: Especially beneficial for large packages like PyTorch and TensorRT
2. **Better dependency resolution**: Fewer conflicts between dependencies
3. **Reproducible environments**: Lock file ensures consistent installations
4. **Python version management**: UV can install and manage Python versions
5. **Modern tooling**: Better aligned with current Python best practices

## Next Steps

> [!IMPORTANT]
> You need to install UV first using the commands above before you can use these features.

After installing UV:
1. Run `uv venv` to create a virtual environment
2. Run `uv pip install -e .` to install all dependencies
3. Replace `pip install` with `uv pip install` in workflows
4. Consider adding `uv.lock` to track exact dependency versions

## References

- [UV Documentation](https://github.com/astral-sh/uv)
- [pyproject.toml Specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [Original README](file:///d:/code/AgenticStockLaw/triton_server/README.md)
