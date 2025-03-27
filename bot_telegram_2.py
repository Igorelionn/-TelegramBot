# -*- coding: utf-8 -*-
"""
Bot Telegram 2 para envio de sinais em canais separados por idioma.
Versão independente que não depende mais do Bot 1.
Os sinais serão enviados da seguinte forma:
- Canal Português: -1002424874613
- Canal Inglês: -1002453956387
- Canal Espanhol: -1002446547846
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

# Configuração dos canais para cada idioma
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

# ID para compatibilidade com código existente
BOT2_CHAT_ID_CORRETO = BOT2_CHAT_IDS[0]  # Usar o primeiro canal como padrão

# Limite de sinais por hora
BOT2_LIMITE_SINAIS_POR_HORA = 3

# Definições de ativos e categorias (copiado do Bot 1)
# Categorias dos ativos
ATIVOS_CATEGORIAS = {
    # Forex
    "EUR/USD": "Binary",
    "EUR/GBP": "Binary",
    "AUD/CAD": "Binary",
    "AUD/JPY": "Binary",
    "EUR/AUD": "Binary",
    "EUR/CAD": "Binary",
    "EUR/JPY": "Binary",
    "GBP/AUD": "Binary",
    "GBP/JPY": "Binary",
    "GBP/USD": "Binary",
    "NZD/USD": "Binary",
    "USD/CAD": "Binary",
    "USD/CHF": "Binary",
    "USD/JPY": "Binary",
    "AUD/USD": "Binary",
    "AUD/NZD": "Binary",
    "CAD/CHF": "Binary",
    "CAD/JPY": "Binary",
    "CHF/JPY": "Binary",
    "EUR/CHF": "Binary",
    "EUR/NZD": "Binary",
    "GBP/CAD": "Binary",
    "GBP/CHF": "Binary",
    "GBP/NZD": "Binary",
    "NZD/CAD": "Binary",
    "NZD/CHF": "Binary",
    "NZD/JPY": "Binary",
    "USD/MXN": "Binary",
    "USD/NOK": "Binary",
    "USD/PLN": "Binary",
    "USD/SGD": "Binary",
    "USD/TRY": "Binary",
    "USD/ZAR": "Binary",
    
    # Crypto
    "BTC/USD": "Binary",
    "ETH/USD": "Binary",
    "XRP/USD": "Binary",
    "LTC/USD": "Binary",
    "EOS/USD": "Binary",
    "BTC/UAH": "Binary",
    "BTC/EUR": "Binary",
    
    # Stock
    "TSLA": "Binary",
    "AAPL": "Binary",
    "AMZN": "Binary",
    "MSFT": "Binary",
    "FB": "Binary",
    "NFLX": "Binary",
    "GOOGL": "Binary",
    "BABA": "Binary",
    "UBER": "Binary",
    "PFE": "Binary",
    "TWTR": "Binary",
    "SBUX": "Binary",
    "BA": "Binary",
    "WMT": "Binary",
    "KO": "Binary",
    "DIS": "Binary",
    "INTC": "Binary",
    "QCOM": "Binary",
    "CSCO": "Binary",
    "NVDA": "Binary",
    "AMD": "Binary",
    "PYPL": "Binary",
    "EBAY": "Binary",
    "MU": "Binary",
    "SNAP": "Binary",
    "GM": "Binary",
    "F": "Binary",
    
    # Índices
    "OTC FTSE 100 Index": "Binary",
    "OTC US 30 Index": "Binary",
    "OTC US 100 NAS": "Binary",
    "OTC US 500 Index": "Binary",
    "OTC HK 50 Index": "Binary",
    "OTC DE 40 Index": "Binary",
    "OTC DE 30 Index": "Binary",
    "OTC EUR 50 Index": "Binary",
    "OTC UK 100 Index": "Binary",
    "OTC JP 225 Index": "Binary",
    "OTC CHN 50 Index": "Binary",
    "OTC AUS 200 Index": "Binary",
    "OTC FR 40 Index": "Binary",
    "OTC NED 25 Index": "Binary",
    "OTC AUS SPI": "Binary",
    "OTC IT 40 Index": "Binary",
    "OTC SP 35 Index": "Binary",
    "OTC 500 INDU": "Binary",
    
    # Commodities
    "GOLD": "Binary",
    "SILVER": "Binary",
    "OIL": "Binary",
    "PLATINUM": "Binary",
    "COPPER": "Binary",
    "COCOA": "Binary",
    "CORN": "Binary",
    "COTTON": "Binary",
    "SOYBEAN": "Binary",
    "SUGAR": "Binary",
    "COFFEE": "Binary",
    
    # OTC Forex
    "AUD/CAD (OTC)": "Binary",
    "AUD/CHF (OTC)": "Binary",
    "AUD/JPY (OTC)": "Binary",
    "AUD/NZD (OTC)": "Binary",
    "EUR/AUD (OTC)": "Binary",
    "EUR/CAD (OTC)": "Binary",
    "EUR/CHF (OTC)": "Binary",
    "EUR/GBP (OTC)": "Binary",
    "EUR/JPY (OTC)": "Binary",
    "EUR/NZD (OTC)": "Binary",
    "EUR/USD (OTC)": "Binary",
    "GBP/AUD (OTC)": "Binary",
    "GBP/CAD (OTC)": "Binary",
    "GBP/CHF (OTC)": "Binary",
    "GBP/JPY (OTC)": "Binary",
    "GBP/NZD (OTC)": "Binary",
    "GBP/USD (OTC)": "Binary",
    "NZD/CAD (OTC)": "Binary",
    "NZD/CHF (OTC)": "Binary",
    "NZD/JPY (OTC)": "Binary",
    "NZD/USD (OTC)": "Binary",
    "USD/CAD (OTC)": "Binary",
    "USD/CHF (OTC)": "Binary",
    "USD/JPY (OTC)": "Binary",
    "USD/SGD (OTC)": "Binary",
    "USD/TRY (OTC)": "Binary",
    
    # Digital Options
    "Digital_AUD/CAD": "Digital",
    "Digital_AUD/CHF": "Digital",
    "Digital_AUD/JPY": "Digital",
    "Digital_AUD/NZD": "Digital",
    "Digital_AUD/USD": "Digital",
    "Digital_CAD/CHF": "Digital",
    "Digital_CAD/JPY": "Digital",
    "Digital_CHF/JPY": "Digital",
    "Digital_EUR/AUD": "Digital",
    "Digital_EUR/CAD": "Digital",
    "Digital_EUR/CHF": "Digital",
    "Digital_EUR/GBP": "Digital",
    "Digital_EUR/JPY": "Digital",
    "Digital_EUR/NZD": "Digital",
    "Digital_EUR/USD": "Digital",
    "Digital_GBP/AUD": "Digital",
    "Digital_GBP/CAD": "Digital",
    "Digital_GBP/CHF": "Digital",
    "Digital_GBP/JPY": "Digital",
    "Digital_GBP/NZD": "Digital",
    "Digital_GBP/USD": "Digital",
    "Digital_NZD/CAD": "Digital",
    "Digital_NZD/CHF": "Digital",
    "Digital_NZD/JPY": "Digital",
    "Digital_NZD/USD": "Digital",
    "Digital_USD/CAD": "Digital",
    "Digital_USD/CHF": "Digital",
    "Digital_USD/JPY": "Digital",
    "Digital_USD/NOK": "Digital",
    "Digital_USD/PLN": "Digital",
    "Digital_USD/SGD": "Digital",
    "Digital_USD/TRY": "Digital",
    "Digital_USD/ZAR": "Digital",
    "Digital_AUD/CAD (OTC)": "Digital",
    "Digital_AUD/JPY (OTC)": "Digital",
    "Digital_EUR/AUD (OTC)": "Digital",
    "Digital_EUR/CAD (OTC)": "Digital",
    "Digital_EUR/CHF (OTC)": "Digital",
    "Digital_EUR/GBP (OTC)": "Digital",
    "Digital_EUR/JPY (OTC)": "Digital",
    "Digital_EUR/USD (OTC)": "Digital",
    "Digital_GBP/AUD (OTC)": "Digital",
    "Digital_GBP/JPY (OTC)": "Digital",
    "Digital_GBP/USD (OTC)": "Digital",
    "Digital_NZD/USD (OTC)": "Digital",
    "Digital_USD/CAD (OTC)": "Digital",
    "Digital_USD/CHF (OTC)": "Digital",
    "Digital_USD/JPY (OTC)": "Digital",
    "Digital_USD/SGD (OTC)": "Digital",
    "Digital_USD/TRY (OTC)": "Digital",
    
    # Blitz
    "EURUSD-OTCFX": "Blitz",
    "GBPUSD-OTCFX": "Blitz",
    "EURGBP-OTCFX": "Blitz",
    "USDCHF-OTCFX": "Blitz",
    "EURJPY-OTCFX": "Blitz",
    "NZDUSD-OTCFX": "Blitz",
    "AUDUSD-OTCFX": "Blitz",
    "USDJPY-OTCFX": "Blitz",
    "USDCAD-OTCFX": "Blitz",
    "AUDJPY-OTCFX": "Blitz",
    "GBPJPY-OTCFX": "Blitz",
}

# Configurações de horários para os ativos
# Configurações de horários
HORARIOS_PADRAO = {
    "forex_padrao": {
        "Monday": ["00:05-23:59"],
        "Tuesday": ["00:05-23:59"],
        "Wednesday": ["00:05-23:59"],
        "Thursday": ["00:05-23:59"],
        "Friday": ["00:05-21:00"],
        "Saturday": [],
        "Sunday": []
    },
    "otc_padrao": {
        "Monday": ["00:05-23:59"],
        "Tuesday": ["00:05-23:59"],
        "Wednesday": ["00:05-23:59"],
        "Thursday": ["00:05-23:59"],
        "Friday": ["00:05-23:59"],
        "Saturday": ["00:05-23:59"],
        "Sunday": ["00:05-23:59"]
    },
    "crypto_padrao": {
        "Monday": ["00:05-23:59"],
        "Tuesday": ["00:05-23:59"],
        "Wednesday": ["00:05-23:59"],
        "Thursday": ["00:05-23:59"],
        "Friday": ["00:05-23:59"],
        "Saturday": ["00:05-23:59"],
        "Sunday": ["00:05-23:59"]
    },
    "stock_padrao": {
        "Monday": ["09:30-16:00"],
        "Tuesday": ["09:30-16:00"],
        "Wednesday": ["09:30-16:00"],
        "Thursday": ["09:30-16:00"],
        "Friday": ["09:30-16:00"],
        "Saturday": [],
        "Sunday": []
    },
    "indices_padrao": {
        "Monday": ["00:05-23:59"],
        "Tuesday": ["00:05-23:59"],
        "Wednesday": ["00:05-23:59"],
        "Thursday": ["00:05-23:59"],
        "Friday": ["00:05-23:59"],
        "Saturday": ["00:05-23:59"],
        "Sunday": ["00:05-23:59"]
    },
    "btc_padrao": {
        "Monday": ["00:05-23:59"],
        "Tuesday": ["00:05-23:59"],
        "Wednesday": ["00:05-23:59"],
        "Thursday": ["00:05-23:59"],
        "Friday": ["00:05-23:59"],
        "Saturday": ["00:05-23:59"],
        "Sunday": ["00:05-23:59"]
    },
    "blitz_padrao": {
        "Monday": ["00:05-23:59"],
        "Tuesday": ["00:05-23:59"],
        "Wednesday": ["00:05-23:59"],
        "Thursday": ["00:05-23:59"],
        "Friday": ["00:05-23:59"],
        "Saturday": ["00:05-23:59"],
        "Sunday": ["00:05-23:59"]
    }
}

# Mapeamento de ativos para padrões de horários
assets = {}

# Configuração para ativos Forex padrão
for ativo in [
    "EUR/USD", "EUR/GBP", "AUD/CAD", "AUD/JPY", "EUR/AUD", "EUR/CAD", "EUR/JPY", "GBP/AUD", "GBP/JPY", "GBP/USD", "NZD/USD", "USD/CAD", "USD/CHF", "USD/JPY",
    "AUD/USD", "AUD/NZD", "CAD/CHF", "CAD/JPY", "CHF/JPY", "EUR/CHF", "EUR/NZD", "GBP/CAD", "GBP/CHF", "GBP/NZD", "NZD/CAD", "NZD/CHF", "NZD/JPY", "USD/MXN",
    "USD/NOK", "USD/PLN", "USD/SGD", "USD/TRY", "USD/ZAR"
]:
    assets[ativo] = HORARIOS_PADRAO["forex_padrao"]

# Configuração para ativos OTC
for ativo in [
    "AUD/CAD (OTC)", "AUD/CHF (OTC)", "AUD/JPY (OTC)", "AUD/NZD (OTC)", "EUR/AUD (OTC)", "EUR/CAD (OTC)", "EUR/CHF (OTC)", "EUR/GBP (OTC)", "EUR/JPY (OTC)",
    "EUR/NZD (OTC)", "EUR/USD (OTC)", "GBP/AUD (OTC)", "GBP/CAD (OTC)", "GBP/CHF (OTC)", "GBP/JPY (OTC)", "GBP/NZD (OTC)", "GBP/USD (OTC)", "NZD/CAD (OTC)",
    "NZD/CHF (OTC)", "NZD/JPY (OTC)", "NZD/USD (OTC)", "USD/CAD (OTC)", "USD/CHF (OTC)", "USD/JPY (OTC)", "USD/SGD (OTC)", "USD/TRY (OTC)"
]:
    assets[ativo] = HORARIOS_PADRAO["otc_padrao"]

# Configuração para ativos Digital Options padrão
for ativo in [
    "Digital_AUD/CAD", "Digital_AUD/CHF", "Digital_AUD/JPY", "Digital_AUD/NZD", "Digital_AUD/USD", "Digital_CAD/CHF", "Digital_CAD/JPY", "Digital_CHF/JPY",
    "Digital_EUR/AUD", "Digital_EUR/CAD", "Digital_EUR/CHF", "Digital_EUR/GBP", "Digital_EUR/JPY", "Digital_EUR/NZD", "Digital_EUR/USD", "Digital_GBP/AUD",
    "Digital_GBP/CAD", "Digital_GBP/CHF", "Digital_GBP/JPY", "Digital_GBP/NZD", "Digital_GBP/USD", "Digital_NZD/CAD", "Digital_NZD/CHF", "Digital_NZD/JPY",
    "Digital_NZD/USD", "Digital_USD/CAD", "Digital_USD/CHF", "Digital_USD/JPY", "Digital_USD/NOK", "Digital_USD/PLN", "Digital_USD/SGD", "Digital_USD/TRY",
    "Digital_USD/ZAR"
]:
    assets[ativo] = HORARIOS_PADRAO["forex_padrao"]

# Configuração para ativos Digital Options OTC
for ativo in [
    "Digital_AUD/CAD (OTC)", "Digital_AUD/JPY (OTC)", "Digital_EUR/AUD (OTC)", "Digital_EUR/CAD (OTC)", "Digital_EUR/CHF (OTC)", "Digital_EUR/GBP (OTC)",
    "Digital_EUR/JPY (OTC)", "Digital_EUR/USD (OTC)", "Digital_GBP/AUD (OTC)", "Digital_GBP/JPY (OTC)", "Digital_GBP/USD (OTC)", "Digital_NZD/USD (OTC)",
    "Digital_USD/CAD (OTC)", "Digital_USD/CHF (OTC)", "Digital_USD/JPY (OTC)", "Digital_USD/SGD (OTC)", "Digital_USD/TRY (OTC)"
]:
    assets[ativo] = HORARIOS_PADRAO["otc_padrao"]

# Configuração para ativos Crypto
for ativo in ["BTC/USD", "ETH/USD", "XRP/USD", "LTC/USD", "EOS/USD", "BTC/UAH", "BTC/EUR"]:
    assets[ativo] = HORARIOS_PADRAO["crypto_padrao"]

# Configuração para ativos Stocks
for ativo in [
    "TSLA", "AAPL", "AMZN", "MSFT", "FB", "NFLX", "GOOGL", "BABA", "UBER", "PFE", "TWTR", "SBUX", "BA", "WMT", "KO", "DIS", "INTC", "QCOM", "CSCO", "NVDA",
    "AMD", "PYPL", "EBAY", "MU", "SNAP", "GM", "F"
]:
    assets[ativo] = HORARIOS_PADRAO["stock_padrao"]

# Configuração para ativos Índices
for ativo in [
    "OTC FTSE 100 Index", "OTC US 30 Index", "OTC US 100 NAS", "OTC US 500 Index", "OTC HK 50 Index", "OTC DE 40 Index", "OTC DE 30 Index", "OTC EUR 50 Index",
    "OTC UK 100 Index", "OTC JP 225 Index", "OTC CHN 50 Index", "OTC AUS 200 Index", "OTC FR 40 Index", "OTC NED 25 Index", "OTC AUS SPI", "OTC IT 40 Index",
    "OTC SP 35 Index", "OTC 500 INDU"
]:
    assets[ativo] = HORARIOS_PADRAO["indices_padrao"]

# Configuração para ativos Commodities
for ativo in ["GOLD", "SILVER", "OIL", "PLATINUM", "COPPER", "COCOA", "CORN", "COTTON", "SOYBEAN", "SUGAR", "COFFEE"]:
    assets[ativo] = HORARIOS_PADRAO["forex_padrao"]

# Configuração para ativos Blitz
for ativo in [
    "EURUSD-OTCFX", "GBPUSD-OTCFX", "EURGBP-OTCFX", "USDCHF-OTCFX", "EURJPY-OTCFX", "NZDUSD-OTCFX", "AUDUSD-OTCFX", "USDJPY-OTCFX", "USDCAD-OTCFX",
    "AUDJPY-OTCFX", "GBPJPY-OTCFX"
]:
    assets[ativo] = HORARIOS_PADRAO["blitz_padrao"]

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
    Formata a mensagem do sinal para o idioma especificado.
    Retorna a mensagem formatada no idioma correto (pt, en ou es).
    """
    ativo = sinal['ativo']
    direcao = sinal['direcao']
    categoria = sinal['categoria']
    tempo_expiracao_minutos = sinal['tempo_expiracao_minutos']

    # Debug: registrar os dados sendo usados para formatar a mensagem
    BOT2_LOGGER.info(f"Formatando mensagem com: ativo={ativo}, direção={direcao}, categoria={categoria}, tempo={tempo_expiracao_minutos}, idioma={idioma}")

    # Formatação do nome do ativo para exibição
    nome_ativo_exibicao = ativo.replace("Digital_", "") if ativo.startswith("Digital_") else ativo
    if "(OTC)" in nome_ativo_exibicao and not " (OTC)" in nome_ativo_exibicao:
        nome_ativo_exibicao = nome_ativo_exibicao.replace("(OTC)", " (OTC)")

    # Configura ações e emojis conforme a direção
    action_pt = "COMPRA" if direcao == 'buy' else "VENDA"
    action_en = "BUY" if direcao == 'buy' else "SELL"
    action_es = "COMPRA" if direcao == 'buy' else "VENTA"
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

    # Textos de expiração em diferentes idiomas
    expiracao_texto_pt = f"⏳ Expiração: {tempo_expiracao_minutos} minuto{'s' if tempo_expiracao_minutos > 1 else ''} ({hora_exp_formatada})"
    expiracao_texto_en = f"⏳ Expiration: {tempo_expiracao_minutos} minute{'s' if tempo_expiracao_minutos > 1 else ''} ({hora_exp_formatada})"
    expiracao_texto_es = f"⏳ Expiración: {tempo_expiracao_minutos} minuto{'s' if tempo_expiracao_minutos > 1 else ''} ({hora_exp_formatada})"
    
    # Mensagem em PT
    mensagem_pt = (f"⚠️TRADE RÁPIDO⚠️\n\n"
            f"💵 Ativo: {nome_ativo_exibicao}\n"
            f"🏷️ Opções: {categoria}\n"
            f"{emoji} {action_pt}\n"
            f"➡ Entrada: {hora_entrada_formatada}\n"
            f"{expiracao_texto_pt}\n"
            f"Reentrada 1 - {hora_reentrada1_formatada}\n"
            f"Reentrada 2 - {hora_reentrada2_formatada}")
            
    # Mensagem em EN
    mensagem_en = (f"⚠️QUICK TRADE⚠️\n\n"
            f"💵 Asset: {nome_ativo_exibicao}\n"
            f"🏷️ Options: {categoria}\n"
            f"{emoji} {action_en}\n"
            f"➡ Entry: {hora_entrada_formatada}\n"
            f"{expiracao_texto_en}\n"
            f"Re-entry 1 - {hora_reentrada1_formatada}\n"
            f"Re-entry 2 - {hora_reentrada2_formatada}")
            
    # Mensagem em ES
    mensagem_es = (f"⚠️COMERCIO RÁPIDO⚠️\n\n"
            f"💵 Activo: {nome_ativo_exibicao}\n"
            f"🏷️ Opciones: {categoria}\n"
            f"{emoji} {action_es}\n"
            f"➡ Entrada: {hora_entrada_formatada}\n"
            f"{expiracao_texto_es}\n"
            f"Reentrada 1 - {hora_reentrada1_formatada}\n"
            f"Reentrada 2 - {hora_reentrada2_formatada}")
            
    # Verificar se há algum texto não esperado antes de retornar a mensagem
    if idioma == "pt":
        mensagem_final = mensagem_pt
    elif idioma == "en":
        mensagem_final = mensagem_en
    elif idioma == "es":
        mensagem_final = mensagem_es
    else:  # Padrão para qualquer outro idioma (português)
        mensagem_final = mensagem_pt
        
    BOT2_LOGGER.info(f"Mensagem formatada final para idioma {idioma}: {mensagem_final}")
    return mensagem_final

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

# Criar os subdiretórios dos idiomas para vídeos pós-sinal
VIDEOS_POS_SINAL_PT_DIR = os.path.join(VIDEOS_POS_SINAL_DIR, "pt")
VIDEOS_POS_SINAL_EN_DIR = os.path.join(VIDEOS_POS_SINAL_DIR, "en")
VIDEOS_POS_SINAL_ES_DIR = os.path.join(VIDEOS_POS_SINAL_DIR, "es")

# Atualização dos diretórios e arquivos para os vídeos especiais por idioma
VIDEOS_ESPECIAL_PT_DIR = os.path.join(VIDEOS_ESPECIAL_DIR, "pt")
VIDEOS_ESPECIAL_EN_DIR = os.path.join(VIDEOS_ESPECIAL_DIR, "en")
VIDEOS_ESPECIAL_ES_DIR = os.path.join(VIDEOS_ESPECIAL_DIR, "es")

# Criar os subdiretórios se não existirem
os.makedirs(VIDEOS_POS_SINAL_DIR, exist_ok=True)
os.makedirs(VIDEOS_ESPECIAL_DIR, exist_ok=True)
os.makedirs(VIDEOS_PROMO_DIR, exist_ok=True)
os.makedirs(VIDEOS_POS_SINAL_PT_DIR, exist_ok=True)
os.makedirs(VIDEOS_POS_SINAL_EN_DIR, exist_ok=True)
os.makedirs(VIDEOS_POS_SINAL_ES_DIR, exist_ok=True)
os.makedirs(VIDEOS_ESPECIAL_PT_DIR, exist_ok=True)
os.makedirs(VIDEOS_ESPECIAL_EN_DIR, exist_ok=True)
os.makedirs(VIDEOS_ESPECIAL_ES_DIR, exist_ok=True)

# Configurar vídeos pós-sinal específicos para cada idioma 
VIDEOS_POS_SINAL = {
    "pt": [
        os.path.join(VIDEOS_POS_SINAL_PT_DIR, "padrão.mp4"),  # Vídeo padrão em português (9/10)
        os.path.join(VIDEOS_POS_SINAL_PT_DIR, "especial.mp4")  # Vídeo especial em português (1/10)
    ],
    "en": [
        os.path.join(VIDEOS_POS_SINAL_EN_DIR, "padrao.mp4"),  # Vídeo padrão em inglês (9/10)
        os.path.join(VIDEOS_POS_SINAL_EN_DIR, "especial.mp4")  # Vídeo especial em inglês (1/10)
    ],
    "es": [
        os.path.join(VIDEOS_POS_SINAL_ES_DIR, "padrao.mp4"),  # Vídeo padrão em espanhol (9/10)
        os.path.join(VIDEOS_POS_SINAL_ES_DIR, "especial.mp4")  # Vídeo especial em espanhol (1/10)
    ]
}

# Vídeo especial a cada 3 sinais (por idioma)
VIDEOS_ESPECIAIS = {
    "pt": os.path.join(VIDEOS_ESPECIAL_DIR, "especial.mp4"),
    "en": os.path.join(VIDEOS_ESPECIAL_EN_DIR, "especial.mp4"),
    "es": os.path.join(VIDEOS_ESPECIAL_ES_DIR, "especial.mp4")
}

# Vídeos promocionais por idioma
VIDEOS_PROMO = {
    "pt": os.path.join(VIDEOS_PROMO_DIR, "pt.mp4"),
    "en": os.path.join(VIDEOS_PROMO_DIR, "en.mp4"),
    "es": os.path.join(VIDEOS_PROMO_DIR, "es.mp4")
}

# Vídeo GIF especial que vai ser enviado a cada 3 sinais (apenas no canal português)
VIDEO_GIF_ESPECIAL_PT = os.path.join(VIDEOS_ESPECIAL_DIR, "gif_especial_pt.mp4")

# Contador para controle dos GIFs pós-sinal
contador_pos_sinal = 0
contador_desde_ultimo_especial = 0

# Função para enviar GIF pós-sinal (1 minuto após cada sinal)
def bot2_enviar_gif_pos_sinal():
    """
    Envia um vídeo 1 minuto após cada sinal.
    Escolhe entre dois vídeos: o primeiro é enviado em 9 de 10 sinais, o segundo em 1 de 10 sinais.
    A escolha do vídeo especial (segundo) é aleatória, garantindo apenas a proporção de 1 a cada 10.
    O vídeo enviado é específico para o idioma de cada canal.
    """
    global contador_pos_sinal, contador_desde_ultimo_especial
    
    try:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] INICIANDO ENVIO DO VÍDEO PÓS-SINAL (1 minuto após o sinal)...")
        
        # Incrementar os contadores
        contador_pos_sinal += 1
        contador_desde_ultimo_especial += 1
        
        # Decidir qual vídeo enviar (9/10 o primeiro, 1/10 o segundo)
        escolha_video = 0  # Índice do primeiro vídeo por padrão
        
        # Lógica para seleção aleatória do vídeo especial
        if contador_desde_ultimo_especial >= 10:
            # Forçar o vídeo especial se já passaram 10 sinais desde o último
            escolha_video = 1
            BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO O VÍDEO ESPECIAL (forçado após 10 sinais)")
            contador_desde_ultimo_especial = 0
        elif contador_desde_ultimo_especial > 1:
            # A probabilidade de enviar o vídeo especial aumenta conforme
            # mais sinais passam sem que o especial seja enviado
            probabilidade = (contador_desde_ultimo_especial - 1) / 10.0
            if random.random() < probabilidade:
                escolha_video = 1
                BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO O VÍDEO ESPECIAL (aleatório com probabilidade {probabilidade:.2f})")
                contador_desde_ultimo_especial = 0
            else:
                BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO O VÍDEO PADRÃO (probabilidade de especial era {probabilidade:.2f})")
        else:
            BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO O VÍDEO PADRÃO (muito cedo para especial)")
        
        # Loop para enviar aos canais configurados
        for chat_id in BOT2_CHAT_IDS:
            # Pegar configuração do canal
            config_canal = BOT2_CANAIS_CONFIG[chat_id]
            idioma = config_canal["idioma"]
            
            # Obter o caminho do vídeo escolhido de acordo com o idioma
            # Se o idioma não existir, usa o português como fallback
            if idioma in VIDEOS_POS_SINAL:
                video_path = VIDEOS_POS_SINAL[idioma][escolha_video]
            else:
                video_path = VIDEOS_POS_SINAL["pt"][escolha_video]
                
            BOT2_LOGGER.info(f"[{horario_atual}] Caminho do vídeo escolhido para {idioma}: {video_path}")
            
            # Verificar se o arquivo existe
            if not os.path.exists(video_path):
                BOT2_LOGGER.error(f"[{horario_atual}] ERRO: Arquivo de vídeo não encontrado: {video_path}")
                # Listar os arquivos na pasta para debug
                pasta_videos = os.path.dirname(video_path)
                BOT2_LOGGER.info(f"[{horario_atual}] Arquivos na pasta {pasta_videos}: {os.listdir(pasta_videos) if os.path.exists(pasta_videos) else 'PASTA NÃO EXISTE'}")
                # Tentar usar o vídeo em português como backup se o idioma não for PT
                if idioma != "pt":
                    video_path = VIDEOS_POS_SINAL["pt"][escolha_video]
                    BOT2_LOGGER.info(f"[{horario_atual}] Tentando usar vídeo em português como backup: {video_path}")
                    if not os.path.exists(video_path):
                        BOT2_LOGGER.error(f"[{horario_atual}] ERRO: Arquivo de vídeo backup também não encontrado: {video_path}")
                        continue
                else:
                    continue
            
            BOT2_LOGGER.info(f"[{horario_atual}] Arquivo de vídeo encontrado: {video_path}")
            
            # Enviar o vídeo escolhido
            BOT2_LOGGER.info(f"[{horario_atual}] Enviando vídeo para o canal {chat_id} em {idioma}...")
            url_base_video = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendVideo"
            
            try:
                with open(video_path, 'rb') as video_file:
                    files = {
                        'video': video_file
                    }
                    
                    payload_video = {
                        'chat_id': chat_id,
                        'parse_mode': 'HTML'
                    }
                    
                    BOT2_LOGGER.info(f"[{horario_atual}] Enviando requisição para API do Telegram...")
                    resposta_video = requests.post(url_base_video, data=payload_video, files=files)
                    BOT2_LOGGER.info(f"[{horario_atual}] Resposta da API: {resposta_video.status_code}")
                    
                    if resposta_video.status_code != 200:
                        BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar vídeo pós-sinal para o canal {chat_id}: {resposta_video.text}")
                    else:
                        tipo_video = "ESPECIAL (1/10)" if escolha_video == 1 else "PADRÃO (9/10)"
                        BOT2_LOGGER.info(f"[{horario_atual}] VÍDEO PÓS-SINAL {tipo_video} ENVIADO COM SUCESSO para o canal {chat_id} em {idioma}")
            except Exception as e:
                BOT2_LOGGER.error(f"[{horario_atual}] Erro ao abrir ou enviar arquivo de vídeo: {str(e)}")
    
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
        
        # Loop para enviar aos canais configurados
        for chat_id in BOT2_CHAT_IDS:
            # Pegar configuração do canal
            config_canal = BOT2_CANAIS_CONFIG[chat_id]
            idioma = config_canal["idioma"]
            
            # Preparar textos baseados no idioma com link diretamente no texto
            if idioma == "pt":
                texto_mensagem = (
                    "👉🏼Abram a corretora Pessoal\n\n"
                    "⚠️FIQUEM ATENTOS⚠️\n\n"
                    "🔥Cadastre-se na XXBROKER agora mesmo🔥\n\n"
                    f"➡️ <a href=\"{XXBROKER_URL}\">CLICANDO AQUI</a>"
                )
            elif idioma == "en":
                texto_mensagem = (
                    "👉🏼Open the broker now\n\n"
                    "⚠️STAY ALERT⚠️\n\n"
                    "🔥Register on XXBROKER right now🔥\n\n"
                    f"➡️ <a href=\"{XXBROKER_URL}\">CLICK HERE</a>"
                )
            elif idioma == "es":
                texto_mensagem = (
                    "👉🏼Abran el corredor ahora\n\n"
                    "⚠️ESTÉN ATENTOS⚠️\n\n"
                    "🔥Regístrese en XXBROKER ahora mismo🔥\n\n"
                    f"➡️ <a href=\"{XXBROKER_URL}\">CLIC AQUÍ</a>"
                )
            else:
                texto_mensagem = (
                    "👉🏼Abram a corretora Pessoal\n\n"
                    "⚠️FIQUEM ATENTOS⚠️\n\n"
                    "🔥Cadastre-se na XXBROKER agora mesmo🔥\n\n"
                    f"➡️ <a href=\"{XXBROKER_URL}\">CLICANDO AQUI</a>"
                )
            
            # Obter caminho do vídeo específico para este idioma
            video_path = VIDEOS_PROMO.get(idioma, VIDEOS_PROMO["pt"])  # Usa o vídeo PT como fallback
            
            # Verificar se o arquivo existe
            if not os.path.exists(video_path):
                BOT2_LOGGER.error(f"[{horario_atual}] Arquivo de vídeo promocional não encontrado: {video_path}")
            else:
                BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO VÍDEO PROMOCIONAL PRÉ-SINAL para o canal {chat_id} em {idioma}...")
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
            BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO MENSAGEM PROMOCIONAL PRÉ-SINAL para o canal {chat_id} em {idioma}...")
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
    Para todos os canais: envia o vídeo específico do idioma e depois a mensagem.
    """
    try:
        horario_atual = bot2_obter_hora_brasilia().strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] INICIANDO ENVIO DA MENSAGEM PROMOCIONAL ESPECIAL (A CADA 3 SINAIS) - Contador: {bot2_contador_sinais}...")
        
        # Loop para enviar aos canais configurados
        for chat_id in BOT2_CHAT_IDS:
            # Pegar configuração do canal
            config_canal = BOT2_CANAIS_CONFIG[chat_id]
            idioma = config_canal["idioma"]
            
            # Preparar textos baseados no idioma com links diretamente no texto
            if idioma == "pt":
                texto_mensagem = (
                    "Seguimos com as operações ✅\n\n"
                    "Mantenham a corretora aberta!!\n\n\n"
                    "Pra quem ainda não começou a ganhar dinheiro com a gente👇🏻\n\n"
                    f"<a href=\"{VIDEO_TELEGRAM_URL}\">CLIQUE AQUI E ASSISTA O VÍDEO</a>\n\n"
                    "🔥Cadastre-se na XXBROKER agora mesmo🔥\n\n"
                    f"➡️ <a href=\"{XXBROKER_URL}\">CLICANDO AQUI</a>"
                )
            elif idioma == "en":
                texto_mensagem = (
                    "We continue with operations ✅\n\n"
                    "Keep the broker open!!\n\n\n"
                    "For those who haven't started making money with us yet👇🏻\n\n"
                    f"<a href=\"{VIDEO_TELEGRAM_URL}\">CLICK HERE AND WATCH THE VIDEO</a>\n\n"
                    "🔥Register on XXBROKER right now🔥\n\n"
                    f"➡️ <a href=\"{XXBROKER_URL}\">CLICK HERE</a>"
                )
            elif idioma == "es":
                texto_mensagem = (
                    "Continuamos con las operaciones ✅\n\n"
                    "¡Mantengan el corredor abierto!\n\n\n"
                    "Para quienes aún no han comenzado a ganar dinero con nosotros👇🏻\n\n"
                    f"<a href=\"{VIDEO_TELEGRAM_URL}\">HAZ CLIC AQUÍ Y MIRA EL VIDEO</a>\n\n"
                    "🔥Regístrese en XXBROKER ahora mismo🔥\n\n"
                    f"➡️ <a href=\"{XXBROKER_URL}\">CLIC AQUÍ</a>"
                )
            else:
                texto_mensagem = (
                    "Seguimos com as operações ✅\n\n"
                    "Mantenham a corretora aberta!!\n\n\n"
                    "Pra quem ainda não começou a ganhar dinheiro com a gente👇🏻\n\n"
                    f"<a href=\"{VIDEO_TELEGRAM_URL}\">CLIQUE AQUI E ASSISTA O VÍDEO</a>\n\n"
                    "🔥Cadastre-se na XXBROKER agora mesmo🔥\n\n"
                    f"➡️ <a href=\"{XXBROKER_URL}\">CLICANDO AQUI</a>"
                )
            
            # Obter o caminho do vídeo especial específico para este idioma
            if idioma in VIDEOS_ESPECIAIS:
                video_path = VIDEOS_ESPECIAIS[idioma]
            else:
                video_path = VIDEOS_ESPECIAIS["pt"]  # Fallback para português
                
            # Verificar se o arquivo existe
            if not os.path.exists(video_path):
                BOT2_LOGGER.error(f"[{horario_atual}] Arquivo de vídeo especial não encontrado: {video_path}")
                # Tentar usar o vídeo em português como backup se o idioma não for PT
                if idioma != "pt":
                    video_path = VIDEOS_ESPECIAIS["pt"]
                    BOT2_LOGGER.info(f"[{horario_atual}] Tentando usar vídeo especial em português como backup: {video_path}")
                    if not os.path.exists(video_path):
                        BOT2_LOGGER.error(f"[{horario_atual}] ERRO: Arquivo de vídeo especial backup também não encontrado: {video_path}")
                        # Prosseguir para enviar apenas a mensagem de texto
                    else:
                        # Enviar vídeo
                        BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO VÍDEO ESPECIAL (A CADA 3 SINAIS) em português para o canal {chat_id}...")
                        bot2_enviar_video_especial(video_path, chat_id, horario_atual)
                else:
                    # Prosseguir para enviar apenas a mensagem de texto
                    pass
            else:
                # Enviar vídeo
                BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO VÍDEO ESPECIAL (A CADA 3 SINAIS) em {idioma} para o canal {chat_id}...")
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
                if not os.path.exists(VIDEO_GIF_ESPECIAL_PT):
                    BOT2_LOGGER.error(f"[{horario_atual}] Arquivo de GIF especial não encontrado: {VIDEO_GIF_ESPECIAL_PT}")
                    BOT2_LOGGER.info(f"[{horario_atual}] Listando arquivos na pasta {VIDEOS_ESPECIAL_DIR}: {os.listdir(VIDEOS_ESPECIAL_DIR) if os.path.exists(VIDEOS_ESPECIAL_DIR) else 'PASTA NÃO EXISTE'}")
                    return
                
                BOT2_LOGGER.info(f"[{horario_atual}] Enviando GIF especial para o canal português {chat_id}...")
                # Usar sendVideo em vez de sendAnimation para maior compatibilidade
                url_base_video = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendVideo"
                
                with open(VIDEO_GIF_ESPECIAL_PT, 'rb') as gif_file:
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
                        with open(VIDEO_GIF_ESPECIAL_PT, 'rb') as alt_file:
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

# Modificar a função bot2_send_message para alterar os tempos de agendamento
def bot2_send_message(ignorar_anti_duplicacao=False):
    global bot2_contador_sinais
    
    try:
        # Verifica se já enviou muito recentemente (anti-duplicação)
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.info(f"[{horario_atual}] INICIANDO ENVIO DO SINAL...")
        
        if not ignorar_anti_duplicacao and hasattr(bot2_send_message, 'ultimo_envio_timestamp'):
            ultimo_envio = bot2_send_message.ultimo_envio_timestamp
            diferenca = (agora - ultimo_envio).total_seconds()
            if diferenca < 60:  # Se a última mensagem foi enviada há menos de 1 minuto
                BOT2_LOGGER.info(f"[{horario_atual}] Anti-duplicação: Mensagem ignorada. Última enviada há {diferenca:.1f} segundos.")
                return

        # Atualiza o timestamp da última mensagem enviada para evitar duplicações
        bot2_send_message.ultimo_envio_timestamp = agora

        # Verifica se não excedeu o limite por hora
        hora_atual = agora.replace(minute=0, second=0, microsecond=0)
        if hora_atual not in bot2_send_message.contagem_por_hora:
            bot2_send_message.contagem_por_hora = {hora_atual: 0}

        if not ignorar_anti_duplicacao and bot2_send_message.contagem_por_hora[hora_atual] >= BOT2_LIMITE_SINAIS_POR_HORA:
            BOT2_LOGGER.info(f"[{horario_atual}] Limite de {BOT2_LIMITE_SINAIS_POR_HORA} sinais por hora atingido. Ignorando este sinal.")
            return

        # Gera um sinal aleatório para enviar
        sinal = bot2_gerar_sinal_aleatorio()
        if not sinal:
            BOT2_LOGGER.error(f"[{horario_atual}] Erro ao gerar sinal. Abortando envio.")
            return

        # Incrementa o contador de mensagens enviadas nesta hora
        bot2_send_message.contagem_por_hora[hora_atual] += 1

        # Registra a hora de geração do sinal
        BOT2_LOGGER.info(f"[{horario_atual}] SINAL GERADO. Enviando para todos os canais configurados...")

        # Obter dados do sinal
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        categoria = sinal['categoria']
        tempo_expiracao_minutos = sinal['tempo_expiracao_minutos']

        # Calcular horários para a operação
        hora_entrada = agora + timedelta(minutes=2)
        hora_expiracao = hora_entrada + timedelta(minutes=tempo_expiracao_minutos)
        hora_reentrada1 = hora_expiracao + timedelta(minutes=1)
        hora_reentrada2 = hora_reentrada1 + timedelta(minutes=tempo_expiracao_minutos)
        
        BOT2_LOGGER.info(f"[{horario_atual}] Detalhes do sinal: Ativo={ativo}, Direção={direcao}, Categoria={categoria}, Expiração={tempo_expiracao_minutos}min")
        BOT2_LOGGER.info(f"[{horario_atual}] Horários: Entrada={hora_entrada.strftime('%H:%M:%S')}, Expiração={hora_expiracao.strftime('%H:%M:%S')}, Reentrada1={hora_reentrada1.strftime('%H:%M:%S')}, Reentrada2={hora_reentrada2.strftime('%H:%M:%S')}")

        # Obtém a hora atual para formatação na mensagem
        hora_formatada = agora.strftime("%H:%M")

        # Loop para enviar aos canais configurados com base no idioma
        for chat_id in BOT2_CHAT_IDS:
            # Pegar configuração do canal
            config_canal = BOT2_CANAIS_CONFIG[chat_id]
            idioma = config_canal["idioma"]
            link_corretora = config_canal["link_corretora"]

            # Enviar apenas no idioma configurado para este canal
            mensagem = bot2_formatar_mensagem(sinal, hora_formatada, idioma)
            
            # IMPORTANTE: Log detalhado do conteúdo exato da mensagem para debug
            BOT2_LOGGER.info(f"[{horario_atual}] CONTEÚDO EXATO DA MENSAGEM DO SINAL: {mensagem}")

            # Texto do botão de acordo com o idioma
            texto_botao = "🔗 Abrir corretora"  # Padrão em português

            if idioma == "en":
                texto_botao = "🔗 Open broker"
            elif idioma == "es":
                texto_botao = "🔗 Abrir corredor"

            # Configura o teclado inline com o link da corretora
            teclado_inline = {
                "inline_keyboard": [
                    [
                        {
                            "text": texto_botao,
                            "url": link_corretora
                        }
                    ]
                ]
            }

            # Envia a mensagem para o canal específico
            url_base = f"https://api.telegram.org/bot{BOT2_TOKEN}/sendMessage"

            payload = {
                'chat_id': chat_id,
                'text': mensagem,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
                'reply_markup': json.dumps(teclado_inline)
            }

            BOT2_LOGGER.info(f"[{horario_atual}] ENVIANDO MENSAGEM DO SINAL em {idioma} para o canal {chat_id}...")
            resposta = requests.post(url_base, data=payload)

            if resposta.status_code != 200:
                BOT2_LOGGER.error(f"[{horario_atual}] Erro ao enviar sinal para o canal {chat_id}: {resposta.text}")
            else:
                BOT2_LOGGER.info(f"[{horario_atual}] MENSAGEM DO SINAL ENVIADA COM SUCESSO para o canal {chat_id} no idioma {idioma}")

        # Registra estatísticas de envio
        bot2_registrar_envio(ativo, direcao, categoria)
        
        # Incrementa o contador global de sinais
        bot2_contador_sinais += 1
        BOT2_LOGGER.info(f"[{horario_atual}] Contador de sinais incrementado: {bot2_contador_sinais}")
        
        # Agendar o envio do GIF pós-sinal para 5 minutos depois (alterado de 1 minuto)
        BOT2_LOGGER.info(f"[{horario_atual}] Agendando envio do GIF pós-sinal para daqui a 5 minutos...")
        import threading
        timer_pos_sinal = threading.Timer(300.0, bot2_enviar_gif_pos_sinal)  # 300 segundos = 5 minutos
        timer_pos_sinal.start()
        
        # Verifica se deve enviar a mensagem promocional especial (a cada 3 sinais)
        if bot2_contador_sinais % 3 == 0:
            # Agendar o envio do GIF especial para 6 minutos - 1 segundo depois (apenas canal PT)
            BOT2_LOGGER.info(f"[{horario_atual}] Agendando envio do GIF especial PT para daqui a {359} segundos...")
            timer_gif_especial = threading.Timer(359.0, bot2_enviar_gif_especial_pt)  # 359 segundos = 5 minutos e 59 segundos
            timer_gif_especial.start()
            
            # Agendar o envio da mensagem promocional especial para 6 minutos depois
            BOT2_LOGGER.info(f"[{horario_atual}] Agendando envio da mensagem promocional especial para daqui a 6 minutos (sinal #{bot2_contador_sinais}, divisível por 3)...")
            timer_promo_especial = threading.Timer(360.0, bot2_enviar_promo_especial)  # 360 segundos = 6 minutos
            timer_promo_especial.start()

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
