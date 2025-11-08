# app/scheduler/whale_monitor.py
"""
Whale Monitoring System v2.0 - Fixed Imports
Главный координатор системы мониторинга whale транзакций
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .monitor_lifecycle import MonitorLifecycle
from .monitor_cycle import MonitorCycleRunner
from .monitor_state import MonitorState

logger = logging.getLogger(__name__)


class WhaleMonitor:
    """
    Главный класс мониторинга крупных криптовалютных перемещений
    
    Улучшения v2.0:
    - Исправлены импорты типов
    - Модульная архитектура
    - Разделение ответственности
    - Улучшенная обработка ошибок
    """
    
    def __init__(self, components: Optional[Dict[str, Any]] = None):
        """
        Инициализация системы мониторинга
        
        Args:
            components: Словарь с компонентами системы (опционально)
        """
        # Инициализация состояния
        self.state = MonitorState()
        
        # Инициализация компонентов через lifecycle
        self.lifecycle = MonitorLifecycle(components or {})
        
        # Инициализация раннера циклов
        self.cycle_runner = MonitorCycleRunner(
            self.lifecycle.components,
            self.state
        )
        
        # Флаг успешной инициализации
        self.state.is_initialized = self.lifecycle.is_valid
        
        if self.state.is_initialized:
            logger.info("🐋 [WHALE] Monitor инициализирован успешно")
            self._log_configuration()
        else:
            logger.warning("⚠️  [WHALE] Monitor инициализирован с ограничениями")
    
    def _log_configuration(self):
        """Вывод информации о конфигурации"""
        try:
            from app.config import config
            
            if hasattr(config, 'blockchain'):
                threshold = getattr(
                    config.blockchain,
                    'whale_min_usd_threshold',
                    100000
                )
                logger.info(f"🐋 [WHALE] Порог: ${threshold:,.0f}")
            
            if hasattr(config, 'features'):
                posts_cap = getattr(config.features, 'whale_posts_per_hour', 20)
                logger.info(f"🐋 [WHALE] Лимит публикаций: {posts_cap}/час")
        
        except Exception as e:
            logger.debug(f"Не удалось вывести конфигурацию: {e}")
    
    async def run_cycle(
        self,
        start_time: datetime,
        chains: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Выполнение одного полного цикла мониторинга
        
        Args:
            start_time: Время начала мониторинга
            chains: Список блокчейнов для мониторинга (опционально)
            
        Returns:
            Dict с результатами цикла
        """
        if not self.state.is_initialized:
            logger.warning("⚠️  [WHALE] Monitor не инициализирован, пропуск цикла")
            return self._create_error_result("Monitor not initialized")
        
        # Определение блокчейнов для мониторинга
        if chains is None:
            chains = self._get_enabled_chains()
        
        if not chains:
            logger.debug("📭 [WHALE] Нет активных блокчейнов для мониторинга")
            return self._create_success_result(chains_monitored=0)
        
        # Выполнение цикла
        try:
            result = await self.cycle_runner.run_cycle(start_time, chains)
            
            # Обновление состояния
            self.state.update_from_cycle(result)
            
            return result
        
        except Exception as e:
            logger.error(f"❌ [WHALE] Критическая ошибка в цикле: {e}", exc_info=True)
            self.state.is_healthy = False
            return self._create_error_result(str(e))
    
    def _get_enabled_chains(self) -> list:
        """
        Получение списка включенных блокчейнов
        
        Returns:
            Список названий блокчейнов
        """
        try:
            from app.config import config
            
            if hasattr(config, 'blockchain'):
                return config.blockchain.enabled_chains or []
            
            return []
        
        except Exception as e:
            logger.debug(f"Не удалось получить enabled_chains: {e}")
            return []
    
    def _create_success_result(self, **kwargs) -> Dict[str, Any]:
        """Создание успешного результата"""
        return {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'is_healthy': self.state.is_healthy,
            **kwargs
        }
    
    def _create_error_result(self, error: str) -> Dict[str, Any]:
        """Создание результата с ошибкой"""
        return {
            'success': False,
            'timestamp': datetime.utcnow().isoformat(),
            'is_healthy': False,
            'error': error
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Получение статуса здоровья системы
        
        Returns:
            Dict со статусом и метриками
        """
        return {
            'is_initialized': self.state.is_initialized,
            'is_healthy': self.state.is_healthy,
            'last_cycle': (
                self.state.last_cycle_time.isoformat()
                if self.state.last_cycle_time
                else None
            ),
            'total_cycles': self.state.total_cycles,
            'total_events_processed': self.state.total_events_processed,
            'total_events_published': self.state.total_events_published,
            'components': self.lifecycle.get_components_status()
        }
    
    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("🧹 [WHALE] Cleanup monitor...")
        
        try:
            await self.cycle_runner.cleanup()
            await self.lifecycle.cleanup()
            
            self.state.is_initialized = False
            logger.info("✅ [WHALE] Cleanup completed")
        
        except Exception as e:
            logger.error(f"⚠️  [WHALE] Cleanup error: {e}")


__all__ = ['WhaleMonitor']