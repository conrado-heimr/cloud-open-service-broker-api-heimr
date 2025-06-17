import requests
import os
from dotenv import load_dotenv
load_dotenv()


IAM_API_KEY = os.getenv("IAM_APIKEY")
GC_OBJECT_ID = os.getenv("GC_OBJECT_ID") #Usar o id de cada produto
API_KEY = os.getenv("API_KEY")


print(f"IAM_API_KEY: {IAM_API_KEY}")
print(f"GC_OBJECT_ID: {GC_OBJECT_ID}")
print(f"API_KEY: {API_KEY}")


# 1. Obter IAM token
def get_iam_token(api_key):
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key,
    }
    res = requests.post(url, headers=headers, data=data)
    res.raise_for_status()
    return res.json()["access_token"]

# 2. Obter catálogo
def get_catalog(access_token, catalog_id):
    #url = f"https://globalcatalog.cloud.ibm.com/api/v1/deployments/{catalog_id}/broker"
    url = f"https://globalcatalog.cloud.ibm.com/api/v1/{catalog_id}?include=%2A&depth=100"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()

if __name__ == "__main__":
    token = get_iam_token(IAM_API_KEY)
    catalog_json = get_catalog(token, GC_OBJECT_ID)

    # Salva o catálogo em arquivo
    with open(f"catalog-{GC_OBJECT_ID}.json", "w") as f:
        import json
        json.dump(catalog_json, f, indent=2)

    print(f"✅ Catálogo salvo como catalog-{GC_OBJECT_ID}.json")
