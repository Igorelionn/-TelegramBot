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
    "pt": [-1003175803559]  # Canal para mensagens em português
}

# Lista de IDs dos canais para facilitar iteração
BOT2_CHAT_IDS = []
for idioma, chats in BOT2_CANAIS_CONFIG.items():
    BOT2_CHAT_IDS.extend(chats)

# Links para cada idioma
LINKS_CORRETORA = {
    "pt": "https://blendbroker.com/?ref=cmgplsb7f018cavh80l81h2cy"
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

# Horários de funcionamento dos ativos - Todos configurados para 24/7
HORARIO_24_7 = {
        "Monday": ["00:00-23:59"],
        "Tuesday": ["00:00-23:59"],
        "Wednesday": ["00:00-23:59"],
        "Thursday": ["00:00-23:59"],
        "Friday": ["00:00-23:59"],
        "Saturday": ["00:00-23:59"],
        "Sunday": ["00:00-23:59"],
}

HORARIOS_PADRAO = {
    "TRUMP_(OTC)": HORARIO_24_7,
    "XAU_USD_(OTC)": HORARIO_24_7,
    "GALA_(OTC)": HORARIO_24_7,
    "BCH_(OTC)": HORARIO_24_7,
    "GRT_(OTC)": HORARIO_24_7,
    "EUR_USD": HORARIO_24_7,
    "WLD_(OTC)": HORARIO_24_7,
    "EUR_USD_(OTC)": HORARIO_24_7,
    "EUR_GBP_(OTC)": HORARIO_24_7,
    "USD_CHF_(OTC)": HORARIO_24_7,
    "EUR_JPY_(OTC)": HORARIO_24_7,
    "NZD_USD_(OTC)": HORARIO_24_7,
    "GBP_USD_(OTC)": HORARIO_24_7,
    "AUD_CAD_(OTC)": HORARIO_24_7,
    "Meta_(OTC)": HORARIO_24_7,
    "Apple_(OTC)": HORARIO_24_7,
    "Snap_(OTC)": HORARIO_24_7,
    "SEI_(OTC)": HORARIO_24_7,
    "USD_CAD": HORARIO_24_7,
    "AUD_JPY": HORARIO_24_7,
    "GBP_CAD": HORARIO_24_7,
    "GBP_CHF": HORARIO_24_7,
    "GBP_AUD": HORARIO_24_7,
    "EUR_CAD": HORARIO_24_7,
    "CHF_JPY": HORARIO_24_7,
    "CAD_CHF": HORARIO_24_7,
    "EUR_AUD": HORARIO_24_7,
    "Amazon_(OTC)": HORARIO_24_7,
    "Tesla_(OTC)": HORARIO_24_7,
    "TRON_(OTC)": HORARIO_24_7,
    "DOGECOIN_(OTC)": HORARIO_24_7,
    "Solana_(OTC)": HORARIO_24_7,
    "EUR_GBP": HORARIO_24_7,
    "INTEL_(OTC)": HORARIO_24_7,
    "Microsoft_(OTC)": HORARIO_24_7,
    "Coca_Cola_(OTC)": HORARIO_24_7,
    "McDonald's_(OTC)": HORARIO_24_7,
    "Nike_(OTC)": HORARIO_24_7,
    "Ripple___XRP_(OTC)": HORARIO_24_7,
    "AUD_USD_(OTC)": HORARIO_24_7,
    "USD_CAD_(OTC)": HORARIO_24_7,
    "AUD_JPY_(OTC)": HORARIO_24_7,
    "GBP_CAD_(OTC)": HORARIO_24_7,
    "GBP_CHF_(OTC)": HORARIO_24_7,
    "EUR_CAD_(OTC)": HORARIO_24_7,
    "CHF_JPY_(OTC)": HORARIO_24_7,
    "CAD_CHF_(OTC)": HORARIO_24_7,
    "EUR_NZD": HORARIO_24_7,
    "Litecoin_(OTC)": HORARIO_24_7,
    "EOS_USD_(OTC)": HORARIO_24_7,
    "AUD_CHF_(OTC)": HORARIO_24_7,
    "AUD_NZD_(OTC)": HORARIO_24_7,
    "EUR_CHF_(OTC)": HORARIO_24_7,
    "GBP_NZD_(OTC)": HORARIO_24_7,
    "CAD_JPY_(OTC)": HORARIO_24_7,
    "NZD_CAD_(OTC)": HORARIO_24_7,
    "NZD_JPY_(OTC)": HORARIO_24_7,
    "ICP_(OTC)": HORARIO_24_7,
    "IMX_(OTC)": HORARIO_24_7,
    "BONK_(OTC)": HORARIO_24_7,
    "LINK_(OTC)": HORARIO_24_7,
    "WIF_(OTC)": HORARIO_24_7,
    "PEPE_(OTC)": HORARIO_24_7,
    "FLOKI_(OTC)": HORARIO_24_7,
    "DOT_(OTC)": HORARIO_24_7,
    "ATOM_(OTC)": HORARIO_24_7,
    "INJ_(OTC)": HORARIO_24_7,
    "IOTA_(OTC)": HORARIO_24_7,
    "DASH_(OTC)": HORARIO_24_7,
    "ARB_(OTC)": HORARIO_24_7,
    "ORDI_(OTC)": HORARIO_24_7,
    "SATS_(OTC)": HORARIO_24_7,
    "PYTH_(OTC)": HORARIO_24_7,
    "RONIN_(OTC)": HORARIO_24_7,
    "TIA_(OTC)": HORARIO_24_7,
    "MANA_(OTC)": HORARIO_24_7,
    "STX_(OTC)": HORARIO_24_7,
    "MATIC_(OTC)": HORARIO_24_7,
    "GBP_JPY": HORARIO_24_7,
    "EUR_JPY": HORARIO_24_7,
    "GBP_USD": HORARIO_24_7,
    "USD_JPY": HORARIO_24_7,
    "AUD_CAD": HORARIO_24_7,
    "Bitcoin": HORARIO_24_7,
    "GBP_JPY_(OTC)": HORARIO_24_7,
    "USD_JPY_(OTC)": HORARIO_24_7,
    "CAD_JPY": HORARIO_24_7,
    "AUD_USD": HORARIO_24_7,
    "Ethereum": HORARIO_24_7,
    "AUD_CHF": HORARIO_24_7,
    "AUD_NZD": HORARIO_24_7,
    "AMAZON": HORARIO_24_7,
    "APPLE": HORARIO_24_7,
    "NZD_JPY": HORARIO_24_7,
    "EUR_SGD": HORARIO_24_7,
    "CHFNOK": HORARIO_24_7,
    "Google_(OTC)": HORARIO_24_7,
    "AUD_SGD": HORARIO_24_7,
    "ETC_USD": HORARIO_24_7,
    "NZD_CAD": HORARIO_24_7,
    "NZD_USD": HORARIO_24_7,
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
            "TRUMP (OTC)",
            "XAU/USD (OTC)",
            "GALA (OTC)",
            "BCH (OTC)",
            "GRT (OTC)",
            "EUR/USD",
            "WLD (OTC)",
            "EUR/USD (OTC)",
            "EUR/GBP (OTC)",
            "USD/CHF (OTC)",
            "EUR/JPY (OTC)",
            "NZD/USD (OTC)",
            "GBP/USD (OTC)",
            "AUD/CAD (OTC)",
            "Meta (OTC)",
            "Apple (OTC)",
            "Snap (OTC)",
            "SEI (OTC)",
            "USD/CAD",
            "AUD/JPY",
            "GBP/CAD",
            "GBP/CHF",
            "GBP/AUD",
            "EUR/CAD",
            "CHF/JPY",
            "CAD/CHF",
            "EUR/AUD",
            "Amazon (OTC)",
            "Tesla (OTC)",
            "TRON (OTC)",
            "DOGECOIN (OTC)",
            "Solana (OTC)",
            "EUR/GBP",
            "INTEL (OTC)",
            "Microsoft (OTC)",
            "Coca-Cola (OTC)",
            "McDonald's (OTC)",
            "Nike (OTC)",
            "Ripple - XRP (OTC)",
            "AUD/USD (OTC)",
            "USD/CAD (OTC)",
            "AUD/JPY (OTC)",
            "GBP/CAD (OTC)",
            "GBP/CHF (OTC)",
            "EUR/CAD (OTC)",
            "CHF/JPY (OTC)",
            "CAD/CHF (OTC)",
            "EUR/NZD",
            "Litecoin (OTC)",
            "EOS/USD (OTC)",
            "AUD/CHF (OTC)",
            "AUD/NZD (OTC)",
            "EUR/CHF (OTC)",
            "GBP/NZD (OTC)",
            "CAD/JPY (OTC)",
            "NZD/CAD (OTC)",
            "NZD/JPY (OTC)",
            "ICP (OTC)",
            "IMX (OTC)",
            "BONK (OTC)",
            "LINK (OTC)",
            "WIF (OTC)",
            "PEPE (OTC)",
            "FLOKI (OTC)",
            "DOT (OTC)",
            "ATOM (OTC)",
            "INJ (OTC)",
            "IOTA (OTC)",
            "DASH (OTC)",
            "ARB (OTC)",
            "ORDI (OTC)",
            "SATS (OTC)",
            "PYTH (OTC)",
            "RONIN (OTC)",
            "TIA (OTC)",
            "MANA (OTC)",
            "STX (OTC)",
            "MATIC (OTC)",
            "GBP/JPY",
            "EUR/JPY",
            "GBP/USD",
            "USD/JPY",
            "AUD/CAD",
            "Bitcoin",
            "GBP/JPY (OTC)",
            "USD/JPY (OTC)",
            "CAD/JPY",
            "AUD/USD",
            "Ethereum",
            "AUD/CHF",
            "AUD/NZD",
            "AMAZON",
            "APPLE",
            "NZD/JPY",
            "EUR/SGD",
            "CHFNOK",
            "Google (OTC)",
            "AUD/SGD",
            "ETC/USD",
            "NZD/CAD",
            "NZD/USD"
        ]
        
        # Filtrar apenas os ativos disponíveis no momento
        ativos_disponiveis = [ativo for ativo in todos_ativos if verificar_disponibilidade_ativo(ativo)]
        
        BOT2_LOGGER.info(f"Ativos disponíveis no momento: {len(ativos_disponiveis)} de {len(todos_ativos)}")
        
        # Se não houver ativos disponíveis, usar alguns ativos como fallback
        if not ativos_disponiveis:
            BOT2_LOGGER.warning("Nenhum ativo disponível! Usando lista de fallback.")
            fallback_ativos = [
                "EUR/USD (OTC)",
                "Bitcoin",
                "Tesla (OTC)",
                "Ethereum"
            ]
            return fallback_ativos
        
        return ativos_disponiveis
        
    except Exception as e:
        BOT2_LOGGER.error(f"Erro geral ao verificar ativos disponíveis: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        # Lista reduzida em caso de erro
        return [
            "EUR/USD (OTC)",
            "Bitcoin",
            "Tesla (OTC)",
            "Ethereum"
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
        "tempo_expiracao": 1,  # 1 minuto de expiração (alterado de 5 para 1)
        "hora_criacao": obter_hora_brasilia()
    }

# Função para formatar a mensagem de sinal
def formatar_mensagem_sinal(sinal, idioma):
    """Formata a mensagem de sinal para o idioma especificado."""
    ativo = sinal["ativo"]
    direcao = sinal["direcao"]
    tempo_expiracao = sinal["tempo_expiracao"]  # Agora sempre será 1 minuto
    
    # Obter horário atual
    hora_atual = obter_hora_brasilia()
    
    # Horário do sinal (3 minutos depois do envio)
    hora_sinal = hora_atual + timedelta(minutes=3)
    
    # Horário de expiração (1 minuto depois do horário do sinal)
    hora_expiracao = hora_sinal + timedelta(minutes=tempo_expiracao)
    
    # Horários das proteções (1 e 2 minutos após expiração)
    hora_protecao1 = hora_expiracao + timedelta(minutes=1)
    hora_protecao2 = hora_protecao1 + timedelta(minutes=1)
    
    # Emoji baseado na direção
    emoji = "🟩" if direcao == "CALL" else "🟥"
    
    # Texto da direção
    action = "COMPRA" if direcao == "CALL" else "VENDA"
    
    # Formatação de horários
    hora_sinal_str = hora_sinal.strftime("%H:%M")
    hora_protecao1_str = hora_protecao1.strftime("%H:%M")
    hora_protecao2_str = hora_protecao2.strftime("%H:%M")
    
    # Obter links específicos para o idioma
    link_corretora = LINKS_CORRETORA[idioma]
    link_video = LINKS_VIDEO[idioma]
    
    # Novo formato de mensagem
    mensagem = (
        f"🧑‍💻 Dark confirmou entrada\n\n"
        f"📊 Par = {ativo}\n"
        f"⏰ Expiração = {tempo_expiracao} Minuto\n\n"
        f"💻 Entrada às {hora_sinal_str}\n"
        f"{emoji} {action}\n\n"
        f"✋🏻 Em caso de LOSS\n"
        f"Fazer 1º Proteção às {hora_protecao1_str}\n"
        f"Fazer 2º Proteção às {hora_protecao2_str}\n\n"
        f'📲 <a href="{link_corretora}">Clique para abrir a corretora</a>\n'
        f'🙋‍♂️ <a href="https://t.me/cryptodarktrade/48">Não sabe operar ainda?</a>'
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
        "🔥Cadastre-se na Blend Broker agora mesmo🔥\n\n"
        f'➡ <a href="{link_corretora}">CLICANDO AQUI</a>'
    )
        
    return mensagem

# As funções enviar_mensagem e enviar_gif foram removidas por não serem mais necessárias
# O código agora envia mensagens diretamente para o canal em português

# Função que envia o sinal para todos os canais
def enviar_sinal():
    """Envia um sinal para todos os canais configurados."""
    global contador_sinais, ultimo_sinal
    
    BOT2_LOGGER.info("Iniciando sequência de envio de sinal")
    
    # Incrementar o contador de sinais
    contador_sinais += 1
    
    # Gerar um novo sinal
    sinal = gerar_sinal()
    ultimo_sinal = sinal
    
    # Registrar informações do sinal
    BOT2_LOGGER.info(f"Sinal #{contador_sinais}: {sinal['ativo']} - {sinal['direcao']}")
    
    chat_id = BOT2_CANAIS_CONFIG["pt"][0]  # Pegar apenas o primeiro canal em português
    
    try:
        # PASSO 1: Enviar mensagem de participação IMEDIATAMENTE (10 min antes do sinal)
        BOT2_LOGGER.info("Enviando mensagem de participação (10 min antes do sinal)")
        mensagem_participacao = formatar_mensagem_participacao("pt")
        bot2.send_message(
            chat_id=chat_id,
            text=mensagem_participacao,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        BOT2_LOGGER.info("Mensagem de participação enviada com sucesso")
        
        # PASSO 2: Agendar GIF para 7 minutos depois (3 min antes do sinal)
        threading.Timer(7 * 60, lambda: enviar_gif_pre_sinal(chat_id)).start()
        BOT2_LOGGER.info("Agendado envio de GIF para daqui a 7 minutos (3 min antes do sinal)")
        
        # PASSO 3: Agendar mensagem de abertura para 8 minutos depois (2 min antes do sinal)
        threading.Timer(8 * 60, lambda: enviar_mensagem_abertura(chat_id)).start()
        BOT2_LOGGER.info("Agendado envio de mensagem de abertura para daqui a 8 minutos (2 min antes do sinal)")
        
        # PASSO 4: Agendar o sinal propriamente dito para 10 minutos depois
        threading.Timer(10 * 60, lambda: enviar_sinal_propriamente_dito(sinal, chat_id)).start()
        BOT2_LOGGER.info("Agendado envio do sinal para daqui a 10 minutos")
        
        return True
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao iniciar sequência de envio: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        return False

# Função para enviar o GIF antes do sinal
def enviar_gif_pre_sinal(chat_id):
    """Envia o GIF 3 minutos antes do sinal."""
    BOT2_LOGGER.info("Iniciando envio do GIF pré-sinal")
    
    try:
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
        
        BOT2_LOGGER.info(f"GIF pré-sinal enviado com sucesso para o canal {chat_id}")
        return True
        
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar GIF pré-sinal: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        return False

# Função para enviar a mensagem de abertura da corretora
def enviar_mensagem_abertura(chat_id):
    """Envia a mensagem de abertura da corretora 2 minutos antes do sinal."""
    BOT2_LOGGER.info("Iniciando envio da mensagem de abertura da corretora")
    
    try:
        mensagem = formatar_mensagem_abertura_corretora("pt")
        bot2.send_message(
            chat_id=chat_id,
            text=mensagem,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        BOT2_LOGGER.info(f"Mensagem de abertura enviada com sucesso para o canal {chat_id}")
        return True
        
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar mensagem de abertura: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        return False

# Função para enviar o sinal propriamente dito
def enviar_sinal_propriamente_dito(sinal, chat_id):
    """Envia o sinal propriamente dito no horário correto."""
    BOT2_LOGGER.info("Iniciando envio do sinal propriamente dito")
    
    try:
        mensagem = formatar_mensagem_sinal(sinal, "pt")
        bot2.send_message(
            chat_id=chat_id,
            text=mensagem,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        BOT2_LOGGER.info(f"Sinal enviado com sucesso para o canal {chat_id}")
        return True
        
    except Exception as e:
        BOT2_LOGGER.error(f"Erro ao enviar sinal: {str(e)}")
        BOT2_LOGGER.error(traceback.format_exc())
        return False


# Função para iniciar o bot e agendar os sinais
def iniciar_bot():
    """Inicia o bot e agenda o envio de sinais para horários específicos."""
    BOT2_LOGGER.info("Iniciando bot...")
    
    # Horários específicos para envio de sinais
    horarios_envio = ["09:00", "09:30", "13:00", "13:30", "16:00", "16:30"]
    
    # Agendar envio de sinais para cada horário específico
    for horario in horarios_envio:
        schedule.every().day.at(horario).do(enviar_sinal)
        BOT2_LOGGER.info(f"Agendado envio de sinal para {horario}")
    
    BOT2_LOGGER.info(f"Bot iniciado com sucesso. {len(horarios_envio)} horários agendados. Executando loop de agendamento...")
    
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
