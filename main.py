from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from typing import Dict, Optional, List
from broker_sdk import OpenServiceBrokerV1
from dotenv import load_dotenv
import os
import logging
import json
import requests

from logging.handlers import RotatingFileHandler
 
# Configuração do logger
logger = logging.getLogger("BrokerAPI")
logger.setLevel(logging.DEBUG) # Definido para DEBUG para logs mais detalhados

# Formato do log
log_format = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s [method=%(method)s, endpoint=%(endpoint)s, status_code=%(status_code)s]'
)
 
# Handler para console
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)
 
# Handler para arquivo com rotação (máx. 5MB, até 10 arquivos de backup)
file_handler = RotatingFileHandler(
    filename="broker_api.log",
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=10
)
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)
 
# Carregar variáveis de ambiente
load_dotenv()
API_KEY = os.getenv("IAM_APIKEY")
ENVIRONMENT = os.getenv("ENVIRONMENT")

# Variável para o ID do catálogo global (agora um único ID)
GC_OBJECT_ID = os.getenv("GC_OBJECT_ID")
 
if not API_KEY:
    logger.error("API_KEY not found in environment variables")
    raise ValueError("IAM_APIKEY environment variable is required")

# URLs da API IBM Cloud (Constantes usadas nas funções de catálogo)
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

# --- Funções para interagir com a API de Catálogo Global da IBM (reutilizadas do seu teste) ---
def get_iam_token(api_key: str) -> str:
    """
    Obtém um token IAM usando a chave de API fornecida.
    """
    url = IAM_TOKEN_URL
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key,
    }
    try:
        logger.info("Obtendo token IAM para o Catálogo Global...")
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("Token de acesso não encontrado na resposta IAM.")
        logger.info("Token IAM obtido com sucesso para o Catálogo Global.")
        return access_token
    except requests.exceptions.RequestException as e:
        status_code = response.status_code if 'response' in locals() else 'N/A'
        logger.error(f"Erro ao obter token IAM para Catálogo Global (Status {status_code}): {e}. Resposta: {response.text if 'response' in locals() else 'N/A'}")
        raise
    except ValueError as e:
        logger.error(f"Erro de processamento da resposta IAM para Catálogo Global: {e}")
        raise

def get_catalog_entry_from_ibm_global_catalog(access_token: str, catalog_id: str) -> dict:
    """
    Obtém a entrada do catálogo para o catalog_id fornecido usando o token de acesso.
    Utiliza a URL específica do seu script de teste (catalog.py).
    """
    url = f"https://globalcatalog.cloud.ibm.com/api/v1/{catalog_id}?include=%2A&depth=100"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    try:
        logger.info(f"Buscando entrada do catálogo global para o ID: {catalog_id} na URL: {url}...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        catalog_data = response.json()
        logger.info(f"Entrada do catálogo global obtida com sucesso para {catalog_id}.")
        logger.debug(f"Resposta bruta do Global Catalog para {catalog_id}: {json.dumps(catalog_data, indent=2)}")
        return catalog_data
    except requests.exceptions.RequestException as e:
        status_code = response.status_code if 'response' in locals() else 'N/A'
        logger.error(f"Erro ao obter entrada do catálogo global para {catalog_id} (Status {status_code}): {e}. URL: {url}. Resposta: {response.text if 'response' in locals() else 'N/A'}")
        raise HTTPException(status_code=status_code, detail=f"Erro ao buscar serviço {catalog_id}: {e}")
    except Exception as e:
        logger.error(f"Falha inesperada ao processar resposta do catálogo global para {catalog_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro inesperado ao processar serviço {catalog_id}: {e}")
# --- Fim das Funções de Catálogo ---


# Configuração do FastAPI
app = FastAPI(title="Open Service Broker API", debug=ENVIRONMENT == 'development')
 
# Middleware para validar o header X-Broker-Api-Version
@app.middleware("http")
async def validar_header_x_broker_api_version(request: Request, call_next):
    # rotas que não precisam do header
    rotas_liberadas = ["/status", "/docs", "/openapi.json"]

    if request.url.path in rotas_liberadas:
        return await call_next(request)

    if request.headers.get("X-Broker-Api-Version") != "2.12":
        logger.warning(
            "Header X-Broker-Api-Version ausente ou inválido",
            extra={"method": request.method, "endpoint": request.url.path, "status_code": 412}
        )
        return Response(
            content='Cabeçalho "X-Broker-Api-Version: 2.12" obrigatório.',
            status_code=412
        )

    return await call_next(request)
 
# Configuração do Open Service Broker
authenticator = IAMAuthenticator(API_KEY)
broker_service = OpenServiceBrokerV1(authenticator=authenticator)
 
# Modelo para solicitações de provisionamento e atualização
class ServiceRequest(BaseModel):
    service_id: str
    plan_id: str
    organization_guid: str
    space_guid: str
    parameters: Optional[Dict] = None
    accepts_incomplete: Optional[bool] = None

 
# Teste da API
@app.get("/status")
async def status():
    """
    Verifica o status da API.
    """
    logger.info("Received status check request", extra={"method": "GET", "endpoint": "/", "status_code": 200})
    response = {"status": "ok", "environment": ENVIRONMENT}
    logger.info("Status check successful", extra={"method": "GET", "endpoint": "/", "status_code": 200})
    return response
 
# Listar catálogo de serviços (INTEGRADO AQUI)
@app.get("/v2/catalog")
async def catalog():
    """
    Retorna o catálogo de serviços, buscando a definição do serviço no IBM Cloud Global Catalog
    para um único ID de serviço fornecido.
    """
    logger.info(
        "Attempting to retrieve catalog definition from IBM Cloud Global Catalog API for a single service ID",
        extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 0}
    )

    if not GC_OBJECT_ID:
        error_msg = "A variável de ambiente 'GC_OBJECT_ID' é necessária e deve conter o ID do serviço no Catálogo Global."
        logger.error(error_msg, extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 500})
        raise HTTPException(status_code=500, detail=error_msg)

    fetched_services = []
    try:
        # Obter token IAM uma única vez
        iam_token = get_iam_token(API_KEY)

        try:
            # Chamar a função para o único GC_OBJECT_ID
            global_catalog_entry = get_catalog_entry_from_ibm_global_catalog(iam_token, GC_OBJECT_ID)

            # --- Lógica de Mapeamento do Global Catalog para o formato OSB ---
            service_id = global_catalog_entry.get("id")
            service_name = global_catalog_entry.get("name")
            service_description = global_catalog_entry.get("overview_ui", {}).get("en", {}).get("description")
            service_long_description = global_catalog_entry.get("overview_ui", {}).get("en", {}).get("long_description", "")
            service_bindable = global_catalog_entry.get("metadata", {}).get("service", {}).get("bindable", False)
            service_tags = global_catalog_entry.get("tags", [])
            
            # Mapear planos: O OSB espera 'plans' como uma lista de objetos de plano
            osb_plans = []
            for child in global_catalog_entry.get("children", []):
                if child.get("kind") == "plan":
                    plan_id = child.get("id")
                    plan_name = child.get("name")
                    plan_description = child.get("overview_ui", {}).get("en", {}).get("description")
                    plan_bindable = child.get("metadata", {}).get("service", {}).get("bindable", False)
                    plan_free = True
                    if child.get("pricing_tags"):
                        plan_free = "paid" not in child.get("pricing_tags", []) and "paid_only" not in child.get("pricing_tags", [])

                    if plan_id and plan_name and plan_description:
                        osb_plans.append({
                            "id": plan_id,
                            "name": plan_name,
                            "description": plan_description,
                            "bindable": plan_bindable,
                            "free": plan_free,
                        })
                    else:
                        logger.warning(f"Plano inválido encontrado para serviço {service_id}: {json.dumps(child)} - Pulando este plano.")
            
            # Construir o objeto de serviço no formato OSB
            osb_service_data = {
                "id": service_id,
                "name": service_name,
                "description": service_description,
                "bindable": service_bindable,
                "tags": service_tags,
                "plans": osb_plans,
                "metadata": {
                    "longDescription": service_long_description,
                    "displayName": global_catalog_entry.get("overview_ui", {}).get("en", {}).get("display_name"),
                    "imageUrl": global_catalog_entry.get("images", {}).get("image"),
                },
                "plan_updateable": global_catalog_entry.get("metadata", {}).get("service", {}).get("plan_updateable", False),
                "instances_retrievable": True,
                "bindings_retrievable": True,
            }

            logger.debug(f"OSB service data for {GC_OBJECT_ID}: {json.dumps(osb_service_data, indent=2)}")

            # Validação final do objeto de serviço OSB antes de adicionar
            if (isinstance(osb_service_data, dict) and
                osb_service_data.get("id") and
                osb_service_data.get("name") and
                osb_service_data.get("description") and
                "bindable" in osb_service_data and
                osb_service_data.get("plans") and isinstance(osb_service_data["plans"], list) and osb_service_data["plans"]):
                fetched_services.append(osb_service_data)
                logger.info(f"Serviço '{service_name}' (ID: {GC_OBJECT_ID}) adicionado ao catálogo do broker com sucesso.")
            else:
                logger.warning(
                    f"O objeto de serviço OSB construído para o ID {GC_OBJECT_ID} não é válido ou está incompleto. Conteúdo: {json.dumps(osb_service_data, indent=2)}",
                    extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 200}
                )

        except HTTPException as e:
            logger.error(f"Falha ao buscar serviço {GC_OBJECT_ID} do Catálogo Global (HTTP Status: {e.status_code}): {e.detail}.",
                         extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": e.status_code})
            raise e 
        except Exception as e:
            logger.error(f"Falha inesperada ao processar o serviço {GC_OBJECT_ID}: {str(e)}.",
                         extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 500})
            raise HTTPException(status_code=500, detail=f"Erro inesperado ao processar o serviço {GC_OBJECT_ID}: {e}")


        if not fetched_services:
            error_msg = "O serviço com o ID fornecido não foi encontrado ou não é válido no IBM Cloud Global Catalog. Verifique o ID, permissões da API Key e o status de publicação do serviço, ou a lógica de mapeamento do JSON."
            logger.error(error_msg, extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 500})
            raise HTTPException(status_code=500, detail=error_msg)

        logger.info(
            f"Successfully fetched 1 service and formatted catalog for OSB /v2/catalog endpoint",
            extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 200}
        )
        return JSONResponse(content={"services": fetched_services})

    except Exception as e:
        logger.error(
            f"Erro crítico ao tentar buscar catálogo da IBM Cloud: {str(e)}",
            extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 500}
        )
        raise HTTPException(status_code=500, detail=f"Erro crítico ao buscar catálogo da IBM Cloud: {e}")

# Provisionar (criar ou substituir) uma instância de serviço
@app.put("/v2/service_instances/{instance_id}")
async def provision_service_instance(instance_id: str, body: ServiceRequest):
    """
    Cria ou substitui uma instância de serviço com base no instance_id.
    """
    logger.info(
        f"Provisioning instance {instance_id} with service_id={body.service_id}, plan_id={body.plan_id}",
        extra={"method": "PUT", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 0}
    )
    try:
        result = broker_service.replace_service_instance(
            instance_id=instance_id,
            service_id=body.service_id,
            plan_id=body.plan_id,
            organization_guid=body.organization_guid,
            space_guid=body.space_guid,
            parameters=body.parameters,
            accepts_incomplete=body.accepts_incomplete
        ).get_result()
        logger.info(
            f"Instance {instance_id} provisioned successfully",
            extra={"method": "PUT", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 200}
        )
        return result
    except Exception as e:
        logger.error(
            f"Failed to provision instance {instance_id}: {str(e)}",
            extra={"method": "PUT", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 400}
        )
        raise HTTPException(status_code=400, detail=str(e))
 
# Atualizar uma instância de serviço
@app.patch("/v2/service_instances/{instance_id}")
async def update_service_instance(instance_id: str, body: ServiceRequest):
    """
    Atualiza uma instância de serviço existente.
    """
    logger.info(
        f"Updating instance {instance_id} with service_id={body.service_id}, plan_id={body.plan_id}",
        extra={"method": "PATCH", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 0}
    )
    try:
        result = broker_service.update_service_instance(
            instance_id=instance_id,
            service_id=body.service_id,
            plan_id=body.plan_id,
            parameters=body.parameters,
            accepts_incomplete=body.accepts_incomplete
        ).get_result()
        logger.info(
            f"Instance {instance_id} updated successfully",
            extra={"method": "PATCH", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 200}
        )
        return result
    except Exception as e:
        logger.error(
            f"Failed to update instance {instance_id}: {str(e)}",
            extra={"method": "PATCH", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 400}
        )
        raise HTTPException(status_code=400, detail=str(e))
 
# Deprovisionar (deletar) uma instância de serviço
@app.delete("/v2/service_instances/{instance_id}")
async def deprovision_service_instance(instance_id: str, service_id: str, plan_id: str, accepts_incomplete: Optional[bool] = None):
    """
    Deleta uma instância de serviço com base no instance_id, service_id e plan_id.
    """
    logger.info(
        f"Deprovisioning instance {instance_id} with service_id={service_id}, plan_id={plan_id}",
        extra={"method": "DELETE", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 0}
    )
    try:
        result = broker_service.delete_service_instance(
            instance_id=instance_id,
            service_id=service_id,
            plan_id=plan_id,
            accepts_incomplete=accepts_incomplete
        ).get_result()
        logger.info(
            f"Instance {instance_id} deprovisioned successfully",
            extra={"method": "DELETE", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 200}
        )
        return result
    except Exception as e:
        logger.error(
            f"Failed to deprovision instance {instance_id}: {str(e)}",
            extra={"method": "DELETE", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 400}
        )
        raise HTTPException(status_code=400, detail=str(e))
