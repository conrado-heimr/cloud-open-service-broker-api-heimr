# config/logger.py
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    logger = logging.getLogger("BrokerAPI")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        log_format = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
            #'%(asctime)s - %(levelname)s - %(message)s [method=%(method)s, endpoint=%(endpoint)s, status_code=%(status_code)s]'
        )
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)
        
        # Caminho para o arquivo de log:
        # 'your_project_root/broker_api.log'
        # Este arquivo (logger.py) está em 'your_project_root/config/logger.py'
        # Então, precisamos subir dois níveis para chegar na raiz do projeto.
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file_path = os.path.join(project_root, "broker_api.log")

        file_handler = RotatingFileHandler(
            filename=log_file_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=10
        )
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    
    return logger