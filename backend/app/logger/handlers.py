"""
Handlers module - Quản lý các handler cho logging.

Vai trò:
- Cấu hình các logging handlers (console, file, rotating file)
- Định nghĩa format cho output
- Xử lý việc ghi log ra các destination khác nhau
"""

import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class ConsoleHandler:
    """Handler for console/stdout output."""
    
    DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    def __init__(
        self,
        level: int = logging.INFO,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
    ):
        self.level = level
        self.fmt = fmt or self.DEFAULT_FORMAT
        self.datefmt = datefmt or self.DEFAULT_DATE_FORMAT
    
    def create(self) -> logging.StreamHandler:
        """Create and configure a StreamHandler for console output."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.level)
        handler.setFormatter(logging.Formatter(self.fmt, self.datefmt))
        return handler


class FileHandler:
    """Handler for rotating file output."""
    
    DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    DEFAULT_BACKUP_COUNT = 5
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        log_file: str = "app.log",
        level: int = logging.INFO,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        backup_count: int = DEFAULT_BACKUP_COUNT,
    ):
        self.log_dir = log_dir or self._default_log_dir()
        self.log_file = log_file
        self.level = level
        self.fmt = fmt or self.DEFAULT_FORMAT
        self.datefmt = datefmt or self.DEFAULT_DATE_FORMAT
        self.max_bytes = max_bytes
        self.backup_count = backup_count
    
    @staticmethod
    def _default_log_dir() -> Path:
        """Get default log directory (backend/logs)."""
        return Path(__file__).parent.parent.parent / "logs"
    
    def create(self) -> RotatingFileHandler:
        """Create and configure a RotatingFileHandler for file output."""
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        log_path = self.log_dir / self.log_file
        
        handler = RotatingFileHandler(
            log_path,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        handler.setLevel(self.level)
        handler.setFormatter(logging.Formatter(self.fmt, self.datefmt))
        return handler
