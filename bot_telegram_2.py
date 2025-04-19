#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bot de Reações Automáticas para Telegram
Reage automaticamente a mensagens em canais específicos.
Suporta adição de múltiplos usuários, cada um reagindo uma vez por mensagem.
"""

import os
import sys
import time
import logging
import random
import json
import asyncio
import traceback
import re
from datetime import datetime
from telethon import TelegramClient, events, errors, functions, types
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import InputPeerChannel, InputChannel

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telethon_reacoes_logs.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
LOGGER = logging.getLogger("TelethonReacoes")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reacoes_config.json")
CONFIG = {}
CLIENTS = {} # Dicionário para armazenar os clientes Telethon ativos (session_name -> client)
LISTENER_CLIENT = None # Cliente que vai ouvir as mensagens

# Variável para armazenar cliente temporário durante o processo de autenticação
TEMP_CLIENT = None
TEMP_PHONE = None

# Mapa para controlar contas aquecidas
CONTAS_AQUECIDAS = set()

# --- Funções de Configuração ---
def carregar_config():
    global CONFIG
    try:
        LOGGER.info(f"Tentando carregar configurações de: {CONFIG_FILE}")
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                CONFIG = json.load(f)
                LOGGER.info(f"Configurações carregadas: {len(CONFIG.get('canais_monitorados', []))} canais, {len(CONFIG.get('reaction_sessions', []))} contas para reagir.")
                # Validação básica
                if not CONFIG.get('api_id') or not CONFIG.get('api_hash'):
                    LOGGER.error("api_id ou api_hash não encontrados no config.json!")
                    sys.exit(1)
                if not CONFIG.get('listener_session'):
                    LOGGER.error("listener_session não definido no config.json!")
                    sys.exit(1)
                return True
        else:
            LOGGER.error(f"Arquivo de configuração {CONFIG_FILE} não encontrado!")
            return False
    except Exception as e:
        LOGGER.error(f"Erro ao carregar/validar configurações: {str(e)}")
        LOGGER.error(traceback.format_exc())
        return False

def salvar_config():
    """Salva a configuração atual no arquivo de configuração."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, ensure_ascii=False, indent=4)
        LOGGER.info("Configuração salva com sucesso.")
        return True
    except Exception as e:
        LOGGER.error(f"Erro ao salvar configuração: {str(e)}")
        return False

# --- Gerenciamento de Usuários ---
def adicionar_usuario(session_name):
    """Adiciona um novo usuário às sessões de reação."""
    global CONFIG
    if not CONFIG.get('reaction_sessions'):
        CONFIG['reaction_sessions'] = []
    
    if session_name in CONFIG['reaction_sessions']:
        LOGGER.warning(f"Usuário {session_name} já existe na configuração.")
        return False
    
    CONFIG['reaction_sessions'].append(session_name)
    LOGGER.info(f"Usuário {session_name} adicionado com sucesso.")
    return salvar_config()

def remover_usuario(session_name):
    """Remove um usuário das sessões de reação."""
    global CONFIG
    if not CONFIG.get('reaction_sessions'):
        LOGGER.warning("Não há usuários configurados para remover.")
        return False
    
    if session_name not in CONFIG['reaction_sessions']:
        LOGGER.warning(f"Usuário {session_name} não encontrado na configuração.")
        return False
    
    CONFIG['reaction_sessions'].remove(session_name)
    LOGGER.info(f"Usuário {session_name} removido com sucesso.")
    return salvar_config()

def listar_usuarios():
    """Lista todos os usuários configurados."""
    global CONFIG
    usuarios = CONFIG.get('reaction_sessions', [])
    return usuarios

# --- Funções de Cliente Telethon ---
async def iniciar_clientes():
    global LISTENER_CLIENT, CONFIG, CLIENTS
    api_id = CONFIG['api_id']
    api_hash = CONFIG['api_hash']
    listener_session_name = CONFIG['listener_session']
    reaction_session_names = CONFIG.get('reaction_sessions', [])

    LOGGER.info("Iniciando clientes Telethon...")

    # Iniciar cliente ouvinte
    try:
        LOGGER.info(f"Iniciando cliente ouvinte: {listener_session_name}")
        client = TelegramClient(listener_session_name, api_id, api_hash)
        await client.start() # Pedirá login interativo se necessário
        if not await client.is_user_authorized():
             LOGGER.error(f"Falha ao autenticar cliente ouvinte {listener_session_name}. Verifique o login.")
             return False
        LISTENER_CLIENT = client
        CLIENTS[listener_session_name] = client
        LOGGER.info(f"Cliente ouvinte {listener_session_name} iniciado com sucesso.")
    except Exception as e:
        LOGGER.error(f"Erro ao iniciar cliente ouvinte {listener_session_name}: {e}")
        return False

    # Iniciar clientes de reação (que ainda não foram iniciados)
    for session_name in reaction_session_names:
        if session_name not in CLIENTS: # Só inicia se não for o ouvinte já iniciado
            try:
                LOGGER.info(f"Iniciando cliente de reação: {session_name}")
                client = TelegramClient(session_name, api_id, api_hash)
                await client.start() # Pedirá login interativo se necessário
                if not await client.is_user_authorized():
                    LOGGER.error(f"Falha ao autenticar cliente {session_name}. Verifique o login.")
                    # Continuar tentando iniciar outros clientes
                    continue
                CLIENTS[session_name] = client
                LOGGER.info(f"Cliente de reação {session_name} iniciado com sucesso.")
            except Exception as e:
                LOGGER.error(f"Erro ao iniciar cliente de reação {session_name}: {e}")
                # Continuar tentando iniciar outros clientes

    if not CLIENTS:
         LOGGER.error("Nenhum cliente Telethon pôde ser iniciado.")
         return False

    LOGGER.info(f"Total de clientes iniciados: {len(CLIENTS)}")
    return True

# --- Processo de Adição de Nova Conta ---
async def iniciar_processo_nova_conta():
    """Inicia o processo de adicionar uma nova conta."""
    global TEMP_CLIENT, TEMP_PHONE, CONFIG
    
    try:
        # Limpar variáveis temporárias
        TEMP_CLIENT = None
        TEMP_PHONE = None
        
        # Solicitar número de telefone
        print("\n=== Adicionar Nova Conta ===")
        numero = input("Digite o número de telefone (formato internacional, ex: +5511999999999): ").strip()
        
        if not numero or not re.match(r'^\+\d+$', numero):
            print("Número inválido. Use o formato +XXYYZZZZZZZ (ex: +5511999999999)")
            return False
        
        # Gerar nome de sessão automaticamente baseado no número (apenas dígitos)
        session_name = f"conta_{re.sub(r'[^0-9]', '', numero)}_{int(datetime.now().timestamp())}"
        print(f"Nome da sessão gerado: {session_name}")
        
        # Criar cliente temporário
        print(f"Iniciando processo de autenticação para {numero}...")
        TEMP_PHONE = numero
        TEMP_CLIENT = TelegramClient(session_name, CONFIG['api_id'], CONFIG['api_hash'])
        
        # Iniciar cliente (isso enviará o código)
        await TEMP_CLIENT.connect()
        await TEMP_CLIENT.send_code_request(numero)
        
        print(f"\nCódigo de verificação enviado para {numero}")
        print("Verifique seu aplicativo Telegram e digite o código recebido:")
        
        return True
        
    except errors.PhoneNumberInvalidError:
        print(f"Erro: Número de telefone inválido: {numero}")
        return False
    except errors.PhoneNumberBannedError:
        print(f"Erro: Este número de telefone está banido do Telegram: {numero}")
        return False
    except Exception as e:
        print(f"Erro ao iniciar processo de autenticação: {e}")
        LOGGER.error(f"Erro ao adicionar nova conta: {e}")
        LOGGER.error(traceback.format_exc())
        return False

async def verificar_codigo(codigo):
    """Verifica o código de autenticação recebido para a nova conta."""
    global TEMP_CLIENT, TEMP_PHONE, CONFIG
    
    if not TEMP_CLIENT or not TEMP_PHONE:
        print("Erro: Nenhum processo de autenticação em andamento.")
        return False
    
    try:
        # Verificar o código
        print(f"Verificando código para {TEMP_PHONE}...")
        await TEMP_CLIENT.sign_in(phone=TEMP_PHONE, code=codigo)
        
        # Verificar se a autenticação foi bem-sucedida
        if await TEMP_CLIENT.is_user_authorized():
            # Obter o nome da sessão
            session_name = TEMP_CLIENT.session.filename
            if session_name.endswith('.session'):
                session_name = os.path.basename(session_name[:-8])  # Remover extensão .session
                
            # Adicionar ao config
            if adicionar_usuario(session_name):
                print(f"\nConta adicionada com sucesso como '{session_name}'!")
                
                # Adicionar o cliente à lista de clientes ativos
                CLIENTS[session_name] = TEMP_CLIENT
                print(f"Cliente '{session_name}' iniciado e pronto para reagir.")
                
                # Inscrever automaticamente nos canais
                print("\nInscrevendo a conta nos canais configurados...")
                await inscrever_cliente_em_canais(TEMP_CLIENT, session_name)
                
                # Iniciar processo de aquecimento
                if CONFIG.get('aquecimento_automatico', True):
                    print("\nIniciando processo de aquecimento da conta...")
                    asyncio.create_task(aquecer_conta(TEMP_CLIENT, session_name))
                
                # Limpar temporários
                TEMP_CLIENT = None
                TEMP_PHONE = None
                
                return True
            else:
                print("Erro ao salvar a configuração.")
                return False
        else:
            print("Falha na autenticação. O código pode estar incorreto.")
            return False
        
    except errors.SessionPasswordNeededError:
        # Se a conta tiver autenticação de dois fatores
        print("\nEsta conta tem verificação em duas etapas.")
        password = input("Digite sua senha de 2FA: ")
        
        try:
            await TEMP_CLIENT.sign_in(password=password)
            
            # Verificar novamente
            if await TEMP_CLIENT.is_user_authorized():
                # Obter o nome da sessão
                session_name = TEMP_CLIENT.session.filename
                if session_name.endswith('.session'):
                    session_name = os.path.basename(session_name[:-8])
                    
                # Adicionar ao config
                if adicionar_usuario(session_name):
                    print(f"\nConta adicionada com sucesso como '{session_name}'!")
                    
                    # Adicionar o cliente à lista de clientes ativos
                    CLIENTS[session_name] = TEMP_CLIENT
                    print(f"Cliente '{session_name}' iniciado e pronto para reagir.")
                    
                    # Inscrever automaticamente nos canais
                    print("\nInscrevendo a conta nos canais configurados...")
                    await inscrever_cliente_em_canais(TEMP_CLIENT, session_name)
                    
                    # Iniciar processo de aquecimento
                    if CONFIG.get('aquecimento_automatico', True):
                        print("\nIniciando processo de aquecimento da conta...")
                        asyncio.create_task(aquecer_conta(TEMP_CLIENT, session_name))
                    
                    # Limpar temporários
                    TEMP_CLIENT = None
                    TEMP_PHONE = None
                    
                    return True
                else:
                    print("Erro ao salvar a configuração.")
                    return False
            else:
                print("Falha na autenticação com 2FA.")
                return False
                
        except Exception as e:
            print(f"Erro na verificação 2FA: {e}")
            return False
    
    except errors.PhoneCodeInvalidError:
        print("Código inválido. Verifique e tente novamente.")
        return False
    except errors.PhoneCodeExpiredError:
        print("Código expirado. Inicie o processo novamente.")
        TEMP_CLIENT = None
        TEMP_PHONE = None
        return False
    except Exception as e:
        print(f"Erro ao verificar código: {e}")
        LOGGER.error(f"Erro na verificação de código: {e}")
        LOGGER.error(traceback.format_exc())
        return False

async def inscrever_cliente_em_canais(client, session_name):
    """Inscreve uma conta nos canais monitorados e também em canais de 'aquecimento'."""
    canais_sucesso = 0
    canais_falha = 0
    
    # Função auxiliar para tentar entrar em um canal
    async def tentar_entrar_canal(canal):
        nonlocal canais_sucesso, canais_falha
        try:
            # Corrigir formato do canal se necessário
            canal_corrigido = canal
            # Se começar com -100, remove para funcionar com o get_entity
            if canal.startswith('-100'):
                canal_corrigido = int(canal.replace('-100', '-'))
            
            # Tentar obter entidade (canal, grupo, etc)
            try:
                entity = await client.get_entity(canal_corrigido)
            except ValueError:
                # Tentar novamente, mas com o ID sem o "-"
                if isinstance(canal_corrigido, int):
                    canal_corrigido = abs(canal_corrigido)
                    entity = await client.get_entity(canal_corrigido)
                else:
                    raise
                
            # Não verificar se já está no canal (isso requer permissões de admin)
            # Tentar entrar diretamente
            await client(functions.channels.JoinChannelRequest(channel=entity))
            print(f"  ✓ Inscrito com sucesso no canal: {canal}")
            canais_sucesso += 1
            return True
            
        except errors.FloodWaitError as e:
            print(f"  ⚠️ Limite excedido ao tentar entrar no canal {canal}. Aguarde {e.seconds} segundos.")
            LOGGER.warning(f"FloodWait ao inscrever {session_name} no canal {canal}: {e.seconds}s")
            await asyncio.sleep(min(e.seconds, 10))  # Esperar até 10 segundos aqui
            canais_falha += 1
            return False
        except errors.ChannelPrivateError:
            print(f"  ❌ Falha ao entrar no canal {canal}: Canal privado")
            canais_falha += 1
            return False
        except errors.InviteRequestSentError:
            print(f"  ⚠️ Solicitação de entrada enviada para o canal: {canal}")
            canais_sucesso += 1  # Contamos como sucesso parcial
            return True
        except errors.UserAlreadyParticipantError:
            print(f"  ✓ A conta já está no canal: {canal}")
            canais_sucesso += 1
            return True
        except errors.ChannelsTooMuchError:
            print(f"  ❌ Falha ao entrar no canal {canal}: Limite de canais atingido")
            canais_falha += 1
            return False
        except errors.UsernameInvalidError:
            print(f"  ❌ Falha ao entrar no canal {canal}: Nome de usuário inválido")
            canais_falha += 1
            return False
        except errors.UsernameNotOccupiedError:
            print(f"  ❌ Falha ao entrar no canal {canal}: Nome de usuário não existe")
            canais_falha += 1
            return False
        except Exception as e:
            print(f"  ❌ Erro ao entrar no canal {canal}: {e.__class__.__name__}: {str(e)}")
            LOGGER.error(f"Erro ao inscrever {session_name} no canal {canal}: {e}")
            canais_falha += 1
            return False
    
    print("\n=== Inscrição em Canais ===")
    # 1. Primeiro inscrever nos canais monitorados (obrigatórios)
    print("Inscrevendo nos canais monitorados:")
    canais_monitorados = CONFIG.get('canais_monitorados', [])
    for canal in canais_monitorados:
        await tentar_entrar_canal(canal)
        # Pequeno delay para evitar flood
        await asyncio.sleep(2)
    
    # 2. Depois inscrever nos canais de aquecimento (opcionais)
    print("\nInscrevendo nos canais de aquecimento:")
    canais_aquecimento = CONFIG.get('canais_aquecimento', [])
    
    # Verificar se há canais de aquecimento
    if not canais_aquecimento:
        print("  ℹ️ Nenhum canal de aquecimento configurado.")
    else:
        for canal in canais_aquecimento:
            await tentar_entrar_canal(canal)
            # Delay maior para canais de aquecimento (evitar detecção de bot)
            await asyncio.sleep(3)
    
    print(f"\nInscrição concluída: {canais_sucesso} sucesso, {canais_falha} falha")
    return canais_sucesso > 0

# --- Lógica de Reação ---
async def reagir_com_cliente(session_name, chat_id, msg_id, reacao):
    """Tenta reagir a uma mensagem usando um cliente específico."""
    if session_name not in CLIENTS:
        LOGGER.warning(f"Cliente {session_name} não encontrado ou não iniciado.")
        return False

    client = CLIENTS[session_name]
    try:
        LOGGER.info(f"Conta '{session_name}' tentando reagir com {reacao} à mensagem {msg_id} no chat {chat_id}")
        await client(SendReactionRequest(
            peer=chat_id,
            msg_id=msg_id,
            reaction=[reacao] # Precisa ser uma lista
        ))
        LOGGER.info(f"Conta '{session_name}' reagiu com {reacao} com sucesso.")
        return True
    except errors.ReactionInvalidError:
        LOGGER.warning(f"Conta '{session_name}' falhou: Reação {reacao} inválida para msg {msg_id} no chat {chat_id}.")
    except errors.MessageIdInvalidError:
         LOGGER.warning(f"Conta '{session_name}' falhou: Mensagem {msg_id} não encontrada no chat {chat_id}.")
    except errors.FloodWaitError as e:
        LOGGER.warning(f"Conta '{session_name}' recebeu FloodWait por {e.seconds} segundos. Aguardando...")
        await asyncio.sleep(e.seconds + 1)
    except errors.UserIsBlockedError:
         LOGGER.error(f"Conta '{session_name}' está bloqueada e não pode reagir.")
    except Exception as e:
        LOGGER.error(f"Erro inesperado ao reagir com conta '{session_name}': {e}")
        LOGGER.error(traceback.format_exc())
    return False

# --- Handler de Novas Mensagens ---
async def registrar_handler_mensagens():
    """Registra os handlers de eventos após a configuração ser carregada"""
    global LISTENER_CLIENT, CONFIG, CONTAS_AQUECIDAS
    
    @events.register(events.NewMessage(chats=CONFIG.get('canais_monitorados', [])))
    async def handler_nova_mensagem(event):
        """Lida com novas mensagens recebidas nos canais monitorados."""
        message = event.message
        chat_id = event.chat_id
        msg_id = message.id
        try:
            # Obter título do chat se possível
            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', f"ID {chat_id}")
        except Exception:
            chat_title = f"ID {chat_id}"

        # Verificar o tipo de conteúdo
        conteudo = "texto"
        if message.photo:
            conteudo = "foto"
        elif message.video:
            conteudo = "vídeo"
        elif message.gif:
            conteudo = "gif"
        elif message.sticker:
            conteudo = "sticker"
        elif message.document:
            conteudo = "documento"
        elif message.voice:
            conteudo = "áudio"
        elif message.poll:
            conteudo = "enquete"

        LOGGER.info(f"Nova mensagem ({conteudo}) recebida no canal '{chat_title}' ({chat_id}): ID {msg_id}")

        # Verificar se o bot está ativo
        if not CONFIG.get('ativo', True):
            LOGGER.info("Bot está desativado. Ignorando mensagem.")
            return

        reacoes_disponiveis = CONFIG.get('reacoes_disponiveis', [])
        if not reacoes_disponiveis:
            LOGGER.warning("Nenhuma reação configurada em reacoes_disponiveis.")
            return

        reaction_sessions = CONFIG.get('reaction_sessions', [])
        if not reaction_sessions:
            LOGGER.warning("Nenhuma conta configurada em reaction_sessions para reagir.")
            return

        delay_entre_reacoes = CONFIG.get('delay_entre_reacoes_seg', 1)
        modo_aleatorio = CONFIG.get('modo_aleatorio', True)
        
        # CORREÇÃO: Cada usuário pode reagir apenas UMA vez por mensagem
        # Vamos mapear cada usuário para uma reação específica
        
        # Lista de contas ativas (já autenticadas) e aquecidas (se necessário)
        contas_ativas = [
            s for s in reaction_sessions 
            if s in CLIENTS and (not CONFIG.get('aquecimento_automatico', True) or s in CONTAS_AQUECIDAS)
        ]
        
        if not contas_ativas:
            LOGGER.warning("Nenhuma conta ativa e aquecida para reagir.")
            return
            
        LOGGER.info(f"Preparando para reagir com {len(contas_ativas)} contas ativas.")
        
        # Shuffle apenas se o modo aleatório estiver ativado
        if modo_aleatorio:
            random.shuffle(contas_ativas)
            random.shuffle(reacoes_disponiveis)
        
        # Criar um mapeamento entre contas e reações
        # Se houver mais contas que reações, algumas contas usarão as mesmas reações
        # Se houver mais reações que contas, algumas reações não serão usadas
        mapeamento_reacoes = {}
        for i, conta in enumerate(contas_ativas):
            # Garantir que não ficamos sem reações disponíveis
            indice_reacao = i % len(reacoes_disponiveis)
            mapeamento_reacoes[conta] = reacoes_disponiveis[indice_reacao]
        
        # Agora reagir com cada conta
        tarefas = []
        for session_name, reacao in mapeamento_reacoes.items():
            # Usar asyncio.sleep para adicionar um delay aleatório e evitar detecção de automação
            delay_aleatorio = random.uniform(delay_entre_reacoes, delay_entre_reacoes * 3) if modo_aleatorio else delay_entre_reacoes
            
            # Criar uma tarefa para reagir após o delay
            tarefa = asyncio.create_task(
                reagir_apos_delay(session_name, chat_id, msg_id, reacao, delay_aleatorio)
            )
            tarefas.append(tarefa)
        
        # Não precisamos esperar as tarefas terminarem para continuar o handler
    
    async def reagir_apos_delay(session_name, chat_id, msg_id, reacao, delay):
        """Função auxiliar para reagir após um delay específico."""
        await asyncio.sleep(delay)
        return await reagir_com_cliente(session_name, chat_id, msg_id, reacao)
        
    # Adicionar o handler ao cliente ouvinte
    LISTENER_CLIENT.add_event_handler(handler_nova_mensagem)
    LOGGER.info("Handler de mensagens registrado.")

# --- Interface de Linha de Comando ---
async def cli_interativo():
    """Interface de linha de comando para gerenciar o bot durante a execução."""
    global TEMP_CLIENT, TEMP_PHONE
    
    print("\n=== Bot de Reações Automáticas ===")
    print("Digite 'ajuda' para ver os comandos disponíveis.")
    
    # Estado para controle do fluxo de adição de conta
    esperando_codigo = False
    
    while True:
        try:
            if esperando_codigo:
                comando = input("\nDigite o código recebido (ou 'cancelar'): ").strip()
                
                if comando.lower() == "cancelar":
                    print("Operação de adição de conta cancelada.")
                    TEMP_CLIENT = None
                    TEMP_PHONE = None
                    esperando_codigo = False
                    continue
                
                # Assumir que é um código e tentar validar
                sucesso = await verificar_codigo(comando)
                esperando_codigo = not sucesso  # Se falhar, continua esperando
                continue
            
            comando = input("\nComando > ").strip().lower()
            
            if comando == "sair" or comando == "exit":
                print("Encerrando o bot...")
                break
                
            elif comando == "ajuda" or comando == "help":
                print("\nComandos disponíveis:")
                print("  novaconta         - Adiciona uma nova conta (solicitará telefone e código)")
                print("  remover [sessão]   - Remove um usuário existente")
                print("  listar             - Lista todos os usuários configurados")
                print("  status             - Mostra o status atual do bot")
                print("  ativar             - Ativa o bot")
                print("  desativar          - Desativa o bot")
                print("  canais             - Lista os canais monitorados e de aquecimento")
                print("  adicionarcanal [tipo] [canal] - Adiciona um canal (tipo: monitorado/aquecimento)")
                print("  removercanal [tipo] [canal] - Remove um canal (tipo: monitorado/aquecimento)")
                print("  inscrever [sessão] - Inscreve uma conta em todos os canais configurados")
                print("  aquecer [sessão]   - Aquece uma conta reagindo a mensagens existentes")
                print("  aquecimento [on/off] - Ativa/desativa o aquecimento automático")
                print("  contas_aquecidas   - Lista as contas já aquecidas")
                print("  reset_aquecimento  - Reseta o status de aquecimento de todas as contas")
                print("  sair/exit          - Encerra o bot")
                
            elif comando == "novaconta":
                sucesso = await iniciar_processo_nova_conta()
                esperando_codigo = sucesso  # Se o processo iniciou com sucesso, espera pelo código
                
            elif comando.startswith("remover "):
                sessao = comando.split(" ", 1)[1].strip()
                if remover_usuario(sessao):
                    print(f"Usuário '{sessao}' removido com sucesso.")
                    # Encerrar o cliente se estiver ativo
                    if sessao in CLIENTS:
                        asyncio.create_task(encerrar_cliente(sessao))
                    # Remover da lista de contas aquecidas
                    if sessao in CONTAS_AQUECIDAS:
                        CONTAS_AQUECIDAS.remove(sessao)
                else:
                    print(f"Falha ao remover usuário '{sessao}'.")
                    
            elif comando == "listar":
                usuarios = listar_usuarios()
                if usuarios:
                    print("\nUsuários configurados:")
                    for i, usuario in enumerate(usuarios, 1):
                        status = "Ativo" if usuario in CLIENTS else "Inativo"
                        aquecido = "Aquecido" if usuario in CONTAS_AQUECIDAS else "Não aquecido"
                        print(f"  {i}. {usuario} - {status}, {aquecido}")
                    print(f"\nTotal: {len(usuarios)} usuários")
                else:
                    print("Nenhum usuário configurado.")
                    
            elif comando == "status":
                usuarios_ativos = sum(1 for usuario in listar_usuarios() if usuario in CLIENTS)
                usuarios_aquecidos = sum(1 for usuario in listar_usuarios() if usuario in CONTAS_AQUECIDAS)
                total_usuarios = len(listar_usuarios())
                
                print("\nStatus do Bot:")
                print(f"  Usuários: {usuarios_ativos}/{total_usuarios} ativos")
                print(f"  Usuários aquecidos: {usuarios_aquecidos}/{total_usuarios}")
                print(f"  Canais monitorados: {len(CONFIG.get('canais_monitorados', []))}")
                print(f"  Canais de aquecimento: {len(CONFIG.get('canais_aquecimento', []))}")
                print(f"  Reações disponíveis: {', '.join(CONFIG.get('reacoes_disponiveis', []))}")
                print(f"  Reações por mensagem: {usuarios_aquecidos} (1 por usuário aquecido)")
                print(f"  Delay entre reações: {CONFIG.get('delay_entre_reacoes_seg', 1)} segundos")
                print(f"  Modo aleatório: {'Ativado' if CONFIG.get('modo_aleatorio', True) else 'Desativado'}")
                print(f"  Aquecimento automático: {'Ativado' if CONFIG.get('aquecimento_automatico', True) else 'Desativado'}")
                print(f"  Posts para aquecimento: {CONFIG.get('posts_para_aquecer', 20)}")
                print(f"  Bot ativo: {'Sim' if CONFIG.get('ativo', True) else 'Não'}")
            
            elif comando == "ativar":
                CONFIG['ativo'] = True
                if salvar_config():
                    print("Bot ativado com sucesso.")
                else:
                    print("Falha ao ativar o bot.")
                    
            elif comando == "desativar":
                CONFIG['ativo'] = False
                if salvar_config():
                    print("Bot desativado com sucesso.")
                else:
                    print("Falha ao desativar o bot.")
            
            elif comando.startswith("aquecer "):
                sessao = comando.split(" ", 1)[1].strip()
                if sessao not in CLIENTS:
                    print(f"Erro: Cliente '{sessao}' não está ativo.")
                    continue
                
                print(f"Iniciando processo de aquecimento para '{sessao}'...")
                resultado = await aquecer_conta(CLIENTS[sessao], sessao)
                if resultado:
                    print(f"Aquecimento de '{sessao}' concluído com sucesso!")
                else:
                    print(f"Falha no aquecimento de '{sessao}'.")
            
            elif comando.startswith("aquecimento "):
                status = comando.split(" ", 1)[1].strip().lower()
                if status in ["on", "1", "sim", "true", "ativar"]:
                    CONFIG['aquecimento_automatico'] = True
                    if salvar_config():
                        print("Aquecimento automático ativado.")
                    else:
                        print("Falha ao ativar aquecimento automático.")
                elif status in ["off", "0", "nao", "não", "false", "desativar"]:
                    CONFIG['aquecimento_automatico'] = False
                    if salvar_config():
                        print("Aquecimento automático desativado.")
                    else:
                        print("Falha ao desativar aquecimento automático.")
                else:
                    print("Valor inválido. Use 'on' ou 'off'.")
            
            elif comando == "contas_aquecidas":
                if CONTAS_AQUECIDAS:
                    print("\nContas aquecidas:")
                    for i, conta in enumerate(CONTAS_AQUECIDAS, 1):
                        ativa = "Ativa" if conta in CLIENTS else "Inativa"
                        print(f"  {i}. {conta} - {ativa}")
                    print(f"\nTotal: {len(CONTAS_AQUECIDAS)} contas aquecidas")
                else:
                    print("Nenhuma conta foi aquecida ainda.")
            
            elif comando == "reset_aquecimento":
                CONTAS_AQUECIDAS.clear()
                print("Status de aquecimento resetado para todas as contas.")
            
            elif comando == "canais":
                print("\n=== Canais Configurados ===")
                
                # Listar canais monitorados
                canais_monitorados = CONFIG.get('canais_monitorados', [])
                print(f"\nCanais Monitorados ({len(canais_monitorados)}):")
                for i, canal in enumerate(canais_monitorados, 1):
                    print(f"  {i}. {canal}")
                
                # Listar canais de aquecimento
                canais_aquecimento = CONFIG.get('canais_aquecimento', [])
                print(f"\nCanais de Aquecimento ({len(canais_aquecimento)}):")
                for i, canal in enumerate(canais_aquecimento, 1):
                    print(f"  {i}. {canal}")
            
            elif comando.startswith("adicionarcanal "):
                partes = comando.split()
                if len(partes) < 3:
                    print("Comando inválido. Use: adicionarcanal [tipo] [canal]")
                    print("Exemplo: adicionarcanal aquecimento @noticias")
                    continue
                
                tipo = partes[1].lower()
                canal = partes[2]
                
                if tipo not in ['monitorado', 'aquecimento']:
                    print("Tipo inválido. Use 'monitorado' ou 'aquecimento'.")
                    continue
                
                # Verificar se o canal já existe na lista
                lista_canais = 'canais_monitorados' if tipo == 'monitorado' else 'canais_aquecimento'
                if not CONFIG.get(lista_canais):
                    CONFIG[lista_canais] = []
                
                if canal in CONFIG[lista_canais]:
                    print(f"Canal {canal} já existe na lista de {tipo}.")
                    continue
                
                # Adicionar canal
                CONFIG[lista_canais].append(canal)
                if salvar_config():
                    print(f"Canal {canal} adicionado à lista de {tipo} com sucesso.")
                else:
                    print(f"Falha ao adicionar canal {canal}.")
            
            elif comando.startswith("removercanal "):
                partes = comando.split()
                if len(partes) < 3:
                    print("Comando inválido. Use: removercanal [tipo] [canal]")
                    print("Exemplo: removercanal aquecimento @noticias")
                    continue
                
                tipo = partes[1].lower()
                canal = partes[2]
                
                if tipo not in ['monitorado', 'aquecimento']:
                    print("Tipo inválido. Use 'monitorado' ou 'aquecimento'.")
                    continue
                
                # Verificar se o canal existe na lista
                lista_canais = 'canais_monitorados' if tipo == 'monitorado' else 'canais_aquecimento'
                if not CONFIG.get(lista_canais) or canal not in CONFIG[lista_canais]:
                    print(f"Canal {canal} não encontrado na lista de {tipo}.")
                    continue
                
                # Remover canal
                CONFIG[lista_canais].remove(canal)
                if salvar_config():
                    print(f"Canal {canal} removido da lista de {tipo} com sucesso.")
                else:
                    print(f"Falha ao remover canal {canal}.")
            
            elif comando.startswith("inscrever "):
                sessao = comando.split(" ", 1)[1].strip()
                if sessao not in CLIENTS:
                    print(f"Erro: Cliente '{sessao}' não está ativo.")
                    continue
                
                print(f"Inscrevendo a conta '{sessao}' em todos os canais configurados...")
                cliente = CLIENTS[sessao]
                await inscrever_cliente_em_canais(cliente, sessao)
                
            else:
                print("Comando desconhecido. Digite 'ajuda' para ver os comandos disponíveis.")
                
        except KeyboardInterrupt:
            print("\nOperação cancelada pelo usuário.")
        except Exception as e:
            print(f"Erro ao processar comando: {e}")
            LOGGER.error(f"Erro no CLI: {e}")
            LOGGER.error(traceback.format_exc())

async def encerrar_cliente(session_name):
    """Encerra um cliente Telethon específico."""
    global CLIENTS
    
    if session_name not in CLIENTS:
        LOGGER.warning(f"Cliente '{session_name}' não está ativo.")
        return True
        
    try:
        LOGGER.info(f"Encerrando cliente: {session_name}")
        await CLIENTS[session_name].disconnect()
        del CLIENTS[session_name]
        LOGGER.info(f"Cliente '{session_name}' encerrado com sucesso.")
        return True
        
    except Exception as e:
        LOGGER.error(f"Erro ao encerrar cliente '{session_name}': {e}")
        return False

# --- Funções de Aquecimento de Contas ---
async def aquecer_conta(client, session_name):
    """Aquece uma conta reagindo a mensagens existentes em canais de aquecimento."""
    global CONTAS_AQUECIDAS
    
    if session_name in CONTAS_AQUECIDAS:
        LOGGER.info(f"Conta '{session_name}' já está aquecida. Pulando processo de aquecimento.")
        return True
    
    print(f"\n=== Aquecendo Conta '{session_name}' ===")
    LOGGER.info(f"Iniciando processo de aquecimento para '{session_name}'")
    
    # Obter canais de aquecimento
    canais_aquecimento = CONFIG.get('canais_aquecimento', [])
    if not canais_aquecimento:
        print("Nenhum canal de aquecimento configurado. Pulando processo.")
        return False
    
    # Número de posts para reagir (para aquecer)
    posts_para_aquecer = CONFIG.get('posts_para_aquecer', 20)
    reacoes_disponiveis = CONFIG.get('reacoes_disponiveis', ["👍"])
    reacoes_realizadas = 0
    max_reacoes = posts_para_aquecer
    
    # Selecionar canais aleatórios (até 10)
    canais_selecionados = random.sample(
        canais_aquecimento, 
        min(10, len(canais_aquecimento))
    )
    
    print(f"Selecionando {len(canais_selecionados)} canais para aquecimento.")
    LOGGER.info(f"Selecionados {len(canais_selecionados)} canais para aquecimento de '{session_name}'")
    
    for canal in canais_selecionados:
        if reacoes_realizadas >= max_reacoes:
            break
            
        print(f"\nAquecendo em: {canal}")
        try:
            # Tentar obter entidade do canal
            try:
                entity = await client.get_entity(canal)
            except ValueError:
                print(f"  ⚠️ Canal '{canal}' não encontrado, pulando...")
                continue
                
            # Buscar mensagens recentes
            mensagens = []
            try:
                mensagens = await client.get_messages(entity, limit=15)
                print(f"  ✓ Encontradas {len(mensagens)} mensagens recentes")
            except Exception as e:
                print(f"  ⚠️ Erro ao obter mensagens de '{canal}': {e}")
                continue
                
            # Se não encontrou mensagens, pular
            if not mensagens:
                print(f"  ⚠️ Nenhuma mensagem encontrada em '{canal}'")
                continue
                
            # Reagir a algumas mensagens aleatórias (até 5 por canal)
            mensagens_para_reagir = random.sample(
                mensagens, 
                min(5, len(mensagens))
            )
            
            for msg in mensagens_para_reagir:
                # Se alcançou o limite de reações, sair
                if reacoes_realizadas >= max_reacoes:
                    break
                    
                # Escolher uma reação aleatória
                reacao = random.choice(reacoes_disponiveis)
                
                # Tentar reagir
                try:
                    await client(SendReactionRequest(
                        peer=entity,
                        msg_id=msg.id,
                        reaction=[reacao]
                    ))
                    print(f"  ✓ Reagiu com {reacao} à mensagem {msg.id}")
                    reacoes_realizadas += 1
                    
                    # Adicionar um delay aleatório entre reações (2-7 segundos)
                    await asyncio.sleep(random.uniform(2, 7))
                    
                except errors.FloodWaitError as e:
                    print(f"  ⚠️ Limite de reações excedido. Aguardando {e.seconds} segundos.")
                    LOGGER.warning(f"FloodWait ao aquecer '{session_name}': {e.seconds}s")
                    await asyncio.sleep(min(e.seconds, 60))  # Esperar até 60 segundos
                    continue
                except Exception as e:
                    print(f"  ⚠️ Erro ao reagir: {e}")
                    continue
            
            # Delay antes de ir para o próximo canal (5-15 segundos)
            await asyncio.sleep(random.uniform(5, 15))
                
        except Exception as e:
            print(f"  ⚠️ Erro ao aquecer em '{canal}': {e}")
            LOGGER.error(f"Erro ao aquecer '{session_name}' no canal '{canal}': {e}")
            continue
    
    print(f"\nAquecimento concluído: {reacoes_realizadas}/{max_reacoes} reações realizadas")
    
    # Marcar a conta como aquecida se tiver feito pelo menos 50% das reações planejadas
    if reacoes_realizadas >= max_reacoes / 2:
        CONTAS_AQUECIDAS.add(session_name)
        LOGGER.info(f"Conta '{session_name}' aquecida com sucesso ({reacoes_realizadas} reações)")
        return True
    else:
        LOGGER.warning(f"Aquecimento de '{session_name}' incompleto ({reacoes_realizadas}/{max_reacoes})")
        return False

# --- Verificações para contas prontas ---
async def verificar_e_aquecer_contas():
    """Verifica e aquece todas as contas que ainda não foram aquecidas."""
    global CLIENTS, CONTAS_AQUECIDAS
    
    # Se o aquecimento automático estiver desativado, não fazer nada
    if not CONFIG.get('aquecimento_automatico', True):
        return
    
    contas_para_aquecer = [
        session_name for session_name in CLIENTS.keys()
        if session_name != CONFIG.get('listener_session') and session_name not in CONTAS_AQUECIDAS
    ]
    
    if not contas_para_aquecer:
        return  # Nenhuma conta para aquecer
    
    LOGGER.info(f"Verificando {len(contas_para_aquecer)} contas para aquecimento")
    
    for session_name in contas_para_aquecer:
        client = CLIENTS[session_name]
        await aquecer_conta(client, session_name)
        # Adicionar delay entre aquecimento de contas para evitar sobrecarga
        await asyncio.sleep(30)  # 30 segundos entre cada conta

# --- Função Principal ---
async def main():
    if not carregar_config():
        LOGGER.error("Falha ao carregar configuração. Encerrando.")
        return

    if not await iniciar_clientes():
        LOGGER.error("Falha ao iniciar clientes. Encerrando.")
        return

    if LISTENER_CLIENT is None:
        LOGGER.error("Cliente ouvinte não iniciado. Encerrando.")
        return

    # Verificar e aquecer contas se necessário
    if CONFIG.get('aquecimento_automatico', True):
        LOGGER.info("Verificando contas para aquecimento...")
        asyncio.create_task(verificar_e_aquecer_contas())

    # Registrar handlers
    await registrar_handler_mensagens()

    LOGGER.info("Clientes iniciados. Monitorando canais...")
    
    # Iniciar interface CLI em uma task separada
    cli_task = asyncio.create_task(cli_interativo())
    
    # Manter o script rodando
    try:
        await LISTENER_CLIENT.run_until_disconnected()
    finally:
        # Garantir que a task CLI seja cancelada
        cli_task.cancel()

if __name__ == "__main__":
    try:
        # Usar asyncio.run() para iniciar a função assíncrona main
        asyncio.run(main())
    except KeyboardInterrupt:
        LOGGER.info("Recebido sinal de interrupção. Encerrando...")
    except Exception as e:
        LOGGER.error(f"Erro fatal: {e}")
        LOGGER.error(traceback.format_exc())
    finally:
        LOGGER.info("Script encerrado.") 
