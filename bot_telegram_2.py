# -*- coding: utf-8 -*-
"""
Bot Telegram para envio automatizado de sinais.

Lógica de sinais implementada:

1. Sinais normais (não múltiplos de 3):
   - Envia o sinal para todos os canais
   - Após 7 minutos, envia o GIF pós-sinal OU a mensagem de perda (apenas uma vez por dia)

2. Sinais múltiplos de 3:
   - Envia o sinal para todos os canais
   - Após 7 minutos, envia o GIF pós-sinal OU a mensagem de perda (apenas uma vez por dia)
   - Após 30 minutos, envia o GIF especial
   - 1 minuto depois do GIF especial, envia a mensagem de cadastro
   - 9 minutos depois da mensagem de cadastro, envia o GIF promo
   - 1 minuto depois do GIF promo, envia a mensagem de abertura da corretora

Todas as mensagens são enviadas para os canais configurados em português, inglês e espanhol,
com os respectivos links personalizados para cada idioma.
"""

import os
import sys
import time
import json
import random
import logging
import traceback
import requests
import schedule
import pytz
import telebot
from functools import lru_cache
from datetime import datetime, timedelta

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot_telegram.log", encoding="utf-8"),
    ],
)

# Logger para o Bot 2
BOT2_LOGGER = logging.getLogger("BOT2")

# Inicializar variáveis globais
bot2_sinais_agendados = False
bot2_contador_sinais = 0
ultimo_sinal_enviado = None

# Token do Bot Telegram
BOT2_TOKEN = "7997585882:AAFDyG-BYskj1gyAbh17X5jd6DDClXdluww"

# Inicialização do bot
bot2 = telebot.TeleBot(BOT2_TOKEN)

# Canais de envio configurados por idioma
BOT2_CANAIS_CONFIG = {
    "-1002424874613": {  # Canal para mensagens em português
        "idioma": "pt",
        "link_corretora": "https://trade.xxbroker.com/register?aff=741613&aff_model=revenue&afftrack=",
        "fuso_horario": "America/Sao_Paulo",  # Brasil (UTC-3)
    },
    "-1002453956387": {  # Canal para mensagens em inglês
        "idioma": "en",
        "link_corretora": "https://trade.xxbroker.com/register?aff=741727&aff_model=revenue&afftrack=",
        # EUA (UTC-5 ou UTC-4 no horário de verão)
        "fuso_horario": "America/New_York",
    },
    "-1002446547846": {  # Canal para mensagens em espanhol
        "idioma": "es",
        "link_corretora": "https://trade.xxbroker.com/register?aff=741726&aff_model=revenue&afftrack=",
        # Espanha (UTC+1 ou UTC+2 no horário de verão)
        "fuso_horario": "Europe/Madrid",
    },
}

# Lista de IDs dos canais
BOT2_CHAT_IDS = list(BOT2_CANAIS_CONFIG.keys())

# URLs dos GIFs
URLS_GIFS_DIRETAS = {
    "pos_sinal_padrao": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExaWVtYnVhamd3bm01OXZyNmYxYTdteDljNDFrMGZybWx1dXJkbmo2cyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PDTiu190mvjkifkbG5/giphy.gif",
    "gif_especial_pt": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExaWVtYnVhamd3bm01OXZyNmYxYTdteDljNDFrMGZybWx1dXJkbmo2cyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PDTiu190mvjkifkbG5/giphy.gif",
    "promo_pt": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExaWVtYnVhamd3bm01OXZyNmYxYTdteDljNDFrMGZybWx1dXJkbmo2cyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PDTiu190mvjkifkbG5/giphy.gif",
    "promo_en": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExaWVtYnVhamd3bm01OXZyNmYxYTdteDljNDFrMGZybWx1dXJkbmo2cyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PDTiu190mvjkifkbG5/giphy.gif",
    "promo_es": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExaWVtYnVhamd3bm01OXZyNmYxYTdteDljNDFrMGZybWx1dXJkbmo2cyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PDTiu190mvjkifkbG5/giphy.gif",
}

# Configurações do bot
CONFIG_JSON = {
    "modo_operacional": True,
    "sinais_habilitados": True,
    "segundos_espera_gif_pos_sinal": 60,
    "link_corretora": "https://trade.xxbroker.com/register?aff=741613&aff_model=revenue&afftrack=",
    "bot2_canais": {
        "pt": ["-1002424874613"],
        "en": ["-1002453956387"],
        "es": ["-1002446547846"]
    }
}

# Limite máximo de sinais por hora
BOT2_LIMITE_SINAIS_POR_HORA = 1

# Definição da variável global assets
assets = {}

# Definição de outras variáveis globais
ultimo_ativo = None

# Base URL do GitHub para os arquivos
GITHUB_BASE_URL = "https://raw.githubusercontent.com/igoredson/signalbotrender/main/"

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
    "promo_pt": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExaWVtYnVhamd3bm01OXZyNmYxYTdteDljNDFrMGZybWx1dXJkbmo2cyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PDTiu190mvjkifkbG5/giphy.gif",
    "promo_en": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExaWVtYnVhamd3bm01OXZyNmYxYTdteDljNDFrMGZybWx1dXJkbmo2cyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PDTiu190mvjkifkbG5/giphy.gif",
    "promo_es": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExaWVtYnVhamd3bm01OXZyNmYxYTdteDljNDFrMGZybWx1dXJkbmo2cyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PDTiu190mvjkifkbG5/giphy.gif",
    "pos_sinal_padrao": "https://raw.githubusercontent.com/IgorElion/-TelegramBot/main/videos/pos_sinal/pt/180398513446716419%20(7).webp",
    "gif_especial_pt": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExN2tzdzB4bjNjaWo4bm9zdDR3d2g4bmQzeHRqcWx6MTQxYTA1cjRoeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/E2EknXAKA5ac8gKVxu/giphy.gif"
}

# ID para compatibilidade com cdigo existente
BOT2_CHAT_ID_CORRETO = BOT2_CHAT_IDS[0]  # Usar o primeiro canal como padro

# Definição das categorias de ativos e seus horários de funcionamento
ATIVOS_CATEGORIAS = {
    "Digital": [
        "EUR/USD", "GBP/USD", "AUD/USD", "USD/JPY", "USD/CHF", "USD/CAD", "EUR/JPY", 
        "EUR/GBP", "AUD/JPY", "GBP/JPY", "CHF/JPY", "CAD/JPY", "NZD/USD", "EUR/AUD", 
        "EUR/CAD", "EUR/CHF", "AUD/CAD", "AUD/CHF", "GBP/CAD", "GBP/CHF", "EUR/NZD", 
        "USD/MXN", "USD/ZAR", "USD/TRY", "USD/NOK", "USD/SEK", "USD/DKK", "USD/HKD", 
        "USD/SGD", "USD/PLN", "USD/CZK", "USD/HUF", "USD/ILS", "EUR/CZK", "EUR/DKK", 
        "EUR/HUF", "EUR/NOK", "EUR/PLN", "EUR/SEK", "EUR/TRY", "EUR/ZAR", "GBP/AUD",
        "GBP/NZD", "AUD/NZD"
    ],
    "OTC": [
        "OTC EUR/USD", "OTC GBP/USD", "OTC AUD/USD", "OTC USD/JPY", "OTC EUR/JPY", 
        "OTC GBP/JPY", "OTC EUR/GBP", "OTC USD/CHF", "OTC EUR/CHF", "OTC AUD/CAD"
    ],
    "Crypto": [
        "BTC/USD", "ETH/USD", "LTC/USD", "XRP/USD", "EOS/USD", "BTC/ETH"
    ]
}

# Horários de funcionamento das categorias de ativos por dia da semana
HORARIOS_CATEGORIAS = {
    "Digital": {
        "Monday": [("00:00", "23:59")],   # Segunda-feira: 24 horas
        "Tuesday": [("00:00", "23:59")],  # Terça-feira: 24 horas
        "Wednesday": [("00:00", "23:59")],# Quarta-feira: 24 horas
        "Thursday": [("00:00", "23:59")], # Quinta-feira: 24 horas
        "Friday": [("00:00", "22:00")],   # Sexta-feira: até 22h (UTC)
        "Saturday": [],                   # Sábado: fechado
        "Sunday": [("21:00", "23:59")]    # Domingo: a partir das 21h
    },
    "OTC": {
        "Monday": [],                    # Segunda-feira: fechado
        "Tuesday": [],                   # Terça-feira: fechado
        "Wednesday": [],                 # Quarta-feira: fechado
        "Thursday": [],                  # Quinta-feira: fechado
        "Friday": [],                    # Sexta-feira: fechado
        "Saturday": [("00:00", "23:59")],# Sábado: 24 horas
        "Sunday": [("00:00", "21:00")]   # Domingo: até 21h (UTC)
    },
    "Crypto": {
        "Monday": [("00:00", "23:59")],   # Segunda-feira: 24 horas
        "Tuesday": [("00:00", "23:59")],  # Terça-feira: 24 horas
        "Wednesday": [("00:00", "23:59")],# Quarta-feira: 24 horas
        "Thursday": [("00:00", "23:59")], # Quinta-feira: 24 horas
        "Friday": [("00:00", "23:59")],   # Sexta-feira: 24 horas
        "Saturday": [("00:00", "23:59")], # Sábado: 24 horas
        "Sunday": [("00:00", "23:59")]    # Domingo: 24 horas
    }
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
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
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
    "USD/CAD": {
        "Monday": ["03:00-15:00"],
        "Tuesday": ["03:00-15:00", "21:00-23:59"],
        "Wednesday": ["00:00-15:00"],
        "Thursday": ["03:00-15:00"],
        "Friday": ["03:00-15:00"],
        "Saturday": [],
        "Sunday": [],
    },
    "USD/JPY": {
        "Monday": ["00:00-14:00", "23:00-23:59"],
        "Tuesday": ["00:00-14:00", "23:00-23:59"],
        "Wednesday": ["00:00-14:00", "23:00-23:59"],
        "Thursday": ["00:00-14:00", "23:00-23:59"],
        "Friday": ["00:00-14:00"],
        "Saturday": [],
        "Sunday": ["23:00-23:59"],
    },
    "MELANIA_Coin_OTC": {  # J existe, mantendo a mesma configurao
        "Monday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Tuesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Wednesday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Thursday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Friday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Saturday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
        "Sunday": ["00:00-05:00", "05:30-12:00", "12:30-23:59"],
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
    "promo_pt": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdnVvZ203ZXphMXc5N2dwMm1uaDk4Nmp4Z3A1OGkwZnd0a2JtdHo1bCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/1Q3HkjW2vvNTfAnPA4/giphy.gif",
    "promo_en": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExbnJqZDV6OWJsd2xtOXpvMjduMDB3Nnc1dG8zZG40NzY5aGtsMHV0OSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Btx7R7ul9qaeCt8eEk/giphy.gif",
    "promo_es": "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGY5aG93cTV4NWg2dzM2anpmaWd5ajlqenkwcjd3bXVjdG0wYnlmYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/5IG2JKmARkpsfMkp4z/giphy.gif",
    "pos_sinal_padrao": "https://raw.githubusercontent.com/IgorElion/-TelegramBot/main/videos/pos_sinal/pt/180398513446716419%20(7).webp",
    "gif_especial_pt": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExN2tzdzB4bjNjaWo4bm9zdDR3d2g4bmQzeHRqcWx6MTQxYTA1cjRoeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/E2EknXAKA5ac8gKVxu/giphy.gif"
}

# Adicionar variável global para controlar mensagem de perda enviada por dia
mensagem_perda_enviada_hoje = False

# Variável para armazenar o último sinal enviado
ultimo_sinal_enviado = None

# Contador para controlar a sequência de GIFs pós-sinal
contador_pos_sinal = 0

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
    Analisa uma string de intervalo de tempo no formato 'HH:MM-HH:MM' e 
    retorna um objeto que permite verificar se um horário está dentro desse intervalo.
    
    Args:
        time_str (str): String de intervalo de tempo no formato 'HH:MM-HH:MM'.
    
    Returns:
        TimeRange: Um objeto que pode ser usado para verificar se um horário está dentro do intervalo.
    """
    class TimeRange:
        def __init__(self, start, end):
            self.start = start
            self.end = end
        
        def is_time_within_range(self, time_to_check):
            """
            Verifica se um horário está dentro do intervalo.
            
            Args:
                time_to_check (str): Horário a ser verificado no formato 'HH:MM'.
            
            Returns:
                bool: True se o horário estiver dentro do intervalo, False caso contrário.
            """
            # Se o horário a verificar for um objeto datetime, converter para string
            if hasattr(time_to_check, 'strftime'):
                time_to_check = time_to_check.strftime("%H:%M")
                
            # Lidar com intervalos que atravessam a meia-noite
            if self.start <= self.end:
                return self.start <= time_to_check <= self.end
            else:
                return time_to_check >= self.start or time_to_check <= self.end
    
    try:
        # Verificar se a string está no formato esperado
        if not isinstance(time_str, str) or '-' not in time_str:
            raise ValueError(f"Formato de intervalo de tempo inválido: {time_str}")
            
        start_time, end_time = time_str.split('-')
        
        # Remover espaços em branco
        start_time = start_time.strip()
        end_time = end_time.strip()
        
        # Verificar se os horários têm o formato HH:MM
        for t in [start_time, end_time]:
            if len(t) != 5 or t[2] != ':' or not (t[0:2].isdigit() and t[3:5].isdigit()):
                raise ValueError(f"Formato de horário inválido: {t}")
        
        return TimeRange(start_time, end_time)
    except Exception as e:
        raise ValueError(f"Erro ao analisar intervalo de tempo '{time_str}': {str(e)}")


# Funo para verificar disponibilidade de ativos


def is_asset_available(asset, current_time=None, current_day=None):
    """
    Verifica se um ativo está disponível no horário atual.

    Args:
        asset (str): O nome do ativo a ser verificado
        current_time (datetime ou str, opcional): Horário atual (padrão: hora atual)
        current_day (str, opcional): Dia atual (padrão: dia atual)

    Returns:
        bool: True se o ativo estiver disponível, False caso contrário
    """
    try:
        # Se não for fornecido o horário atual, usar o horário atual de Brasília
        if current_time is None:
            current_time = bot2_obter_hora_brasilia()
            current_time_str = current_time.strftime("%H:%M")
        elif isinstance(current_time, str):
            current_time_str = current_time  # Já é uma string no formato HH:MM
        else:
            current_time_str = current_time.strftime("%H:%M")
            
        # Se não for fornecido o dia atual, usar o dia atual
        if current_day is None:
            current_day = bot2_obter_hora_brasilia().strftime("%A")
            
        # Verificar se o ativo está na lista de ativos disponíveis
        categoria = None
        for cat, ativos in ATIVOS_CATEGORIAS.items():
            if asset in ativos:
                categoria = cat
                break
                
        if categoria is None:
            BOT2_LOGGER.warning(f"Ativo {asset} não está registrado em nenhuma categoria.")
            return False
            
        # Obter o horário de funcionamento da categoria
        horario_range = HORARIOS_CATEGORIAS.get(categoria, {}).get(current_day)
        if not horario_range:
            BOT2_LOGGER.warning(f"Categoria {categoria} não tem horário definido para {current_day}.")
            return False
            
        # Verificar se o horário atual está dentro do range de funcionamento
        for start_time, end_time in horario_range:
            if parse_time_range(f"{start_time}-{end_time}").is_time_within_range(current_time_str):
                return True
                
        BOT2_LOGGER.warning(f"Ativo {asset} (categoria {categoria}) não está disponível em {current_day} às {current_time_str}.")
        return False
        
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao verificar disponibilidade do ativo {asset}: {str(e)}")
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
    """Verifica quais ativos estão disponíveis no momento para envio de sinais."""
    try:
        # Obter o horário atual de Brasília
        hora_atual = bot2_obter_hora_brasilia()
        hora_str = hora_atual.strftime("%H:%M")
        dia_atual = hora_atual.strftime("%A")
        
        BOT2_LOGGER.info(f"Verificando disponibilidade para o dia {dia_atual} às {hora_str}")
        
        # Contar quantos ativos da categoria Digital estão disponíveis
        total_ativos = len(ATIVOS_CATEGORIAS["Digital"])
        BOT2_LOGGER.info(f"Total de ativos na categoria Digital: {total_ativos}")
        
        # Verificar quantos ativos da categoria Digital estão disponíveis
        ativos_disponiveis = []
        for ativo in ATIVOS_CATEGORIAS["Digital"]:
            if is_asset_available(ativo, hora_atual, dia_atual):
                ativos_disponiveis.append(ativo)
        
        # Se não houver ativos disponíveis, retornar False
        if not ativos_disponiveis:
            BOT2_LOGGER.warning(f"Não há ativos disponíveis no momento ({hora_str}).")
            return False
        
        # Caso contrário, retornar a lista de ativos disponíveis
        BOT2_LOGGER.info(f"Ativos disponíveis ({len(ativos_disponiveis)}): {', '.join(ativos_disponiveis)}")
        return ativos_disponiveis
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao verificar disponibilidade de ativos: {str(e)}")
        return False


def bot2_gerar_sinal_aleatorio():
    """Gera um sinal de trading aleatório com base nas categorias disponíveis."""
    global assets

    try:
        # Obter a hora atual em Brasília
        agora = bot2_obter_hora_brasilia()

        # Selecionar apenas uma categoria para todos os sinais (Digital)
        categoria = "Digital"

        # Verificar se há ativos disponíveis na categoria selecionada
        ativos_na_categoria = ATIVOS_CATEGORIAS[categoria]

        if not ativos_na_categoria:
            BOT2_LOGGER.warning(
                f"Nenhum ativo disponível na categoria {categoria}")
            return None

        # Escolher aleatoriamente um ativo da categoria
        ativo = random.choice(ativos_na_categoria)

        # Escolher aleatoriamente a direção (CALL ou PUT)
        direcao = random.choice(["CALL", "PUT"])

        # Definir o tempo de expiração fixo em 5 minutos para todos os sinais
        tempo_expiracao_minutos = 5
        expiracao_time = bot2_obter_hora_brasilia() + timedelta(
            minutes=tempo_expiracao_minutos
        )
        expiracao_texto = f"🕒 Expiração: {tempo_expiracao_minutos} minutos ({expiracao_time.strftime('%H:%M')})"

        # Registrar nos logs que um sinal foi gerado
        BOT2_LOGGER.info(
            f"Sinal gerado: Ativo={ativo}, Direção={direcao}, Expiração={tempo_expiracao_minutos}min, Categoria={categoria}"
        )

        # Retornar o sinal como um dicionário
        return {
            "ativo": ativo,
            "direcao": direcao,
            "tempo_expiracao_minutos": tempo_expiracao_minutos,
            "expiracao_texto": expiracao_texto,
            "categoria": categoria,
        }

    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao gerar sinal aleatório: {str(e)}")
        import traceback

        BOT2_LOGGER.error(traceback.format_exc())
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
    Formata a mensagem do sinal para o idioma especificado.
    Retorna a mensagem formatada no idioma correto (pt, en ou es).
    """
    ativo = sinal["ativo"]
    direcao = sinal["direcao"]
    categoria = sinal["categoria"]
    tempo_expiracao_minutos = sinal["tempo_expiracao_minutos"]

    # Debug: registrar os dados sendo usados para formatar a mensagem
    BOT2_LOGGER.info(
        f"Formatando mensagem com: ativo={ativo}, direção={direcao}, categoria={categoria}, tempo={tempo_expiracao_minutos}, idioma={idioma}"
    )

    # Formatação do nome do ativo para exibição
    nome_ativo_exibicao = (
        ativo.replace("Digital_", "") if ativo.startswith(
            "Digital_") else ativo
    )
    if "(OTC)" in nome_ativo_exibicao and not " (OTC)" in nome_ativo_exibicao:
        nome_ativo_exibicao = nome_ativo_exibicao.replace("(OTC)", " (OTC)")

    # Configura ações e emojis conforme a direção
    action_pt = "PUT" if direcao == "sell" else "CALL"
    action_en = "PUT" if direcao == "sell" else "CALL"
    action_es = "PUT" if direcao == "sell" else "CALL"
    emoji = "🟥" if direcao == "sell" else "🟩"

    # Encontrar o fuso horário adequado para o idioma
    fuso_horario = "America/Sao_Paulo"  # Padrão (Brasil)
    
    # Buscar o fuso horário na configuração dos canais
    for chat_id, config in BOT2_CANAIS_CONFIG.items():
        if config["idioma"] == idioma:
            fuso_horario = config.get("fuso_horario", "America/Sao_Paulo")
            break
    
    # Hora de entrada convertida para datetime no fuso horário de Brasília
    hora_entrada = datetime.strptime(hora_formatada, "%H:%M")
    hora_entrada_br = bot2_obter_hora_brasilia().replace(
        hour=hora_entrada.hour, minute=hora_entrada.minute, second=0, microsecond=0
    )
    
    # Converter para o fuso horário do canal
    hora_entrada_local = bot2_converter_fuso_horario(
        hora_entrada_br, fuso_horario)
    
    # Calcular horário de expiração no fuso horário de Brasília
    hora_expiracao_br = hora_entrada_br + \
        timedelta(minutes=tempo_expiracao_minutos)
    
    # Converter expiração para o fuso horário do canal
    hora_expiracao_local = bot2_converter_fuso_horario(
        hora_expiracao_br, fuso_horario)
    
    # Calcular horários de gale (reentrada) no fuso horário de Brasília
    # 1° GALE é o horário de expiração + 5 minutos
    hora_gale1_br = hora_expiracao_br + timedelta(minutes=5)
    # 2° GALE é o 1° GALE + 5 minutos
    hora_gale2_br = hora_gale1_br + timedelta(minutes=5)
    # 3° GALE é o 2° GALE + 5 minutos
    hora_gale3_br = hora_gale2_br + timedelta(minutes=5)
    
    # Converter gales para o fuso horário do canal
    hora_gale1_local = bot2_converter_fuso_horario(hora_gale1_br, fuso_horario)
    hora_gale2_local = bot2_converter_fuso_horario(hora_gale2_br, fuso_horario)
    hora_gale3_local = bot2_converter_fuso_horario(hora_gale3_br, fuso_horario)
    
    # Formatar os horários para exibição (no fuso horário local)
    hora_entrada_formatada = hora_entrada_local.strftime("%H:%M")
    hora_expiracao_formatada = hora_expiracao_local.strftime("%H:%M")
    hora_gale1_formatada = hora_gale1_local.strftime("%H:%M")
    hora_gale2_formatada = hora_gale2_local.strftime("%H:%M")
    hora_gale3_formatada = hora_gale3_local.strftime("%H:%M")
    
    # Registrar a conversão de fuso horário
    BOT2_LOGGER.info(
        f"Horários convertidos para fuso {fuso_horario}: Entrada={hora_entrada_formatada}, "
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
        f"{nome_ativo_exibicao};{hora_entrada_formatada};{action_pt} {emoji} {categoria_exibicao}\n\n"
            f"🕐{texto_tempo} {hora_expiracao_formatada}\n\n"
            f"{texto_gale1} {hora_gale1_formatada}\n"
            f"{texto_gale2} {hora_gale2_formatada}\n"
            f"{texto_gale3} {hora_gale3_formatada}\n\n"
        f'📲 <a href="{link_corretora}">{texto_corretora}</a>\n'
        f'🙋‍♂️ Não sabe operar ainda? <a href="{link_video}">{texto_video}</a>'
    )
            
    # Mensagem em EN
    mensagem_en = (
        f"💰{tempo_expiracao_minutos} {texto_minutos_en} expiration\n"
        f"{nome_ativo_exibicao};{hora_entrada_formatada};{action_en} {emoji} {categoria_exibicao}\n\n"
            f"🕐{texto_tempo} {hora_expiracao_formatada}\n\n"
            f"{texto_gale1} {hora_gale1_formatada}\n"
            f"{texto_gale2} {hora_gale2_formatada}\n"
            f"{texto_gale3} {hora_gale3_formatada}\n\n"
        f'📲 <a href="{link_corretora}">{texto_corretora}</a>\n'
        f'🙋‍♂️ Don\'t know how to trade yet? <a href="{link_video}">{texto_video}</a>'
    )
            
    # Mensagem em ES
    mensagem_es = (
        f"💰{tempo_expiracao_minutos} {texto_minutos_es} de expiración\n"
        f"{nome_ativo_exibicao};{hora_entrada_formatada};{action_es} {emoji} {categoria_exibicao}\n\n"
            f"🕐{texto_tempo} {hora_expiracao_formatada}\n\n"
            f"{texto_gale1} {hora_gale1_formatada}\n"
            f"{texto_gale2} {hora_gale2_formatada}\n"
            f"{texto_gale3} {hora_gale3_formatada}\n\n"
        f'📲 <a href="{link_corretora}">{texto_corretora}</a>\n'
        f'🙋‍♂️ ¿No sabe operar todavía? <a href="{link_video}">{texto_video}</a>'
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
    Verifica se a URL do GIF está acessível.
    
    Args:
        url (str): A URL do GIF a ser verificada
        
    Returns:
        tuple: (url_a_usar, is_valid) onde url_a_usar é a URL verificada ou alternativa,
               e is_valid é um booleano indicando se a URL está acessível
    """
    try:
        BOT2_LOGGER.info(f"Verificando URL de GIF: {url}")
        response = requests.head(url, timeout=5)
        
        if response.status_code == 200:
            BOT2_LOGGER.info(f"URL de GIF válida: {url}")
            return url, True
        else:
            BOT2_LOGGER.warning(f"URL de GIF inválida (código {response.status_code}): {url}")
            return url, False
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao verificar URL {url}: {str(e)}")
        return url, False


def bot2_enviar_gif_pos_sinal(signal=None):
    """Envia um GIF após o resultado do sinal ou uma mensagem de gerenciamento uma vez por dia."""
    global BOT2_LOGGER, BOT2_CANAIS_CONFIG, BOT2_TOKEN, CONFIG_JSON, ultimo_sinal_enviado, bot2, URLS_GIFS_DIRETAS
    
    try:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        data_atual = agora.strftime("%Y-%m-%d")
        
        # Criar uma variável estática para controlar se a mensagem já foi enviada hoje
        if not hasattr(bot2_enviar_gif_pos_sinal, "mensagem_perda_enviada_hoje"):
            bot2_enviar_gif_pos_sinal.mensagem_perda_enviada_hoje = ""
        
        # Decidir se vamos enviar uma mensagem de perda ou o gif normal
        enviar_mensagem_perda = bot2_enviar_gif_pos_sinal.mensagem_perda_enviada_hoje != data_atual
        
        if enviar_mensagem_perda:
            BOT2_LOGGER.info(f"[{horario_atual}] Enviando mensagem de gerenciamento de banca em vez de GIF pós-sinal")
            # Marcar que a mensagem de perda foi enviada hoje
            bot2_enviar_gif_pos_sinal.mensagem_perda_enviada_hoje = data_atual
        else:
            BOT2_LOGGER.info(f"[{horario_atual}] INICIANDO ENVIO DA IMAGEM PÓS-SINAL...")
            BOT2_LOGGER.info(f"[{horario_atual}] 🎬 LOG GIF: Preparando para enviar GIFs pós-sinal")
        
        # Verificar se o sinal existe
        if not signal:
            signal = ultimo_sinal_enviado
        
        if not signal:
            BOT2_LOGGER.error(f"[{horario_atual}] Não foi possível encontrar o sinal para enviar a mensagem/GIF.")
            return False
        
        # Verifica se o ativo está dentro do horário de operação
        ativo = signal.get('ativo', None)
        categoria = signal.get('categoria', 'Digital')
        
        if ativo and not bot2_verificar_horario_ativo(ativo, categoria):
            BOT2_LOGGER.warning(
                f"Ativo {ativo} não está dentro do horário de operação. Não enviando mensagem/GIF pós-sinal.")
            return False
        
        # Contar quantas mensagens/GIFs foram enviados
        envios_com_sucesso = 0
        
        # Para cada idioma configurado, envia a mensagem formatada
        for idioma, chats in BOT2_CANAIS_CONFIG.items():
            if not chats:  # Se não houver chats configurados para este idioma, pula
                continue
            
            for chat_id in chats:
                try:
                    if enviar_mensagem_perda:
                        # Preparar a mensagem de perda conforme o idioma
                        link_corretora = CONFIG_JSON.get("link_corretora", "")
                        
                        if idioma == "pt":
                            texto_perda = f"⚠️ GERENCIAMENTO DE BANCA ⚠️\n\nSinal anterior não alcançou o resultado esperado!\nLembre-se de seguir seu gerenciamento para recuperar na próxima entrada.\n\n<a href=\"{link_corretora}\"><font color=\"blue\">Continue operando</font></a> 📈"
                        elif idioma == "en":
                            texto_perda = f"⚠️ BANKROLL MANAGEMENT ⚠️\n\nPrevious signal did not reach the expected outcome!\nRemember to follow your management to recover in the next entry.\n\n<a href=\"{link_corretora}\"><font color=\"blue\">Keep trading</font></a> 📈"
                        else:  # es
                            texto_perda = f"⚠️ GESTIÓN DE BANCA ⚠️\n\nLa señal anterior no alcanzó el resultado esperado!\nRecuerde seguir su gestión para recuperarse en la próxima entrada.\n\n<a href=\"{link_corretora}\"><font color=\"blue\">Sigue operando</font></a> 📈"
                        
                        # URL base para a API do Telegram
                        url_base = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
                        
                        resposta = requests.post(
                            url_base,
                            json={
                                "chat_id": chat_id,
                                "text": texto_perda,
                                "parse_mode": "HTML",
                                "disable_web_page_preview": False,
                            },
                            timeout=10,
                        )
                        
                        if resposta.status_code == 200:
                            BOT2_LOGGER.info(
                                f"[{horario_atual}] Mensagem de gerenciamento enviada com sucesso para {chat_id} (idioma: {idioma})"
                            )
                            envios_com_sucesso += 1
                        else:
                            BOT2_LOGGER.error(
                                f"[{horario_atual}] Erro ao enviar mensagem de gerenciamento para {chat_id}: {resposta.text}"
                            )
                    else:
                        # Enviar GIF normal pós-sinal
                        # Definir a URL do GIF para envio
                        usar_gif_especial = hasattr(bot2_enviar_gif_pos_sinal, "contador_pos_sinal") and bot2_enviar_gif_pos_sinal.contador_pos_sinal % 3 == 0
                        
                        if not hasattr(bot2_enviar_gif_pos_sinal, "contador_pos_sinal"):
                            bot2_enviar_gif_pos_sinal.contador_pos_sinal = 0
                        bot2_enviar_gif_pos_sinal.contador_pos_sinal += 1
                        
                        if usar_gif_especial and idioma == "pt":
                            # Apenas para português, usar o GIF especial
                            gif_url = URLS_GIFS_DIRETAS["gif_especial_pt"]
                            BOT2_LOGGER.info(f"[{horario_atual}] Usando GIF especial para canal PT")
                        else:
                            # Para os demais casos, usar o GIF padrão
                            gif_url = URLS_GIFS_DIRETAS["pos_sinal_padrao"]
                            BOT2_LOGGER.info(f"[{horario_atual}] Usando GIF padrão para canal {idioma}")
                        
                        BOT2_LOGGER.info(f"[{horario_atual}] 🎬 LOG GIF: Preparando envio do GIF: {gif_url} para canal {chat_id}")
                        
                        try:
                            # Baixar o arquivo para enviar como arquivo em vez de URL
                            BOT2_LOGGER.info(f"[{horario_atual}] 🎬 LOG GIF: Baixando arquivo de {gif_url}")
                            arquivo_resposta = requests.get(gif_url, stream=True, timeout=10)
                            
                            if arquivo_resposta.status_code == 200:
                                # Criar um arquivo temporário no formato correto
                                extensao = ".gif"
                                if ".webp" in gif_url.lower():
                                    extensao = ".webp"
                                
                                nome_arquivo_temp = f"temp_gif_{random.randint(1000, 9999)}{extensao}"
                                
                                # Salvar o arquivo temporariamente
                                with open(nome_arquivo_temp, 'wb') as f:
                                    f.write(arquivo_resposta.content)
                                
                                BOT2_LOGGER.info(f"[{horario_atual}] 🎬 LOG GIF: Arquivo baixado com sucesso como {nome_arquivo_temp}")
                                
                                # Abrir o arquivo e enviar como animação
                                with open(nome_arquivo_temp, 'rb') as f_gif:
                                    # Enviar o GIF como animação diretamente do arquivo nas dimensões especificadas
                                    BOT2_LOGGER.info(f"[{horario_atual}] 🎬 LOG GIF: Enviando arquivo como animação")
                                    bot2.send_animation(
                                        chat_id=chat_id,
                                        animation=f_gif,
                                        caption="",
                                        parse_mode="HTML",
                                        width=208,
                                        height=84  # Arredondando para 84 pixels já que não é possível usar valores decimais
                                    )
                                
                                # Remover o arquivo temporário
                                try:
                                    os.remove(nome_arquivo_temp)
                                    BOT2_LOGGER.info(f"[{horario_atual}] 🎬 LOG GIF: Arquivo temporário {nome_arquivo_temp} removido")
                                except:
                                    BOT2_LOGGER.warning(f"[{horario_atual}] 🎬 LOG GIF: Não foi possível remover o arquivo temporário {nome_arquivo_temp}")
                                
                                BOT2_LOGGER.info(f"GIF enviado com sucesso como animação para o canal {chat_id}")
                                envios_com_sucesso += 1
                            else:
                                BOT2_LOGGER.error(f"[{horario_atual}] 🎬 LOG GIF: Erro ao baixar o arquivo. Status code: {arquivo_resposta.status_code}")
                                # Tentar enviar diretamente com a URL como fallback
                                bot2.send_animation(
                                    chat_id=chat_id,
                                    animation=gif_url,
                                    caption="",
                                    parse_mode="HTML",
                                    width=208,
                                    height=84
                                )
                                BOT2_LOGGER.info(f"GIF enviado com sucesso como URL para o canal {chat_id} (fallback)")
                                envios_com_sucesso += 1
                        except Exception as download_error:
                            BOT2_LOGGER.error(f"[{horario_atual}] 🎬 LOG GIF: Erro ao baixar/enviar o arquivo: {str(download_error)}")
                            # Tentar enviar diretamente com a URL como fallback
                            bot2.send_animation(
                                chat_id=chat_id,
                                animation=gif_url,
                                caption="",
                                parse_mode="HTML",
                                width=208,
                                height=84
                            )
                            BOT2_LOGGER.info(f"GIF enviado com sucesso como URL para o canal {chat_id} (fallback após erro)")
                            envios_com_sucesso += 1
                
                except Exception as e:
                    BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar para o canal {chat_id}: {str(e)}")
                    
                    if "rights to send" in str(e).lower():
                        BOT2_LOGGER.error(f"Bot não tem permissões de administrador no canal {chat_id}")
        
        if envios_com_sucesso > 0:
            if enviar_mensagem_perda:
                BOT2_LOGGER.info(f"[{horario_atual}] Total de {envios_com_sucesso} mensagens de gerenciamento enviadas com sucesso")
            else:
                BOT2_LOGGER.info(f"[{horario_atual}] Total de {envios_com_sucesso} GIFs pós-sinal enviados com sucesso")
            return True
        else:
            BOT2_LOGGER.warning(f"[{horario_atual}] Nenhuma mensagem ou GIF foi enviado")
            return False
    
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar mensagem/GIF pós-sinal: {str(e)}")
        traceback.print_exc()
        return False


def bot2_enviar_mensagem_cadastro():
    """
    Envia a mensagem especial de cadastro para todos os canais após o GIF especial nos sinais múltiplos de 3.
    """
    global BOT2_LOGGER, BOT2_CANAIS_CONFIG, BOT2_TOKEN
    
    try:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] Enviando mensagem de cadastro para todos os canais")
        
        mensagens_enviadas = 0
        
        # Para cada idioma configurado, envia a mensagem formatada
        for idioma, chats in BOT2_CANAIS_CONFIG.items():
            if not chats:  # Se não houver chats configurados para este idioma, pula
                continue
            
            # Preparar a mensagem conforme o idioma
            if idioma == "pt":
                link_corretora = "https://trade.xxbroker.com/register?aff=741613&aff_model=revenue&afftrack="
                link_video = "https://t.me/trendingbrazil/215"
                texto_cadastro = f"⚠️⚠️PARA PARTICIPAR DESTA SESSÃO, SIGA O PASSO A PASSO ABAIXO⚠️⚠️\n\n\n1º ✅ —>  Crie sua conta na corretora no link abaixo e GANHE $10.000 DE GRAÇA pra começar a operar com a gente sem ter que arriscar seu dinheiro.\n\nVocê vai poder testar todos nossas\noperações com risco ZERO!\n\n👇🏻👇🏻👇🏻👇🏻\n\n<a href=\"{link_corretora}\"><font color=\"blue\">CRIE SUA CONTA AQUI E GANHE R$10.000</font></a>\n\n—————————————————————\n\n2º ✅ —>  Assista o vídeo abaixo e aprenda como depositar e como entrar com a gente nas nossas operações!\n\n👇🏻👇🏻👇🏻👇🏻\n\n<a href=\"{link_video}\"><font color=\"blue\">CLIQUE AQUI E ASSISTA O VÍDEO</font></a>"
            elif idioma == "en":
                link_corretora = "https://trade.xxbroker.com/register?aff=741727&aff_model=revenue&afftrack="
                link_video = "https://t.me/trendingenglish/226"
                texto_cadastro = f"⚠️⚠️TO PARTICIPATE IN THIS SESSION, FOLLOW THE STEP BY STEP BELOW⚠️⚠️\n\n\n1º ✅ —>  Create your account on the broker through the link below and GET $10,000 FOR FREE to start trading with us without having to risk your money.\n\nYou will be able to test all our\noperations with ZERO risk!\n\n👇🏻👇🏻👇🏻👇🏻\n\n<a href=\"{link_corretora}\"><font color=\"blue\">CREATE YOUR ACCOUNT HERE AND GET $10,000</font></a>\n\n—————————————————————\n\n2º ✅ —>  Watch the video below and learn how to deposit and how to enter with us in our operations!\n\n👇🏻👇🏻👇🏻👇🏻\n\n<a href=\"{link_video}\"><font color=\"blue\">CLICK HERE AND WATCH THE VIDEO</font></a>"
            else:  # es
                link_corretora = "https://trade.xxbroker.com/register?aff=741726&aff_model=revenue&afftrack="
                link_video = "https://t.me/trendingespanish/212"
                texto_cadastro = f"⚠️⚠️PARA PARTICIPAR EN ESTA SESIÓN, SIGA EL PASO A PASO A CONTINUACIÓN⚠️⚠️\n\n\n1º ✅ —>  Cree su cuenta en el broker a través del enlace de abajo y OBTENGA $10.000 GRATIS para comenzar a operar con nosotros sin tener que arriesgar su dinero.\n\nPodrá probar todas nuestras\noperaciones con riesgo CERO!\n\n👇🏻👇🏻👇🏻👇🏻\n\n<a href=\"{link_corretora}\"><font color=\"blue\">CREE SU CUENTA AQUÍ Y OBTENGA $10.000</font></a>\n\n—————————————————————\n\n2º ✅ —>  ¡Mire el video a continuación y aprenda cómo depositar y cómo entrar con nosotros en nuestras operaciones!\n\n👇🏻👇🏻👇🏻👇🏻\n\n<a href=\"{link_video}\"><font color=\"blue\">HAGA CLIC AQUÍ Y VEA EL VIDEO</font></a>"
            
            for chat_id in chats:
                try:
                    # URL base para a API do Telegram
                    url_base = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
                    
                    resposta = requests.post(
                        url_base,
                        json={
                            "chat_id": chat_id,
                            "text": texto_cadastro,
                            "parse_mode": "HTML",
                            "disable_web_page_preview": False,
                        },
                        timeout=10,
                    )
                    
                    if resposta.status_code == 200:
                        BOT2_LOGGER.info(
                            f"[{horario_atual}] Mensagem de cadastro enviada com sucesso para {chat_id} (idioma: {idioma})"
                        )
                        mensagens_enviadas += 1
                    else:
                        BOT2_LOGGER.error(
                            f"[{horario_atual}] Erro ao enviar mensagem de cadastro para {chat_id}: {resposta.text}"
                        )
                except Exception as e:
                    BOT2_LOGGER.error(
                        f"[{horario_atual}] Exceção ao enviar mensagem de cadastro para {chat_id}: {str(e)}"
                    )
        
        if mensagens_enviadas > 0:
            BOT2_LOGGER.info(f"[{horario_atual}] Total de {mensagens_enviadas} mensagens de cadastro enviadas com sucesso")
            
            # Agendar envio da mensagem de abertura da corretora em 9 minutos
            schedule.every(9).minutes.do(bot2_enviar_mensagem_abertura_corretora).tag("abertura_corretora")
            BOT2_LOGGER.info(f"[{horario_atual}] Agendado envio da mensagem de abertura da corretora em 9 minutos")
            
            return True
        else:
            BOT2_LOGGER.warning(f"[{horario_atual}] Nenhuma mensagem de cadastro foi enviada")
            return False
    
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar mensagem de cadastro: {str(e)}")
        traceback.print_exc()
        return False


def bot2_enviar_mensagem_abertura_corretora():
    """
    Envia a mensagem de abertura da corretora após o GIF promo.
    """
    global BOT2_LOGGER, BOT2_CANAIS_CONFIG, BOT2_TOKEN
    
    try:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] Enviando mensagem de abertura da corretora para todos os canais")
        
        mensagens_enviadas = 0
        
        # Para cada idioma configurado, envia a mensagem formatada
        for idioma, chats in BOT2_CANAIS_CONFIG.items():
            if not chats:  # Se não houver chats configurados para este idioma, pula
                continue
            
            # Preparar a mensagem conforme o idioma
            if idioma == "pt":
                link_corretora = "https://trade.xxbroker.com/register?aff=741613&aff_model=revenue&afftrack="
                texto_abertura = f"👉🏼Abram a corretora Pessoal\n\n⚠️FIQUEM ATENTOS⚠️\n\n🔥Cadastre-se na XXBROKER agora mesmo🔥\n\n➡️ <a href=\"{link_corretora}\"><font color=\"blue\">CLICANDO AQUI</font></a>"
            elif idioma == "en":
                link_corretora = "https://trade.xxbroker.com/register?aff=741727&aff_model=revenue&afftrack="
                texto_abertura = f"👉🏼Open the broker now\n\n⚠️STAY ALERT⚠️\n\n🔥Register on XXBROKER right now🔥\n\n➡️ <a href=\"{link_corretora}\"><font color=\"blue\">CLICK HERE</font></a>"
            else:  # es
                link_corretora = "https://trade.xxbroker.com/register?aff=741726&aff_model=revenue&afftrack="
                texto_abertura = f"👉🏼Abran el broker ahora\n\n⚠️ESTÉN ATENTOS⚠️\n\n🔥Regístrese en XXBROKER ahora mismo🔥\n\n➡️ <a href=\"{link_corretora}\"><font color=\"blue\">CLIC AQUÍ</font></a>"
            
            for chat_id in chats:
                try:
                    # URL base para a API do Telegram
                    url_base = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
                    
                    resposta = requests.post(
                        url_base,
                        json={
                            "chat_id": chat_id,
                            "text": texto_abertura,
                            "parse_mode": "HTML",
                            "disable_web_page_preview": False,
                        },
                        timeout=10,
                    )
                    
                    if resposta.status_code == 200:
                        BOT2_LOGGER.info(
                            f"[{horario_atual}] Mensagem de abertura da corretora enviada com sucesso para {chat_id} (idioma: {idioma})"
                        )
                        mensagens_enviadas += 1
                    else:
                        BOT2_LOGGER.error(
                            f"[{horario_atual}] Erro ao enviar mensagem de abertura para {chat_id}: {resposta.text}"
                        )
                except Exception as e:
                    BOT2_LOGGER.error(
                        f"[{horario_atual}] Exceção ao enviar mensagem de abertura para {chat_id}: {str(e)}"
                    )
        
        if mensagens_enviadas > 0:
            BOT2_LOGGER.info(f"[{horario_atual}] Total de {mensagens_enviadas} mensagens de abertura enviadas com sucesso")
            return True
        else:
            BOT2_LOGGER.warning(f"[{horario_atual}] Nenhuma mensagem de abertura foi enviada")
            return False
    
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar mensagem de abertura: {str(e)}")
        traceback.print_exc()
        return False


def bot2_enviar_gif_promo(idioma="pt"):
    """
    Envia um GIF promocional antes do sinal.

    Args:
        idioma (str): O idioma do GIF a ser enviado (pt, en, es)
    """
    global BOT2_LOGGER, BOT2_CANAIS_CONFIG, BOT2_TOKEN, URLS_GIFS_DIRETAS, bot2
    
    try:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] Iniciando função bot2_enviar_gif_promo para idioma {idioma}")

        gif_enviado_com_sucesso = False
        
        # Limpar quaisquer agendamentos anteriores para envio de mensagem de abertura
        schedule.clear("abertura_corretora")

        for chat_id, config in BOT2_CANAIS_CONFIG.items():
            canal_idioma = config.get("idioma", "pt")

            # Ignorar canais com idioma diferente do especificado
            if canal_idioma != idioma:
                continue

            try:
                # Definir a URL do GIF do Giphy com base no idioma
                gif_key = f"promo_{idioma}"
                if gif_key in URLS_GIFS_DIRETAS:
                    gif_url = URLS_GIFS_DIRETAS[gif_key]
                else:
                    # Usar o gif promocional em inglês como padrão
                    gif_url = URLS_GIFS_DIRETAS["promo_en"]

                BOT2_LOGGER.info(
                    f"[{horario_atual}] Tentando enviar GIF promo como animação do URL: {gif_url} para o canal {chat_id}"
                )
                
                try:
                    # Baixar o arquivo para enviar como arquivo em vez de URL
                    BOT2_LOGGER.info(f"[{horario_atual}] Baixando arquivo de {gif_url}")
                    arquivo_resposta = requests.get(gif_url, stream=True, timeout=10)
                    
                    if arquivo_resposta.status_code == 200:
                        # Criar um arquivo temporário no formato correto
                        extensao = ".gif"
                        if ".webp" in gif_url.lower():
                            extensao = ".webp"
                        
                        nome_arquivo_temp = f"temp_gif_{random.randint(1000, 9999)}{extensao}"
                        
                        # Salvar o arquivo temporariamente
                        with open(nome_arquivo_temp, 'wb') as f:
                            f.write(arquivo_resposta.content)
                        
                        BOT2_LOGGER.info(f"[{horario_atual}] Arquivo baixado com sucesso como {nome_arquivo_temp}")
                        
                        # Abrir o arquivo e enviar como animação
                        with open(nome_arquivo_temp, 'rb') as f_gif:
                            # Enviar o GIF como animação diretamente do arquivo nas dimensões especificadas
                            BOT2_LOGGER.info(f"[{horario_atual}] Enviando arquivo como animação")
                            bot2.send_animation(
                                chat_id=chat_id,
                                animation=f_gif,
                                caption="",
                                parse_mode="HTML",
                                width=208,
                                height=84  # Arredondando para 84 pixels já que não é possível usar valores decimais
                            )
                        
                        # Remover o arquivo temporário
                        try:
                            os.remove(nome_arquivo_temp)
                            BOT2_LOGGER.info(f"[{horario_atual}] Arquivo temporário {nome_arquivo_temp} removido")
                        except:
                            BOT2_LOGGER.warning(f"[{horario_atual}] Não foi possível remover o arquivo temporário {nome_arquivo_temp}")
                        
                        BOT2_LOGGER.info(f"[{horario_atual}] GIF promocional enviado com sucesso como animação para o canal {chat_id}")
                        gif_enviado_com_sucesso = True
                    else:
                        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao baixar o arquivo. Status code: {arquivo_resposta.status_code}")
                        # Tentar enviar diretamente com a URL como fallback
                        bot2.send_animation(
                            chat_id=chat_id,
                            animation=gif_url,
                            caption="",
                            parse_mode="HTML",
                            width=208,
                            height=84
                        )
                        BOT2_LOGGER.info(f"[{horario_atual}] GIF enviado com sucesso como URL para o canal {chat_id} (fallback)")
                        gif_enviado_com_sucesso = True
                except Exception as download_error:
                    BOT2_LOGGER.error(f"[{horario_atual}] Erro ao baixar/enviar o arquivo: {str(download_error)}")
                    # Tentar enviar diretamente com a URL como fallback
                    bot2.send_animation(
                        chat_id=chat_id,
                        animation=gif_url,
                        caption="",
                        parse_mode="HTML",
                        width=208,
                        height=84
                    )
                    BOT2_LOGGER.info(f"[{horario_atual}] GIF enviado com sucesso como URL para o canal {chat_id} (fallback após erro)")
                    gif_enviado_com_sucesso = True

            except Exception as e:
                BOT2_LOGGER.error(
                    f"[{horario_atual}] Erro ao enviar GIF promocional para o canal {chat_id}: {str(e)}"
                )

                if "rights to send" in str(e).lower():
                    BOT2_LOGGER.error(
                        f"[{horario_atual}] Bot não tem permissões de administrador no canal {chat_id}"
                    )

        if gif_enviado_com_sucesso:
            BOT2_LOGGER.info(f"[{horario_atual}] GIF promocional enviado com sucesso para idioma {idioma}")
            
            # Agendar o envio da mensagem de abertura da corretora para 1 minuto depois
            schedule.every(1).minutes.do(bot2_enviar_mensagem_abertura_corretora).tag("abertura_corretora")
            BOT2_LOGGER.info(f"[{horario_atual}] Agendado envio da mensagem de abertura da corretora em 1 minuto")
            
            return True
        else:
            BOT2_LOGGER.warning(
                f"[{horario_atual}] Não foi possível enviar o GIF promocional para idioma {idioma}"
            )
            return False
    
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar GIF promocional: {str(e)}")
        traceback.print_exc()
        return False


def bot2_enviar_gif_especial():
    """
    Envia um GIF especial para todos os canais após sinais múltiplos de 3.
    """
    global BOT2_LOGGER, BOT2_CANAIS_CONFIG, BOT2_TOKEN, URLS_GIFS_DIRETAS, bot2
    
    try:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] Iniciando envio de GIF especial para múltiplos de 3")

        gif_enviado_com_sucesso = False
        
        # Limpar quaisquer agendamentos anteriores para envio de mensagem de cadastro
        schedule.clear("cadastro_especial")

        for chat_id, config in BOT2_CANAIS_CONFIG.items():
            idioma = config.get("idioma", "pt")

            try:
                # Usar o GIF especial 
                if idioma == "pt":
                    gif_url = URLS_GIFS_DIRETAS["gif_especial_pt"]
                else:
                    # Para os outros idiomas usar o mesmo gif
                    gif_url = URLS_GIFS_DIRETAS["gif_especial_pt"]

                BOT2_LOGGER.info(
                    f"[{horario_atual}] Tentando enviar GIF especial como animação do URL: {gif_url} para o canal {chat_id}"
                )
                
                try:
                    # Baixar o arquivo para enviar como arquivo em vez de URL
                    BOT2_LOGGER.info(f"[{horario_atual}] Baixando arquivo de {gif_url}")
                    arquivo_resposta = requests.get(gif_url, stream=True, timeout=10)
                    
                    if arquivo_resposta.status_code == 200:
                        # Criar um arquivo temporário no formato correto
                        extensao = ".gif"
                        if ".webp" in gif_url.lower():
                            extensao = ".webp"
                        
                        nome_arquivo_temp = f"temp_gif_{random.randint(1000, 9999)}{extensao}"
                        
                        # Salvar o arquivo temporariamente
                        with open(nome_arquivo_temp, 'wb') as f:
                            f.write(arquivo_resposta.content)
                        
                        BOT2_LOGGER.info(f"[{horario_atual}] Arquivo baixado com sucesso como {nome_arquivo_temp}")
                        
                        # Abrir o arquivo e enviar como animação
                        with open(nome_arquivo_temp, 'rb') as f_gif:
                            # Enviar o GIF como animação diretamente do arquivo nas dimensões especificadas
                            BOT2_LOGGER.info(f"[{horario_atual}] Enviando arquivo como animação")
                            bot2.send_animation(
                                chat_id=chat_id,
                                animation=f_gif,
                                caption="",
                                parse_mode="HTML",
                                width=208,
                                height=84  # Arredondando para 84 pixels já que não é possível usar valores decimais
                            )
                        
                        # Remover o arquivo temporário
                        try:
                            os.remove(nome_arquivo_temp)
                            BOT2_LOGGER.info(f"[{horario_atual}] Arquivo temporário {nome_arquivo_temp} removido")
                        except:
                            BOT2_LOGGER.warning(f"[{horario_atual}] Não foi possível remover o arquivo temporário {nome_arquivo_temp}")
                        
                        BOT2_LOGGER.info(f"[{horario_atual}] GIF especial enviado com sucesso como animação para o canal {chat_id}")
                        gif_enviado_com_sucesso = True
                    else:
                        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao baixar o arquivo. Status code: {arquivo_resposta.status_code}")
                        # Tentar enviar diretamente com a URL como fallback
                        bot2.send_animation(
                            chat_id=chat_id,
                            animation=gif_url,
                            caption="",
                            parse_mode="HTML",
                            width=208,
                            height=84
                        )
                        BOT2_LOGGER.info(f"[{horario_atual}] GIF enviado com sucesso como URL para o canal {chat_id} (fallback)")
                        gif_enviado_com_sucesso = True
                except Exception as download_error:
                    BOT2_LOGGER.error(f"[{horario_atual}] Erro ao baixar/enviar o arquivo: {str(download_error)}")
                    # Tentar enviar diretamente com a URL como fallback
                    bot2.send_animation(
                        chat_id=chat_id,
                        animation=gif_url,
                        caption="",
                        parse_mode="HTML",
                        width=208,
                        height=84
                    )
                    BOT2_LOGGER.info(f"[{horario_atual}] GIF enviado com sucesso como URL para o canal {chat_id} (fallback após erro)")
                    gif_enviado_com_sucesso = True

            except Exception as e:
                BOT2_LOGGER.error(
                    f"[{horario_atual}] Erro ao enviar GIF especial para o canal {chat_id}: {str(e)}"
                )

                if "rights to send" in str(e).lower():
                    BOT2_LOGGER.error(
                        f"[{horario_atual}] Bot não tem permissões de administrador no canal {chat_id}"
                    )

        if gif_enviado_com_sucesso:
            BOT2_LOGGER.info(f"[{horario_atual}] GIF especial enviado com sucesso para sinais múltiplos de 3")
            
            # Agendar o envio da mensagem de cadastro para 1 minuto depois
            schedule.every(1).minutes.do(bot2_enviar_mensagem_cadastro).tag("cadastro_especial")
            BOT2_LOGGER.info(f"[{horario_atual}] Agendado envio da mensagem de cadastro em 1 minuto após GIF especial")
            
            return True
        else:
            BOT2_LOGGER.warning(
                f"[{horario_atual}] Não foi possível enviar o GIF especial para sinais múltiplos de 3"
            )
            return False
    
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar GIF especial: {str(e)}")
        traceback.print_exc()
        return False


def bot2_send_message(ignorar_anti_duplicacao=False, enviar_gif_imediatamente=False):
    """Envia uma mensagem com sinal para todos os canais configurados."""
    global bot2_contador_sinais, ultimo_sinal_enviado, BOT2_LOGGER, BOT2_CHAT_IDS, BOT2_CANAIS_CONFIG, BOT2_TOKEN
    
    try:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        data_atual = agora.strftime("%Y-%m-%d")
        BOT2_LOGGER.info(f"[{horario_atual}] INICIANDO ENVIO DO SINAL...")
        
        # Verificar se há ativos disponíveis antes de tentar enviar sinais
        ativos_disponiveis = bot2_verificar_disponibilidade()
        if not ativos_disponiveis:
            BOT2_LOGGER.warning("Não há ativos disponíveis no momento. Mensagem não enviada.")
            return False
            
        # Gerar o sinal aleatório
        sinal = bot2_gerar_sinal_aleatorio()
        if not sinal:
            BOT2_LOGGER.error(
                f"[{horario_atual}] Não foi possível gerar um sinal válido. Tentando novamente mais tarde."
            )
            return False
        
        # Armazenar o sinal na variável global para uso posterior
        ultimo_sinal_enviado = sinal
            
        # Em vez de desempacotar diretamente, obtenha os valores do dicionário
        ativo = sinal["ativo"]
        direcao = sinal["direcao"]
        tempo_expiracao_minutos = sinal["tempo_expiracao_minutos"]
        categoria = sinal["categoria"]

        # Registra o sinal
        bot2_registrar_envio(ativo, direcao, categoria)

        # Calcular o horário de entrada (2 minutos após o envio do sinal)
        hora_entrada = agora + timedelta(minutes=2)
        hora_formatada = hora_entrada.strftime("%H:%M")
        
        # Enviar para cada canal
        mensagens_enviadas = 0
        for chat_id in BOT2_CHAT_IDS:
            config_canal = BOT2_CANAIS_CONFIG[chat_id]
            idioma = config_canal["idioma"]
            
            mensagem_formatada = bot2_formatar_mensagem(
                sinal, hora_formatada, idioma)
            url_base = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"
            
            # Registrar envio nos logs
            BOT2_LOGGER.info(
                f"[{horario_atual}] Enviando sinal: Ativo={ativo}, Direção={direcao}, Categoria={categoria}, Tempo={tempo_expiracao_minutos}, Idioma={idioma}"
            )
            
            try:
                resposta = requests.post(
                    url_base,
                    json={
                    "chat_id": chat_id,
                    "text": mensagem_formatada,
                    "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=10,
                )
                
                if resposta.status_code == 200:
                    BOT2_LOGGER.info(
                        f"[{horario_atual}] SUCESSO: SINAL ENVIADO COM SUCESSO para o canal {chat_id}"
                    )
                    mensagens_enviadas += 1
                else:
                    BOT2_LOGGER.error(
                        f"[{horario_atual}] ERRO: Erro ao enviar mensagem para o canal {chat_id}: {resposta.text}"
                    )
            except Exception as msg_error:
                BOT2_LOGGER.error(
                    f"[{horario_atual}] ERRO: Exceção ao enviar mensagem para o canal {chat_id}: {str(msg_error)}"
                    )

        # Incrementa o contador global de sinais
        bot2_contador_sinais += 1
        is_multiplo_tres = bot2_contador_sinais % 3 == 0
        
        if mensagens_enviadas > 0:
            BOT2_LOGGER.info(
                f"[{horario_atual}] Sinal enviado com sucesso para {mensagens_enviadas} canais: {ativo} {direcao} {categoria}"
            )
            
            # Limpar quaisquer agendamentos anteriores para o GIF pós-sinal
            schedule.clear("gif_pos_sinal")
            schedule.clear("gif_especial")
            
            # Tempo de espera para o gif pós-sinal (7 minutos)
            tempo_pos_sinal = 7

            # Calcular a hora exata para o envio do GIF pós-sinal
            horario_pos_sinal = agora + timedelta(minutes=tempo_pos_sinal)
            hora_pos_sinal_str = horario_pos_sinal.strftime("%H:%M")

            BOT2_LOGGER.info(
                f"[{horario_atual}] LOG: Agendando GIF/mensagem pós-sinal para {hora_pos_sinal_str} (daqui a {tempo_pos_sinal} minutos)"
            )
            
            # Verificar se deve enviar imediatamente (para testes)
            if enviar_gif_imediatamente:
                BOT2_LOGGER.info(
                    f"[{horario_atual}] LOG: Opção de envio imediato ativada - enviando mensagens agora..."
                )
                bot2_enviar_gif_pos_sinal(sinal)
                
                # Se for múltiplo de 3, enviar o GIF especial após 30 minutos
                if is_multiplo_tres:
                    BOT2_LOGGER.info(f"[{horario_atual}] LOG: Enviando GIF especial imediatamente (sinais múltiplos de 3)")
                    bot2_enviar_gif_especial()
            else:
                # Agendar o envio do GIF pós-sinal (normal para todos os sinais)
                scheduler_job = (
                    schedule.every(tempo_pos_sinal)
                    .minutes
                    .do(bot2_enviar_gif_pos_sinal, sinal)
                    .tag("gif_pos_sinal")
                )

                if scheduler_job:
                    BOT2_LOGGER.info(
                        f"[{horario_atual}] LOG: Agendamento criado com sucesso: {scheduler_job}"
                    )
                    
                    # Se for múltiplo de 3, agendar o envio do GIF especial após 30 minutos
                    if is_multiplo_tres:
                        tempo_gif_especial = 30  # 30 minutos após o sinal
                        horario_gif_especial = agora + timedelta(minutes=tempo_gif_especial)
                        hora_gif_especial_str = horario_gif_especial.strftime("%H:%M")
                        
                        BOT2_LOGGER.info(
                            f"[{horario_atual}] LOG: Agendando GIF especial para {hora_gif_especial_str} (múltiplo de 3, contador: {bot2_contador_sinais})"
                        )
                        
                        schedule.every(tempo_gif_especial).minutes.do(bot2_enviar_gif_especial).tag("gif_especial")
                else:
                    BOT2_LOGGER.error(
                        f"[{horario_atual}] LOG: FALHA ao criar agendamento para o GIF pós-sinal!"
                    )

            return True
        else:
            BOT2_LOGGER.warning("Nenhuma mensagem foi enviada para os canais.")
            return False

    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar sinal: {str(e)}")
        traceback.print_exc()
        return False


def bot2_iniciar_ciclo_sinais():
    """
    Agenda o envio de sinais do Bot 2 a cada hora no minuto 13.
    """
    global bot2_sinais_agendados, BOT2_LOGGER
    
    try:
        # Limpar agendamentos anteriores de sinais
        schedule.clear("bot2_sinais")
        
        # Configurar para enviar sempre no minuto 13 de cada hora
        minuto_envio = 13
        
        # Agendar a cada hora no minuto 13
        schedule.every().hour.at(f":{minuto_envio:02d}").do(bot2_send_message).tag("bot2_sinais")
        
        BOT2_LOGGER.info(f"Sinal do Bot 2 agendado para o minuto {minuto_envio} de cada hora")
        BOT2_LOGGER.info("Configuração atual: 1 sinal por hora, no minuto 13")
        
        # Verificar próximo horário de envio
        agora = bot2_obter_hora_brasilia()
        hora_atual = agora.hour
        minuto_atual = agora.minute
        
        if minuto_atual >= minuto_envio:
            # Se já passou do minuto 13 dessa hora, o próximo será na próxima hora
            proximo_envio = f"{(hora_atual + 1) % 24:02d}:{minuto_envio:02d}"
        else:
            # Se ainda não chegou no minuto 13 dessa hora, será nessa hora mesmo
            proximo_envio = f"{hora_atual:02d}:{minuto_envio:02d}"
            
        BOT2_LOGGER.info(f"Próximo sinal agendado para: {proximo_envio}")
        
        bot2_sinais_agendados = True
        return True
        
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao iniciar ciclo de sinais do Bot 2: {str(e)}")
        traceback.print_exc()
        bot2_sinais_agendados = False
        return False


def iniciar_ambos_bots():
    """
    Inicializa o Bot 2 e mantém o programa em execução,
    tratando as tarefas agendadas periodicamente.
    """
    global bot2_sinais_agendados, BOT2_LOGGER
    
    try:
        # Iniciar o Bot 2
        if not bot2_sinais_agendados:
            bot2_iniciar_ciclo_sinais()  # Agendar sinais para o Bot 2
            
        BOT2_LOGGER.info("=== BOT 2 INICIADO COM SUCESSO! ===")
        BOT2_LOGGER.info("Aguardando envio de sinais nos horários programados...")
        
        # Teste inicial (descomentar para testes)
        # bot2_send_message(enviar_gif_imediatamente=True)
        
        # Loop principal para manter o programa em execução
        while True:
            # Registrar todas as tarefas pendentes a cada 5 minutos (diagnóstico)
            agora = bot2_obter_hora_brasilia()
            if agora.minute % 5 == 0 and agora.second == 0:
                jobs = schedule.get_jobs()
                BOT2_LOGGER.info(f"[{agora.strftime('%H:%M:%S')}] DIAGNÓSTICO: Verificando {len(jobs)} tarefas agendadas")
                for i, job in enumerate(jobs):
                    BOT2_LOGGER.info(f"[{agora.strftime('%H:%M:%S')}] DIAGNÓSTICO: Tarefa {i + 1}: {job} - Próxima execução: {job.next_run}")
            
            # Executar tarefas agendadas
            schedule.run_pending()
            
            # Pequena pausa para evitar uso excessivo de CPU
            time.sleep(1)
            
    except KeyboardInterrupt:
        BOT2_LOGGER.info("Bot encerrado pelo usuário (Ctrl+C)")
    except Exception as e:
        BOT2_LOGGER.error(f"Erro na execução do bot: {str(e)}")
        traceback.print_exc()
        raise


# Executar se este arquivo for o script principal
if __name__ == "__main__":
    try:
        # Exibir informações de inicialização
        print("=== INICIANDO O BOT TELEGRAM DE SINAIS ===")
        print("Bot configurado para enviar sinais no minuto 13 de cada hora")
        
        # Verificar URLs de GIFs
        print("=== VERIFICANDO DISPONIBILIDADE DOS GIFS ===")
        for nome, url in URLS_GIFS_DIRETAS.items():
            print(f"Verificando GIF {nome}: {url}")
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    print(f"  ✓ GIF {nome} disponível")
                else:
                    print(f"  ✗ GIF {nome} não disponível (código {response.status_code})")
            except Exception as e:
                print(f"  ✗ Erro ao verificar GIF {nome}: {str(e)}")
        
        # Inicializar o bot
        print("\n=== INICIANDO BOT ===")
        BOT2_LOGGER.info("Bot iniciado")
        
        # Teste de envio de GIF (descomentar para testar)
        # bot2_enviar_gif_pos_sinal()
        
        # Iniciar o ciclo de sinais e manter o bot em execução
        iniciar_ambos_bots()
        
    except Exception as e:
        print(f"Erro ao iniciar o bot: {str(e)}")
        traceback.print_exc()

