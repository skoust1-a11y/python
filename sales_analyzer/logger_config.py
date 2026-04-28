import logging
from pathlib import Path

def setup_logger():
    logger = logging.getLogger(__name__)   
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:

        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

    
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(log_dir / 'Sales_Analyzer.log')

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%d-%m-%Y %H:%M:%S'
        )

        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger