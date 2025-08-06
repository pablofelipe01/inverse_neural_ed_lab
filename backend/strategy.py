# strategy.py
#Algoritmo de Algebra Invertida para opciones binarias

import warnings
import threading

# Suprimir errores de threads secundarios
threading.excepthook = lambda args: None

import time
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import pytz
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from iqoptionapi.stable_api import IQ_Option

from config import (
    IQ_EMAIL, IQ_PASSWORD, ACCOUNT_TYPE, TRADING_ASSETS, ASSET_IQ_MAPPING,
    RSI_PERIOD, OVERSOLD_LEVEL, OVERBOUGHT_LEVEL, EXPIRY_MINUTES, CANDLE_TIMEFRAME,
    ABSOLUTE_STOP_LOSS_PERCENT, MONTHLY_STOP_LOSS_PERCENT, POSITION_SIZE_PERCENT,
    MIN_POSITION_SIZE, MIN_TIME_BETWEEN_SIGNALS, MAX_CONSECUTIVE_LOSSES,
    ALLOWED_ASSET_SUFFIXES, PRIORITY_SUFFIX, STRATEGY_MODE, LOG_LEVEL, LOG_FILE,
    API_TIMEOUT, SAVE_STATE_INTERVAL, STATE_FILE, USE_POSITION_HISTORY,
    POSITION_HISTORY_TIMEOUT, DEBUG_ORDER_RESULTS,
    # NUEVAS IMPORTACIONES
    get_asset_group, get_rsi_levels_for_asset, get_min_momentum_for_asset,
    RSI_LEVELS, MIN_MOMENTUM_POINTS_BY_GROUP, POSITION_SIZE_PERCENT_BY_GROUP,
    # IMPORTACIONES DE AGRESIVIDAD
    AGGRESSIVENESS_MODE, ACTIVE_CONFIG, print_aggressiveness_configuration,
    # FUNCIONES DINÁMICAS DE AGRESIVIDAD
    get_aggressiveness_config, get_expiry_minutes, get_candle_timeframe, get_min_strength,
    # NUEVA IMPORTACIÓN PARA LÍMITE DE TRADES
    MAX_SIMULTANEOUS_TRADES
)
from utils import calculate_rsi, is_market_open, format_currency, calculate_win_rate, setup_logger

class MultiAssetRSIBinaryOptionsStrategy:
    def __init__(self, email, password, account_type="PRACTICE", selected_pairs=None, selected_crypto=None, 
                 position_size=None, pairs_position_size=None, crypto_position_size=None, aggressiveness=None):
        """
        Inicializar la estrategia de opciones con Algoritmo
        Adaptado de QuantConnect para IQ Option - Multi-Activos
        
        Args:
            email: Email de IQ Option
            password: Contraseña de IQ Option  
            account_type: Tipo de cuenta ("PRACTICE" o "REAL")
            selected_pairs: Lista de pares específicos a operar (ej: ["NVDA/AMD", "TESLA/FORD"])
            selected_crypto: Lista de crypto específicos a operar (ej: ["BTCUSD", "ETHUSD"])
            position_size: Tamaño de posición personalizado (1-15%) - legacy
            pairs_position_size: Tamaño de posición para pares (1-15%)
            crypto_position_size: Tamaño de posición para crypto (1-5%)
            aggressiveness: Nivel de agresividad ("conservador", "balanceado", "agresivo")
        """
        # Configurar logger
        self.logger = setup_logger(__name__, LOG_FILE, getattr(logging, LOG_LEVEL))
        
        # HEADER PRINCIPAL DE LA ESTRATEGIA
        self.logger.info("=" * 60)
        self.logger.info("   ESTRATEGIA ALGEBRA MULTI-ACTIVOS PARA OPTION")
        self.logger.info("   ⚡ LÓGICA INVERTIDA ⚡")
        self.logger.info("=" * 60)
        self.logger.info(f"📅 Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"📧 Usuario: {email[:3]}***@{email.split('@')[1] if '@' in email else 'gmail.com'}")
        self.logger.info("=" * 60)
        self.logger.info("⚠️ IMPORTANTE: Esta estrategia usa lógica INVERTIDA")
        self.logger.info("   - PUT cuando Algebra Inversa ≤ 35 (sobreventa)")
        self.logger.info("   - CALL cuando Algebra Inversa ≥ 65 (sobrecompra)")
        self.logger.info("=" * 60)
        self.logger.info("🚀 Inicializando estrategia...")
        self.logger.info(f"🎯 Pares seleccionados: {', '.join(selected_pairs) if selected_pairs else 'Todos los disponibles'}")
        self.logger.info(f"🪙 Crypto seleccionados: {', '.join(selected_crypto) if selected_crypto else 'Todos los disponibles'}")
        self.logger.info(f"💰 Tamaño de posición (legacy): {position_size if position_size else 'Por defecto'}%")
        self.logger.info(f"📊 Tamaño de posición pares: {pairs_position_size if pairs_position_size else 'Por defecto'}%")
        self.logger.info(f"🪙 Tamaño de posición crypto: {crypto_position_size if crypto_position_size else 'Por defecto'}%")
        self.logger.info(f"⚡ Nivel de agresividad: {aggressiveness if aggressiveness else 'Por defecto'}")
        
        self.logger.info("🎯 INICIANDO ESTRATEGIA ALGEBRA MULTI-ACTIVOS (LÓGICA INVERTIDA)")
        self.logger.info("📊 Configuración: Niveles Algebra Inversa dinámicos por grupo de activos")
        self.logger.info("⚡ LÓGICA INVERTIDA: PUT en sobreventa, CALL en sobrecompra")
        self.logger.info(f"🎯 LÍMITE DE TRADES SIMULTÁNEOS: {MAX_SIMULTANEOUS_TRADES}")
        
        # Configuración personalizada de pares
        if selected_pairs:
            self.logger.info(f"🎯 PARES SELECCIONADOS: {selected_pairs}")
            # Filtrar TRADING_ASSETS para usar solo los pares seleccionados
            self.selected_pairs = selected_pairs
            
            # Los nombres del frontend son exactamente iguales a los del config.py
            # No necesitamos mapeo, solo verificar que estén en TRADING_ASSETS
            filtered_assets = []
            for pair in selected_pairs:
                if pair in TRADING_ASSETS:
                    filtered_assets.append(pair)
                    self.logger.info(f"✅ Par habilitado: {pair}")
                else:
                    self.logger.warning(f"⚠️ Par no encontrado en configuración: {pair}")
            
            if filtered_assets:
                self.trading_assets = filtered_assets
                self.logger.info(f"🎯 Operando con {len(filtered_assets)} pares seleccionados")
            else:
                self.logger.warning("⚠️ Ningún par válido seleccionado, usando configuración por defecto")
                self.trading_assets = TRADING_ASSETS
        else:
            self.trading_assets = TRADING_ASSETS
        
        # Configuración personalizada de crypto assets
        if selected_crypto:
            self.logger.info(f"🪙 CRYPTO SELECCIONADOS: {selected_crypto}")
            from config import CRYPTO_ASSETS
            
            # Verificar que los crypto seleccionados estén en la configuración
            filtered_crypto = []
            for crypto in selected_crypto:
                if crypto in CRYPTO_ASSETS:
                    filtered_crypto.append(crypto)
                    self.logger.info(f"✅ Crypto habilitado: {crypto}")
                else:
                    self.logger.warning(f"⚠️ Crypto no encontrado en configuración: {crypto}")
            
            if filtered_crypto:
                # Agregar crypto assets a la lista de trading assets
                self.trading_assets.extend(filtered_crypto)
                self.logger.info(f"🪙 Operando con {len(filtered_crypto)} crypto seleccionados")
            else:
                self.logger.warning("⚠️ Ningún crypto válido seleccionado")
        
        # Configuración personalizada de tamaños de posición
        if position_size:
            self.custom_position_size = position_size
            self.logger.info(f"💰 Tamaño de posición personalizado (legacy): {position_size}%")
        else:
            self.custom_position_size = None
        
        # Position sizes separados por tipo de asset
        if pairs_position_size:
            self.custom_pairs_position_size = pairs_position_size
            self.logger.info(f"📊 Tamaño de posición pares personalizado: {pairs_position_size}%")
        else:
            self.custom_pairs_position_size = None
        
        if crypto_position_size:
            self.custom_crypto_position_size = crypto_position_size
            self.logger.info(f"🪙 Tamaño de posición crypto personalizado: {crypto_position_size}%")
        else:
            self.custom_crypto_position_size = None
        
        # Configuración personalizada de agresividad
        if aggressiveness:
            # Mapear valores del frontend a valores del config
            aggressiveness_mapping = {
                'conservador': 'CONSERVATIVE',
                'balanceado': 'BALANCED', 
                'agresivo': 'AGGRESSIVE'
            }
            
            mapped_aggressiveness = aggressiveness_mapping.get(aggressiveness.lower(), 'BALANCED')
            self.custom_aggressiveness = mapped_aggressiveness
            self.logger.info(f"⚡ Agresividad personalizada: {aggressiveness} → {mapped_aggressiveness}")
            
            # Obtener configuración dinámica
            self.active_config = get_aggressiveness_config(mapped_aggressiveness)
        else:
            self.custom_aggressiveness = None
            self.active_config = get_aggressiveness_config()  # Configuración por defecto
        
        # Mostrar configuración de agresividad
        print_aggressiveness_configuration()
        
        # Mostrar modo activo (personalizado o por defecto)
        if self.custom_aggressiveness:
            self.logger.info(f"⚙️ Modo de agresividad: {self.custom_aggressiveness} (personalizado)")
        else:
            self.logger.info(f"⚙️ Modo de agresividad: {AGGRESSIVENESS_MODE} (por defecto)")
        
        # Usar configuración dinámica
        self.expiry_minutes = self.active_config["expiry_minutes"]
        self.candle_timeframe = self.active_config["candle_timeframe"]
        self.min_strength = self.active_config["min_strength"]
        
        self.logger.info(f"📊 Timeframe: {self.candle_timeframe//60} min | Expiración: {self.expiry_minutes} min | Fuerza mínima: {self.min_strength}%")
        
        # Conexión a IQ Option
        self._connect_to_iq_option(email, password, account_type)
        
        # Capital inicial y gestión de riesgo
        self.initial_capital = self.iqoption.get_balance()
        self.logger.info(f"💰 Capital inicial: {format_currency(self.initial_capital)}")
        
        # Umbrales de stop loss
        self.absolute_stop_loss_threshold = self.initial_capital * (1 - ABSOLUTE_STOP_LOSS_PERCENT)
        self.absolute_stop_loss_activated = False
        
        # Configuración de posiciones
        if self.custom_position_size:
            self.position_size_percent = self.custom_position_size / 100.0  # Convertir de % a decimal
        else:
            self.position_size_percent = POSITION_SIZE_PERCENT
        self.min_position_size = MIN_POSITION_SIZE
        
        # Parámetros de trading - usar los assets filtrados y configuración dinámica
        self.asset_mapping = ASSET_IQ_MAPPING
        self.rsi_period = RSI_PERIOD
        self.min_time_between_signals = MIN_TIME_BETWEEN_SIGNALS
        
        # NUEVO: Ya no usamos valores fijos de RSI
        # Los niveles se obtienen dinámicamente por activo
        
        # Gestión de operaciones activas
        self.active_options = defaultdict(list)
        self.last_signal_time = defaultdict(lambda: datetime.min)
        self.consecutive_losses = defaultdict(int)
        self.daily_lockouts = defaultdict(lambda: False)
        
        # Historial de RSI para validación de momentum
        self.rsi_history = defaultdict(lambda: deque(maxlen=5))  # Últimas 5 lecturas
        
        # Stop loss mensual
        self.monthly_stop_loss = False
        self.stop_loss_triggered_month = None
        self.monthly_starting_capital = {}
        self.current_month = None
        
        # Estadísticas de trading
        self.wins = defaultdict(int)
        self.losses = defaultdict(int)
        self.ties = defaultdict(int)  # Contador de empates
        self.total_profit = 0.0
        self.daily_profit = 0.0
        self.monthly_profits = defaultdict(float)
        self.last_date = None
        self.min_capital = self.initial_capital
        
        # Balance tracking para verificación
        self.session_start_balance = self.initial_capital
        self.day_start_balance = self.initial_capital
        
        # Daily profit/loss tracking con nueva lógica
        self.daily_consecutive_wins = 0
        self.daily_consecutive_losses = 0
        self.daily_lock = False
        self.daily_lock_time = None
        self.daily_lock_reason = None  # "wins" o "losses"
        self.max_daily_consecutive = 2  # 2 consecutivas para activar lock
        
        # Historial de resultados recientes (para tracking global)
        self.recent_results = deque(maxlen=2)  # Solo necesitamos las últimas 2
        
        # Control de sistema
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.last_activity_time = time.time()
        self.start_time = time.time()
        
        # Cache para optimización
        self.opcode_cache = {}
        self.opcode_cache_timestamp = 0
        self.asset_open_status_cache = {}
        self.asset_open_status_timestamp = 0
        
        # Mapeo de activos
        self.asset_option_types = {}
        self.iqoption_assets = {}
        self.valid_assets = []
        
        # Cargar estado previo si existe
        self.load_state()
        
        # Verificar si es un nuevo día al iniciar
        current_date = datetime.now().date()
        if self.last_date != current_date:
            self.logger.info(f"🌅 Detectado nuevo día al iniciar: {current_date}")
            self.on_new_day()
            self.last_date = current_date
        
        # Validar activos disponibles
        self.check_valid_assets()
        
        # Mostrar configuración de grupos
        self._print_group_configuration()
        
        self.logger.info("✅ Sistema iniciado - Detectando momentum real con validación dinámica")
        self.logger.info("🎯 Iniciando operaciones...")
        self.logger.info("ℹ️ Para detener la estrategia, desactiva el switch en el dashboard")
        
    def _print_group_configuration(self):
        """Mostrar la configuración de niveles por grupo"""
        self.logger.info("\n📊 CONFIGURACIÓN DE NIVELES ALGEBRA INVERSA POR GRUPO:")
        self.logger.info("=" * 60)
        
        # Agrupar activos válidos por tipo
        groups_in_use = defaultdict(list)
        for asset in self.valid_assets:
            group = get_asset_group(asset)
            groups_in_use[group].append(asset)
        
        # Mostrar solo grupos con activos activos
        for group, assets in groups_in_use.items():
            if assets:
                levels = RSI_LEVELS[group]
                momentum = MIN_MOMENTUM_POINTS_BY_GROUP[group]
                
                # Usar configuración personalizada si está disponible
                if self.custom_position_size:
                    position_size = self.position_size_percent  # Ya en decimal
                    position_display = f"{self.custom_position_size}% (personalizado)"
                else:
                    position_size = POSITION_SIZE_PERCENT_BY_GROUP.get(group, POSITION_SIZE_PERCENT)
                    position_display = f"{position_size*100}%"
                
                self.logger.info(f"\n{group}:")
                self.logger.info(f"  Activos: {', '.join(assets)}")
                self.logger.info(f"  Algebra Inversa Sobreventa/Sobrecompra: {levels['OVERSOLD']}/{levels['OVERBOUGHT']}")
                self.logger.info(f"  Momentum mínimo: {momentum} puntos")
                self.logger.info(f"  Tamaño posición: {position_display}")
        
        self.logger.info("=" * 60)
        
        # Mostrar configuración de señales
        active_config, active_mode = self.get_aggressiveness_config()
        self.logger.info("\n⚡ CONFIGURACIÓN DE SEÑALES:")
        mode_display = f"{active_mode} (personalizado)" if self.custom_aggressiveness else active_mode
        self.logger.info(f"  Modo: {mode_display}")
        self.logger.info(f"  Fuerza mínima: {active_config['min_strength']}%")
        self.logger.info(f"  Cruces válidos: últimas {active_config.get('max_candles_for_cross', 2)} niveles dinámicos")
        self.logger.info(f"  Permitir rebotes: {'Sí' if active_config['allow_rebounds'] else 'No'}")
        if active_config['allow_rebounds']:
            self.logger.info(f"  Máx rebotes: {active_config['max_rebounds']} de hasta {active_config['rebound_tolerance']} puntos")
        self.logger.info(f"  🎯 Máximo trades simultáneos: {MAX_SIMULTANEOUS_TRADES}")
        self.logger.info("=" * 60)
        
    def _connect_to_iq_option(self, email, password, account_type):
        """Conectar a IQ Option con manejo de errores"""
        self.logger.info("🔗 Conectando a IQ Option...")
        self.iqoption = IQ_Option(email, password)
        login_status, login_reason = self.iqoption.connect()
        
        if not login_status:
            self.logger.error(f"❌ Error al conectar: {login_reason}")
            if "2FA" in str(login_reason).upper():
                self.logger.info("🔑 Se requiere autenticación de dos factores (2FA)")
            raise Exception(f"Error al conectar a IQ Option: {login_reason}")
        
        self.logger.info("✅ Conexión exitosa")
        self.iqoption.change_balance(account_type)
        balance = self.iqoption.get_balance()
        self.logger.info(f"💰 Balance actual: {format_currency(balance)}")
    
    def api_call_with_timeout(self, func, *args, timeout=API_TIMEOUT, **kwargs):
        """Ejecutar llamada API con timeout"""
        self.last_activity_time = time.time()
        try:
            future = self.executor.submit(func, *args, **kwargs)
            result = future.result(timeout=timeout)
            return result
        except FutureTimeoutError:
            self.logger.error(f"⚠️ TIMEOUT: {func.__name__} tardó más de {timeout}s")
            return None
        except Exception as e:
            self.logger.error(f"❌ Error en {func.__name__}: {str(e)}")
            return None
    
    def check_valid_assets(self):
        """Verificar qué activos están disponibles para operar"""
        self.logger.info("🔍 Verificando activos disponibles...")
        
        # Actualizar lista de activos
        self.api_call_with_timeout(self.iqoption.update_ACTIVES_OPCODE)
        opcodes = self.api_call_with_timeout(self.iqoption.get_all_ACTIVES_OPCODE)
        
        if not opcodes:
            self.logger.error("❌ No se pudieron obtener los activos disponibles")
            return []
        
        # Obtener estado de activos
        all_assets = self.api_call_with_timeout(self.iqoption.get_all_open_time)
        if not all_assets:
            self.logger.error("❌ No se pudo obtener el estado de los activos")
            return []
        
        self.valid_assets = []
        self.asset_option_types = {}
        self.iqoption_assets = {}
        
        # Verificar cada activo
        for asset in self.trading_assets:
            # Si tenemos un mapeo conocido, usarlo directamente
            if asset in self.asset_mapping:
                iq_name = self.asset_mapping[asset]
                found = False
                
                # Buscar en opciones turbo y binarias (preferir binarias)
                for option_type in ["binary", "turbo"]:
                    if option_type not in all_assets:
                        continue
                    
                    if iq_name in all_assets[option_type]:
                        if all_assets[option_type][iq_name].get("open", False):
                            self.valid_assets.append(asset)
                            self.asset_option_types[asset] = option_type
                            self.iqoption_assets[asset] = iq_name
                            group = get_asset_group(asset)
                            self.logger.info(f"✅ {asset}: Disponible como {iq_name} ({option_type}) - Grupo: {group}")
                            found = True
                            break
                
                if not found:
                    self.logger.warning(f"⚠️ {asset}: No disponible ({iq_name})")
            else:
                # Buscar variantes si no hay mapeo (compatibilidad con versión anterior)
                asset_upper = asset.upper()
                found = False
                available_options = []
                
                # Buscar en opciones turbo y binarias
                for option_type in ["turbo", "binary"]:
                    if option_type not in all_assets:
                        continue
                    
                    # Lista de variantes a verificar
                    variants_to_check = [
                        asset_upper,
                        f"{asset_upper}-OTC",
                        f"{asset_upper}-op"
                    ]
                    
                    # Buscar cada variante
                    for variant in variants_to_check:
                        if variant in all_assets[option_type]:
                            if all_assets[option_type][variant].get("open", False):
                                available_options.append({
                                    'asset': asset,
                                    'option_type': option_type,
                                    'iq_name': variant,
                                    'is_otc': variant.endswith('-OTC')
                                })
                                group = get_asset_group(asset)
                                self.logger.info(f"✅ {asset}: Encontrado como {variant} ({option_type}) - Grupo: {group}")
                
                # Seleccionar la mejor opción disponible
                if available_options:
                    best_option = available_options[0]  # Primera disponible
                    self.valid_assets.append(best_option['asset'])
                    self.asset_option_types[best_option['asset']] = best_option['option_type']
                    self.iqoption_assets[best_option['asset']] = best_option['iq_name']
                else:
                    self.logger.warning(f"⚠️ {asset}: No disponible en ninguna variante")
        
        # Log resumen
        self.logger.info(f"📊 Total activos disponibles: {len(self.valid_assets)}")
        
        return self.valid_assets
    
    def handle_trading_error(self, asset, error_message):
        """
        Manejar errores de trading y cambiar a activo alternativo si es necesario
        """
        self.logger.warning(f"⚠️ Error con {self.iqoption_assets[asset]}: {error_message}")
        
        # Si el activo no está disponible, intentar con una variante alternativa
        if "not available" in error_message or "suspended" in error_message:
            self.logger.info(f"🔄 Buscando alternativa para {asset}...")
            
            # Obtener estado actual de activos
            all_assets = self.api_call_with_timeout(self.iqoption.get_all_open_time)
            if not all_assets:
                return False
            
            current_asset = self.iqoption_assets[asset]
            
            # Para activos con mapeo fijo, no hay alternativas
            if asset in self.asset_mapping:
                self.logger.warning(f"❌ {asset} tiene mapeo fijo, no hay alternativas")
                if asset in self.valid_assets:
                    self.valid_assets.remove(asset)
                return False
            
            # Para otros activos, buscar alternativas
            asset_upper = asset.upper()
            alternatives = [
                f"{asset_upper}-OTC",
                asset_upper,
                f"{asset_upper}-op"
            ]
            
            # Quitar el activo actual de las alternativas
            alternatives = [alt for alt in alternatives if alt != current_asset]
            
            # Buscar una alternativa funcional
            for alt_asset in alternatives:
                for option_type in ["binary", "turbo"]:
                    if option_type in all_assets and alt_asset in all_assets[option_type]:
                        if all_assets[option_type][alt_asset].get("open", False):
                            # Actualizar a la alternativa
                            self.logger.info(f"✅ Cambiando {asset} de {current_asset} a {alt_asset} ({option_type})")
                            self.iqoption_assets[asset] = alt_asset
                            self.asset_option_types[asset] = option_type
                            return True
            
            # Si no hay alternativas, eliminar el activo temporalmente
            self.logger.warning(f"❌ No hay alternativas disponibles para {asset}, eliminándolo temporalmente")
            if asset in self.valid_assets:
                self.valid_assets.remove(asset)
            return False
        
        return True
    
    def calculate_position_size(self, asset=None):
        """Calcular tamaño de posición basado en el capital actual y configuración personalizada"""
        current_capital = self.api_call_with_timeout(self.iqoption.get_balance)
        if current_capital is None:
            current_capital = self.initial_capital
        
        # Determinar si es crypto o par
        is_crypto = False
        if asset:
            from config import CRYPTO_ASSETS
            is_crypto = asset in CRYPTO_ASSETS
        
        # Usar position sizes específicos si están configurados
        if is_crypto and self.custom_crypto_position_size:
            position_percent = self.custom_crypto_position_size / 100.0
            self.logger.debug(f"🪙 Usando tamaño personalizado crypto: {self.custom_crypto_position_size}%")
        elif not is_crypto and self.custom_pairs_position_size:
            position_percent = self.custom_pairs_position_size / 100.0
            self.logger.debug(f"📊 Usando tamaño personalizado pares: {self.custom_pairs_position_size}%")
        elif self.custom_position_size:
            # Fallback a legacy position size
            position_percent = self.position_size_percent  # Ya convertido a decimal en el constructor
            self.logger.debug(f"💰 Usando tamaño personalizado (legacy): {self.custom_position_size}%")
        else:
            # Solo usar configuración por grupo si NO hay configuración personalizada
            if asset:
                group = get_asset_group(asset)
                position_percent = POSITION_SIZE_PERCENT_BY_GROUP.get(group, self.position_size_percent)
            else:
                position_percent = self.position_size_percent
        
        # Calcular porcentaje del capital actual
        position_size = round(current_capital * position_percent, 2)
        
        # Solo aplicar límite mínimo (no hay límite máximo)
        position_size = max(self.min_position_size, position_size)
        
        self.logger.debug(f"💰 Capital: ${current_capital:,.2f} → Posición: ${position_size:,.2f} ({position_percent*100}%) {'🪙' if is_crypto else '📊'}")
        
        return position_size
    
    def get_aggressiveness_config(self):
        """Obtener configuración de agresividad activa (personalizada o por defecto)"""
        from config import AGGRESSIVENESS_CONFIG
        
        if self.custom_aggressiveness:
            config = AGGRESSIVENESS_CONFIG[self.custom_aggressiveness]
            self.logger.debug(f"⚡ Usando configuración personalizada: {self.custom_aggressiveness}")
            return config, self.custom_aggressiveness
        else:
            config = ACTIVE_CONFIG
            mode = AGGRESSIVENESS_MODE
            self.logger.debug(f"⚡ Usando configuración por defecto: {mode}")
            return config, mode
    
    def get_rsi(self, asset):
        """Obtener RSI para un activo específico usando timeframe configurado"""
        try:
            # Usar el timeframe configurado (15 minutos por defecto)
            candles = self.api_call_with_timeout(
                self.iqoption.get_candles,
                self.iqoption_assets[asset],
                self.candle_timeframe,  # 900 segundos = 15 minutos
                100,
                time.time()
            )
            
            if candles and len(candles) >= self.rsi_period:
                rsi = calculate_rsi(candles, self.rsi_period)
                if rsi is not None:
                    self.logger.debug(f"📊 {asset} - Algebra Inversa({self.candle_timeframe//60}min): {rsi:.2f}")
                return rsi
            
            self.logger.warning(f"⚠️ No se pudo calcular Algebra Inversa para {asset}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo Algebra Inversa para {asset}: {str(e)}")
            return None
    
    def place_option(self, asset, direction, amount):
        """Colocar una opción binaria con reintentos automáticos"""
        max_retries = 2
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                asset_name = self.iqoption_assets[asset]
                option_type = self.asset_option_types[asset]
                
                self.logger.info(f"📈 Colocando {direction} en {asset} ({asset_name}), cantidad: {format_currency(amount)}")
                
                status, order_id = self.api_call_with_timeout(
                    self.iqoption.buy,
                    int(amount),
                    asset_name,
                    direction.lower(),
                    self.expiry_minutes
                )
                
                if status:
                    self.logger.info(f"✅ Orden colocada exitosamente. ID: {order_id}")
                    return order_id
                else:
                    # Manejar el error
                    error_msg = str(order_id) if order_id else "Error desconocido"
                    
                    # Si es un error de disponibilidad y tenemos reintentos
                    if retry_count < max_retries - 1 and ("not available" in error_msg or "suspended" in error_msg):
                        if self.handle_trading_error(asset, error_msg):
                            retry_count += 1
                            self.logger.info(f"🔄 Reintentando con activo alternativo... (intento {retry_count + 1}/{max_retries})")
                            time.sleep(1)  # Pequeña pausa antes de reintentar
                            continue
                    
                    self.logger.error(f"❌ Error colocando orden: {error_msg}")
                    return None
                    
            except Exception as e:
                self.logger.error(f"❌ Excepción colocando orden: {str(e)}")
                
                # Si es un error de conexión/timeout y tenemos reintentos
                if retry_count < max_retries - 1:
                    retry_count += 1
                    self.logger.info(f"🔄 Reintentando... (intento {retry_count + 1}/{max_retries})")
                    time.sleep(2)
                    continue
                
                return None
        
        return None
    
    def calculate_signal_strength(self, asset, current_rsi, direction, history, oversold_level, overbought_level):
        """Calcular fuerza de la señal (0-100)"""
        strength = 0
        
        # Factor 1: Qué tan extremo es el RSI (40%)
        if direction == "PUT":
            oversold_distance = oversold_level - current_rsi
            strength += min(40, oversold_distance * 4)
        else:
            overbought_distance = current_rsi - overbought_level
            strength += min(40, overbought_distance * 4)
        
        # Factor 2: Velocidad del movimiento (30%)
        momentum = abs(history[0] - current_rsi)
        strength += min(30, momentum * 3)
        
        # Factor 3: Limpieza de la tendencia (30%)
        clean_trend_score = self.calculate_trend_cleanliness(history, current_rsi, direction)
        strength += clean_trend_score * 30
        
        return strength
    
    def calculate_trend_cleanliness(self, history, current_rsi, direction):
        """Calcular qué tan limpia es la tendencia (0-1)"""
        if len(history) < 2:
            return 0
        
        rebounds = 0
        total_comparisons = 0
        
        # Agregar RSI actual al análisis
        full_history = list(history) + [current_rsi]
        
        for i in range(len(full_history) - 1):
            total_comparisons += 1
            
            if direction == "PUT":
                # Para PUT, esperamos que cada valor sea menor que el anterior
                if full_history[i] <= full_history[i + 1]:
                    rebounds += 1
            else:
                # Para CALL, esperamos que cada valor sea mayor que el anterior
                if full_history[i] >= full_history[i + 1]:
                    rebounds += 1
        
        # Calcular puntuación (1 = perfecta, 0 = muy mala)
        if total_comparisons == 0:
            return 0
        
        cleanliness = 1 - (rebounds / total_comparisons)
        return cleanliness
    
    def has_valid_momentum(self, asset, current_rsi, direction, min_momentum_points):
        """Verificar si hay momentum real en la dirección esperada - VERSIÓN FLEXIBLE"""
        history = list(self.rsi_history[asset])
        
        # Necesitamos al menos 3 valores para validar tendencia
        if len(history) < 3:
            return False
        
        # Obtener configuración de agresividad activa
        active_config, _ = self.get_aggressiveness_config()
        allow_rebounds = active_config["allow_rebounds"]
        max_rebounds = active_config["max_rebounds"]
        rebound_tolerance = active_config["rebound_tolerance"]
        min_strength = active_config["min_strength"]
        
        # NUEVO: Verificar que es un cruce FRESCO (no una señal gastada)
        oversold_level, overbought_level = get_rsi_levels_for_asset(asset)
        
        # Para señal PUT (RSI bajando)
        if direction == "PUT":
            # Verificar que el cruce es reciente (según configuración)
            cross_found = False
            max_candles_back = active_config.get("max_candles_for_cross", 2)
            
            for i in range(min(max_candles_back, len(history)-1)):
                if history[i] > oversold_level and history[i+1] <= oversold_level:
                    cross_found = True
                    self.logger.debug(f"📉 {asset} - Cruce fresco detectado hace {i+1} nivel(es) dinámico(s): {history[i]:.1f} → {history[i+1]:.1f}")
                    break
            
            # Si el RSI actual cruza el nivel, también es válido
            if len(history) > 0 and history[-1] > oversold_level and current_rsi <= oversold_level:
                cross_found = True
                self.logger.debug(f"📉 {asset} - Cruce fresco ACTUAL: {history[-1]:.1f} → {current_rsi:.1f}")
            
            if not cross_found:
                self.logger.debug(f"⏭️ {asset} - Algebra Inversa en sobreventa pero sin cruce fresco (señal gastada)")
                return False
            
            # Verificar tendencia con tolerancia a rebotes
            if allow_rebounds:
                rebounds = 0
                for i in range(len(history) - 1):
                    if history[i] <= history[i + 1]:
                        # Verificar si es un rebote menor
                        if history[i + 1] - history[i] <= rebound_tolerance:
                            rebounds += 1
                            if rebounds > max_rebounds:
                                self.logger.debug(f"📉 {asset} - Demasiados rebotes ({rebounds})")
                                return False
                        else:
                            # Rebote grande, no es tendencia válida
                            self.logger.debug(f"📉 {asset} - Rebote muy grande ({history[i + 1] - history[i]:.1f} puntos)")
                            return False
            else:
                # Modo conservador: no permitir rebotes
                for i in range(len(history) - 1):
                    if history[i] <= history[i + 1]:
                        return False
            
            # Verificar magnitud mínima del movimiento
            total_drop = history[0] - current_rsi
            if total_drop < min_momentum_points:
                self.logger.debug(f"📉 {asset} - Caída insuficiente: {total_drop:.1f} puntos (mínimo: {min_momentum_points})")
                return False
            
            # Calcular fuerza de la señal
            signal_strength = self.calculate_signal_strength(asset, current_rsi, direction, history, oversold_level, 0)
            
            if signal_strength < min_strength:
                self.logger.debug(f"📉 {asset} - Señal débil: {signal_strength:.0f}% (mínimo: {min_strength}%)")
                return False
            
            # Momentum válido
            self.logger.info(f"✅ {asset} - Momentum PUT confirmado: {history[0]:.1f} → {current_rsi:.1f}")
            self.logger.info(f"   Caída: {total_drop:.1f} puntos | Fuerza: {signal_strength:.0f}% | Cruce FRESCO ✓")
            return True
        
        # Para señal CALL (RSI subiendo)
        elif direction == "CALL":
            # Verificar que el cruce es reciente (según configuración)
            cross_found = False
            max_candles_back = active_config.get("max_candles_for_cross", 2)
            
            for i in range(min(max_candles_back, len(history)-1)):
                if history[i] < overbought_level and history[i+1] >= overbought_level:
                    cross_found = True
                    self.logger.debug(f"📈 {asset} - Cruce fresco detectado hace {i+1} nivel(es) dinámico(s): {history[i]:.1f} → {history[i+1]:.1f}")
                    break
            
            # Si el RSI actual cruza el nivel, también es válido
            if len(history) > 0 and history[-1] < overbought_level and current_rsi >= overbought_level:
                cross_found = True
                self.logger.debug(f"📈 {asset} - Cruce fresco ACTUAL: {history[-1]:.1f} → {current_rsi:.1f}")
            
            if not cross_found:
                self.logger.debug(f"⏭️ {asset} - Algebra Inversa en sobrecompra pero sin cruce fresco (señal gastada)")
                return False
            
            # Verificar tendencia con tolerancia a rebotes
            if allow_rebounds:
                rebounds = 0
                for i in range(len(history) - 1):
                    if history[i] >= history[i + 1]:
                        # Verificar si es un rebote menor
                        if history[i] - history[i + 1] <= rebound_tolerance:
                            rebounds += 1
                            if rebounds > max_rebounds:
                                self.logger.debug(f"📈 {asset} - Demasiados rebotes ({rebounds})")
                                return False
                        else:
                            # Rebote grande, no es tendencia válida
                            self.logger.debug(f"📈 {asset} - Rebote muy grande ({history[i] - history[i + 1]:.1f} puntos)")
                            return False
            else:
                # Modo conservador: no permitir rebotes
                for i in range(len(history) - 1):
                    if history[i] >= history[i + 1]:
                        return False
            
            # Verificar magnitud mínima del movimiento
            total_rise = current_rsi - history[0]
            if total_rise < min_momentum_points:
                self.logger.debug(f"📈 {asset} - Subida insuficiente: {total_rise:.1f} puntos (mínimo: {min_momentum_points})")
                return False
            
            # Calcular fuerza de la señal
            signal_strength = self.calculate_signal_strength(asset, current_rsi, direction, history, 0, overbought_level)
            
            if signal_strength < min_strength:
                self.logger.debug(f"📈 {asset} - Señal débil: {signal_strength:.0f}% (mínimo: {min_strength}%)")
                return False
            
            # Momentum válido
            self.logger.info(f"✅ {asset} - Momentum CALL confirmado: {history[0]:.1f} → {current_rsi:.1f}")
            self.logger.info(f"   Subida: {total_rise:.1f} puntos | Fuerza: {signal_strength:.0f}% | Cruce FRESCO ✓")
            return True
        
        return False
    
    def process_asset(self, asset):
        """Procesar señales para un activo - CON VALIDACIÓN DE MOMENTUM Y NIVELES DINÁMICOS"""
        # NUEVO: Verificar el total de trades activos en TODOS los activos
        total_active_trades = sum(len(trades) for trades in self.active_options.values())
        
        # Si ya tenemos el máximo de trades activos, no procesar más señales
        if total_active_trades >= MAX_SIMULTANEOUS_TRADES:
            # Solo logear cada cierto tiempo para no llenar los logs
            if hasattr(self, '_last_max_trades_log') and time.time() - self._last_max_trades_log < 60:
                return
            self.logger.debug(f"⏭️ {asset} - Señal ignorada: {total_active_trades} trades activos (máximo: {MAX_SIMULTANEOUS_TRADES})")
            self._last_max_trades_log = time.time()
            return
        
        # Verificar si hay órdenes activas para ESTE activo específico
        if len(self.active_options.get(asset, [])) > 0:
            return
        
        # Verificar tiempo desde última señal (1 hora)
        time_since_last = (datetime.now() - self.last_signal_time.get(asset, datetime.min)).total_seconds() / 60
        if time_since_last < self.min_time_between_signals:
            return
        
        # Obtener RSI actual
        current_rsi = self.get_rsi(asset)
        if current_rsi is None:
            return
        
        # Obtener configuración específica del activo
        group = get_asset_group(asset)
        oversold_level, overbought_level = get_rsi_levels_for_asset(asset)
        min_momentum_points = get_min_momentum_for_asset(asset)
        
        # NUEVO: Limpiar historial si el RSI ha estado en zona extrema por mucho tiempo
        if len(self.rsi_history[asset]) >= 3:
            # Verificar si todos los valores históricos están en zona extrema
            all_oversold = all(rsi <= oversold_level for rsi in self.rsi_history[asset])
            all_overbought = all(rsi >= overbought_level for rsi in self.rsi_history[asset])
            
            if (all_oversold and current_rsi <= oversold_level) or \
               (all_overbought and current_rsi >= overbought_level):
                # RSI ha estado en zona extrema por mucho tiempo, limpiar historial
                self.logger.debug(f"🔄 {asset} - Algebra Inversa en zona extrema por mucho tiempo, limpiando historial")
                self.rsi_history[asset].clear()
        
        # Actualizar historial de RSI
        self.rsi_history[asset].append(current_rsi)
        
        # Si no tenemos suficiente historial, esperar
        if len(self.rsi_history[asset]) < 3:
            self.logger.debug(f"📊 {asset} ({group}) - Construyendo historial Algebra Inversa: {len(self.rsi_history[asset])}/3")
            return
        
        # Detectar señales con validación de momentum
        signal = None
        
        # Verificar condiciones para PUT
        if current_rsi <= oversold_level:
            if self.has_valid_momentum(asset, current_rsi, "PUT", min_momentum_points):
                signal = "PUT"
                self.logger.info(f"🔴 {asset} ({group}) - Señal PUT con momentum válido (Algebra Inversa: {current_rsi:.2f} ≤ {oversold_level})")
            else:
                self.logger.debug(f"⏭️ {asset} ({group}) - Algebra Inversa en sobreventa ({current_rsi:.2f} ≤ {oversold_level}) pero sin señal válida")
        
        # Verificar condiciones para CALL
        elif current_rsi >= overbought_level:
            if self.has_valid_momentum(asset, current_rsi, "CALL", min_momentum_points):
                signal = "CALL"
                self.logger.info(f"🟢 {asset} ({group}) - Señal CALL con momentum válido (Algebra Inversa: {current_rsi:.2f} ≥ {overbought_level})")
            else:
                self.logger.debug(f"⏭️ {asset} ({group}) - Algebra Inversa en sobrecompra ({current_rsi:.2f} ≥ {overbought_level}) pero sin señal válida")
        
        # Si hay señal válida, operar
        if signal:
            # Log del estado de trades activos antes de abrir nueva posición
            self.logger.info(f"📊 Trades activos antes de abrir: {total_active_trades}/{MAX_SIMULTANEOUS_TRADES}")
            
            self.create_binary_option(asset, signal, current_rsi)
            self.last_signal_time[asset] = datetime.now()
            # Limpiar historial después de operar para esperar nueva tendencia
            self.rsi_history[asset].clear()
    
    def create_binary_option(self, asset, direction, rsi_value):
        """Crear una opción binaria"""
        # Calcular tamaño de posición específico para el activo
        bet_size = self.calculate_position_size(asset)
        
        # Verificar capital disponible
        current_balance = self.api_call_with_timeout(self.iqoption.get_balance)
        if current_balance is None or current_balance < bet_size:
            self.logger.warning(f"⚠️ Capital insuficiente para {asset}")
            return
        
        # Colocar orden
        order_id = self.place_option(asset, direction, bet_size)
        
        if order_id:
            # Registrar orden activa
            order_info = {
                "id": order_id,
                "type": direction,
                "asset": asset,
                "size": bet_size,
                "entry_time": datetime.now(),
                "expiry_time": datetime.now() + timedelta(minutes=self.expiry_minutes),
                "rsi": rsi_value,
                "balance_before": current_balance,  # Guardar balance antes
                "asset_group": get_asset_group(asset)  # Guardar grupo del activo
            }
            self.active_options[asset].append(order_info)
            
            # Log del total de trades activos después de abrir
            total_active_trades = sum(len(trades) for trades in self.active_options.values())
            self.logger.info(f"📝 Orden registrada para {asset} - Total trades activos: {total_active_trades}/{MAX_SIMULTANEOUS_TRADES}")
    
    def check_active_orders(self):
        """Verificar el estado de las órdenes activas"""
        current_time = datetime.now()
        
        for asset in list(self.active_options.keys()):
            remaining_orders = []
            
            for order in self.active_options[asset]:
                # Calcular tiempo desde expiración
                time_since_expiry = (current_time - order["expiry_time"]).total_seconds()
                
                # Si la orden expiró hace más de 15 segundos, procesarla
                if time_since_expiry > 45:
                    self.process_expired_order(asset, order)
                # Si expiró pero es muy reciente, esperar un poco más
                elif order["expiry_time"] <= current_time:
                    self.logger.debug(f"⏳ Orden {order['id']} expiró hace {time_since_expiry:.0f}s, esperando...")
                    remaining_orders.append(order)
                else:
                    remaining_orders.append(order)
            
            if remaining_orders:
                self.active_options[asset] = remaining_orders
            else:
                del self.active_options[asset]
    
    def verify_and_recalculate_daily_profit(self):
        """Verificar y recalcular el profit diario basado en el balance real"""
        current_balance = self.api_call_with_timeout(self.iqoption.get_balance)
        if current_balance is None:
            return
        
        # Calcular el profit real del día
        real_daily_profit = current_balance - self.day_start_balance
        
        # Si hay discrepancia significativa, ajustar
        if abs(real_daily_profit - self.daily_profit) > 1.0:
            self.logger.warning(f"⚠️ Discrepancia detectada en profit diario")
            self.logger.warning(f"   Calculado: ${self.daily_profit:,.2f}")
            self.logger.warning(f"   Real: ${real_daily_profit:,.2f}")
            self.logger.warning(f"   Ajustando al valor real...")
            self.daily_profit = real_daily_profit
    
    def process_expired_order(self, asset, order):
        """Procesar una orden expirada - VERSIÓN CORREGIDA"""
        try:
            self.logger.info(f"🔄 Verificando orden {order['id']}...")
            
            # Verificar tiempo desde expiración
            time_since_expiry = (datetime.now() - order["expiry_time"]).total_seconds()
            
            # Si es muy reciente, esperar
            if time_since_expiry < 45:
                self.logger.info(f"⏳ Orden muy reciente ({time_since_expiry:.0f}s), esperando...")
                return
            
            # Variables para resultado
            result_found = False
            win_status = None
            win_amount = 0
            profit_percent = 0
            
            # MÉTODO 1: Verificar en api.order_binary (MÁS CONFIABLE)
            if hasattr(self.iqoption.api, 'order_binary') and order['id'] in self.iqoption.api.order_binary:
                order_data = self.iqoption.api.order_binary[order['id']]
                self.logger.info(f"📋 Orden encontrada en order_binary")
                
                # Leer el resultado directamente
                if 'result' in order_data:
                    result = order_data['result'].lower()
                    profit_percent = order_data.get('profit_percent', 85)
                    
                    if result == 'win':
                        win_status = 'win'
                        # CORRECCIÓN: win_amount es solo la ganancia neta
                        win_amount = order["size"] * (profit_percent / 100)
                        result_found = True
                        self.logger.info(f"   Result: WIN (profit: {profit_percent}%)")
                    elif result == 'loose':
                        win_status = 'loose'
                        win_amount = 0
                        result_found = True
                        self.logger.info(f"   Result: LOOSE")
                    elif result == 'equal':
                        win_status = 'equal'
                        win_amount = 0  # En empate no hay ganancia ni pérdida
                        result_found = True
                        self.logger.info(f"   Result: EQUAL")
            
            # MÉTODO 2: Verificar en api.listinfodata
            if not result_found and hasattr(self.iqoption.api, 'listinfodata') and isinstance(self.iqoption.api.listinfodata, dict):
                self.logger.debug("📋 Buscando en listinfodata...")
                for key, value in self.iqoption.api.listinfodata.items():
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and str(item.get('id')) == str(order['id']):
                                result_found = True
                                win_status = str(item.get('win', '')).lower()
                                win_amount_raw = float(item.get('win_amount', 0))
                                
                                # Determinar si win_amount incluye la inversión
                                if win_status == 'win' and win_amount_raw > order["size"]:
                                    # win_amount incluye la inversión
                                    win_amount = win_amount_raw - order["size"]
                                else:
                                    # win_amount es solo la ganancia
                                    win_amount = win_amount_raw
                                
                                self.logger.info(f"📋 Orden encontrada en listinfodata:")
                                self.logger.info(f"   Win: {win_status}")
                                self.logger.info(f"   Win Amount: {win_amount_raw}")
                                break
                    if result_found:
                        break
            
            # MÉTODO 3: Verificar por balance (para cuentas REAL)
            if not result_found and 'balance_before' in order and time_since_expiry > 90:  # Solo después de 90s
                current_balance = self.api_call_with_timeout(self.iqoption.get_balance)
                if current_balance is not None:
                    balance_diff = current_balance - order['balance_before']
                    
                    self.logger.info(f"📊 Verificación por balance:")
                    self.logger.info(f"   Balance antes: ${order['balance_before']:,.2f}")
                    self.logger.info(f"   Balance ahora: ${current_balance:,.2f}")
                    self.logger.info(f"   Diferencia: ${balance_diff:+,.2f}")
                    
                    # Solo usar balance si hay cambio significativo
                    if abs(balance_diff) > 0.1:
                        if balance_diff > 0:
                            win_status = 'win'
                            win_amount = balance_diff
                            result_found = True
                        else:
                            win_status = 'loose'
                            win_amount = 0
                            result_found = True
            
            # MÉTODO 4: Intentar get_async_order como último recurso
            if not result_found and time_since_expiry > 20:
                self.logger.info("📋 Intentando get_async_order...")
                order_result = self.api_call_with_timeout(
                    self.iqoption.get_async_order,
                    order["id"],
                    timeout=3
                )
                
                if order_result and isinstance(order_result, dict):
                    # Procesar con la lógica original
                    self._process_order_result(asset, order, order_result)
                    return
            
            # Procesar resultado si se encontró
            if result_found and win_status:
                bet_size = order["size"]
                
                if win_status == 'win':
                    self.logger.info(f"✅ Victoria detectada")
                    self.process_win(asset, order, win_amount)
                elif win_status == 'equal':
                    self.logger.info(f"🟡 Empate detectado")
                    self.process_tie(asset, order)
                elif win_status == 'loose':
                    self.logger.info(f"❌ Pérdida detectada")
                    self.process_loss(asset, order)
                else:
                    # Si no podemos determinar, verificar por monto
                    if win_amount > 0:
                        self.process_win(asset, order, win_amount)
                    elif win_amount == 0:
                        self.process_loss(asset, order)
                    else:
                        self.process_loss(asset, order)
                
                # Verificar y ajustar profit diario después de procesar
                self.verify_and_recalculate_daily_profit()
                return
            
            # Si han pasado más de 2 minutos y no hay resultado, asumir pérdida
            if time_since_expiry > 120:
                self.logger.error(f"❌ No se pudo verificar orden después de {time_since_expiry:.0f}s")
                self.logger.error(f"❌ Asumiendo pérdida por timeout")
                self.process_loss(asset, order)
                
        except Exception as e:
            self.logger.error(f"❌ Error procesando orden expirada: {str(e)}")
            self.logger.error(f"Detalles: {traceback.format_exc()}")
            # En caso de error, registrar como pérdida para ser conservadores
            self.process_loss(asset, order)
    
    def _process_order_result(self, asset, order, order_result):
        """Procesar resultado de orden desde get_async_order"""
        bet_size = order["size"]
        is_win = False
        is_tie = False
        win_amount = 0
        
        # Log detallado
        for key, value in order_result.items():
            self.logger.info(f"   {key}: {value}")
        
        # Método 1: Campo 'win' directo
        if "win" in order_result:
            win_status = str(order_result["win"]).lower()
            self.logger.info(f"   Campo 'win' encontrado: {win_status}")
            
            if win_status == "win":
                is_win = True
                # Buscar el monto ganado
                if "win_amount" in order_result:
                    win_amount_raw = float(order_result["win_amount"])
                    # Verificar si incluye la inversión
                    if win_amount_raw > bet_size:
                        win_amount = win_amount_raw - bet_size
                    else:
                        win_amount = win_amount_raw
                elif "profit_amount" in order_result:
                    win_amount = float(order_result["profit_amount"])
                else:
                    # Asumir 80% payout
                    win_amount = bet_size * 0.80
                    
            elif win_status == "equal":
                is_tie = True
                win_amount = 0
            else:
                is_win = False
                win_amount = 0
        
        # Método 2: Otros campos
        elif "win_amount" in order_result:
            win_amount_raw = float(order_result.get("win_amount", 0))
            if win_amount_raw > bet_size:
                is_win = True
                win_amount = win_amount_raw - bet_size
            elif win_amount_raw == bet_size:
                is_tie = True
                win_amount = 0
            else:
                is_win = False
                win_amount = 0
        
        # Procesar según resultado
        if is_win:
            self.process_win(asset, order, win_amount)
        elif is_tie:
            self.process_tie(asset, order)
        else:
            self.process_loss(asset, order)
    
    def process_win(self, asset, order, win_amount):
        """Procesar una operación ganadora - VERSIÓN CON LÓGICA 2 CONSECUTIVAS"""
        # win_amount ahora es SOLO la ganancia neta (no incluye la inversión)
        profit = win_amount
        group = order.get('asset_group', get_asset_group(asset))
        
        # Log del estado de trades activos
        total_active_trades = sum(len(trades) for trades in self.active_options.values())
        self.logger.info(f"✅ {asset} ({group}) - {order['type']} GANADA! Beneficio: {format_currency(profit)}")
        self.logger.info(f"📊 Trades activos restantes: {total_active_trades - 1}/{MAX_SIMULTANEOUS_TRADES}")
        
        self.wins[asset] += 1
        self.total_profit += profit
        self.daily_profit += profit
        self.consecutive_losses[asset] = 0
        
        # Actualizar consecutivas diarias
        self.daily_consecutive_wins += 1
        self.daily_consecutive_losses = 0
        
        # Agregar al historial reciente
        self.recent_results.append('win')
        
        self.logger.info(f"📊 Victorias consecutivas del día: {self.daily_consecutive_wins}/{self.max_daily_consecutive}")
        
        # Verificar si alcanzamos el límite
        if self.daily_consecutive_wins >= self.max_daily_consecutive and not self.daily_lock:
            self.activate_daily_lock("wins")
    
    def process_tie(self, asset, order):
        """Procesar una operación empatada (On The Money)"""
        group = order.get('asset_group', get_asset_group(asset))
        
        # Log del estado de trades activos
        total_active_trades = sum(len(trades) for trades in self.active_options.values())
        self.logger.info(f"🟡 {asset} ({group}) - {order['type']} EMPATE (On The Money). Sin ganancia ni pérdida")
        self.logger.info(f"📊 Trades activos restantes: {total_active_trades - 1}/{MAX_SIMULTANEOUS_TRADES}")
        
        # En un empate no se cuentan pérdidas ni victorias consecutivas
        self.ties[asset] += 1
        # Los empates NO afectan las consecutivas ni agregan al historial
        # Solo registramos para estadísticas
    
    def process_loss(self, asset, order):
        """Procesar una operación perdedora - VERSIÓN CON LÓGICA 2 CONSECUTIVAS"""
        loss = order["size"]
        group = order.get('asset_group', get_asset_group(asset))
        
        # Log del estado de trades activos
        total_active_trades = sum(len(trades) for trades in self.active_options.values())
        self.logger.info(f"❌ {asset} ({group}) - {order['type']} PERDIDA. Pérdida: {format_currency(loss)}")
        self.logger.info(f"📊 Trades activos restantes: {total_active_trades - 1}/{MAX_SIMULTANEOUS_TRADES}")
        
        self.losses[asset] += 1
        self.total_profit -= loss
        self.daily_profit -= loss
        self.consecutive_losses[asset] += 1
        
        # Actualizar consecutivas diarias
        self.daily_consecutive_losses += 1
        self.daily_consecutive_wins = 0
        
        # Agregar al historial reciente
        self.recent_results.append('loss')
        
        self.logger.info(f"📊 {asset} - Pérdidas consecutivas: {self.consecutive_losses[asset]}")
        self.logger.info(f"📊 Pérdidas consecutivas del día: {self.daily_consecutive_losses}/{self.max_daily_consecutive}")
        
        # Verificar si alcanzamos el límite
        if self.daily_consecutive_losses >= self.max_daily_consecutive and not self.daily_lock:
            self.activate_daily_lock("losses")
        
        # Guardar estado después de cada pérdida
        self.save_state()
    
    def activate_daily_lock(self, reason):
        """Activar el bloqueo diario por 2 consecutivas"""
        self.daily_lock = True
        self.daily_lock_time = datetime.now()
        self.daily_lock_reason = reason
        
        # Obtener balance actual para mostrar
        current_balance = self.api_call_with_timeout(self.iqoption.get_balance)
        
        self.logger.info("=" * 60)
        if reason == "wins":
            self.logger.info("🎯 2 VICTORIAS CONSECUTIVAS - TRADING PAUSADO")
            self.logger.info("=" * 60)
            self.logger.info(f"✅ Victorias consecutivas: {self.daily_consecutive_wins}")
        else:
            self.logger.info("❌ 2 PÉRDIDAS CONSECUTIVAS - TRADING PAUSADO")
            self.logger.info("=" * 60)
            self.logger.info(f"❌ Pérdidas consecutivas: {self.daily_consecutive_losses}")
        
        self.logger.info(f"💰 Profit del día: {format_currency(self.daily_profit)}")
        self.logger.info(f"📊 Balance actual: {format_currency(current_balance)}")
        self.logger.info(f"🕐 Hora: {self.daily_lock_time.strftime('%H:%M:%S')}")
        self.logger.info("🛑 No se realizarán más operaciones hoy")
        self.logger.info("🔄 El trading se reanudará mañana")
        self.logger.info("=" * 60)
    
    def check_daily_lock(self):
        """Verificar si debemos parar de operar por 2 consecutivas (wins o losses)"""
        # Si ya está activado el lock, solo mostrar mensaje periódicamente
        if self.daily_lock:
            if time.time() % 600 < 15:  # Cada 10 minutos aproximadamente
                if self.daily_lock_reason == "wins":
                    self.logger.info(f"🔒 Trading pausado - {self.daily_consecutive_wins} victorias consecutivas")
                else:
                    self.logger.info(f"🔒 Trading pausado - {self.daily_consecutive_losses} pérdidas consecutivas")
            time.sleep(15)
            return True
        
        # No hacer check si hay posiciones abiertas
        if len(self.active_options) > 0:
            return False
        
        return False
    
    def check_stop_loss(self):
        """Verificar condiciones de stop loss"""
        current_capital = self.api_call_with_timeout(self.iqoption.get_balance)
        if current_capital is None:
            return True
        
        # Actualizar capital mínimo
        if current_capital < self.min_capital:
            self.min_capital = current_capital
            loss_percent = ((self.initial_capital - self.min_capital) / self.initial_capital) * 100
            self.logger.info(f"📉 Nuevo mínimo: {format_currency(self.min_capital)} ({loss_percent:.2f}% pérdida)")
        
        # Stop loss absoluto
        if current_capital <= self.absolute_stop_loss_threshold and not self.absolute_stop_loss_activated:
            self.absolute_stop_loss_activated = True
            self.logger.critical("🚨 STOP LOSS ABSOLUTO ACTIVADO!")
            self.logger.critical(f"Capital: {format_currency(current_capital)} (75% de pérdida)")
            return False
        
        if self.absolute_stop_loss_activated:
            return False
        
        # Stop loss mensual
        current_month = f"{datetime.now().year}-{datetime.now().month:02d}"
        
        if self.current_month != current_month:
            self.on_new_month(current_month, current_capital)
        
        if self.monthly_stop_loss and self.stop_loss_triggered_month == current_month:
            return False
        
        monthly_start = self.monthly_starting_capital.get(current_month, self.initial_capital)
        monthly_threshold = monthly_start * (1 - MONTHLY_STOP_LOSS_PERCENT)
        
        if current_capital <= monthly_threshold and not self.monthly_stop_loss:
            self.monthly_stop_loss = True
            self.stop_loss_triggered_month = current_month
            self.logger.critical("🚨 STOP LOSS MENSUAL ACTIVADO!")
            self.logger.critical(f"Pérdida del mes: 40%")
            return False
        
        return True
    
    def on_new_day(self):
        """Resetear variables diarias"""
        self.logger.info("🌅 Reseteando variables para nuevo día de trading")
        
        # Guardar balance del día anterior para tracking
        current_balance = self.api_call_with_timeout(self.iqoption.get_balance)
        if current_balance is not None:
            self.day_start_balance = current_balance
        
        # Resetear daily lock
        if self.daily_lock:
            if self.daily_lock_reason == "wins":
                self.logger.info(f"🔓 Desbloqueando trading - {self.daily_consecutive_wins} victorias consecutivas del día anterior")
            else:
                self.logger.info(f"🔓 Desbloqueando trading - {self.daily_consecutive_losses} pérdidas consecutivas del día anterior")
            self.daily_lock = False
            self.daily_lock_time = None
            self.daily_lock_reason = None
        
        # Resetear contadores de consecutivas
        self.daily_consecutive_wins = 0
        self.daily_consecutive_losses = 0
        self.recent_results.clear()
        
        # Resetear pérdidas consecutivas por activo
        for asset in list(self.consecutive_losses.keys()):
            if self.consecutive_losses[asset] > 0:
                self.logger.info(f"✅ Reseteando pérdidas consecutivas de {asset}: {self.consecutive_losses[asset]} → 0")
            self.consecutive_losses[asset] = 0
        
        # Actualizar beneficios mensuales
        if self.last_date:
            month_key = f"{self.last_date.year}-{self.last_date.month:02d}"
            self.monthly_profits[month_key] += self.daily_profit
        
        self.daily_profit = 0
        self.last_date = datetime.now().date()
        self.logger.info("✅ Variables diarias reseteadas")
    
    def on_new_month(self, new_month, current_capital):
        """Manejar cambio de mes"""
        self.logger.info(f"📅 NUEVO MES: {new_month}")
        self.monthly_starting_capital[new_month] = current_capital
        self.current_month = new_month
        
        # Resetear stop loss mensual si aplica
        if self.monthly_stop_loss:
            self.monthly_stop_loss = False
            self.stop_loss_triggered_month = None
            self.logger.info("✅ Stop loss mensual reseteado")
    
    def save_state(self):
        """Guardar estado actual de la estrategia"""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "strategy_mode": STRATEGY_MODE,
                "active_options": {
                    asset: [
                        {
                            **order,
                            "entry_time": order["entry_time"].isoformat(),
                            "expiry_time": order["expiry_time"].isoformat()
                        }
                        for order in orders
                    ]
                    for asset, orders in self.active_options.items()
                },
                "last_signal_time": {
                    asset: time.isoformat() if time != datetime.min else "datetime.min"
                    for asset, time in self.last_signal_time.items()
                },
                "consecutive_losses": dict(self.consecutive_losses),
                "daily_lockouts": dict(self.daily_lockouts),
                "wins": dict(self.wins),
                "losses": dict(self.losses),
                "ties": dict(self.ties),  # Guardar empates
                "total_profit": self.total_profit,
                "daily_profit": self.daily_profit,
                "monthly_profits": dict(self.monthly_profits),
                "monthly_starting_capital": self.monthly_starting_capital,
                "monthly_stop_loss": self.monthly_stop_loss,
                "stop_loss_triggered_month": self.stop_loss_triggered_month,
                "absolute_stop_loss_activated": self.absolute_stop_loss_activated,
                "min_capital": self.min_capital,
                "last_date": self.last_date.isoformat() if self.last_date else None,
                "current_month": self.current_month,
                "daily_consecutive_wins": self.daily_consecutive_wins,
                "daily_consecutive_losses": self.daily_consecutive_losses,
                "daily_lock": self.daily_lock,
                "daily_lock_time": self.daily_lock_time.isoformat() if self.daily_lock_time else None,
                "daily_lock_reason": self.daily_lock_reason,
                "max_daily_consecutive": self.max_daily_consecutive,
                "recent_results": list(self.recent_results),
                "day_start_balance": self.day_start_balance,
                # Guardar historial de RSI
                "rsi_history": {asset: list(history) for asset, history in self.rsi_history.items()},
                "aggressiveness_mode": self.custom_aggressiveness or AGGRESSIVENESS_MODE  # Guardar modo actual (personalizado o por defecto)
            }
            
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=4)
            
            self.logger.debug("💾 Estado guardado correctamente")
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando estado: {str(e)}")
    
    def load_state(self):
        """Cargar estado previo si existe"""
        try:
            if not os.path.exists(STATE_FILE):
                self.logger.info("📂 No hay archivo de estado previo")
                self.last_date = datetime.now().date()
                self.current_month = f"{datetime.now().year}-{datetime.now().month:02d}"
                self.monthly_starting_capital[self.current_month] = self.initial_capital
                return
            
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            
            # Verificar si el modo de agresividad cambió
            saved_mode = state.get("aggressiveness_mode", None)
            current_mode = self.custom_aggressiveness or AGGRESSIVENESS_MODE
            if saved_mode and saved_mode != current_mode:
                self.logger.warning(f"⚠️ Modo de agresividad cambió: {saved_mode} → {current_mode}")
                self.logger.warning("   Limpiando historial Algebra Inversa para adaptarse al nuevo modo")
                # No cargar historial RSI si cambió el modo
                state["rsi_history"] = {}
            
            # Cargar órdenes activas
            self.active_options = defaultdict(list)
            for asset, orders in state.get("active_options", {}).items():
                for order in orders:
                    order["entry_time"] = datetime.fromisoformat(order["entry_time"])
                    order["expiry_time"] = datetime.fromisoformat(order["expiry_time"])
                    # Compatibilidad: cambiar 'pair' a 'asset' si existe
                    if 'pair' in order and 'asset' not in order:
                        order['asset'] = order.pop('pair')
                    self.active_options[asset].append(order)
            
            # Cargar tiempos de última señal
            self.last_signal_time = defaultdict(lambda: datetime.min)
            for asset, time_str in state.get("last_signal_time", {}).items():
                if time_str == "datetime.min":
                    self.last_signal_time[asset] = datetime.min
                else:
                    self.last_signal_time[asset] = datetime.fromisoformat(time_str)
            
            # Cargar estadísticas
            self.consecutive_losses = defaultdict(int, state.get("consecutive_losses", {}))
            self.daily_lockouts = defaultdict(bool, state.get("daily_lockouts", {}))
            self.wins = defaultdict(int, state.get("wins", {}))
            self.losses = defaultdict(int, state.get("losses", {}))
            self.ties = defaultdict(int, state.get("ties", {}))  # Cargar empates
            self.total_profit = state.get("total_profit", 0)
            self.daily_profit = state.get("daily_profit", 0)
            self.monthly_profits = defaultdict(float, state.get("monthly_profits", {}))
            self.monthly_starting_capital = state.get("monthly_starting_capital", {})
            self.monthly_stop_loss = state.get("monthly_stop_loss", False)
            self.stop_loss_triggered_month = state.get("stop_loss_triggered_month", None)
            self.absolute_stop_loss_activated = state.get("absolute_stop_loss_activated", False)
            self.min_capital = state.get("min_capital", self.initial_capital)
            self.day_start_balance = state.get("day_start_balance", self.initial_capital)
            
            # Cargar daily lock
            self.daily_consecutive_wins = state.get("daily_consecutive_wins", 0)
            self.daily_consecutive_losses = state.get("daily_consecutive_losses", 0)
            self.daily_lock = state.get("daily_lock", False)
            lock_time = state.get("daily_lock_time")
            if lock_time:
                self.daily_lock_time = datetime.fromisoformat(lock_time)
            else:
                self.daily_lock_time = None
            self.daily_lock_reason = state.get("daily_lock_reason", None)
            self.max_daily_consecutive = state.get("max_daily_consecutive", 2)
            
            # Cargar historial reciente
            recent_results_data = state.get("recent_results", [])
            self.recent_results = deque(recent_results_data, maxlen=2)
            
            # Cargar historial de RSI
            rsi_history_data = state.get("rsi_history", {})
            for asset, history in rsi_history_data.items():
                self.rsi_history[asset] = deque(history, maxlen=5)
            
            # Cargar fechas
            last_date_str = state.get("last_date")
            if last_date_str:
                self.last_date = datetime.fromisoformat(last_date_str).date()
            else:
                self.last_date = datetime.now().date()
            
            self.current_month = state.get("current_month", f"{datetime.now().year}-{datetime.now().month:02d}")
            
            self.logger.info(f"✅ Estado cargado desde {state.get('timestamp', 'N/A')}")
            
        except Exception as e:
            self.logger.error(f"❌ Error cargando estado: {str(e)}")
            self.last_date = datetime.now().date()
            self.current_month = f"{datetime.now().year}-{datetime.now().month:02d}"
            self.monthly_starting_capital[self.current_month] = self.initial_capital
    
    def print_summary(self):
        """Imprimir resumen de la estrategia"""
        current_capital = self.api_call_with_timeout(self.iqoption.get_balance)
        if current_capital is None:
            current_capital = self.initial_capital
        
        self.logger.info("=" * 60)
        self.logger.info("📊 RESUMEN DE LA ESTRATEGIA ALGEBRA MULTI-ACTIVOS (LÓGICA INVERTIDA)")
        self.logger.info("=" * 60)
        self.logger.info("⚡ Estrategia: PUT en sobreventa (Algebra Inversa dinámico), CALL en sobrecompra (Algebra Inversa dinámico)")
        self.logger.info(f"⚙️ Modo: {AGGRESSIVENESS_MODE} - {ACTIVE_CONFIG['description']}")
        self.logger.info(f"🎯 Límite de trades simultáneos: {MAX_SIMULTANEOUS_TRADES}")
        self.logger.info(f"💰 Capital Inicial: {format_currency(self.initial_capital)}")
        self.logger.info(f"💰 Balance Final: {format_currency(current_capital)}")
        
        total_return = ((current_capital - self.initial_capital) / self.initial_capital) * 100
        self.logger.info(f"📈 Rendimiento Total: {total_return:.2f}%")
        
        # Estadísticas por operaciones
        total_wins = sum(self.wins.values())
        total_losses = sum(self.losses.values())
        total_ties = sum(self.ties.values())
        total_trades = total_wins + total_losses + total_ties
        
        self.logger.info(f"🎯 Total Operaciones: {total_trades}")
        if total_trades > 0:
            win_rate = calculate_win_rate(total_wins, total_losses)
            self.logger.info(f"✅ Victorias: {total_wins} ({total_wins/total_trades*100:.1f}%)")
            self.logger.info(f"❌ Derrotas: {total_losses} ({total_losses/total_trades*100:.1f}%)")
            self.logger.info(f"🟡 Empates: {total_ties} ({total_ties/total_trades*100:.1f}%)")
            self.logger.info(f"📊 Tasa de Éxito (sin empates): {win_rate:.2f}%")
        
        self.logger.info(f"💵 Beneficio Neto: {format_currency(self.total_profit)}")
        self.logger.info(f"📉 Capital Mínimo: {format_currency(self.min_capital)}")
        
        # Stop losses activados
        if self.absolute_stop_loss_activated:
            self.logger.info("🚨 Stop Loss Absoluto: ACTIVADO")
        if self.monthly_stop_loss:
            self.logger.info(f"🚨 Stop Loss Mensual: ACTIVADO en {self.stop_loss_triggered_month}")
        
        # Daily lock
        if self.daily_lock:
            if self.daily_lock_reason == "wins":
                self.logger.info(f"🔒 Daily Lock: ACTIVO desde {self.daily_lock_time.strftime('%H:%M')} ({self.daily_consecutive_wins} victorias)")
            else:
                self.logger.info(f"🔒 Daily Lock: ACTIVO desde {self.daily_lock_time.strftime('%H:%M')} ({self.daily_consecutive_losses} pérdidas)")
        
        # Estadísticas por activo agrupadas por tipo
        self.logger.info("\n📊 Estadísticas por Activo (agrupadas por tipo):")
        
        # Agrupar activos por tipo
        groups_stats = defaultdict(list)
        for asset in self.trading_assets:
            if asset in self.wins or asset in self.losses or asset in self.ties:
                asset_wins = self.wins.get(asset, 0)
                asset_losses = self.losses.get(asset, 0)
                asset_ties = self.ties.get(asset, 0)
                asset_total = asset_wins + asset_losses + asset_ties
                if asset_total > 0:
                    group = get_asset_group(asset)
                    groups_stats[group].append({
                        'asset': asset,
                        'wins': asset_wins,
                        'losses': asset_losses,
                        'ties': asset_ties,
                        'total': asset_total,
                        'win_rate': (asset_wins / (asset_wins + asset_losses) * 100) if (asset_wins + asset_losses) > 0 else 0,
                        'cons_losses': self.consecutive_losses.get(asset, 0)
                    })
        
        # Mostrar por grupo
        for group in ["FOREX", "INDEX", "STOCK", "COMMODITY", "CRYPTO", "PAIR", "DEFAULT"]:
            if group in groups_stats:
                self.logger.info(f"\n{group}:")
                for stat in groups_stats[group]:
                    self.logger.info(f"  {stat['asset']}: {stat['total']} trades | {stat['wins']}W/{stat['losses']}L/{stat['ties']}T | {stat['win_rate']:.1f}% éxito | Pérdidas consec: {stat['cons_losses']}")
        
        # Rendimiento mensual
        self.logger.info("\n📅 Rendimiento Mensual:")
        for month in sorted(self.monthly_profits.keys()):
            monthly_profit = self.monthly_profits[month]
            tag = " (STOP LOSS)" if month == self.stop_loss_triggered_month else ""
            self.logger.info(f"{month}: {format_currency(monthly_profit)}{tag}")
        
        self.logger.info("=" * 60)
    
    def run(self):
        """Ejecutar la estrategia principal"""
        # Obtener configuración activa (personalizada o por defecto)
        active_config, active_mode = self.get_aggressiveness_config()
        
        self.logger.info("🚀 Iniciando estrategia ALGEBRA Multi-Activos (LÓGICA INVERTIDA)")
        self.logger.info(f"📊 Configuración: {len(self.valid_assets)} activos disponibles")
        mode_display = f"{active_mode} (personalizado)" if self.custom_aggressiveness else active_mode
        self.logger.info(f"⚙️ Modo: {mode_display} - {active_config['description']}")
        self.logger.info(f"📊 Algebra Inversa en timeframe de {self.candle_timeframe//60} minutos")
        self.logger.info(f"⏱️ Expiración de opciones: {self.expiry_minutes} minutos")
        self.logger.info(f"⏰ Tiempo entre señales: {self.min_time_between_signals} minutos")
        self.logger.info(f"🔄 Bloqueo diario después de {self.max_daily_consecutive} operaciones consecutivas (wins o losses)")
        self.logger.info(f"🎯 Máximo {MAX_SIMULTANEOUS_TRADES} trade(s) simultáneo(s)")
        self.logger.info(f"💪 Fuerza mínima de señal: {active_config['min_strength']}%")
        self.logger.info(f"🆕 Solo cruces frescos en últimas {active_config.get('max_candles_for_cross', 2)} niveles dinámicos")
        
        cycle_count = 0
        
        try:
            while True:
                cycle_start = time.time()
                cycle_count += 1
                
                # Log periódico del estado de trades
                if cycle_count % 10 == 0:
                    total_active_trades = sum(len(trades) for trades in self.active_options.values())
                    self.logger.info(f"🔄 Ciclo #{cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Trades activos: {total_active_trades}/{MAX_SIMULTANEOUS_TRADES}")
                
                # Verificar conexión
                if not self.iqoption.check_connect():
                    self.logger.warning("🔌 Reconectando...")
                    self._connect_to_iq_option(IQ_EMAIL, IQ_PASSWORD, ACCOUNT_TYPE)
                    time.sleep(5)
                    continue
                
                # Verificar stop loss
                if not self.check_stop_loss():
                    self.logger.info("🛑 Stop loss activo. Esperando...")
                    time.sleep(300)  # Esperar 5 minutos
                    continue
                
                # Verificar daily lock (2 consecutivas)
                if self.check_daily_lock():
                    continue
                
                # Verificar órdenes activas
                self.check_active_orders()
                
                # Verificar nuevo día
                current_date = datetime.now().date()
                if self.last_date != current_date:
                    self.on_new_day()
                
                # Procesar cada activo disponible
                for asset in self.valid_assets:
                    try:
                        self.process_asset(asset)
                    except Exception as e:
                        self.logger.error(f"❌ Error procesando {asset}: {str(e)}")
                
                # Guardar estado periódicamente
                if cycle_count % SAVE_STATE_INTERVAL == 0:
                    self.save_state()
                
                # Re-verificar activos periódicamente
                if cycle_count % 100 == 0:
                    self.logger.info("🔄 Re-verificando activos disponibles...")
                    self.check_valid_assets()
                
                # Control de tiempo del ciclo
                cycle_duration = time.time() - cycle_start
                sleep_time = max(5.0, 15.0 - cycle_duration)  # Mínimo 5 segundos entre ciclos
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.logger.info("⏹️ Estrategia detenida por el usuario")
        except Exception as e:
            self.logger.critical(f"🚨 Error crítico: {str(e)}")
            self.logger.critical(traceback.format_exc())
        finally:
            self.logger.info("🏁 Finalizando estrategia...")
            self.save_state()
            self.print_summary()
            
            # Cerrar executor
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True)
            
            self.logger.info("👋 Estrategia finalizada")
    
    def __del__(self):
        """Limpieza al destruir el objeto"""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
        except:
            pass


# Alias para compatibilidad con main.py
MultiCurrencyRSIBinaryOptionsStrategy = MultiAssetRSIBinaryOptionsStrategy