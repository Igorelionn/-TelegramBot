#!/bin/bash

# Ativa o ambiente virtual se existir
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Instala as dependências se necessário
pip install -r requirements.txt

# Cria o diretório de vídeos se não existir
mkdir -p videos

# Define as variáveis de ambiente
export PYTHONUNBUFFERED=1
export TZ=America/Sao_Paulo

# Inicia o bot
python bot_telegram.py
