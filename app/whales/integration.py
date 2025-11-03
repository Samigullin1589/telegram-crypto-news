"""
WHALE SYSTEM INTEGRATION - PRODUCTION READY
Интеграция всех компонентов whale monitoring system
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

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
            'total_signals': 0,
            'last_scan_at': None,
            'last_discovery_at': None,
            'last_validation_at': None,
            'last_learning_update_at': None
        }
        
        # История операций
        self.operation_history: List[Dict] = []
        self.max_history_size = 100
        
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
                'timestamp': datetime.utcnow().isoformat(),
                'duration_seconds': 0
            }
            
            if not self.monitor:
                logger.warning("⚠️ Monitor не инициализирован")
                return result
            
            start_time = datetime.utcnow()
            
            # Запускаем основной мониторинг
            logger.info("🔍 Запуск whale monitor scan...")
            
            if hasattr(self.monitor, 'scan'):
                scan_result = await self.monitor.scan()
            elif hasattr(self.monitor, 'monitor'):
                scan_result = await self.monitor.monitor()
            elif hasattr(self.monitor, 'run'):
                scan_result = await self.monitor.run()
            else:
                logger.error("❌ Monitor не имеет метода scan/monitor/run")
                return result
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            if scan_result:
                result['success'] = True
                result['found'] = scan_result.get('transactions', 0) or scan_result.get('found', 0)
                result['signals'] = scan_result.get('signals', 0)
                result['duration_seconds'] = duration
                
                self.stats['scans_completed'] += 1
                self.stats['total_transactions'] += result['found']
                self.stats['total_signals'] += result['signals']
                self.stats['last_scan_at'] = datetime.utcnow().isoformat()
                
                # Записываем в историю
                self._add_to_history({
                    'operation': 'scan',
                    'timestamp': datetime.utcnow().isoformat(),
                    'result': result
                })
                
                logger.info(f"✅ Scan completed: {result['found']} transactions, {result['signals']} signals ({duration:.1f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка в WhaleSystemIntegration.scan: {e}")
            import traceback
            traceback.print_exc()
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
    
    async def discover_wallets(self, max_results: int = 50) -> Dict[str, Any]:
        """Запуск discovery для поиска новых кошельков"""
        try:
            if not self.smart_discovery and not self.discovery:
                return {'success': False, 'new_wallets': 0, 'error': 'No discovery system available'}
            
            logger.info("🔍 Запуск wallet discovery...")
            
            discovery_system = self.smart_discovery or self.discovery
            
            if hasattr(discovery_system, 'discover'):
                result = await discovery_system.discover(max_results=max_results)
            elif hasattr(discovery_system, 'discover_wallets'):
                result = await discovery_system.discover_wallets(max_results=max_results)
            elif hasattr(discovery_system, 'run'):
                result = await discovery_system.run()
            else:
                logger.warning("⚠️ Discovery system не имеет метода discover/run")
                return {'success': False, 'new_wallets': 0}
            
            if result:
                new_wallets = result.get('new_wallets', 0) or len(result.get('wallets', []))
                self.stats['discoveries_made'] += new_wallets
                self.stats['last_discovery_at'] = datetime.utcnow().isoformat()
                
                self._add_to_history({
                    'operation': 'discovery',
                    'timestamp': datetime.utcnow().isoformat(),
                    'new_wallets': new_wallets
                })
                
                logger.info(f"✅ Discovery completed: {new_wallets} new wallets found")
                
                return {
                    'success': True,
                    'new_wallets': new_wallets,
                    'details': result
                }
            
            return {'success': False, 'new_wallets': 0}
            
        except Exception as e:
            logger.error(f"❌ Ошибка в discover_wallets: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'new_wallets': 0}
    
    async def validate_wallets(self, wallets: List[Dict] = None) -> Dict[str, Any]:
        """Запуск валидации кошельков"""
        try:
            if not self.validator:
                return {'success': False, 'removed': 0, 'error': 'No validator available'}
            
            logger.info("🧹 Запуск wallet validator...")
            
            if hasattr(self.validator, 'validate'):
                result = await self.validator.validate(wallets)
            elif hasattr(self.validator, 'validate_all_wallets'):
                result = await self.validator.validate_all_wallets(wallets or [])
            elif hasattr(self.validator, 'run'):
                result = await self.validator.run()
            elif hasattr(self.validator, 'cleanup'):
                result = await self.validator.cleanup()
            else:
                logger.warning("⚠️ Validator не имеет метода validate/run/cleanup")
                return {'success': False, 'removed': 0}
            
            if result:
                removed = result.get('removed', 0) or result.get('summary', {}).get('remove', 0)
                warnings = result.get('warnings', 0) or result.get('summary', {}).get('warning', 0)
                
                self.stats['validations_done'] += 1
                self.stats['last_validation_at'] = datetime.utcnow().isoformat()
                
                self._add_to_history({
                    'operation': 'validation',
                    'timestamp': datetime.utcnow().isoformat(),
                    'removed': removed,
                    'warnings': warnings
                })
                
                logger.info(f"✅ Validation completed: {removed} removed, {warnings} warnings")
                
                return {
                    'success': True,
                    'removed': removed,
                    'warnings': warnings,
                    'details': result
                }
            
            return {'success': False, 'removed': 0}
            
        except Exception as e:
            logger.error(f"❌ Ошибка в validate_wallets: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'removed': 0}
    
    async def update_learning(self, performance_data: List[Dict] = None) -> Dict[str, Any]:
        """Обновление learning engine"""
        try:
            if not self.learning_engine:
                return {'success': False, 'error': 'No learning engine available'}
            
            logger.info("🧠 Обновление learning engine...")
            
            if hasattr(self.learning_engine, 'update'):
                result = await self.learning_engine.update(performance_data)
            elif hasattr(self.learning_engine, 'train'):
                result = await self.learning_engine.train(performance_data)
            elif hasattr(self.learning_engine, 'update_signal_type_weights'):
                # Синхронная функция
                if performance_data:
                    weights = self.learning_engine.update_signal_type_weights(performance_data)
                    result = {'success': True, 'weights': weights}
                else:
                    result = {'success': False, 'error': 'No performance data'}
            elif hasattr(self.learning_engine, 'learn'):
                result = await self.learning_engine.learn()
            else:
                logger.warning("⚠️ Learning engine не имеет метода update/train/learn")
                return {'success': False}
            
            if result:
                self.stats['learning_updates'] += 1
                self.stats['last_learning_update_at'] = datetime.utcnow().isoformat()
                
                self._add_to_history({
                    'operation': 'learning',
                    'timestamp': datetime.utcnow().isoformat(),
                    'result': result
                })
                
                logger.info(f"✅ Learning update completed")
                
                return {
                    'success': True,
                    'details': result
                }
            
            return {'success': False}
            
        except Exception as e:
            logger.error(f"❌ Ошибка в update_learning: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    async def track_performance(self) -> Dict[str, Any]:
        """Отслеживание производительности сигналов"""
        try:
            if not self.performance_tracker:
                return {'success': False, 'error': 'No performance tracker available'}
            
            logger.debug("📊 Проверка performance...")
            
            if hasattr(self.performance_tracker, 'track'):
                result = await self.performance_tracker.track()
            elif hasattr(self.performance_tracker, 'check'):
                result = await self.performance_tracker.check()
            elif hasattr(self.performance_tracker, 'check_pending_signals'):
                result = await self.performance_tracker.check_pending_signals()
            elif hasattr(self.performance_tracker, 'update'):
                result = await self.performance_tracker.update()
            else:
                logger.warning("⚠️ Performance tracker не имеет метода track/check/update")
                return {'success': False}
            
            if result:
                logger.debug(f"✅ Performance check completed: {result.get('checked', 0)} signals checked")
                
                return {
                    'success': True,
                    'details': result
                }
            
            return {'success': False}
            
        except Exception as e:
            logger.error(f"❌ Ошибка в track_performance: {e}")
            return {'success': False, 'error': str(e)}
    
    async def full_cycle(self) -> Dict[str, Any]:
        """
        Полный цикл работы системы:
        1. Scan (мониторинг)
        2. Performance tracking
        3. Discovery (периодически)
        4. Validation (периодически)
        5. Learning (периодически)
        """
        
        cycle_start = datetime.utcnow()
        results = {
            'cycle_start': cycle_start.isoformat(),
            'scan': None,
            'performance': None,
            'discovery': None,
            'validation': None,
            'learning': None,
            'success': True
        }
        
        try:
            # 1. Основной scan
            results['scan'] = await self.scan()
            
            # 2. Performance tracking (каждый цикл)
            if self.performance_tracker:
                results['performance'] = await self.track_performance()
            
            # 3. Discovery (каждые N циклов)
            if self.discovery and self.stats['scans_completed'] % 10 == 0:
                results['discovery'] = await self.discover_wallets()
            
            # 4. Validation (каждые M циклов)
            if self.validator and self.stats['scans_completed'] % 20 == 0:
                results['validation'] = await self.validate_wallets()
            
            # 5. Learning (каждые K циклов)
            if self.learning_engine and self.stats['scans_completed'] % 50 == 0:
                results['learning'] = await self.update_learning()
            
            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
            results['cycle_duration_seconds'] = cycle_duration
            
            logger.info(f"✅ Full cycle completed in {cycle_duration:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в full_cycle: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику работы системы"""
        return {
            **self.stats,
            'components_active': sum(self.components.values()),
            'components_total': len(self.components),
            'components': self.components,
            'uptime_minutes': self._calculate_uptime(),
            'operations_history_size': len(self.operation_history)
        }
    
    def get_component_status(self) -> Dict[str, bool]:
        """Получить статус всех компонентов"""
        return self.components.copy()
    
    def get_operation_history(self, limit: int = 20) -> List[Dict]:
        """Получить историю операций"""
        return self.operation_history[-limit:]
    
    def _add_to_history(self, operation: Dict):
        """Добавить операцию в историю"""
        self.operation_history.append(operation)
        
        if len(self.operation_history) > self.max_history_size:
            self.operation_history = self.operation_history[-self.max_history_size:]
    
    def _calculate_uptime(self) -> float:
        """Рассчитать uptime в минутах"""
        if self.stats.get('last_scan_at'):
            try:
                last_scan = datetime.fromisoformat(self.stats['last_scan_at'])
                uptime = (datetime.utcnow() - last_scan).total_seconds() / 60
                return uptime
            except:
                pass
        
        return 0.0
    
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
            f"scans={self.stats['scans_completed']}, "
            f"signals={self.stats['total_signals']})"
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