import { ArrowDownRight, ArrowUpRight, Target, Shield, TrendingUp, BarChart2, Clock, Percent, RefreshCw, Check, X, LineChart, BarChart, TrendingDown, Activity, AlertTriangle, ChevronUp, ChevronDown, BarChart4, BookOpen, ChevronRight, Loader2, ChevronsUp, Tag } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchTradingSignals, fetchCorrelationData, fetchOnChainMetrics, fetchOrderBookData, tradingSignalService } from "@/services";
import { getLatestPrices } from "@/services/getSimulatedPrices";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { useNavigate } from "react-router-dom";
import { SignalType, SignalStrength } from "@/services/types";
import type { TradingSignal as ServiceTradingSignal } from "@/services/types";
import type { TradingSignal } from "@/types/tradingSignals";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { useEffect, useState, useCallback, useRef } from "react";
import { notificationService } from "@/services/notificationService";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { useLanguage } from "@/contexts/LanguageContext";
import { TimeZoneSelector } from "@/components/dashboard/TimeZoneSelector";
import { useTimeZone } from "@/contexts/TimeZoneContext";
import { motion, AnimatePresence } from "framer-motion";

// Tempo de expiração em minutos para todos os sinais
const SIGNAL_EXPIRY_TIME = 5; 

// Tempo entre o horário de Reentrada 2 e o próximo sinal
const TIME_BETWEEN_SIGNALS = 10;

// Tempo de espera antes de processar automaticamente um sinal (10 minutos em ms)
const AUTO_COMPLETE_TIMEOUT = 10 * 60 * 1000;

// Modo de teste para processamento rápido (30 segundos)
const TEST_MODE = true;
const TEST_TIMEOUT = 30 * 1000;

// Obter o tempo de expiração dependendo do modo
const getExpirationTimeout = () => {
  return TEST_MODE ? TEST_TIMEOUT : AUTO_COMPLETE_TIMEOUT;
};

// Variável para controlar a contagem de sinais processados (para gerar 1 perda a cada 10 ganhos)
let signalProcessCount = 0;

// Função auxiliar para encontrar o próximo horário válido
const findNextValidEntryTime = (currentTime: string, existingTimes: string[]): string => {
  const [hoursStr, minutesStr] = currentTime.split(':');
  let hours = parseInt(hoursStr);
  let minutes = parseInt(minutesStr);
  
  // Tentar horários até encontrar um válido
  for (let attempt = 0; attempt < 24; attempt++) {
    // Avançar 10 minutos, mantendo o último dígito em 3 ou 7
    minutes += 10;
    if (minutes >= 60) {
      hours = (hours + 1) % 24;
      minutes = minutes % 60;
    }
    
    // Ajustar último dígito para 3 ou 7
    const lastDigit = minutes % 10;
    if (lastDigit !== 3 && lastDigit !== 7) {
      minutes = Math.floor(minutes / 10) * 10 + (Math.random() < 0.5 ? 3 : 7);
    }
    
    // Formatar o novo horário
    const newTime = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    
    // Verificar se o novo horário tem pelo menos 10 minutos de diferença de todos os existentes
    let isValid = true;
    for (const existingTime of existingTimes) {
      if (getTimeDifferenceInMinutes(existingTime, newTime) < 10) {
        isValid = false;
        break;
      }
    }
    
    if (isValid) {
      return newTime;
    }
  }
  
  // Fallback: retornar tempo original se não encontrar um válido após várias tentativas
  return currentTime;
};

// Função para calcular a diferença em minutos entre dois horários no formato "HH:MM"
const getTimeDifferenceInMinutes = (time1: string, time2: string): number => {
  const [hours1, minutes1] = time1.split(':').map(Number);
  const [hours2, minutes2] = time2.split(':').map(Number);
  
  const totalMinutes1 = hours1 * 60 + minutes1;
  const totalMinutes2 = hours2 * 60 + minutes2;
  
  return Math.abs(totalMinutes1 - totalMinutes2);
};

// Função para calcular o próximo horário baseado nas regras definidas
const calculateNextTime = (baseTime: string, addMinutes: number): string => {
  const [hoursStr, minutesStr] = baseTime.split(':');
  let hours = parseInt(hoursStr);
  let minutes = parseInt(minutesStr) + addMinutes;
  
  // Ajustar para o próximo dia se necessário
  if (minutes >= 60) {
    hours = (hours + Math.floor(minutes / 60)) % 24;
    minutes = minutes % 60;
  }
  
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
};

// Tempo de cache em milissegundos (10 minutos)
const CACHE_DURATION = 10 * 60 * 1000;

// Chave para armazenar sinais no localStorage
const SIGNALS_CACHE_KEY = 'trending_signals_cache';

// Chave para armazenar todos os sinais do dia no localStorage
const DAILY_SIGNALS_CACHE_KEY = 'trending_daily_signals_cache';

// Cache global para evitar regeneração de sinais entre trocas de aba
let globalSignalsCache = null;

// Cache global para sinais do dia todo
let globalDailySignalsCache = null;

// Função auxiliar para obter o slot de tempo atual (a cada 10 min)
const getInitialTimeSlot = (): string => {
  const now = new Date();
  const hours = now.getHours();
  const minutes = now.getMinutes();
  const minuteSlot = Math.floor(minutes / 10);
  return `${hours.toString().padStart(2, '0')}:${minuteSlot}`;
};

// Verificar se temos sinais do dia no localStorage
const checkDailySignalsCache = () => {
  // Verificar primeiro o cache global
  if (globalDailySignalsCache && globalDailySignalsCache.timestamp) {
    const now = Date.now();
    // Verificar se o cache ainda é do mesmo dia
    const cacheDate = new Date(globalDailySignalsCache.timestamp);
    const currentDate = new Date();
    
    if (cacheDate.toDateString() === currentDate.toDateString()) {
      console.log('Usando sinais do dia do cache global');
      return globalDailySignalsCache;
    }
  }

  try {
    const cachedData = localStorage.getItem(DAILY_SIGNALS_CACHE_KEY);
    if (cachedData) {
      const parsedData = JSON.parse(cachedData);
      const now = Date.now();
      
      // Verificar se o cache é do dia atual
      const cacheDate = new Date(parsedData.timestamp);
      const currentDate = new Date();
      
      if (cacheDate.toDateString() === currentDate.toDateString()) {
        console.log('Usando sinais do dia do localStorage');
        // Atualizar o cache global
        globalDailySignalsCache = {
          valid: true,
          data: parsedData.data,
          timestamp: parsedData.timestamp,
          timeSlots: parsedData.timeSlots
        };
        return globalDailySignalsCache;
      }
    }
  } catch (error) {
    console.error('Erro ao verificar sinais do dia no localStorage:', error);
  }
  return { valid: false, data: null, timestamp: 0, timeSlots: [] };
};

// Verificar se temos sinais armazenados no localStorage
const checkLocalStorageSignals = () => {
  // Verificar primeiro o cache global
  if (globalSignalsCache && globalSignalsCache.timestamp) {
    const now = Date.now();
    if ((now - globalSignalsCache.timestamp) <= CACHE_DURATION) {
      console.log('Usando sinais do cache global - evitando regeneração em troca de aba');
      return globalSignalsCache;
    }
  }

  try {
    const cachedData = localStorage.getItem(SIGNALS_CACHE_KEY);
    if (cachedData) {
      const parsedData = JSON.parse(cachedData);
      const now = Date.now();
      
      // Garantir que usamos os sinais do slot atual, mesmo que tenham sido
      // gerados anteriormente na mesma sessão de navegação
      const currentTimeSlot = getInitialTimeSlot();
      if (parsedData.timeSlot === currentTimeSlot) {
        console.log(`Usando sinais do localStorage para o slot ${currentTimeSlot}`);
        // Atualizar o cache global
        globalSignalsCache = {
          valid: true,
          data: parsedData.data,
          timestamp: parsedData.timestamp,
          timeSlot: parsedData.timeSlot
        };
        return globalSignalsCache;
      }
    }
  } catch (error) {
    console.error('Erro ao verificar sinais no localStorage:', error);
  }
  return { valid: false, data: null, timestamp: 0, timeSlot: '' };
};

// Salvar cache no localStorage e no cache global
const saveSignalsToLocalStorage = (signals, timestamp, timeSlot) => {
  try {
    const dataToSave = {
      data: signals,
      timestamp,
      timeSlot
    };
    
    localStorage.setItem(SIGNALS_CACHE_KEY, JSON.stringify(dataToSave));
    
    // Atualizar o cache global
    globalSignalsCache = {
      valid: true,
      data: signals,
      timestamp,
      timeSlot
    };
    
    console.log('Sinais salvos no localStorage e cache global');
  } catch (error) {
    console.error('Erro ao salvar sinais no localStorage:', error);
  }
};

// Salvar cache dos sinais diários no localStorage e no cache global
const saveDailySignalsToLocalStorage = (signals, timeSlots) => {
  try {
    const dataToSave = {
      data: signals,
      timestamp: Date.now(),
      timeSlots
    };
    
    localStorage.setItem(DAILY_SIGNALS_CACHE_KEY, JSON.stringify(dataToSave));
    
    // Atualizar o cache global
    globalDailySignalsCache = {
      valid: true,
      data: signals,
      timestamp: dataToSave.timestamp,
      timeSlots
    };
    
    console.log('Sinais do dia salvos no localStorage e cache global');
  } catch (error) {
    console.error('Erro ao salvar sinais do dia no localStorage:', error);
  }
};

const isAssetAlreadyUsedInGroup = (signalGroup: EnrichedSignal[], asset: string): boolean => {
  return signalGroup.some(signal => signal.symbol === asset);
};

// Função para gerar a sequência de sinais para o dia todo, começando à meia-noite
const generateDailySignals = async () => {
  console.log('Gerando sinais para o dia todo...');
  const dailySignals = [];
  const timeSlots = [];
  
  // Definir a hora inicial como meia-noite (00:03)
  let currentEntryTime = "00:03";
  
  // Gerar sinais para o dia todo
  while (true) {
    // Calcular os horários para este sinal
    const entryTime = currentEntryTime;
    const expiryTime = calculateNextTime(entryTime, SIGNAL_EXPIRY_TIME);
    const gale1Time = expiryTime; // Reentrada 1 é igual ao horário de expiração
    const gale2Time = calculateNextTime(gale1Time, SIGNAL_EXPIRY_TIME); // Reentrada 2 é Reentrada 1 + tempo de expiração
    
    // Adicionar este sinal ao conjunto
    const signal = createSignalObject({
      entry_time: entryTime,
      expiry_time_str: expiryTime,
      gale1_time: gale1Time,
      gale2_time: gale2Time
    });
    
    dailySignals.push(signal);
    timeSlots.push(entryTime);
    
    // Definir o horário de entrada do próximo sinal (10 minutos após a Reentrada 2)
    currentEntryTime = calculateNextTime(gale2Time, TIME_BETWEEN_SIGNALS);
    
    // Verificar se já passamos da meia-noite do próximo dia
    const [hours] = currentEntryTime.split(':').map(Number);
    if (hours === 0 && dailySignals.length > 1) {
      // Já chegamos ao próximo dia, então paramos
      break;
    }
  }
  
  console.log(`Gerados ${dailySignals.length} sinais para o dia`);
  
  // Salvar os sinais gerados
  saveDailySignalsToLocalStorage(dailySignals, timeSlots);
  
  return {
    signals: dailySignals,
    timeSlots
  };
};

// Função para criar um objeto de sinal com os horários especificados
const createSignalObject = ({ entry_time, expiry_time_str, gale1_time, gale2_time }) => {
  // Lista de ativos disponíveis
  const availableAssets = ["BTCUSD", "ETHUSD", "XRPUSD", "ADAUSD", "SOLUSD", "AVAXUSD", "MATICUSD", "LINKUSD", "DOTUSD", "DOGEUSD"];
  
  // Selecionar um ativo aleatório
  const assetIndex = Math.floor(Math.random() * availableAssets.length);
  const symbol = availableAssets[assetIndex];
  
  // Determinar aleatoriamente se é compra ou venda com tipo explícito
  const signalType: 'BUY' | 'SELL' = Math.random() > 0.5 ? 'BUY' : 'SELL';
  
  // Determinar a força do sinal com tipo correto
  const strengthValue: SignalStrength = Math.random() > 0.7 
    ? SignalStrength.STRONG 
    : (Math.random() > 0.4 ? SignalStrength.MODERATE : SignalStrength.WEAK);
  
  // Gerar os demais dados do sinal
  return {
    id: `signal_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    symbol,
    type: SignalType.TECHNICAL,
    signal: signalType,
    reason: "Análise técnica baseada em padrões de preço e volume",
    strength: strengthValue,
    timestamp: new Date().toISOString(),
    price: signalType === 'BUY' ? 100 + Math.random() * 10 : 100 - Math.random() * 10,
    entry_price: 100,
    stop_loss: signalType === 'BUY' ? 95 : 105,
    target_price: signalType === 'BUY' ? 110 : 90,
    success_rate: 70 + Math.random() * 20,
    timeframe: "5m",
    expiry: `${SIGNAL_EXPIRY_TIME}m`,
    risk_reward: "1:2",
    status: 'active' as const,
    qualityScore: 70 + Math.random() * 30,
    entry_time,
    expiry_time_str,
    gale1_time,
    gale2_time,
    exchange: "Binance",
    categoria: "Tendência",
    entryTimestamp: 0, // Será definido quando o sinal estiver ativo
    processed: false
  };
};

// Nossa interface EnrichedSignal personalizada
interface EnrichedSignal {
  id: string;
  symbol: string;
  type: SignalType;
  signal: 'BUY' | 'SELL';
  reason: string;
  strength: SignalStrength;
  timestamp: string;
  price: number;
  entry_price: number;
  stop_loss: number;
  target_price: number;
  success_rate: number;
  timeframe: string;
  expiry: string;
  risk_reward: string;
  status: 'active' | 'completed' | 'cancelled';
  qualityScore: number;
  entry_time?: string;
  expiry_time_str?: string;
  gale1_time?: string;
  gale2_time?: string;
  exchange?: string;
  categoria?: string;
  newsAnalysis?: any;
  correlationAnalysis?: any;
  onChainMetrics?: any;
  orderBookAnalysis?: any;
  entryTimestamp?: number; // Timestamp para cálculo de tempo decorrido
  processed?: boolean; // Indica se o sinal já foi processado (ganho/perda)
  result?: 'success' | 'failure'; // Resultado do sinal após processamento
  isAnimating?: boolean; // Indica se o sinal está em animação
  [key: string]: any; // Permite campos adicionais
}

// Obter os sinais atuais com base no horário atual
const getCurrentTimeSlotSignals = (signalsArray: any[], timeSlots: string[]) => {
  // Obter o horário atual
  const now = new Date();
  const currentTimeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
  
  // Encontrar o slot de tempo mais próximo que já passou
  let closestPastTimeSlot = null;
  let closestFutureTimeSlot = null;
  
  for (const timeSlot of timeSlots) {
    // Verificar se este horário já passou
    if (isTimeEarlierOrEqual(timeSlot, currentTimeStr)) {
      // Se ainda não temos um slot mais próximo ou este é mais recente
      if (!closestPastTimeSlot || isTimeEarlierOrEqual(closestPastTimeSlot, timeSlot)) {
        closestPastTimeSlot = timeSlot;
      }
    } else {
      // Este é um slot futuro
      if (!closestFutureTimeSlot || isTimeEarlierOrEqual(timeSlot, closestFutureTimeSlot)) {
        closestFutureTimeSlot = timeSlot;
      }
    }
  }
  
  // Se não encontramos um slot passado, usar o último do dia anterior
  if (!closestPastTimeSlot && timeSlots.length > 0) {
    closestPastTimeSlot = timeSlots[timeSlots.length - 1];
  }
  
  console.log(`Horário atual: ${currentTimeStr}, Slot mais próximo: ${closestPastTimeSlot}`);
  
  // Retornar os sinais para este slot de tempo
  if (closestPastTimeSlot) {
    // Começar a partir do sinal encontrado e pegar os 3 próximos
    const startIndex = timeSlots.indexOf(closestPastTimeSlot);
    let signalsToShow = [];
    
    // Obter o primeiro sinal do slot mais próximo
    if (startIndex >= 0 && startIndex < signalsArray.length) {
      signalsToShow.push(signalsArray[startIndex]);
    }
    
    // Obter os próximos dois sinais, considerando a rotação ao final da lista
    for (let i = 1; i <= 2; i++) {
      const nextIndex = (startIndex + i) % signalsArray.length;
      if (nextIndex >= 0 && nextIndex < signalsArray.length) {
        signalsToShow.push(signalsArray[nextIndex]);
      }
    }
    
    // Adicionar mais sinais se não tivermos 3 ainda
    while (signalsToShow.length < 3 && signalsArray.length > 0) {
      signalsToShow.push({...signalsArray[0]});
    }
    
    return signalsToShow.slice(0, 3);
  }
  
  // Fallback: criar 3 sinais genéricos se não encontrarmos nada
  return [
    createSignalObject({
      entry_time: currentTimeStr,
      expiry_time_str: calculateNextTime(currentTimeStr, SIGNAL_EXPIRY_TIME),
      gale1_time: calculateNextTime(currentTimeStr, SIGNAL_EXPIRY_TIME),
      gale2_time: calculateNextTime(currentTimeStr, SIGNAL_EXPIRY_TIME * 2)
    }),
    createSignalObject({
      entry_time: calculateNextTime(currentTimeStr, 10),
      expiry_time_str: calculateNextTime(calculateNextTime(currentTimeStr, 10), SIGNAL_EXPIRY_TIME),
      gale1_time: calculateNextTime(calculateNextTime(currentTimeStr, 10), SIGNAL_EXPIRY_TIME),
      gale2_time: calculateNextTime(calculateNextTime(currentTimeStr, 10), SIGNAL_EXPIRY_TIME * 2)
    }),
    createSignalObject({
      entry_time: calculateNextTime(currentTimeStr, 20),
      expiry_time_str: calculateNextTime(calculateNextTime(currentTimeStr, 20), SIGNAL_EXPIRY_TIME),
      gale1_time: calculateNextTime(calculateNextTime(currentTimeStr, 20), SIGNAL_EXPIRY_TIME),
      gale2_time: calculateNextTime(calculateNextTime(currentTimeStr, 20), SIGNAL_EXPIRY_TIME * 2)
    })
  ];
};

// Função para verificar se um horário é anterior ou igual a outro
const isTimeEarlierOrEqual = (time1, time2) => {
  const [hours1, minutes1] = time1.split(':').map(Number);
  const [hours2, minutes2] = time2.split(':').map(Number);
  
  if (hours1 < hours2) return true;
  if (hours1 > hours2) return false;
  return minutes1 <= minutes2;
};

const SignalsCard = () => {
  const { t, language } = useLanguage();
  const { timeZone } = useTimeZone();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  // Estado para os sinais atuais na interface
  const [signals, setSignals] = useState<EnrichedSignal[]>([]);
  
  // Estado para os sinais do dia inteiro
  const [dailySignals, setDailySignals] = useState<EnrichedSignal[]>([]);
  
  // Estado para os slots de tempo do dia
  const [timeSlots, setTimeSlots] = useState<string[]>([]);
  
  // Estado para controlar a animação dos sinais
  const [animatingSignalIndex, setAnimatingSignalIndex] = useState<number | null>(null);
  
  // Referência para o contador de tempo
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  
  // Método para inicializar os sinais
  useEffect(() => {
    // Verificar se já temos sinais gerados para o dia
    const cachedDailySignals = checkDailySignalsCache();
    
    if (cachedDailySignals.valid && cachedDailySignals.data) {
      console.log('Usando sinais do dia do cache');
      setDailySignals(cachedDailySignals.data);
      setTimeSlots(cachedDailySignals.timeSlots);
      
      // Obter os sinais atuais com base no horário
      const currentSignals = getCurrentTimeSlotSignals(cachedDailySignals.data, cachedDailySignals.timeSlots);
      setSignals(currentSignals);
    } else {
      console.log('Gerando novos sinais para o dia');
      // Gerar novos sinais para o dia todo
      generateDailySignals().then(({ signals: generatedSignals, timeSlots: generatedTimeSlots }) => {
        setDailySignals(generatedSignals);
        setTimeSlots(generatedTimeSlots);
        
        // Obter os sinais atuais com base no horário
        const currentSignals = getCurrentTimeSlotSignals(generatedSignals, generatedTimeSlots);
        setSignals(currentSignals);
      });
    }
    
    // Iniciar a verificação periódica dos sinais
    const intervalId = setInterval(() => {
      checkSignalProgression();
    }, 1000);
    
    return () => clearInterval(intervalId);
  }, []);
  
  // Método para verificar a progressão dos sinais
  const checkSignalProgression = () => {
    const now = new Date();
    const currentTimeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    
    // Verificar se algum sinal completou sua Reentrada 2
    const updatedSignals = [...signals];
    let needsUpdate = false;
    
    for (let i = 0; i < updatedSignals.length; i++) {
      const signal = updatedSignals[i];
      
      // Verificar se este sinal já completou a Reentrada 2 e passou 1 minuto
      if (!signal.processed && signal.gale2_time) {
        const gale2Time = signal.gale2_time;
        const animationTime = calculateNextTime(gale2Time, 1); // 1 minuto após Reentrada 2
        const completionTime = calculateNextTime(animationTime, 5); // 5 minutos após o início da animação
        
        // Verificar se é hora de iniciar a animação
        if (isCurrentTimeAfter(currentTimeStr, animationTime) && !signal.isAnimating) {
          console.log(`Iniciando animação para o sinal ${i}`);
          updatedSignals[i] = {
            ...signal,
            isAnimating: true
          };
          setAnimatingSignalIndex(i);
          needsUpdate = true;
        }
        
        // Verificar se a animação terminou e é hora de processar o resultado
        if (signal.isAnimating && isCurrentTimeAfter(currentTimeStr, completionTime) && !signal.processed) {
          console.log(`Processando resultado para o sinal ${i}`);
          
          // Determinar se é ganho ou perda (9 ganhos para 1 perda)
          signalProcessCount++;
          const isSuccess = signalProcessCount % 11 !== 0; // 10 ganhos para 1 perda
          
          updatedSignals[i] = {
            ...signal,
            processed: true,
            result: isSuccess ? 'success' : 'failure'
          };
          needsUpdate = true;
          
          // Após processar o resultado, agendar a rotação dos sinais
          setTimeout(() => {
            rotateSignals();
          }, 3000); // Esperar 3 segundos antes de rotacionar
        }
      }
    }
    
    if (needsUpdate) {
      setSignals(updatedSignals);
    }
  };
  
  // Função para verificar se o horário atual é posterior a um horário específico
  const isCurrentTimeAfter = (currentTime, targetTime) => {
    // Extrair horas, minutos e segundos dos horários
    const [currentHours, currentMinutes, currentSeconds] = currentTime.split(':').map(Number);
    const [targetHours, targetMinutes] = targetTime.split(':').map(Number);
    
    // Converter para segundos totais para comparação
    const currentTotalSeconds = currentHours * 3600 + currentMinutes * 60 + (currentSeconds || 0);
    const targetTotalSeconds = targetHours * 3600 + targetMinutes * 60;
    
    return currentTotalSeconds > targetTotalSeconds;
  };
  
  // Método para rotacionar os sinais após um resultado
  const rotateSignals = () => {
    // Remover o primeiro sinal e mover os outros para cima
    const newSignals = [...signals.slice(1)];
    
    // Encontrar o próximo sinal a ser adicionado
    if (dailySignals.length > 0 && timeSlots.length > 0) {
      // Encontrar o horário de entrada do último sinal visível
      const lastSignal = newSignals[newSignals.length - 1];
      const nextEntryTime = calculateNextTime(lastSignal.gale2_time, TIME_BETWEEN_SIGNALS);
      
      // Encontrar um sinal que tenha esse horário de entrada no conjunto de sinais diários
      const nextSignalIndex = dailySignals.findIndex(s => s.entry_time === nextEntryTime);
      
      if (nextSignalIndex >= 0) {
        // Usar o sinal encontrado
        newSignals.push({...dailySignals[nextSignalIndex]});
      } else {
        // Criar um novo sinal com o horário calculado
        newSignals.push(createSignalObject({
          entry_time: nextEntryTime,
          expiry_time_str: calculateNextTime(nextEntryTime, SIGNAL_EXPIRY_TIME),
          gale1_time: calculateNextTime(nextEntryTime, SIGNAL_EXPIRY_TIME),
          gale2_time: calculateNextTime(nextEntryTime, SIGNAL_EXPIRY_TIME * 2)
        }));
      }
    }
    
    // Resetar animação
    setAnimatingSignalIndex(null);
    
    // Atualizar sinais
    setSignals(newSignals);
  };
  
  // No componente de renderização, adicionar uma classe especial para sinais em animação
  const getSignalCardClass = (signal: EnrichedSignal, index: number) => {
    let className = "bg-card rounded-lg p-4 transition-all duration-300 relative overflow-hidden";
    
    if (signal.processed && signal.result) {
      className += signal.result === 'success' 
        ? " signal-completed-win" 
        : " signal-completed-loss";
    } else if (index === animatingSignalIndex) {
      className += " animate-pulse border border-primary/50";
    } else {
      className += " border border-border/40 hover:border-border/70";
    }
    
    return className;
  };
  
  // Renderização do sinal com animação
  const renderSignalResult = (signal: EnrichedSignal) => {
    if (!signal.processed || !signal.result) return null;
    
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 z-10">
        <div className={`result-icon ${signal.result === 'success' ? 'win-icon' : 'loss-icon'}`}>
          {signal.result === 'success' ? (
            <Check className="h-8 w-8 text-green-500" />
          ) : (
            <X className="h-8 w-8 text-red-500" />
          )}
        </div>
        <div className="result-text">
          {signal.result === 'success' ? (
            <span className="text-green-500">WIN</span>
          ) : (
            <span className="text-red-500">LOSS</span>
          )}
        </div>
      </div>
    );
  };
  
  // Ir para a página de sinais quando clicar em "Ver mais"
  const handleSeeMore = () => {
    navigate('/signals');
  };
  
  // Renderizar temporizador para o sinal
  const renderTimer = (signal: EnrichedSignal) => {
    if (signal.processed) return null;
    
    const now = new Date();
    const currentHour = now.getHours();
    const currentMinute = now.getMinutes();
    const currentTimeStr = `${currentHour.toString().padStart(2, '0')}:${currentMinute.toString().padStart(2, '0')}`;
    
    let timerLabel = "";
    let targetTime = "";
    
    // Definir o texto e o horário alvo com base no estado atual do sinal
    if (signal.entry_time && isTimeEarlierOrEqual(currentTimeStr, signal.entry_time)) {
      timerLabel = t("Entrada em");
      targetTime = signal.entry_time;
    } else if (signal.expiry_time_str && isTimeEarlierOrEqual(currentTimeStr, signal.expiry_time_str)) {
      timerLabel = t("Expiração em");
      targetTime = signal.expiry_time_str;
    } else if (signal.gale1_time && isTimeEarlierOrEqual(currentTimeStr, signal.gale1_time)) {
      timerLabel = t("Reentrada 1 em");
      targetTime = signal.gale1_time;
    } else if (signal.gale2_time && isTimeEarlierOrEqual(currentTimeStr, signal.gale2_time)) {
      timerLabel = t("Reentrada 2 em");
      targetTime = signal.gale2_time;
    } else {
      timerLabel = t("Processando");
      return (
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <RefreshCw className="w-3 h-3 animate-spin" />
          <span>{timerLabel}...</span>
        </div>
      );
    }
    
    // Calcular a diferença de tempo
    const [targetHour, targetMinute] = targetTime.split(":").map(Number);
    const targetDate = new Date();
    targetDate.setHours(targetHour, targetMinute, 0, 0);
    
    const timeDiffMs = targetDate.getTime() - now.getTime();
    
    // Se já passou o horário, não mostrar o timer
    if (timeDiffMs <= 0) return null;
    
    // Converter para minutos e segundos
    const minutes = Math.floor(timeDiffMs / 60000);
    const seconds = Math.floor((timeDiffMs % 60000) / 1000);
    
    return (
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <Clock className="w-3 h-3" />
        <span>{timerLabel}: {minutes}m {seconds}s</span>
      </div>
    );
  };
  
  // Renderizar o componente completo
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle>
            {t("Sinais de Trading")}
          </CardTitle>
          <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={handleSeeMore}>
            {t("Ver mais")}
            <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pb-4">
        <div className="space-y-3">
          {signals.length > 0 ? (
            signals.map((signal, index) => (
              <div key={signal.id} className={getSignalCardClass(signal, index)}>
                {renderSignalResult(signal)}
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-1">
                      <span className="font-semibold">{signal.symbol}</span>
                      <Badge variant={signal.signal === 'BUY' ? 'secondary' : 'destructive'} className="ml-2">
                        {signal.signal === 'BUY' ? t('COMPRA') : t('VENDA')}
                      </Badge>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t("Entrada")}: <span className="font-medium">{signal.entry_time}</span>
                    </div>
                    <div className="flex flex-col mt-1 gap-0.5">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        <span>{t("Expiração")}: {signal.expiry_time_str} ({signal.timeframe})</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        <span>{t("Reentrada 1")}: {signal.gale1_time}</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        <span>{t("Reentrada 2")}: {signal.gale2_time}</span>
                      </div>
                      {renderTimer(signal)}
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <div className="flex items-center gap-1">
                      {signal.signal === 'BUY' ? (
                        <ArrowUpRight className="h-4 w-4 text-green-500" />
                      ) : (
                        <ArrowDownRight className="h-4 w-4 text-red-500" />
                      )}
                      <span className={signal.signal === 'BUY' ? "text-green-500" : "text-red-500"}>
                        {signal.signal === 'BUY' ? '+' : '-'}{Math.floor(Math.random() * 2) + 1}.{Math.floor(Math.random() * 100).toString().padStart(2, '0')}%
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground text-right">
                      {t("Taxa de sucesso")}: {signal.success_rate.toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-4 text-center">
              <Loader2 className="w-8 h-8 mx-auto animate-spin text-primary/50" />
              <p className="mt-2 text-sm text-muted-foreground">{t("Carregando sinais...")}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default SignalsCard;
