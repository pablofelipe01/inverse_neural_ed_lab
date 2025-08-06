# config.py
# Configuración de la estrategia RSI para IQ Option - Multi-Activos con niveles dinámicos

# Credenciales IQ Option (Placeholders - Configurar desde el dashboard)
IQ_EMAIL = "tu_email@example.com"  # Placeholder - Ingresa desde el dashboard
IQ_PASSWORD = "tu_password_aqui"   # Placeholder - Ingresa desde el dashboard  
ACCOUNT_TYPE = "PRACTICE"          # "PRACTICE" o "REAL"


# CONTROL DE TRADES SIMULTÁNEOS
MAX_SIMULTANEOUS_TRADES = 1  # Máximo número de trades abiertos al mismo tiempo (1 o 2 recomendado)

# DEFINICIÓN DE GRUPOS DE ACTIVOS
FOREX_ASSETS = []


INDEX_ASSETS = []
STOCK_ASSETS = []
COMMODITY_ASSETS = []

# Criptomonedas - Activos de alta volatilidad con niveles ajustados
CRYPTO_ASSETS = [
    "BTCUSD",     # Bitcoin - Rey de las crypto
    "ETHUSD",     # Ethereum - Smart contracts
    "MATICUSD",   # Polygon - Layer 2 
    "NEARUSD",    # NEAR Protocol - Web3
    "ATOMUSD",    # Cosmos - Interoperability
    "DOTUSD",     # Polkadot - Parachains
    "ARBUSD",     # Arbitrum - L2 scaling
    "LINKUSD"     # Chainlink - Oracles
]

PAIR_ASSETS = [
    # Pares existentes
    "NVDA/AMD",      # Tech momentum
    "TESLA/FORD",    # EV revolution   # Europe divergence     # Metals ratio
    "META/GOOGLE",   # Ad tech battle
    "AMZN/ALIBABA",  # East vs West commerce
    "MSFT/AAPL",     # Tech leadership
    "AMZN/EBAY",     # E-commerce giants
    "NFLX/AMZN",     # Streaming vs Commerce
    "GOOGLE/MSFT",   # Search vs Software
    "INTEL/IBM",     # Chip legacy battle
]
    

# Lista consolidada de activos para trading (INCLUYE CRYPTO)
TRADING_ASSETS = FOREX_ASSETS + INDEX_ASSETS + STOCK_ASSETS + COMMODITY_ASSETS + PAIR_ASSETS + CRYPTO_ASSETS

# NIVELES  PERSONALIZADOS POR GRUPO
RSI_LEVELS = {
    "FOREX": {
        "OVERSOLD": 35,
        "OVERBOUGHT": 65,
        "DESCRIPTION": "Niveles estándar para pares de divisas"
    },
    "INDEX": {
        "OVERSOLD": 35,
        "OVERBOUGHT": 65,
        "DESCRIPTION": "Niveles estándar para índices bursátiles"
    },
    "STOCK": {
        "OVERSOLD": 30,
        "OVERBOUGHT": 70,
        "DESCRIPTION": "Niveles más extremos para acciones individuales"
    },
    "COMMODITY": {
        "OVERSOLD": 33,
        "OVERBOUGHT": 67,
        "DESCRIPTION": "Niveles ajustados para oro y plata"
    },
    "CRYPTO": {
        "OVERSOLD": 35,
        "OVERBOUGHT": 65,
        "DESCRIPTION": "Niveles ajustados para alta volatilidad crypto"
    },
    "PAIR": {
        "OVERSOLD": 32,
        "OVERBOUGHT": 68,
        "DESCRIPTION": "Niveles ajustados para pares comparativos"
    },
    "DEFAULT": {
        "OVERSOLD": 35,
        "OVERBOUGHT": 65,
        "DESCRIPTION": "Niveles por defecto para activos no categorizados"
    }
}

# MOMENTUM MÍNIMO REQUERIDO POR GRUPO (en puntos de RSI)
MIN_MOMENTUM_POINTS_BY_GROUP = {
    "FOREX": 5,        # Para pares de divisas
    "INDEX": 5,        # Reducido de 8
    "STOCK": 7,        # Reducido de 10
    "COMMODITY": 5,    # Reducido de 7
    "CRYPTO": 5,       # Reducido para crypto activo
    "PAIR": 4,         # Reducido de 6 (más estable)
    "DEFAULT": 5       # Reducido de 8
}

# FUNCIÓN HELPER PARA DETERMINAR EL GRUPO DE UN ACTIVO
def get_asset_group(asset):
    """
    Determinar a qué grupo pertenece un activo
    
    Args:
        asset (str): Nombre del activo
        
    Returns:
        str: Grupo al que pertenece el activo
    """
    if asset in FOREX_ASSETS:
        return "FOREX"
    elif asset in INDEX_ASSETS:
        return "INDEX"
    elif asset in STOCK_ASSETS:
        return "STOCK"
    elif asset in COMMODITY_ASSETS:
        return "COMMODITY"
    elif asset in CRYPTO_ASSETS:
        return "CRYPTO"
    elif asset in PAIR_ASSETS:
        return "PAIR"
    else:
        return "DEFAULT"

# FUNCIÓN PARA OBTENER NIVELES RSI DE UN ACTIVO
def get_rsi_levels_for_asset(asset):
    """
    Obtener los niveles de RSI específicos para un activo
    
    Args:
        asset (str): Nombre del activo
        
    Returns:
        tuple: (oversold_level, overbought_level)
    """
    group = get_asset_group(asset)
    return (
        RSI_LEVELS[group]["OVERSOLD"],
        RSI_LEVELS[group]["OVERBOUGHT"]
    )

# FUNCIÓN PARA OBTENER MOMENTUM MÍNIMO DE UN ACTIVO
def get_min_momentum_for_asset(asset):
    """
    Obtener el momentum mínimo requerido para un activo
    
    Args:
        asset (str): Nombre del activo
        
    Returns:
        int: Puntos mínimos de momentum requeridos
    """
    group = get_asset_group(asset)
    return MIN_MOMENTUM_POINTS_BY_GROUP[group]

# Mapeo ACTUALIZADO - Con nombres correctos
ASSET_IQ_MAPPING = {
    # Índices
    "US500": "SP500",     # S&P se llama SP500 en IQ Option
}

# Configuración RSI general (usado como fallback)
RSI_PERIOD = 14
OVERSOLD_LEVEL = 35    # Nivel por defecto (se sobrescribe por grupo)
OVERBOUGHT_LEVEL = 65  # Nivel por defecto (se sobrescribe por grupo)

# CONFIGURACIÓN DE AGRESIVIDAD DE LA ESTRATEGIA
AGGRESSIVENESS_MODE = "BALANCED"  # "CONSERVATIVE", "BALANCED", "AGGRESSIVE"

AGGRESSIVENESS_CONFIG = {
    "CONSERVATIVE": {
        "candle_timeframe": 900,      # 15 minutos
        "expiry_minutes": 5,          # 5 minutos de expiración
        "min_strength": 60,           # Señal fuerte requerida
        "allow_rebounds": False,      # No permitir rebotes
        "max_rebounds": 0,            # Cero rebotes
        "rebound_tolerance": 0,       # Sin tolerancia
        "max_candles_for_cross": 1,   # Solo cruces en la vela actual
        "description": "Pocas señales, alta calidad"
    },
    "BALANCED": {
        "candle_timeframe": 300,      # 5 minutos
        "expiry_minutes": 1,          # 1 minutos de expiración
        "min_strength": 60,           # Señal moderada
        "allow_rebounds": True,       # Permitir rebotes menores
        "max_rebounds": 1,            # Máximo 1 rebote
        "rebound_tolerance": 2,       # Rebote hasta 2 puntos RSI
        "max_candles_for_cross": 2,   # Cruces en últimas 2 velas
        "description": "Balance entre cantidad y calidad"
    },
    "AGGRESSIVE": {
        "candle_timeframe": 300,      # 5 minutos
        "expiry_minutes": 5,          # 5 minutos de expiración
        "min_strength": 50,           # Señal más débil aceptada
        "allow_rebounds": True,       # Permitir rebotes
        "max_rebounds": 2,            # Hasta 2 rebotes
        "rebound_tolerance": 3,       # Rebote hasta 3 puntos RSI
        "max_candles_for_cross": 3,   # Cruces en últimas 3 velas
        "description": "Más señales, menor filtro"
    }
}

# Obtener configuración activa
ACTIVE_CONFIG = AGGRESSIVENESS_CONFIG[AGGRESSIVENESS_MODE]

# FUNCIÓN PARA OBTENER CONFIGURACIÓN DINÁMICA POR MODO
def get_aggressiveness_config(mode=None):
    """
    Obtener la configuración de agresividad para un modo específico
    
    Args:
        mode (str): Modo de agresividad ("CONSERVATIVE", "BALANCED", "AGGRESSIVE")
                   Si es None, usa el modo por defecto
        
    Returns:
        dict: Configuración de agresividad
    """
    if mode is None:
        return ACTIVE_CONFIG
    
    return AGGRESSIVENESS_CONFIG.get(mode, AGGRESSIVENESS_CONFIG["BALANCED"])

# FUNCIÓN PARA OBTENER VALORES DE CONFIGURACIÓN ESPECÍFICOS
def get_expiry_minutes(mode=None):
    """Obtener minutos de expiración para un modo específico"""
    config = get_aggressiveness_config(mode)
    return config["expiry_minutes"]

def get_candle_timeframe(mode=None):
    """Obtener timeframe de velas para un modo específico"""
    config = get_aggressiveness_config(mode)
    return config["candle_timeframe"]

def get_min_strength(mode=None):
    """Obtener fuerza mínima de señal para un modo específico"""
    config = get_aggressiveness_config(mode)
    return config["min_strength"]

# Configuración de opciones binarias (desde modo activo)
EXPIRY_MINUTES = ACTIVE_CONFIG["expiry_minutes"]
CANDLE_TIMEFRAME = ACTIVE_CONFIG["candle_timeframe"]

# Configuración específica por grupo (opcional - para futuras optimizaciones)
EXPIRY_MINUTES_BY_GROUP = {
    "FOREX": ACTIVE_CONFIG["expiry_minutes"],
    "INDEX": ACTIVE_CONFIG["expiry_minutes"],
    "STOCK": ACTIVE_CONFIG["expiry_minutes"],
    "COMMODITY": ACTIVE_CONFIG["expiry_minutes"],
    "CRYPTO": max(2, ACTIVE_CONFIG["expiry_minutes"] - 1),  # Mínimo 2 minutos para crypto
    "PAIR": ACTIVE_CONFIG["expiry_minutes"],
    "DEFAULT": ACTIVE_CONFIG["expiry_minutes"]
}

# Gestión de riesgo - Stop Loss
ABSOLUTE_STOP_LOSS_PERCENT = 0.75  # 75% de pérdida del capital inicial
MONTHLY_STOP_LOSS_PERCENT = 0.40   # 40% de pérdida mensual

# Tamaño de posición - TODOS AL 5%
POSITION_SIZE_PERCENT = 0.05  # < 5% del capital disponible
MIN_POSITION_SIZE = 1     # Mínimo $1 USD (ajustar según el mínimo de IQ Option segun moneda de tu país)

# Tamaño de posición por grupo - TODOS AL 1%
POSITION_SIZE_PERCENT_BY_GROUP = {
    "FOREX": 0.05,      # 5% para Forex
    "INDEX": 0.05,      # 5% para índices
    "STOCK": 0.05,      # 5% para acciones
    "COMMODITY": 0.05,  # 5% para commodities
    "CRYPTO": 0.02,     # 2% para crypto (más conservador)
    "PAIR": 0.05,       # 5% para pares
    "DEFAULT": 0.05     # 5% por defecto
}

# Control de operaciones
MIN_TIME_BETWEEN_SIGNALS = 60  # Minutos entre señales del mismo activo (1 hora)
MAX_CONSECUTIVE_FOR_DAILY_LOCK = 2  # Número de operaciones consecutivas (wins o losses) para parar el día
MAX_CONSECUTIVE_LOSSES = 999   # No se usa - ahora se para con 2 consecutivas (wins o losses)

# Configuración de activos
ALLOWED_ASSET_SUFFIXES = ["-OTC", "-op", ""]
PRIORITY_SUFFIX = None  # Sin prioridad - usa cualquier variante disponible

# Modo de estrategia
STRATEGY_MODE = "CALL_PUT"

# Configuración de logging
LOG_LEVEL = "INFO"
LOG_FILE = "iqoption_strategy.log"

# Configuración de caché y timeouts
API_TIMEOUT = 15
SAVE_STATE_INTERVAL = 30

# Archivo de estado
STATE_FILE = "strategy_state.json"

# Configuración de debugging
USE_POSITION_HISTORY = True
POSITION_HISTORY_TIMEOUT = 5
DEBUG_ORDER_RESULTS = True

# Mostrar configuración al iniciar (para debugging)
def print_asset_configuration():
    """Imprimir la configuración de activos para verificación"""
    print("\n📊 CONFIGURACIÓN DE ACTIVOS POR GRUPO:")
    print("=" * 60)
    
    for group in ["FOREX", "INDEX", "STOCK", "COMMODITY", "CRYPTO", "PAIR"]:
        assets = globals()[f"{group}_ASSETS"]
        if assets:
            levels = RSI_LEVELS[group]
            momentum = MIN_MOMENTUM_POINTS_BY_GROUP[group]
            position_size = POSITION_SIZE_PERCENT_BY_GROUP.get(group, POSITION_SIZE_PERCENT)
            print(f"\n{group}:")
            print(f"  Activos: {', '.join(assets)}")
            print(f"  Algebra Inversa: {levels['OVERSOLD']}/{levels['OVERBOUGHT']}")
            print(f"  Momentum mínimo: {momentum} puntos")
            print(f"  Tamaño posición: {position_size*100}%")
            print(f"  Descripción: {levels['DESCRIPTION']}")
    
    print("\n" + "=" * 60)
    
    # Mostrar resumen total
    total_assets = len(TRADING_ASSETS)
    print(f"\n📊 TOTAL DE ACTIVOS CONFIGURADOS: {total_assets}")
    print(f"📊 COMPOSICIÓN:")
    print(f"  - Forex: {len(FOREX_ASSETS)}")
    print(f"  - Índices: {len(INDEX_ASSETS)}")
    print(f"  - Acciones: {len(STOCK_ASSETS)}")
    print(f"  - Commodities: {len(COMMODITY_ASSETS)}")
    print(f"  - Pares: {len(PAIR_ASSETS)}")
    print(f"  - Crypto: {len(CRYPTO_ASSETS)} (ACTIVO)")
    print("=" * 60)

def print_aggressiveness_configuration():
    """Imprimir la configuración de agresividad activa"""
    print("\n⚡ CONFIGURACIÓN DE AGRESIVIDAD:")
    print("=" * 60)
    print(f"Modo activo: {AGGRESSIVENESS_MODE}")
    print(f"Descripción: {ACTIVE_CONFIG['description']}")
    print(f"\nParámetros:")
    print(f"  - Timeframe velas: {ACTIVE_CONFIG['candle_timeframe']//60} minutos")
    print(f"  - Expiración: {ACTIVE_CONFIG['expiry_minutes']} minutos")
    print(f"  - Fuerza mínima señal: {ACTIVE_CONFIG['min_strength']}%")
    print(f"  - Cruces válidos: últimas {ACTIVE_CONFIG.get('max_candles_for_cross', 2)} velas")
    print(f"  - Permitir rebotes: {'Sí' if ACTIVE_CONFIG['allow_rebounds'] else 'No'}")
    if ACTIVE_CONFIG['allow_rebounds']:
        print(f"  - Máximo rebotes: {ACTIVE_CONFIG['max_rebounds']}")
        print(f"  - Tolerancia rebote: {ACTIVE_CONFIG['rebound_tolerance']} puntos Algebra Inversa")
    print(f"\n🎯 LÍMITE DE TRADES SIMULTÁNEOS: {MAX_SIMULTANEOUS_TRADES}")
    print("=" * 60)