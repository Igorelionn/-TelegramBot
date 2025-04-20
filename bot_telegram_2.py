# -*- coding: utf-8 -*-
"""
Bot de envio de sinais para canais do Telegram
Por: Trending Brasil
Versão: 2.0
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

# Declarar funções que precisam ser globalmente acessíveis em qualquer escopo
# Estas declarações garantem que as funções sejam reconhecidas mesmo quando executadas em diferentes contextos
enviar_mensagem_participacao = None  # Será definida mais adiante no código
bot2_enviar_gif_promo = None  # Será definida mais adiante no código
bot2_enviar_mensagem_abertura_corretora = None  # Será definida mais adiante no código

# Constantes e configurações
# ... existing code ...

# Definição da variável global assets
assets = {}

# Definição de outras variáveis globais
ultimo_ativo = None
ultimo_signal = None

# Configuração do logger específico para o Bot 2
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
    "pt": [-1002424874613],  # Canal para mensagens em português
    "en": [-1002453956387],  # Canal para mensagens em inglês
    "es": [-1002446547846]   # Canal para mensagens em espanhol
}

# Configurações adicionais por idioma
CONFIGS_IDIOMA = {
    "pt": {
        "link_corretora": "https://trade.xxbroker.com/register?aff=741613&aff_model=revenue&afftrack=",
        "fuso_horario": "America/Sao_Paulo",  # Brasil (UTC-3)
    },
    "en": {
        "link_corretora": "https://trade.xxbroker.com/register?aff=741727&aff_model=revenue&afftrack=",
        "fuso_horario": "America/New_York",  # EUA (UTC-5 ou UTC-4 no horário de verão)
    },
    "es": {
        "link_corretora": "https://trade.xxbroker.com/register?aff=741726&aff_model=revenue&afftrack=",
        "fuso_horario": "Europe/Madrid",  # Espanha (UTC+1 ou UTC+2 no horário de verão)
    }
}

# Lista de IDs dos canais para facilitar iterao
BOT2_CHAT_IDS = []
for idioma, chats in BOT2_CANAIS_CONFIG.items():
    BOT2_CHAT_IDS.extend(chats)

# Log dos IDs dos canais para debug
BOT2_LOGGER.info(f"IDs dos canais configurados (BOT2_CHAT_IDS): {BOT2_CHAT_IDS}")

# Base URL do GitHub para os arquivos
GITHUB_BASE_URL = "https://raw.githubusercontent.com/IgorElion/-TelegramBot/main/"

# Dicionário de mapeamento de caminhos dos GIFs válidos
GIFS_VALIDOS = {
    "gif_especial_pt": "videos/gif_especial/pt/especial.gif",
    "pos_sinal_pt": "videos/pos_sinal/pt/padrao.gif",
    "pos_sinal_en": "videos/pos_sinal/en/padrao.gif",
    "pos_sinal_es": "videos/pos_sinal/es/padrao.gif",
    "promo_pt": "videos/promo/pt/promo.gif",
    "promo_en": "videos/promo/en/promo.gif",
    "promo_es": "videos/promo/es/promo.gif",
}

# URLs alternativas para GIFs (utilizadas apenas na verificação)
ALTERNATIVE_GIFS = {}

# URLs diretas para GIFs do Giphy
URLS_GIFS_DIRETAS = {
    "promo_pt": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZGhqMmNqOWFpbTQ2cjNxMzF1YncxcnAwdTFvN2o1NWRmc2dvYXZ6bCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/whPiIq21hxXuJn7WVX/giphy.gif",
    "promo_en": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZGhqMmNqOWFpbTQ2cjNxMzF1YncxcnAwdTFvN2o1NWRmc2dvYXZ6bCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/whPiIq21hxXuJn7WVX/giphy.gif",
    "promo_es": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZGhqMmNqOWFpbTQ2cjNxMzF1YncxcnAwdTFvN2o1NWRmc2dvYXZ6bCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/whPiIq21hxXuJn7WVX/giphy.gif",
    "pos_sinal_padrao": "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjZjb3hyMDVqOHAyb2xvZTgxZzVpb2ZscWE3M2RzOHY5Z3VzZTc2YiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/eWbGux0IXOygZ7m2Of/giphy.gif",
    "gif_especial_pt": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExN2tzdzB4bjNjaWo4bm9zdDR3d2g4bmQzeHRqcWx6MTQxYTA1cjRoeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/E2EknXAKA5ac8gKVxu/giphy.gif"
}

# ID para compatibilidade com cdigo existente
BOT2_CHAT_ID_CORRETO = BOT2_CHAT_IDS[0]  # Usar o primeiro canal como padro

# Limite de sinais por hora
BOT2_LIMITE_SINAIS_POR_HORA = 1

# Categorias de ativos
ATIVOS_CATEGORIAS = {
    "Binary": [],
    "Blitz": [],
    "Digital": [
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
        "US 500 (OTC)",
    ],
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
        "Sunday": ["00:00-23:59"],
    },
    "USOUSD_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-23:59"],
        "Thursday": ["00:00-06:00", "06:30-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "BTC/USD_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Google_OTC": {
        "Monday": ["00:00-15:30", "16:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-15:30", "16:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-15:30", "16:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "EUR/JPY_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-01:00", "01:15-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "ETH/USD_OTC": {
        "Monday": ["00:00-19:45", "20:15-23:59"],
        "Tuesday": ["00:00-19:45", "20:15-23:59"],
        "Wednesday": ["00:00-19:45", "20:15-23:59"],
        "Thursday": ["00:00-19:45", "20:15-23:59"],
        "Friday": ["00:00-19:45", "20:15-23:59"],
        "Saturday": ["00:00-19:45", "20:15-23:59"],
        "Sunday": ["00:00-19:45", "20:15-23:59"],
    },
    "MELANIA_COIN_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "EUR/GBP_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-01:00", "01:15-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "Apple_OTC": {
        "Monday": ["00:00-15:30", "16:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-15:30", "16:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-15:30", "16:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "Amazon_OTC": {
        "Monday": ["00:00-15:30", "16:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-15:30", "16:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-15:30", "16:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "TRUM_Coin_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Nike_Inc_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "DOGECOIN_OTC": {
        "Monday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Tuesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Wednesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Thursday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Friday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Saturday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Sunday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
    },
    "Tesla_OTC": {
        "Monday": ["00:00-15:30", "16:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-15:30", "16:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-15:30", "16:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "SOL/USD_OTC": {
        "Monday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Tuesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Wednesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Thursday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Friday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Saturday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Sunday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
    },
    "1000Sats_OTC": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "XAUUSD_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-23:59"],
        "Thursday": ["00:00-06:00", "06:30-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "McDonalds_Corporation_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Meta_OTC": {
        "Monday": ["00:00-15:30", "16:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-15:30", "16:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-15:30", "16:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "Coca_Cola_Company_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "CARDANO_OTC": {
        "Monday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Tuesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Wednesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Thursday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Friday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Saturday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Sunday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
    },
    "EUR/USD_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-01:00", "01:15-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "PEN/USD_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-00:45", "01:15-23:59"],
        "Wednesday": ["00:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "Bitcoin_Cash_OTC": {
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "AUD/CAD_OTC": {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-01:00", "01:15-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "Tesla/Ford_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "US_100_OTC": {
        "Monday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Tuesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Wednesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Thursday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
    },
    "FR_40_OTC": {  # Novo horrio para FR 40 (OTC)
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "AUS_200_OTC": {  # Atualizado com horrios especficos
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "US_500_OTC": {  # Atualizado com horrios especficos
        "Monday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Tuesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Wednesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Thursday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
    },
    "EU_50_OTC": {  # Novo ativo com horrios especficos
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Gold": {  # Novo ativo com horrios especficos
        "Monday": ["04:00-16:00"],
        "Tuesday": ["04:00-16:00"],
        "Wednesday": ["04:00-16:00"],
        "Thursday": ["04:00-16:00"],
        "Friday": ["04:00-16:00"],
        "Saturday": [],
        "Sunday": [],
    },
    "XAUUSD_OTC": {  # Atualizado com horrios especficos
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-23:59"],
        "Thursday": ["00:00-06:00", "06:10-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "US2000_OTC": {  # Novo ativo com horrios especficos
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Gala_OTC": {  # Novo horrio especfico para Gala (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Floki_OTC": {  # Novo horrio especfico para Floki (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Graph_OTC": {  # Novo horrio especfico para Graph (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Intel_IBM_OTC": {  # Novo horrio para Intel/IBM (OTC)
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Pyth_OTC": {  # Atualizado para Pyth (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "IOTA_OTC": {  # Atualizado para IOTA (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "DOGECOIN_OTC": {  # Atualizado para DOGECOIN (OTC)
        "Monday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Tuesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Wednesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Thursday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Friday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Saturday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Sunday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
    },
    "Sei_OTC": {  # Atualizado para Sei (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Decentraland_OTC": {  # Atualizado para Decentraland (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "PEN_USD_OTC": {  # Atualizado para PEN/USD (OTC)
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-00:45", "01:15-23:59"],
        "Wednesday": ["00:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "Sandbox_OTC": {  # Atualizado para Sandbox (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "TRON_USD_OTC": {  # Atualizado para TRON/USD (OTC)
        "Monday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Tuesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Wednesday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Thursday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Friday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Saturday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
        "Sunday": ["00:00-05:45", "06:15-17:45", "18:15-23:59"],
    },
    "Ripple_OTC": {  # Atualizado para Ripple (OTC)
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "NEAR_OTC": {  # Atualizado para NEAR (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Arbitrum_OTC": {  # Atualizado para Arbitrum (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Polygon_OTC": {  # Atualizado para Polygon (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "EOS_OTC": {  # Atualizado para EOS (OTC)
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "Alphabet_Microsoft_OTC": {  # Novo horrio para Alphabet/Microsoft (OTC)
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Jupiter_OTC": {  # Atualizado para Jupiter (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Dogwifhat_OTC": {  # Novo horrio para Dogwifhat (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Immutable_OTC": {  # Atualizado para Immutable (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Stacks_OTC": {  # Atualizado para Stacks (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Pepe_OTC": {  # Atualizado para Pepe (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "Ronin_OTC": {  # Atualizado para Ronin (OTC)
        "Monday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Tuesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Wednesday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Thursday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Friday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Saturday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
        "Sunday": ["00:00-05:05", "05:10-12:05", "12:10-23:59"],
    },
    "USD/CAD": {
        "Monday": ["03:00-15:00"],
        "Tuesday": ["03:00-15:00", "21:00-23:59"],
        "Wednesday": ["00:00-15:00"],
        "Thursday": ["03:00-15:00"],
        "Friday": ["03:00-15:00"],
        "Saturday": [],
        "Sunday": [],
    },
    "MELANIA_Coin_OTC": {  # J existe, mantendo a mesma configurao
    },
    "Gold/Silver_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Worldcoin_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "USD/THB_OTC": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "ETH/USD_OTC": {
        "Monday": ["00:00-19:45", "20:15-23:59"],
        "Tuesday": ["00:00-19:45", "20:15-23:59"],
        "Wednesday": ["00:00-19:45", "20:15-23:59"],
        "Thursday": ["00:00-19:45", "20:15-23:59"],
        "Friday": ["00:00-19:45", "20:15-23:59"],
        "Saturday": ["00:00-19:45", "20:15-23:59"],
        "Sunday": ["00:00-19:45", "20:15-23:59"],
    },
    "CHF/JPY_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Pepe_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "GBP/AUD_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "GBP/CHF": {
        "Monday": ["00:00-16:00"],
        "Tuesday": ["00:00-16:00"],
        "Wednesday": ["00:00-16:00"],
        "Thursday": ["00:00-16:00"],
        "Friday": ["00:00-14:00"],
                "Saturday": [],
        "Sunday": [],
    },
    "GBP/CAD_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "EUR/JPY_OTC": {
                "Monday": ["00:00-23:59"],
                "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-01:00", "01:15-23:59"],
                "Thursday": ["00:00-23:59"],
                "Friday": ["00:00-23:59"],
                "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
    },
    "AUD/CHF": {
        "Monday": ["00:00-16:00"],
        "Tuesday": ["00:00-16:00"],
        "Wednesday": ["00:00-16:00"],
        "Thursday": ["00:00-16:00"],
        "Friday": ["00:00-14:00"],
                "Saturday": [],
        "Sunday": [],
    },
    "GER_30_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "AUD/CHF_OTC": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "EUR/AUD": {
        "Monday": ["00:00-16:00"],
        "Tuesday": ["00:00-16:00"],
        "Wednesday": ["00:00-16:00"],
        "Thursday": ["00:00-16:00"],
        "Friday": ["00:00-14:00"],
                "Saturday": [],
        "Sunday": [],
    },
    "USD/CAD_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "BTC/USD": {
        "Monday": ["03:00-15:00"],
        "Tuesday": ["03:00-15:00"],
        "Wednesday": ["03:00-15:00"],
        "Thursday": ["03:00-15:00"],
        "Friday": ["03:00-15:00"],
        "Saturday": [],
        "Sunday": [],
    },
    "Amazon/Ebay_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Coca-Cola_Company_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "AIG_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Amazon/Alibaba_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "Bitcoin_Cash_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "USD Currency Index_OTC": {
        "Monday": ["00:00-10:00", "10:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-10:00", "10:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-10:00", "10:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-10:00", "10:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-10:00", "10:30-18:00"],
        "Saturday": [],
        "Sunday": ["19:00-23:59"],
    },
    "AUS_200_OTC": {  # J existe, mas atualizando para os novos horrios
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "JP_225_OTC": {
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "AUD/CAD_OTC": {  # J existe, atualizando a configurao
        "Monday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Tuesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Wednesday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Thursday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Friday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Saturday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
        "Sunday": ["00:00-03:00", "03:30-22:00", "22:30-23:59"],
    },
    "AUD/JPY_OTC": {
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
    },
    "US_500_OTC": {  # J existe, atualizando a configurao
        "Monday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Tuesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Wednesday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
        "Thursday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
                "Friday": ["00:00-23:59"],
                "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-11:30", "12:00-17:30", "18:00-23:59"],
    },
}

# URLs diretas para GIFs
URLS_GIFS_DIRETAS = {
    "promo_pt": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZGhqMmNqOWFpbTQ2cjNxMzF1YncxcnAwdTFvN2o1NWRmc2dvYXZ6bCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/whPiIq21hxXuJn7WVX/giphy.gif",
    "promo_en": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZGhqMmNqOWFpbTQ2cjNxMzF1YncxcnAwdTFvN2o1NWRmc2dvYXZ6bCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/whPiIq21hxXuJn7WVX/giphy.gif",
    "promo_es": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZGhqMmNqOWFpbTQ2cjNxMzF1YncxcnAwdTFvN2o1NWRmc2dvYXZ6bCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/whPiIq21hxXuJn7WVX/giphy.gif",
    "pos_sinal_padrao": "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjZjb3hyMDVqOHAyb2xvZTgxZzVpb2ZscWE3M2RzOHY5Z3VzZTc2YiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/eWbGux0IXOygZ7m2Of/giphy.gif",
    "gif_especial_pt": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExN2tzdzB4bjNjaWo4bm9zdDR3d2g4bmQzeHRqcWx6MTQxYTA1cjRoeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/E2EknXAKA5ac8gKVxu/giphy.gif"
}

# Adicionar variável global para controlar mensagem de perda enviada por dia
mensagem_perda_enviada_hoje = False

# Variáveis para controle de sinais
ultimo_sinal_enviado = None

# Variáveis globais de controle
bot2_contador_sinais = 0
ultimo_sinal_enviado = None
bot2_sinais_agendados = False
thread_sequencia_ativa = None
thread_gif_pos_sinal_ativa = None
mensagem_perda_enviada_hoje = False

# Iniciar uma variável de semáforo para controlar acesso concorrente
sequencia_multiplo_tres_lock = threading.Lock()

# Adicionar variável para rastrear a última data em que a mensagem de perda foi enviada
ultima_data_mensagem_perda = None

# Links de afiliados para cada idioma
LINKS_CORRETORA = {
    "pt": "https://trade.xxbroker.com/register?aff=741613&aff_model=revenue&afftrack=",
    "en": "https://trade.xxbroker.com/register?aff=741727&aff_model=revenue&afftrack=",
    "es": "https://trade.xxbroker.com/register?aff=741726&aff_model=revenue&afftrack="
}

# Mensagem de perda para ser enviada uma vez ao dia
def get_mensagem_perda(idioma):
    """Retorna a mensagem de perda formatada para o idioma especificado"""
    link = LINKS_CORRETORA.get(idioma, LINKS_CORRETORA["pt"])  # Usar link PT como fallback
    
    if idioma == "pt":
        return f"""⚠️ GERENCIAMENTO DE BANCA ⚠️

Sinal anterior não alcançou o resultado esperado!
Lembre-se de seguir seu gerenciamento para recuperar na próxima entrada.

<a href="{link}">Continue operando 📈</a>"""
    elif idioma == "en":
        return f"""⚠️ BANKROLL MANAGEMENT ⚠️

Previous signal did not achieve the expected result!
Remember to follow your management to recover in the next entry.

<a href="{link}">Continue trading 📈</a>"""
    elif idioma == "es":
        return f"""⚠️ GESTIÓN DE BANCA ⚠️

¡La señal anterior no alcanzó el resultado esperado!
Recuerde seguir su gestión para recuperarse en la próxima entrada.

<a href="{link}">Continúe operando 📈</a>"""
    else:
        # Fallback para português
        return f"""⚠️ GERENCIAMENTO DE BANCA ⚠️

Sinal anterior não alcançou o resultado esperado!
Lembre-se de seguir seu gerenciamento para recuperar na próxima entrada.

<a href="{link}">Continue operando 📈</a>"""

def verificar_mensagem_perda_hoje():
    """
    Verifica se a mensagem de perda já foi enviada hoje.
    
    Returns:
        bool: True se a mensagem já foi enviada hoje, False caso contrário
    """
    global ultima_data_mensagem_perda
    
    # Obter a data atual em Brasília
    agora = bot2_obter_hora_brasilia()
    data_atual = agora.strftime("%Y-%m-%d")
    
    # Se nunca foi enviada ou foi enviada em outro dia, deve enviar hoje
    if ultima_data_mensagem_perda is None or ultima_data_mensagem_perda != data_atual:
        return False
    
    # Se já foi enviada hoje, não enviar novamente
    return True

def enviar_mensagem_perda(signal=None):
    """
    Envia uma mensagem de perda para todos os canais configurados.
    
    Args:
        signal: O sinal que foi enviado anteriormente. Se None, usa o último sinal enviado.
    
    Returns:
        bool: True se pelo menos uma mensagem foi enviada com sucesso, False caso contrário.
    """
    global BOT2_LOGGER, BOT2_CANAIS_CONFIG, BOT2_TOKEN, ultimo_sinal_enviado, ultima_data_mensagem_perda
    
    try:
        # Registrar que a mensagem de perda foi enviada hoje
        agora = bot2_obter_hora_brasilia()
        data_atual = agora.strftime("%Y-%m-%d")
        ultima_data_mensagem_perda = data_atual
        
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[PERDA][{horario_atual}] 🔄 Iniciando envio de mensagem de perda (uma vez ao dia)")
        
        # Se não foi fornecido um sinal, usar o último sinal enviado
        if not signal and ultimo_sinal_enviado:
            signal = ultimo_sinal_enviado
            BOT2_LOGGER.info(f"[PERDA][{horario_atual}] ℹ️ Usando último sinal enviado: {signal['ativo']} {signal['direcao']}")
        
        if not signal:
            BOT2_LOGGER.error(f"[PERDA][{horario_atual}] ❌ Nenhum sinal fornecido e nenhum sinal anterior disponível")
            return False
        
        # Verificar conexão com API antes de enviar
        BOT2_LOGGER.info(f"[PERDA][{horario_atual}] 🔄 Verificando conexão com API do Telegram...")
        try:
            url_verificacao = f"https://api.telegram.org/bot{BOT2_TOKEN}/getMe"
            resposta = requests.get(url_verificacao, timeout=10)
            if resposta.status_code == 200:
                BOT2_LOGGER.info(f"[PERDA][{horario_atual}] ✅ Conexão com API OK!")
            else:
                BOT2_LOGGER.warning(f"[PERDA][{horario_atual}] ⚠️ API do Telegram respondeu com código {resposta.status_code}")
        except Exception as e:
            BOT2_LOGGER.warning(f"[PERDA][{horario_atual}] ⚠️ Erro ao verificar conexão com API: {str(e)}")
        
        # Lista para armazenar resultado dos envios
        resultados_envio = []
        
        # Contadores para estatísticas
        total_canais = sum(len(chats) for chats in BOT2_CANAIS_CONFIG.items())
        enviados_com_sucesso = 0
        
        BOT2_LOGGER.info(f"[PERDA][{horario_atual}] 📊 Total de canais configurados: {total_canais}")
        
        # Para cada idioma, enviar a mensagem de perda apropriada
        for idioma, chats in BOT2_CANAIS_CONFIG.items():
            if not chats:
                BOT2_LOGGER.info(f"[PERDA][{horario_atual}] ℹ️ Nenhum chat configurado para idioma {idioma}, pulando")
                continue
            
            BOT2_LOGGER.info(f"[PERDA][{horario_atual}] 🌐 Processando idioma: {idioma} ({len(chats)} canais)")
            
            # Obter a mensagem formatada para o idioma
            mensagem = get_mensagem_perda(idioma)
            
            # Enviar para cada chat configurado neste idioma
            for chat_id in chats:
                try:
                    # Preparar a URL para o método sendMessage da API do Telegram
                    url = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
                    
                    # Montar o payload da requisição
                    payload = {
                        "chat_id": chat_id,
                        "text": mensagem,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                        "disable_notification": False
                    }
                    
                    BOT2_LOGGER.info(f"[PERDA][{horario_atual}] 🚀 Enviando mensagem de perda para chat_id: {chat_id} (idioma: {idioma})")
                    
                    # Enviar a requisição para a API
                    inicio_envio = time.time()
                    resposta = requests.post(url, json=payload, timeout=15)
                    tempo_resposta = (time.time() - inicio_envio) * 1000  # em milissegundos
                    
                    # Verificar o resultado da requisição
                    if resposta.status_code == 200:
                        BOT2_LOGGER.info(f"[PERDA][{horario_atual}] ✅ Mensagem enviada com sucesso para {chat_id} (tempo: {tempo_resposta:.1f}ms)")
                        resultados_envio.append(True)
                        enviados_com_sucesso += 1
                    else:
                        BOT2_LOGGER.error(f"[PERDA][{horario_atual}] ❌ Falha ao enviar mensagem para {chat_id}: {resposta.status_code} - {resposta.text}")
                        resultados_envio.append(False)
                        
                        # Se falhar, tentar novamente uma vez
                        BOT2_LOGGER.info(f"[PERDA][{horario_atual}] 🔄 Tentando novamente para {chat_id}...")
                        try:
                            resposta_retry = requests.post(url, json=payload, timeout=15)
                            if resposta_retry.status_code == 200:
                                BOT2_LOGGER.info(f"[PERDA][{horario_atual}] ✅ Mensagem enviada com sucesso na segunda tentativa para {chat_id}")
                                resultados_envio.append(True)
                                enviados_com_sucesso += 1
                            else:
                                BOT2_LOGGER.error(f"[PERDA][{horario_atual}] ❌ Falha na segunda tentativa: {resposta_retry.status_code}")
                        except Exception as e:
                            BOT2_LOGGER.error(f"[PERDA][{horario_atual}] ❌ Erro na segunda tentativa: {str(e)}")
                
                except Exception as e:
                    BOT2_LOGGER.error(f"[PERDA][{horario_atual}] ❌ Exceção ao enviar mensagem para {chat_id}: {str(e)}")
                    BOT2_LOGGER.error(f"[PERDA][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
                    resultados_envio.append(False)
        
        # Calcular estatísticas finais
        if total_canais > 0:
            taxa_sucesso = (enviados_com_sucesso / total_canais) * 100
            BOT2_LOGGER.info(f"[PERDA][{horario_atual}] 📊 RESUMO: {enviados_com_sucesso}/{total_canais} mensagens enviadas com sucesso ({taxa_sucesso:.1f}%)")
        else:
            BOT2_LOGGER.warning(f"[PERDA][{horario_atual}] ⚠️ Nenhum canal configurado para envio de mensagens!")
        
        # Retornar True se pelo menos uma mensagem foi enviada com sucesso
        envio_bem_sucedido = any(resultados_envio)
        
        if envio_bem_sucedido:
            BOT2_LOGGER.info(f"[PERDA][{horario_atual}] ✅ Envio de mensagem de perda concluído com sucesso")
        else:
            BOT2_LOGGER.error(f"[PERDA][{horario_atual}] ❌ Falha em todos os envios de mensagem de perda")
        
        return envio_bem_sucedido
    
    except Exception as e:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[PERDA][{horario_atual}] ❌ Erro crítico ao enviar mensagem de perda: {str(e)}")
        BOT2_LOGGER.error(f"[PERDA][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
        return False

def adicionar_blitz(lista_ativos):
    for ativo in lista_ativos:
        if ativo in HORARIOS_PADRAO:
            assets[ativo] = HORARIOS_PADRAO[ativo]
        else:
            assets[ativo] = {
                "Monday": ["00:00-23:59"],
                "Tuesday": ["00:00-23:59"],
                "Wednesday": ["00:00-23:59"],
                "Thursday": ["00:00-23:59"],
                "Friday": ["00:00-23:59"],
                "Saturday": ["00:00-23:59"],
                "Sunday": ["00:00-23:59"],
            }
        ATIVOS_CATEGORIAS[ativo] = "Blitz"


# Exemplos de como adicionar ativos (comentado para referncia)
# adicionar_forex(["EUR/USD", "GBP/USD"])
# adicionar_crypto(["BTC/USD", "ETH/USD"])
# adicionar_stocks(["AAPL", "MSFT"])

# Funo para parsear os horrios


@lru_cache(maxsize=128)
def parse_time_range(time_str):
    """
    Converte uma string de intervalo de tempo (e.g. "09:30-16:00") para um par de time objects.
    """
    start_str, end_str = time_str.split("-")
    start_time = datetime.strptime(start_str, "%H:%M").time()
    end_time = datetime.strptime(end_str, "%H:%M").time()
    return start_time, end_time


# Funo para verificar disponibilidade de ativos


def is_asset_available(asset, current_time=None, current_day=None):
    """
    Verifica se um ativo está disponível para negociação no horário especificado.
    
    Args:
        asset (str): Nome do ativo a ser verificado
        current_time (datetime ou str): Horário atual (formato datetime ou string HH:MM)
        current_day (str): Dia da semana atual (em inglês: Monday, Tuesday, etc.)
    
    Returns:
        bool: True se o ativo estiver disponível, False caso contrário
    """
    global BOT2_LOGGER, HORARIOS_PADRAO
    
    try:
        # Se o horário e o dia não foram fornecidos, usar o horário atual de Brasília
        if current_time is None:
            agora = bot2_obter_hora_brasilia()
            current_time = agora
            current_day = agora.strftime("%A")
        
        # Verificar se current_time é uma string ou objeto datetime
        if isinstance(current_time, str):
            # Se for string, converter para objeto time
            current_time_obj = datetime.strptime(current_time, "%H:%M").time()
        else:
            # Se for datetime, extrair o componente time
            current_time_obj = current_time.time()
        
        # Mapeamento de nomes de ativos para as chaves em HORARIOS_PADRAO
        mapeamento_chaves = {
            "Gold/Silver (OTC)": "Gold/Silver_OTC",
            "Worldcoin (OTC)": "Worldcoin_OTC",
            "USD/THB (OTC)": "USD/THB_OTC",
            "ETH/USD (OTC)": "ETH/USD_OTC",
            "CHF/JPY (OTC)": "CHF/JPY_OTC",
            "Pepe (OTC)": "Pepe_OTC",
            "GBP/AUD (OTC)": "GBP/AUD_OTC",
            "GBP/CHF": "GBP/CHF",
            "GBP/CAD (OTC)": "GBP/CAD_OTC",
            "EUR/JPY (OTC)": "EUR/JPY_OTC",
            "AUD/CHF": "AUD/CHF",
            "GER 30 (OTC)": "GER_30_OTC",
            "AUD/CHF (OTC)": "AUD/CHF_OTC",
            "EUR/AUD": "EUR/AUD",
            "USD/CAD (OTC)": "USD/CAD_OTC",
            "BTC/USD": "BTC/USD",
            "Amazon/Ebay (OTC)": "Amazon/Ebay_OTC",
            "Coca-Cola Company (OTC)": "Coca-Cola_Company_OTC",
            "AIG (OTC)": "AIG_OTC",
            "Amazon/Alibaba (OTC)": "Amazon/Alibaba_OTC",
            "Bitcoin Cash (OTC)": "Bitcoin_Cash_OTC",
            "AUD/USD": "AUD/USD",
            "DASH (OTC)": "DASH_OTC",
            "BTC/USD (OTC)": "BTC/USD_OTC",
            "SP 35 (OTC)": "SP_35_OTC",
            "TRUMP Coin (OTC)": "TRUM_Coin_OTC",
            "US 100 (OTC)": "US_100_OTC",
            "EUR/CAD (OTC)": "EUR/CAD_OTC",
            "HK 33 (OTC)": "HK_33_OTC",
            "Alphabet/Microsoft (OTC)": "Alphabet_Microsoft_OTC",
            "1000Sats (OTC)": "1000Sats_OTC",
            "USD/ZAR (OTC)": "USD/ZAR_OTC",
            "Litecoin (OTC)": "Litecoin_OTC",
            "Hamster Kombat (OTC)": "Hamster_Kombat_OTC",
            "USD Currency Index (OTC)": "USD Currency Index_OTC",
            "AUS 200 (OTC)": "AUS_200_OTC",
            "USD/CAD": "USD/CAD",
            "MELANIA Coin (OTC)": "MELANIA_Coin_OTC",
            "JP 225 (OTC)": "JP_225_OTC",
            "AUD/CAD (OTC)": "AUD/CAD_OTC",
            "AUD/JPY (OTC)": "AUD/JPY_OTC",
            "US 500 (OTC)": "US_500_OTC",
        }
        
        # Obter a chave correta para o ativo
        if asset in mapeamento_chaves:
            asset_key = mapeamento_chaves[asset]
        else:
            # Normalização alternativa (fallback)
            asset_key = asset.replace(" ", "_").replace("/", "_").replace("(", "_").replace(")", "_")
        
        # Verificar se o ativo existe no dicionário de horários
        if asset_key not in HORARIOS_PADRAO:
            BOT2_LOGGER.warning(f"Ativo {asset} não encontrado na configuração de horários")
            return False
        
        # Verificar se o dia atual está na configuração do ativo
        if current_day not in HORARIOS_PADRAO[asset_key]:
            BOT2_LOGGER.debug(f"Dia {current_day} não configurado para o ativo {asset}")
            return False
        
        # Obter intervalos de horário para o dia atual
        horarios_dia = HORARIOS_PADRAO[asset_key][current_day]
        
        # Se a lista de horários estiver vazia, o ativo não está disponível nesse dia
        if not horarios_dia:
            return False
        
        # Verificar se o horário atual está dentro de algum dos intervalos configurados
        for intervalo in horarios_dia:
            intervalo_inicio, intervalo_fim = parse_time_range(intervalo)
            
            # Agora, comparar objetos time
            if intervalo_inicio <= current_time_obj <= intervalo_fim:
                return True
        
        # Se chegou até aqui, não está em nenhum intervalo
        return False
    
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao verificar disponibilidade do ativo {asset}: {str(e)}")
        BOT2_LOGGER.error(f"Detalhes: {traceback.format_exc()}")
        return False


def bot2_verificar_horario_ativo(ativo, categoria):
    """
    Verifica se um ativo está disponível no horário atual.

    Args:
        ativo (str): O nome do ativo a verificar
        categoria (str): A categoria do ativo (Binary, Blitz, Digital)

    Returns:
        bool: True se o ativo estiver disponível, False caso contrário
    """
    # Obter o horário atual em Brasília
    agora = bot2_obter_hora_brasilia()
    dia_semana = agora.strftime("%A")

    # Verificar disponibilidade usando a função is_asset_available
    return is_asset_available(ativo, agora, dia_semana)


# Funo para obter hora no fuso horário de Brasília (específica para Bot 2)


def bot2_obter_hora_brasilia():
    """
    Retorna a hora atual no fuso horário de Brasília.
    """
    fuso_horario_brasilia = pytz.timezone("America/Sao_Paulo")
    return datetime.now(fuso_horario_brasilia)


def bot2_verificar_disponibilidade():
    """
    Verifica quais ativos estão disponíveis para negociação no momento atual.
    
    Returns:
        list: Lista de nomes dos ativos disponíveis
    """
    global BOT2_LOGGER, ATIVOS_CATEGORIAS
    
    try:
        # Obter hora atual em Brasília
        agora = bot2_obter_hora_brasilia()
        
        # Formar strings de hora e dia para logs e verificação
        hora_atual = agora.strftime("%H:%M")
        dia_atual = agora.strftime("%A")
        data_hora_str = agora.strftime("%Y-%m-%d %H:%M:%S")
        
        BOT2_LOGGER.info(f"📆 Data/Hora atual: {data_hora_str} ({dia_atual})")
        BOT2_LOGGER.info(f"Verificando disponibilidade para o dia {dia_atual} às {hora_atual}")
        
        # Inicializar lista de ativos disponíveis
        ativos_disponiveis = []
        
        # Percorrer a categoria "Digital" para verificar quais ativos estão disponíveis
        ativos_digital = ATIVOS_CATEGORIAS.get("Digital", [])
        BOT2_LOGGER.info(f"Total de ativos na categoria Digital: {len(ativos_digital)}")
        
        if not ativos_digital:
            BOT2_LOGGER.warning("Nenhum ativo encontrado na categoria Digital")
            return []
            
        # Verificar disponibilidade de cada ativo
        for ativo in ativos_digital:
            try:
                # Passar objeto datetime para a função de verificação
                if is_asset_available(ativo, agora, dia_atual):
                    ativos_disponiveis.append(ativo)
            except Exception as e:
                BOT2_LOGGER.error(f"Erro ao verificar disponibilidade do ativo {ativo}: {str(e)}")
        
        # Logs informativos sobre o resultado da verificação
        total_disponiveis = len(ativos_disponiveis)
        percentual = (total_disponiveis / len(ativos_digital)) * 100 if ativos_digital else 0
        
        BOT2_LOGGER.info(f"✅ Ativos disponíveis: {total_disponiveis}/{len(ativos_digital)} ({percentual:.1f}%)")
        if ativos_disponiveis:
            BOT2_LOGGER.info(f"📋 Lista de ativos disponíveis: {', '.join(ativos_disponiveis)}")
        else:
            BOT2_LOGGER.warning("⚠️ Nenhum ativo disponível no momento atual!")
            
        return ativos_disponiveis
        
    except Exception as e:
        BOT2_LOGGER.error(f"❌ Erro ao verificar disponibilidade dos ativos: {str(e)}")
        BOT2_LOGGER.error(f"🔍 Detalhes: {traceback.format_exc()}")
        return []


def bot2_gerar_sinal_aleatorio():
    """Gera um sinal de trading aleatório com base nos ativos disponíveis no momento."""
    global BOT2_LOGGER, ATIVOS_CATEGORIAS
    
    try:
        # Obter a hora atual de Brasília para logs detalhados
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        
        BOT2_LOGGER.info(f"[GERADOR][{horario_atual}] 🎲 Iniciando geração de sinal aleatório...")
        
        # Verificar ativos disponíveis em tempo real (sempre, antes de cada sinal)
        BOT2_LOGGER.info(f"[GERADOR][{horario_atual}] 🔍 Verificando disponibilidade atual dos ativos...")
        ativos_disponiveis = bot2_verificar_disponibilidade()
        
        # Se não houver ativos disponíveis diretamente da função, verificar a lista armazenada
        if not ativos_disponiveis and "Digital_Disponiveis" in ATIVOS_CATEGORIAS:
            ativos_disponiveis = ATIVOS_CATEGORIAS["Digital_Disponiveis"]
            BOT2_LOGGER.info(f"[GERADOR][{horario_atual}] ℹ️ Usando lista de ativos pré-verificados: {len(ativos_disponiveis)} ativos")
        
        if not ativos_disponiveis:
            BOT2_LOGGER.warning(f"[GERADOR][{horario_atual}] ⚠️ ALERTA: Nenhum ativo disponível neste momento!")
            BOT2_LOGGER.info(f"[GERADOR][{horario_atual}] 🔄 Tentando usar lista completa de ativos como fallback...")
            
            # Como último recurso, usar todos os ativos da categoria Digital
            ativos_disponiveis = ATIVOS_CATEGORIAS["Digital"]
            
            if not ativos_disponiveis:
                BOT2_LOGGER.error(f"[GERADOR][{horario_atual}] ❌ Falha crítica: Nenhum ativo configurado na categoria Digital!")
                return None
                
            BOT2_LOGGER.warning(f"[GERADOR][{horario_atual}] ⚠️ Usando lista completa como fallback: {len(ativos_disponiveis)} ativos")
        
        # Comparar com o total de ativos configurados
        total_ativos = len(ATIVOS_CATEGORIAS["Digital"])
        percentual_disponivel = (len(ativos_disponiveis) / total_ativos) * 100
        
        BOT2_LOGGER.info(f"[GERADOR][{horario_atual}] 📊 Ativos disponíveis: {len(ativos_disponiveis)}/{total_ativos} ({percentual_disponivel:.1f}%)")
        
        # Escolher aleatoriamente um ativo dos disponíveis
        ativo = random.choice(ativos_disponiveis)
        BOT2_LOGGER.info(f"[GERADOR][{horario_atual}] 🎯 Ativo selecionado: {ativo}")
        
        # Verificar se o ativo está realmente disponível neste horário específico
        if not bot2_verificar_horario_ativo(ativo, "Digital"):
            BOT2_LOGGER.warning(f"[GERADOR][{horario_atual}] ⚠️ Segundo verificação adicional, o ativo {ativo} não está disponível agora")
            BOT2_LOGGER.warning(f"[GERADOR][{horario_atual}] ⚠️ Usando mesmo assim, pois foi selecionado pela verificação principal")
        
        # Escolher aleatoriamente a direção (CALL ou PUT)
        direcao = random.choice(["CALL", "PUT"])
        BOT2_LOGGER.info(f"[GERADOR][{horario_atual}] 🎯 Direção selecionada: {direcao}")
        
        # Tempo de expiração fixo de 5 minutos
        tempo_expiracao_minutos = 5
        
        # Calcular o horário exato de expiração
        expiracao_time = agora + timedelta(minutes=tempo_expiracao_minutos)
        expiracao_texto = f"🕒 Expiração: {tempo_expiracao_minutos} minutos ({expiracao_time.strftime('%H:%M')})"
        
        BOT2_LOGGER.info(f"[GERADOR][{horario_atual}] ⏱️ Tempo de expiração: {tempo_expiracao_minutos} minutos (até {expiracao_time.strftime('%H:%M:%S')})")
        
        # Categoria é sempre "Digital"
        categoria = "Digital"
        
        # Registrar sinal gerado nos logs
        BOT2_LOGGER.info(f"[GERADOR][{horario_atual}] ✅ Sinal gerado com sucesso: {ativo} {direcao} {tempo_expiracao_minutos}min")
        
        # Retornar o sinal como um dicionário
        return {
            "ativo": ativo,
            "direcao": direcao,
            "tempo_expiracao_minutos": tempo_expiracao_minutos,
            "expiracao_texto": expiracao_texto,
            "categoria": categoria,
        }
    
    except Exception as e:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[GERADOR][{horario_atual}] ❌ Erro ao gerar sinal aleatório: {str(e)}")
        BOT2_LOGGER.error(f"[GERADOR][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
        return None


# Funo para obter hora no fuso horário específico (a partir da hora de
# Brasília)


def bot2_converter_fuso_horario(hora_brasilia, fuso_destino):
    """
    Converte uma hora do fuso horário de Brasília para o fuso horário de destino.
    
    Args:
        hora_brasilia (datetime): Hora no fuso horário de Brasília
        fuso_destino (str): Nome do fuso horário de destino (ex: 'America/New_York')
        
    Returns:
        datetime: Hora convertida para o fuso horário de destino
    """
    # Garantir que hora_brasilia tenha informações de fuso horário
    fuso_horario_brasilia = pytz.timezone("America/Sao_Paulo")
    
    # Se a hora não tiver informação de fuso, adicionar
    if hora_brasilia.tzinfo is None:
        hora_brasilia = fuso_horario_brasilia.localize(hora_brasilia)
    
    # Converter para o fuso horário de destino
    fuso_destino_tz = pytz.timezone(fuso_destino)
    hora_destino = hora_brasilia.astimezone(fuso_destino_tz)
    
    return hora_destino


def bot2_formatar_mensagem(sinal, hora_formatada, idioma):
    """
    Formata a mensagem de sinal para envio, conforme o idioma especificado.
    """
    global BOT2_LOGGER, CONFIGS_IDIOMA
    
    try:
        BOT2_LOGGER.info(
            f"Formatando mensagem com: ativo={sinal['ativo']}, direção={sinal['direcao']}, "
            + f"categoria={sinal['categoria']}, tempo={sinal['tempo_expiracao_minutos']}, idioma={idioma}"
        )
        
        # Obter configuração para o idioma
        config_idioma = CONFIGS_IDIOMA.get(idioma, CONFIGS_IDIOMA["pt"])
        
        # Obter informações do sinal
        ativo = sinal["ativo"]
        direcao = sinal["direcao"]
        categoria = sinal["categoria"]
        tempo_expiracao_minutos = sinal["tempo_expiracao_minutos"]
        
        # Definir o fuso horário de acordo com o idioma
        fuso_horario = config_idioma.get("fuso_horario", "America/Sao_Paulo")
        
        # Obter link da corretora específico para o idioma
        link_corretora = config_idioma.get("link_corretora", "")
        
        # Tratar nome do ativo para exibição
        nome_ativo_exibicao = ativo.replace("_", " ")
        # Ajustar a parte OTC para não ter parênteses duplicados
        if "OTC" in nome_ativo_exibicao:
            nome_ativo_exibicao = nome_ativo_exibicao.replace("OTC", "(OTC)")
            # Garantir que não temos parênteses duplicados
            nome_ativo_exibicao = nome_ativo_exibicao.replace("((OTC))", "(OTC)")
        
        # Determinar emoji baseado na direção
        emoji = "🟩" if direcao.upper() == "CALL" else "🟥"
        
        # Definir texto da direção para cada idioma
        if direcao.upper() == "CALL":
            action_pt = "COMPRA"
            action_en = "BUY"
            action_es = "COMPRA"
        else:
            action_pt = "VENDA"
            action_en = "SELL"
            action_es = "VENTA"
        
        # Ajustar o formato da hora dependendo do que foi recebido
        if len(hora_formatada) <= 5:  # Formato HH:MM
            hora_formatada = hora_formatada + ":00"  # Adicionar segundos como 00
            
        # Converter a hora de entrada para o formato correto
        try:
            hora_entrada = datetime.strptime(hora_formatada, "%H:%M:%S")
        except ValueError:
            try:
                # Tentar formato alternativo se o primeiro falhar
                hora_entrada = datetime.strptime(hora_formatada, "%H:%M")
            except ValueError:
                BOT2_LOGGER.error(f"Formato de hora inválido: {hora_formatada}. Usando hora atual.")
                # Usar a hora atual como fallback
                hora_entrada = datetime.now().replace(microsecond=0)

        # Ajustar para o horário atual se hora_entrada for apenas um time, não um datetime
        if isinstance(hora_entrada, datetime_time):
            agora = datetime.now()
            hora_entrada = datetime(
                agora.year, agora.month, agora.day, 
                hora_entrada.hour, hora_entrada.minute, hora_entrada.second
            )
        
        # MODIFICAÇÃO: Ajustar o horário para 2 minutos à frente para ser exibido ao lado de COMPRA/VENDA
        hora_exibicao = hora_entrada + timedelta(minutes=2)
        hora_exibicao_formatada = hora_exibicao.strftime("%H:%M")
        
        # Calcular as horas de expiração e gales com base na hora_exibicao
        hora_expiracao = hora_exibicao + timedelta(minutes=tempo_expiracao_minutos)
        hora_gale1 = hora_expiracao + timedelta(minutes=5)
        hora_gale2 = hora_gale1 + timedelta(minutes=5)
        hora_gale3 = hora_gale2 + timedelta(minutes=5)
        
        # Formatar as horas para exibição sem os segundos
        hora_entrada_formatada = hora_entrada.strftime("%H:%M")
        hora_expiracao_formatada = hora_expiracao.strftime("%H:%M")
        hora_gale1_formatada = hora_gale1.strftime("%H:%M")
        hora_gale2_formatada = hora_gale2.strftime("%H:%M")
        hora_gale3_formatada = hora_gale3.strftime("%H:%M")
        
        # Converter as horas para o fuso horário específico do idioma
        if fuso_horario != "America/Sao_Paulo":
            # Converter para o fuso horário do idioma
            hora_exibicao_formatada = bot2_converter_fuso_horario(
                hora_exibicao, fuso_horario
            ).strftime("%H:%M")
            hora_entrada_formatada = bot2_converter_fuso_horario(
                hora_entrada, fuso_horario
            ).strftime("%H:%M")
            hora_expiracao_formatada = bot2_converter_fuso_horario(
                hora_expiracao, fuso_horario
            ).strftime("%H:%M")
            hora_gale1_formatada = bot2_converter_fuso_horario(
                hora_gale1, fuso_horario
            ).strftime("%H:%M")
            hora_gale2_formatada = bot2_converter_fuso_horario(
                hora_gale2, fuso_horario
            ).strftime("%H:%M")
            hora_gale3_formatada = bot2_converter_fuso_horario(
                hora_gale3, fuso_horario
            ).strftime("%H:%M")
        
        # Registrar os horários convertidos para o log
        BOT2_LOGGER.info(
            f"Horários convertidos para fuso {fuso_horario}: Exibição={hora_exibicao_formatada}, Entrada={hora_entrada_formatada}, "
            + f"Expiração={hora_expiracao_formatada}, Gale1={hora_gale1_formatada}, "
            + f"Gale2={hora_gale2_formatada}, Gale3={hora_gale3_formatada}"
        )

        # Formatação para singular ou plural de "minuto" baseado no tempo de
        # expiração
        texto_minutos_pt = "minuto" if tempo_expiracao_minutos == 1 else "minutos"
        texto_minutos_en = "minute" if tempo_expiracao_minutos == 1 else "minutes"
        texto_minutos_es = "minuto" if tempo_expiracao_minutos == 1 else "minutos"

        # Configurar links baseados no idioma
        if idioma == "pt":
            # Não sobrescrever link_corretora se já estiver definido
            if not link_corretora:
                link_corretora = (
                    "https://trade.xxbroker.com/register?aff=741613&aff_model=revenue&afftrack="
                )
            link_video = "https://t.me/trendingbrazil/215"
            texto_corretora = "Clique para abrir a corretora"
            texto_video = "Clique aqui"
            texto_tempo = "TEMPO PARA"
            texto_gale1 = "1º GALE — TEMPO PARA"
            texto_gale2 = "2º GALE TEMPO PARA"
            texto_gale3 = "3º GALE TEMPO PARA"
        elif idioma == "en":
            # Não sobrescrever link_corretora se já estiver definido
            if not link_corretora:
                link_corretora = (
                    "https://trade.xxbroker.com/register?aff=741727&aff_model=revenue&afftrack="
                )
            link_video = "https://t.me/trendingenglish/226"
            texto_corretora = "Click to open broker"
            texto_video = "Click here"
            texto_tempo = "TIME UNTIL"
            texto_gale1 = "1st GALE — TIME UNTIL"
            texto_gale2 = "2nd GALE TIME UNTIL"
            texto_gale3 = "3rd GALE TIME UNTIL"
        else:  # espanhol
            # Não sobrescrever link_corretora se já estiver definido
            if not link_corretora:
                link_corretora = (
                    "https://trade.xxbroker.com/register?aff=741726&aff_model=revenue&afftrack="
                )
            link_video = "https://t.me/trendingespanish/212"
            texto_corretora = "Haga clic para abrir el corredor"
            texto_video = "Haga clic aquí"
            texto_tempo = "TIEMPO HASTA"
            texto_gale1 = "1º GALE — TIEMPO HASTA"
            texto_gale2 = "2º GALE TIEMPO HASTA"
            texto_gale3 = "3º GALE TIEMPO HASTA"
        
        # Determinar a categoria de exibição (Binary, Digital)
        categoria_exibicao = "Binary"
        if isinstance(categoria, list) and len(categoria) > 0:
            # Escolher apenas um item da lista para exibir (o primeiro)
            categoria_exibicao = categoria[0]
        else:
            categoria_exibicao = categoria  # Usar o valor de categoria diretamente

        # Mensagem em PT
        mensagem_pt = (
            f"💰{tempo_expiracao_minutos} {texto_minutos_pt} de expiração\n"
            f"{nome_ativo_exibicao};{hora_exibicao_formatada};{action_pt} {emoji} {categoria_exibicao}\n\n"
                f"🕐{texto_tempo} {hora_expiracao_formatada}\n\n"
                f"{texto_gale1} {hora_gale1_formatada}\n"
                f"{texto_gale2} {hora_gale2_formatada}\n"
                f"{texto_gale3} {hora_gale3_formatada}\n\n"
            f'📲 <a href="{link_corretora}" title="">Clique para abrir a corretora</a>\n'
            f'🙋‍♂️ Não sabe operar ainda? <a href="{link_video}" title="">Clique aqui</a>'
        )
                
        # Mensagem em EN
        mensagem_en = (
            f"💰{tempo_expiracao_minutos} {texto_minutos_en} expiration\n"
            f"{nome_ativo_exibicao};{hora_exibicao_formatada};{action_en} {emoji} {categoria_exibicao}\n\n"
                f"🕐{texto_tempo} {hora_expiracao_formatada}\n\n"
                f"{texto_gale1} {hora_gale1_formatada}\n"
                f"{texto_gale2} {hora_gale2_formatada}\n"
                f"{texto_gale3} {hora_gale3_formatada}\n\n"
            f'📲 <a href="{link_corretora}" title="">Click to open broker</a>\n'
            f'🙋‍♂️ Don\'t know how to trade yet? <a href="{link_video}" title="">Click here</a>'
        )
                
        # Mensagem em ES
        mensagem_es = (
            f"💰{tempo_expiracao_minutos} {texto_minutos_es} de expiración\n"
            f"{nome_ativo_exibicao};{hora_exibicao_formatada};{action_es} {emoji} {categoria_exibicao}\n\n"
                f"🕐{texto_tempo} {hora_expiracao_formatada}\n\n"
                f"{texto_gale1} {hora_gale1_formatada}\n"
                f"{texto_gale2} {hora_gale2_formatada}\n"
                f"{texto_gale3} {hora_gale3_formatada}\n\n"
            f'📲 <a href="{link_corretora}" title="">Haga clic para abrir el corredor</a>\n'
            f'🙋‍♂️ ¿No sabe operar todavía? <a href="{link_video}" title="">Haga clic aquí</a>'
        )
                
        # Verificar se há algum texto não esperado antes de retornar a mensagem
        if idioma == "pt":
            mensagem_final = mensagem_pt
        elif idioma == "en":
            mensagem_final = mensagem_en
        elif idioma == "es":
            mensagem_final = mensagem_es
        else:  # Padrão para qualquer outro idioma (português)
            mensagem_final = mensagem_pt
            
        BOT2_LOGGER.info(
            f"Mensagem formatada final para idioma {idioma}: {mensagem_final}")
        return mensagem_final

    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao formatar mensagem: {str(e)}")
        traceback.print_exc()
        return None


def bot2_registrar_envio(ativo, direcao, categoria):
    """
    Registra o envio de um sinal no banco de dados.
    Implementao futura: Aqui voc adicionaria o cdigo para registrar o envio no banco de dados.
    """
    pass


# Inicializao do Bot 2 quando este arquivo for executado
bot2_sinais_agendados = False
bot2_contador_sinais = 0  # Contador para rastrear quantos sinais foram enviados
BOT2_ATIVOS_CATEGORIAS = {}  # Inicialização de categorias de ativos

# URLs promocionais
XXBROKER_URL = (
    "https://trade.xxbroker.com/register?aff=741613&aff_model=revenue&afftrack="
)
VIDEO_TELEGRAM_URL = "https://t.me/trendingbrazil/215"
VIDEO_TELEGRAM_ES_URL = "https://t.me/trendingespanish/212"
VIDEO_TELEGRAM_EN_URL = "https://t.me/trendingenglish/226"

# Base directory para os arquivos do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Definindo diretrios para os vdeos
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Subdiretrios para organizar os vdeos
VIDEOS_POS_SINAL_DIR = os.path.join(VIDEOS_DIR, "pos_sinal")
VIDEOS_PROMO_DIR = os.path.join(VIDEOS_DIR, "promo")
# Alterado de "especial" para "gif_especial"
VIDEOS_ESPECIAL_DIR = os.path.join(VIDEOS_DIR, "gif_especial")

# Criar os subdiretrios se no existirem
os.makedirs(VIDEOS_POS_SINAL_DIR, exist_ok=True)
os.makedirs(VIDEOS_PROMO_DIR, exist_ok=True)
os.makedirs(VIDEOS_ESPECIAL_DIR, exist_ok=True)

# Diretrios para vdeos ps-sinal em cada idioma
VIDEOS_POS_SINAL_PT_DIR = os.path.join(VIDEOS_POS_SINAL_DIR, "pt")
VIDEOS_POS_SINAL_EN_DIR = os.path.join(VIDEOS_POS_SINAL_DIR, "en")
VIDEOS_POS_SINAL_ES_DIR = os.path.join(VIDEOS_POS_SINAL_DIR, "es")

# Diretrios para vdeos especiais em cada idioma
VIDEOS_ESPECIAL_PT_DIR = os.path.join(VIDEOS_ESPECIAL_DIR, "pt")
VIDEOS_ESPECIAL_EN_DIR = os.path.join(VIDEOS_ESPECIAL_DIR, "en")
VIDEOS_ESPECIAL_ES_DIR = os.path.join(VIDEOS_ESPECIAL_DIR, "es")

# Criar os subdiretrios para cada idioma se no existirem
os.makedirs(VIDEOS_POS_SINAL_PT_DIR, exist_ok=True)
os.makedirs(VIDEOS_POS_SINAL_EN_DIR, exist_ok=True)
os.makedirs(VIDEOS_POS_SINAL_ES_DIR, exist_ok=True)
os.makedirs(VIDEOS_ESPECIAL_PT_DIR, exist_ok=True)
os.makedirs(VIDEOS_ESPECIAL_EN_DIR, exist_ok=True)
os.makedirs(VIDEOS_ESPECIAL_ES_DIR, exist_ok=True)

# URLs dos GIFs diretamente do GitHub (seguindo a estrutura de seu repositório)
VIDEOS_POS_SINAL_GITHUB = {
    "pt": [
        # Vdeo padro em portugus (9/10)
        f"{GITHUB_BASE_URL}videos/pos_sinal/pt/padrão.gif",
        # Vdeo especial em portugus (1/10)
        f"{GITHUB_BASE_URL}videos/pos_sinal/pt/especial.gif",
    ],
    "en": [
        # Vdeo padro em ingls (9/10)
        f"{GITHUB_BASE_URL}videos/pos_sinal/en/padrao.gif",
        # Vdeo especial em ingls (1/10)
        f"{GITHUB_BASE_URL}videos/pos_sinal/en/especial.gif",
    ],
    "es": [
        # Vdeo padro em espanhol (9/10)
        f"{GITHUB_BASE_URL}videos/pos_sinal/es/padrao.gif",
        # Vdeo especial em espanhol (1/10)
        f"{GITHUB_BASE_URL}videos/pos_sinal/es/especial.gif",
    ],
}

# Configurar vdeos ps-sinal especficos para cada idioma (local paths)
VIDEOS_POS_SINAL = {
    "pt": [
        os.path.join(VIDEOS_POS_SINAL_PT_DIR, "padrão.gif"),
        # Vdeo padro em portugus (9/10)
        # Vdeo especial em portugus (1/10)
        os.path.join(VIDEOS_POS_SINAL_PT_DIR, "especial.gif"),
    ],
    "en": [
        os.path.join(VIDEOS_POS_SINAL_EN_DIR, "padrao.gif"),
        # Vdeo padro em ingls (9/10)
        # Vdeo especial em ingls (1/10)
        os.path.join(VIDEOS_POS_SINAL_EN_DIR, "especial.gif"),
    ],
    "es": [
        os.path.join(VIDEOS_POS_SINAL_ES_DIR, "padrao.gif"),
        # Vdeo padro em espanhol (9/10)
        # Vdeo especial em espanhol (1/10)
        os.path.join(VIDEOS_POS_SINAL_ES_DIR, "especial.gif"),
    ],
}

# Vdeo especial a cada 3 sinais (por idioma) - URLs do GitHub
VIDEOS_ESPECIAIS_GITHUB = {
    "pt": f"{GITHUB_BASE_URL}videos/gif_especial/pt/especial.gif",
    "en": f"{GITHUB_BASE_URL}videos/gif_especial/en/especial.gif",
    "es": f"{GITHUB_BASE_URL}videos/gif_especial/es/especial.gif",
}

# Vdeo especial a cada 3 sinais (por idioma) - local paths
VIDEOS_ESPECIAIS = {
    "pt": os.path.join(VIDEOS_ESPECIAL_PT_DIR, "especial.gif"),
    "en": os.path.join(VIDEOS_ESPECIAL_EN_DIR, "especial.gif"),
    "es": os.path.join(VIDEOS_ESPECIAL_ES_DIR, "especial.gif"),
}

# Vdeos promocionais por idioma - URLs do GitHub
VIDEOS_PROMO_GITHUB = {
    "pt": f"{GITHUB_BASE_URL}videos/promo/pt/promo.gif",
    "en": f"{GITHUB_BASE_URL}videos/promo/en/promo.gif",
    "es": f"{GITHUB_BASE_URL}videos/promo/es/promo.gif",
}

# Vdeos promocionais por idioma - local paths
VIDEOS_PROMO = {
    "pt": os.path.join(VIDEOS_PROMO_DIR, "pt", "promo.gif"),
    "en": os.path.join(VIDEOS_PROMO_DIR, "en", "promo.gif"),
    "es": os.path.join(VIDEOS_PROMO_DIR, "es", "promo.gif"),
}

# Logs para diagnstico
print(f"VIDEOS_DIR: {VIDEOS_DIR}")
print(f"VIDEOS_ESPECIAL_DIR: {VIDEOS_ESPECIAL_DIR}")
print(f"VIDEOS_ESPECIAL_PT_DIR: {VIDEOS_ESPECIAL_PT_DIR}")

# Caminho para o vdeo do GIF especial PT
VIDEO_GIF_ESPECIAL_PT = os.path.join(VIDEOS_ESPECIAL_PT_DIR, "especial.gif")
print(f"VIDEO_GIF_ESPECIAL_PT: {VIDEO_GIF_ESPECIAL_PT}")

# Contador para controle dos GIFs ps-sinal
contador_pos_sinal = 0
contador_desde_ultimo_especial = 0

# Adicionar variveis para controle da imagem especial diria
horario_especial_diario = None
imagem_especial_ja_enviada_hoje = False

# Funo para definir o horrio especial dirio


def definir_horario_especial_diario():
    global horario_especial_diario, imagem_especial_ja_enviada_hoje, mensagem_perda_enviada_hoje
    
    # Reseta o status de envio da imagem especial e mensagem de perda
    imagem_especial_ja_enviada_hoje = False
    mensagem_perda_enviada_hoje = False
    
    # Define um horrio aleatrio entre 0 e 23 horas
    horas_disponiveis = list(range(0, 24))
    hora_aleatoria = random.choice(horas_disponiveis)
    
    # Definir o mesmo minuto usado para o envio de sinais
    minuto_envio = 13
    
    # Define o horrio especial para hoje
    horario_atual = bot2_obter_hora_brasilia()
    horario_especial_diario = horario_atual.replace(
        hour=hora_aleatoria, 
        minute=minuto_envio,  # Mesmo minuto usado para envio de sinais
        second=0, 
        microsecond=0,
    )
    
    BOT2_LOGGER.info(
        f"Horário especial diário definido para: {horario_especial_diario.strftime('%H:%M')}"
    )
    
    # Se o horrio j passou hoje, reagenda para amanh
    if horario_especial_diario < horario_atual:
        horario_especial_diario = horario_especial_diario + timedelta(days=1)
        BOT2_LOGGER.info(
            f"Horário já passou hoje, reagendado para amanhã: {horario_especial_diario.strftime('%H:%M')}"
        )


# Agendar a redefinio do horrio especial dirio  meia-noite


def agendar_redefinicao_horario_especial():
    schedule.every().day.at("00:01").do(definir_horario_especial_diario)
    BOT2_LOGGER.info(
        "Agendada redefinição do horário especial diário para meia-noite e um minuto"
    )


# Chamar a funo no incio para definir o horrio especial para hoje
definir_horario_especial_diario()
agendar_redefinicao_horario_especial()


def verificar_url_gif(url):
    """
    Verifica se a URL de um GIF é válida antes de tentar enviar.
    
    Args:
        url: URL do GIF a ser verificada
        
    Returns:
        bool: True se a URL é válida, False caso contrário
    """
    try:
        # Não precisamos baixar o conteúdo completo, apenas verificar o cabeçalho
        resposta = requests.head(url, timeout=5)
        
        # Verificar se a resposta foi bem-sucedida
        if resposta.status_code == 200:
            # Verificar se o Content-Type é de uma imagem ou GIF
            content_type = resposta.headers.get('Content-Type', '')
            if 'image' in content_type or 'gif' in content_type:
                BOT2_LOGGER.info(f"✅ URL de GIF válida: {url}")
                return True
            else:
                BOT2_LOGGER.warning(f"⚠️ URL retorna conteúdo não-imagem: {content_type}")
                return False
        else:
            BOT2_LOGGER.warning(f"⚠️ URL de GIF inválida. Status: {resposta.status_code}")
            return False
    except Exception as e:
        BOT2_LOGGER.error(f"❌ Erro ao verificar URL de GIF: {url} - Erro: {str(e)}")
        return False


def bot2_enviar_gif_pos_sinal(signal=None):
    """
    Envia uma imagem pós-sinal para todos os canais configurados, 7 minutos após o sinal original.
    Uma vez por dia, envia uma mensagem de perda em vez da imagem.
    
    Args:
        signal: O sinal que foi enviado anteriormente. Se None, usa o último sinal enviado.
    
    Returns:
        bool: True se pelo menos uma imagem/mensagem foi enviada com sucesso, False caso contrário.
    """
    global BOT2_LOGGER, BOT2_CANAIS_CONFIG, BOT2_TOKEN, ultimo_sinal_enviado
    
    try:
        # Obter a hora atual em Brasília para os logs
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        
        # Verificar se devemos enviar a mensagem de perda em vez do GIF
        # (uma vez por dia)
        if not verificar_mensagem_perda_hoje():
            BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] 🔄 Decidido enviar mensagem de perda em vez de imagem pós-sinal (uma vez ao dia)")
            return enviar_mensagem_perda(signal)
        
        BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] 🔄 Iniciando envio de imagem pós-sinal")
        
        # Se não foi fornecido um sinal, usar o último sinal enviado
        if not signal and ultimo_sinal_enviado:
            signal = ultimo_sinal_enviado
            BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] ℹ️ Usando último sinal enviado: {signal['ativo']} {signal['direcao']}")
        
        if not signal:
            BOT2_LOGGER.error(f"[GIF-POS][{horario_atual}] ❌ Nenhum sinal fornecido e nenhum sinal anterior disponível")
            return False
        
        # Verificar conexão com API antes de enviar
        BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] 🔄 Verificando conexão com API do Telegram...")
        try:
            url_verificacao = f"https://api.telegram.org/bot{BOT2_TOKEN}/getMe"
            resposta = requests.get(url_verificacao, timeout=10)
            if resposta.status_code == 200:
                BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] ✅ Conexão com API OK!")
            else:
                BOT2_LOGGER.warning(f"[GIF-POS][{horario_atual}] ⚠️ API do Telegram respondeu com código {resposta.status_code}")
        except Exception as e:
            BOT2_LOGGER.warning(f"[GIF-POS][{horario_atual}] ⚠️ Erro ao verificar conexão com API: {str(e)}")
        
        # Lista para armazenar resultado dos envios
        resultados_envio = []
        
        # Contadores para estatísticas
        total_canais = sum(len(chats) for chats in BOT2_CANAIS_CONFIG.items())
        enviados_com_sucesso = 0
        
        BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] 📊 Total de canais configurados: {total_canais}")
        
        # Caminho do sticker pós-sinal com transparência (webp formato)
        # Usando sticker com transparência ao invés de GIF/imagem normal
        sticker_url = "https://raw.githubusercontent.com/IgorElion/-TelegramBot/main/videos/pos_sinal/180398513446716419%20(7).webp"
        
        # Verificar se o arquivo existe (via HEAD request)
        try:
            resposta_verificacao = requests.head(sticker_url, timeout=5)
            if resposta_verificacao.status_code != 200:
                BOT2_LOGGER.warning(f"[GIF-POS][{horario_atual}] ⚠️ Sticker pós-sinal não encontrado: {sticker_url} (Status: {resposta_verificacao.status_code})")
                # Fallback para URL alternativa se necessário
                sticker_url = "https://i.imgur.com/6MLS405.webp"
                BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] 🔄 Usando URL de fallback: {sticker_url}")
        except Exception as e:
            BOT2_LOGGER.error(f"[GIF-POS][{horario_atual}] ❌ Erro ao verificar URL do sticker: {str(e)}")
            # Fallback para URL alternativa
            sticker_url = "https://i.imgur.com/6MLS405.webp"
            BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] 🔄 Usando URL de fallback: {sticker_url}")
        
        # Para cada idioma, enviar o sticker pós-sinal
        for idioma, chats in BOT2_CANAIS_CONFIG.items():
            if not chats:
                BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] ℹ️ Nenhum chat configurado para idioma {idioma}, pulando")
                continue
            
            BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] 🌐 Processando idioma: {idioma} ({len(chats)} canais)")
            
            # Enviar para cada chat configurado neste idioma
            for chat_id in chats:
                try:
                    # Preparar a URL para o método sendSticker da API do Telegram (preserva transparência)
                    url = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendSticker"
                    
                    # Montar o payload da requisição
                    payload = {
                        "chat_id": chat_id,
                        "sticker": sticker_url,
                        "disable_notification": False
                    }
                    
                    BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] 🚀 Enviando sticker pós-sinal para chat_id: {chat_id} (idioma: {idioma})")
                    
                    # Enviar a requisição para a API
                    inicio_envio = time.time()
                    resposta = requests.post(url, json=payload, timeout=15)
                    tempo_resposta = (time.time() - inicio_envio) * 1000  # em milissegundos
                    
                    # Verificar o resultado da requisição
                    if resposta.status_code == 200:
                        BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] ✅ Sticker enviado com sucesso para {chat_id} (tempo: {tempo_resposta:.1f}ms)")
                        resultados_envio.append(True)
                        enviados_com_sucesso += 1
                    else:
                        BOT2_LOGGER.error(f"[GIF-POS][{horario_atual}] ❌ Falha ao enviar sticker para {chat_id}: {resposta.status_code} - {resposta.text}")
                        resultados_envio.append(False)
                        
                        # Se falhar, tentar novamente uma vez
                        BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] 🔄 Tentando novamente para {chat_id}...")
                        try:
                            resposta_retry = requests.post(url, json=payload, timeout=15)
                            if resposta_retry.status_code == 200:
                                BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] ✅ Sticker enviado com sucesso na segunda tentativa para {chat_id}")
                                resultados_envio.append(True)
                                enviados_com_sucesso += 1
                            else:
                                BOT2_LOGGER.error(f"[GIF-POS][{horario_atual}] ❌ Falha na segunda tentativa: {resposta_retry.status_code}")
                        except Exception as e:
                            BOT2_LOGGER.error(f"[GIF-POS][{horario_atual}] ❌ Erro na segunda tentativa: {str(e)}")
                
                except Exception as e:
                    BOT2_LOGGER.error(f"[GIF-POS][{horario_atual}] ❌ Exceção ao enviar sticker para {chat_id}: {str(e)}")
                    BOT2_LOGGER.error(f"[GIF-POS][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
                    resultados_envio.append(False)
        
        # Calcular estatísticas finais
        if total_canais > 0:
            taxa_sucesso = (enviados_com_sucesso / total_canais) * 100
            BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] 📊 RESUMO: {enviados_com_sucesso}/{total_canais} stickers enviados com sucesso ({taxa_sucesso:.1f}%)")
        else:
            BOT2_LOGGER.warning(f"[GIF-POS][{horario_atual}] ⚠️ Nenhum canal configurado para envio de stickers!")
        
        # Retornar True se pelo menos uma imagem foi enviada com sucesso
        envio_bem_sucedido = any(resultados_envio)
        
        if envio_bem_sucedido:
            BOT2_LOGGER.info(f"[GIF-POS][{horario_atual}] ✅ Envio de sticker pós-sinal concluído com sucesso")
        else:
            BOT2_LOGGER.error(f"[GIF-POS][{horario_atual}] ❌ Falha em todos os envios de sticker pós-sinal")
        
        return envio_bem_sucedido
    
    except Exception as e:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[GIF-POS][{horario_atual}] ❌ Erro crítico ao enviar sticker pós-sinal: {str(e)}")
        BOT2_LOGGER.error(f"[GIF-POS][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
        return False


def bot2_send_message(ignorar_anti_duplicacao=False, enviar_gif_imediatamente=False):
    """Gera e envia um sinal de trading para os canais configurados."""
    global BOT2_LOGGER, BOT2_CANAIS_CONFIG, BOT2_TOKEN, CONFIGS_IDIOMA, ultimo_sinal_enviado, bot2_contador_sinais, thread_sequencia_ativa

    try:
        # Obtendo a hora atual de Brasília para logs
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        data_atual = agora.strftime("%Y-%m-%d")
        
        # Log dos IDs dos canais configurados
        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 📋 Resumo de canais configurados:")
        for idioma, canais in BOT2_CANAIS_CONFIG.items():
            BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🌐 Canais para {idioma}: {canais} (tipo: {type(canais).__name__})")
            for i, canal in enumerate(canais):
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ▶️ Canal {i+1} para {idioma}: {canal} (tipo: {type(canal).__name__})")
        
        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🔄 Iniciando geração e envio de sinal (data: {data_atual})")
        
        # Verificar quais ativos estão disponíveis no momento
        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🔍 Verificando ativos disponíveis para este horário...")
        ativos_disponiveis = bot2_verificar_disponibilidade()
        
        # Log detalhado sobre ativos disponíveis
        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ℹ️ Total de {len(ativos_disponiveis)} ativos disponíveis de {len(ATIVOS_CATEGORIAS['Digital'])} configurados")
        if len(ativos_disponiveis) < 5:
            BOT2_LOGGER.warning(f"[SINAL][{horario_atual}] ⚠️ Poucos ativos disponíveis: {', '.join(ativos_disponiveis)}")
        else:
            # Mostrar os primeiros ativos disponíveis (máximo 5) para não poluir o log
            ativos_amostra = ativos_disponiveis[:5]
            BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ℹ️ Exemplos de ativos disponíveis: {', '.join(ativos_amostra)} e outros {len(ativos_disponiveis) - 5}...")
        
        # Adicionar os ativos disponíveis à categoria temporária
        ATIVOS_CATEGORIAS["Digital_Disponiveis"] = ativos_disponiveis
        
        # Gerar um sinal aleatório considerando apenas os ativos disponíveis
        sinal = bot2_gerar_sinal_aleatorio()
        if not sinal:
            BOT2_LOGGER.error(f"[SINAL][{horario_atual}] ❌ Falha ao gerar sinal aleatório")
            return False

        # Log do sinal gerado com mais detalhes
        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 📊 Sinal gerado: Ativo={sinal['ativo']}, Direção={sinal['direcao']}, Categoria={sinal['categoria']}, Tempo={sinal['tempo_expiracao_minutos']}min")
        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🕒 Horário exato de expiração: {(agora + timedelta(minutes=sinal['tempo_expiracao_minutos'])).strftime('%H:%M:%S')}")

        # Incrementar o contador de sinais (apenas se não estiver ignorando a anti-duplicação)
        if not ignorar_anti_duplicacao:
            bot2_contador_sinais += 1
            BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🔢 Contador incrementado: {bot2_contador_sinais}")
            
            # Verificar se é múltiplo de 3
            e_multiplo_3 = bot2_contador_sinais % 3 == 0
            if e_multiplo_3:
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🎯 SINAL MÚLTIPLO DE 3 DETECTADO! Sinal #{bot2_contador_sinais} é o {bot2_contador_sinais//3}º múltiplo de 3")
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 📋 Sequência especial será ativada para o sinal #{bot2_contador_sinais}")
            else:
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ℹ️ Sinal comum (não múltiplo de 3). Contador atual: {bot2_contador_sinais}")
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ℹ️ Próximo múltiplo de 3 será o sinal #{((bot2_contador_sinais//3)+1)*3}")

        # Lista para armazenar resultado dos envios
        resultados_envio = []
        
        # Contadores para estatísticas
        total_canais = sum(len(chats) for chats in BOT2_CANAIS_CONFIG.items())
        sinais_enviados_com_sucesso = 0
        
        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 📊 Total de canais configurados: {total_canais}")
        
        # Para cada idioma configurado, enviar o sinal
        for idioma, chats in BOT2_CANAIS_CONFIG.items():
            if not chats:
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ℹ️ Nenhum canal configurado para idioma {idioma}, pulando")
                continue
                
            BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🌐 Processando idioma: {idioma} ({len(chats)} canais)")
            
            # Converter o fuso horário para o idioma
            hora_local = bot2_converter_fuso_horario(agora, CONFIGS_IDIOMA.get(idioma, {}).get("fuso_horario", "America/Sao_Paulo"))
            hora_formatada = hora_local.strftime("%H:%M")
            
            # Obter a mensagem formatada para este idioma
            mensagem = bot2_formatar_mensagem(sinal, hora_formatada, idioma)
            
            # Enviar para cada canal deste idioma
            for chat_id in chats:
                try:
                    # URL base da API do Telegram
                    url_base = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
                    
                    # Log especial para canal em português
                    if idioma == "pt":
                        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🚨 ENVIANDO PARA CANAL PT: chat_id={chat_id} (tipo: {type(chat_id).__name__})")
                    
                    # Enviar o sinal
                    BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🚀 Enviando sinal para chat_id: {chat_id} (idioma: {idioma})")
                    
                    # Registrando o envio para estatísticas
                    bot2_registrar_envio(sinal["ativo"], sinal["direcao"], sinal["categoria"])
                    
                    # Armazenar o último sinal enviado para ser usado pelo GIF pós-sinal
                    ultimo_sinal_enviado = sinal
                    
                    # Enviar a mensagem para a API
                    resposta = requests.post(
                        url_base,
                        json={
                            "chat_id": chat_id,
                            "text": mensagem,
                            "parse_mode": "HTML",
                            "disable_web_page_preview": True,
                        },
                        timeout=15,
                    )
                    
                    # Log especial para canal em português com resultado
                    if idioma == "pt":
                        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🚨 RESULTADO CANAL PT: status={resposta.status_code}, resposta={resposta.text}")
                    
                    # Verificar resultado
                    if resposta.status_code == 200:
                        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ✅ Sinal enviado com sucesso para {chat_id}")
                        resultados_envio.append(True)
                        sinais_enviados_com_sucesso += 1
                    else:
                        BOT2_LOGGER.error(f"[SINAL][{horario_atual}] ❌ Erro ao enviar para {chat_id}: Status {resposta.status_code} - {resposta.text}")
                        
                        # Tentar novamente uma vez se falhar
                        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🔄 Tentando enviar novamente para {chat_id}...")
                        try:
                            retry_resposta = requests.post(
                                url_base,
                                json={
                                    "chat_id": chat_id,
                                    "text": mensagem,
                                    "parse_mode": "HTML",
                                    "disable_web_page_preview": True,
                                },
                                timeout=15,
                            )
                            
                            if retry_resposta.status_code == 200:
                                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ✅ Sinal enviado com sucesso na segunda tentativa para {chat_id}")
                                sinais_enviados_com_sucesso += 1
                            else:
                                BOT2_LOGGER.error(f"[SINAL][{horario_atual}] ❌ Falha na segunda tentativa: {retry_resposta.status_code}")
                        except Exception as retry_e:
                            BOT2_LOGGER.error(f"[SINAL][{horario_atual}] ❌ Erro na segunda tentativa: {str(retry_e)}")

                except Exception as e:
                    BOT2_LOGGER.error(f"[SINAL][{horario_atual}] ❌ Erro ao enviar para {chat_id}: {str(e)}")
                    BOT2_LOGGER.error(f"[SINAL][{horario_atual}] 🔍 Detalhes do erro: {traceback.format_exc()}")

        # Resumo do envio
        if total_canais > 0:
            taxa_sucesso = (sinais_enviados_com_sucesso / total_canais) * 100
            BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 📊 RESUMO: {sinais_enviados_com_sucesso}/{total_canais} sinais enviados com sucesso ({taxa_sucesso:.1f}%)")
        else:
            BOT2_LOGGER.warning(f"[SINAL][{horario_atual}] ⚠️ Nenhum canal configurado para envio de sinais!")

        # GIF imediato (apenas para testes) ou sequência normal
        if enviar_gif_imediatamente:
            # Se solicitado, enviar o GIF imediatamente (para testes)
            BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🔄 Modo de teste: enviando GIF pós-sinal imediatamente")
            bot2_enviar_gif_pos_sinal(sinal)
        else:
            # Verificar se é múltiplo de 3 para enviar a sequência especial
            e_multiplo_3 = bot2_contador_sinais % 3 == 0
            BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🔢 Verificando se sinal #{bot2_contador_sinais} é múltiplo de 3: {e_multiplo_3}")
            
            if e_multiplo_3:
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🔄 Sinal múltiplo de 3 detectado (#{bot2_contador_sinais})")
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 📋 Iniciando sequência especial para múltiplos de 3")
                
                # Verificar se já existe uma thread de sequência ativa
                if hasattr(enviar_sequencia_multiplo_tres, 'thread_ativa') and enviar_sequencia_multiplo_tres.thread_ativa and enviar_sequencia_multiplo_tres.thread_ativa.is_alive():
                    BOT2_LOGGER.warning(f"[SINAL][{horario_atual}] ⚠️ Já existe uma sequência múltipla de 3 em andamento. Não iniciando nova sequência.")
                    
                    # Log da thread existente para diagnóstico
                    thread_existente = enviar_sequencia_multiplo_tres.thread_ativa
                    BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ℹ️ Thread existente ID: {thread_existente.ident}, Nome: {thread_existente.name}, Ativa: {thread_existente.is_alive()}")
                    
                    # Mesmo com uma thread existente, garantimos que uma nova seja criada para este sinal múltiplo de 3
                    BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🔄 Forçando criação de nova thread para garantir sequência do sinal #{bot2_contador_sinais}")
                    
                    # Iniciar thread para sequência especial de múltiplo de 3
                    sequencia_thread = threading.Thread(
                        target=enviar_sequencia_multiplo_tres, 
                        name=f"Sequencia-M3-Sinal{bot2_contador_sinais}"
                    )
                    sequencia_thread.daemon = True
                    sequencia_thread.start()
                    
                    # Armazenar referência à thread
                    enviar_sequencia_multiplo_tres.thread_ativa = sequencia_thread
                    
                    BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🧵 Nova thread para sequência de múltiplo de 3 iniciada com sucesso - ID: {sequencia_thread.ident}")
                else:
                    # Iniciar thread para sequência especial de múltiplo de 3
                    sequencia_thread = threading.Thread(
                        target=enviar_sequencia_multiplo_tres,
                        name=f"Sequencia-M3-Sinal{bot2_contador_sinais}"
                    )
                    sequencia_thread.daemon = True
                    sequencia_thread.start()
                    
                    # Armazenar referência à thread
                    enviar_sequencia_multiplo_tres.thread_ativa = sequencia_thread
                    
                    BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🧵 Thread para sequência de múltiplo de 3 iniciada com sucesso - ID: {sequencia_thread.ident}")
                
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 📋 CRONOGRAMA COMPLETO DA SEQUÊNCIA MÚLTIPLO DE 3:")
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ⏱️ T+0: Sinal principal já enviado")
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ⏱️ T+7: GIF pós-sinal (7 minutos após o sinal)")
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ⏱️ T+27: Mensagem de participação (27 minutos após o sinal)")
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ⏱️ T+35: GIF promocional (35 minutos após o sinal)")
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ⏱️ T+36: Mensagem de abertura da corretora (36 minutos após o sinal)")
            else:
                # Para sinais não múltiplos de 3, apenas enviar o GIF pós-sinal após 7 minutos
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ⏱️ Agendando GIF pós-sinal para 7 minutos (T+7)")
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🔍 VALIDAÇÃO: sinal={sinal}")
                
                def enviar_gif_pos_sinal_apos_delay():
                    try:
                        # ID único para rastreamento nos logs
                        thread_id = str(uuid.uuid4())[:8]
                        
                        # Capturar o sinal aqui dentro da função para garantir que estamos usando o valor correto
                        sinal_thread = sinal  # Capturando o valor de sinal no momento da criação da thread
                        BOT2_LOGGER.info(f"[GIF-DELAY][{bot2_obter_hora_brasilia().strftime('%H:%M:%S')}][Thread-{thread_id}] 🔍 Sinal capturado na thread: {sinal_thread}")
                        
                        # Aguardar 7 minutos
                        inicio_espera = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
                        BOT2_LOGGER.info(f"[GIF-DELAY][{inicio_espera}][Thread-{thread_id}] ⏲️ Iniciando contagem de 7 minutos para o GIF pós-sinal")
                        
                        # Log adicional para depuração - a cada minuto
                        for i in range(1, 8):
                            time.sleep(60)  # 1 minuto
                            agora_log = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
                            BOT2_LOGGER.info(f"[GIF-DELAY][{agora_log}][Thread-{thread_id}] ⏳ Aguardando... {i}/7 minutos decorridos")
                        
                        # Enviar o GIF pós-sinal
                        agora = bot2_obter_hora_brasilia()
                        horario_atual = agora.strftime("%H:%M:%S")
                        BOT2_LOGGER.info(f"[GIF-DELAY][{horario_atual}][Thread-{thread_id}] ⏰ Tempo de espera concluído, enviando GIF pós-sinal (T+7)")
                        
                        # Log detalhado antes de chamar a função
                        BOT2_LOGGER.info(f"[GIF-DELAY][{horario_atual}][Thread-{thread_id}] 🔍 Tentando enviar GIF pós-sinal. Sinal usado: {sinal_thread}")
                        resultado = bot2_enviar_gif_pos_sinal(sinal_thread)
                        BOT2_LOGGER.info(f"[GIF-DELAY][{horario_atual}][Thread-{thread_id}] 📊 Resultado do envio do GIF pós-sinal: {'✅ Sucesso' if resultado else '❌ Falha'}")
                    except Exception as e:
                        agora = bot2_obter_hora_brasilia()
                        horario_atual = agora.strftime("%H:%M:%S")
                        BOT2_LOGGER.error(f"[GIF-DELAY][{horario_atual}] ❌ Erro no agendamento do GIF pós-sinal: {str(e)}")
                        BOT2_LOGGER.error(f"[GIF-DELAY][{horario_atual}] 🔍 Detalhes do erro: {traceback.format_exc()}")
                
                # Iniciar thread para envio do GIF pós-sinal
                global thread_gif_pos_sinal_ativa
                thread_gif_pos_sinal_ativa = threading.Thread(
                    target=enviar_gif_pos_sinal_apos_delay,
                    name=f"GIF-POS-Sinal{bot2_contador_sinais}"
                )
                thread_gif_pos_sinal_ativa.daemon = True
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 🧵 Iniciando thread para GIF pós-sinal (T+7 minutos)")
                thread_gif_pos_sinal_ativa.start()
                BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ✅ Thread para GIF pós-sinal iniciada com sucesso ID: {thread_gif_pos_sinal_ativa.ident}")

        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] ✅ Processamento do sinal concluído com sucesso")
        
        # Agendar a verificação do próximo sinal
        proximo_sinal = agora + timedelta(hours=1)
        proximo_sinal = proximo_sinal.replace(minute=13, second=0, microsecond=0)
        BOT2_LOGGER.info(f"[SINAL][{horario_atual}] 📅 Próximo sinal agendado para: {proximo_sinal.strftime('%H:%M:%S')} (horário de Brasília)")
        
        return True

    except Exception as e:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[SINAL][{horario_atual}] ❌ Erro geral ao enviar sinal: {str(e)}")
        BOT2_LOGGER.error(f"[SINAL][{horario_atual}] 🔍 Detalhes do erro: {traceback.format_exc()}")
        traceback.print_exc()
        return False


def enviar_sequencia_multiplo_tres():
    """
    Envia uma sequência de mensagens para sinais múltiplos de 3.
    A sequência é:
    1. Sinal normal (T+0)
    2. Mensagem de participação (T+26 min)
    3. GIF promocional (T+35 min)
    4. Mensagem de abertura de corretora (T+55 min)
    """
    global BOT2_LOGGER, ultimo_sinal_enviado, sequencia_multiplo_tres_lock, BOT2_CANAIS_CONFIG, thread_sequencia_ativa
    
    # Gerar ID único para esta sequência para rastrear nos logs
    seq_id = uuid.uuid4().hex[:8]
    
    # Usar lock para garantir acesso exclusivo
    with sequencia_multiplo_tres_lock:
        # Se já existe uma thread rodando, não iniciar outra
        if thread_sequencia_ativa is not None and thread_sequencia_ativa.is_alive():
            agora = bot2_obter_hora_brasilia()
            horario_atual = agora.strftime("%H:%M:%S")
            BOT2_LOGGER.warning(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ⚠️ Já existe uma sequência múltiplo de 3 em execução. Ignorando solicitação.")
            return

    try:
        # Iniciar o tempo para medir duração total
        inicio_sequencia = time.time()
        
        # Registrar início da sequência
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🚀 Iniciando sequência especial para múltiplo de 3")
        
        # ETAPA 1: Enviar sinal normal
        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🔔 ETAPA 1/4: Enviando sinal normal")
        
        # Chamar a função de envio de sinal
        result_sinal = bot2_send_message()
        if not result_sinal:
            BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Falha ao enviar sinal normal. Abortando sequência.")
            return False
            
        # Verificar se o último sinal foi salvo corretamente
        if ultimo_sinal_enviado is None:
            BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ ultimo_sinal_enviado é None no início da sequência!")
            
        # Aguardar 26 minutos após o sinal normal
        tempo_participacao = 26 * 60  # 26 minutos em segundos
        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ⏱️ Aguardando {tempo_participacao/60:.1f} minutos até a mensagem de participação")
        
        # Loop de espera com feedback
        for minuto in range(1, 27):
            time.sleep(60)  # Esperar 1 minuto
            tempo_decorrido = time.time() - inicio_sequencia
            BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ⏳ Aguardando mensagem de participação... {minuto}/26 minutos decorridos (tempo total: {tempo_decorrido:.1f}s)")
            
        # ETAPA 2: Enviar mensagem de participação (T+26)
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 📣 ETAPA 2/4: Enviando mensagem de participação (T+26)")
        
        # Verificar se a função enviar_mensagem_participacao existe e é chamável
        if enviar_mensagem_participacao is None:
            BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Função enviar_mensagem_participacao não está definida!")
            # Continuar com a sequência mesmo sem enviar a mensagem de participação
        else:
            # Tentar enviar até 3 vezes com intervalo de 30 segundos
            max_tentativas = 3
            for tentativa in range(1, max_tentativas + 1):
                BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🔄 Tentativa {tentativa}/{max_tentativas} de enviar mensagem de participação")
                try:
                    resultado_participacao = enviar_mensagem_participacao()
                    if resultado_participacao:
                        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ✅ Mensagem de participação enviada com sucesso")
                        break
                    else:
                        BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Falha ao enviar mensagem de participação")
                except Exception as e:
                    BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Erro ao enviar mensagem de participação: {str(e)}")
                    BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🔍 Detalhes: {traceback.format_exc()}")
                
                # Se não for a última tentativa, aguardar antes de tentar novamente
                if tentativa < max_tentativas:
                    time.sleep(30)  # Aguardar 30 segundos entre tentativas
                    horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
            
            # Verificar se todas as tentativas falharam
            if tentativa == max_tentativas:
                BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Falha nas {max_tentativas} tentativas de enviar mensagem de participação. Continuando sequência...")
        
        # Aguardar mais 8 minutos (T+35 total) para o GIF promocional
        # Esta espera é APÓS a mensagem de participação
        tempo_gif_promo = 8 * 60  # 8 minutos em segundos
        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ⏱️ Agendando GIF promocional para T+35 minutos (8 minutos após mensagem de participação)")
        
        # Loop de espera com feedback
        for minuto in range(1, 9):
            time.sleep(60)  # Esperar 1 minuto
            tempo_decorrido = time.time() - inicio_sequencia
            agora = bot2_obter_hora_brasilia()
            horario_atual = agora.strftime("%H:%M:%S")
            BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ⏳ Aguardando GIF promocional... {minuto}/8 minutos decorridos após mensagem de participação (tempo total: {tempo_decorrido:.1f}s)")
            
        # ETAPA 3: Enviar GIF promocional (T+35)
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🎬 ETAPA 3/4: Enviando GIF promocional (T+35)")
        
        # Enviar para cada idioma configurado
        for idioma in BOT2_CANAIS_CONFIG.keys():
            BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🌐 Enviando GIF promocional para idioma: {idioma}")
            
            # Verificar se a função bot2_enviar_gif_promo existe e é chamável
            if bot2_enviar_gif_promo is None:
                BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Função bot2_enviar_gif_promo não está definida!")
                # Pular para o próximo idioma sem tentar chamar a função
                continue
                
            # Tentar enviar até 3 vezes com intervalo de 30 segundos
            max_tentativas = 3
            for tentativa in range(1, max_tentativas + 1):
                BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🔄 Tentativa {tentativa}/{max_tentativas} para idioma {idioma}")
                try:
                    resultado_gif_promo = bot2_enviar_gif_promo(idioma)
                    if resultado_gif_promo:
                        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ✅ GIF promocional enviado com sucesso para idioma {idioma}")
                        break
                    else:
                        BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Falha ao enviar GIF promocional para idioma {idioma}")
                except Exception as e:
                    BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Erro ao enviar GIF promocional para idioma {idioma}: {str(e)}")
                    BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🔍 Detalhes: {traceback.format_exc()}")
                
                # Se não for a última tentativa, aguardar antes de tentar novamente
                if tentativa < max_tentativas:
                    time.sleep(30)  # Aguardar 30 segundos entre tentativas
                    horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
            
            # Verificar se todas as tentativas falharam
            if tentativa == max_tentativas:
                BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Falha nas {max_tentativas} tentativas para idioma {idioma}.")
        
        # Aguardar mais 20 minutos (T+55 total) para a mensagem de corretora
        # Esta espera é APÓS o GIF promocional
        tempo_corretora = 20 * 60  # 20 minutos em segundos
        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ⏱️ Agendando mensagem de corretora para T+55 minutos (20 minutos após GIF promocional)")
        
        # Loop de espera com feedback
        for minuto in range(1, 21):
            time.sleep(60)  # Esperar 1 minuto
            tempo_decorrido = time.time() - inicio_sequencia
            agora = bot2_obter_hora_brasilia()
            horario_atual = agora.strftime("%H:%M:%S")
            BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ⏳ Aguardando mensagem de corretora... {minuto}/20 minutos decorridos após GIF promocional (tempo total: {tempo_decorrido:.1f}s)")
            
        # ETAPA 4: Enviar mensagem de abertura de corretora (T+55)
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 📢 ETAPA 4/4: Enviando mensagem de abertura de corretora (T+55)")
        
        # Verificar se a função bot2_enviar_mensagem_abertura_corretora existe e é chamável
        if bot2_enviar_mensagem_abertura_corretora is None:
            BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Função bot2_enviar_mensagem_abertura_corretora não está definida!")
            # Finalizar a sequência mesmo sem enviar a mensagem de abertura
        else:
            # Enviar para cada idioma configurado
            for idioma in BOT2_CANAIS_CONFIG.keys():
                BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🌐 Enviando mensagem de corretora para idioma: {idioma}")
                
                # Tentar enviar até 3 vezes com intervalo de 30 segundos
                max_tentativas = 3
                for tentativa in range(1, max_tentativas + 1):
                    BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🔄 Tentativa {tentativa}/{max_tentativas} para idioma {idioma}")
                    try:
                        resultado_corretora = bot2_enviar_mensagem_abertura_corretora(idioma)
                        if resultado_corretora:
                            BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ✅ Mensagem de corretora enviada com sucesso para idioma {idioma}")
                            break
                        else:
                            BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Falha ao enviar mensagem de corretora para idioma {idioma}")
                    except Exception as e:
                        BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Erro ao enviar mensagem de corretora para idioma {idioma}: {str(e)}")
                        BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🔍 Detalhes: {traceback.format_exc()}")
                    
                    # Se não for a última tentativa, aguardar antes de tentar novamente
                    if tentativa < max_tentativas:
                        time.sleep(30)  # Aguardar 30 segundos entre tentativas
                        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
                
                # Verificar se todas as tentativas falharam
                if tentativa == max_tentativas:
                    BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Falha nas {max_tentativas} tentativas para idioma {idioma}.")
        
        # Calcular tempo total da sequência
        tempo_total = time.time() - inicio_sequencia
        
        # Finalizar a sequência
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ✅ Sequência múltiplo de 3 CONCLUÍDA! Tempo total: {tempo_total/60:.1f} minutos ({tempo_total:.1f}s)")
        
        return True
        
    except Exception as e:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] ❌ Erro ao executar sequência: {str(e)}")
        BOT2_LOGGER.error(f"[SEQUENCIA-3][{horario_atual}][Seq-{seq_id}] 🔍 Detalhes: {traceback.format_exc()}")
        return False
    finally:
        # Resetar a variável de controle de thread para permitir novas sequências
        thread_sequencia_ativa = None


def bot2_iniciar_ciclo_sinais():
    """
    Inicia o ciclo de envio de sinais do Bot 2, agendando para serem enviados
    a cada hora no minuto 13.
    Também agenda uma verificação de ativos disponíveis 3 minutos antes do sinal.
    """
    global bot2_sinais_agendados, BOT2_LOGGER
    
    try:
        # Limpar agendamentos anteriores para evitar duplicação
        schedule.clear("bot2_sinais")
        schedule.clear("verificacao_previa")
        schedule.clear("reset_controle")
        
        BOT2_LOGGER.info("🔄 Sinal do Bot 2 agendado para o minuto 13 de cada hora")
        BOT2_LOGGER.info("🔄 Verificação prévia de ativos agendada para o minuto 10 de cada hora (3 min antes do sinal)")
        BOT2_LOGGER.info("🔄 Reset de controle anti-duplicação agendado para o minuto 0 de cada hora")
        BOT2_LOGGER.info("⚙️ Configuração atual: 1 sinal por hora, apenas ativos Digital, expiração de 5 minutos")
        
        # Verificar os ativos disponíveis no momento da inicialização
        BOT2_LOGGER.info("🔍 Verificando ativos disponíveis no momento da inicialização...")
        
        # Obter a hora atual de Brasília
        hora_atual = bot2_obter_hora_brasilia()
        dia_semana = hora_atual.strftime("%A")
        hora_minuto = hora_atual.strftime("%H:%M")
        
        BOT2_LOGGER.info(f"📆 Data/Hora atual: {hora_atual.strftime('%Y-%m-%d %H:%M:%S')} ({dia_semana})")
        
        # Verificar quais ativos estão disponíveis neste momento
        ativos_disponiveis = bot2_verificar_disponibilidade()
        total_ativos = len(ATIVOS_CATEGORIAS["Digital"])
        
        if ativos_disponiveis:
            percentual_disponivel = (len(ativos_disponiveis) / total_ativos) * 100
            BOT2_LOGGER.info(f"✅ {len(ativos_disponiveis)}/{total_ativos} ativos disponíveis ({percentual_disponivel:.1f}%)")
            
            # Mostrar alguns ativos disponíveis (até 5)
            amostra_disponiveis = ativos_disponiveis[:5]
            BOT2_LOGGER.info(f"🟢 Exemplos disponíveis: {', '.join(amostra_disponiveis)}{' e outros...' if len(ativos_disponiveis) > 5 else ''}")
        else:
            BOT2_LOGGER.warning("⚠️ ATENÇÃO: Nenhum ativo disponível no momento atual!")
            BOT2_LOGGER.info("💡 Os sinais serão enviados quando houver ativos disponíveis")
        
        # Hora atual e próximo horário de sinal (minuto 13 da próxima hora)
        proxima_hora = hora_atual.replace(minute=13, second=0, microsecond=0)
        if hora_atual.minute >= 13:
            proxima_hora = proxima_hora + timedelta(hours=1)
            
        # Calcular quanto tempo falta para o próximo sinal
        tempo_para_proximo = (proxima_hora - hora_atual).total_seconds() / 60.0
        
        BOT2_LOGGER.info(f"📅 Próximo sinal agendado para: {proxima_hora.strftime('%H:%M')} (em {tempo_para_proximo:.1f} minutos)")
        
        # Função para verificar ativos disponíveis 3 minutos antes do sinal
        def verificar_ativos_pre_sinal():
            """Verifica ativos disponíveis 3 minutos antes do sinal agendado"""
            try:
                # Obter hora atual
                hora_atual = bot2_obter_hora_brasilia()
                hora_formatada = hora_atual.strftime("%H:%M:%S")
                
                BOT2_LOGGER.info(f"[PRE-SINAL][{hora_formatada}] 🔍 VERIFICAÇÃO PRÉ-SINAL: Verificando ativos disponíveis 3 minutos antes do sinal")
                BOT2_LOGGER.info(f"[PRE-SINAL][{hora_formatada}] 🕒 Hora atual: {hora_atual.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Calcular hora do próximo sinal (3 minutos após esta verificação)
                hora_proximo_sinal = hora_atual + timedelta(minutes=3)
                BOT2_LOGGER.info(f"[PRE-SINAL][{hora_formatada}] ⏱️ Sinal será enviado às: {hora_proximo_sinal.strftime('%H:%M:%S')}")
                
                # Verificar ativos disponíveis
                ativos_disponiveis = bot2_verificar_disponibilidade()
                
                # Armazenar ativos disponíveis para uso na geração do sinal
                ATIVOS_CATEGORIAS["Digital_Disponiveis"] = ativos_disponiveis
                
                total_ativos = len(ATIVOS_CATEGORIAS["Digital"])
                
                if not ativos_disponiveis:
                    BOT2_LOGGER.warning(f"[PRE-SINAL][{hora_formatada}] ⚠️ ALERTA: Nenhum ativo disponível para o próximo sinal!")
                    BOT2_LOGGER.warning(f"[PRE-SINAL][{hora_formatada}] ⚠️ O sinal pode não ser enviado se essa situação persistir!")
                    return
                
                percentual_disponivel = (len(ativos_disponiveis) / total_ativos) * 100
                BOT2_LOGGER.info(f"[PRE-SINAL][{hora_formatada}] ✅ {len(ativos_disponiveis)}/{total_ativos} ativos disponíveis ({percentual_disponivel:.1f}%)")
                
                # Mostrar alguns ativos disponíveis (até 5)
                amostra_disponiveis = ativos_disponiveis[:5]
                BOT2_LOGGER.info(f"[PRE-SINAL][{hora_formatada}] 🟢 Exemplos disponíveis: {', '.join(amostra_disponiveis)}{' e outros...' if len(ativos_disponiveis) > 5 else ''}")
                
                # Verificar conexão com a API do Telegram
                BOT2_LOGGER.info(f"[PRE-SINAL][{hora_formatada}] 🔄 Verificando conexão com a API do Telegram...")
                
                try:
                    url = f"https://api.telegram.org/bot{BOT2_TOKEN}/getMe"
                    resposta = requests.get(url, timeout=10)
                    
                    if resposta.status_code == 200:
                        bot_info = resposta.json()
                        BOT2_LOGGER.info(f"[PRE-SINAL][{hora_formatada}] ✅ Conexão com API OK! Bot: @{bot_info['result']['username']}")
                    else:
                        BOT2_LOGGER.error(f"[PRE-SINAL][{hora_formatada}] ❌ Falha na conexão com API: {resposta.status_code} - {resposta.text}")
                        BOT2_LOGGER.warning(f"[PRE-SINAL][{hora_formatada}] ⚠️ Recomendado verificar a conexão antes do envio do sinal!")
                except Exception as e:
                    BOT2_LOGGER.error(f"[PRE-SINAL][{hora_formatada}] ❌ Erro ao verificar API: {str(e)}")
                    BOT2_LOGGER.warning(f"[PRE-SINAL][{hora_formatada}] ⚠️ Tente reiniciar o bot se o problema persistir!")
                    
            except Exception as e:
                agora = bot2_obter_hora_brasilia()
                BOT2_LOGGER.error(f"[PRE-SINAL][{agora.strftime('%H:%M:%S')}] ❌ Erro ao fazer verificação pré-sinal: {str(e)}")
                BOT2_LOGGER.error(f"[PRE-SINAL][{agora.strftime('%H:%M:%S')}] 🔍 Detalhes: {traceback.format_exc()}")
        
        # Agendar para o minuto 13 de cada hora
        schedule.every().hour.at(":13").do(enviar_sinal_com_verificacao).tag("bot2_sinais")
        
        # Agendar verificação prévia 3 minutos antes do sinal
        schedule.every().hour.at(":10").do(verificar_ativos_pre_sinal).tag("verificacao_previa")
        
        # Agendar reset do controle de duplicação a cada hora
        schedule.every().hour.at(":00").do(verificar_e_resetar_controle_sinal_minuto_13).tag("reset_controle")
        
        # Marcar como agendado
        bot2_sinais_agendados = True
        
        return True
    except Exception as e:
        BOT2_LOGGER.error(f"❌ Erro ao iniciar ciclo de sinais: {str(e)}")
        BOT2_LOGGER.error(f"🔍 Detalhes: {traceback.format_exc()}")
        return False


def iniciar_ambos_bots():
    """
    Inicializa o Bot 2 e mantém o programa em execução,
    tratando as tarefas agendadas periodicamente.
    """
    global bot2_sinais_agendados, BOT2_LOGGER
    
    try:
        # Verificar configurações antes de iniciar
        if not verificar_configuracoes_bot():
            BOT2_LOGGER.error("Falha na verificação de configurações. Corriga os erros antes de iniciar o bot.")
            return False
            
        # Iniciar o Bot 2
        if not bot2_sinais_agendados:
            bot2_iniciar_ciclo_sinais()  # Agendar sinais para o Bot 2
            
        BOT2_LOGGER.info("=== BOT 2 INICIADO COM SUCESSO! ===")
        BOT2_LOGGER.info("Aguardando envio de sinais nos horários programados...")
        
        # Teste inicial (descomentar para testes)
        # bot2_send_message(enviar_gif_imediatamente=True)
        
        # Loop principal para manter o programa em execução
        while True:
            try:
                # Executar tarefas agendadas
                schedule.run_pending()
                
                # Pausa para não sobrecarregar a CPU
                time.sleep(1)
            except KeyboardInterrupt:
                print("\nPrograma encerrado manualmente.")
                sys.exit(0)
            except Exception as e:
                BOT2_LOGGER.error(f"Erro no loop principal: {str(e)}")
                traceback.print_exc()
        
        return True
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao iniciar bots: {str(e)}")
        traceback.print_exc()
        return False

# Função para enviar sinal manualmente (para testes)
def enviar_sinal_manual():
    """Função para enviar um sinal manualmente para testes."""
    try:
        BOT2_LOGGER.info("Enviando sinal manualmente para teste...")
        resultado = bot2_send_message()
        
        if resultado:
            BOT2_LOGGER.info("Sinal manual enviado com sucesso!")
            return True
        else:
            BOT2_LOGGER.error("Falha ao enviar sinal manual.")
            return False
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar sinal manual: {str(e)}")
        traceback.print_exc()
        return False


def verificar_agendamento_sinais():
    """Verifica se os sinais estão agendados corretamente e reagenda se necessário."""
    global bot2_sinais_agendados, BOT2_LOGGER
    
    try:
        BOT2_LOGGER.info("Verificando agendamento de sinais...")
        
        # Verificar se há jobs agendados com a tag "bot2_sinais"
        jobs_sinais = schedule.get_jobs("bot2_sinais")
        
        if not jobs_sinais:
            BOT2_LOGGER.warning("Nenhum job de sinal agendado! Reagendando...")
            bot2_iniciar_ciclo_sinais()
            return True
        else:
            BOT2_LOGGER.info(f"Encontrados {len(jobs_sinais)} jobs de sinais agendados")
            for job in jobs_sinais:
                BOT2_LOGGER.info(f"Job agendado: {job}")
            return True
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao verificar agendamento de sinais: {str(e)}")
        traceback.print_exc()
        return False


def verificar_configuracoes_bot():
    """
    Verifica se as configurações do bot estão corretas antes de iniciar.
    
    Returns:
        bool: True se as configurações estão corretas, False caso contrário
    """
    global BOT2_LOGGER, BOT2_CANAIS_CONFIG, BOT2_TOKEN, ATIVOS_CATEGORIAS
    
    try:
        BOT2_LOGGER.info("Verificando configurações do bot...")
        
        # Verificar se o token está configurado
        if not BOT2_TOKEN or len(BOT2_TOKEN) < 10:
            BOT2_LOGGER.error("Token do bot não configurado ou inválido")
            return False
        
        # Verificar canais configurados
        if not BOT2_CANAIS_CONFIG:
            BOT2_LOGGER.error("Nenhum canal configurado para envio de sinais")
            return False
        
        # Contar o número total de canais
        total_canais = sum(len(chats) for chats in BOT2_CANAIS_CONFIG.values())
        if total_canais == 0:
            BOT2_LOGGER.error("Nenhum canal configurado para envio de sinais")
            return False
        
        # Verificar se existem ativos configurados
        if not ATIVOS_CATEGORIAS or "Digital" not in ATIVOS_CATEGORIAS:
            BOT2_LOGGER.error("Categoria 'Digital' não configurada ou sem ativos")
            return False
        
        if not ATIVOS_CATEGORIAS["Digital"]:
            BOT2_LOGGER.error("Nenhum ativo configurado na categoria 'Digital'")
            return False
        
        # Exibir resumo das configurações
        BOT2_LOGGER.info(f"Token do bot configurado: {BOT2_TOKEN[:5]}...{BOT2_TOKEN[-5:]}")
        BOT2_LOGGER.info(f"Total de canais configurados: {total_canais}")
        
        for idioma, chats in BOT2_CANAIS_CONFIG.items():
            BOT2_LOGGER.info(f"Canais para idioma '{idioma}': {len(chats)}")
        
        BOT2_LOGGER.info(f"Total de ativos na categoria 'Digital': {len(ATIVOS_CATEGORIAS['Digital'])}")
        BOT2_LOGGER.info("Todas as configurações estão corretas!")
        
        return True
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao verificar configurações: {str(e)}")
        traceback.print_exc()
        return False


def bot2_enviar_mensagem_abertura_corretora(idioma=None):
    """
    Envia mensagem de abertura da corretora para os canais do idioma especificado.
    Esta mensagem é enviada 55 minutos após o sinal principal (T+55) para sinais múltiplos de 3.
    
    Args:
        idioma: Idioma dos canais para enviar a mensagem (pt, en, es). 
                Se None, envia para todos os canais.
    
    Returns:
        bool: True se a mensagem foi enviada com sucesso, False caso contrário
    """
    try:
        # Obter hora atual para os logs
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        
        BOT2_LOGGER.info(f"[ABERTURA][{horario_atual}] 🔄 Iniciando envio da mensagem de abertura da corretora" + (f" para idioma {idioma}" if idioma else ""))
        
        # Links de afiliados por idioma
        links = {
            "pt": "https://trade.xxbroker.com/register?aff=741613&aff_model=revenue&afftrack=",
            "en": "https://trade.xxbroker.com/register?aff=741727&aff_model=revenue&afftrack=",
            "es": "https://trade.xxbroker.com/register?aff=741726&aff_model=revenue&afftrack="
        }
        
        # Mensagens por idioma
        mensagens = {
            "pt": f"""👉🏼Abram a corretora Pessoal

⚠️FIQUEM ATENTOS⚠️

🔥Cadastre-se na XXBROKER agora mesmo🔥

➡️ <a href="{links['pt']}">CLICANDO AQUI</a>""",
            
            "en": f"""👉🏼Open your broker account now

⚠️STAY ALERT⚠️

🔥Register at XXBROKER right now🔥

➡️ <a href="{links['en']}">CLICK HERE</a>""",
            
            "es": f"""👉🏼Abran su cuenta de corredor ahora

⚠️ESTÉN ATENTOS⚠️

🔥Regístrese en XXBROKER ahora mismo🔥

➡️ <a href="{links['es']}">HAGA CLIC AQUÍ</a>"""
        }
        
        canais_enviados = 0
        total_canais = 0
        
        # Determinar quais idiomas e canais processar
        if idioma is not None:
            # Se um idioma específico foi solicitado
            if idioma not in BOT2_CANAIS_CONFIG:
                BOT2_LOGGER.warning(f"[ABERTURA][{horario_atual}] ⚠️ Idioma {idioma} não configurado")
                return False
                
            idiomas_para_processar = {idioma: BOT2_CANAIS_CONFIG[idioma]}
        else:
            # Processar todos os idiomas
            idiomas_para_processar = BOT2_CANAIS_CONFIG
        
        # Para cada idioma, enviar mensagem para os canais configurados
        for idioma_atual, chats in idiomas_para_processar.items():
            if not chats:
                BOT2_LOGGER.info(f"[ABERTURA][{horario_atual}] ℹ️ Nenhum canal configurado para idioma {idioma_atual}")
                continue
                
            total_canais += len(chats)
            mensagem = mensagens.get(idioma_atual, mensagens["pt"])  # Usar PT como fallback
            
            BOT2_LOGGER.info(f"[ABERTURA][{horario_atual}] 📤 Enviando mensagem de abertura para {len(chats)} canais no idioma {idioma_atual}")
            
            for chat_id in chats:
                try:
                    # URL da API do Telegram
                    url = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
                    
                    # Payload da requisição
                    payload = {
                        "chat_id": chat_id,
                        "text": mensagem,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": False
                    }
                    
                    # Enviar mensagem
                    BOT2_LOGGER.info(f"[ABERTURA][{horario_atual}] 🚀 Enviando para chat_id: {chat_id}")
                    resposta = requests.post(url, json=payload, timeout=10)
                    
                    if resposta.status_code == 200:
                        BOT2_LOGGER.info(f"[ABERTURA][{horario_atual}] ✅ Mensagem de abertura enviada com sucesso para {chat_id}")
                        canais_enviados += 1
                    else:
                        BOT2_LOGGER.error(f"[ABERTURA][{horario_atual}] ❌ Erro ao enviar para {chat_id}: {resposta.status_code} - {resposta.text}")
                
                except Exception as e:
                    BOT2_LOGGER.error(f"[ABERTURA][{horario_atual}] ❌ Erro ao enviar para {chat_id}: {str(e)}")
                    BOT2_LOGGER.error(f"[ABERTURA][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
        
        # Verificar se pelo menos um canal recebeu a mensagem
        sucesso = canais_enviados > 0
        if sucesso:
            BOT2_LOGGER.info(f"[ABERTURA][{horario_atual}] ✅ Mensagem de abertura enviada com sucesso para {canais_enviados}/{total_canais} canais")
        else:
            BOT2_LOGGER.error(f"[ABERTURA][{horario_atual}] ❌ Falha ao enviar mensagem de abertura para todos os canais")
            
        return sucesso
            
    except Exception as e:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[ABERTURA][{horario_atual}] ❌ Erro geral ao enviar mensagem de abertura da corretora: {str(e)}")
        BOT2_LOGGER.error(f"[ABERTURA][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
        return False

# Atribuir a função à variável global para garantir acesso em todos os contextos
globals()['bot2_enviar_mensagem_abertura_corretora'] = bot2_enviar_mensagem_abertura_corretora

# Inicialização do sistema de envio de sinais
if __name__ == "__main__":
    try:
        print(f"\n{'=' * 50}")
        print(f"  INICIANDO BOT DE SINAIS")
        print(f"  TESTE IMEDIATO DE MENSAGENS SERÁ EXECUTADO")
        print(f"{'=' * 50}\n")
        
        # Configurar captura de exceções não tratadas para logar adequadamente
        def log_uncaught_exceptions(exctype, value, tb):
            BOT2_LOGGER.critical(f"❌ ERRO CRÍTICO NÃO TRATADO: {exctype.__name__}: {value}")
            BOT2_LOGGER.critical(f"🔍 Detalhes completos do erro:")
            traceback_str = ''.join(traceback.format_tb(tb))
            BOT2_LOGGER.critical(traceback_str)
            sys.__excepthook__(exctype, value, tb)  # Chamar o manipulador original
        
        # Substituir o manipulador padrão de exceções
        sys.excepthook = log_uncaught_exceptions
        
        # Configurar data e hora no início da execução
        data_inicio = datetime.now().strftime("%Y-%m-%d")
        hora_inicio = datetime.now().strftime("%H:%M:%S")
        
        # Configurar sistema de logging detalhado
        BOT2_LOGGER.info(f"🚀 INICIANDO SISTEMA DE SINAIS v2.0 ({data_inicio} {hora_inicio})")
        BOT2_LOGGER.info(f"🔧 Configurando ambiente e inicializando serviços...")
        
        # Definir o horário especial diário para enviar sinais
        definir_horario_especial_diario()
        
        # Agendar a redefinição do horário especial à meia-noite 
        agendar_redefinicao_horario_especial()
        
        # Iniciar sistema de envio de sinais
        BOT2_LOGGER.info(f"=== 🚀 Iniciando sistema de envio de sinais ===")
        
        # Testar a conexão com a API do Telegram antes de iniciar
        BOT2_LOGGER.info(f"🔄 Testando conexão com a API do Telegram...")
        
        url = f"https://api.telegram.org/bot{BOT2_TOKEN}/getMe"
        try:
            resposta = requests.get(url, timeout=10)
            if resposta.status_code == 200:
                bot_info = resposta.json()["result"]
                BOT2_LOGGER.info(f"✅ Conexão com API do Telegram OK! Bot: @{bot_info['username']} ({bot_info['first_name']})")
            else:
                BOT2_LOGGER.error(f"❌ Falha na conexão com a API do Telegram: {resposta.status_code} - {resposta.text}")
                BOT2_LOGGER.error(f"⚠️ Verifique o token do bot e a conexão com a internet")
                sys.exit(1)
        except Exception as e:
            BOT2_LOGGER.error(f"❌ Erro ao conectar com a API do Telegram: {str(e)}")
            BOT2_LOGGER.error(f"🔍 Detalhes: {traceback.format_exc()}")
            sys.exit(1)
            
        # IMPORTANTE: O teste imediato será executado apenas APÓS a definição das funções
        # no final do script. Isso garantirá que as funções não sejam None quando chamadas.
        
        # Continuar inicialização normal
        BOT2_LOGGER.info("🔄 Continuando inicialização normal do bot...")
            
        # Iniciar tentativas de inicialização do bot
        max_retries = 5
        retry_count = 0
        retry_delay = 10  # segundos
        
        # Código do loop principal de inicialização
        # ... existing code ...
    except Exception as e:
        print(f"Erro na inicialização: {str(e)}")
        BOT2_LOGGER.error(f"Erro na inicialização: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())

# Definição das funções enviar_mensagem_participacao e bot2_enviar_gif_promo
# Estas funções DEVEM estar definidas ANTES de serem chamadas

# Variável global para controlar a execução dos sinais no minuto 13
SINAL_MINUTO_13_JA_ENVIADO = False

# Função para garantir que o sinal do minuto 13 não seja duplicado
def verificar_e_resetar_controle_sinal_minuto_13():
    """
    Verifica e reseta a variável global de controle do sinal do minuto 13.
    Essa função é chamada no início de cada hora para garantir que o sinal
    possa ser enviado no próximo minuto 13.
    """
    global SINAL_MINUTO_13_JA_ENVIADO, BOT2_LOGGER
    
    # Resetar o controle no início de uma nova hora
    if SINAL_MINUTO_13_JA_ENVIADO:
        hora_atual = bot2_obter_hora_brasilia()
        BOT2_LOGGER.info(f"[CONTROLE][{hora_atual.strftime('%H:%M:%S')}] 🔄 Resetando controle de sinal para minuto 13 da próxima hora")
        SINAL_MINUTO_13_JA_ENVIADO = False
    
    return True

# Função para enviar o sinal com verificação prévia
def enviar_sinal_com_verificacao():
    """Função que verifica ativos disponíveis antes de enviar o sinal."""
    global SINAL_MINUTO_13_JA_ENVIADO
    
    try:
        # Obter hora atual
        hora_atual = bot2_obter_hora_brasilia()
        hora_formatada = hora_atual.strftime("%H:%M:%S")
        minuto_atual = hora_atual.minute
        
        # Verificar se estamos no minuto 13 e se o sinal já foi enviado nesta hora
        if minuto_atual == 13 and SINAL_MINUTO_13_JA_ENVIADO:
            BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] ⚠️ Sinal do minuto 13 já foi enviado nesta hora. Ignorando duplicação.")
            return False
        
        BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 🔔 INICIANDO CICLO DE ENVIO DE SINAL")
        BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 🕒 Hora atual: {hora_atual.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Verificar ativos disponíveis no momento do envio
        BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 🔍 Verificando ativos disponíveis em tempo real...")
        ativos_disponiveis = bot2_verificar_disponibilidade()
        
        if not ativos_disponiveis:
            BOT2_LOGGER.warning(f"[SINAL][{hora_formatada}] ⚠️ ALERTA: Nenhum ativo disponível neste momento!")
            BOT2_LOGGER.warning(f"[SINAL][{hora_formatada}] ⚠️ O sinal NÃO será enviado!")
            return False
        
        total_ativos = len(ATIVOS_CATEGORIAS["Digital"])
        percentual_disponivel = (len(ativos_disponiveis) / total_ativos) * 100
        
        BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] ✅ {len(ativos_disponiveis)}/{total_ativos} ativos disponíveis ({percentual_disponivel:.1f}%)")
        
        # Mostra alguns ativos disponíveis (até 5)
        amostra_disponiveis = ativos_disponiveis[:5]
        BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 🟢 Exemplos disponíveis: {', '.join(amostra_disponiveis)}{' e outros...' if len(ativos_disponiveis) > 5 else ''}")
        
        # Verificar conexão com a API do Telegram antes de enviar
        BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 🔄 Verificando conexão com a API do Telegram...")
        
        try:
            url = f"https://api.telegram.org/bot{BOT2_TOKEN}/getMe"
            resposta = requests.get(url, timeout=10)
            
            if resposta.status_code == 200:
                bot_info = resposta.json()
                BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] ✅ Conexão com API OK! Bot: @{bot_info['result']['username']}")
            else:
                BOT2_LOGGER.error(f"[SINAL][{hora_formatada}] ❌ Falha na conexão com API: {resposta.status_code} - {resposta.text}")
                BOT2_LOGGER.warning(f"[SINAL][{hora_formatada}] ⚠️ Tentando enviar sinal mesmo assim...")
        except Exception as e:
            BOT2_LOGGER.error(f"[SINAL][{hora_formatada}] ❌ Erro ao verificar API: {str(e)}")
            BOT2_LOGGER.warning(f"[SINAL][{hora_formatada}] ⚠️ Tentando enviar sinal mesmo assim...")
        
        # Armazenar ativos disponíveis para uso na geração do sinal
        ATIVOS_CATEGORIAS["Digital_Disponiveis"] = ativos_disponiveis
        
        # Agora sim, enviar o sinal
        BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 🚀 Iniciando envio do sinal...")
        resultado = bot2_send_message(ignorar_anti_duplicacao=False, enviar_gif_imediatamente=False)
        
        if resultado:
            BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] ✅ Sinal enviado com sucesso!")
            
            # Marcar que o sinal do minuto 13 foi enviado nesta hora
            if minuto_atual == 13:
                SINAL_MINUTO_13_JA_ENVIADO = True
                BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 🔒 Sinal do minuto 13 marcado como enviado para esta hora")
            
            # Agendar verificação do próximo sinal
            proxima_hora = hora_atual + timedelta(hours=1)
            proxima_hora = proxima_hora.replace(minute=13, second=0, microsecond=0)
            BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 📅 Próximo sinal agendado para: {proxima_hora.strftime('%H:%M')}")
        else:
            BOT2_LOGGER.error(f"[SINAL][{hora_formatada}] ❌ Falha ao enviar sinal!")
            
            # Verificar se há erros de conexão e agendar uma tentativa em 5 minutos
            BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 🔄 Agendando nova tentativa em 5 minutos...")
            
            # Criar um job único para tentar novamente em 5 minutos
            proxima_tentativa = hora_atual + timedelta(minutes=5)
            BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 🕒 Próxima tentativa: {proxima_tentativa.strftime('%H:%M:%S')}")
        
        # Verificar e limpar tarefas desnecessárias para evitar acúmulo
        BOT2_LOGGER.info(f"[SINAL][{hora_formatada}] 🧹 Verificando e limpando tarefas pendentes...")
        
        return resultado
    except Exception as e:
        agora = bot2_obter_hora_brasilia()
        BOT2_LOGGER.error(f"[SINAL][{agora.strftime('%H:%M:%S')}] ❌ Erro crítico ao enviar sinal: {str(e)}")
        BOT2_LOGGER.error(f"[SINAL][{agora.strftime('%H:%M:%S')}] 🔍 Detalhes: {traceback.format_exc()}")
        return False

def enviar_mensagem_participacao():
    """
    Envia a mensagem de participação 27 minutos após o sinal principal para sinais múltiplos de 3.
    
    Retorna: True se enviado com sucesso, False caso contrário.
    """
    try:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[PARTICIPACAO][{horario_atual}] 🔄 Iniciando envio da mensagem de participação")
        
        # Links específicos para cada idioma
        link_pt = "https://trade.xxbroker.com/register?aff=741613&aff_model=revenue&afftrack="
        link_en = "https://trade.xxbroker.com/register?aff=741727&aff_model=revenue&afftrack="
        link_es = "https://trade.xxbroker.com/register?aff=741726&aff_model=revenue&afftrack="
        
        # Links dos vídeos para cada idioma
        video_pt = "https://t.me/trendingbrazil/215"
        video_en = "https://t.me/trendingenglish/226"
        video_es = "https://t.me/trendingespanish/212"
        
        # Mensagens para cada idioma com os links incorporados em HTML
        mensagem_pt = f"""⚠️⚠️PARA PARTICIPAR DESTA SESSÃO, SIGA O PASSO A PASSO ABAIXO⚠️⚠️

1º ✅ —>  Crie sua conta na corretora no link abaixo e GANHE $10.000 DE GRAÇA pra começar a operar com a gente sem ter que arriscar seu dinheiro.

Você vai poder testar todos nossas
operações com risco ZERO!

👇🏻👇🏻👇🏻👇🏻

<a href="{link_pt}"><b>CRIE SUA CONTA AQUI E GANHE R$10.000</b></a>

—————————————————————

2º ✅ —>  Assista o vídeo abaixo e aprenda como depositar e como entrar com a gente nas nossas operações!

👇🏻👇🏻👇🏻👇🏻

<a href="{video_pt}"><b>CLIQUE AQUI E ASSISTA O VÍDEO</b></a>"""

        mensagem_en = f"""⚠️⚠️TO PARTICIPATE IN THIS SESSION, FOLLOW THE STEPS BELOW⚠️⚠️

1st ✅ —> Create your broker account at the link below and GET $10,000 FOR FREE to start operating with us without having to risk your money.

You will be able to test all our
operations with ZERO risk!

👇🏻👇🏻👇🏻👇🏻

<a href="{link_en}"><b>CREATE YOUR ACCOUNT HERE AND GET $10,000</b></a>

—————————————————————

2nd ✅ —> Watch the video below and learn how to deposit and how to join us in our operations!

👇🏻👇🏻👇🏻👇🏻

<a href="{video_en}"><b>CLICK HERE AND WATCH THE VIDEO</b></a>"""

        mensagem_es = f"""⚠️⚠️PARA PARTICIPAR EN ESTA SESIÓN, SIGA LOS PASOS A CONTINUACIÓN⚠️⚠️

1º ✅ —> Cree su cuenta de corredor en el enlace a continuación y OBTENGA $10,000 GRATIS para comenzar a operar con nosotros sin tener que arriesgar su dinero.

Podrás probar todas nuestras
operaciones con riesgo CERO!

👇🏻👇🏻👇🏻👇🏻

<a href="{link_es}"><b>CREE SU CUENTA AQUÍ Y OBTENGA $10,000</b></a>

—————————————————————

2º ✅ —> ¡Mire el video a continuación y aprenda cómo depositar y cómo unirse a nosotros en nuestras operaciones!

👇🏻👇🏻👇🏻👇🏻

<a href="{video_es}"><b>HAGA CLIC AQUÍ Y VEA EL VIDEO</b></a>"""
        
        mensagens_enviadas = []
        
        # Enviar para cada idioma configurado
        for idioma, chats in BOT2_CANAIS_CONFIG.items():
            if not chats:
                BOT2_LOGGER.info(f"[PARTICIPACAO][{horario_atual}] ℹ️ Nenhum chat configurado para idioma {idioma}")
                continue
                
            # Selecionar a mensagem conforme o idioma
            if idioma == "pt":
                mensagem = mensagem_pt
            elif idioma == "en":
                mensagem = mensagem_en
            elif idioma == "es":
                mensagem = mensagem_es
            else:
                mensagem = mensagem_pt  # Usar PT como fallback
                
            BOT2_LOGGER.info(f"[PARTICIPACAO][{horario_atual}] 📤 Enviando mensagem de participação para {len(chats)} canais no idioma {idioma}")
            
            # Enviar para cada canal deste idioma
            for chat_id in chats:
                try:
                    # Construir URL da API
                    url = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
                    
                    # Montar payload
                    payload = {
                        "chat_id": chat_id,
                        "text": mensagem,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    }
                    
                    # Enviar mensagem
                    BOT2_LOGGER.info(f"[PARTICIPACAO][{horario_atual}] 🚀 Enviando para chat_id: {chat_id}")
                    resposta = requests.post(url, json=payload, timeout=10)
                    
                    if resposta.status_code == 200:
                        BOT2_LOGGER.info(f"[PARTICIPACAO][{horario_atual}] ✅ Mensagem de participação enviada com sucesso para {chat_id}")
                        mensagens_enviadas.append(True)
                    else:
                        BOT2_LOGGER.error(f"[PARTICIPACAO][{horario_atual}] ❌ Erro ao enviar para {chat_id}: {resposta.status_code} - {resposta.text}")
                        mensagens_enviadas.append(False)
                        
                except Exception as e:
                    BOT2_LOGGER.error(f"[PARTICIPACAO][{horario_atual}] ❌ Erro ao enviar para {chat_id}: {str(e)}")
                    BOT2_LOGGER.error(f"[PARTICIPACAO][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
                    mensagens_enviadas.append(False)
        
        # Verificar se pelo menos uma mensagem foi enviada com sucesso
        sucesso = any(mensagens_enviadas)
        if sucesso:
            BOT2_LOGGER.info(f"[PARTICIPACAO][{horario_atual}] ✅ Mensagem de participação enviada com sucesso para pelo menos um canal")
        else:
            BOT2_LOGGER.error(f"[PARTICIPACAO][{horario_atual}] ❌ Falha ao enviar mensagem de participação para todos os canais")
            
        return sucesso
            
    except Exception as e:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[PARTICIPACAO][{horario_atual}] ❌ Erro geral ao enviar mensagem de participação: {str(e)}")
        BOT2_LOGGER.error(f"[PARTICIPACAO][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
        return False

def bot2_enviar_gif_promo(idioma="pt"):
    """
    Envia o GIF promocional para todos os canais do idioma especificado.
    Este GIF é enviado 35 minutos após o sinal original (T+35) para sinais múltiplos de 3.
    
    Args:
        idioma: Idioma dos canais para enviar o GIF (pt, en, es)
        
    Returns:
        bool: True se o GIF foi enviado com sucesso, False caso contrário
    """
    global BOT2_LOGGER, BOT2_CANAIS_CONFIG, BOT2_TOKEN
    
    try:
        # Obter hora atual em Brasília para os logs
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        
        BOT2_LOGGER.info(f"[GIF-PROMO][{horario_atual}] 🔄 Iniciando envio de GIF promocional para idioma {idioma}")
        
        # Verificar se há canais configurados para o idioma
        if idioma not in BOT2_CANAIS_CONFIG or not BOT2_CANAIS_CONFIG[idioma]:
            BOT2_LOGGER.warning(f"[GIF-PROMO][{horario_atual}] ⚠️ Nenhum canal configurado para idioma {idioma}")
            return False
        
        # Canais para este idioma
        chats = BOT2_CANAIS_CONFIG[idioma]
        BOT2_LOGGER.info(f"[GIF-PROMO][{horario_atual}] 📢 Total de canais para idioma {idioma}: {len(chats)}")
        
        # Usar a mesma URL do GIF promocional para todos os idiomas
        gif_url = "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZGhqMmNqOWFpbTQ2cjNxMzF1YncxcnAwdTFvN2o1NWRmc2dvYXZ6bCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/whPiIq21hxXuJn7WVX/giphy.gif"
        
        # Verificar se a URL do GIF é válida
        if not verificar_url_gif(gif_url):
            BOT2_LOGGER.warning(f"[GIF-PROMO][{horario_atual}] ⚠️ URL do GIF promocional inválida: {gif_url}")
            # Usar URL alternativa se a verificação falhar
            gif_url = "https://i.imgur.com/jphWAEq.gif"
            BOT2_LOGGER.info(f"[GIF-PROMO][{horario_atual}] 🔄 Usando URL alternativa: {gif_url}")
        
        # Lista para armazenar resultados dos envios
        resultados_envio = []
        enviados_com_sucesso = 0
        
        # Enviar para cada canal configurado
        for chat_id in chats:
            try:
                # URL para o método sendAnimation da API do Telegram (para GIFs)
                url = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendAnimation"
                
                # Montar payload da requisição
                payload = {
                    "chat_id": chat_id,
                    "animation": gif_url,
                    "disable_notification": False
                }
                
                BOT2_LOGGER.info(f"[GIF-PROMO][{horario_atual}] 🚀 Enviando GIF promocional para chat_id: {chat_id}")
                
                # Enviar requisição para API
                inicio_envio = time.time()
                resposta = requests.post(url, json=payload, timeout=15)
                tempo_resposta = (time.time() - inicio_envio) * 1000  # em milissegundos
                
                # Verificar resultado da requisição
                if resposta.status_code == 200:
                    BOT2_LOGGER.info(f"[GIF-PROMO][{horario_atual}] ✅ GIF promocional enviado com sucesso para {chat_id} (tempo: {tempo_resposta:.1f}ms)")
                    resultados_envio.append(True)
                    enviados_com_sucesso += 1
                else:
                    BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] ❌ Falha ao enviar GIF promocional para {chat_id}: {resposta.status_code} - {resposta.text}")
                    resultados_envio.append(False)
                    
                    # Tentar novamente uma vez se falhar
                    BOT2_LOGGER.info(f"[GIF-PROMO][{horario_atual}] 🔄 Tentando novamente para {chat_id}...")
                    try:
                        resposta_retry = requests.post(url, json=payload, timeout=15)
                        if resposta_retry.status_code == 200:
                            BOT2_LOGGER.info(f"[GIF-PROMO][{horario_atual}] ✅ GIF promocional enviado com sucesso na segunda tentativa para {chat_id}")
                            resultados_envio.append(True)
                            enviados_com_sucesso += 1
                        else:
                            BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] ❌ Falha na segunda tentativa: {resposta_retry.status_code}")
                    except Exception as e:
                        BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] ❌ Erro na segunda tentativa: {str(e)}")
                        
            except Exception as e:
                BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] ❌ Exceção ao enviar GIF promocional para {chat_id}: {str(e)}")
                BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
                resultados_envio.append(False)
        
        # Calcular estatísticas finais
        if chats:
            taxa_sucesso = (enviados_com_sucesso / len(chats)) * 100
            BOT2_LOGGER.info(f"[GIF-PROMO][{horario_atual}] 📊 RESUMO: {enviados_com_sucesso}/{len(chats)} GIFs promocionais enviados com sucesso ({taxa_sucesso:.1f}%)")
        
        # Retornar True se pelo menos um GIF foi enviado com sucesso
        envio_bem_sucedido = any(resultados_envio)
        
        if envio_bem_sucedido:
            BOT2_LOGGER.info(f"[GIF-PROMO][{horario_atual}] ✅ Envio de GIF promocional para idioma {idioma} concluído com sucesso")
        else:
            BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] ❌ Falha em todos os envios de GIF promocional para idioma {idioma}")
        
        return envio_bem_sucedido
    
    except Exception as e:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] ❌ Erro crítico ao enviar GIF promocional: {str(e)}")
        BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
        return False

# Garantir que as funções estejam registradas no escopo global
globals()['enviar_mensagem_participacao'] = enviar_mensagem_participacao
globals()['bot2_enviar_gif_promo'] = bot2_enviar_gif_promo

# Variável de controle para executar o teste apenas uma vez
TESTE_JA_EXECUTADO = False

def executar_teste_imediato_mensagens():
    """
    Função para executar o teste imediato de mensagens uma única vez.
    Envia uma mensagem de participação e um GIF promocional para os canais em espanhol.
    """
    global TESTE_JA_EXECUTADO
    
    # Se o teste já foi executado, não executar novamente
    if TESTE_JA_EXECUTADO:
        BOT2_LOGGER.info("Teste já foi executado anteriormente, seguindo fluxo normal.")
        return True
        
    BOT2_LOGGER.info("="*70)
    BOT2_LOGGER.info("===== INICIANDO TESTE IMEDIATO =====")
    BOT2_LOGGER.info("="*70)
    
    # Verificar se as funções estão definidas corretamente
    if 'enviar_mensagem_participacao' not in globals() or not callable(globals()['enviar_mensagem_participacao']):
        BOT2_LOGGER.error("❌ ERRO CRÍTICO: Função enviar_mensagem_participacao não está definida ou não é callable!")
        return False
        
    if 'bot2_enviar_gif_promo' not in globals() or not callable(globals()['bot2_enviar_gif_promo']):
        BOT2_LOGGER.error("❌ ERRO CRÍTICO: Função bot2_enviar_gif_promo não está definida ou não é callable!")
        return False
    
    # Obter referências às funções
    func_mensagem = globals()['enviar_mensagem_participacao']
    func_gif = globals()['bot2_enviar_gif_promo']
    
    # Executar teste direto para o canal ES
    canais_es = BOT2_CANAIS_CONFIG.get("es", [])
    BOT2_LOGGER.info(f"📢 Canais em espanhol: {canais_es}")
    
    try:
        # Backup da configuração original
        canais_backup = copy.deepcopy(BOT2_CANAIS_CONFIG)
        
        # Modificar temporariamente para enviar apenas para ES
        canais_temp = {"es": canais_es, "pt": [], "en": []}
        BOT2_CANAIS_CONFIG.clear()
        BOT2_CANAIS_CONFIG.update(canais_temp)
        
        # 1. Enviar mensagem de participação
        BOT2_LOGGER.info("🚀 ENVIANDO MENSAGEM DE PARTICIPAÇÃO PARA CANAL ES...")
        try:
            resultado = func_mensagem()
            BOT2_LOGGER.info(f"📋 Resultado mensagem participação: {'✅ SUCESSO' if resultado else '❌ FALHA'}")
        except Exception as e:
            BOT2_LOGGER.error(f"❌ ERRO AO ENVIAR MENSAGEM DE PARTICIPAÇÃO: {str(e)}")
            BOT2_LOGGER.error(traceback.format_exc())
        
        # Aguardar 5 segundos
        BOT2_LOGGER.info("⏱️ Aguardando 5 segundos...")
        time.sleep(5)
        
        # 2. Enviar GIF promocional
        BOT2_LOGGER.info("🎬 ENVIANDO GIF PROMOCIONAL PARA CANAL ES...")
        try:
            resultado = func_gif("es")
            BOT2_LOGGER.info(f"📋 Resultado GIF promocional: {'✅ SUCESSO' if resultado else '❌ FALHA'}")
        except Exception as e:
            BOT2_LOGGER.error(f"❌ ERRO AO ENVIAR GIF PROMOCIONAL: {str(e)}")
            BOT2_LOGGER.error(traceback.format_exc())
            
    finally:
        # Restaurar configuração original
        BOT2_CANAIS_CONFIG.clear()
        BOT2_CANAIS_CONFIG.update(canais_backup)
        BOT2_LOGGER.info("🔄 Configuração original de canais restaurada")
        
    BOT2_LOGGER.info("="*70)
    BOT2_LOGGER.info("===== FIM DO TESTE IMEDIATO =====")
    BOT2_LOGGER.info("="*70)
    
    # Marcar o teste como executado
    TESTE_JA_EXECUTADO = True
    
    return True

# Executar este teste imediatamente após todas as definições de funções
if __name__ == "__main__" and 'enviar_mensagem_participacao' in globals() and 'bot2_enviar_gif_promo' in globals():
    # Verificar se já foi executado antes (para casos de reinicialização do script)
    if not TESTE_JA_EXECUTADO:
        # Verificar se ambas as funções existem e estão definidas corretamente
        BOT2_LOGGER.info("🧪 Executando teste imediato de mensagens...")
        executar_teste_imediato_mensagens()
    else:
        BOT2_LOGGER.info("🔄 Teste já foi executado anteriormente, pulando execução")
    
    # Após o teste, iniciar o ciclo normal do bot
    BOT2_LOGGER.info("🚀 Iniciando ciclo normal de sinais após teste inicial...")
    bot2_iniciar_ciclo_sinais()
