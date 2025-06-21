# main.py
from fastapi import FastAPI, Request, Response, HTTPException
import os

# Importe suas configurações da pasta 'config'
from config.settings import settings

# Importe a função de configuração do logger da pasta 'config'
from config.logger import setup_logging

# Importe a FUNÇÃO que cria o APIRouter da pasta 'app'
from routers.open_service_routes import create_osb_router

# A primeira coisa a fazer é configurar o logger
logger = setup_logging()

# Configuração do FastAPI
app = FastAPI(title="Open Service Broker API", debug=settings.ENVIRONMENT == 'development', root_path=settings.ROOT_PATH)

# Middleware para validar o header X-Broker-Api-Version
@app.middleware("http")
async def validar_header_x_broker_api_version(request: Request, call_next):
    # rotas que não precisam do header (status ou docs genéricos)
    rotas_liberadas = ["/", "/docs", "/openapi.json"]

    if any(request.url.path.startswith(f"/{service_type}/status") for service_type in ["cloud-professional-services", "vmware-professional-services", "powervs-professional-services", "textract"]) or \
       request.url.path in rotas_liberadas:
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

# Teste da API - Um endpoint genérico de status pode ser mantido aqui
@app.get("/")
async def root_status():
    """
    Verifica o status da API principal.
    """
    logger.info("Received root status check request", extra={"method": "GET", "endpoint": "/status", "status_code": 200})
    response = {"status": "ok", "environment": settings.ENVIRONMENT, "message": "Broker API Gateway is running"}
    logger.info("Root status check successful", extra={"method": "GET", "endpoint": "/status", "status_code": 200})
    return response

# --- Inclusão dos APIRouters para cada tipo de serviço ---

# Cloud Professional Services
app.include_router(
    create_osb_router(api_key=settings.IAM_APIKEY, gc_object_id=settings.GC_OBJECT_ID_CLOUD),
    prefix="/cloud-professional-services",
    tags=["Cloud Professional Services OSB"],
)

# VMware Professional Services
app.include_router(
    create_osb_router(api_key=settings.IAM_APIKEY, gc_object_id=settings.GC_OBJECT_ID_VMWARE),
    prefix="/vmware-professional-services",
    tags=["VMware Professional Services OSB"],
)

# PowerVS Professional Services
app.include_router(
    create_osb_router(api_key=settings.IAM_APIKEY, gc_object_id=settings.GC_OBJECT_ID_POWERVS),
    prefix="/powervs-professional-services",
    tags=["PowerVS Professional Services OSB"],
)