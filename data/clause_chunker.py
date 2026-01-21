#!/usr/bin/env python3
"""
Single class OOP with LangChain, UUID for IDs
Output: JSONL with child_id, parent_text, child_text, parent_id, file_id, name_file
"""

import re
import json
import uuid
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class ChunkRecord:
    """Output record"""
    child_id: str
    parent_text: str
    child_text: str
    parent_id: str
    file_id: str
    name_file: str


class ClauseChunker:
    """
    Single class OOP để chunking văn bản pháp luật Việt Nam.
    Sử dụng UUID cho parent_id và child_id.
    """
    
    # Regex patterns
    DIEU_PATTERN = re.compile(r'^(Điều|ĐIỀU)\s+(\d+[a-z]?)[\.:\s]+(.*)$', re.MULTILINE)
    PHU_LUC_PATTERN = re.compile(r'^(Phụ lục|PHỤ LỤC)\s+(\d+|[IVXLCDM]+|[A-Z])[\.:\s]*(.*)$', re.MULTILINE)
    KHOAN_PATTERN = re.compile(r'^(\d+)[\.:\s]+(.*)$')
    DIEM_PATTERN = re.compile(r'^([a-zđ])\)\s*(.*)$')
    
    def __init__(
        self,
        input_dir: str = "content_clean",
        metadata_dir: str = "metadata",
        output_file: str = "chunks.jsonl",
        chunk_size: int = 800,
        max_parent_text_len: int = 2000
    ):
        self.input_dir = Path(input_dir)
        self.metadata_dir = Path(metadata_dir)
        self.output_file = Path(output_file)
        self.max_parent_text_len = max_parent_text_len
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", "; ", ", ", " "]
        )
        
        self.stats = {"total_files": 0, "chunks": 0, "errors": 0}
        self._metadata_cache: Dict[str, dict] = {}
    
    # === PUBLIC API ===
    
    def run(self) -> None:
        """Main entry point."""
        print(f"ClauseChunker v2 - UUID IDs")
        print(f"Input: {self.input_dir} | Output: {self.output_file}")
        print("-" * 50)
        
        txt_files = sorted(self.input_dir.glob("*.txt"))
        self.stats["total_files"] = len(txt_files)
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            for i, filepath in enumerate(txt_files):
                if (i + 1) % 100 == 0:
                    print(f"Processing {i + 1}/{len(txt_files)}...")
                
                try:
                    for record in self._process_file(filepath):
                        f.write(json.dumps(asdict(record), ensure_ascii=False) + '\n')
                        self.stats["chunks"] += 1
                except Exception as e:
                    print(f"Error {filepath.name}: {e}")
                    self.stats["errors"] += 1
        
        print(f"\nDone! Files: {self.stats['total_files']} | Chunks: {self.stats['chunks']} | Errors: {self.stats['errors']}")
    
    # === FILE PROCESSING ===
    
    def _process_file(self, filepath: Path) -> List[ChunkRecord]:
        file_id = filepath.stem
        content = filepath.read_text(encoding='utf-8')
        name_file = self._get_name_file(file_id)
        
        if self.DIEU_PATTERN.search(content):
            return self._parse_structured(file_id, content, name_file)
        return self._parse_unstructured(file_id, content, name_file)
    
    # === METADATA ===
    
    def _get_name_file(self, file_id: str) -> str:
        if file_id not in self._metadata_cache:
            path = self.metadata_dir / f"{file_id}.json"
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self._metadata_cache[file_id] = json.load(f)
                except:
                    self._metadata_cache[file_id] = {}
            else:
                self._metadata_cache[file_id] = {}
        
        return self._metadata_cache[file_id].get("data", {}).get("diagram", {}).get("ten", "")
    
    # === STRUCTURED PARSING ===
    
    def _parse_structured(self, file_id: str, content: str, name_file: str) -> List[ChunkRecord]:
        records = []
        
        # Parse Điều
        dieu_matches = list(self.DIEU_PATTERN.finditer(content))
        for idx, match in enumerate(dieu_matches):
            dieu_num = match.group(2)
            start = match.start()
            end = dieu_matches[idx + 1].start() if idx + 1 < len(dieu_matches) else len(content)
            dieu_content = content[start:end].strip()
            
            # Generate 1 UUID cho parent
            parent_id = str(uuid.uuid4())
            parent_text = self._truncate(dieu_content)
            
            # Extract children
            children = self._extract_children(dieu_content)
            
            if not children:
                # No children, whole content is child
                lines = dieu_content.split('\n')[1:]
                child_text = '\n'.join(lines).strip()
                if child_text:
                    records.append(ChunkRecord(
                        child_id=str(uuid.uuid4()),
                        parent_text=parent_text,
                        child_text=child_text,
                        parent_id=parent_id,
                        file_id=file_id,
                        name_file=name_file
                    ))
            else:
                for child_text in children:
                    records.append(ChunkRecord(
                        child_id=str(uuid.uuid4()),
                        parent_text=parent_text,
                        child_text=child_text,
                        parent_id=parent_id,  # Same parent_id for all children of this Điều
                        file_id=file_id,
                        name_file=name_file
                    ))
        
        # Parse Phụ lục
        records.extend(self._parse_phu_luc(file_id, content, name_file))
        
        return records
    
    def _extract_children(self, dieu_content: str) -> List[str]:
        """Extract leaf children (Điểm if exists, else Khoản)."""
        children = []
        lines = dieu_content.split('\n')[1:]  # Skip Điều header
        text = '\n'.join(lines)
        
        khoans = self._extract_khoans(text)
        if not khoans:
            return children
        
        for khoan_content in khoans:
            diems = self._extract_diems(khoan_content)
            if diems:
                children.extend(diems)
            else:
                children.append(khoan_content)
        
        return children
    
    def _extract_khoans(self, text: str) -> List[str]:
        """Extract Khoản content list."""
        khoans = []
        current = None
        lines_buf = []
        
        for line in text.split('\n'):
            stripped = line.strip()
            if not stripped:
                if lines_buf:
                    lines_buf.append("")
                continue
            
            if self.KHOAN_PATTERN.match(stripped):
                if current is not None:
                    khoans.append('\n'.join(lines_buf).strip())
                current = stripped
                lines_buf = [stripped]
            elif current is not None:
                lines_buf.append(stripped)
        
        if current is not None and lines_buf:
            khoans.append('\n'.join(lines_buf).strip())
        
        return khoans
    
    def _extract_diems(self, khoan_content: str) -> List[str]:
        """Extract Điểm content list."""
        diems = []
        current = None
        lines_buf = []
        
        for line in khoan_content.split('\n'):
            stripped = line.strip()
            if not stripped:
                if lines_buf:
                    lines_buf.append("")
                continue
            
            if self.DIEM_PATTERN.match(stripped):
                if current is not None:
                    diems.append('\n'.join(lines_buf).strip())
                current = stripped
                lines_buf = [stripped]
            elif current is not None:
                lines_buf.append(stripped)
        
        if current is not None and lines_buf:
            diems.append('\n'.join(lines_buf).strip())
        
        return diems
    
    def _parse_phu_luc(self, file_id: str, content: str, name_file: str) -> List[ChunkRecord]:
        records = []
        matches = list(self.PHU_LUC_PATTERN.finditer(content))
        
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
            phu_luc_content = content[start:end].strip()
            
            parent_id = str(uuid.uuid4())
            parent_text = self._truncate(phu_luc_content)
            
            text = '\n'.join(phu_luc_content.split('\n')[1:]).strip()
            if text:
                chunks = self.text_splitter.split_text(text)
                for chunk in chunks:
                    if chunk.strip():
                        records.append(ChunkRecord(
                            child_id=str(uuid.uuid4()),
                            parent_text=parent_text,
                            child_text=chunk.strip(),
                            parent_id=parent_id,
                            file_id=file_id,
                            name_file=name_file
                        ))
        
        return records
    
    # === UNSTRUCTURED PARSING ===
    
    def _parse_unstructured(self, file_id: str, content: str, name_file: str) -> List[ChunkRecord]:
        records = []
        parent_id = str(uuid.uuid4())
        parent_text = self._truncate(content)
        
        chunks = self.text_splitter.split_text(content)
        for chunk in chunks:
            if chunk.strip():
                records.append(ChunkRecord(
                    child_id=str(uuid.uuid4()),
                    parent_text=parent_text,
                    child_text=chunk.strip(),
                    parent_id=parent_id,
                    file_id=file_id,
                    name_file=name_file
                ))
        
        return records
    
    # === UTILS ===
    
    def _truncate(self, text: str) -> str:
        """Truncate parent_text to save space."""
        if len(text) <= self.max_parent_text_len:
            return text
        return text[:self.max_parent_text_len] + "..."


if __name__ == "__main__":
    ClauseChunker().run()
