"""
Fetch BGE-M3 Model from HuggingFace
Downloads the BAAI/bge-m3 model and saves in Triton model repository format.
"""

import os
from pathlib import Path
from transformers import AutoTokenizer, AutoModel
import torch


# Triton model repository paths
MODEL_REPOSITORY = Path(__file__).parent / "model_repository"
PYTORCH_MODEL_DIR = MODEL_REPOSITORY / "bge_m3"
TOKENIZER_DIR = MODEL_REPOSITORY / "tokenizer"


def fetch_bge_model(
    model_name: str = "BAAI/bge-m3",
    model_repository: Path = MODEL_REPOSITORY
) -> tuple:
    """
    Download and save BGE-M3 model in Triton model repository format.
    
    Args:
        model_name: HuggingFace model identifier
        model_repository: Root directory for Triton model repository
        
    Returns:
        Tuple of (model, tokenizer)
    """
    pytorch_dir = model_repository / "bge_m3"
    tokenizer_dir = model_repository / "tokenizer"
    
    # Create Triton directory structure
    version_dir = pytorch_dir / "1"
    version_dir.mkdir(parents=True, exist_ok=True)
    tokenizer_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading model: {model_name}")
    
    # Download tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Download model
    model = AutoModel.from_pretrained(model_name)
    
    # Save as TorchScript for Triton PyTorch backend
    model.eval()
    model_path = version_dir / "model.pt"
    torch.save(model.state_dict(), model_path)
    print(f"✓ PyTorch model saved to: {model_path}")
    
    # Create Triton config.pbtxt
    # BGE-M3 has hidden_size=1024
    config_content = '''name: "bge_m3"
platform: "pytorch_libtorch"
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
    kind: KIND_GPU
  }
]

dynamic_batching {
  preferred_batch_size: [ 1, 2, 4, 8 ]
  max_queue_delay_microseconds: 100
}
'''
    config_path = pytorch_dir / "config.pbtxt"
    config_path.write_text(config_content)
    print(f"✓ Triton config saved to: {config_path}")
    
    return model, tokenizer


def load_bge_model(model_repository: Path = MODEL_REPOSITORY) -> tuple:
    """
    Load BGE-M3 model and tokenizer from Triton model repository.
    
    Args:
        model_repository: Root directory of Triton model repository
        
    Returns:
        Tuple of (model, tokenizer)
    """
    from transformers import AutoModel, AutoTokenizer
    
    tokenizer = AutoTokenizer.from_pretrained(model_repository / "tokenizer")
    model = AutoModel.from_pretrained("BAAI/bge-m3")
    model.load_state_dict(torch.load(model_repository / "bge_m3" / "1" / "model.pt"))
    
    return model, tokenizer


def test_model(model, tokenizer, text: str = "What is machine learning?"):
    """
    Test the model with a sample text.
    """
    model.eval()
    
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    
    with torch.no_grad():
        outputs = model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
    
    print(f"\n--- Test Results ---")
    print(f"Input text: {text}")
    print(f"Embedding shape: {embeddings.shape}")
    print(f"Embedding sample (first 5 values): {embeddings[0][:5].tolist()}")
    
    return embeddings


if __name__ == "__main__":
    MODEL_NAME = "BAAI/bge-m3"
    
    print("=" * 60)
    print("BGE-M3 Model Fetcher for Triton Inference Server")
    print("=" * 60)
    
    # Fetch and save model
    model, tokenizer = fetch_bge_model(MODEL_NAME)
    
    # Test the model
    test_model(model, tokenizer)
    
    print("\n" + "=" * 60)
    print("✅ BGE-M3 model fetched and saved in Triton format!")
    print(f"   Model repository: {MODEL_REPOSITORY}")
    print("=" * 60)
