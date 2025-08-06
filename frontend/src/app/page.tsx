'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Image from 'next/image';
import {
  Config,
  AlgorithmStatus,
  LogEntry,
  HealthStatus,
  TRADING_PAIRS,
  CRYPTO_ASSETS,
  DEFAULT_CONFIG,
  INITIAL_STATUS,
  INITIAL_LOGS,
  API_CONFIG
} from '@/types';
import { useUser } from '@/contexts/UserContext';
import Loading from '@/components/Loading';

export default function HomePage() {
  // App context
  const { loading } = useUser();

  // Refs
  const logsContainerRef = useRef<HTMLDivElement>(null);
  
  // State management
  const [status, setStatus] = useState<AlgorithmStatus>(INITIAL_STATUS);
  const [config, setConfig] = useState<Config>(DEFAULT_CONFIG);
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS);
  const [isLoading, setIsLoading] = useState(false);
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('checking');
  const [connectionRetries, setConnectionRetries] = useState(0);
  const [isResetting, setIsResetting] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [isClient, setIsClient] = useState(false);
  
  // Smart scroll state
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const [hasNewLogs, setHasNewLogs] = useState(false);

  // Helper function to create consistent timestamps
  const createTimestamp = useCallback(() => {
    return isClient ? new Date().toISOString() : '2025-08-06T00:00:00.000Z';
  }, [isClient]);

  // Hydration fix - set isClient to true only after mount
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Helper functions for position size sliders
  const getPositionSizeColor = (value: number) => {
    if (value <= 3) return 'text-green-400';
    if (value <= 6) return 'text-yellow-400'; 
    if (value <= 8) return 'text-orange-400';
    return 'text-red-400';
  };

  const getRiskLevel = (value: number) => {
    if (value <= 3) return 'Low Risk';
    if (value <= 6) return 'Medium Risk';
    if (value <= 8) return 'High Risk'; 
    return 'Very High Risk';
  };

  const getSliderGradient = (value: number) => {
    if (value <= 3) return 'from-green-500 to-green-600';
    if (value <= 6) return 'from-yellow-500 to-yellow-600';
    if (value <= 8) return 'from-orange-500 to-orange-600';
    return 'from-red-500 to-red-600';
  };

  // API functions
  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.STATUS}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(5000),
      });
      
      if (response.ok) {
        const data = await response.json();
        setStatus(prev => ({ ...prev, ...data }));
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
      console.error('Error fetching status:', errorMessage);
      
      setLogs(prev => [...prev, {
        timestamp: createTimestamp(),
        level: 'warning',
        message: `Error al obtener estado: ${errorMessage}`
      }]);
    }
  }, [createTimestamp]);

  const checkHealth = useCallback(async () => {
    try {
      setHealthStatus('checking');
      
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.HEALTH}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        mode: 'cors',
        signal: AbortSignal.timeout(5000),
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Health check successful:', data);
        setHealthStatus('healthy');
        setConnectionRetries(0);
        
        if (connectionRetries > 0) {
          setLogs(prev => [...prev, {
            timestamp: new Date().toISOString(),
            level: 'success',
            message: 'Conexión con backend restablecida'
          }]);
        }
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      let errorMessage = 'Error de conexión';
      
      if (err instanceof Error) {
        if (err.name === 'TypeError' && err.message.includes('Failed to fetch')) {
          errorMessage = 'Error CORS - Backend no configurado para frontend';
        } else if (err.name === 'AbortError') {
          errorMessage = 'Timeout - Backend no responde';
        } else {
          errorMessage = err.message;
        }
      }
      
      console.error('Health check failed:', errorMessage);
      
      setHealthStatus('error');
      setConnectionRetries(prev => prev + 1);
      
      if (connectionRetries % 3 === 0) {
        setLogs(prev => [...prev, {
          timestamp: new Date().toISOString(),
          level: 'error',
          message: `Error de conexión con backend (intento ${connectionRetries + 1}): ${errorMessage}`
        }]);
      }
    }
  }, [connectionRetries]);

  const fetchLogs = useCallback(async () => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.LOGS}?limit=100`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(5000),
      });
      
      if (response.ok) {
        const data = await response.json();
        // Backend devuelve { "logs": [...] }
        const logsArray = data.logs || data;
        if (Array.isArray(logsArray) && logsArray.length > 0) {
          const newLogs = logsArray.map((entry: unknown) => {
            if (typeof entry === 'object' && entry !== null) {
              const logEntry = entry as Record<string, unknown>;
              return {
                timestamp: String(logEntry.timestamp || new Date().toISOString()),
                level: (logEntry.level as LogEntry['level']) || 'info',
                message: String(logEntry.message || 'Sin mensaje')
              };
            }
            return {
              timestamp: new Date().toISOString(),
              level: 'info' as const,
              message: String(entry)
            };
          });
          
          setLogs(prevLogs => {
            if (prevLogs.length > 0 && newLogs.length > prevLogs.length) {
              setHasNewLogs(true);
            }
            return newLogs;
          });
        }
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
      console.error('Error fetching logs:', errorMessage);
      
      if (connectionRetries === 0) {
        setLogs(prev => [...prev, {
          timestamp: new Date().toISOString(),
          level: 'warning',
          message: `Error al obtener logs: ${errorMessage}`
        }]);
      }
    }
  }, [connectionRetries]);

  const startAlgorithm = async () => {
    if (!config.email || !config.password) {
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        level: 'warning',
        message: 'Por favor complete las credenciales de IQ Option antes de iniciar'
      }]);
      return;
    }

    if (config.selectedPairs.length === 0 && config.selectedCrypto.length === 0) {
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        level: 'warning',
        message: 'Por favor seleccione al menos un activo antes de iniciar'
      }]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.START}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
        signal: AbortSignal.timeout(10000),
      });
      
      if (response.ok) {
        const data = await response.json();
        setStatus(prev => ({ ...prev, ...data }));
        setLogs(prev => [...prev, {
          timestamp: new Date().toISOString(),
          level: 'success',
          message: 'Algoritmo iniciado exitosamente'
        }]);
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
      console.error('Error starting algorithm:', errorMessage);
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        level: 'error',
        message: `Error al iniciar algoritmo: ${errorMessage}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const stopAlgorithm = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.STOP}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(5000),
      });
      
      if (response.ok) {
        const data = await response.json();
        setStatus(prev => ({ ...prev, ...data, status: 'stopped' }));
        setLogs(prev => [...prev, {
          timestamp: createTimestamp(),
          level: 'info',
          message: 'Algorithm stopped successfully'
        }]);
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
      console.error('Error stopping algorithm:', errorMessage);
      setLogs(prev => [...prev, {
        timestamp: createTimestamp(),
        level: 'error',
        message: `Error stopping algorithm: ${errorMessage}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const resetAlgorithm = async () => {
    setIsResetting(true);
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.RESET}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(15000), // Longer timeout for reset operation
      });
      
      if (response.ok) {
        const data = await response.json();
        setStatus(INITIAL_STATUS);
        setLogs([{
          timestamp: new Date().toISOString(),
          level: 'success',
          message: '✅ Algorithm statistics reset successfully'
        }]);
        
        if (data.output) {
          setLogs(prev => [...prev, {
            timestamp: new Date().toISOString(),
            level: 'info',
            message: `📋 ${data.output}`
          }]);
        }
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
      console.error('Error resetting algorithm:', errorMessage);
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        level: 'error',
        message: `❌ Error resetting algorithm: ${errorMessage}`
      }]);
    } finally {
      setIsResetting(false);
      setShowResetConfirm(false);
    }
  };

  // Auto-scroll to bottom when new logs arrive (only if user isn't scrolling)
  useEffect(() => {
    if (hasNewLogs && !isUserScrolling && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
      setHasNewLogs(false);
    }
  }, [logs, hasNewLogs, isUserScrolling]);

  // Polling intervals
  useEffect(() => {
    const statusInterval = setInterval(fetchStatus, API_CONFIG.POLLING_INTERVALS.STATUS);
    const logsInterval = setInterval(fetchLogs, API_CONFIG.POLLING_INTERVALS.LOGS);
    const healthInterval = setInterval(checkHealth, API_CONFIG.POLLING_INTERVALS.HEALTH);

    // Initial fetch
    checkHealth();
    fetchStatus();
    fetchLogs();

    return () => {
      clearInterval(statusInterval);
      clearInterval(logsInterval);
      clearInterval(healthInterval);
    };
  }, [fetchStatus, fetchLogs, checkHealth]);

  // Scroll detection for smart auto-scroll
  const handleScroll = useCallback(() => {
    if (logsContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current;
      const isAtBottom = scrollHeight - scrollTop <= clientHeight + 50; // 50px tolerance
      setIsUserScrolling(!isAtBottom);
    }
  }, []);

  if (loading) {
    return <Loading />;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <style jsx>{`
        input[type="range"].slider-thumb::-webkit-slider-thumb {
          appearance: none;
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: #ffffff;
          border: 2px solid #374151;
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        
        input[type="range"].slider-thumb::-moz-range-thumb {
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: #ffffff;
          border: 2px solid #374151;
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
      `}</style>
      {/* Header */}
      <header className="sticky top-0 z-50 bg-gray-800 border-b border-gray-700 px-4 sm:px-6 py-4 backdrop-blur-sm bg-opacity-95">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image 
              src="/logo.png" 
              alt="InverseNeural Lab" 
              width={40}
              height={40}
              className="w-8 h-8 sm:w-10 sm:h-10"
            />
            <div>
              <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-blue-400 to-green-400 bg-clip-text text-transparent">
                InverseNeural Lab
              </h1>
              <p className="text-gray-400 text-xs sm:text-sm">Educational Trading Platform</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${
                healthStatus === 'healthy' ? 'bg-green-500' : 
                healthStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500'
              }`} />
              <span className="text-sm text-gray-400">
                {healthStatus === 'healthy' ? 'Connected' : 
                 healthStatus === 'error' ? 'Disconnected' : 'Checking...'}
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-4 sm:p-6 space-y-6">
       

        {/* Control Panel */}
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-semibold text-white mb-4">Control Panel</h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* IQ Option Credentials */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">IQ Option Credentials</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={config.email}
                  onChange={(e) => setConfig(prev => ({ ...prev, email: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="your-email@example.com"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={config.password}
                  onChange={(e) => setConfig(prev => ({ ...prev, password: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Your password"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Account Type
                </label>
                <select
                  value={config.accountType}
                  onChange={(e) => setConfig(prev => ({ ...prev, accountType: e.target.value as 'PRACTICE' | 'REAL' }))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="PRACTICE">Practice (Recommended)</option>
                  <option value="REAL">Real</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Strategy
                </label>
                <select
                  value={config.aggressiveness}
                  onChange={(e) => setConfig(prev => ({ ...prev, aggressiveness: e.target.value as 'conservador' | 'balanceado' | 'agresivo' }))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="conservador">Conservador - Pocas señales, alta calidad</option>
                  <option value="balanceado">Balanceado - Balance entre cantidad y calidad</option>
                  <option value="agresivo">Agresivo - Más señales, menor filtro</option>
                </select>
              </div>

              {/* Position Size Sliders */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Stock Pairs Position Size
                </label>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-medium ${getPositionSizeColor(config.pairsPositionSize)}`}>
                      {config.pairsPositionSize}% - {getRiskLevel(config.pairsPositionSize)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={config.pairsPositionSize}
                    onChange={(e) => setConfig(prev => ({ ...prev, pairsPositionSize: parseInt(e.target.value) }))}
                    className={`w-full h-2 rounded-lg appearance-none cursor-pointer bg-gradient-to-r ${getSliderGradient(config.pairsPositionSize)} slider-thumb`}
                    style={{
                      background: `linear-gradient(to right, 
                        ${config.pairsPositionSize <= 3 ? '#10b981' : 
                          config.pairsPositionSize <= 6 ? '#f59e0b' : 
                          config.pairsPositionSize <= 8 ? '#f97316' : '#ef4444'} 0%, 
                        ${config.pairsPositionSize <= 3 ? '#059669' : 
                          config.pairsPositionSize <= 6 ? '#d97706' : 
                          config.pairsPositionSize <= 8 ? '#ea580c' : '#dc2626'} 100%)`
                    }}
                  />
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>1% (Conservative)</span>
                    <span>10% (Very Aggressive)</span>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Crypto Position Size
                </label>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-medium ${getPositionSizeColor(config.cryptoPositionSize)}`}>
                      {config.cryptoPositionSize}% - {getRiskLevel(config.cryptoPositionSize)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={config.cryptoPositionSize}
                    onChange={(e) => setConfig(prev => ({ ...prev, cryptoPositionSize: parseInt(e.target.value) }))}
                    className={`w-full h-2 rounded-lg appearance-none cursor-pointer bg-gradient-to-r ${getSliderGradient(config.cryptoPositionSize)} slider-thumb`}
                    style={{
                      background: `linear-gradient(to right, 
                        ${config.cryptoPositionSize <= 3 ? '#10b981' : 
                          config.cryptoPositionSize <= 6 ? '#f59e0b' : 
                          config.cryptoPositionSize <= 8 ? '#f97316' : '#ef4444'} 0%, 
                        ${config.cryptoPositionSize <= 3 ? '#059669' : 
                          config.cryptoPositionSize <= 6 ? '#d97706' : 
                          config.cryptoPositionSize <= 8 ? '#ea580c' : '#dc2626'} 100%)`
                    }}
                  />
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>1% (Conservative)</span>
                    <span>10% (Very Aggressive)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Asset Selection */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">Asset Selection</h3>
              
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-300">
                    Stock Pairs ({config.selectedPairs.length} selected)
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setConfig(prev => ({ ...prev, selectedPairs: [...TRADING_PAIRS] }))}
                      className="text-xs px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                    >
                      All
                    </button>
                    <button
                      onClick={() => setConfig(prev => ({ ...prev, selectedPairs: [] }))}
                      className="text-xs px-2 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
                    >
                      None
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto">
                  {TRADING_PAIRS.map((pair) => (
                    <label key={pair} className="flex items-center space-x-2 text-sm">
                      <input
                        type="checkbox"
                        checked={config.selectedPairs.includes(pair)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setConfig(prev => ({ 
                              ...prev, 
                              selectedPairs: [...prev.selectedPairs, pair] 
                            }));
                          } else {
                            setConfig(prev => ({ 
                              ...prev, 
                              selectedPairs: prev.selectedPairs.filter(p => p !== pair) 
                            }));
                          }
                        }}
                        className="rounded border-gray-600 text-blue-600 focus:ring-blue-500 focus:ring-2"
                      />
                      <span className="text-gray-300">{pair}</span>
                    </label>
                  ))}
                </div>
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-300">
                    Crypto Assets ({config.selectedCrypto.length} selected)
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setConfig(prev => ({ ...prev, selectedCrypto: [...CRYPTO_ASSETS] }))}
                      className="text-xs px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                    >
                      All
                    </button>
                    <button
                      onClick={() => setConfig(prev => ({ ...prev, selectedCrypto: [] }))}
                      className="text-xs px-2 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
                    >
                      None
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto">
                  {CRYPTO_ASSETS.map((crypto) => (
                    <label key={crypto} className="flex items-center space-x-2 text-sm">
                      <input
                        type="checkbox"
                        checked={config.selectedCrypto.includes(crypto)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setConfig(prev => ({ 
                              ...prev, 
                              selectedCrypto: [...prev.selectedCrypto, crypto] 
                            }));
                          } else {
                            setConfig(prev => ({ 
                              ...prev, 
                              selectedCrypto: prev.selectedCrypto.filter(c => c !== crypto) 
                            }));
                          }
                        }}
                        className="rounded border-gray-600 text-blue-600 focus:ring-blue-500 focus:ring-2"
                      />
                      <span className="text-gray-300">{crypto}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Algorithm Controls */}
          <div className="mt-6 pt-6 border-t border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex gap-4">
                <button
                  onClick={startAlgorithm}
                  disabled={isLoading || status.status === 'running'}
                  className="flex items-center gap-2 px-6 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                >
                  {isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Starting...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1m6-6L12 14l-6-6" />
                      </svg>
                      Start Algorithm
                    </>
                  )}
                </button>

                <button
                  onClick={stopAlgorithm}
                  disabled={isLoading || status.status === 'stopped'}
                  className="flex items-center gap-2 px-6 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10h6v4H9z" />
                  </svg>
                  Stop Algorithm
                </button>

                <button
                  onClick={() => setShowResetConfirm(true)}
                  disabled={isResetting || status.status === 'running'}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.962-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  Reset Statistics
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Real-time Logs */}
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white">Real-time Logs</h2>
            <div className="text-sm text-gray-400">
              {logs.length} entries
              {hasNewLogs && (
                <span className="ml-2 px-2 py-1 bg-blue-600 text-blue-100 rounded text-xs">
                  New
                </span>
              )}
            </div>
          </div>
          
          <div 
            ref={logsContainerRef}
            onScroll={handleScroll}
            className="h-64 overflow-y-auto bg-gray-900 rounded border border-gray-700 p-4 font-mono text-sm"
          >
            {logs.length === 0 ? (
              <div className="text-gray-500 text-center py-8">
                No logs available yet...
              </div>
            ) : (
              logs.map((log, index) => (
                <div key={index} className="mb-2 flex gap-3">
                  <span className="text-gray-500 text-xs min-w-[120px]">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={`text-xs min-w-[60px] uppercase font-medium ${
                    log.level === 'error' ? 'text-red-400' :
                    log.level === 'warning' ? 'text-yellow-400' :
                    log.level === 'success' ? 'text-green-400' :
                    'text-blue-400'
                  }`}>
                    {log.level}
                  </span>
                  <span className="text-gray-300 flex-1">
                    {log.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Reset Algorithm Statistics</h3>
            <p className="text-gray-300 mb-6">
              Are you sure you want to reset all algorithm statistics? This will clear:
            </p>
            <ul className="text-gray-300 mb-6 ml-4 space-y-1">
              <li>• All win/loss records</li>
              <li>• Profit/loss history</li>
              <li>• Consecutive loss counters</li>
              <li>• Stop loss states</li>
            </ul>
            <p className="text-yellow-400 text-sm mb-6">
              ⚠️ This action cannot be undone, but a backup will be created.
            </p>
            <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 mb-6">
              <p className="text-red-400 text-sm font-medium">
                🚨 SUPER WARNING: This action goes AGAINST our money management protection system. 
                You should ONLY use this if your algorithm or you made some serious mistake that 
                requires a complete reset. Resetting statistics removes all safety mechanisms and 
                historical data that protect your capital.
              </p>
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowResetConfirm(false)}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={resetAlgorithm}
                disabled={isResetting}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-orange-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                {isResetting ? 'Resetting...' : 'Reset Statistics'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
