from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi import Request
from pydantic import BaseModel
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from typing import Dict, Optional
from broker_sdk import OpenServiceBrokerV1
from dotenv import load_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler
 
# Configuração do logger
logger = logging.getLogger("BrokerAPI")
logger.setLevel(logging.INFO)
 
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
 
if not API_KEY:
    logger.error("API_KEY not found in environment variables")
    raise ValueError("IAM_APIKEY environment variable is required")
 
# Configuração do FastAPI
app = FastAPI(title="Open Service Broker API",debug=ENVIRONMENT == 'development')
 
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
 
    # Teste da API``
@app.get("/teste")
async def teste (request: ServiceRequest):
    """
    Verifica o teste da API.
    """
    #response = {"body": body}
    return request.headers.get("authorization")
 
# Teste da API``
@app.get("/status")
async def status():
    """
    Verifica o status da API.
    """
    logger.info("Received status check request", extra={"method": "GET", "endpoint": "/", "status_code": 200})
    response = {"status": "ok"}
    logger.info("Status check successful", extra={"method": "GET", "endpoint": "/", "status_code": 200})
    return response
 
# Listar catálogo de serviços
@app.get("/v2/catalog")
async def catalog():
    """
    Retorna o catálogo de serviços disponíveis.
    """
    logger.info("Fetching service catalog", extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 0})
    try:
        result = broker_service.list_catalog().get_result()
        logger.info(
            f"Catalog fetched successfully: {len(result.get('services', []))} services",
            extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 200}
        )
        return result
    except Exception as e:
        logger.error(
            f"Failed to fetch catalog: {str(e)}",
            extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 500}
        )
        raise HTTPException(status_code=500, detail=f"Erro ao buscar catálogo: {str(e)}")
 
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