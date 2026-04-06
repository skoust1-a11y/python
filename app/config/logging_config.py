import logging
import os
import sys


class LoggingConfig:
    """Centralized logging configuration for the Wellbeing Coach application."""

    def __init__(self):
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv(
            "LOG_FORMAT",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.log_file = os.getenv("LOG_FILE")
        self.log_max_size = int(os.getenv("LOG_MAX_SIZE_MB", "10")) * 1024 * 1024
        self.log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        self.enable_console = os.getenv("LOG_CONSOLE", "true").lower() == "true"
        self.enable_file = bool(self.log_file)

        # Create logs directory if file logging is enabled
        if self.enable_file:
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger instance for the given name."""
        logger = logging.getLogger(name)

        # Avoid duplicate handlers
        if logger.handlers:
            return logger

        logger.setLevel(getattr(logging, self.log_level, logging.INFO))

        formatter = logging.Formatter(self.log_format)

        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.log_level, logging.INFO))
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        if self.enable_file:
            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.log_max_size,
                backupCount=self.log_backup_count,
            )
            file_handler.setLevel(getattr(logging, self.log_level, logging.INFO))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def setup_root_logger(self) -> logging.Logger:
        """Setup the root logger for the application."""
        return self.get_logger("wellbeing_coach")


# Global logging configuration instance
logging_config = LoggingConfig()


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for the given module name."""
    return logging_config.get_logger(name)


# Initialize root logger
root_logger = logging_config.setup_root_logger()

# Module-level logger
logger = get_logger(__name__)
