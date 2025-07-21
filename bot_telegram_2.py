# -*- coding: utf-8 -*-
"""
Bot de envio de sinais para canais do Telegram
Por: Trending Brasil
Versão: 3.0
"""

# Importar bibliotecas necessárias
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
import telebot
import threading
from datetime import time as datetime_time
import uuid
import copy
from pathlib import Path

# Configuração do logger
BOT2_LOGGER = logging.getLogger("bot2")
BOT2_LOGGER.setLevel(logging.INFO)
bot2_formatter = logging.Formatter(
    "%(asctime)s - BOT2 - %(levelname)s - %(message)s")

# Evitar duplicação de handlers
if not BOT2_LOGGER.handlers:
    # Handler para arquivo (pode usar UTF-8)
    bot2_file_handler = logging.FileHandler("bot_telegram_bot2_logs.log", encoding='utf-8')
    bot2_file_handler.setFormatter(bot2_formatter)
    BOT2_LOGGER.addHandler(bot2_file_handler)

    # Handler para console (sem emojis para evitar problemas de codificação)
    class NoEmojiFormatter(logging.Formatter):
        """Formatter que remove emojis e outros caracteres Unicode incompatíveis com Windows console"""
        def format(self, record):
            # Primeiro obter a mensagem formatada normalmente
            msg = super().format(record)
            # Substitua emojis comuns por equivalentes ASCII
            emoji_map = {
                '🚀': '[ROCKET]',
                '🔧': '[CONFIG]',
                '✅': '[OK]',
                '❌': '[ERRO]',
                '⚠️': '[AVISO]',
                '🔄': '[RELOAD]',
                '📅': '[DATA]',
                '🔍': '[BUSCA]',
                '📊': '[STATS]',
                '📋': '[LISTA]',
                '🌐': '[GLOBAL]',
                '📣': '[ANUNCIO]',
                '🎬': '[VIDEO]',
                '⏱️': '[TEMPO]',
                '⏳': '[ESPERA]',
                '🟢': '[VERDE]',
                '🔒': '[LOCK]',
                '🔓': '[UNLOCK]',
                '📤': '[ENVIO]',
                '⚙️': '[ENGRENAGEM]',
                '🛑': '[PARAR]',
                '🆔': '[ID]',
            }
            
            for emoji, replacement in emoji_map.items():
                msg = msg.replace(emoji, replacement)
                
            return msg
    
    console_formatter = NoEmojiFormatter("%(asctime)s - BOT2 - %(levelname)s - %(message)s")
    bot2_console_handler = logging.StreamHandler()
    bot2_console_handler.setFormatter(console_formatter)
    BOT2_LOGGER.addHandler(bot2_console_handler)

# Credenciais Telegram
BOT2_TOKEN = "7997585882:AAFDyG-BYskj1gyAbh17X5jd6DDClXdluww"

# Inicialização do bot
bot2 = telebot.TeleBot(BOT2_TOKEN)

# Configuração dos canais para cada idioma
BOT2_CANAIS_CONFIG = {
    "pt": [-1002592398378]  # Canal para mensagens em português
}

# Lista de IDs dos canais para facilitar iteração
BOT2_CHAT_IDS = []
for idioma, chats in BOT2_CANAIS_CONFIG.items():
    BOT2_CHAT_IDS.extend(chats)

# Links para cada idioma
LINKS_CORRETORA = {
    "pt": "https://www.homebroker.com/ref/cDOWMjSI/"
}

# URLs dos vídeos para cada idioma
LINKS_VIDEO = {
    "pt": "https://t.me/trendingbrazil/215"
}

# URLs diretas para GIFs
# GIF pós-sinal removido
# Atualizado para usar o arquivo do GitHub
GIF_PROMO_PATH = "videos/promo/siren-lights (2).mp4"  # Arquivo do GitHub

"""
INSTRUÇÕES PARA OTIMIZAR GIFs:
1. Baixe o GIF original do Giphy
2. Use um conversor online como ezgif.com para:
   - Redimensionar: largura máxima de 300-400px 
   - Otimizar: reduzir qualidade para 70-80%
   - Converter para formato WebP ou MP4 (mais leve que GIF)
3. Salve o arquivo otimizado em:
   - videos/promo/siren-lights (2).mp4 (para o promocional)
4. Tamanho máximo recomendado: 1MB para melhor compatibilidade com celulares
"""

# Horários de funcionamento dos ativos
HORARIOS_PADRAO = {
    "BTC_USD_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "ETH_USD_(OTC)": {
        "Monday": ["00:00-19:45", "20:15-23:59"],
        "Tuesday": ["00:00-19:45", "20:15-23:59"],
        "Wednesday": ["00:00-19:45", "20:15-23:59"],
        "Thursday": ["00:00-19:45", "20:15-23:59"],
        "Friday": ["00:00-19:45", "20:15-23:59"],
        "Saturday": ["00:00-19:45", "20:15-23:59"],
        "Sunday": ["00:00-19:45", "20:15-23:59"],
    },
    "EUR_JPY_(OTC)": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-01:00", "01:15-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "1000Sats_(OTC)": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Pepe_(OTC)": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "US_500_(OTC)": {
        "Monday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Tuesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Wednesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Thursday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
    },
    "Gold_Silver_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Worldcoin_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "USD_THB_(OTC)": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "CHF_JPY_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "GBP_AUD_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "GBP_CHF": {
        "Monday": ["00:00-16:00"],
        "Tuesday": ["00:00-16:00"],
        "Wednesday": ["00:00-16:00"],
        "Thursday": ["00:00-16:00"],
        "Friday": ["00:00-14:00"],
        "Saturday": [],
        "Sunday": [],
    },
    "GBP_CAD_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "AUD_CHF": {
        "Monday": ["00:00-16:00"],
        "Tuesday": ["00:00-16:00"],
        "Wednesday": ["00:00-16:00"],
        "Thursday": ["00:00-16:00"],
        "Friday": ["00:00-14:00"],
        "Saturday": [],
        "Sunday": [],
    },
    "GER_30_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "AUD_CHF_(OTC)": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "EUR_AUD": {
        "Monday": ["00:00-16:00"],
        "Tuesday": ["00:00-16:00"],
        "Wednesday": ["00:00-16:00"],
        "Thursday": ["00:00-16:00"],
        "Friday": ["00:00-14:00"],
        "Saturday": [],
        "Sunday": [],
    },
    "USD_CAD_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "BTC_USD": {
        "Monday": ["03:00-15:00"],
        "Tuesday": ["03:00-15:00"],
        "Wednesday": ["03:00-15:00"],
        "Thursday": ["03:00-15:00"],
        "Friday": ["03:00-15:00"],
        "Saturday": [],
        "Sunday": [],
    },
    "USD_CAD": {
        "Monday": ["03:00-15:00"],
        "Tuesday": ["03:00-15:00", "21:00-23:59"],
        "Wednesday": ["00:00-15:00"],
        "Thursday": ["03:00-15:00"],
        "Friday": ["03:00-15:00"],
        "Saturday": [],
        "Sunday": [],
    },
    "AUD_JPY_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "AUD_USD": {
        "Monday": ["00:00-16:00"],
        "Tuesday": ["00:00-16:00"],
        "Wednesday": ["00:00-16:00"],
        "Thursday": ["00:00-16:00"],
        "Friday": ["00:00-14:00"],
        "Saturday": [],
        "Sunday": [],
    },
    "Bitcoin_Cash_(OTC)": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "MELANIA_Coin_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "US_100_(OTC)": {
        "Monday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Tuesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Wednesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Thursday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
    },
    "AUD_CAD_(OTC)": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "Amazon_Ebay_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Coca_Cola_Company_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "AIG_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Amazon_Alibaba_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "DASH_(OTC)": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "SP_35_(OTC)": {
        "Monday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Tuesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Wednesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Thursday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
    },
    "TRUMP_Coin_(OTC)": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "EUR_CAD_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "HK_33_(OTC)": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "Alphabet_Microsoft_(OTC)": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "USD_ZAR_(OTC)": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "Litecoin_(OTC)": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Hamster_Kombat_(OTC)": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "USD_Currency_Index_(OTC)": {
        "Monday": ["00:00-10:00", "10:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-10:00", "10:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-10:00", "10:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-10:00", "10:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-10:00", "10:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "AUS_200_(OTC)": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "JP_225_(OTC)": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    }
}

# Variáveis de controle
contador_sinais = 0  # Para rastrear o número de sinais enviados
sinais_enviados_hoje = []  # Lista para armazenar os sinais enviados hoje
ultimo_sinal = None  # Armazenar o último sinal enviado

# Função para obter a hora atual no fuso horário de Brasília
def obter_hora_brasilia():
    """Retorna a hora atual no fuso horário de Brasília."""
    fuso_horario_brasilia = pytz.timezone("America/Sao_Paulo")
    return datetime.now(fuso_horario_brasilia)

# Função para verificar se um ativo está disponível no horário atual
def verificar_disponibilidade_ativo(ativo):
    """
    Verifica se um ativo está disponível para trade no momento atual.
    
    Args:
        ativo (str): Nome do ativo a ser verificado
        
    Returns:
        bool: True se o ativo está disponível, False caso contrário
    """
    try:
        # Obter hora atual em Brasília
        agora = obter_hora_brasilia()
        
        # Dia da semana em inglês (Monday, Tuesday, etc.)
        dia_semana = agora.strftime("%A")
        
        # Hora atual no formato HH:MM
        hora_atual = agora.strftime("%H:%M")
        
        # Verificar se o ativo está no dicionário de horários
        ativo_formatado = ativo.replace(" ", "_").replace("/", "_").replace("-", "_")
        
        # Logging do nome formatado do ativo
        BOT2_LOGGER.debug(f"Verificando disponibilidade do ativo: {ativo} (formatado como {ativo_formatado})")
        
        # Se o ativo não estiver no dicionário de horários, consideramos disponível
        if ativo_formatado not in HORARIOS_PADRAO:
            BOT2_LOGGER.warning(f"Ativo {ativo} ({ativo_formatado}) não encontrado na tabela de horários. Considerando disponível.")
            return True
            
        # Obter os intervalos de horário para o dia atual
        intervalos = HORARIOS_PADRAO[ativo_formatado].get(dia_semana, [])
        
        # Se não houver intervalos definidos para este dia, o ativo está indisponível
        if not intervalos:
            BOT2_LOGGER.info(f"Ativo {ativo} não está disponível aos {dia_semana}.")
            return False
            
        # Verificar se a hora atual está dentro de algum dos intervalos
        for intervalo in intervalos:
            inicio, fim = intervalo.split("-")
            if inicio <= hora_atual <= fim:
                BOT2_LOGGER.info(f"Ativo {ativo} está disponível no intervalo {intervalo}")
                return True
                
        BOT2_LOGGER.info(f"Ativo {ativo} não está disponível no horário atual {hora_atual}.")
        return False
        
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao verificar disponibilidade do ativo {ativo}: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        # Em caso de erro, consideramos o ativo disponível
        return True

# Função para verificar quais ativos estão disponíveis para trade
def verificar_ativos_disponiveis():
    """
    Verifica quais ativos estão disponíveis para trade no momento atual.
    
    Returns:
        list: Lista de ativos disponíveis para trade
    """
    BOT2_LOGGER.info("Verificando ativos disponíveis para trade...")
    
    try:
        # Lista completa dos ativos disponíveis
        todos_ativos = [
            "Gold/Silver (OTC)",
            "Worldcoin (OTC)",
            "USD/THB (OTC)",
            "ETH/USD (OTC)",
            "CHF/JPY (OTC)",
            "Pepe (OTC)",
            "GBP/AUD (OTC)",
            "GBP/CHF",
            "GBP/CAD (OTC)",
            "EUR/JPY (OTC)",
            "AUD/CHF",
            "GER 30 (OTC)",
            "AUD/CHF (OTC)",
            "EUR/AUD",
            "USD/CAD (OTC)",
            "BTC/USD",
            "Amazon/Ebay (OTC)",
            "Coca-Cola Company (OTC)",
            "AIG (OTC)",
            "Amazon/Alibaba (OTC)",
            "Bitcoin Cash (OTC)",
            "AUD/USD",
            "DASH (OTC)",
            "BTC/USD (OTC)",
            "SP 35 (OTC)",
            "TRUMP Coin (OTC)",
            "US 100 (OTC)",
            "EUR/CAD (OTC)",
            "HK 33 (OTC)",
            "Alphabet/Microsoft (OTC)",
            "1000Sats (OTC)",
            "USD/ZAR (OTC)",
            "Litecoin (OTC)",
            "Hamster Kombat (OTC)",
            "USD Currency Index (OTC)",
            "AUS 200 (OTC)",
            "USD/CAD",
            "MELANIA Coin (OTC)",
            "JP 225 (OTC)",
            "AUD/CAD (OTC)",
            "AUD/JPY (OTC)",
            "US 500 (OTC)"
        ]
        
        # Filtrar apenas os ativos disponíveis no momento
        ativos_disponiveis = [ativo for ativo in todos_ativos if verificar_disponibilidade_ativo(ativo)]
        
        BOT2_LOGGER.info(f"Ativos disponíveis no momento: {len(ativos_disponiveis)} de {len(todos_ativos)}")
        
        # Se não houver ativos disponíveis, usar alguns ativos como fallback
        if not ativos_disponiveis:
            BOT2_LOGGER.warning("Nenhum ativo disponível! Usando lista de fallback.")
            fallback_ativos = [
                "ETH/USD (OTC)",
                "BTC/USD (OTC)",
                "US 500 (OTC)",
                "Gold/Silver (OTC)"
            ]
            return fallback_ativos
        
        return ativos_disponiveis
        
    except Exception as e:
        BOT2_LOGGER.error(f"Erro geral ao verificar ativos disponíveis: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        # Lista reduzida em caso de erro
        return [
            "EUR/USD (OTC)",
            "Gold/Silver (OTC)",
            "BTC/USD (OTC)",
            "ETH/USD (OTC)"
        ]

# Função para gerar um sinal aleatório
def gerar_sinal():
    """Gera um sinal aleatório com ativo e direção."""
    # Verificar quais ativos estão disponíveis no momento
    ativos_disponiveis = verificar_ativos_disponiveis()
    
    # Registrar a quantidade de ativos disponíveis
    BOT2_LOGGER.info(f"Encontrados {len(ativos_disponiveis)} ativos disponíveis para trade")
    
    # Se houver menos de 3 ativos disponíveis, adicionar logs de aviso
    if len(ativos_disponiveis) < 3:
        BOT2_LOGGER.warning(f"Poucos ativos disponíveis: {ativos_disponiveis}")
    
    # Escolher um ativo aleatório dentre os disponíveis
    ativo = random.choice(ativos_disponiveis)
    direcoes = ["CALL", "PUT"]
    direcao = random.choice(direcoes)
    
    BOT2_LOGGER.info(f"Sinal gerado: {ativo} - {direcao}")
    
    return {
        "ativo": ativo,
        "direcao": direcao,
        "tempo_expiracao": 5,  # 5 minutos de expiração
        "hora_criacao": obter_hora_brasilia()
    }

# Função para formatar a mensagem de sinal
def formatar_mensagem_sinal(sinal, idioma):
    """Formata a mensagem de sinal para o idioma especificado."""
    ativo = sinal["ativo"]
    direcao = sinal["direcao"]
    tempo_expiracao = sinal["tempo_expiracao"]
    
    # Obter horário atual
    hora_atual = obter_hora_brasilia()
    
    # Horário do sinal (2 minutos depois do envio)
    hora_sinal = hora_atual + timedelta(minutes=2)
    
    # Horário de expiração (5 minutos depois do horário do sinal)
    hora_expiracao = hora_sinal + timedelta(minutes=tempo_expiracao)
    
    # Horários de gales
    hora_gale1 = hora_expiracao + timedelta(minutes=5)
    hora_gale2 = hora_gale1 + timedelta(minutes=5)
    hora_gale3 = hora_gale2 + timedelta(minutes=5)
    
    # Emoji baseado na direção
    emoji = "🟩" if direcao == "CALL" else "🟥"
    
    # Texto da direção
    action = "COMPRA" if direcao == "CALL" else "VENDA"
    
    # Formatação de horários
    hora_sinal_str = hora_sinal.strftime("%H:%M")
    hora_expiracao_str = hora_expiracao.strftime("%H:%M")
    hora_gale1_str = hora_gale1.strftime("%H:%M")
    hora_gale2_str = hora_gale2.strftime("%H:%M")
    hora_gale3_str = hora_gale3.strftime("%H:%M")
    
    # Obter links específicos para o idioma
    link_corretora = LINKS_CORRETORA[idioma]
    link_video = LINKS_VIDEO[idioma]
    
    # Mensagem em português
    mensagem = (
        f"💰{tempo_expiracao} minutos de expiração\n"
        f"{ativo};{hora_sinal_str};{action} {emoji} Digital\n\n"
        f"🕐TEMPO PARA {hora_expiracao_str}\n\n"
        f"1º GALE — TEMPO PARA {hora_gale1_str}\n"
        f"2º GALE TEMPO PARA {hora_gale2_str}\n"
        f"3º GALE TEMPO PARA {hora_gale3_str}\n\n"
        f'📲 <a href="{link_corretora}">Clique para abrir a corretora</a>\n'
        f'🙋‍♂️ Não sabe operar ainda? <a href="{link_video}">Clique aqui</a>'
    )
        
    return mensagem

# Função para formatar a mensagem de participação
def formatar_mensagem_participacao(idioma):
    """Formata a mensagem de participação para o idioma especificado."""
    link_corretora = LINKS_CORRETORA[idioma]
    link_video = LINKS_VIDEO[idioma]
    
    # Mensagem em português
    mensagem = (
        "⚠⚠PARA PARTICIPAR DESTA SESSÃO, SIGA O PASSO A PASSO ABAIXO⚠⚠\n\n"
        "1º ✅ —>  Crie sua conta na corretora no link abaixo e GANHE $10.000 DE GRAÇA pra começar a operar com a gente sem ter que arriscar seu dinheiro.\n\n"
        "Você vai poder testar todos nossas\n"
        "operações com risco ZERO!\n\n"
        "👇🏻👇🏻👇🏻👇🏻\n\n"
        f'<a href="{link_corretora}">CRIE SUA CONTA AQUI E GANHE R$10.000</a>\n\n'
        "—————————————————————\n\n"
        "2º ✅ —>  Assista o vídeo abaixo e aprenda como depositar e como entrar com a gente nas nossas operações!\n\n"
        "👇🏻👇🏻👇🏻👇🏻\n\n"
        f'<a href="{link_video}">CLIQUE AQUI E ASSISTA O VÍDEO</a>'
    )
        
    return mensagem

# Função para formatar a mensagem de abertura da corretora
def formatar_mensagem_abertura_corretora(idioma):
    """Formata a mensagem de abertura da corretora para o idioma especificado."""
    link_corretora = LINKS_CORRETORA[idioma]
    
    # Mensagem em português
    mensagem = (
        "👉🏼Abram a corretora Pessoal\n\n"
        "⚠FIQUEM ATENTOS⚠\n\n"
        "🔥Cadastre-se na XXBROKER agora mesmo🔥\n\n"
        f'➡ <a href="{link_corretora}">CLICANDO AQUI</a>'
    )
        
    return mensagem

# As funções enviar_mensagem e enviar_gif foram removidas por não serem mais necessárias
# O código agora envia mensagens diretamente para o canal em português

# Função que envia o sinal para todos os canais
def enviar_sinal():
    """Envia um sinal para todos os canais configurados."""
    global contador_sinais, ultimo_sinal
    
    BOT2_LOGGER.info("Iniciando envio de sinal")
    
    # Incrementar o contador de sinais
    contador_sinais += 1
    
    # Gerar um novo sinal
    sinal = gerar_sinal()
    ultimo_sinal = sinal
    
    # Registrar informações do sinal
    BOT2_LOGGER.info(f"Sinal #{contador_sinais}: {sinal['ativo']} - {sinal['direcao']}")
    BOT2_LOGGER.info("Enviando sinal único")
    
    # Formatar mensagem apenas para português
    mensagem = formatar_mensagem_sinal(sinal, "pt")
    
    # Enviar o sinal apenas para o canal em português
    try:
        chat_id = BOT2_CANAIS_CONFIG["pt"][0]  # Pegar apenas o primeiro canal em português
        BOT2_LOGGER.info(f"Tentando enviar sinal para canal {chat_id}")
        
        bot2.send_message(
            chat_id=chat_id,
            text=mensagem,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        BOT2_LOGGER.info(f"Sinal enviado com sucesso para o canal {chat_id}")
        
        # Sequência especial para todos os sinais
        threading.Timer(7 * 60, lambda: iniciar_sequencia_especial(sinal)).start()
        BOT2_LOGGER.info("Agendada sequência especial para o sinal")
        return True
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar sinal para o canal: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        return False

# Função para enviar o GIF pós-sinal - removida
def enviar_gif_pos_sinal():
    """Função de envio do GIF pós-sinal removida."""
    BOT2_LOGGER.info("Função de envio do GIF pós-sinal foi removida.")
    return True

# Função para iniciar a sequência de envios para todos os sinais
def iniciar_sequencia_especial(sinal):
    """
    Inicia a sequência de envios especial para todos os sinais.
    
    Args:
        sinal: O sinal que foi enviado
    """
    BOT2_LOGGER.info("Iniciando sequência especial para o sinal")
    
    # Agendar envio da mensagem de participação (40 minutos após o sinal)
    threading.Timer(40 * 60, enviar_mensagem_participacao).start()
    BOT2_LOGGER.info("Agendado envio da mensagem de participação para daqui a 40 minutos")

# Função para enviar a mensagem de participação
def enviar_mensagem_participacao():
    """Envia a mensagem de participação para o canal."""
    BOT2_LOGGER.info("Iniciando processo de envio da mensagem de participação")
    
    try:
        # Formatar mensagem de participação para português
        mensagem = formatar_mensagem_participacao("pt")
        BOT2_LOGGER.info("Mensagem de participação formatada com sucesso")
        
        # Enviar para o canal em português
        chat_id = BOT2_CANAIS_CONFIG["pt"][0]
        BOT2_LOGGER.info(f"Tentando enviar mensagem de participação para canal {chat_id}")
        
        bot2.send_message(
            chat_id=chat_id,
            text=mensagem,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        BOT2_LOGGER.info(f"Mensagem de participação enviada com sucesso para o canal {chat_id}")
        
        # Agendar envio do GIF promocional (10 minutos depois)
        BOT2_LOGGER.info("Agendando envio do GIF promocional para daqui a 10 minutos")
        threading.Timer(10 * 60, enviar_gif_promocional).start()
        BOT2_LOGGER.info("Agendado envio do GIF promocional para daqui a 10 minutos")
        return True
        
    except Exception as e:
        BOT2_LOGGER.error(f"Exceção ao enviar mensagem de participação: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        return False

# Função para enviar o GIF promocional
def enviar_gif_promocional():
    """Envia o GIF promocional para o canal."""
    BOT2_LOGGER.info("Iniciando processo de envio do GIF promocional")
    
    try:
        chat_id = BOT2_CANAIS_CONFIG["pt"][0]
        
        # Verificar se o arquivo local existe
        if os.path.exists(GIF_PROMO_PATH):
            BOT2_LOGGER.info(f"Usando arquivo: {GIF_PROMO_PATH}")
            with open(GIF_PROMO_PATH, 'rb') as arquivo:
                bot2.send_animation(
                    chat_id=chat_id,
                    animation=arquivo,
                    caption=None
                )
        else:
            # Usar URL como fallback
            fallback_url = "https://media.giphy.com/media/whPiIq21hxXuJn7WVX/giphy.gif"
            BOT2_LOGGER.warning(f"Arquivo local {GIF_PROMO_PATH} não encontrado. Usando URL de fallback.")
            bot2.send_animation(
                chat_id=chat_id,
                animation=fallback_url
            )
        
        BOT2_LOGGER.info(f"GIF promocional enviado com sucesso para o canal {chat_id}")
        
        # Agendar envio da mensagem de abertura da corretora (1 minuto depois)
        BOT2_LOGGER.info("Agendando envio da mensagem de abertura da corretora para daqui a 1 minuto")
        threading.Timer(1 * 60, enviar_mensagem_abertura_corretora).start()
        BOT2_LOGGER.info("Agendado envio da mensagem de abertura da corretora para daqui a 1 minuto")
        return True
        
    except Exception as e:
        BOT2_LOGGER.error(f"Exceção ao enviar GIF promocional: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        return False

# Função para enviar a mensagem de abertura da corretora
def enviar_mensagem_abertura_corretora():
    """Envia a mensagem de abertura da corretora para o canal."""
    BOT2_LOGGER.info("Iniciando processo de envio da mensagem de abertura da corretora")
    
    try:
        # Formatar mensagem de abertura da corretora para português
        mensagem = formatar_mensagem_abertura_corretora("pt")
        BOT2_LOGGER.info("Mensagem de abertura da corretora formatada com sucesso")
        
        # Enviar para o canal em português
        chat_id = BOT2_CANAIS_CONFIG["pt"][0]
        BOT2_LOGGER.info(f"Tentando enviar mensagem de abertura da corretora para canal {chat_id}")
        
        bot2.send_message(
            chat_id=chat_id,
            text=mensagem,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        BOT2_LOGGER.info(f"Mensagem de abertura da corretora enviada com sucesso para o canal {chat_id}")
        return True
        
    except Exception as e:
        BOT2_LOGGER.error(f"Exceção ao enviar mensagem de abertura da corretora: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        return False

# Função para iniciar o bot e agendar os sinais
def iniciar_bot():
    """Inicia o bot e agenda o envio de sinais para cada hora."""
    BOT2_LOGGER.info("Iniciando bot...")
    
    # Agendar envio de sinais para minuto 13 de cada hora
    for hora in range(24):
        # Formato: HH:MM (exemplo: "09:13")
        horario = f"{hora:02d}:13"
        schedule.every().day.at(horario).do(enviar_sinal)
        BOT2_LOGGER.info(f"Agendado envio de sinal para {horario}")
    
    BOT2_LOGGER.info("Bot iniciado com sucesso. Executando loop de agendamento...")
    
    # Loop para verificar os agendamentos
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            BOT2_LOGGER.error(f"Erro no loop principal: {str(e)}")
            BOT2_LOGGER.error(traceback.format_exc())
            time.sleep(10)  # Esperar um pouco antes de continuar

# Executar o bot se este arquivo for executado diretamente
if __name__ == "__main__":
    try:
        BOT2_LOGGER.info("Iniciando execução do bot")
        iniciar_bot()
    except KeyboardInterrupt:
        BOT2_LOGGER.info("Bot interrompido pelo usuário")
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao iniciar o bot: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
