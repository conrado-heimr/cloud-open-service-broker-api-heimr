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

Ambiente hospedado

dev
```
cd /mnt/dev/broker-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
prod 
````
cd /mnt/prod/broker-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Tornar start.sh Executável:

````
chmod +x /mnt/dev/broker-api/start.sh /mnt/prod/broker-api/start.sh
`````

3. Atualizar os Serviços Systemd
Ajuste o broker-api-dev.service e crie o broker-api-prod.service para usar o usuário ubuntu e os diretórios corretos.

Atualizar broker-api-dev.service:
bash

sudo nano /etc/systemd/system/broker-api-dev.service
Substitua por:
ini

[Unit]
Description=Serviço Uvicorn para API do Broker (Dev)
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/mnt/dev/broker-api
Environment="ENVIRONMENT=development"
ExecStart=/bin/bash /mnt/dev/broker-api/start.sh
Restart=always

[Install]
WantedBy=multi-user.target
Criar broker-api-prod.service:
bash

sudo nano /etc/systemd/system/broker-api-prod.service
Adicione:
ini

[Unit]
Description=Serviço Gunicorn para API do Broker (Prod)
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/mnt/prod/broker-api
Environment="ENVIRONMENT=production"
ExecStart=/bin/bash /mnt/prod/broker-api/start.sh
Restart=always

[Install]
WantedBy=multi-user.target

Ativar e Iniciar os Serviços:
bash

sudo systemctl daemon-reload
sudo systemctl enable broker-api-dev.service
sudo systemctl start broker-api-dev.service
sudo systemctl enable broker-api-prod.service
sudo systemctl start broker-api-prod.service
