#!/usr/bin/env python3
"""
Script để đổi tên file trong folder content dựa trên metadata.
Mỗi file trong content sẽ được đổi tên theo trường "ten" trong metadata tương ứng.
"""

import os
import json
import re
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """
    Làm sạch tên file để đảm bảo hợp lệ trên các hệ điều hành.
    - Loại bỏ ký tự không hợp lệ
    - Giới hạn độ dài (tính theo bytes để tương thích Linux)
    """
    # Thay thế các ký tự không hợp lệ trong tên file
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', name)
    
    # Thay thế nhiều dấu cách liên tiếp bằng 1 dấu cách
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Loại bỏ dấu cách đầu/cuối
    sanitized = sanitized.strip()
    
    # Linux giới hạn 255 bytes cho filename
    # Tiếng Việt UTF-8 có thể chiếm 2-4 bytes mỗi ký tự
    # Giới hạn ở 80 ký tự để an toàn (khoảng 160-240 bytes)
    max_chars = 80
    if len(sanitized) > max_chars:
        sanitized = sanitized[:max_chars].rsplit(' ', 1)[0]  # Cắt ở từ cuối cùng
    
    # Đảm bảo không quá 240 bytes (để dành chỗ cho extension)
    while len(sanitized.encode('utf-8')) > 240:
        sanitized = sanitized[:-1]
    
    return sanitized


def get_title_from_metadata(metadata_path: Path) -> str | None:
    """
    Đọc file metadata và trích xuất trường "ten".
    """
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('data', {}).get('diagram', {}).get('ten')
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Lỗi đọc file {metadata_path}: {e}")
        return None


def rename_content_files():
    """
    Đổi tên tất cả file trong folder content dựa trên metadata.
    """
    # Xác định đường dẫn
    script_dir = Path(__file__).parent
    content_dir = script_dir / 'content'
    metadata_dir = script_dir / 'metadata'
    
    if not content_dir.exists():
        print(f"Folder content không tồn tại: {content_dir}")
        return
    
    if not metadata_dir.exists():
        print(f"Folder metadata không tồn tại: {metadata_dir}")
        return
    
    # Đếm số file đã xử lý
    success_count = 0
    error_count = 0
    skip_count = 0
    
    # Lấy tất cả file trong content
    content_files = list(content_dir.iterdir())
    total_files = len(content_files)
    
    print(f"Tìm thấy {total_files} file trong folder content")
    print("-" * 50)
    
    for content_file in content_files:
        if not content_file.is_file():
            continue
        
        # Lấy tên file không có extension (VD: 66b9c0b03ab9c4ae3d5fea5f)
        file_id = content_file.stem
        file_extension = content_file.suffix  # VD: .txt
        
        # Tìm file metadata tương ứng
        metadata_file = metadata_dir / f"{file_id}.json"
        
        if not metadata_file.exists():
            print(f"⚠️  Không tìm thấy metadata cho: {content_file.name}")
            error_count += 1
            continue
        
        # Lấy tiêu đề từ metadata
        title = get_title_from_metadata(metadata_file)
        
        if not title:
            print(f"⚠️  Không tìm thấy trường 'ten' trong: {metadata_file.name}")
            error_count += 1
            continue
        
        # Làm sạch tên file
        new_filename = sanitize_filename(title) + file_extension
        new_path = content_dir / new_filename
        
        # Kiểm tra xem file mới đã tồn tại chưa
        if new_path.exists() and new_path != content_file:
            # Thêm ID vào cuối tên để tránh trùng
            new_filename = f"{sanitize_filename(title)} ({file_id}){file_extension}"
            new_path = content_dir / new_filename
        
        # Nếu tên file đã đúng rồi thì bỏ qua
        if content_file.name == new_filename:
            skip_count += 1
            continue
        
        try:
            # Đổi tên file
            content_file.rename(new_path)
            success_count += 1
            print(f"✓ Đổi tên: {content_file.name} → {new_filename[:60]}...")
        except OSError as e:
            print(f"✗ Lỗi đổi tên {content_file.name}: {e}")
            error_count += 1
    
    # In kết quả
    print("-" * 50)
    print(f"Hoàn thành!")
    print(f"  ✓ Thành công: {success_count}")
    print(f"  ⚠️  Lỗi: {error_count}")
    print(f"  ⏭️  Bỏ qua (đã đúng tên): {skip_count}")


if __name__ == "__main__":
    rename_content_files()
