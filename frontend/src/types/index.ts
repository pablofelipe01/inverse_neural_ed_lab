/**
 * InverseNeural Lab - Type Definitions
 * Tipos centralizados para el dashboard de trading cuantitativo
 */

// ===== CORE TYPES =====

// Estados del algoritmo de trading
export interface AlgorithmStatus {
  status: 'running' | 'stopped';
  profit: number;
  trades: number;
  win_rate: number;
  start_time?: string;
  last_update?: string;
}

// Entradas del sistema de logs
export interface LogEntry {
  timestamp: string;
  level: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

// Configuración de parámetros del algoritmo
export interface Config {
  selectedPairs: string[];
  selectedCrypto: string[];
  positionSize: number;
  pairsPositionSize: number; // Separate position size for pairs (5% default)
  cryptoPositionSize: number; // Separate position size for crypto (2% default)
  aggressiveness: 'conservador' | 'balanceado' | 'agresivo';
  // Credenciales IQ Option
  email: string;
  password: string;
  accountType: 'PRACTICE' | 'REAL';
}

// ===== ELESTIO API TYPES =====

// Response types for Elestio backend
export interface ElestioAPIResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// Algorithm configuration for Elestio backend
export interface AlgorithmConfig {
  selectedPairs: string[];
  selectedCrypto: string[];
  positionSize: number;
  pairsPositionSize: number;
  cryptoPositionSize: number;
  aggressiveness: string;
  email: string;
  password: string;
  accountType: string;
}

// Health check response
export interface HealthCheckResponse {
  status: 'healthy' | 'error';
  timestamp: string;
  version?: string;
  uptime?: number;
}

// ===== UNION TYPES =====

// Estados de salud del sistema
export type HealthStatus = 'healthy' | 'error' | 'checking';

// Niveles de agresividad disponibles
export type AggressivenessLevel = 'conservador' | 'balanceado' | 'agresivo';

// Pares de acciones disponibles (Stock Pairs)
export type TradingPair = 
  | 'NVDA/AMD'
  | 'TESLA/FORD' 
  | 'META/GOOGLE'
  | 'AMZN/ALIBABA'
  | 'MSFT/AAPL'
  | 'AMZN/EBAY'
  | 'NFLX/AMZN'
  | 'GOOGLE/MSFT'
  | 'INTEL/IBM';

// Crypto assets available
export type CryptoAsset = 
  | 'BTCUSD'
  | 'ETHUSD'
  | 'MATICUSD'
  | 'NEARUSD'
  | 'ATOMUSD'
  | 'DOTUSD'
  | 'ARBUSD'
  | 'LINKUSD';

// Asset groups
export type AssetGroup = 'pairs' | 'crypto';

// Niveles de severity para logs
export type LogLevel = 'info' | 'success' | 'warning' | 'error';

// Estado del toggle switch
export type AlgorithmState = 'running' | 'stopped';

// ===== CONSTANTS =====

// Stock Pairs constants
export const TRADING_PAIRS: TradingPair[] = [
  'NVDA/AMD',
  'TESLA/FORD', 
  'META/GOOGLE',
  'AMZN/ALIBABA',
  'MSFT/AAPL',
  'AMZN/EBAY',
  'NFLX/AMZN',
  'GOOGLE/MSFT',
  'INTEL/IBM'
];

// Crypto assets constants
export const CRYPTO_ASSETS: CryptoAsset[] = [
  'BTCUSD',
  'ETHUSD',
  'MATICUSD',
  'NEARUSD',
  'ATOMUSD',
  'DOTUSD',
  'ARBUSD',
  'LINKUSD'
];

// Mapeo de símbolos de Stock Pairs para display
export const TRADING_SYMBOLS: Record<TradingPair, string> = {
  'NVDA/AMD': 'NVDA/AMD',
  'TESLA/FORD': 'TSLA/F', 
  'META/GOOGLE': 'META/GOOGL',
  'AMZN/ALIBABA': 'AMZN/BABA',
  'MSFT/AAPL': 'MSFT/AAPL',
  'AMZN/EBAY': 'AMZN/EBAY',
  'NFLX/AMZN': 'NFLX/AMZN',
  'GOOGLE/MSFT': 'GOOGL/MSFT',
  'INTEL/IBM': 'INTC/IBM'
};

// Crypto symbols display mapping
export const CRYPTO_SYMBOLS: Record<CryptoAsset, string> = {
  'BTCUSD': 'BTC/USD',
  'ETHUSD': 'ETH/USD',
  'MATICUSD': 'MATIC/USD',
  'NEARUSD': 'NEAR/USD',
  'ATOMUSD': 'ATOM/USD',
  'DOTUSD': 'DOT/USD',
  'ARBUSD': 'ARB/USD',
  'LINKUSD': 'LINK/USD'
};

// Configuración por defecto
export const DEFAULT_CONFIG: Config = {
  selectedPairs: [], // Empezar sin stock pairs seleccionados
  selectedCrypto: [], // Empezar sin crypto seleccionados
  positionSize: 5,    // 5% for traditional pairs (legacy field)
  pairsPositionSize: 5, // 5% for stock pairs
  cryptoPositionSize: 2, // 2% for crypto (more conservative)
  aggressiveness: 'balanceado',
  email: '',
  password: '',
  accountType: 'PRACTICE'
};

// Estado inicial del algoritmo
export const INITIAL_STATUS: AlgorithmStatus = {
  status: 'stopped',
  profit: 0,
  trades: 0,
  win_rate: 0
};

// Configuración de API
export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  ENDPOINTS: {
    START: '/strategy/start',
    STOP: '/strategy/stop',
    STATUS: '/strategy/status',
    HEALTH: '/health',
    LOGS: '/strategy/logs',
    RESET: '/strategy/reset'
  },
  POLLING_INTERVALS: {
    STATUS: 5000,     // 5 segundos
    LOGS: 3000,       // 3 segundos para logs
    HEALTH: 30000     // 30 segundos
  }
} as const;

// Rangos de position size y sus colores
export const POSITION_SIZE_CONFIG = {
  MIN: 1,
  MAX: 15,
  COLORS: {
    CONSERVATIVE: { min: 1, max: 5, class: 'text-green-400' },
    BALANCED: { min: 6, max: 10, class: 'text-yellow-400' },
    AGGRESSIVE: { min: 11, max: 15, class: 'text-red-400' }
  }
} as const;

// Crypto-specific position size configuration
export const CRYPTO_POSITION_SIZE_CONFIG = {
  MIN: 1,
  MAX: 5, // More conservative range for crypto
  COLORS: {
    CONSERVATIVE: { min: 1, max: 2, class: 'text-purple-400' },
    BALANCED: { min: 3, max: 4, class: 'text-cyan-400' },
    AGGRESSIVE: { min: 5, max: 5, class: 'text-orange-400' }
  }
} as const;

// Asset group styling
export const ASSET_GROUP_STYLING = {
  pairs: {
    bgColor: 'bg-blue-900/20',
    borderColor: 'border-blue-500/30',
    textColor: 'text-blue-300',
    selectedColor: 'bg-blue-600 border-blue-400',
    title: 'Pares Comparativos',
    description: 'Algoritmos de comparación relativa entre activos correlacionados',
    riskLevel: '5%'
  },
  crypto: {
    bgColor: 'bg-purple-900/20',
    borderColor: 'border-purple-500/30',
    textColor: 'text-purple-300',
    selectedColor: 'bg-purple-600 border-purple-400',
    title: 'Criptomonedas',
    description: 'Activos digitales de alta volatilidad con algoritmos especializados',
    riskLevel: '2%'
  }
} as const;

// Mensajes iniciales para los logs - Solo estado del sistema
export const INITIAL_LOGS: LogEntry[] = [
  { 
    timestamp: '2025-08-06T00:00:00.000Z', 
    level: 'info', 
    message: '🚀 Sistema InverseNeural Lab listo para configuración' 
  },
  { 
    timestamp: '2025-08-06T00:00:01.000Z', 
    level: 'info', 
    message: '⚙️ Configure los parámetros y presione "Activar Algoritmo" para comenzar' 
  }
];

// ===== RE-EXPORTS =====


