# BGE-M3 ONNX Conversion Update

**Date:** 2026-02-02  
**Change:** Modified tokenizer loading to use HuggingFace directly

## Changes Made

Updated [convert_pytorch_to_onnx.py](file:///d:/code/AgenticStockLaw/triton_server/convert_pytorch_to_onnx.py) to load the BGE-M3 tokenizer directly from HuggingFace (`BAAI/bge-m3`) instead of from a local directory.

### Modified Functions

1. **`convert_to_onnx()`** - Line 47: Changed from local `tokenizer_dir` to `"BAAI/bge-m3"`
2. **`verify_onnx_model()`** - Line 157: Changed from local `tokenizer_dir` to `"BAAI/bge-m3"`

### Benefits

- ✅ No need to run `fetch_bge_model.py` first
- ✅ Always uses the latest tokenizer from HuggingFace
- ✅ Simpler workflow - just run `python3 convert_pytorch_to_onnx.py`

## Usage

```bash
# Install sentencepiece first
pip install sentencepiece

# Run the converter (will download from HuggingFace)
python3 convert_pytorch_to_onnx.py
```

The script will now download both the model and tokenizer from HuggingFace automatically.
