# -*- coding: utf-8 -*-
"""
Sistema de envio de sinais automatizados para a xxbroker.
Desenvolvido por IteamHost 2023
"""

# Importações
import os
import sys
import time
import json
import random
import copy
import uuid
import logging
import traceback
import threading
import requests
from datetime import datetime, timedelta
from functools import lru_cache
import schedule
import re
import urllib.request
import pytz  # Adicionar importação do pytz para manipulação de fusos horários

# Definir constantes globais
BOT_VERSION = "2.0.1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BOT2_CANAIS_CONFIG = {"pt": [], "en": [], "es": []}
ATIVOS_CATEGORIAS = {"Digital": [], "Digital_Disponiveis": []}

# Variáveis globais de controle
bot2_contador_sinais = 0
ultimo_sinal_enviado = None
bot2_sinais_agendados = False
thread_sequencia_ativa = None
sequencia_multiplo_tres_lock = threading.Lock()

# Variável para controlar execução do teste apenas uma vez
TESTE_JA_EXECUTADO = False

# Definir token do Telegram - SUBSTITUA PELO SEU TOKEN
BOT2_TOKEN = "5834194999:AAFEz3NbvMC1-l89x5ue3I0eoO-B_E2CHVI" # Token do Bot 2

# Configurar logging personalizado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'bot_sinais.log'), encoding='utf-8')
    ]
)

# Criar o logger específico para o Bot 2
BOT2_LOGGER = logging.getLogger("Bot2")

# Configurações dos idiomas (fusos horários)
CONFIGS_IDIOMA = {
    "pt": {"fuso_horario": "America/Sao_Paulo", "nome": "Português"},
    "en": {"fuso_horario": "America/New_York", "nome": "English"},
    "es": {"fuso_horario": "Europe/Madrid", "nome": "Español"}
}

# Funções de utilidade
def bot2_obter_hora_brasilia():
    """
    Obtém a hora atual no fuso horário de Brasília (America/Sao_Paulo).
    
    Returns:
        datetime: Objeto datetime com a hora atual no fuso de Brasília
    """
    fuso_brasilia = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso_brasilia)

def verificar_url_gif(url):
    """
    Verifica se a URL do GIF é válida e acessível.
    
    Args:
        url: URL do GIF a ser verificada
        
    Returns:
        bool: True se a URL for válida e acessível, False caso contrário
    """
    try:
        # Configurar um timeout curto para evitar esperas longas
        requisicao = urllib.request.Request(url, method="HEAD")
        resposta = urllib.request.urlopen(requisicao, timeout=5)
        
        # Verificar se o código de status é 200 (OK)
        return resposta.getcode() == 200
    except Exception as e:
        BOT2_LOGGER.warning(f"Erro ao verificar URL do GIF: {str(e)}")
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
    
    # Adicionando proteção contra envios duplicados durante o teste
    # Se esta variável não existir ainda, criamos ela
    if not hasattr(bot2_enviar_gif_promo, 'gif_enviado_por_idioma'):
        bot2_enviar_gif_promo.gif_enviado_por_idioma = {
            'pt': False,
            'en': False,
            'es': False
        }
    
    # Se o teste inicial estiver sendo executado (TESTE_JA_EXECUTADO = False)
    # e o GIF já foi enviado para este idioma, não enviar novamente
    if not TESTE_JA_EXECUTADO and bot2_enviar_gif_promo.gif_enviado_por_idioma.get(idioma, False):
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.warning(f"[GIF-PROMO][{horario_atual}] ⚠️ GIF JÁ ENVIADO para idioma {idioma} durante o teste inicial. Ignorando chamada duplicada.")
        return True  # Retornar sucesso para não interromper o fluxo
    
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
            
            # Se ainda estamos no teste inicial, marcar este idioma como já enviado
            if not TESTE_JA_EXECUTADO:
                bot2_enviar_gif_promo.gif_enviado_por_idioma[idioma] = True
                BOT2_LOGGER.info(f"[GIF-PROMO][{horario_atual}] 🔒 Marcando GIF para idioma {idioma} como já enviado durante o teste")
        else:
            BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] ❌ Falha em todos os envios de GIF promocional para idioma {idioma}")
        
        return envio_bem_sucedido
    
    except Exception as e:
        agora = bot2_obter_hora_brasilia()
        horario_atual = agora.strftime("%H:%M:%S")
        BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] ❌ Erro crítico ao enviar GIF promocional: {str(e)}")
        BOT2_LOGGER.error(f"[GIF-PROMO][{horario_atual}] 🔍 Detalhes: {traceback.format_exc()}")
        return False
