# config/settings.py
from dotenv import load_dotenv
import os
import logging
from typing import Optional

# Carrega as variáveis de ambiente do .env (deve ser a primeira coisa a rodar)
load_dotenv()

# Obtenha o logger. Ele será configurado em config/logger.py, mas já podemos usá-lo aqui.
logger = logging.getLogger("BrokerAPI") 

class Settings:
    """
    Classe para carregar e gerenciar todas as configurações da aplicação.
    """
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    IAM_APIKEY: str = os.getenv("IAM_API_KEY")

    ROOT_PATH = os.environ.get("ROOT_PATH", "")
    print(f"ROOT_PATH:{ROOT_PATH}")
    GC_OBJECT_ID_CLOUD: str = os.getenv("GC_OBJECT_ID_CLOUD")
    GC_OBJECT_ID_VMWARE: str = os.getenv("GC_OBJECT_ID_VMWARE")
    GC_OBJECT_ID_POWERVS: str = os.getenv("GC_OBJECT_ID_POWERVS")

    IMAGES_DIR = "images"
           
    def __init__(self):
        if not self.IAM_APIKEY:
            logger.error("ERRO: Variável de ambiente IAM_APIKEY não definida.")
            raise ValueError("A variável de ambiente 'IAM_APIKEY' é obrigatória para a autenticação IBM Cloud.")
        
# Instancia as configurações uma vez para toda a aplicação
settings = Settings()

# Para fins de depuração, você pode logar as configurações carregadas (sem a API Key)
logger.debug(f"Configurações carregadas: ENVIRONMENT={settings.ENVIRONMENT}, "
             f"GC_CLOUD={settings.GC_OBJECT_ID_CLOUD[:5]}..., "
             f"GC_VMWARE={settings.GC_OBJECT_ID_VMWARE[:5]}..., "
             f"GC_POWERVS={settings.GC_OBJECT_ID_POWERVS[:5]}...")