"""
Convert ONNX Model to TensorRT Engine for GPU Inference
Converts BGE-M3 ONNX model to optimized TensorRT engine with dynamic batch size.

Requirements:
- NVIDIA GPU with CUDA
- TensorRT installed
- pycuda (optional, for testing)

Usage:
    python convert_onnx_to_tensorrt.py
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
import numpy as np

try:
    import tensorrt as trt
except ImportError:
    print("❌ TensorRT not found. Please install TensorRT.")
    print("   Install guide: https://developer.nvidia.com/tensorrt")
    sys.exit(1)


@dataclass
class DynamicBatchConfig:
    """
    Configuration for dynamic batch size optimization.
    Optimized for GTX 1660 Super (6GB VRAM).
    """
    min_batch_size: int = 1
    opt_batch_size: int = 4          # Reduced for 6GB GPU
    max_batch_size: int = 8          # Reduced for 6GB GPU
    min_sequence_length: int = 1
    opt_sequence_length: int = 256   # Optimal for embeddings
    max_sequence_length: int = 512   # Safe for 6GB GPU


def convert_onnx_to_tensorrt(
    onnx_path: str,
    trt_output_path: str,
    batch_config: DynamicBatchConfig = None,
    fp16_mode: bool = True,
    workspace_size_gb: float = 2.0   # Reduced for 6GB GPU (leaves room for model)
) -> str:
    """
    Convert ONNX model to TensorRT engine with dynamic batch size support.
    
    Args:
        onnx_path: Path to ONNX model
        trt_output_path: Output path for TensorRT engine (.plan)
        batch_config: Dynamic batch size configuration
        fp16_mode: Enable FP16 precision for faster inference
        workspace_size_gb: GPU memory workspace in GB
        
    Returns:
        Path to the TensorRT engine
    """
    if batch_config is None:
        batch_config = DynamicBatchConfig()
    
    onnx_path = Path(onnx_path)
    output_path = Path(trt_output_path)
    
    if not onnx_path.exists():
        raise FileNotFoundError(f"ONNX model not found: {onnx_path}")
    
    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("TensorRT Conversion (GPU)")
    print("=" * 60)
    print(f"Input ONNX: {onnx_path}")
    print(f"Output TRT: {trt_output_path}")
    print(f"\nDynamic Batch Configuration:")
    print(f"  Batch size: min={batch_config.min_batch_size}, "
          f"opt={batch_config.opt_batch_size}, max={batch_config.max_batch_size}")
    print(f"  Sequence length: min={batch_config.min_sequence_length}, "
          f"opt={batch_config.opt_sequence_length}, max={batch_config.max_sequence_length}")
    print(f"  FP16 mode: {fp16_mode}")
    print(f"  Workspace: {workspace_size_gb} GB")
    
    # Create TensorRT logger and builder
    TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(TRT_LOGGER)
    
    if builder is None:
        raise RuntimeError(
            "Failed to create TensorRT builder. "
            "CUDA may not be available on this machine."
        )
    
    # Create network with explicit batch
    network = builder.create_network(
        1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
    )
    parser = trt.OnnxParser(network, TRT_LOGGER)
    
    # Parse ONNX model
    # Use parse_from_file to handle external data files (model.onnx.data)
    print("\nParsing ONNX model...")
    print(f"  Note: Loading from file to support external data")
    
    success = parser.parse_from_file(str(onnx_path))
    if not success:
        print("\n❌ ONNX Parsing Errors:")
        for i in range(parser.num_errors):
            print(f"  Error {i}: {parser.get_error(i)}")
        raise RuntimeError("Failed to parse ONNX model")
    
    # Print network info
    print(f"\nNetwork Inputs ({network.num_inputs}):")
    for i in range(network.num_inputs):
        inp = network.get_input(i)
        print(f"  - {inp.name}: {inp.shape}")
    
    print(f"\nNetwork Outputs ({network.num_outputs}):")
    for i in range(network.num_outputs):
        out = network.get_output(i)
        print(f"  - {out.name}: {out.shape}")
    
    # Create builder config
    config = builder.create_builder_config()
    config.set_memory_pool_limit(
        trt.MemoryPoolType.WORKSPACE,
        int(workspace_size_gb * (1 << 30))
    )
    
    # Enable FP16 if supported
    if fp16_mode and builder.platform_has_fast_fp16:
        config.set_flag(trt.BuilderFlag.FP16)
        print("\n✓ FP16 mode enabled")
    elif fp16_mode:
        print("\n⚠ FP16 not supported on this GPU, using FP32")
    
    # Create optimization profile for dynamic shapes
    profile = builder.create_optimization_profile()
    
    print("\nDynamic shape profiles:")
    for i in range(network.num_inputs):
        input_tensor = network.get_input(i)
        input_name = input_tensor.name
        
        min_shape = (batch_config.min_batch_size, batch_config.min_sequence_length)
        opt_shape = (batch_config.opt_batch_size, batch_config.opt_sequence_length)
        max_shape = (batch_config.max_batch_size, batch_config.max_sequence_length)
        
        profile.set_shape(input_name, min_shape, opt_shape, max_shape)
        print(f"  {input_name}: min={min_shape}, opt={opt_shape}, max={max_shape}")
    
    config.add_optimization_profile(profile)
    
    # Build TensorRT engine
    print("\nBuilding TensorRT engine (this may take several minutes)...")
    serialized_engine = builder.build_serialized_network(network, config)
    
    if serialized_engine is None:
        raise RuntimeError("Failed to build TensorRT engine")
    
    # Save engine
    with open(output_path, "wb") as f:
        f.write(serialized_engine)
    
    engine_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ TensorRT engine saved: {output_path}")
    print(f"   Size: {engine_size_mb:.2f} MB")
    
    return str(output_path)


def generate_triton_config(
    model_name: str,
    output_dir: str,
    batch_config: DynamicBatchConfig = None
) -> str:
    """
    Generate Triton config.pbtxt for TensorRT model.
    
    Args:
        model_name: Name of the model
        output_dir: Model repository directory
        batch_config: Dynamic batch configuration
        
    Returns:
        Path to config file
    """
    if batch_config is None:
        batch_config = DynamicBatchConfig()
    
    output_dir = Path(output_dir) / model_name
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / "config.pbtxt"
    
    config_content = f'''name: "{model_name}"
platform: "tensorrt_plan"
max_batch_size: {batch_config.max_batch_size}

input [
  {{
    name: "input_ids"
    data_type: TYPE_INT64
    dims: [ -1 ]
  }},
  {{
    name: "attention_mask"
    data_type: TYPE_INT64
    dims: [ -1 ]
  }}
]

output [
  {{
    name: "last_hidden_state"
    data_type: TYPE_FP16
    dims: [ -1, 1024 ]
  }}
]

instance_group [
  {{
    count: 1
    kind: KIND_GPU
  }}
]

dynamic_batching {{
  preferred_batch_size: [ {batch_config.opt_batch_size}, {batch_config.max_batch_size} ]
  max_queue_delay_microseconds: 100
}}
'''
    
    with open(config_path, "w") as f:
        f.write(config_content)
    
    print(f"\n✅ Triton config saved: {config_path}")
    return str(config_path)


def main():
    """Convert BGE-M3 ONNX to TensorRT."""
    # Configuration
    MODEL_REPOSITORY = "./model_repository"
    MODEL_NAME_ONNX = "bge_m3_onnx"
    MODEL_NAME_TRT = "bge_m3_tensorrt"
    
    ONNX_PATH = f"{MODEL_REPOSITORY}/{MODEL_NAME_ONNX}/1/model.onnx"
    TRT_OUTPUT = f"{MODEL_REPOSITORY}/{MODEL_NAME_TRT}/1/model.plan"
    
    # Dynamic batch config - uses defaults optimized for 6GB GPU
    # Modify here if you have a larger GPU
    batch_config = DynamicBatchConfig()
    
    # Check ONNX exists
    if not Path(ONNX_PATH).exists():
        print(f"❌ ONNX model not found: {ONNX_PATH}")
        print("   Run convert_to_onnx.py first.")
        sys.exit(1)
    
    # Convert to TensorRT with FP16
    convert_onnx_to_tensorrt(
        onnx_path=ONNX_PATH,
        trt_output_path=TRT_OUTPUT,
        batch_config=batch_config,
        fp16_mode=True,
        workspace_size_gb=2.0  # 2GB for 6GB GPU
    )
    
    # Generate Triton config
    generate_triton_config(
        model_name=MODEL_NAME_TRT,
        output_dir=MODEL_REPOSITORY,
        batch_config=batch_config
    )
    
    print("\n" + "=" * 60)
    print("✅ Conversion complete!")
    print("=" * 60)
    print(f"\nTo use with Triton:")
    print(f"  GPU: {MODEL_REPOSITORY}/{MODEL_NAME_TRT}/")
    print(f"  CPU: {MODEL_REPOSITORY}/{MODEL_NAME_ONNX}/ (ONNX, no conversion needed)")


if __name__ == "__main__":
    main()