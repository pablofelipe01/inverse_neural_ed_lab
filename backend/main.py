# main.py
# Punto de entrada principal para la estrategia RSI en IQ Option

import sys
import argparse
import logging
from datetime import datetime

from config import IQ_EMAIL, IQ_PASSWORD, ACCOUNT_TYPE, LOG_FILE
from strategy import MultiAssetRSIBinaryOptionsStrategy
from utils import setup_logger

def main():
    """Función principal para ejecutar la estrategia"""
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Estrategia Algebra Multi-Activos para Option')
    parser.add_argument('--email', type=str, help='Email de IQ Option (sobrescribe config)')
    parser.add_argument('--password', type=str, help='Contraseña de IQ Option (sobrescribe config)')
    parser.add_argument('--account', type=str, choices=['PRACTICE', 'REAL'], 
                       default=ACCOUNT_TYPE, help='Tipo de cuenta a usar')
    parser.add_argument('--test', action='store_true', help='Ejecutar en modo prueba')
    parser.add_argument('--debug-assets', action='store_true', 
                       help='Mostrar todos los activos disponibles y salir')
    parser.add_argument('--check-order', type=str, 
                       help='Verificar el resultado de una orden específica por ID')
    parser.add_argument('--check-recent', action='store_true',
                       help='Verificar resultados de órdenes recientes')
    parser.add_argument('--pairs', nargs='+', 
                       help='Pares específicos para operar (ej: --pairs NVDA/AMD TESLA/FORD)')
    parser.add_argument('--crypto', nargs='+', 
                       help='Crypto específicos para operar (ej: --crypto BTCUSD ETHUSD)')
    parser.add_argument('--position-size', type=int,
                       help='Tamaño de posición en porcentaje (1-15)')
    parser.add_argument('--pairs-position-size', type=int,
                       help='Tamaño de posición para pares en porcentaje (1-15)')
    parser.add_argument('--crypto-position-size', type=int,
                       help='Tamaño de posición para crypto en porcentaje (1-5)')
    parser.add_argument('--aggressiveness', choices=['conservador', 'balanceado', 'agresivo'],
                       help='Nivel de agresividad del algoritmo')
    
    args = parser.parse_args()
    
    # Usar credenciales de argumentos o de config
    email = args.email or IQ_EMAIL
    password = args.password or IQ_PASSWORD
    account_type = args.account
    
    # Verificar credenciales
    if not email or not password or email == "tu_email@example.com":
        print("❌ ERROR: Por favor configura tus credenciales en config.py o pásalas como argumentos")
        print("Uso: python main.py --email tu_email@example.com --password tu_password")
        sys.exit(1)
    
    # Configurar logger principal
    logger = setup_logger('main', LOG_FILE)
    
    # Banner de inicio
    logger.info("=" * 60)
    logger.info("   ESTRATEGIA ALGEBRA MULTI-ACTIVOS PARA OPTION")
    logger.info("   ⚡ LÓGICA INVERTIDA ⚡")
    logger.info("=" * 60)
    logger.info(f"📅 Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📧 Usuario: {email[:3]}***{email[-10:]}")  # Ocultar parte del email
    logger.info("=" * 60)
    logger.info("⚠️ IMPORTANTE: Esta estrategia usa lógica INVERTIDA")
    logger.info("   - PUT cuando Algebra Inversa ≤ 35 (sobreventa)")
    logger.info("   - CALL cuando Algebra Inversa ≥ 65 (sobrecompra)")
    logger.info("=" * 60)
    
    try:
        # Crear e inicializar la estrategia
        logger.info("🚀 Inicializando estrategia...")
        
        # Preparar parámetros adicionales
        strategy_params = {
            'email': email,
            'password': password,
            'account_type': account_type
        }
        
        # Agregar pares específicos si se proporcionaron
        if args.pairs:
            logger.info(f"🎯 Pares seleccionados: {', '.join(args.pairs)}")
            strategy_params['selected_pairs'] = args.pairs
        
        # Agregar crypto específicos si se proporcionaron
        if args.crypto:
            logger.info(f"🪙 Crypto seleccionados: {', '.join(args.crypto)}")
            strategy_params['selected_crypto'] = args.crypto
        
        # Agregar configuración adicional
        if args.position_size:
            logger.info(f"💰 Tamaño de posición (legacy): {args.position_size}%")
            strategy_params['position_size'] = args.position_size
        
        if args.pairs_position_size:
            logger.info(f"📊 Tamaño de posición pares: {args.pairs_position_size}%")
            strategy_params['pairs_position_size'] = args.pairs_position_size
        
        if args.crypto_position_size:
            logger.info(f"🪙 Tamaño de posición crypto: {args.crypto_position_size}%")
            strategy_params['crypto_position_size'] = args.crypto_position_size
        
        if args.aggressiveness:
            logger.info(f"⚡ Nivel de agresividad: {args.aggressiveness}")
            strategy_params['aggressiveness'] = args.aggressiveness
        
        strategy = MultiAssetRSIBinaryOptionsStrategy(**strategy_params)
        
        # Si es modo debug de activos
        if args.debug_assets:
            logger.info("🔍 MODO DEBUG: Mostrando todos los activos disponibles...")
            strategy.debug_show_all_available_assets()
            logger.info("✅ Debug completado. Revisa los logs para ver todos los activos.")
            return
        
        # Si queremos verificar una orden específica
        if args.check_order:
            logger.info(f"🔍 Verificando orden {args.check_order}...")
            strategy.test_check_order_result(args.check_order)
            logger.info("✅ Verificación completada.")
            return
        
        # Si queremos verificar órdenes recientes
        if args.check_recent:
            logger.info("🔍 Verificando órdenes recientes...")
            strategy.check_recent_orders_results()
            logger.info("✅ Verificación completada.")
            return
        
        if args.test:
            # Modo prueba: verificar conexión y mostrar información
            logger.info("🧪 MODO PRUEBA - Verificando configuración...")
            logger.info(f"✅ Conexión exitosa")
            logger.info(f"💰 Balance: ${strategy.initial_capital:,.2f}")
            logger.info(f"📊 Activos disponibles: {len(strategy.valid_assets)}")
            if strategy.valid_assets:
                logger.info("📋 Activos habilitados:")
                for asset in strategy.valid_assets[:10]:  # Mostrar hasta 10
                    iq_name = strategy.iqoption_assets[asset]
                    option_type = strategy.asset_option_types[asset]
                    logger.info(f"   - {asset} → {iq_name} ({option_type})")
            else:
                logger.warning("⚠️ No hay activos disponibles para operar")
                logger.info("💡 Ejecuta con --debug-assets para ver todos los activos disponibles")
            logger.info("✅ Prueba completada exitosamente")
            return
        
        # Ejecutar estrategia
        logger.info("🎯 Iniciando operaciones...")
        logger.info("ℹ️ Para detener la estrategia, desactiva el switch en el dashboard")
        strategy.run()
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Estrategia detenida por el usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {str(e)}")
        logger.error("Traceback completo:", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("👋 Programa finalizado")

if __name__ == "__main__":
    main()