# core/tasks/trading_runner.py
"""
Trading System Runner
Раннер для trading системы
"""

import asyncio
import logging
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TradingSystemRunner:
    """
    Раннер для Trading System
    
    Управляет циклами анализа и генерации сигналов
    """
    
    def __init__(
        self,
        trading_system: Any,
        health_monitor: Any,
        resource_monitor: Any,
        statistics: Any,
        shutdown_event: asyncio.Event
    ):
        """
        Инициализация раннера
        
        Args:
            trading_system: Trading system
            health_monitor: Монитор здоровья
            resource_monitor: Монитор ресурсов
            statistics: Статистика
            shutdown_event: Event для shutdown
        """
        self.trading_system = trading_system
        self.health_monitor = health_monitor
        self.resource_monitor = resource_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
        
        # Настройки
        self.check_interval = 300  # 5 минут
        self.heartbeat_interval = 60
    
    async def run(self):
        """Основной цикл trading system"""
        logger.info("📈 [TRADING] Starting Trading System...")
        
        # Начальная задержка
        await asyncio.sleep(30)
        
        # Отправка первого heartbeat
        self.health_monitor.send_heartbeat('Trading System')
        
        last_heartbeat = datetime.now()
        
        while not self.shutdown_event.is_set():
            try:
                # Heartbeat
                if (datetime.now() - last_heartbeat).seconds >= self.heartbeat_interval:
                    self.health_monitor.send_heartbeat('Trading System')
                    last_heartbeat = datetime.now()
                
                # Проверка enable status
                if not self.trading_system.is_enabled():
                    logger.debug("[TRADING] System disabled, waiting...")
                    await asyncio.sleep(self.check_interval)
                    continue
                
                # Выполнение цикла анализа
                await self._run_trading_cycle()
                
                # Пауза до следующего цикла
                await asyncio.sleep(self.check_interval)
            
            except asyncio.CancelledError:
                logger.info("📈 [TRADING] Received cancellation")
                break
            
            except Exception as e:
                logger.error(f"❌ [TRADING] Cycle error: {e}", exc_info=True)
                self.statistics.increment_errors()
                await asyncio.sleep(self.check_interval)
        
        logger.info("📈 [TRADING] Trading System stopped")
    
    async def _run_trading_cycle(self):
        """Выполнение цикла trading"""
        logger.debug("[TRADING] Running analysis cycle...")
        
        try:
            # Здесь будет логика анализа активов
            # Пока просто логируем
            stats = await self.trading_system.get_performance_stats()
            
            logger.debug(
                f"[TRADING] Stats: "
                f"signals={stats.get('total_signals', 0)}, "
                f"trades={stats.get('total_trades', 0)}"
            )
        
        except Exception as e:
            logger.error(f"❌ [TRADING] Analysis error: {e}")


__all__ = ['TradingSystemRunner']