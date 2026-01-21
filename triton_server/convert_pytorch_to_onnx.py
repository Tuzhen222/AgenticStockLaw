"""
Convert PyTorch BGE-M3 Model to ONNX Format
Exports the BGE-M3 model to ONNX in Triton model repository format.
"""

import os
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModel


# Triton model repository paths
MODEL_REPOSITORY = Path(__file__).parent / "model_repository"
ONNX_MODEL_DIR = MODEL_REPOSITORY / "bge_m3_onnx"
TOKENIZER_DIR = MODEL_REPOSITORY / "tokenizer"


def convert_to_onnx(
    model_repository: Path = MODEL_REPOSITORY,
    max_length: int = 8192,
    opset_version: int = 18
) -> str:
    """
    Convert PyTorch BGE-M3 model to ONNX format in Triton structure.
    
    Args:
        model_repository: Root directory for Triton model repository
        max_length: Maximum sequence length
        opset_version: ONNX opset version
        
    Returns:
        Path to the exported ONNX model
    """
    onnx_dir = model_repository / "bge_m3_onnx"
    tokenizer_dir = model_repository / "tokenizer"
    
    # Create Triton directory structure
    version_dir = onnx_dir / "1"
    version_dir.mkdir(parents=True, exist_ok=True)
    
    onnx_path = version_dir / "model.onnx"
    
    print(f"Loading tokenizer from: {tokenizer_dir}")
    print(f"Loading model from HuggingFace...")
    
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir)
    model = AutoModel.from_pretrained("BAAI/bge-m3")
    
    # Load saved weights if available
    pytorch_weights = model_repository / "bge_m3" / "1" / "model.pt"
    if pytorch_weights.exists():
        model.load_state_dict(torch.load(pytorch_weights))
        print(f"✓ Loaded weights from: {pytorch_weights}")
    
    model.eval()
    
    # Create dummy inputs for tracing - use batch of 2 to ensure dynamic batch axis
    dummy_texts = ["This is a sample text", "Another sample for batch"]
    dummy_inputs = tokenizer(
        dummy_texts,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=max_length
    )
    
    # Define dynamic axes for variable batch size and sequence length
    dynamic_axes = {
        "input_ids": {0: "batch_size", 1: "sequence_length"},
        "attention_mask": {0: "batch_size", 1: "sequence_length"},
        "last_hidden_state": {0: "batch_size", 1: "sequence_length"},
        "pooler_output": {0: "batch_size"}
    }
    
    input_names = ["input_ids", "attention_mask"]
    
    print(f"\nExporting to ONNX: {onnx_path}")
    print(f"  - Opset version: {opset_version}")
    print(f"  - Max sequence length: {max_length}")
    
    # Export to ONNX
    torch.onnx.export(
        model,
        (dummy_inputs["input_ids"], dummy_inputs["attention_mask"]),
        str(onnx_path),
        input_names=input_names,
        output_names=["last_hidden_state", "pooler_output"],
        dynamic_axes=dynamic_axes,
        opset_version=opset_version,
        do_constant_folding=True,
        export_params=True,
        verbose=False
    )
    
    print(f"✓ ONNX model exported to: {onnx_path}")
    
    # Create Triton config.pbtxt for ONNX
    # BGE-M3 has hidden_size=1024
    config_content = '''name: "bge_m3_onnx"
platform: "onnxruntime_onnx"
max_batch_size: 8

input [
  {
    name: "input_ids"
    data_type: TYPE_INT64
    dims: [ -1 ]
  },
  {
    name: "attention_mask"
    data_type: TYPE_INT64
    dims: [ -1 ]
  }
]

output [
  {
    name: "last_hidden_state"
    data_type: TYPE_FP32
    dims: [ -1, 1024 ]
  }
]

instance_group [
  {
    count: 1
    kind: KIND_CPU
  }
]

dynamic_batching {
  preferred_batch_size: [ 1, 2, 4, 8 ]
  max_queue_delay_microseconds: 1000
}
'''
    config_path = onnx_dir / "config.pbtxt"
    config_path.write_text(config_content)
    print(f"✓ Triton config saved to: {config_path}")
    
    return str(onnx_path)


def verify_onnx_model(model_repository: Path = MODEL_REPOSITORY) -> bool:
    """
    Verify the ONNX model by comparing outputs with PyTorch.
    """
    import numpy as np
    import onnxruntime as ort
    
    onnx_path = model_repository / "bge_m3_onnx" / "1" / "model.onnx"
    tokenizer_dir = model_repository / "tokenizer"
    
    print(f"\nVerifying ONNX model: {onnx_path}")
    
    # Load PyTorch model
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir)
    pytorch_model = AutoModel.from_pretrained("BAAI/bge-m3")
    
    pytorch_weights = model_repository / "bge_m3" / "1" / "model.pt"
    if pytorch_weights.exists():
        pytorch_model.load_state_dict(torch.load(pytorch_weights))
    
    pytorch_model.eval()
    
    # Load ONNX model
    ort_session = ort.InferenceSession(str(onnx_path))
    
    # Test input
    test_text = "This is a test sentence for verification"
    inputs = tokenizer(
        test_text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512
    )
    
    # PyTorch inference
    with torch.no_grad():
        pytorch_outputs = pytorch_model(**inputs)
        pytorch_embeddings = pytorch_outputs.last_hidden_state.numpy()
    
    # ONNX inference
    ort_inputs = {
        "input_ids": inputs["input_ids"].numpy(),
        "attention_mask": inputs["attention_mask"].numpy()
    }
    
    onnx_outputs = ort_session.run(None, ort_inputs)
    onnx_embeddings = onnx_outputs[0]
    
    # Compare outputs
    max_diff = np.max(np.abs(pytorch_embeddings - onnx_embeddings))
    mean_diff = np.mean(np.abs(pytorch_embeddings - onnx_embeddings))
    
    print(f"  Max difference: {max_diff:.8f}")
    print(f"  Mean difference: {mean_diff:.8f}")
    
    tolerance = 1e-4
    if max_diff < tolerance:
        print(f"✓ Verification passed! (tolerance: {tolerance})")
        return True
    else:
        print(f"⚠️ Warning: max diff {max_diff} > tolerance {tolerance}")
        return False


if __name__ == "__main__":
    MAX_LENGTH = 8192
    OPSET_VERSION = 18
    
    print("=" * 60)
    print("PyTorch to ONNX Converter for Triton Inference Server")
    print("=" * 60)
    
    # Convert to ONNX
    onnx_path = convert_to_onnx(
        model_repository=MODEL_REPOSITORY,
        max_length=MAX_LENGTH,
        opset_version=OPSET_VERSION
    )
    
    # Verify the exported model
    verify_onnx_model(MODEL_REPOSITORY)
    
    print("\n" + "=" * 60)
    print("✅ PyTorch to ONNX conversion completed!")
    print(f"   ONNX model: {onnx_path}")
    print("=" * 60)
