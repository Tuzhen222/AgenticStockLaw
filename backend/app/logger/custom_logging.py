

import logging
from pathlib import Path
from typing import Optional

from .handlers import ConsoleHandler, FileHandler


class AppLogger:
    """
    Application Logger class.
    
    Quản lý việc tạo và cấu hình logger với console và file handlers.
    
    Example:
        from app.logger import AppLogger
        
        # Tạo logger với cấu hình mặc định
        logger = AppLogger("my_module").get_logger()
        logger.info("Hello, world!")
        
        # Hoặc với cấu hình tùy chỉnh
        logger = AppLogger(
            name="api",
            level=logging.DEBUG,
            log_file="api.log"
        ).get_logger()
    """
    
    _loggers: dict[str, logging.Logger] = {}  # Cache các logger đã tạo
    
    def __init__(
        self,
        name: str = "app",
        level: int = logging.INFO,
        log_dir: Optional[Path] = None,
        log_file: Optional[str] = None,
        console_output: bool = True,
        file_output: bool = True,
    ):
        """
        Initialize AppLogger.
        
        Args:
            name: Tên logger (thường dùng __name__)
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Thư mục chứa file log
            log_file: Tên file log (mặc định: {name}.log)
            console_output: Bật/tắt output ra console
            file_output: Bật/tắt output ra file
        """
        self.name = name
        self.level = level
        self.log_dir = log_dir
        self.log_file = log_file or f"{name}.log"
        self.console_output = console_output
        self.file_output = file_output
    
    def get_logger(self) -> logging.Logger:
        """
        Get or create a configured logger.
        
        Returns:
            Configured logging.Logger instance
        """
        # Return cached logger if exists
        if self.name in self._loggers:
            return self._loggers[self.name]
        
        logger = logging.getLogger(self.name)
        
        # Avoid adding handlers multiple times
        if logger.handlers:
            return logger
        
        logger.setLevel(self.level)
        logger.propagate = False
        
        # Add console handler
        if self.console_output:
            console_handler = ConsoleHandler(level=self.level)
            logger.addHandler(console_handler.create())
        
        # Add file handler
        if self.file_output:
            file_handler = FileHandler(
                log_dir=self.log_dir,
                log_file=self.log_file,
                level=self.level,
            )
            logger.addHandler(file_handler.create())
        
        # Cache the logger
        self._loggers[self.name] = logger
        
        return logger


def get_logger(name: str = "app") -> logging.Logger:
    """
    Convenience function to get a logger.
    
    Args:
        name: Logger name (recommend using __name__)
    
    Returns:
        Configured logger instance
    """
    return AppLogger(name=name).get_logger()
