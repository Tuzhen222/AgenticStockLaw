"""
Upload documents to MinIO with proper names from metadata.

This script:
1. Reads metadata JSON files from data/metadata/
2. Extracts document name from data.diagram.ten
3. Creates an ASCII-safe filename using document ID
4. Uploads the corresponding content_clean file to MinIO
5. Stores metadata (original name) in MinIO object tags

Usage:
    python upload_documents.py

Environment:
    MINIO_HOST: MinIO hostname (default: localhost)
    MINIO_PORT: MinIO port (default: 9000)
"""
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

from minio import Minio
from minio.error import S3Error
from minio.commonconfig import Tags

# Configuration
MINIO_HOST = os.environ.get("MINIO_HOST", "localhost")
MINIO_PORT = int(os.environ.get("MINIO_PORT", "9000"))
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
DOCUMENTS_BUCKET = "documents"

# Paths (relative to project root)
# Script is in ai/utils/, project root is two levels up
PROJECT_ROOT = Path(__file__).parent.parent.parent
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"
CONTENT_DIR = PROJECT_ROOT / "data" / "content_clean"


def vietnamese_to_ascii(text: str) -> str:
    """Convert Vietnamese text to ASCII-safe equivalent."""
    # Vietnamese character mappings
    vietnamese_map = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'À': 'A', 'Á': 'A', 'Ả': 'A', 'Ã': 'A', 'Ạ': 'A',
        'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ẳ': 'A', 'Ẵ': 'A', 'Ặ': 'A',
        'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ậ': 'A',
        'Đ': 'D',
        'È': 'E', 'É': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ẹ': 'E',
        'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ể': 'E', 'Ễ': 'E', 'Ệ': 'E',
        'Ì': 'I', 'Í': 'I', 'Ỉ': 'I', 'Ĩ': 'I', 'Ị': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ọ': 'O',
        'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ộ': 'O',
        'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ở': 'O', 'Ỡ': 'O', 'Ợ': 'O',
        'Ù': 'U', 'Ú': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ụ': 'U',
        'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ử': 'U', 'Ữ': 'U', 'Ự': 'U',
        'Ỳ': 'Y', 'Ý': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y', 'Ỵ': 'Y',
    }
    
    result = []
    for char in text:
        if char in vietnamese_map:
            result.append(vietnamese_map[char])
        elif ord(char) < 128:  # ASCII character
            result.append(char)
        else:
            # Try to normalize other unicode characters
            normalized = unicodedata.normalize('NFKD', char)
            ascii_char = normalized.encode('ascii', 'ignore').decode('ascii')
            result.append(ascii_char if ascii_char else '')
    
    return ''.join(result)


def sanitize_filename(name: str) -> str:
    """
    Create a safe filename from a document name.
    Converts Vietnamese to ASCII and removes special characters.
    """
    # Convert Vietnamese to ASCII
    name = vietnamese_to_ascii(name)
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    # Remove characters that are problematic in filenames and S3/MinIO
    name = re.sub(r'[<>:"/\\|?*,;#%&{}$!\'`@+=\[\]()]', '', name)
    # Replace remaining spaces with underscores for cleaner filenames
    name = name.replace(' ', '_')
    # Limit length (keep sufficient for readability)
    if len(name) > 150:
        name = name[:150]
    # Strip whitespace and underscores from ends
    name = name.strip('_ ')
    return name


def get_document_name(metadata_path: Path) -> str | None:
    """Extract document name from metadata JSON file."""
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Navigate to data.diagram.ten
        if 'data' in data and 'diagram' in data['data'] and 'ten' in data['data']['diagram']:
            return data['data']['diagram']['ten']
        return None
    except Exception as e:
        print(f"Error reading {metadata_path}: {e}")
        return None


def upload_to_minio(client: Minio, file_path: Path, object_name: str) -> tuple[bool, str]:
    """Upload a file to MinIO bucket."""
    try:
        client.fput_object(
            DOCUMENTS_BUCKET,
            object_name,
            str(file_path),
            content_type="text/plain; charset=utf-8",
        )
        return True, ""
    except S3Error as e:
        return False, str(e)


def main():
    """Main function to upload all documents."""
    print(f"Connecting to MinIO at {MINIO_HOST}:{MINIO_PORT}...")
    
    # Initialize MinIO client
    client = Minio(
        f"{MINIO_HOST}:{MINIO_PORT}",
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )
    
    # Ensure bucket exists
    try:
        if not client.bucket_exists(DOCUMENTS_BUCKET):
            client.make_bucket(DOCUMENTS_BUCKET)
            print(f"Created bucket: {DOCUMENTS_BUCKET}")
        else:
            print(f"Bucket '{DOCUMENTS_BUCKET}' already exists")
    except S3Error as e:
        print(f"Error with bucket: {e}")
        sys.exit(1)
    
    # Check directories exist
    if not METADATA_DIR.exists():
        print(f"Metadata directory not found: {METADATA_DIR}")
        sys.exit(1)
    
    if not CONTENT_DIR.exists():
        print(f"Content directory not found: {CONTENT_DIR}")
        sys.exit(1)
    
    # Process each metadata file
    metadata_files = list(METADATA_DIR.glob("*.json"))
    print(f"Found {len(metadata_files)} metadata files")
    
    # Store mapping of filename to original name
    mapping = {}
    
    uploaded = 0
    skipped = 0
    errors = 0
    
    for metadata_path in metadata_files:
        # Get the ID (filename without extension)
        doc_id = metadata_path.stem
        
        # Find corresponding content file
        content_path = CONTENT_DIR / f"{doc_id}.txt"
        if not content_path.exists():
            print(f"  Content file not found for {doc_id}, skipping")
            skipped += 1
            continue
        
        # Get document name from metadata
        doc_name = get_document_name(metadata_path)
        if not doc_name:
            # Use ID as fallback
            doc_name = doc_id
        
        # Create safe filename (ASCII-safe)
        safe_name = sanitize_filename(doc_name)
        if not safe_name:  # If sanitization resulted in empty string
            safe_name = doc_id
        object_name = f"{safe_name}.txt"
        
        # Store mapping
        mapping[object_name] = {
            "id": doc_id,
            "original_name": doc_name,
        }
        
        # Check if already uploaded
        try:
            client.stat_object(DOCUMENTS_BUCKET, object_name)
            print(f"  Already exists: {object_name[:70]}...")
            skipped += 1
            continue
        except S3Error:
            pass  # Object doesn't exist, proceed with upload
        
        # Upload to MinIO
        print(f"  Uploading: {object_name[:70]}...")
        success, error_msg = upload_to_minio(client, content_path, object_name)
        if success:
            uploaded += 1
        else:
            print(f"    ERROR: {error_msg}")
            errors += 1
    
    # Save mapping file
    mapping_path = PROJECT_ROOT / "data" / "document_mapping.json"
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"\nSaved document mapping to: {mapping_path}")
    
    print(f"\nDone! Uploaded: {uploaded}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    main()
