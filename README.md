# Open Service Broker API (FastAPI + IBM SDK)

Este projeto implementa uma API REST compatível com a especificação Open Service Broker, utilizando o SDK oficial da IBM (`ibm-platform-services`) com FastAPI.

---

## 🔧 Requisitos

- Python 3.9 ou superior  
- Variável de ambiente `IAM_APIKEY` configurada com sua API Key da IBM Cloud.
- Variável de ambiente `ENVIRONMENT` configurada com padrao 'development'.

---

## 📦 Instalação

1. Clone o repositório ou descompacte o projeto.

2. Crie um ambiente virtual (venv) para isolar as dependências:

```bash
python -m venv venv
```

3. Ative o ambiente virtual:

- No **Windows (cmd)**:
```cmd
venv\Scripts\activate.bat
```

- No **Windows (PowerShell)**:
```powershell
venv\Scripts\Activate.ps1
```

- No **Linux/macOS**:
```bash
source venv/bin/activate
```

4. Instale as dependências dentro do ambiente ativado:

```bash
pip install -r requirements.txt
```


5. Inicie o servidor (com o ambiente virtual ativado):

```bash
bash start.sh
```

A API estará disponível em: [http://localhost:8000](http://localhost:8000)

---

## 🛠️ Endpoints disponíveis

| Método | Rota                                  | Descrição                         |
|--------|---------------------------------------|-----------------------------------|
| GET    | `/status`                             | Verifica o status da API.         |
| PUT    | `/v2/service_instances/{instance_id}` | Provisiona uma nova instância     |
| DELETE | `/v2/service_instances/{instance_id}` | Remove uma instância provisionada |

---

## 🧪 Teste rápido com curl

```bash
curl http://localhost:8000/status
```

---

## 🔐 IBM IAM API Key

Sua API key pode ser encontrada em:  
[https://cloud.ibm.com/iam/apikeys](https://cloud.ibm.com/iam/apikeys)

---

## 📄 Licença

MIT License

---

## ⚙️ Script `start.sh`

```bash
#!/bin/bash

# Ativar ambiente virtual se existir
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Rodar servidor FastAPI com Uvicorn
echo "Iniciando API..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---
