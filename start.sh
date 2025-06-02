#!/bin/bash

# Carregar variáveis de ambiente do arquivo .env
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
else
  echo "ERRO: Arquivo $ENV_FILE não encontrado."
  exit 1
fi

# Definir a porta com base no ENVIRONMENT
if [ "$ENVIRONMENT" == "development" ]; then
  PORT=8000
elif [ "$ENVIRONMENT" == "production" ]; then
  PORT=8001
else
  echo "ERRO: Variável ENVIRONMENT inválida ou não definida. Use 'development' ou 'production'."
  exit 1
fi

# Ativar ambiente virtual se existir
if [ -d "venv" ]; then
  source venv/bin/activate
else
  echo "ERRO: Diretório venv não encontrado."
  exit 1
fi

# Executar conforme o ambiente
if [ "$ENVIRONMENT" == "development" ]; then
  echo "Ambiente de desenvolvimento detectado. Iniciando com Uvicorn na porta $PORT..."
  uvicorn main:app --host 0.0.0.0 --port $PORT --reload
elif [ "$ENVIRONMENT" == "production" ]; then
  echo "Ambiente de produção detectado. Iniciando com Gunicorn na porta $PORT..."
  gunicorn main:app -k uvicorn.workers.UvicornWorker -c gunicorn.conf.py --bind 0.0.0.0:$PORT
fi