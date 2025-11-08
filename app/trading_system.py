# app/trading_system.py
"""
Trading System Facade v5.0
Унифицированный интерфейс для Trading System с улучшенной архитектурой
"""

import logging
from typing import Dict, Any, Optional, List

from app.config import config

logger = logging.getLogger(__name__)


class TradingSystem:
    """
    Фасад для Trading System
    
    Улучшения v5.0:
    - Использует app.config вместо app.settings
    - Модульная архитектура
    - Улучшенная обработка ошибок
    - Безопасная инициализация
    """
    
    def __init__(self):
        """Инициализация Trading System"""
        
        # Проверка включен ли trading в конфигурации
        self.enabled = config.is_feature_enabled('trading')
        
        # Получение конфигурации
        self.trading_config = config.features.get_trading_config()
        self.dry_run = self.trading_config.get('dry_run', True)
        
        # Компоненты
        self.signal_generator = None
        self.positions = None
        self.performance = None
        self._initialized = False
        
        # Попытка инициализации компонентов
        if self.enabled:
            self._initialize_components()
        else:
            logger.info("📈 [TRADING] Trading System disabled in configuration")
            self._log_disabled_status()
    
    def _initialize_components(self):
        """Инициализация компонентов Trading System"""
        try:
            # Импорт модулей trading
            from app.trading.signal_generator import SignalGenerator
            from app.trading.position_tracker import PositionTracker
            from app.trading.performance_stats import PerformanceStats
            
            # Получение CoinGecko API key
            coingecko_key = getattr(config.api, 'coingecko_api_key', None)
            
            # Инициализация компонентов
            self.signal_generator = SignalGenerator(coingecko_key=coingecko_key)
            self.positions = self.signal_generator.positions
            self.performance = self.signal_generator.performance
            
            self._initialized = True
            
            self._log_initialization_success()
        
        except ImportError as e:
            logger.warning(f"⚠️  [TRADING] Trading modules not available: {e}")
            self.enabled = False
            self._log_modules_unavailable()
        
        except Exception as e:
            logger.error(f"❌ [TRADING] Initialization error: {e}", exc_info=True)
            self.enabled = False
    
    def _log_initialization_success(self):
        """Логирование успешной инициализации"""
        logger.info("\n" + "="*80)
        logger.info("📈 TRADING SYSTEM v5.0 - INITIALIZED")
        logger.info("="*80)
        logger.info(f"Status: ✅ ENABLED")
        logger.info(f"Mode: {'🧪 DRY RUN' if self.dry_run else '💰 LIVE'}")
        logger.info(f"Min Confidence: {self.trading_config.get('min_confidence', 75)}/100")
        logger.info(f"Max Signals/Day: {self.trading_config.get('max_signals_per_day', 10)}")
        logger.info(f"Max Open Positions: {self.trading_config.get('max_open_positions', 5)}")
        logger.info(f"Stop Loss: {self.trading_config.get('default_stop_loss', 3.0)}%")
        logger.info(f"Take Profit: {self.trading_config.get('default_take_profit', 5.0)}%")
        logger.info("="*80 + "\n")
    
    def _log_disabled_status(self):
        """Логирование отключенного статуса"""
        logger.info("\n" + "="*80)
        logger.info("📈 TRADING SYSTEM v5.0")
        logger.info("="*80)
        logger.info("Status: ❌ DISABLED")
        logger.info("Reason: TRADING_ENABLED=false in configuration")
        logger.info("="*80 + "\n")
    
    def _log_modules_unavailable(self):
        """Логирование недоступности модулей"""
        logger.info("\n" + "="*80)
        logger.info("📈 TRADING SYSTEM v5.0")
        logger.info("="*80)
        logger.info("Status: ❌ DISABLED")
        logger.info("Reason: Trading modules not available")
        logger.info("="*80 + "\n")
    
    def is_enabled(self) -> bool:
        """
        Проверка включен ли Trading System
        
        Returns:
            True если система включена и инициализирована
        """
        return self.enabled and self._initialized and self.signal_generator is not None
    
    async def generate_signal(
        self,
        symbol: str,
        price_data: Any,
        session: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Генерация торгового сигнала
        
        Args:
            symbol: Тикер актива
            price_data: DataFrame с OHLCV данными
            session: aiohttp session
            
        Returns:
            Signal dict или None
        """
        if not self.is_enabled():
            logger.debug(f"[TRADING] System not enabled, skipping signal for {symbol}")
            return None
        
        try:
            # Генерация сигнала
            signal = await self.signal_generator.generate_signal(
                asset=symbol,
                price_data=price_data,
                session=session
            )
            
            if not signal:
                return None
            
            # Фильтрация по confidence
            min_confidence = self.trading_config.get('min_confidence', 75)
            if signal.confidence < min_confidence:
                logger.debug(
                    f"[TRADING] Signal {symbol} filtered: "
                    f"confidence {signal.confidence:.1f} < {min_confidence}"
                )
                return None
            
            # Конвертация в dict
            return signal.to_dict()
        
        except Exception as e:
            logger.error(f"❌ [TRADING] Error generating signal for {symbol}: {e}")
            return None
    
    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Получение открытых позиций
        
        Returns:
            Список открытых позиций
        """
        if not self.is_enabled() or not self.positions:
            return []
        
        try:
            open_pos = self.positions.get_open_positions()
            return [pos.to_dict() for pos in open_pos]
        except Exception as e:
            logger.error(f"❌ [TRADING] Error getting positions: {e}")
            return []
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """
        Получение статистики производительности
        
        Returns:
            Dict со статистикой
        """
        if not self.is_enabled() or not self.performance:
            return {
                'total_signals': 0,
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'total_pnl': 0.0
            }
        
        try:
            return self.performance.get_summary_stats()
        except Exception as e:
            logger.error(f"❌ [TRADING] Error getting stats: {e}")
            return {
                'total_signals': 0,
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'total_pnl': 0.0
            }
    
    async def update_positions(self, price_provider: Any = None) -> List[Dict[str, Any]]:
        """
        Обновление позиций (проверка SL/TP)
        
        Args:
            price_provider: Provider для получения текущих цен
            
        Returns:
            Список закрытых позиций
        """
        if not self.is_enabled() or not self.positions:
            return []
        
        try:
            closed = []
            open_positions = self.positions.get_open_positions()
            
            for position in open_positions:
                # Получение текущей цены
                if price_provider and hasattr(price_provider, 'get_price'):
                    try:
                        current_price = await price_provider.get_price(position.asset)
                        
                        # Обновление позиции
                        updated = self.positions.update_position(
                            position.id,
                            current_price
                        )
                        
                        # Проверка закрытия
                        if updated and updated.status != 'OPEN':
                            closed.append(updated.to_dict())
                    
                    except Exception as e:
                        logger.warning(
                            f"⚠️  [TRADING] Error updating position {position.asset}: {e}"
                        )
            
            return closed
        
        except Exception as e:
            logger.error(f"❌ [TRADING] Error updating positions: {e}")
            return []
    
    def format_signal_for_telegram(self, signal: Dict[str, Any]) -> str:
        """
        Форматирование сигнала для Telegram
        
        Args:
            signal: Signal dict
            
        Returns:
            Formatted message (HTML)
        """
        if not self.is_enabled():
            return ""
        
        try:
            # Если объект TradingSignal
            if hasattr(signal, 'format_signal_message'):
                return signal.format_signal_message()
            
            # Если dict - используем signal_generator
            if self.signal_generator:
                return self.signal_generator.format_signal_message(signal)
        
        except Exception as e:
            logger.error(f"❌ [TRADING] Error formatting signal: {e}")
        
        return ""
    
    def get_config(self) -> Dict[str, Any]:
        """
        Получение текущей конфигурации
        
        Returns:
            Dict с конфигурацией
        """
        return {
            'enabled': self.enabled,
            'initialized': self._initialized,
            **self.trading_config
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса системы
        
        Returns:
            Dict со статусом
        """
        return {
            'enabled': self.enabled,
            'initialized': self._initialized,
            'dry_run': self.dry_run,
            'has_signal_generator': self.signal_generator is not None,
            'has_positions': self.positions is not None,
            'has_performance': self.performance is not None
        }
    
    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("🧹 [TRADING] Cleanup...")
        
        try:
            if self.signal_generator and hasattr(self.signal_generator, 'cleanup'):
                await self.signal_generator.cleanup()
            
            self._initialized = False
            logger.info("✅ [TRADING] Cleanup completed")
        
        except Exception as e:
            logger.error(f"⚠️  [TRADING] Cleanup error: {e}")


__all__ = ['TradingSystem']