#!/bin/bash

# Define o diretório do projeto
cd /opt/render/project/src

# Cria o diretório de vídeos se não existir
mkdir -p videos

# Define as variáveis de ambiente
export PYTHONUNBUFFERED=1
export TZ=America/Sao_Paulo

# Inicia o bot
python bot_telegram.py
