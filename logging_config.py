import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional
import colorlog

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_format:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_format = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

class Logger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    def debug(self, message: str, **kwargs) -> None:
        self.logger.debug(message, **kwargs)
    def info(self, message: str, **kwargs) -> None:
        self.logger.info(message, **kwargs)
    def warning(self, message: str, **kwargs) -> None:
        self.logger.warning(message, **kwargs)
    def error(self, message: str, **kwargs) -> None:
        self.logger.error(message, **kwargs)
    def critical(self, message: str, **kwargs) -> None:
        self.logger.critical(message, **kwargs)
    def exception(self, message: str, **kwargs) -> None:
        self.logger.exception(message, **kwargs)

def get_logger(name: str) -> Logger:
    return Logger(name)
