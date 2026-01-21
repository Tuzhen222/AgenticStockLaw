# BGE-M3 Model Conversion for Triton Inference Server

Pipeline để tải và chuyển đổi model BGE-M3 thành các định dạng tối ưu cho Triton Inference Server.

## Tổng quan

Pipeline này gồm 3 bước:
1. **Fetch Model**: Tải model BGE-M3 từ HuggingFace
2. **Convert to ONNX**: Chuyển đổi PyTorch model sang ONNX format
3. **Convert to TensorRT**: Tối ưu hoá ONNX model với TensorRT

## Cấu trúc thư mục

```
triton/
├── model_repository/
│   ├── bge_m3/              # PyTorch model
│   │   ├── 1/
│   │   │   └── model.pt
│   │   └── config.pbtxt
│   ├── bge_m3_onnx/         # ONNX model
│   │   ├── 1/
│   │   │   └── model.onnx
│   │   └── config.pbtxt
│   ├── bge_m3_trt/          # TensorRT engine
│   │   ├── 1/
│   │   │   └── model.plan
│   │   └── config.pbtxt
│   └── tokenizer/           # Shared tokenizer
│       └── ...
├── fetch_bge_model.py       # Script tải model
├── convert_pytorch_to_onnx.py
├── convert_onnx_to_tensorrt.py
└── README.md
```

## Hướng dẫn sử dụng

### 1. Cài đặt dependencies

```bash
pip install torch transformers onnx onnxruntime
# Cho TensorRT conversion:
pip install tensorrt pycuda
```

### 2. Tải model BGE-M3

```bash
python fetch_bge_model.py
```

### 3. Convert sang ONNX

```bash
python convert_pytorch_to_onnx.py
```

### 4. Convert sang TensorRT (optional)

```bash
docker run --gpus all -v $(pwd):/workspace -w /workspace \
  nvcr.io/nvidia/tensorrt:24.08-py3 \
  python3 convert_onnx_to_tensorrt.py
```

## Specifications

### Model Info

| Property | Value |
|----------|-------|
| Model | BAAI/bge-m3 |
| Hidden Size | 1024 |
| Max Sequence Length | 512 |
| ONNX Opset | 18 |

### Triton Configuration

| Property | Value |
|----------|-------|
| Max Batch Size | 8 |
| Dynamic Batching | Enabled |
| GPU Instance | 1 |

## Chạy Triton Server

```bash
docker run -it --rm -p 8000:8000 -p 8001:8001 -p 8002:8002 \
  -v $(pwd)/model_repository:/models \
  nvcr.io/nvidia/tritonserver:24.08-py3 tritonserver --model-repository=/models
```

## Notes

- BGE-M3 là một multilingual embedding model hỗ trợ dense, sparse và multi-vector retrieval
- Model có hidden_size=1024 giống E5-Large
- Khuyến nghị sử dụng FP16 mode với TensorRT để tối ưu performance
