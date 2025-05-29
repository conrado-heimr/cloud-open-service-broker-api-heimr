#!/bin/bash

# Ativar ambiente virtual se existir
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Rodar servidor FastAPI com Uvicorn
echo "Iniciando API..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
