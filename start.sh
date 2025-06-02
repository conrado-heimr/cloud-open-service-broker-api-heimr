#!/bin/bash

# Carregar variáveis de ambiente do arquivo .env
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Ativar ambiente virtual se existir
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Executar conforme o ambiente
if [ "$ENVIRONMENT" == "development" ]; then
  echo "Ambiente de desenvolvimento detectado. Iniciando com Uvicorn..."
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

elif [ "$ENVIRONMENT" == "production" ]; then
  echo "Ambiente de produção detectado. Iniciando com Gunicorn..."
  gunicorn main:app -k uvicorn.workers.UvicornWorker -c gunicorn.conf.py

else
  echo "ERRO: Variável ENVIRONMENT inválida ou não definida. Use 'development' ou 'production'."
  exit 1
fi
