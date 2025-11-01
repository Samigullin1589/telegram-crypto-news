# app/whales/integration.py
"""
WHALE SYSTEM INTEGRATION - PRODUCTION READY
Интеграция всех компонентов whale monitoring system
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app import settings

logger = logging.getLogger(__name__)


class WhaleSystemIntegration:
    """
    Интеграция всех компонентов whale системы:
    - Monitor (основной мониторинг)
    - Discovery (поиск новых кошельков)
    - Learning Engine (обучение)
    - Performance Tracker (отслеживание результатов)
    - Validator (очистка базы)
    - Smart Discovery (умный поиск)
    """
    
    def __init__(
        self,
        monitor,
        discovery=None,
        learning_engine=None,
        performance_tracker=None,
        validator=None,
        smart_discovery=None,
        publisher=None,
        alert_manager=None
    ):
        """
        Инициализация интеграции
        
        Args:
            monitor: Основной whale monitor
            discovery: Discovery system
            learning_engine: Learning engine
            performance_tracker: Performance tracker
            validator: Validator
            smart_discovery: Smart discovery
            publisher: Message publisher
            alert_manager: Alert manager
        """
        self.monitor = monitor
        self.discovery = discovery
        self.learning_engine = learning_engine
        self.performance_tracker = performance_tracker
        self.validator = validator
        self.smart_discovery = smart_discovery
        self.publisher = publisher
        self.alert_manager = alert_manager
        
        # Статус компонентов
        self.components = {
            'monitor': self.monitor is not None,
            'discovery': self.discovery is not None,
            'learning_engine': self.learning_engine is not None,
            'performance_tracker': self.performance_tracker is not None,
            'validator': self.validator is not None,
            'smart_discovery': self.smart_discovery is not None,
            'publisher': self.publisher is not None,
            'alert_manager': self.alert_manager is not None
        }
        
        self.running = False
        self.stats = {
            'scans_completed': 0,
            'discoveries_made': 0,
            'validations_done': 0,
            'learning_updates': 0,
            'total_transactions': 0,
            'total_signals': 0
        }
        
        logger.info("✅ WhaleSystemIntegration инициализирован")
        logger.info(f"   Активных компонентов: {sum(self.components.values())}/{len(self.components)}")
    
    async def scan(self) -> Dict[str, Any]:
        """
        Основной метод сканирования
        Совместим с IntegratedScheduler
        
        Returns:
            Dict с результатами сканирования
        """
        try:
            result = {
                'success': False,
                'found': 0,
                'signals': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if not self.monitor:
                logger.warning("⚠️ Monitor не инициализирован")
                return result
            
            # Запускаем основной мониторинг
            if hasattr(self.monitor, 'scan'):
                scan_result = await self.monitor.scan()
            elif hasattr(self.monitor, 'monitor'):
                scan_result = await self.monitor.monitor()
            elif hasattr(self.monitor, 'run'):
                scan_result = await self.monitor.run()
            else:
                logger.error("❌ Monitor не имеет метода scan/monitor/run")
                return result
            
            if scan_result:
                result['success'] = True
                result['found'] = scan_result.get('transactions', 0) or scan_result.get('found', 0)
                result['signals'] = scan_result.get('signals', 0)
                
                self.stats['scans_completed'] += 1
                self.stats['total_transactions'] += result['found']
                self.stats['total_signals'] += result['signals']
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка в WhaleSystemIntegration.scan: {e}")
            return {
                'success': False,
                'found': 0,
                'signals': 0,
                'error': str(e)
            }
    
    async def run_scan(self) -> Dict[str, Any]:
        """Альтернативное имя для scan()"""
        return await self.scan()
    
    async def monitor_cycle(self) -> Dict[str, Any]:
        """Альтернативное имя для scan()"""
        return await self.scan()
    
    async def discover_wallets(self) -> Dict[str, Any]:
        """Запуск discovery для поиска новых кошельков"""
        try:
            if not self.smart_discovery:
                return {'success': False, 'new_wallets': 0}
            
            logger.info("🔍 Запуск smart discovery...")
            
            if hasattr(self.smart_discovery, 'discover'):
                result = await self.smart_discovery.discover()
            elif hasattr(self.smart_discovery, 'run'):
                result = await self.smart_discovery.run()
            else:
                logger.warning("⚠️ Smart discovery не имеет метода discover/run")
                return {'success': False, 'new_wallets': 0}
            
            if result:
                self.stats['discoveries_made'] += result.get('new_wallets', 0)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка в discover_wallets: {e}")
            return {'success': False, 'error': str(e)}
    
    async def validate_wallets(self) -> Dict[str, Any]:
        """Запуск валидации кошельков"""
        try:
            if not self.validator:
                return {'success': False, 'removed': 0}
            
            logger.info("🧹 Запуск validator...")
            
            if hasattr(self.validator, 'validate'):
                result = await self.validator.validate()
            elif hasattr(self.validator, 'run'):
                result = await self.validator.run()
            elif hasattr(self.validator, 'cleanup'):
                result = await self.validator.cleanup()
            else:
                logger.warning("⚠️ Validator не имеет метода validate/run/cleanup")
                return {'success': False, 'removed': 0}
            
            if result:
                self.stats['validations_done'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка в validate_wallets: {e}")
            return {'success': False, 'error': str(e)}
    
    async def update_learning(self) -> Dict[str, Any]:
        """Обновление learning engine"""
        try:
            if not self.learning_engine:
                return {'success': False}
            
            logger.info("🧠 Обновление learning engine...")
            
            if hasattr(self.learning_engine, 'update'):
                result = await self.learning_engine.update()
            elif hasattr(self.learning_engine, 'train'):
                result = await self.learning_engine.train()
            elif hasattr(self.learning_engine, 'learn'):
                result = await self.learning_engine.learn()
            else:
                logger.warning("⚠️ Learning engine не имеет метода update/train/learn")
                return {'success': False}
            
            if result:
                self.stats['learning_updates'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка в update_learning: {e}")
            return {'success': False, 'error': str(e)}
    
    async def track_performance(self) -> Dict[str, Any]:
        """Отслеживание производительности сигналов"""
        try:
            if not self.performance_tracker:
                return {'success': False}
            
            logger.debug("📊 Проверка performance...")
            
            if hasattr(self.performance_tracker, 'track'):
                result = await self.performance_tracker.track()
            elif hasattr(self.performance_tracker, 'check'):
                result = await self.performance_tracker.check()
            elif hasattr(self.performance_tracker, 'update'):
                result = await self.performance_tracker.update()
            else:
                logger.warning("⚠️ Performance tracker не имеет метода track/check/update")
                return {'success': False}
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка в track_performance: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику работы системы"""
        return {
            **self.stats,
            'components_active': sum(self.components.values()),
            'components_total': len(self.components),
            'components': self.components
        }
    
    def get_component_status(self) -> Dict[str, bool]:
        """Получить статус всех компонентов"""
        return self.components.copy()
    
    async def start(self):
        """Запустить систему"""
        self.running = True
        logger.info("▶️ Whale System Integration запущена")
    
    async def stop(self):
        """Остановить систему"""
        self.running = False
        logger.info("⏹️ Whale System Integration остановлена")
    
    def __repr__(self):
        return (
            f"WhaleSystemIntegration("
            f"components={sum(self.components.values())}/{len(self.components)}, "
            f"scans={self.stats['scans_completed']})"
        )


# Функция для создания интеграции

async def create_whale_integration(
    monitor,
    discovery=None,
    learning_engine=None,
    performance_tracker=None,
    validator=None,
    smart_discovery=None,
    publisher=None,
    alert_manager=None
) -> WhaleSystemIntegration:
    """
    Создать whale system integration
    
    Args:
        monitor: Основной whale monitor
        discovery: Discovery system (опционально)
        learning_engine: Learning engine (опционально)
        performance_tracker: Performance tracker (опционально)
        validator: Validator (опционально)
        smart_discovery: Smart discovery (опционально)
        publisher: Publisher (опционально)
        alert_manager: Alert manager (опционально)
    
    Returns:
        WhaleSystemIntegration
    """
    integration = WhaleSystemIntegration(
        monitor=monitor,
        discovery=discovery,
        learning_engine=learning_engine,
        performance_tracker=performance_tracker,
        validator=validator,
        smart_discovery=smart_discovery,
        publisher=publisher,
        alert_manager=alert_manager
    )
    
    await integration.start()
    
    return integration


# Экспорт
__all__ = ['WhaleSystemIntegration', 'create_whale_integration']