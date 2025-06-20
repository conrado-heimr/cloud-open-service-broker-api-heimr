# open_service_routes.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from typing import Dict, Optional, List
from sdk_ibm_services.broker_sdk import OpenServiceBrokerV1
import logging
import json
import requests

logger = logging.getLogger("BrokerAPI") # Usamos o logger configurado no main.py

# URLs da API IBM Cloud
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

# --- Funções para interagir com a API de Catálogo Global da IBM (mantidas) ---
# (As funções get_iam_token e get_catalog_entry_from_ibm_global_catalog permanecem as mesmas)
def get_iam_token(api_key: str) -> str:
    # ... (seu código get_iam_token aqui) ...
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
    # ... (seu código get_catalog_entry_from_ibm_global_catalog aqui) ...
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

# Modelo para solicitações de provisionamento e atualização
class ServiceRequest(BaseModel):
    service_id: str
    plan_id: str
    organization_guid: str
    space_guid: str
    parameters: Optional[Dict] = None
    accepts_incomplete: Optional[bool] = None

# ---- FUNÇÃO QUE RETORNA O APIRouter ----
def create_osb_router(api_key: str, gc_object_id: str):
    """
    Cria e retorna um APIRouter configurado para um GC_OBJECT_ID específico.
    """
    if not api_key:
        raise ValueError("API_KEY não fornecida ao criar o router OSB.")
    if not gc_object_id:
        raise ValueError("GC_OBJECT_ID não fornecido ao criar o router OSB.")

    authenticator = IAMAuthenticator(api_key)
    broker_service = OpenServiceBrokerV1(authenticator=authenticator)

    router = APIRouter()

    # Listar catálogo de serviços
    @router.get("/v2/catalog")
    async def catalog():
        logger.info(
            f"Attempting to retrieve catalog definition for GC_OBJECT_ID: {gc_object_id}",
            extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 0}
        )

        fetched_services = []
        try:
            iam_token = get_iam_token(api_key) # Usa a API_KEY passada para a função
            global_catalog_entry = get_catalog_entry_from_ibm_global_catalog(iam_token, gc_object_id) # Usa o GC_OBJECT_ID passado

            # Sua lógica de mapeamento para OSB Service (mantida igual)
            service_id = global_catalog_entry.get("id")
            service_name = global_catalog_entry.get("name")
            service_description = global_catalog_entry.get("overview_ui", {}).get("en", {}).get("description")
            service_long_description = global_catalog_entry.get("overview_ui", {}).get("en", {}).get("long_description", "")
            service_bindable = global_catalog_entry.get("metadata", {}).get("service", {}).get("bindable", False)
            service_tags = global_catalog_entry.get("tags", [])
            
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

            logger.debug(f"OSB service data for {gc_object_id}: {json.dumps(osb_service_data, indent=2)}")

            if (isinstance(osb_service_data, dict) and
                osb_service_data.get("id") and
                osb_service_data.get("name") and
                osb_service_data.get("description") and
                "bindable" in osb_service_data and
    osb_service_data.get("plans") and isinstance(osb_service_data["plans"], list) and osb_service_data["plans"]):
                fetched_services.append(osb_service_data)
                logger.info(f"Serviço '{service_name}' (ID: {gc_object_id}) adicionado ao catálogo do broker com sucesso.")
            else:
                logger.warning(
                    f"O objeto de serviço OSB construído para o ID {gc_object_id} não é válido ou está incompleto. Conteúdo: {json.dumps(osb_service_data, indent=2)}",
                    extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 200}
                )

            if not fetched_services:
                error_msg = "O serviço com o ID fornecido não foi encontrado ou não é válido no IBM Cloud Global Catalog. Verifique o ID, permissões da API Key e o status de publicação do serviço, ou a lógica de mapeamento do JSON."
                logger.error(error_msg, extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 500})
                raise HTTPException(status_code=500, detail=error_msg)

            logger.info(
                f"Successfully fetched 1 service and formatted catalog for OSB /v2/catalog endpoint",
                extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 200}
            )
            return JSONResponse(content={"services": fetched_services})

        except HTTPException as e:
            logger.error(f"Falha ao buscar serviço {gc_object_id} do Catálogo Global (HTTP Status: {e.status_code}): {e.detail}.",
                         extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": e.status_code})
            raise e
        except Exception as e:
            logger.error(f"Falha inesperada ao processar o serviço {gc_object_id}: {str(e)}.",
                         extra={"method": "GET", "endpoint": "/v2/catalog", "status_code": 500})
            raise HTTPException(status_code=500, detail=f"Erro inesperado ao processar o serviço {gc_object_id}: {e}")

    # Provisionar (criar ou substituir) uma instância de serviço
    @router.put("/v2/service_instances/{instance_id}")
    async def provision_service_instance(instance_id: str, body: ServiceRequest):
        logger.info(
            f"Provisioning instance {instance_id} for GC_OBJECT_ID: {gc_object_id}",
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
                f"Instance {instance_id} provisioned successfully for {gc_object_id}",
                extra={"method": "PUT", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 200}
            )
            return result
        except Exception as e:
            logger.error(
                f"Failed to provision instance {instance_id} for {gc_object_id}: {str(e)}",
                extra={"method": "PUT", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 400}
            )
            raise HTTPException(status_code=400, detail=str(e))

    # Atualizar uma instância de serviço
    @router.patch("/v2/service_instances/{instance_id}")
    async def update_service_instance(instance_id: str, body: ServiceRequest):
        logger.info(
            f"Updating instance {instance_id} for GC_OBJECT_ID: {gc_object_id}",
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
                f"Instance {instance_id} updated successfully for {gc_object_id}",
                extra={"method": "PATCH", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 200}
            )
            return result
        except Exception as e:
            logger.error(
                f"Failed to update instance {instance_id} for {gc_object_id}: {str(e)}",
                extra={"method": "PATCH", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 400}
            )
            raise HTTPException(status_code=400, detail=str(e))

    # Deprovisionar (deletar) uma instância de serviço
    @router.delete("/v2/service_instances/{instance_id}")
    async def deprovision_service_instance(instance_id: str, service_id: str, plan_id: str, accepts_incomplete: Optional[bool] = None):
        logger.info(
            f"Deprovisioning instance {instance_id} for GC_OBJECT_ID: {gc_object_id}",
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
                f"Instance {instance_id} deprovisioned successfully for {gc_object_id}",
                extra={"method": "DELETE", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 200}
            )
            return result
        except Exception as e:
            logger.error(
                f"Failed to deprovision instance {instance_id} for {gc_object_id}: {str(e)}",
                extra={"method": "DELETE", "endpoint": f"/v2/service_instances/{instance_id}", "status_code": 400}
            )
            raise HTTPException(status_code=400, detail=str(e))

    return router 