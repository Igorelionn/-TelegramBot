# -*- coding: utf-8 -*-
"""
Bot Telegram 2 para envio de sinais em canais em português.
Versão independente que não depende mais do Bot 1.
Os sinais serão enviados para os seguintes canais:
- Sala ChamaNaAlta: -1002658649212
- Sala do Np.bo: -1002538423500
- Minha sala: -1002317995059
O bot enviará 3 sinais por hora nos minutos 10, 30 e 50.
"""

# Importações necessárias
import traceback
import socket
import pytz
from datetime import datetime, timedelta, time as dt_time
import json
import random
import time
import schedule
import requests
import logging
import sys
import os
from functools import lru_cache

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

# Credenciais Telegram
BOT2_TOKEN = '7997585882:AAFDyG-BYskj1gyAbh17X5jd6DDClXdluww'

# Configuração dos canais em português
BOT2_CANAIS_CONFIG = {
    "-1002658649212": {  # Sala ChamaNaAlta
        "idioma": "pt",
        "link_corretora": "https://trade.xxbroker.com/register?aff=751626&aff_model=revenue&afftrack="
    },
    "-1002538423500": {  # Sala do Np.bo
        "idioma": "pt",
        "link_corretora": "https://trade.xxbroker.com/register?aff=751924&aff_model=revenue&afftrack="
    },
    "-1002317995059": {  # Minha sala
        "idioma": "pt",
        "link_corretora": "https://trade.xxbroker.com/register?aff=436564&aff_model=revenue&afftrack="
    }
}

# Lista de IDs dos canais para facilitar iteração
BOT2_CHAT_IDS = list(BOT2_CANAIS_CONFIG.keys())

# ID para compatibilidade com código existente
BOT2_CHAT_ID_CORRETO = BOT2_CHAT_IDS[0]  # Usar o primeiro canal como padrão

# Limite de sinais por hora
BOT2_LIMITE_SINAIS_POR_HORA = 3

# Categorias dos ativos
ATIVOS_CATEGORIAS = {
    # Ativos Blitz
    "USD/BRL (OTC)": "Blitz",
    "USOUSD (OTC)": "Blitz",
    "BTC/USD (OTC)": "Blitz",
    "Google (OTC)": "Blitz",
    "EUR/JPY (OTC)": "Blitz",
    "ETH/USD (OTC)": "Blitz",
    "MELANIA COIN (OTC)": "Blitz",
    "EUR/GBP (OTC)": "Blitz",
    "Apple (OTC)": "Blitz",
    "Amazon (OTC)": "Blitz",
    "TRUM Coin (OTC)": "Blitz",
    "Nike, Inc. (OTC)": "Blitz",
    "DOGECOIN (OTC)": "Blitz",
    "Tesla (OTC)": "Blitz",
    "SOL/USD (OTC)": "Blitz",
    "1000Sats (OTC)": "Blitz",
    "XAUUSD (OTC)": "Blitz",
    "McDonald´s Corporation (OTC)": "Blitz",
    "Meta (OTC)": "Blitz",
    "Coca-Cola Company (OTC)": "Blitz",
    "CARDANO (OTC)": "Blitz",
    "EUR/USD (OTC)": "Blitz",
    "PEN/USD (OTC)": "Blitz",
    "Bitcoin Cash (OTC)": "Blitz",
    "AUD/CAD (OTC)": "Blitz",
    "Tesla/Ford (OTC)": "Blitz",
    "US 100 (OTC)": "Blitz",
    "TRON/USD (OTC)": "Blitz",
    "USD/CAD (OTC)": "Blitz",
    "AUD/USD (OTC)": "Blitz",
    "AIG (OTC)": "Blitz",
    "Alibaba Group Holding (OTC)": "Blitz",
    "Snap Inc. (OTC)": "Blitz",
    "US 500 (OTC)": "Blitz",
    "AUD/CHF (OTC)": "Blitz",
    "Amazon/Alibaba (OTC)": "Blitz",
    "Pepe (OTC)": "Blitz",
    "Chainlink (OTC)": "Blitz",
    "USD/ZAR (OTC)": "Blitz",
}

# Configurações de horários específicos para cada ativo
HORARIOS_PADRAO = {
    "USD/BRL_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-00:45", "01:15-23:59"],
        "Wednesday": ["00:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "USOUSD_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-23:59"],
        "Thursday": ["00:00-06:00", "06:30-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "BTC/USD_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "Google_OTC": {
        "Monday": ["00:00-15:30", "16:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-15:30", "16:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-15:30", "16:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "EUR/JPY_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-01:00", "01:15-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "ETH/USD_OTC": {
        "Monday": ["00:00-18:45", "19:15-23:59"],
        "Tuesday": ["00:00-18:45", "19:15-23:59"],
        "Wednesday": ["00:00-18:45", "19:15-23:59"],
        "Thursday": ["00:00-18:45", "19:15-23:59"],
        "Friday": ["00:00-18:45", "19:15-23:59"],
        "Saturday": ["00:00-18:45", "19:15-23:59"],
        "Sunday": ["00:00-18:45", "19:15-23:59"]
    },
    "MELANIA_COIN_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "EUR/GBP_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-01:00", "01:15-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "Apple_OTC": {
        "Monday": ["00:00-15:30", "16:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-15:30", "16:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-15:30", "16:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "Amazon_OTC": {
        "Monday": ["00:00-15:30", "16:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-15:30", "16:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-15:30", "16:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "TRUM_Coin_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "Nike_Inc_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "DOGECOIN_OTC": {
        "Monday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Tuesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Wednesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Thursday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Friday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Saturday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Sunday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"]
    },
    "Tesla_OTC": {
        "Monday": ["00:00-15:30", "16:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-15:30", "16:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-15:30", "16:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "SOL/USD_OTC": {
        "Monday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Tuesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Wednesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Thursday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Friday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Saturday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Sunday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"]
    },
    "1000Sats_OTC": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"]
    },
    "XAUUSD_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-23:59"],
        "Thursday": ["00:00-06:00", "06:30-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "McDonalds_Corporation_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "Meta_OTC": {
        "Monday": ["00:00-15:30", "16:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-15:30", "16:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-15:30", "16:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "Coca_Cola_Company_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "CARDANO_OTC": {
        "Monday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Tuesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Wednesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Thursday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Friday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Saturday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Sunday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"]
    },
    "EUR/USD_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-01:00", "01:15-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "PEN/USD_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-00:45", "01:15-23:59"],
        "Wednesday": ["00:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "Bitcoin_Cash_OTC": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"]
    },
    "AUD/CAD_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-01:00", "01:15-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"]
    },
    "Tesla/Ford_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "US_100_OTC": {
        "Monday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Tuesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Wednesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Thursday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"]
    },
    "TRON/USD_OTC": {
        "Monday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Tuesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Wednesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Thursday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Friday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Saturday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Sunday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"]
    },
    "USD/CAD_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "AUD/USD_OTC": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"]
    },
    "AIG_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "Alibaba_Group_Holding_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "Snap_Inc_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "US_500_OTC": {
        "Monday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Tuesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Wednesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Thursday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"]
    },
    "AUD/CHF_OTC": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"]
    },
    "Amazon/Alibaba_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    },
    "Pepe_OTC": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"]
    },
    "Chainlink_OTC": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"]
    },
    "USD/ZAR_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"]
    }
}

# Mapeamento de ativos para padrões de horários
assets = {
    "USD/BRL (OTC)": HORARIOS_PADRAO["USD/BRL_OTC"],
    "USOUSD (OTC)": HORARIOS_PADRAO["USOUSD_OTC"],
    "BTC/USD (OTC)": HORARIOS_PADRAO["BTC/USD_OTC"],
    "Google (OTC)": HORARIOS_PADRAO["Google_OTC"],
    "EUR/JPY (OTC)": HORARIOS_PADRAO["EUR/JPY_OTC"],
    "ETH/USD (OTC)": HORARIOS_PADRAO["ETH/USD_OTC"],
    "MELANIA COIN (OTC)": HORARIOS_PADRAO["MELANIA_COIN_OTC"],
    "EUR/GBP (OTC)": HORARIOS_PADRAO["EUR/GBP_OTC"],
    "Apple (OTC)": HORARIOS_PADRAO["Apple_OTC"],
    "Amazon (OTC)": HORARIOS_PADRAO["Amazon_OTC"],
    "TRUM Coin (OTC)": HORARIOS_PADRAO["TRUM_Coin_OTC"],
    "Nike, Inc. (OTC)": HORARIOS_PADRAO["Nike_Inc_OTC"],
    "DOGECOIN (OTC)": HORARIOS_PADRAO["DOGECOIN_OTC"],
    "Tesla (OTC)": HORARIOS_PADRAO["Tesla_OTC"],
    "SOL/USD (OTC)": HORARIOS_PADRAO["SOL/USD_OTC"],
    "1000Sats (OTC)": HORARIOS_PADRAO["1000Sats_OTC"],
    "XAUUSD (OTC)": HORARIOS_PADRAO["XAUUSD_OTC"],
    "McDonald´s Corporation (OTC)": HORARIOS_PADRAO["McDonalds_Corporation_OTC"],
    "Meta (OTC)": HORARIOS_PADRAO["Meta_OTC"],
    "Coca-Cola Company (OTC)": HORARIOS_PADRAO["Coca_Cola_Company_OTC"],
    "CARDANO (OTC)": HORARIOS_PADRAO["CARDANO_OTC"],
    "EUR/USD (OTC)": HORARIOS_PADRAO["EUR/USD_OTC"],
    "PEN/USD (OTC)": HORARIOS_PADRAO["PEN/USD_OTC"],
    "Bitcoin Cash (OTC)": HORARIOS_PADRAO["Bitcoin_Cash_OTC"],
    "AUD/CAD (OTC)": HORARIOS_PADRAO["AUD/CAD_OTC"],
    "Tesla/Ford (OTC)": HORARIOS_PADRAO["Tesla/Ford_OTC"],
    "US 100 (OTC)": HORARIOS_PADRAO["US_100_OTC"],
    "TRON/USD (OTC)": HORARIOS_PADRAO["TRON/USD_OTC"],
    "USD/CAD (OTC)": HORARIOS_PADRAO["USD/CAD_OTC"],
    "AUD/USD (OTC)": HORARIOS_PADRAO["AUD/USD_OTC"],
    "AIG (OTC)": HORARIOS_PADRAO["AIG_OTC"],
    "Alibaba Group Holding (OTC)": HORARIOS_PADRAO["Alibaba_Group_Holding_OTC"],
    "Snap Inc. (OTC)": HORARIOS_PADRAO["Snap_Inc_OTC"],
    "US 500 (OTC)": HORARIOS_PADRAO["US_500_OTC"],
    "AUD/CHF (OTC)": HORARIOS_PADRAO["AUD/CHF_OTC"],
    "Amazon/Alibaba (OTC)": HORARIOS_PADRAO["Amazon/Alibaba_OTC"],
    "Pepe (OTC)": HORARIOS_PADRAO["Pepe_OTC"],
    "Chainlink (OTC)": HORARIOS_PADRAO["Chainlink_OTC"],
    "USD/ZAR (OTC)": HORARIOS_PADRAO["USD/ZAR_OTC"]
}

# Lista de ativos disponíveis para negociação
ATIVOS_FORNECIDOS = list(ATIVOS_CATEGORIAS.keys())

# Categorias dos ativos do Bot 2 (usando as mesmas do Bot 1)
BOT2_ATIVOS_CATEGORIAS = ATIVOS_CATEGORIAS

# Mapeamento de ativos para padrões de horários do Bot 2 (usando os mesmos do Bot 1)
BOT2_ASSETS = assets

# Função para parsear os horários
@lru_cache(maxsize=128)
def parse_time_range(time_str):
    """
    Converte uma string de intervalo de tempo (e.g. "09:30-16:00") para um par de time objects.
    """
    start_str, end_str = time_str.split('-')
    start_time = datetime.strptime(start_str, "%H:%M").time()
    end_time = datetime.strptime(end_str, "%H:%M").time()
    return start_time, end_time

# Função para verificar disponibilidade de ativos
def is_asset_available(asset, current_time=None, current_day=None):
    """
    Verifica se um ativo está disponível no horário atual.
    """
    if asset not in assets:
        return False

    if current_day not in assets[asset]:
        return False

    if not current_time:
        current_time = datetime.now().strftime("%H:%M")

    current_time_obj = datetime.strptime(current_time, "%H:%M").time()

    for time_range in assets[asset][current_day]:
        start_time, end_time = parse_time_range(time_range)
        if start_time <= current_time_obj <= end_time:
            return True

    return False

# Função para obter hora no fuso horário de Brasília (específica para Bot 2)
def bot2_obter_hora_brasilia():
    """
    Retorna a hora atual no fuso horário de Brasília.
    """
    fuso_horario_brasilia = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso_horario_brasilia)

def bot2_verificar_disponibilidade():
    """
    Verifica quais ativos estão disponíveis para o sinal atual.
    Retorna uma lista de ativos disponíveis.
    """
    agora = bot2_obter_hora_brasilia()
    current_time = agora.strftime("%H:%M")
    current_day = agora.strftime("%A")

    available_assets = [asset for asset in BOT2_ATIVOS_CATEGORIAS.keys()
                       if is_asset_available(asset, current_time, current_day)]

    return available_assets

def bot2_gerar_sinal_aleatorio():
    """
    Gera um sinal aleatório para enviar.
    Retorna um dicionário com os dados do sinal ou None se não houver sinal.
    """
    ativos_disponiveis = bot2_verificar_disponibilidade()
    if not ativos_disponiveis:
        return None

    ativo = random.choice(ativos_disponiveis)
    direcao = random.choice(['buy', 'sell'])
    categoria = BOT2_ATIVOS_CATEGORIAS.get(ativo, "Não categorizado")

    # Definir o tempo de expiração baseado na categoria
    if categoria == "Blitz":
        expiracao_segundos = random.choice([5, 10, 15, 30])
        tempo_expiracao_minutos = 1  # Fixo em 1 minuto para Blitz
        expiracao_texto = f"⏳ Expiração: {expiracao_segundos} segundos"

    elif categoria == "Digital":
        tempo_expiracao_minutos = random.choice([1, 3, 5])
        expiracao_time = bot2_obter_hora_brasilia() + timedelta(minutes=tempo_expiracao_minutos)
        if tempo_expiracao_minutos == 1:
            expiracao_texto = f"⏳ Expiração: 1 minuto ({expiracao_time.strftime('%H:%M')})"
        else:
            expiracao_texto = f"⏳ Expiração: {tempo_expiracao_minutos} minutos ({expiracao_time.strftime('%H:%M')})"
    elif categoria == "Binary":
        tempo_expiracao_minutos = 1
        expiracao_time = bot2_obter_hora_brasilia() + timedelta(minutes=tempo_expiracao_minutos)
        expiracao_texto = f"⏳ Expiração: 1 minuto ({expiracao_time.strftime('%H:%M')})"
    else:
        tempo_expiracao_minutos = 5
        expiracao_texto = "⏳ Expiração: até 5 minutos"

    return {
        'ativo': ativo,
        'direcao': direcao,
        'categoria': categoria,
        'expiracao_texto': expiracao_texto,
        'tempo_expiracao_minutos': int(tempo_expiracao_minutos)  # Garante que seja inteiro
    }

def bot2_formatar_mensagem(sinal, hora_formatada, idioma):
    """
    Formata a mensagem do sinal em português.
    Retorna a mensagem formatada.
    """
    ativo = sinal['ativo']
    direcao = sinal['direcao']
    categoria = sinal['categoria']
    tempo_expiracao_minutos = sinal['tempo_expiracao_minutos']

    # Debug: registrar os dados sendo usados para formatar a mensagem
    BOT2_LOGGER.info(f"Formatando mensagem com: ativo={ativo}, direção={direcao}, categoria={categoria}, tempo={tempo_expiracao_minutos}")

    # Formatação do nome do ativo para exibição
    nome_ativo_exibicao = ativo.replace("Digital_", "") if ativo.startswith("Digital_") else ativo
    if "(OTC)" in nome_ativo_exibicao and not " (OTC)" in nome_ativo_exibicao:
        nome_ativo_exibicao = nome_ativo_exibicao.replace("(OTC)", " (OTC)")

    # Configura ações e emojis conforme a direção
    action_pt = "COMPRA" if direcao == 'buy' else "VENDA"
    emoji = "🟢" if direcao == 'buy' else "🔴"

    # Hora de entrada convertida para datetime
    hora_entrada = datetime.strptime(hora_formatada, "%H:%M")
    hora_entrada = bot2_obter_hora_brasilia().replace(hour=hora_entrada.hour, minute=hora_entrada.minute, second=0, microsecond=0)
    
    # Determinar quantos minutos adicionar baseado no último dígito do minuto 
    ultimo_digito = hora_entrada.minute % 10
    if ultimo_digito == 3:
        minutos_adicionar = 2  # Se termina em 3, adiciona 2 minutos
    elif ultimo_digito == 7:
        minutos_adicionar = 3  # Se termina em 7, adiciona 3 minutos
    else:
        minutos_adicionar = 2  # Padrão: adiciona 2 minutos

    # Calcular horário de entrada
    hora_entrada_ajustada = hora_entrada + timedelta(minutes=minutos_adicionar)

    # Calcular horário de expiração (a partir do horário de entrada ajustado)
    hora_expiracao = hora_entrada_ajustada + timedelta(minutes=tempo_expiracao_minutos)

    # Calcular horários de reentrada
    # Reentrada 1: Expiração + 2 minutos
    hora_reentrada1 = hora_expiracao + timedelta(minutes=2)

    # Reentrada 2: Reentrada 1 + tempo_expiracao_minutos + 2 minutos
    hora_reentrada2 = hora_reentrada1 + timedelta(minutes=tempo_expiracao_minutos) + timedelta(minutes=2)

    # Formatação dos horários
    hora_entrada_formatada = hora_entrada_ajustada.strftime("%H:%M")
    hora_exp_formatada = hora_expiracao.strftime("%H:%M")
    hora_reentrada1_formatada = hora_reentrada1.strftime("%H:%M")
    hora_reentrada2_formatada = hora_reentrada2.strftime("%H:%M")

    # Texto de expiração
    expiracao_texto_pt = f"⏳ Expiração: {tempo_expiracao_minutos} minuto{'s' if tempo_expiracao_minutos > 1 else ''} ({hora_exp_formatada})"
    
    # Mensagem em PT
    mensagem_pt = (f"⚠️TRADE RÁPIDO⚠️\n\n"
            f"💵 Ativo: {nome_ativo_exibicao}\n"
            f"🏷️ Opções: {categoria}\n"
            f"{emoji} {action_pt}\n"
            f"➡ Entrada: {hora_entrada_formatada}\n"
            f"{expiracao_texto_pt}\n"
            f"Reentrada 1 - {hora_reentrada1_formatada}\n"
            f"Reentrada 2 - {hora_reentrada2_formatada}")
            
    BOT2_LOGGER.info(f"Mensagem formatada final: {mensagem_pt}")
    return mensagem_pt

def bot2_registrar_envio(ativo, direcao, categoria):
    """
    Registra o envio de um sinal no banco de dados.
    Implementação futura: Aqui você adicionaria o código para registrar o envio no banco de dados.
    """
    pass

# Inicialização do Bot 2 quando este arquivo for executado
bot2_sinais_agendados = False
bot2_contador_sinais = 0  # Contador para rastrear quantos sinais foram enviados

# URLs promocionais
XXBROKER_URL = "https://trade.xxbroker.com/register?aff=436564&aff_model=revenue&afftrack="
VIDEO_TELEGRAM_URL = "https://t.me/trendingbrazil/215"

# Diretórios para os vídeos
VIDEOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Subdiretórios para organizar os vídeos
VIDEOS_POS_SINAL_DIR = os.path.join(VIDEOS_DIR, "pos_sinal")
VIDEOS_ESPECIAL_DIR = os.path.join(VIDEOS_DIR, "especial")
VIDEOS_PROMO_DIR = os.path.join(VIDEOS_DIR, "promo")

# Criar os subdiretórios dos idiomas para vídeos pós-sinal (apenas PT)
VIDEOS_POS_SINAL_PT_DIR = os.path.join(VIDEOS_POS_SINAL_DIR, "pt")
os.makedirs(VIDEOS_POS_SINAL_PT_DIR, exist_ok=True)

# Atualização dos diretórios e arquivos para os vídeos especiais (apenas PT)
VIDEOS_ESPECIAL_PT_DIR = os.path.join(VIDEOS_ESPECIAL_DIR, "pt")
os.makedirs(VIDEOS_ESPECIAL_PT_DIR, exist_ok=True)

# Arquivos para vídeos promocionais (apenas PT)
VIDEO_PROMO_PT = os.path.join(VIDEOS_PROMO_DIR, "promo_pt.mp4")

# Dicionário com os caminhos dos vídeos promocionais (apenas PT)
VIDEOS_PROMO = {
    "pt": VIDEO_PROMO_PT
}

# Dicionário com os caminhos dos vídeos especiais (apenas PT)
VIDEOS_ESPECIAIS = {
    "pt": os.path.join(VIDEOS_ESPECIAL_PT_DIR, "especial_pt.mp4")
}

# Dicionário com os caminhos dos vídeos pós-sinal (apenas PT)
VIDEOS_POS_SINAL = {
    "pt": os.path.join(VIDEOS_POS_SINAL_PT_DIR, "pos_sinal_pt.mp4")
}

# Caminho do GIF especial para o canal português
GIF_ESPECIAL_PT = "gif_especial_pt.mp4"  # No diretório principal

# Contador para controle dos GIFs pós-sinal
contador_pos_sinal = 0
contador_desde_ultimo_especial = 0

# Função para enviar GIF após o sinal
def bot2_enviar_gif_pos_sinal():
    """
    Envia um GIF após cada sinal (5 minutos depois).
    """
    try:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] INICIANDO ENVIO DO GIF PÓS-SINAL...")
        
        # Garantir que as pastas existam
        os.makedirs(VIDEOS_POS_SINAL_PT_DIR, exist_ok=True)
        
        # Para cada canal, enviar o GIF correspondente
        for chat_id in BOT2_CHAT_IDS:
            # Obter o vídeo pós-sinal para português
            video_path = VIDEOS_POS_SINAL["pt"]
            
            if not os.path.exists(video_path):
                BOT2_LOGGER.error(f"[{horario_atual}] Arquivo de vídeo pós-sinal não encontrado: {video_path}")
                continue
                
            BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO VÍDEO PÓS-SINAL para o canal {chat_id}...")
            
            # Enviar o vídeo
            url_base = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendVideo"
            
            with open(video_path, 'rb') as video_file:
                files = {
                    'video': video_file
                }
                
                payload = {
                    'chat_id': chat_id,
                    'parse_mode': 'HTML'
                }
                
                resposta = requests.post(url_base, data=payload, files=files)
                
                if resposta.status_code != 200:
                    BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar vídeo pós-sinal para o canal {chat_id}: {resposta.text}")
                else:
                    BOT2_LOGGER.info(f"[{horario_atual}] VÍDEO PÓS-SINAL ENVIADO COM SUCESSO para o canal {chat_id}")
    
    except Exception as e:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar vídeo pós-sinal: {str(e)}")
        traceback.print_exc()

# Função para enviar mensagem promocional antes do sinal
def bot2_enviar_promo_pre_sinal():
    """
    Envia uma mensagem promocional 10 minutos antes de cada sinal com vídeo.
    """
    try:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] INICIANDO ENVIO DA MENSAGEM PROMOCIONAL PRÉ-SINAL...")
        
        # Loop para enviar ao canal configurado
        for chat_id in BOT2_CHAT_IDS:
            # Obter link específico para este canal
            config_canal = BOT2_CANAIS_CONFIG[chat_id]
            link_corretora = config_canal["link_corretora"]
            
            # Preparar texto em português com o link específico
            texto_mensagem = (
                "👉🏼Abram a corretora Pessoal\n\n"
                "⚠️FIQUEM ATENTOS⚠️\n\n"
                "🔥Cadastre-se na XXBROKER agora mesmo🔥\n\n"
                f"➡️ <a href=\"{link_corretora}\">CLICANDO AQUI</a>"
            )
            
            # Obter caminho do vídeo para português
            video_path = VIDEOS_PROMO["pt"]
            
            # Verificar se o arquivo existe
            if not os.path.exists(video_path):
                BOT2_LOGGER.error(f"[{horario_atual}] Arquivo de vídeo promocional não encontrado: {video_path}")
            else:
                BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO VÍDEO PROMOCIONAL PRÉ-SINAL para o canal {chat_id}...")
                # Enviar vídeo
                url_base_video = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendVideo"
                
                with open(video_path, 'rb') as video_file:
                    files = {
                        'video': video_file
                    }
                    
                    payload_video = {
                        'chat_id': chat_id,
                        'parse_mode': 'HTML'
                    }
                    
                    resposta_video = requests.post(url_base_video, data=payload_video, files=files)
                    if resposta_video.status_code != 200:
                        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar vídeo promocional para o canal {chat_id}: {resposta_video.text}")
                    else:
                        BOT2_LOGGER.info(f"[{horario_atual}] VÍDEO PROMOCIONAL PRÉ-SINAL ENVIADO COM SUCESSO para o canal {chat_id}")
            
            # Enviar mensagem com link (agora incorporado diretamente no texto, não como botão)
            BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO MENSAGEM PROMOCIONAL PRÉ-SINAL para o canal {chat_id}...")
            url_base_msg = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
            
            payload_msg = {
                'chat_id': chat_id,
                'text': texto_mensagem,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            resposta_msg = requests.post(url_base_msg, data=payload_msg)
            if resposta_msg.status_code != 200:
                BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar mensagem promocional para o canal {chat_id}: {resposta_msg.text}")
            else:
                BOT2_LOGGER.info(f"[{horario_atual}] MENSAGEM PROMOCIONAL PRÉ-SINAL ENVIADA COM SUCESSO para o canal {chat_id}")
    
    except Exception as e:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar mensagem promocional pré-sinal: {str(e)}")
        traceback.print_exc()

# Função para enviar mensagem promocional a cada 3 sinais
def bot2_enviar_promo_especial():
    """
    Envia uma mensagem promocional especial a cada 3 sinais enviados.
    """
    try:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] INICIANDO ENVIO DA MENSAGEM PROMOCIONAL ESPECIAL (A CADA 3 SINAIS) - Contador: {bot2_contador_sinais}...")
        
        # Loop para enviar ao canal configurado
        for chat_id in BOT2_CHAT_IDS:
            # Obter link específico para este canal
            config_canal = BOT2_CANAIS_CONFIG[chat_id]
            link_corretora = config_canal["link_corretora"]
            
            # Preparar texto em português com o link específico
            texto_mensagem = (
                "Seguimos com as operações ✅\n\n"
                "Mantenham a corretora aberta!!\n\n\n"
                "Pra quem ainda não começou a ganhar dinheiro com a gente👇🏻\n\n"
                "🔥Cadastre-se na XXBROKER agora mesmo🔥\n\n"
                f"➡️ <a href=\"{link_corretora}\">CLICANDO AQUI</a>"
            )
            
            # Obter o caminho do vídeo especial
            video_path = VIDEOS_ESPECIAIS["pt"]
                
            # Verificar se o arquivo existe
            if not os.path.exists(video_path):
                BOT2_LOGGER.error(f"[{horario_atual}] Arquivo de vídeo especial não encontrado: {video_path}")
            else:
                # Enviar vídeo
                BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO VÍDEO ESPECIAL (A CADA 3 SINAIS) para o canal {chat_id}...")
                bot2_enviar_video_especial(video_path, chat_id, horario_atual)
            
            # Enviar mensagem com links (agora incorporados diretamente no texto)
            BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO MENSAGEM PROMOCIONAL ESPECIAL (A CADA 3 SINAIS) para o canal {chat_id}...")
            url_base_msg = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
            
            payload_msg = {
                'chat_id': chat_id,
                'text': texto_mensagem,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            resposta_msg = requests.post(url_base_msg, data=payload_msg)
            if resposta_msg.status_code != 200:
                BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar mensagem promocional especial para o canal {chat_id}: {resposta_msg.text}")
            else:
                BOT2_LOGGER.info(f"[{horario_atual}] MENSAGEM PROMOCIONAL ESPECIAL (A CADA 3 SINAIS) ENVIADA COM SUCESSO para o canal {chat_id}")
    
    except Exception as e:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar mensagem promocional especial: {str(e)}")
        traceback.print_exc()

# Função auxiliar para enviar o vídeo especial
def bot2_enviar_video_especial(video_path, chat_id, horario_atual):
    """
    Função auxiliar para enviar o vídeo especial.
    """
    try:
        url_base_video = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendVideo"
        
        with open(video_path, 'rb') as video_file:
            files = {
                'video': video_file
            }
            
            payload_video = {
                'chat_id': chat_id,
                'parse_mode': 'HTML'
            }
            
            resposta_video = requests.post(url_base_video, data=payload_video, files=files)
            if resposta_video.status_code != 200:
                BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar vídeo especial para o canal {chat_id}: {resposta_video.text}")
                return False
            else:
                BOT2_LOGGER.info(f"[{horario_atual}] VÍDEO ESPECIAL (A CADA 3 SINAIS) ENVIADO COM SUCESSO para o canal {chat_id}")
                return True
    except Exception as e:
        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao abrir ou enviar arquivo de vídeo especial: {str(e)}")
        return False

# Função para enviar o GIF especial a cada 3 sinais (apenas para o canal português)
def bot2_enviar_gif_especial_pt():
    """
    Envia um GIF especial a cada 3 sinais, apenas para o canal português.
    Este GIF é enviado 1 segundo antes da mensagem promocional especial.
    """
    try:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] INICIANDO ENVIO DO GIF ESPECIAL (A CADA 3 SINAIS) - Apenas canal PT...")
        
        # Garantir que a pasta existe
        if not os.path.exists(VIDEOS_ESPECIAL_DIR):
            os.makedirs(VIDEOS_ESPECIAL_DIR, exist_ok=True)
            BOT2_LOGGER.info(f"[{horario_atual}] Criada pasta para GIFs especiais: {VIDEOS_ESPECIAL_DIR}")
        
        # Obter o chat_id do canal português
        for chat_id in BOT2_CHAT_IDS:
            config_canal = BOT2_CANAIS_CONFIG[chat_id]
            idioma = config_canal["idioma"]
            
            # Enviar apenas para o canal em português
            if idioma == "pt":
                # Verificar se o arquivo existe
                if not os.path.exists(GIF_ESPECIAL_PT):
                    BOT2_LOGGER.error(f"[{horario_atual}] Arquivo de GIF especial não encontrado: {GIF_ESPECIAL_PT}")
                    BOT2_LOGGER.info(f"[{horario_atual}] Listando arquivos na pasta {VIDEOS_ESPECIAL_DIR}: {os.listdir(VIDEOS_ESPECIAL_DIR) if os.path.exists(VIDEOS_ESPECIAL_DIR) else 'PASTA NÃO EXISTE'}")
                    return
                
                BOT2_LOGGER.info(f"[{horario_atual}] Enviando GIF especial para o canal português {chat_id}...")
                # Usar sendVideo em vez de sendAnimation para maior compatibilidade
                url_base_video = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendVideo"
                
                with open(GIF_ESPECIAL_PT, 'rb') as gif_file:
                    files = {
                        'video': gif_file
                    }
                    
                    payload_video = {
                        'chat_id': chat_id,
                        'parse_mode': 'HTML'
                    }
                    
                    resposta_video = requests.post(url_base_video, data=payload_video, files=files)
                    if resposta_video.status_code != 200:
                        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar GIF especial para o canal {chat_id}: {resposta_video.text}")
                        # Tentar método alternativo se o primeiro falhar
                        url_alt = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendAnimation"
                        with open(GIF_ESPECIAL_PT, 'rb') as alt_file:
                            files_alt = {'animation': alt_file}
                            resp_alt = requests.post(url_alt, data=payload_video, files=files_alt)
                            if resp_alt.status_code == 200:
                                BOT2_LOGGER.info(f"[{horario_atual}] GIF ESPECIAL ENVIADO COM SUCESSO via método alternativo para o canal português {chat_id}")
                    else:
                        BOT2_LOGGER.info(f"[{horario_atual}] GIF ESPECIAL ENVIADO COM SUCESSO para o canal português {chat_id}")
                
                # Só enviar para o canal PT, então podemos interromper a iteração
                break
    
    except Exception as e:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar GIF especial: {str(e)}")
        traceback.print_exc()

def bot2_send_message(ignorar_anti_duplicacao=False):
    """
    Função principal para enviar uma mensagem de sinal para o canal do Telegram.
    Executa todo o processo de geração e envio de sinal.
    """
    try:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        hora_formatada = bot2_obter_hora_brasilia().strftime("%H:%M")
        BOT2_LOGGER.info(f"[{horario_atual}] INICIANDO ENVIO DE SINAL...")

        # Verificação anti-duplicação (menos de 15 minutos entre envios)
        if not ignorar_anti_duplicacao:
            tempo_desde_ultimo_envio = (bot2_obter_hora_brasilia() - bot2_send_message.ultimo_envio_timestamp).total_seconds() / 60
            if tempo_desde_ultimo_envio < 10:  # Ajustado para 10 minutos
                BOT2_LOGGER.warning(f"[{horario_atual}] Tentativa de envio muito próxima ao último envio ({tempo_desde_ultimo_envio:.1f} minutos). Pulando.")
                return

        # Escolher aleatoriamente um sinal para enviar
        sinal = bot2_gerar_sinal_aleatorio()
        if not sinal:
            BOT2_LOGGER.error(f"[{horario_atual}] Não foi possível gerar um sinal. Nenhum ativo disponível.")
            return
        
        # Extrair dados do sinal
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        categoria = sinal['categoria']
        
        BOT2_LOGGER.info(f"[{horario_atual}] Sinal gerado: Ativo={ativo}, Direção={direcao}, Categoria={categoria}")

        # Para cada canal configurado, enviar o sinal no idioma correto
        for chat_id in BOT2_CHAT_IDS:
            # Obter configuração e link específico para este canal
            config_canal = BOT2_CANAIS_CONFIG[chat_id]
            link_corretora = config_canal["link_corretora"]
            
            # Formatação da mensagem em português
            mensagem = bot2_formatar_mensagem(sinal, hora_formatada, "pt")
            
            # Configurar teclado inline com o link específico da corretora
            teclado_inline = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🔗 Abrir corretora",
                            "url": link_corretora
                        }
                    ]
                ]
            }
            
            BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO MENSAGEM para o canal {chat_id}...")
            url_base = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
            
            payload = {
                'chat_id': chat_id,
                'text': mensagem,
                'parse_mode': 'HTML',
                'reply_markup': json.dumps(teclado_inline)
            }
            
            resposta = requests.post(url_base, data=payload)

            if resposta.status_code != 200:
                BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar sinal para o canal {chat_id}: {resposta.text}")
            else:
                BOT2_LOGGER.info(f"[{horario_atual}] MENSAGEM DO SINAL ENVIADA COM SUCESSO para o canal {chat_id}")

        # Registra estatísticas de envio
        bot2_registrar_envio(ativo, direcao, categoria)
        
        # Incrementa o contador global de sinais
        global bot2_contador_sinais
        bot2_contador_sinais += 1
        BOT2_LOGGER.info(f"[{horario_atual}] Contador de sinais incrementado: {bot2_contador_sinais}")
        
        # Agendar o envio do GIF pós-sinal para 5 minutos depois
        BOT2_LOGGER.info(f"[{horario_atual}] Agendando envio do GIF pós-sinal para daqui a 5 minutos...")
        import threading
        timer_pos_sinal = threading.Timer(300.0, bot2_enviar_gif_pos_sinal)  # 300 segundos = 5 minutos
        timer_pos_sinal.start()
        
        # Verifica se deve enviar a mensagem promocional especial (a cada 3 sinais)
        if bot2_contador_sinais % 3 == 0:
            # Agendar o envio do GIF especial para 6 minutos - 1 segundo depois
            BOT2_LOGGER.info(f"[{horario_atual}] Agendando envio do GIF especial PT para daqui a {359} segundos...")
            timer_gif_especial = threading.Timer(359.0, bot2_enviar_gif_especial_pt)  # 359 segundos = 5 minutos e 59 segundos
            timer_gif_especial.start()
            
            # Agendar o envio da mensagem promocional especial para 6 minutos depois
            BOT2_LOGGER.info(f"[{horario_atual}] Agendando envio da mensagem promocional especial para daqui a 6 minutos (sinal #{bot2_contador_sinais}, divisível por 3)...")
            timer_promo_especial = threading.Timer(360.0, bot2_enviar_promo_especial)  # 360 segundos = 6 minutos
            timer_promo_especial.start()

        # Atualiza o timestamp do último envio
        bot2_send_message.ultimo_envio_timestamp = bot2_obter_hora_brasilia()

    except Exception as e:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar mensagem: {str(e)}")
        traceback.print_exc()

# Inicializações para a função send_message
bot2_send_message.ultimo_envio_timestamp = bot2_obter_hora_brasilia()
bot2_send_message.contagem_por_hora = {bot2_obter_hora_brasilia().replace(minute=0, second=0, microsecond=0): 0}

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
            # Primeiro sinal - Promo 10 minutos antes
            schedule.every().day.at(f"{hora:02d}:03:02").do(bot2_enviar_promo_pre_sinal)
            schedule.every().day.at(f"{hora:02d}:13:02").do(bot2_send_message)

            # Segundo sinal - Promo 10 minutos antes
            schedule.every().day.at(f"{hora:02d}:27:02").do(bot2_enviar_promo_pre_sinal)
            schedule.every().day.at(f"{hora:02d}:37:02").do(bot2_send_message)

            # Terceiro sinal - Promo 10 minutos antes
            schedule.every().day.at(f"{hora:02d}:43:02").do(bot2_enviar_promo_pre_sinal)
            schedule.every().day.at(f"{hora:02d}:53:02").do(bot2_send_message)

        # Marcar como agendado
        bot2_schedule_messages.scheduled = True

        BOT2_LOGGER.info("Agendamento de mensagens do Bot 2 concluído com sucesso")
        BOT2_LOGGER.info("Horários configurados:")
        BOT2_LOGGER.info("Promos pré-sinal: XX:03:02, XX:27:02, XX:43:02")
        BOT2_LOGGER.info("Sinais: XX:13:02, XX:37:02, XX:53:02")

    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao agendar mensagens do Bot 2: {str(e)}")
        traceback.print_exc()

def bot2_testar_envio_promocional():
    """
    Função para testar o envio das mensagens promocionais e vídeos.
    """
    BOT2_LOGGER.info("Iniciando teste de avisos pré-sinais...")
    
    # Testar mensagem promocional pré-sinal
    BOT2_LOGGER.info("Testando envio de mensagem promocional pré-sinal...")
    bot2_enviar_promo_pre_sinal()
    
    # Agendar o teste de envio do sinal para 30 segundos depois
    BOT2_LOGGER.info("Agendando teste de envio do sinal para 30 segundos depois...")
    import threading
    timer_sinal = threading.Timer(30.0, lambda: bot2_send_message(ignorar_anti_duplicacao=True))
    timer_sinal.start()
    
    BOT2_LOGGER.info("Iniciando operação normal do Bot 2...")

# Função para testar toda a sequência de sinais imediatamente
def bot2_testar_sequencia_completa():
    """
    Função para testar toda a sequência de sinais imediatamente:
    1. Vídeo/mensagem pré-sinal
    2. Sinal
    3. Vídeo pós-sinal
    """
    BOT2_LOGGER.info("TESTE COMPLETO: Iniciando teste da sequência completa...")
    
    # Função para executar cada etapa da sequência
    def executar_etapa(etapa, func, delay_segundos=0):
        BOT2_LOGGER.info(f"TESTE COMPLETO: Etapa {etapa} será executada em {delay_segundos} segundos...")
        if delay_segundos > 0:
            import threading
            timer = threading.Timer(delay_segundos, func)
            timer.start()
        else:
            func()
    
    # Etapa 1: Enviar vídeo e mensagem pré-sinal
    executar_etapa(1, lambda: bot2_enviar_promo_pre_sinal(), 0)
    
    # Etapa 2: Enviar sinal 5 segundos depois
    executar_etapa(2, lambda: bot2_send_message(ignorar_anti_duplicacao=True), 5)
    
    # Etapa 3: Enviar vídeo pós-sinal diretamente após 10 segundos (sem esperar 1 minuto)
    executar_etapa(3, lambda: bot2_enviar_gif_pos_sinal(), 10)
    
    BOT2_LOGGER.info("TESTE COMPLETO: Sequência de teste agendada com sucesso!")

# Modificar a função de inicialização para não executar a sequência de teste
def iniciar_ambos_bots():
    """
    Inicializa ambos os bots quando executado como script principal.
    """
    # Não executar o teste, iniciar o bot normalmente
    # bot2_testar_sequencia_completa()  # Comentado para executar normalmente
    
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
        BOT2_LOGGER.info("Inicializando Bot 2 em modo normal...")
        bot2_schedule_messages()  # Agendar mensagens nos horários normais
        bot2_keep_bot_running()  # Chamada direta para a função do Bot 2
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao inicializar Bot 2: {str(e)}")
    
    logging.info("Ambos os bots estão em execução!")
    BOT2_LOGGER.info("Ambos os bots estão em execução em modo normal!")
    
    # Loop principal para verificar os agendamentos
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logging.error(f"Erro no loop principal: {str(e)}")
            BOT2_LOGGER.error(f"Erro no loop principal: {str(e)}")
            time.sleep(5)  # Pausa maior em caso de erro

# Função para verificar se o bot já está em execução
def is_bot_already_running():
    """
    Verifica se já existe uma instância do bot em execução usando um socket.
    """
    try:
        # Tenta criar um socket em uma porta específica
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 9876))  # Porta arbitrária para verificação
        return False
    except socket.error:
        # Se a porta estiver em uso, assume que o bot está rodando
        return True

# Função original do Bot 1 (implementação mínima para compatibilidade)
def schedule_messages():
    """
    Função de compatibilidade com o Bot 1 original.
    Esta implementação é um placeholder e não realiza agendamentos reais.
    """
    logging.info("Função schedule_messages() do Bot 1 chamada (sem efeito)")
    pass

# Função para manter o Bot 2 em execução
def bot2_keep_bot_running():
    """
    Mantém o Bot 2 em execução, verificando os agendamentos.
    """
    BOT2_LOGGER.info("Iniciando função keep_bot_running do Bot 2")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        BOT2_LOGGER.error(f"Erro na função keep_bot_running do Bot 2: {str(e)}")
        traceback.print_exc()

# Executar se este arquivo for o script principal
if __name__ == "__main__":
    iniciar_ambos_bots()
