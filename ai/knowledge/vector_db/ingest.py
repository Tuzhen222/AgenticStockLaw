"""
Ingestion Script for Vector Database
Reads chunks.jsonl, embeds child_text via Triton BGE-M3 ONNX, pushes to Qdrant.
"""

import json
from pathlib import Path
from typing import Iterator
import numpy as np

import tritonclient.grpc as grpcclient
from transformers import AutoTokenizer

from qdrant import QdrantVectorDB, QdrantConfig


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "chunks.jsonl"
TOKENIZER_DIR = PROJECT_ROOT / "triton_server" / "model_repository" / "tokenizer"

# BGE-M3 model ID for tokenizer (fallback if local not found)
BGE_M3_MODEL_ID = "BAAI/bge-m3"


# Triton configuration
TRITON_HOST = "localhost"
TRITON_GRPC_PORT = 8001
MODEL_NAME = "bge_m3_tensorrt"
MAX_SEQ_LENGTH = 512
BATCH_SIZE = 8


def load_tokenizer() -> AutoTokenizer:
    """Load HuggingFace tokenizer from local or HuggingFace Hub."""
    # Try local first, fallback to HuggingFace
    if TOKENIZER_DIR.exists() and (TOKENIZER_DIR / "tokenizer_config.json").exists():
        print(f"Loading tokenizer from: {TOKENIZER_DIR}")
        return AutoTokenizer.from_pretrained(str(TOKENIZER_DIR))
    else:
        print(f"Local tokenizer not found, loading from HuggingFace: {BGE_M3_MODEL_ID}")
        return AutoTokenizer.from_pretrained(BGE_M3_MODEL_ID)


def read_jsonl(file_path: Path) -> Iterator[dict]:
    """Read JSONL file line by line.
    
    Yields:
        Dictionary for each line.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def count_lines(file_path: Path) -> int:
    """Count total lines in file."""
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for _ in f:
            count += 1
    return count


class TritonEmbedder:
    """Triton client for BGE-M3 ONNX embeddings."""
    
    def __init__(
        self,
        host: str = TRITON_HOST,
        port: int = TRITON_GRPC_PORT,
        model_name: str = MODEL_NAME,
    ):
        """Initialize Triton gRPC client.
        
        Args:
            host: Triton server hostname.
            port: Triton gRPC port.
            model_name: Name of the model in Triton.
        """
        self.model_name = model_name
        self.client = grpcclient.InferenceServerClient(
            url=f"{host}:{port}",
        )
        
        if not self.client.is_server_ready():
            raise ConnectionError(f"Triton server at {host}:{port} is not ready")
        
        if not self.client.is_model_ready(model_name):
            raise ConnectionError(f"Model '{model_name}' is not ready")
        
        print(f"✓ Connected to Triton server at {host}:{port}")
        print(f"✓ Model '{model_name}' is ready")
    
    def embed_batch(
        self,
        input_ids: np.ndarray,
        attention_mask: np.ndarray,
    ) -> np.ndarray:
        """Get embeddings from Triton server.
        
        Args:
            input_ids: Tokenized input IDs [batch_size, seq_len].
            attention_mask: Attention mask [batch_size, seq_len].
            
        Returns:
            Embeddings array [batch_size, 1024].
        """
        # Prepare inputs
        input_ids_tensor = grpcclient.InferInput(
            "input_ids", input_ids.shape, "INT64"
        )
        input_ids_tensor.set_data_from_numpy(input_ids.astype(np.int64))
        
        attention_mask_tensor = grpcclient.InferInput(
            "attention_mask", attention_mask.shape, "INT64"
        )
        attention_mask_tensor.set_data_from_numpy(attention_mask.astype(np.int64))
        
        # Request output
        outputs = [
            grpcclient.InferRequestedOutput("last_hidden_state"),
        ]
        
        # Inference
        response = self.client.infer(
            model_name=self.model_name,
            inputs=[input_ids_tensor, attention_mask_tensor],
            outputs=outputs,
        )
        
        # Get last_hidden_state [batch_size, seq_len, 1024]
        last_hidden_state = response.as_numpy("last_hidden_state")
        
        # Mean pooling with attention mask
        # Expand attention mask to match hidden state dimensions
        mask = attention_mask[:, :, np.newaxis].astype(np.float32)
        
        # Mask hidden states and compute mean
        masked_hidden = last_hidden_state * mask
        sum_hidden = masked_hidden.sum(axis=1)  # [batch_size, 1024]
        sum_mask = mask.sum(axis=1)  # [batch_size, 1]
        
        embeddings = sum_hidden / np.maximum(sum_mask, 1e-9)  # Avoid division by zero
        
        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.maximum(norms, 1e-9)
        
        return embeddings


def batch_records(records: Iterator[dict], batch_size: int) -> Iterator[list[dict]]:
    """Batch records into lists.
    
    Args:
        records: Iterator of records.
        batch_size: Size of each batch.
        
    Yields:
        Lists of records.
    """
    batch = []
    for record in records:
        batch.append(record)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def ingest(
    data_file: Path = DATA_FILE,
    batch_size: int = BATCH_SIZE,
    max_seq_length: int = MAX_SEQ_LENGTH,
    qdrant_config: QdrantConfig = None,
    recreate_collection: bool = False,
):
    """Run the ingestion pipeline.
    
    Args:
        data_file: Path to chunks.jsonl file.
        batch_size: Batch size for processing.
        max_seq_length: Maximum sequence length for tokenization.
        qdrant_config: Qdrant configuration.
        recreate_collection: Whether to delete and recreate collection.
    """
    print("=" * 60)
    print("Vector DB Ingestion Pipeline")
    print("=" * 60)
    
    # Count total records
    print(f"\nCounting records in: {data_file}")
    total_records = count_lines(data_file)
    print(f"Total records: {total_records:,}")
    
    # Initialize components
    print("\n--- Initializing ---")
    tokenizer = load_tokenizer()
    embedder = TritonEmbedder()
    db = QdrantVectorDB(qdrant_config or QdrantConfig())
    
    # Setup collection
    if recreate_collection:
        db.delete_collection()
    db.create_collection_if_not_exists()
    
    # Process batches
    print(f"\n--- Processing (batch_size={batch_size}) ---")
    processed = 0
    
    for batch in batch_records(read_jsonl(data_file), batch_size):
        # Extract texts for embedding
        texts = [record["child_text"] for record in batch]
        
        # Tokenize
        tokens = tokenizer(
            texts,
            return_tensors="np",
            padding="max_length",
            truncation=True,
            max_length=max_seq_length,
        )
        
        # Embed via Triton
        embeddings = embedder.embed_batch(
            tokens["input_ids"],
            tokens["attention_mask"],
        )
        
        # Prepare data for Qdrant
        ids = [record["child_id"] for record in batch]
        vectors = embeddings.tolist()
        payloads = [
            {
                "child_id": record["child_id"],
                "child_text": record["child_text"],
                "parent_text": record["parent_text"],
                "parent_id": record["parent_id"],
                "file_id": record["file_id"],
                "name_file": record["name_file"],
            }
            for record in batch
        ]
        
        # Upsert to Qdrant
        db.upsert_batch(ids, vectors, payloads)
        
        processed += len(batch)
        
        # Progress report
        if processed % 1000 == 0 or processed == total_records:
            pct = (processed / total_records) * 100
            print(f"  Processed: {processed:,} / {total_records:,} ({pct:.1f}%)")
    
    # Summary
    print("\n--- Complete ---")
    info = db.get_collection_info()
    print(f"Collection: {info['name']}")
    print(f"Total points: {info['points_count']:,}")
    print(f"Status: {info['status']}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest chunks to Qdrant")
    parser.add_argument(
        "--recreate", 
        action="store_true",
        help="Delete and recreate collection before ingesting"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size (default: {BATCH_SIZE})"
    )
    parser.add_argument(
        "--triton-host",
        type=str,
        default=TRITON_HOST,
        help=f"Triton server host (default: {TRITON_HOST})"
    )
    parser.add_argument(
        "--qdrant-host",
        type=str,
        default="localhost",
        help="Qdrant server host (default: localhost)"
    )
    
    args = parser.parse_args()
    
    qdrant_config = QdrantConfig(host=args.qdrant_host)
    
    ingest(
        batch_size=args.batch_size,
        qdrant_config=qdrant_config,
        recreate_collection=args.recreate,
    )
