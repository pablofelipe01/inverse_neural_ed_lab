from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import os
import signal
import time

app = FastAPI(title="Educational Trading Strategy API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development server
        "http://127.0.0.1:3000",  # Alternative localhost format
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Single process for educational use (instead of multi-user dictionary)
active_process = None

@app.get("/")
async def root():
    return {"message": "Educational Trading Strategy API is running"}

@app.get("/strategy/start")
async def start_strategy(pairs: str = None):
    global active_process
    
    if active_process is not None:
        # Verificar si el proceso aún está vivo
        if active_process.poll() is None:  # Proceso aún corriendo
            return {"error": "Strategy already running", "pid": active_process.pid}
        else:
            # Proceso murió, limpiarlo
            active_process = None
    
    try:
        # Preparar comando con pares seleccionados
        cmd = ['python3', 'main.py']
        
        # Si se especifican pares, agregarlos como argumento
        if pairs:
            # Los pares vienen como string separado por comas: "NVDA/AMD,TESLA/FORD,META/GOOGLE"
            selected_pairs = pairs.split(',')
            cmd.extend(['--pairs'] + selected_pairs)
        
        # Ejecutar main.py con los pares seleccionados
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Guardar referencia del proceso
        active_process = process
        
        return {
            "message": "Strategy started successfully",
            "pid": process.pid,
            "status": "running",
            "selected_pairs": selected_pairs if pairs else "all_pairs"
        }
        
    except Exception as e:
        return {"error": f"Failed to start strategy: {str(e)}"}

@app.post("/strategy/start")
async def start_strategy_post(request: Request):
    """
    Endpoint POST para recibir configuración completa desde el dashboard
    """
    global active_process
    
    if active_process is not None:
        if active_process.poll() is None:
            return {"error": "Strategy already running", "pid": active_process.pid}
        else:
            active_process = None
    
    try:
        # Obtener el payload JSON del request
        config = await request.json()
        print(f"🔧 Configuración recibida desde dashboard: {config}")
        
        cmd = ['python3', 'main.py']
        
        # Procesar configuración del dashboard
        if 'selectedPairs' in config and config['selectedPairs']:
            selected_pairs = config['selectedPairs']
            cmd.extend(['--pairs'] + selected_pairs)
            print(f"📊 Pares seleccionados: {selected_pairs}")
        
        # Procesar crypto assets
        if 'selectedCrypto' in config and config['selectedCrypto']:
            selected_crypto = config['selectedCrypto']
            cmd.extend(['--crypto'] + selected_crypto)
            print(f"🪙 Crypto seleccionados: {selected_crypto}")
            
        # Agregar credenciales IQ Option
        if 'email' in config and config['email']:
            cmd.extend(['--email', config['email']])
            print(f"📧 Email configurado: {config['email'][:3]}***{config['email'][-10:]}")  # Ocultar email parcialmente
            
        if 'password' in config and config['password']:
            cmd.extend(['--password', config['password']])
            print(f"🔒 Contraseña configurada: {'*' * len(config['password'])}")  # Ocultar contraseña completa
            
        if 'accountType' in config:
            cmd.extend(['--account', config['accountType']])
            print(f"🏦 Tipo de cuenta: {config['accountType']}")
            
        # Agregar tamaño de posición (legacy para compatibilidad)
        if 'positionSize' in config:
            cmd.extend(['--position-size', str(config['positionSize'])])
            print(f"💰 Tamaño de posición (legacy): {config['positionSize']}%")
        
        # Agregar tamaños de posición separados
        if 'pairsPositionSize' in config:
            cmd.extend(['--pairs-position-size', str(config['pairsPositionSize'])])
            print(f"📊 Tamaño de posición pares: {config['pairsPositionSize']}%")
        
        if 'cryptoPositionSize' in config:
            cmd.extend(['--crypto-position-size', str(config['cryptoPositionSize'])])
            print(f"🪙 Tamaño de posición crypto: {config['cryptoPositionSize']}%")
        
        # Agregar nivel de agresividad
        if 'aggressiveness' in config:
            cmd.extend(['--aggressiveness', config['aggressiveness']])
            print(f"⚡ Agresividad: {config['aggressiveness']}")
        
        print(f"🚀 Ejecutando comando: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        active_process = process
        
        return {
            "message": "Strategy started successfully",
            "pid": process.pid,
            "status": "running",
            "config": config
        }
        
    except Exception as e:
        print(f"❌ Error al iniciar estrategia: {str(e)}")
        return {"error": f"Failed to start strategy: {str(e)}"}

@app.get("/strategy/stop")
async def stop_strategy():
    global active_process
    
    if active_process is None:
        return {"error": "No active strategy running"}
    
    try:
        # Enviar SIGINT (equivalente a Ctrl+C)
        active_process.send_signal(signal.SIGINT)
        
        # Esperar un poco a que termine gracefully
        time.sleep(2)
        
        # Si aún está corriendo, forzar terminación
        if active_process.poll() is None:
            active_process.terminate()
            time.sleep(1)
            if active_process.poll() is None:
                active_process.kill()
        
        # Limpiar referencia
        active_process = None
        
        return {
            "message": "Strategy stopped successfully",
            "status": "stopped"
        }
        
    except Exception as e:
        return {"error": f"Failed to stop strategy: {str(e)}"}

@app.get("/strategy/status")
async def get_status():
    global active_process
    
    if active_process is None:
        return {"status": "stopped"}
    
    # Verificar si el proceso aún está vivo
    if active_process.poll() is None:
        return {
            "status": "running",
            "pid": active_process.pid
        }
    else:
        # Proceso murió, limpiar
        active_process = None
        return {"status": "stopped"}

@app.get("/health")
async def health_check():
    global active_process
    
    return {
        "status": "healthy",
        "strategy_running": active_process is not None and active_process.poll() is None,
        "process_info": {
            "pid": active_process.pid if active_process and active_process.poll() is None else None,
            "running": active_process.poll() is None if active_process else False
        } if active_process else None
    }

@app.get("/strategy/reset")
async def reset_strategy():
    """
    Resetea las estadísticas ejecutando reset_strategy.py
    CRUCIAL: Este endpoint es esencial para usuarios educativos
    """
    global active_process
    
    try:
        # Verificar si hay proceso activo
        if active_process is not None:
            if active_process.poll() is None:  # Proceso aún corriendo
                return {
                    "error": "Cannot reset while strategy is running. Stop the strategy first.",
                    "message": "Detén el algoritmo antes de hacer reset"
                }
        
        # Verificar que existe el archivo reset_strategy.py
        reset_script = "reset_strategy.py"
        if not os.path.exists(reset_script):
            return {
                "error": f"Reset script not found: {reset_script}",
                "message": "Script de reset no encontrado"
            }
        
        # Ejecutar reset_strategy.py con input automático 's'
        reset_process = subprocess.Popen(
            ['python3', reset_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Enviar ambas confirmaciones automáticamente:
        # 1. "¿Estás seguro de que quieres reiniciar la estrategia? (s/N):" -> 's'
        # 2. "¿Deseas también limpiar el archivo de log? (s/N):" -> 's'
        auto_input = 's\ns\n'
        stdout, stderr = reset_process.communicate(input=auto_input, timeout=30)
        
        if reset_process.returncode == 0:
            return {
                "success": True,
                "message": "Estadísticas reseteadas exitosamente",
                "output": stdout.strip() if stdout else "Reset completado"
            }
        else:
            return {
                "error": "Reset failed",
                "message": f"Error en el proceso de reset: {stderr or 'Error desconocido'}",
                "returncode": reset_process.returncode
            }
            
    except subprocess.TimeoutExpired:
        return {
            "error": "Reset timeout",
            "message": "El proceso de reset tardó demasiado tiempo"
        }
    except Exception as e:
        return {
            "error": f"Reset exception: {str(e)}",
            "message": f"Error inesperado durante el reset: {str(e)}"
        }

@app.get("/strategy/logs")
async def get_logs(limit: int = 50):
    """
    Obtiene los logs más recientes del proceso de trading para el sistema educacional
    """
    global active_process
    
    try:
        # Leer logs del archivo principal siempre (tanto si hay proceso como si no)
        log_file = "iqoption_strategy.log"
        logs = []
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                # Tomar las últimas 'limit' líneas
                recent_lines = lines[-limit:] if len(lines) > limit else lines
                
                for line in recent_lines:
                    line = line.strip()
                    if line:
                        # Parsear formato de log: "TIMESTAMP | LEVEL | MESSAGE"
                        try:
                            if ' | ' in line:
                                parts = line.split(' | ', 2)
                                if len(parts) >= 3:
                                    timestamp_str = parts[0]
                                    level = parts[1].lower()
                                    message = parts[2]
                                    
                                    # Mapear niveles de log correctamente
                                    if level in ['info', 'debug']:
                                        level = 'info'
                                    elif level in ['warn', 'warning']:
                                        level = 'warning'
                                    elif level in ['err', 'error']:
                                        level = 'error'
                                    elif level in ['critical']:
                                        level = 'error'
                                    else:
                                        level = 'info'
                                    
                                    logs.append({
                                        "timestamp": timestamp_str,
                                        "level": level,
                                        "message": message  # Mantener mensaje original con emojis
                                    })
                                else:
                                    # Línea sin formato estándar, tratarla como info
                                    logs.append({
                                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                        "level": "info",
                                        "message": line
                                    })
                            else:
                                # Línea sin separadores, tratarla como info
                                logs.append({
                                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                    "level": "info",
                                    "message": line
                                })
                        except Exception as parse_error:
                            # Si hay error parseando, incluir la línea tal como está
                            logs.append({
                                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "level": "info",
                                "message": line
                            })
                            
                # Si tenemos logs del archivo, devolverlos
                if logs:
                    return {"logs": logs}
                    
            except Exception as file_error:
                print(f"Error leyendo archivo de logs: {str(file_error)}")
        
        # Si no hay archivo de log o está vacío, devolver estado del sistema
        if active_process is not None and active_process.poll() is None:
            # Proceso activo pero sin logs aún
            logs = [
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "level": "success",
                    "message": f"� Algorithm ejecutándose (PID: {active_process.pid})"
                },
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "level": "info",
                    "message": "🧮 Analizando mercados con algoritmos educacionales..."
                },
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "level": "info",
                    "message": "📈 Monitoreando oportunidades educacionales de trading..."
                }
            ]
        else:
            # No hay proceso activo
            logs = [
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "level": "info",
                    "message": "� Sistema Educacional InverseNeural Lab listo para iniciar"
                },
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "level": "info", 
                    "message": "⚙️ Configure los parámetros y presione 'Activar Algoritmo'"
                },
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "level": "success", 
                    "message": "✅ Plataforma educacional inicializada correctamente"
                }
            ]
        
        return {"logs": logs}
        
    except Exception as e:
        return {
            "logs": [
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "level": "error",
                    "message": f"❌ Error obteniendo logs: {str(e)}"
                }
            ]
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
