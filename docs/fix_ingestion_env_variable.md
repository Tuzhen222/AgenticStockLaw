# Fixed Ingestion Script Environment Variable

**Date:** 2026-02-02  
**Issue:** Hardcoded model name in ingestion script

## Problem

The [ingestion script](file:///d:/code/AgenticStockLaw/ai/knowledge/vector_db/ingest.py) had a hardcoded value on line 29:
```python
MODEL_NAME = "bge_m3_tensorrt"
```

This ignored the `EMBEDDING_MODEL` environment variable in `.env`, causing it to always try to use the TensorRT model even when configured for ONNX.

## Solution

Changed line 29 to:
```python
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "bge_m3_onnx")  # Default to ONNX
```

Now it reads from the `EMBEDDING_MODEL` environment variable with a sensible default.

## Usage

Set in your `.env` file:
```bash
EMBEDDING_MODEL=bge_m3_onnx
```

Or override at runtime:
```bash
EMBEDDING_MODEL=bge_m3_tensorrt python knowledge/vector_db/ingest.py
```

✅ The script now respects the environment configuration!
