# -*- coding: utf-8 -*-
import requests
import schedule
import time
import random
import logging
import json
from datetime import datetime, timedelta
import pytz
from functools import lru_cache  # Importar lru_cache para otimização
import os
import sys
import socket
import atexit
import traceback

# Configuração do fuso horário e logger
FUSO_HORARIO_BRASILIA = pytz.timezone('America/Sao_Paulo')
obter_hora_brasilia = lambda: datetime.now(FUSO_HORARIO_BRASILIA)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot_telegram_logs.log"), logging.StreamHandler()]
)

# Arquivo de bloqueio para impedir múltiplas instâncias
LOCK_FILE = "bot_telegram.lock"
lock_socket = None

# Variável global para controlar se os sinais já foram agendados
sinais_agendados = False

def is_bot_already_running():
    """Verifica se outra instância do bot já está rodando"""
    try:
        # Método alternativo usando arquivo de lock, compatível com serviços de hospedagem
        if os.path.exists(LOCK_FILE):
            # Verifica se o PID no arquivo ainda está em execução
            with open(LOCK_FILE, 'r') as f:
                pid = f.read().strip()
                
            # Em ambientes Linux
            try:
                os.kill(int(pid), 0)
                logging.error(f"ERRO: Outra instância do bot já está rodando com PID {pid}!")
                return True
            except (OSError, ValueError):
                # Processo não existe mais, podemos prosseguir
                pass
        
        # Cria um novo arquivo de lock
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        # Registra uma função para liberar o lock ao sair
        def release_lock():
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
                logging.info("Lock liberado ao encerrar o bot.")
        
        atexit.register(release_lock)
        logging.info("Bot inicializado - não há outras instâncias rodando.")
        return False
    except Exception as e:
        logging.error(f"Erro ao verificar lock: {e}")
        # Em caso de erro, permitimos que o bot inicie
        return False

# Credenciais Telegram
TOKEN = '7997585882:AAFDyG-BYskj1gyAbh17X5jd6DDClXdluww'

# Configuração de canais e links específicos
CANAIS_CONFIG = {
    '-1002317995059': {
        'nome': 'Canal 1',
        'link_corretora': 'https://encurtador.com.br/8928H'
    },
    '-1002538423500': {
        'nome': 'Canal 2',
        'link_corretora': 'https://trade.xxbroker.com/register?aff=751924&aff_model=revenue&afftrack='
    },
    '-1002599454520': {
        'nome': 'Canal 3',
        'link_corretora': 'https://encurtador.com.br/EdRSx'
    },
    '-1002658649212': {
        'nome': 'Canal 4',
        'link_corretora': 'https://encurtador.com.br/uvuJ0'
    }
}

# Lista de canais para enviar os sinais
CHAT_IDS = list(CANAIS_CONFIG.keys())

# Estado global para evitar repetições
ultimo_ativo = None
ultimo_signal = None

# Definição de dias da semana para reutilização
DIAS_SEMANA = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Padrões de horários reutilizáveis
def criar_horario_24h():
    return {dia: [{"start": "00:00", "end": "23:59"}] for dia in DIAS_SEMANA}

def criar_horario_padrao(intervalos_por_dia):
    return {DIAS_SEMANA[i]: intervalos for i, intervalos in intervalos_por_dia.items()}

# Definição dos padrões de horários
HORARIOS_PADRAO = {
    "24h": criar_horario_24h(),
    
    "forex_padrao1": criar_horario_padrao({
        0: [{"start": "00:00", "end": "23:59"}],  # Segunda
        1: [{"start": "00:00", "end": "23:59"}],  # Terça
        2: [{"start": "00:00", "end": "01:00"}, {"start": "01:15", "end": "23:59"}],  # Quarta
        3: [{"start": "00:00", "end": "23:59"}],  # Quinta
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo
    }),
    
    "btc_padrao": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias
    
    "tech_stocks": criar_horario_padrao({
        0: [{"start": "00:00", "end": "15:30"}, {"start": "16:00", "end": "23:59"}],  # Segunda
        1: [{"start": "00:00", "end": "15:30"}, {"start": "16:00", "end": "23:59"}],  # Terça
        2: [{"start": "00:00", "end": "15:30"}, {"start": "16:00", "end": "23:59"}],  # Quarta
        3: [{"start": "00:00", "end": "15:30"}, {"start": "16:00", "end": "23:59"}],  # Quinta
        4: [{"start": "00:00", "end": "15:30"}, {"start": "16:00", "end": "23:59"}],  # Sexta
        5: [{"start": "00:00", "end": "15:30"}, {"start": "16:00", "end": "23:59"}],  # Sábado
        6: [{"start": "00:00", "end": "15:30"}, {"start": "16:00", "end": "23:59"}]   # Domingo
    }),
    
    "commodities": criar_horario_padrao({
        0: [{"start": "00:00", "end": "23:59"}],  # Segunda
        1: [{"start": "00:00", "end": "23:59"}],  # Terça
        2: [{"start": "00:00", "end": "23:59"}],  # Quarta
        3: [{"start": "00:00", "end": "06:00"}, {"start": "06:30", "end": "23:59"}],  # Quinta
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo
    }),
    
    "crypto_fechado_quartaquinta": criar_horario_padrao({
        0: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}],  # Segunda
        1: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "21:00"}],  # Terça
        2: [],  # Quarta (fechado)
        3: [],  # Quinta (fechado)
        4: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}],  # Sexta
        5: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}],  # Sábado
        6: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}]   # Domingo
    }),
    
    "usd_sgd": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "03:00"}, 
        {"start": "03:30", "end": "22:00"}, 
        {"start": "22:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias
    
    "usd_brl": criar_horario_padrao({
        0: [{"start": "00:00", "end": "23:59"}],  # Segunda
        1: [{"start": "00:00", "end": "00:45"}, {"start": "01:15", "end": "23:59"}],  # Terça
        2: [{"start": "00:00", "end": "23:59"}],  # Quarta
        3: [{"start": "00:00", "end": "23:59"}],  # Quinta
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo
    }),
    
    "eth_usd": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "18:45"}, 
        {"start": "19:15", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias
    
    "us_100_otc": criar_horario_padrao({
        0: [{"start": "00:00", "end": "11:30"}, {"start": "12:00", "end": "17:30"}, {"start": "18:00", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "11:30"}, {"start": "12:00", "end": "17:30"}, {"start": "18:00", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "11:30"}, {"start": "12:00", "end": "17:30"}, {"start": "18:00", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "11:30"}, {"start": "12:00", "end": "17:30"}, {"start": "18:00", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "11:30"}, {"start": "12:00", "end": "17:30"}, {"start": "18:00", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    # Novo padrão para GBP/USD Binary
    "gbp_usd_binary": criar_horario_padrao({
        0: [{"start": "00:00", "end": "01:00"}, {"start": "01:10", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    # Novo padrão para EUR/GBP Binary
    "eur_gbp_binary": criar_horario_padrao({
        0: [{"start": "00:00", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "01:00"}, {"start": "01:15", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    # Novo padrão para USD/CHF Binary
    "usd_chf_binary": criar_horario_padrao({
        0: [{"start": "00:00", "end": "01:00"}, {"start": "01:10", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    # Padrão específico para AUD/CAD (OTC)
    "aud_cad_otc": criar_horario_padrao({
        0: [{"start": "00:00", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "01:00"}, {"start": "01:15", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    # Padrão específico para MELANIA Coin (OTC)
    "melania_coin_otc": criar_horario_padrao({
        0: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "05:00"}, {"start": "05:30", "end": "12:00"}, {"start": "12:30", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    # Padrão específico para EUR/USD (OTC)
    "eur_usd_otc": criar_horario_padrao({
        0: [{"start": "00:00", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "01:00"}, {"start": "01:15", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    # Padrão específico para NOK/JPY (OTC)
    "nok_jpy_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "03:00"}, 
        {"start": "03:30", "end": "22:00"}, 
        {"start": "22:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias
    
    # Padrão específico para TRUMP Coin (OTC)
    "trump_coin_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias
    
    # Padrão específico para XAUUSD (OTC)
    "xauusd_otc": criar_horario_padrao({
        0: [{"start": "00:00", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "06:00"}, {"start": "06:10", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    # Padrão específico para EUR/JPY (OTC)
    "eur_jpy_otc": criar_horario_padrao({
        0: [{"start": "00:00", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "01:00"}, {"start": "01:15", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    "nzdchf_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "03:00"},
        {"start": "03:30", "end": "22:00"},
        {"start": "22:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias
    
    # Padrão específico para USD/MXN (OTC)
    "usd_mxn_otc": criar_horario_padrao({
        0: [{"start": "00:00", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "00:45"}, {"start": "01:15", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    # Padrão específico para GBP/JPY (OTC)
    "gbp_jpy_otc": criar_horario_padrao({
        0: [{"start": "00:00", "end": "01:00"}, {"start": "01:10", "end": "23:59"}],  # Segunda (24/03)
        1: [{"start": "00:00", "end": "23:59"}],  # Terça (25/03)
        2: [{"start": "00:00", "end": "23:59"}],  # Quarta (26/03)
        3: [{"start": "00:00", "end": "23:59"}],  # Quinta (27/03)
        4: [{"start": "00:00", "end": "23:59"}],  # Sexta (21/03)
        5: [{"start": "00:00", "end": "23:59"}],  # Sábado (22/03)
        6: [{"start": "00:00", "end": "23:59"}]   # Domingo (23/03)
    }),
    
    # Padrão específico para Chainlink (OTC)
    "chainlink_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:05"}, 
        {"start": "05:10", "end": "12:05"}, 
        {"start": "12:10", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias
    
    # Padrão específico para JP 225 (OTC)
    "jp_225_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "03:00"}, 
        {"start": "03:30", "end": "22:00"}, 
        {"start": "22:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para AUD/USD (OTC)
    "aud_usd_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "03:00"}, 
        {"start": "03:30", "end": "22:00"}, 
        {"start": "22:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para SP 35 (OTC)
    "sp_35_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para Dash (OTC)
    "dash_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para Litecoin (OTC)
    "litecoin_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "03:00"}, 
        {"start": "03:30", "end": "22:00"}, 
        {"start": "22:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para UK 100 (OTC)
    "uk_100_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para HK 33 (OTC)
    "hk_33_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "03:00"}, 
        {"start": "03:30", "end": "22:00"}, 
        {"start": "22:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para AUD/JPY (OTC)
    "aud_jpy_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para BTC/USD (OTC)
    "btc_usd_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para 1000Sats (OTC)
    "1000sats_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para Pepe (OTC)
    "pepe_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para Hamster Kombat (OTC)
    "hamster_kombat_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "03:00"}, 
        {"start": "03:30", "end": "22:00"}, 
        {"start": "22:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para Jupiter (OTC)
    "jupiter_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para IOTA (OTC)
    "iota_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para Decentraland (OTC)
    "decentraland_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)}),  # Mesmo padrão para todos os dias de 21/03 a 27/03
    
    # Padrão específico para McDonald's Corporation (OTC)
    "mcdonalds_otc": criar_horario_padrao({dia: [
        {"start": "00:00", "end": "05:00"}, 
        {"start": "05:30", "end": "12:00"}, 
        {"start": "12:30", "end": "23:59"}
    ] for dia in range(7)})  # Mesmo padrão para todos os dias de 21/03 a 27/03
}

# Categorias de ativos
ATIVOS_CATEGORIAS = {
    # Blitz 
    "USD/BRL(OTC)": "Blitz", "EUR/USD (OTC)": "Blitz",
    "AUD/CAD (OTC)": "Blitz", "EUR/GBP (OTC)": "Blitz", "PEN/USD (OTC)": "Blitz",
    "USD/ZAR (OTC)": "Blitz", "USD/COP (OTC)": "Blitz", "USD/SGD (OTC)": "Blitz",
    "USOUSD (OTC)": "Blitz",
    "BTC/USD(OTC)": "Blitz", "ETH/USD (OTC)": "Blitz", "MELANIA Coin (OTC)": "Blitz",
    "DOGECOIN (OTC)": "Blitz", "SOL/USD (OTC)": "Blitz",
    "1000Sats (OTC)": "Blitz", "Ondo (OTC)": "Blitz",
    "CARDANO (OTC)": "Blitz", "HBAR(OTC)": "Blitz", "BTC(OTC)": "Blitz",
    "ETH(OTC)": "Blitz", "BNB(OTC)": "Blitz", 
    "SOL(OTC)": "Blitz",
    "DOT(OTC)": "Blitz",
    "NEAR(OTC)": "Blitz",
    "ETC(OTC)": "Blitz", "BCH(OTC)": "Blitz",
    "GOOGLE (OTC)": "Blitz", "Amazon (OTC)": "Blitz", "Apple (OTC)": "Blitz",
    "Meta (OTC)": "Blitz", "Tesla (OTC)": "Blitz", "Nike, Inc. (OTC)": "Blitz",
    "Coca-Cola Company (OTC)": "Blitz", "McDonald's Corporation (OTC)": "Blitz",
    "Intel Corporation (OTC)": "Blitz", "Meta/Alphabet (OTC)": "Blitz",
    
    # Binary (Mantém os ativos já classificados como Binary)
    "GBP/USD (OTC)": "Binary",
    "EUR/GBP (OTC)": "Binary",
    "USD/CHF (OTC)": "Binary",
    "NOK/JPY (OTC)": "Binary",
    "TRUMP Coin (OTC)": "Binary",
    "XAUUSD (OTC)": "Binary",
    "DYDX (OTC)": "Binary",
    "EUR/JPY (OTC)": "Binary",
    "Fartcoin (OTC)": "Binary",
    "TAO(OTC)": "Binary",
    "Sui (OTC)": "Binary",
    "Raydium (OTC)": "Binary",
    "Onyxcoin (OTC)": "Binary",
    "JPY/THB (OTC)": "Binary",
    "Pudgy Penguins (OTC)": "Binary",
    "FET (OTC)": "Binary",
    "NZDCHF (OTC)": "Binary",
    "Render (OTC)": "Binary",
    "USD/MXN (OTC)": "Binary",
    "USD/THB (OTC)": "Binary",
    "EUR/THB (OTC)": "Binary",
    "GBP/JPY (OTC)": "Binary",
    "USD/JPY (OTC)": "Binary",
    "Nike, Inc. (OTC)": "Binary",
    "Beam (OTC)": "Binary",
    "AUS 200": "Binary",
    "EUR/CHF (OTC)": "Binary",
    "Ronin (OTC)": "Binary",
    "Dash (OTC)": "Binary",
    "USD/CAD (OTC)": "Binary",
    "GBP/NZD (OTC)": "Binary",
    "Cosmos (OTC)": "Binary",
    "US 100 (OTC)": "Binary",
    "GER 30 (OTC)": "Binary",
    "Sandbox (OTC)": "Binary",
    "USD/NOK (OTC)": "Binary",
    "Arbitrum (OTC)": "Binary",
    "Meta/Alphabet (OTC)": "Binary",
    "EUR/NZD (OTC)": "Binary",
    "NEAR (OTC)": "Binary",
    "FR 40 (OTC)": "Binary",
    "Polygon (OTC)": "Binary",
    "Sei (OTC)": "Binary",
    "US500/JP225 (OTC)": "Binary",
    "Morgan Stanley (OTC)": "Binary",
    "USD/ZAR (OTC)": "Binary",
    "Floki (OTC)": "Binary",
    "US 500 (OTC)": "Binary",
    "Chainlink (OTC)": "Binary",
    "USD/TRY (OTC)": "Binary",
    "USD/SEK (OTC)": "Binary",
    "US 2000 (OTC)": "Binary",
    "Gold/Silver (OTC)": "Binary",
    "US100/JP225 (OTC)": "Binary",
    "GBP/AUD (OTC)": "Binary",
    "Microsoft Corporation (OTC)": "Binary",
    "GRAPH (OTC)": "Binary",
    "JP 225 (OTC)": "Binary",
    "AUD/USD (OTC)": "Binary",
    "SP 35 (OTC)": "Binary",
    "UK 100 (OTC)": "Binary",
    "AUD/JPY (OTC)": "Binary",
    "HK 33 (OTC)": "Binary",
    "Pepe (OTC)": "Binary",
    "Hamster Kombat (OTC)": "Binary",
    "Jupiter (OTC)": "Binary",
    "IOTA (OTC)": "Binary",
    "Decentraland (OTC)": "Binary",
    "McDonald's Corporation (OTC)": "Binary",
    
    # Digital (Nova categoria)
    "Digital_Chainlink (OTC)": "Digital",
    "Digital_GRAPH (OTC)": "Digital",
    "Digital_US 500 (OTC)": "Digital",
    "Digital_Gold/Silver (OTC)": "Digital",
    "Digital_USD/TRY (OTC)": "Digital", 
    "Digital_USD/SEK (OTC)": "Digital",
    "Digital_GBP/AUD (OTC)": "Digital",
    "Digital_Microsoft Corporation (OTC)": "Digital",
    "Digital_AUS 200 (OTC)": "Digital"
}

# Mapeamento de ativos para padrões de horários
assets = {
    # Forex com padrão específico
    "USD/BRL(OTC)": HORARIOS_PADRAO["usd_brl"],
    "USD/SGD (OTC)": HORARIOS_PADRAO["usd_sgd"],
    
    # Forex com padrão comum
    "EUR/USD (OTC)": HORARIOS_PADRAO["eur_usd_otc"],
    "AUD/CAD (OTC)": HORARIOS_PADRAO["aud_cad_otc"],
    "EUR/GBP (OTC)": HORARIOS_PADRAO["forex_padrao1"],
    
    # Commodities
    "USOUSD (OTC)": HORARIOS_PADRAO["commodities"],
    
    # Crypto com padrão BTC
    "BTC/USD(OTC)": HORARIOS_PADRAO["btc_usd_otc"],
    "MELANIA Coin (OTC)": HORARIOS_PADRAO["melania_coin_otc"],
    "Meta/Alphabet (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "1000Sats (OTC)": HORARIOS_PADRAO["1000sats_otc"],
    
    # Crypto com padrão específico ETH
    "ETH/USD (OTC)": HORARIOS_PADRAO["eth_usd"],
    
    # Crypto fechado quarta e quinta
    "HBAR(OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Ondo (OTC)": HORARIOS_PADRAO["btc_padrao"],
    
    # Stocks com padrão tech
    "GOOGLE (OTC)": HORARIOS_PADRAO["tech_stocks"],
    "Amazon (OTC)": HORARIOS_PADRAO["tech_stocks"],
    "Apple (OTC)": HORARIOS_PADRAO["tech_stocks"],
    "Meta (OTC)": HORARIOS_PADRAO["tech_stocks"],
    "Tesla (OTC)": HORARIOS_PADRAO["tech_stocks"],
    "Nike, Inc. (OTC)": HORARIOS_PADRAO["btc_padrao"],
    
    # Ativos Binary serão adicionados aqui
    "GBP/USD (OTC)": HORARIOS_PADRAO["gbp_usd_binary"],
    "EUR/GBP (OTC)": HORARIOS_PADRAO["eur_gbp_binary"],
    "USD/CHF (OTC)": HORARIOS_PADRAO["usd_chf_binary"],
    "NOK/JPY (OTC)": HORARIOS_PADRAO["nok_jpy_otc"],
    "TRUMP Coin (OTC)": HORARIOS_PADRAO["trump_coin_otc"],
    "XAUUSD (OTC)": HORARIOS_PADRAO["xauusd_otc"],
    "DYDX (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "EUR/JPY (OTC)": HORARIOS_PADRAO["eur_jpy_otc"],
    "Fartcoin (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "TAO(OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Sui (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Raydium (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Onyxcoin (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "JPY/THB (OTC)": HORARIOS_PADRAO["nok_jpy_otc"],
    "Pudgy Penguins (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "FET (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "NZDCHF (OTC)": HORARIOS_PADRAO["nzdchf_otc"],
    "Render (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "USD/MXN (OTC)": HORARIOS_PADRAO["usd_mxn_otc"],
    "USD/THB (OTC)": HORARIOS_PADRAO["nok_jpy_otc"],
    "EUR/THB (OTC)": HORARIOS_PADRAO["jp_225_otc"],
    "GBP/JPY (OTC)": HORARIOS_PADRAO["gbp_jpy_otc"],
    "USD/JPY (OTC)": HORARIOS_PADRAO["gbp_jpy_otc"],
    "Beam (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Ripple (OTC)": HORARIOS_PADRAO["nzdchf_otc"],
    "AUS 200": HORARIOS_PADRAO["nzdchf_otc"],
    "EUR/CHF (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Ronin (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Dash (OTC)": HORARIOS_PADRAO["dash_otc"],
    "USD/CAD (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "GBP/NZD (OTC)": HORARIOS_PADRAO["nzdchf_otc"],
    "Cosmos (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "US 100 (OTC)": HORARIOS_PADRAO["us_100_otc"],
    "GER 30 (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Sandbox (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "USD/NOK (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Arbitrum (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "EUR/NZD (OTC)": HORARIOS_PADRAO["nzdchf_otc"],
    "NEAR (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "FR 40 (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Polygon (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Sei (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "US500/JP225 (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Morgan Stanley (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "USD/ZAR (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Floki (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "US 500 (OTC)": HORARIOS_PADRAO["us_100_otc"],
    "Chainlink (OTC)": HORARIOS_PADRAO["chainlink_otc"],
    "USD/TRY (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "USD/SEK (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "US 2000 (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Gold/Silver (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "US100/JP225 (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "GBP/AUD (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Microsoft Corporation (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "GRAPH (OTC)": HORARIOS_PADRAO["chainlink_otc"],
    "JP 225 (OTC)": HORARIOS_PADRAO["jp_225_otc"],
    "AUD/USD (OTC)": HORARIOS_PADRAO["aud_usd_otc"],
    "SP 35 (OTC)": HORARIOS_PADRAO["sp_35_otc"],
    "Litecoin (OTC)": HORARIOS_PADRAO["litecoin_otc"],
    "UK 100 (OTC)": HORARIOS_PADRAO["uk_100_otc"],
    "AUD/JPY (OTC)": HORARIOS_PADRAO["aud_jpy_otc"],
    "HK 33 (OTC)": HORARIOS_PADRAO["hk_33_otc"],
    "Pepe (OTC)": HORARIOS_PADRAO["pepe_otc"],
    "Hamster Kombat (OTC)": HORARIOS_PADRAO["hamster_kombat_otc"],
    "Jupiter (OTC)": HORARIOS_PADRAO["jupiter_otc"],
    "IOTA (OTC)": HORARIOS_PADRAO["iota_otc"],
    "Decentraland (OTC)": HORARIOS_PADRAO["decentraland_otc"],
    "McDonald's Corporation (OTC)": HORARIOS_PADRAO["mcdonalds_otc"],
    
    # Ativos Digital
    "Digital_Chainlink (OTC)": HORARIOS_PADRAO["chainlink_otc"],
    "Digital_GRAPH (OTC)": HORARIOS_PADRAO["chainlink_otc"],
    "Digital_US 500 (OTC)": HORARIOS_PADRAO["us_100_otc"],
    "Digital_Gold/Silver (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Digital_USD/TRY (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Digital_USD/SEK (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Digital_GBP/AUD (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Digital_Microsoft Corporation (OTC)": HORARIOS_PADRAO["btc_padrao"],
    "Digital_AUS 200 (OTC)": HORARIOS_PADRAO["nzdchf_otc"],
    "BTC/USD(OTC)": HORARIOS_PADRAO["btc_usd_otc"]
}

# Lista de ativos para facilitar o acesso
ATIVOS_FORNECIDOS = list(ATIVOS_CATEGORIAS.keys())

# Cache para horários de negociação (melhora o desempenho)
@lru_cache(maxsize=128)
def parse_time_range(time_str):
    """Converte string de tempo para objeto datetime e armazena em cache para reutilização."""
    return datetime.strptime(time_str, "%H:%M")

# Função para verificar se o ativo está disponível no horário atual
def is_asset_available(asset, current_time=None, current_day=None):
    if current_time is None or current_day is None:
        agora = obter_hora_brasilia()
        current_time = agora.strftime("%H:%M")
        current_day = agora.strftime("%A")
    
    if asset not in assets:
        return True  # Se não tem configuração específica, está disponível
        
    if current_day not in assets[asset]:
        return False  # Se o dia não está configurado, não está disponível

    # Converte o tempo atual apenas uma vez
    current_time_obj = datetime.strptime(current_time, "%H:%M")
    
    # Verifica se o tempo atual está dentro de algum intervalo permitido
    for time_range in assets[asset][current_day]:
        start_time = parse_time_range(time_range["start"])
        end_time = parse_time_range(time_range["end"])
        if start_time <= current_time_obj <= end_time:
            return True
    
    return False

# Funções para gerar sinais e verificar disponibilidade
def verificar_disponibilidade():
    global ultimo_ativo, ultimo_signal
    agora = obter_hora_brasilia()
    current_time = agora.strftime("%H:%M")
    current_day = agora.strftime("%A")
    
    available_assets = [asset for asset in ATIVOS_FORNECIDOS if is_asset_available(asset, current_time, current_day)]
    
    # Reduzir a verbosidade dos logs
    logging.info(f"Ativos disponíveis para negociação no momento: {len(available_assets)}")
    if available_assets and len(available_assets) > 0:
        # Mostrar apenas os primeiros 10 ativos para logs mais rápidos
        logging.info(f"Amostra de ativos disponíveis: {', '.join(available_assets[:10])}")
        if len(available_assets) > 10:
            logging.info(f"... e mais {len(available_assets) - 10} ativos")
    else:
        logging.warning("Nenhum ativo disponível no momento.")
    
    return available_assets

# Função principal para enviar mensagens
def send_message():
    global ultimo_ativo, ultimo_signal, ultimo_envio_timestamp
    
    try:
        # Verificar se o último envio ocorreu há menos de 5 minutos
        agora = obter_hora_brasilia()
        if hasattr(send_message, 'ultimo_envio_timestamp'):
            tempo_desde_ultimo_envio = (agora - send_message.ultimo_envio_timestamp).total_seconds() / 60.0
            if tempo_desde_ultimo_envio < 5:
                logging.warning(f"Ignorando sinal - último envio ocorreu há apenas {tempo_desde_ultimo_envio:.1f} minutos")
                return

        # Restante do código original
        current_time = agora.strftime("%H:%M")
        current_day = agora.strftime("%A")

        # Filtrar ativos disponíveis
        available_assets = [asset for asset in ATIVOS_FORNECIDOS 
                          if asset != ultimo_ativo and is_asset_available(asset, current_time, current_day)]

        if not available_assets:
            available_assets = [asset for asset in ATIVOS_FORNECIDOS 
                             if is_asset_available(asset, current_time, current_day)]
            if not available_assets:
                logging.warning("Nenhum ativo disponível no horário atual.")
                return

        # Escolher um ativo e gerar o sinal
        asset = random.choice(available_assets)
        signal = 'sell' if ultimo_signal == 'buy' else 'buy' if ultimo_signal is not None else random.choice(['buy', 'sell'])
        action = "COMPRA" if signal == 'buy' else "VENDA"
        emoji = "🟢" if signal == 'buy' else "🛑"

        # Calcular horários
        entry_time = agora + timedelta(minutes=2)
        categoria = ATIVOS_CATEGORIAS.get(asset, "Não categorizado")
        
        nome_ativo_exibicao = asset.replace("Digital_", "") if asset.startswith("Digital_") else asset
        
        if "(OTC)" in nome_ativo_exibicao and not " (OTC)" in nome_ativo_exibicao:
            nome_ativo_exibicao = nome_ativo_exibicao.replace("(OTC)", " (OTC)")
        
        tempo_expiracao_minutos = 1
        
        if "NEAR (OTC)" in nome_ativo_exibicao or asset == "NEAR (OTC)":
            tempo_expiracao_minutos = 2
            expiracao_time = entry_time + timedelta(minutes=tempo_expiracao_minutos)
            expiracao_texto = f"⏳ Expiração: {tempo_expiracao_minutos} minutos ({expiracao_time.strftime('%H:%M')})"
        elif categoria == "Blitz":
            expiracao_segundos = random.choice([5, 10, 15, 30])
            tempo_expiracao_minutos = expiracao_segundos / 60
            expiracao_texto = f"⏳ Expiração: {expiracao_segundos} segundos"
        elif categoria == "Digital":
            tempo_expiracao_minutos = random.choice([1, 3, 5])
            expiracao_time = entry_time + timedelta(minutes=tempo_expiracao_minutos)
            if tempo_expiracao_minutos == 1:
                expiracao_texto = f"⏳ Expiração: 1 minuto ({expiracao_time.strftime('%H:%M')})"
            else:
                expiracao_texto = f"⏳ Expiração: {tempo_expiracao_minutos} minutos ({expiracao_time.strftime('%H:%M')})"
        elif categoria == "Binary":
            tempo_expiracao_minutos = 1
            expiracao_time = entry_time + timedelta(minutes=tempo_expiracao_minutos)
            expiracao_texto = f"⏳ Expiração: 1 minuto ({expiracao_time.strftime('%H:%M')})"
        else:
            tempo_expiracao_minutos = 5
            expiracao_texto = "⏳ Expiração: até 5 minutos"

        fim_operacao = entry_time + timedelta(minutes=tempo_expiracao_minutos)
        gale1_time = fim_operacao + timedelta(minutes=1)
        fim_gale1 = gale1_time + timedelta(minutes=tempo_expiracao_minutos)
        gale2_time = fim_gale1 + timedelta(minutes=1)

        # Enviar mensagem
        logging.info(f"Enviando sinal para o ativo {asset}: {action}")
        envio_sucesso = False
        
        # Enviar para todos os canais configurados
        for chat_id in CHAT_IDS:
            try:
                link_corretora = CANAIS_CONFIG[chat_id]['link_corretora']
                
                canal_message = (
                    f"⚠️TRADE RÁPIDO⚠️\n\n"
                    f"💵 Ativo: {nome_ativo_exibicao}\n"
                    f"🏷️ Categoria: {categoria}\n"
                    f"{emoji} {action}\n"
                    f"➡ Entrada: {entry_time.strftime('%H:%M')}\n"
                    f"{expiracao_texto}\n"
                    f"Reentrada 1 - {gale1_time.strftime('%H:%M')}\n"
                    f"Reentrada 2 - {gale2_time.strftime('%H:%M')}"
                )
                
                # Configura o teclado inline com o link da corretora
                teclado_inline = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "👉🏻 Abrir corretora",
                                "url": link_corretora
                            }
                        ]
                    ]
                }
                
                response = requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": canal_message,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                        "reply_markup": json.dumps(teclado_inline)
                    }
                )
                
                if response.status_code == 200:
                    logging.info(f"Sinal enviado com sucesso para o canal {chat_id}")
                    envio_sucesso = True
                else:
                    logging.error(f"Falha ao enviar mensagem para o canal {chat_id}. Erro: {response.status_code} - {response.text}")
            except Exception as e:
                logging.error(f"Erro ao enviar para o canal {chat_id}: {e}")
                continue
        
        if envio_sucesso:
            logging.info(f"Operação realizada com sucesso! Ativo: {asset}")
            proximo_sinal = agora + timedelta(minutes=6)
            logging.info(f"Esperando 6 minutos para o próximo sinal. Próximo sinal previsto para: {proximo_sinal.strftime('%H:%M:%S')}")
            
            # Registrar timestamp deste envio
            send_message.ultimo_envio_timestamp = agora
            
            # Atualizar valores para controle
            ultimo_ativo = asset
            ultimo_signal = signal
        else:
            logging.error(f"Falha ao enviar o sinal para todos os canais.")
    
    except Exception as e:
        logging.error(f"Erro durante o envio da mensagem: {e}")

# Inicializar o timestamp de último envio
send_message.ultimo_envio_timestamp = obter_hora_brasilia() - timedelta(minutes=10)  # Inicializar com um valor no passado

def schedule_messages():
    """
    Agenda o envio de sinais a cada 6 minutos durante 24 horas, com 2 segundos de delay.
    Horários: 00:00:02, 00:06:02, 00:12:02, ..., 23:54:02
    """
    # Limpa todos os agendamentos existentes para evitar duplicação
    schedule.clear()
    
    # Flag global para controlar se os sinais já foram agendados
    global sinais_agendados
    if sinais_agendados:
        logging.info("Sinais já agendados. Pulando reagendamento.")
        return
    
    # Definindo horários a cada 6 minutos ao longo do dia com 2 segundos de atraso
    for hora in range(24):  # 0 a 23 horas
        for minuto in range(0, 60, 6):  # 0, 6, 12, 18, 24, 30, 36, 42, 48, 54
            horario_formatado = f"{hora:02d}:{minuto:02d}:02"
            schedule.every().day.at(horario_formatado).do(send_message)
            logging.info(f"Sinal agendado para {horario_formatado}")
    
    # Lista todos os horários agendados para verificação
    horarios = [f"{hora:02d}:{minuto:02d}:02" 
                for hora in range(24) 
                for minuto in range(0, 60, 6)]
    
    logging.info(f"Total de {len(horarios)} sinais agendados para as 24 horas")
    logging.info("Horários agendados:")
    for i, horario in enumerate(horarios[:10], 1):
        logging.info(f"Sinal {i}: {horario}")
    logging.info("... e assim por diante a cada 6 minutos")
    
    sinais_agendados = True

# Função para manter o bot vivo em serviços de hospedagem gratuitos
def keep_alive():
    """Ajuda a manter o bot vivo em serviços de hospedagem que desligam por inatividade"""
    try:
        # Simula atividade periodicamente para evitar suspensão do serviço
        logging.info("Verificação de manutenção: Bot está ativo e funcionando")
    except Exception as e:
        logging.error(f"Erro na função keep_alive: {e}")

def keep_bot_running():
    """
    Mantém o bot em execução, verificando e reagendando sinais se necessário.
    Verifica a cada 10 minutos se o bot está funcionando adequadamente.
    """
    # Obter o horário atual em Brasília
    fuso_horario = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(fuso_horario)
    logging.info(f"Bot iniciado! Horário de Brasília atual: {agora.strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Verificar quais ativos estão disponíveis
    ativos = list(ATIVOS_CATEGORIAS.keys())
    logging.info(f"Ativos disponíveis para negociação no momento: {len(ativos)}")
    amostra = ativos[:10]
    logging.info(f"Amostra de ativos disponíveis: {', '.join(amostra)}")
    logging.info(f"... e mais {len(ativos) - 10} ativos")
    
    # Agendar sinais apenas se não tiverem sido agendados ainda
    if not sinais_agendados:
        schedule_messages()
    
    # Agendar a verificação de funcionamento do bot (keep_alive) a cada 10 minutos
    schedule.every(10).minutes.do(keep_alive)
    
    # Calcular tempo até o próximo sinal agendado
    agora = datetime.now(fuso_horario)
    minuto_atual = agora.minute
    proximo_minuto = ((minuto_atual // 6) + 1) * 6
    if proximo_minuto >= 60:
        proximo_minuto = 0
        proxima_hora = (agora.hour + 1) % 24
    else:
        proxima_hora = agora.hour
        
    # Definir o próximo horário exato (com ajuste de 2 segundos para evitar arredondamento no Telegram)
    proximo_horario = agora.replace(hour=proxima_hora, minute=proximo_minuto, second=2, microsecond=0)
    if proximo_horario <= agora:
        proximo_horario = proximo_horario + timedelta(minutes=6)
    
    # Calcular tempo de espera
    tempo_espera = (proximo_horario - agora).total_seconds()
    logging.info(f"Aguardando até o próximo horário para iniciar: {proximo_horario.strftime('%H:%M:%S')}")
    
    # Loop principal para manter o bot em execução
    while True:
        schedule.run_pending()
        time.sleep(1)

# --------------------------------------------------------------------------------
# INÍCIO DO CÓDIGO DO BOT 2 - NÃO MODIFICAR ESTA LINHA
# --------------------------------------------------------------------------------

# Configuração do logger específico para o Bot 2
BOT2_LOGGER = logging.getLogger('bot2')
BOT2_LOGGER.setLevel(logging.INFO)
bot2_formatter = logging.Formatter('%(asctime)s - BOT2 - %(levelname)s - %(message)s')

# Evitar duplicação de handlers
if not BOT2_LOGGER.handlers:
    bot2_file_handler = logging.FileHandler("bot_telegram_bot2_logs.log")
    bot2_file_handler.setFormatter(bot2_formatter)
    BOT2_LOGGER.addHandler(bot2_file_handler)
    
    bot2_console_handler = logging.StreamHandler()
    bot2_console_handler.setFormatter(bot2_formatter)
    BOT2_LOGGER.addHandler(bot2_console_handler)

# Credenciais Telegram do Bot 2
BOT2_TOKEN = '7997585882:AAFDyG-BYskj1gyAbh17X5jd6DDClXdluww'

# Configuração dos canais para cada idioma do Bot 2
BOT2_CANAIS_CONFIG = {
    "-1002424874613": {  # Canal para mensagens em português
        "idioma": "pt",
        "link_corretora": "https://trade.xxbroker.com/register?aff=436564&aff_model=revenue&afftrack="
    },
    "-1002453956387": {  # Canal para mensagens em inglês
        "idioma": "en",
        "link_corretora": "https://trade.xxbroker.com/register?aff=436564&aff_model=revenue&afftrack="
    },
    "-1002446547846": {  # Canal para mensagens em espanhol
        "idioma": "es",
        "link_corretora": "https://trade.xxbroker.com/register?aff=436564&aff_model=revenue&afftrack="
    }
}

# Lista de IDs dos canais para facilitar iteração
BOT2_CHAT_IDS = list(BOT2_CANAIS_CONFIG.keys())

def bot2_schedule_messages():
    """Agenda o envio de mensagens para o Bot 2."""
    try:
        # Verificar se já existe agendamento
        if hasattr(bot2_schedule_messages, 'scheduled'):
            BOT2_LOGGER.info("Agendamentos já existentes. Pulando...")
            return
            
        BOT2_LOGGER.info("Iniciando agendamento de mensagens para o Bot 2")
        
        # Agendar envio de sinais a cada hora
        for hora in range(24):
            # Primeiro sinal
            schedule.every().day.at(f"{hora:02d}:03:02").do(bot2_enviar_aviso_pre_sinais)
            schedule.every().day.at(f"{hora:02d}:13:02").do(bot2_send_message)
            schedule.every().day.at(f"{hora:02d}:20:02").do(bot2_enviar_mensagem_fim_operacao)
            
            # Segundo sinal
            schedule.every().day.at(f"{hora:02d}:27:02").do(bot2_enviar_aviso_pre_sinais)
            schedule.every().day.at(f"{hora:02d}:37:02").do(bot2_send_message)
            schedule.every().day.at(f"{hora:02d}:44:02").do(bot2_enviar_mensagem_fim_operacao)
            
            # Terceiro sinal
            schedule.every().day.at(f"{hora:02d}:43:02").do(bot2_enviar_aviso_pre_sinais)
            schedule.every().day.at(f"{hora:02d}:53:02").do(bot2_send_message)
            schedule.every().day.at(f"{hora:02d}:00:02").do(bot2_enviar_mensagem_fim_operacao)
        
        # Marcar como agendado
        bot2_schedule_messages.scheduled = True
        
        BOT2_LOGGER.info("Agendamento de mensagens do Bot 2 concluído com sucesso")
        BOT2_LOGGER.info("Horários configurados:")
        BOT2_LOGGER.info("1. Aviso pré-sinal: XX:03:02, XX:27:02, XX:43:02")
        BOT2_LOGGER.info("2. Sinal: XX:13:02, XX:37:02, XX:53:02")
        BOT2_LOGGER.info("3. Mensagem pós-sinal: XX:20:02, XX:44:02, XX:00:02")
        
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao agendar mensagens do Bot 2: {str(e)}")
        traceback.print_exc()

def bot2_send_message():
    """Envia mensagem de sinal para os canais do Bot 2"""
    try:
        BOT2_LOGGER.info("Enviando mensagem de sinal...")
        # Implementação da função de envio de mensagem
        for chat_id in BOT2_CHAT_IDS:
            try:
                config_canal = BOT2_CANAIS_CONFIG[chat_id]
                idioma = config_canal["idioma"]
                
                # Mensagem padrão em português
                mensagem = "⚠️ SINAL DE TRADING ⚠️\n\nPróximo sinal em breve!"
                
                url = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
                payload = {
                    'chat_id': chat_id,
                    'text': mensagem,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, data=payload)
                
                if response.status_code == 200:
                    BOT2_LOGGER.info(f"Mensagem enviada com sucesso para o canal {chat_id}")
                else:
                    BOT2_LOGGER.error(f"Erro ao enviar mensagem para o canal {chat_id}: {response.text}")
            except Exception as e:
                BOT2_LOGGER.error(f"Erro ao enviar mensagem para o canal {chat_id}: {str(e)}")
                continue
                
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar mensagem: {str(e)}")

def bot2_enviar_mensagem_fim_operacao():
    """Envia mensagem de fim de operação para os canais do Bot 2"""
    try:
        BOT2_LOGGER.info("Enviando mensagem de fim de operação...")
        for chat_id in BOT2_CHAT_IDS:
            try:
                config_canal = BOT2_CANAIS_CONFIG[chat_id]
                idioma = config_canal["idioma"]
                
                # Mensagem padrão em português
                mensagem = "✅ Operação finalizada!\n\nAguardem o próximo sinal."
                
                url = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
                payload = {
                    'chat_id': chat_id,
                    'text': mensagem,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, data=payload)
                
                if response.status_code == 200:
                    BOT2_LOGGER.info(f"Mensagem de fim de operação enviada com sucesso para o canal {chat_id}")
                else:
                    BOT2_LOGGER.error(f"Erro ao enviar mensagem de fim de operação para o canal {chat_id}: {response.text}")
            except Exception as e:
                BOT2_LOGGER.error(f"Erro ao enviar mensagem de fim de operação para o canal {chat_id}: {str(e)}")
                continue
                
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar mensagem de fim de operação: {str(e)}")

def bot2_enviar_aviso_pre_sinais():
    """Envia aviso pré-sinais com vídeo e mensagem"""
    try:
        # Define o diretório base dos vídeos (agora relativo ao script)
        videos_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
        BOT2_LOGGER.info(f"Diretório de vídeos: {videos_dir}")
        
        # Criar o diretório se não existir
        if not os.path.exists(videos_dir):
            os.makedirs(videos_dir)
            BOT2_LOGGER.info(f"Diretório de vídeos criado: {videos_dir}")
        
        BOT2_LOGGER.info(f"Diretório existe: {os.path.exists(videos_dir)}")
        
        BOT2_LOGGER.info(f"Diretório existe: {os.path.exists(videos_dir)}")
        
        # Dicionário com avisos por idioma
        avisos_por_idioma = {
            'pt': {
                'video': f"{videos_dir}\\cpu_pt.mp4",  # Vídeo em português
                'mensagem': '👉🏼Abram a corretora Pessoal\n\n⚠️FIQUEM ATENTOS⚠️\n\n🔥Cadastre-se na XXBROKER agora mesmo🔥\n\n<a href="https://trade.xxbroker.com/register?aff=436564&aff_model=revenue&afftrack=">➡️ CLICANDO AQUI</a>'
            },
            'en': {
                'video': f"{videos_dir}\\cpu_en.mp4",  # Vídeo em inglês
                'mensagem': '👉🏼Open the broker Everyone\n\n⚠️PAY ATTENTION⚠️\n\n🔥Register on XXBROKER right now🔥\n\n<a href="https://trade.xxbroker.com/register?aff=436564&aff_model=revenue&afftrack=">➡️ CLICK HERE</a>'
            },
            'es': {
                'video': f"{videos_dir}\\cpu_es.mp4",  # Vídeo em espanhol
                'mensagem': '👉🏼Abran el corredor Todos\n\n⚠️PRESTEN ATENCIÓN⚠️\n\n🔥Regístrese en XXBROKER ahora mismo🔥\n\n<a href="https://trade.xxbroker.com/register?aff=436564&aff_model=revenue&afftrack=">➡️ CLIC AQUÍ</a>'
            }
        }

        for chat_id in BOT2_CHAT_IDS:
            try:
                # Obtém a configuração do canal
                config_canal = BOT2_CANAIS_CONFIG[chat_id]
                idioma = config_canal["idioma"]
                aviso = avisos_por_idioma.get(idioma, avisos_por_idioma['pt'])

                # Envia o vídeo
                try:
                    # Verifica se o arquivo de vídeo existe
                    video_path = aviso['video']
                    BOT2_LOGGER.info(f"Tentando acessar vídeo: {video_path}")
                    BOT2_LOGGER.info(f"Arquivo existe: {os.path.exists(video_path)}")
                    
                    if not os.path.exists(video_path):
                        BOT2_LOGGER.error(f"Arquivo de vídeo não encontrado: {video_path}")
                        # Tenta enviar apenas a mensagem se o vídeo não existir
                        raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")

                    # Envia o vídeo
                    url = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendVideo"
                    
                    # Abre o arquivo de vídeo
                    with open(aviso['video'], 'rb') as video_file:
                        files = {
                            'video': video_file
                        }
                        data = {
                            'chat_id': chat_id,
                            'caption': aviso['mensagem'],
                            'parse_mode': 'HTML',
                            'supports_streaming': True,  # Habilita streaming do vídeo
                            'width': 480,  # Largura do vídeo
                            'height': 360,  # Altura do vídeo
                            'duration': 3  # Duração em segundos
                        }
                        response = requests.post(url, files=files, data=data)
                    
                    if response.status_code == 200:
                        BOT2_LOGGER.info(f"Vídeo e mensagem enviados com sucesso para o canal {chat_id}")
                    else:
                        BOT2_LOGGER.error(f"Erro ao enviar vídeo para o canal {chat_id}: {response.text}")
                        # Tenta enviar apenas a mensagem se o vídeo falhar
                        try:
                            url_msg = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
                            payload_msg = {
                                'chat_id': chat_id,
                                'text': aviso['mensagem'],
                                'parse_mode': 'HTML'
                            }
                            response_msg = requests.post(url_msg, data=payload_msg)
                            if response_msg.status_code == 200:
                                BOT2_LOGGER.info(f"Mensagem enviada com sucesso para o canal {chat_id}")
                            else:
                                BOT2_LOGGER.error(f"Erro ao enviar mensagem para o canal {chat_id}: {response_msg.text}")
                        except Exception as e:
                            BOT2_LOGGER.error(f"Erro ao enviar mensagem para o canal {chat_id}: {str(e)}")
                except Exception as e:
                    BOT2_LOGGER.error(f"Erro ao enviar vídeo para o canal {chat_id}: {str(e)}")

            except Exception as e:
                BOT2_LOGGER.error(f"Erro ao processar canal {chat_id}: {str(e)}")
                continue

    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar avisos pré-sinais: {str(e)}")

def bot2_testar_aviso_pre_sinais():
    """Função para testar o envio de avisos pré-sinais"""
    try:
        BOT2_LOGGER.info("Iniciando teste de avisos pré-sinais...")
        bot2_enviar_aviso_pre_sinais()
        BOT2_LOGGER.info("Teste de avisos pré-sinais concluído!")
    except Exception as e:
        BOT2_LOGGER.error(f"Erro durante o teste de avisos pré-sinais: {str(e)}")

def iniciar_ambos_bots():
    """
    Inicializa ambos os bots quando executado como script principal.
    """
    # Inicializar o Bot 1 (original)
    try:
        logging.info("Inicializando Bot 1...")
        # Verifica se já existe uma instância do bot rodando
        if is_bot_already_running():
            logging.error("O bot já está rodando em outra instância. Encerrando...")
            sys.exit(1)
        schedule_messages()      # Função original do bot 1
    except Exception as e:
        logging.error(f"Erro ao inicializar Bot 1: {str(e)}")
    
    # Inicializar o Bot 2
    try:
        BOT2_LOGGER.info("Inicializando Bot 2...")
        
        # Executar teste inicial
        BOT2_LOGGER.info("Executando teste inicial do Bot 2...")
        bot2_testar_aviso_pre_sinais()
        
        # Aguardar 5 segundos após o teste
        time.sleep(5)
        
        # Iniciar operação normal
        BOT2_LOGGER.info("Iniciando operação normal do Bot 2...")
        bot2_schedule_messages()
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao inicializar Bot 2: {str(e)}")
    
    logging.info("Ambos os bots estão em execução!")
    BOT2_LOGGER.info("Ambos os bots estão em execução!")
    
    # Loop principal para verificar os agendamentos
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logging.error(f"Erro no loop principal: {str(e)}")
            BOT2_LOGGER.error(f"Erro no loop principal: {str(e)}")
            time.sleep(5)  # Pausa maior em caso de erro

# Iniciar os bots quando o script for executado diretamente
if __name__ == "__main__":
    try:
        iniciar_ambos_bots()
    except KeyboardInterrupt:
        logging.info("Bot encerrado pelo usuário")
        BOT2_LOGGER.info("Bot encerrado pelo usuário")
    except Exception as e:
        logging.error(f"Erro fatal: {str(e)}")
        BOT2_LOGGER.error(f"Erro fatal: {str(e)}")
        traceback.print_exc()

