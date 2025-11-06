"""
Resource Monitor - Production Grade

Мониторинг системных ресурсов с:
- Отслеживанием использования памяти
- Автоматическим garbage collection
- CPU мониторингом
- Thread tracking
- Memory warnings и alerts
"""

import gc
import logging
import psutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """
    Production-grade мониторинг системных ресурсов
    
    Features:
    - Memory usage tracking
    - Automatic garbage collection
    - CPU monitoring
    - Thread counting
    - Configurable thresholds
    - Warning system
    """
    
    def __init__(self, max_memory_mb: int = 450):
        """
        Инициализация Resource Monitor
        
        Args:
            max_memory_mb: Максимальный лимит памяти в MB
        """
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()
        
        # GC management
        self.last_gc = datetime.now(timezone.utc)
        self.gc_interval = 300  # 5 minutes
        self.gc_runs = 0
        
        # Warning tracking
        self.memory_warnings = 0
        self.critical_warnings = 0
        
        # Thresholds
        self.warning_threshold = 0.85  # 85% of max
        self.critical_threshold = 0.95  # 95% of max
        
        logger.info("💾 [RESOURCE] Resource Monitor инициализирован")
        logger.info(f"   Max Memory: {self.max_memory_mb}MB")
        logger.info(f"   Warning Threshold: {int(self.warning_threshold * 100)}%")
        logger.info(f"   Critical Threshold: {int(self.critical_threshold * 100)}%")
        logger.info(f"   GC Interval: {self.gc_interval}s")
    
    def check_memory(self) -> bool:
        """
        Проверка использования памяти с автоматическим GC
        
        Returns:
            bool: True если память в норме, False если превышен лимит
        """
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = memory_mb / self.max_memory_mb
            
            # Check thresholds
            if memory_percent >= self.critical_threshold:
                self.critical_warnings += 1
                logger.error(
                    f"🚨 [MEMORY] CRITICAL: {memory_mb:.1f}MB / {self.max_memory_mb}MB "
                    f"({memory_percent*100:.1f}%)"
                )
                self._force_gc(memory_mb)
                
                # Check again after GC
                memory_info_after = self.process.memory_info()
                memory_mb_after = memory_info_after.rss / 1024 / 1024
                
                if memory_mb_after > self.max_memory_mb:
                    logger.error(
                        f"🚨 [MEMORY] STILL OVER LIMIT after GC: {memory_mb_after:.1f}MB"
                    )
                    return False
                
                return True
            
            elif memory_percent >= self.warning_threshold:
                self.memory_warnings += 1
                logger.warning(
                    f"⚠️ [MEMORY] WARNING: {memory_mb:.1f}MB / {self.max_memory_mb}MB "
                    f"({memory_percent*100:.1f}%)"
                )
                self._force_gc(memory_mb)
                return True
            
            elif memory_mb > self.max_memory_mb:
                # Hard limit exceeded
                self.memory_warnings += 1
                logger.warning(
                    f"⚠️ [MEMORY] Over limit: {memory_mb:.1f}MB / {self.max_memory_mb}MB"
                )
                self._force_gc(memory_mb)
                
                # Check after GC
                memory_info_after = self.process.memory_info()
                memory_mb_after = memory_info_after.rss / 1024 / 1024
                
                if memory_mb_after > self.max_memory_mb:
                    return False
                
                return True
            
            # Memory is fine
            logger.debug(
                f"[MEMORY] OK: {memory_mb:.1f}MB / {self.max_memory_mb}MB "
                f"({memory_percent*100:.1f}%)"
            )
            return True
        
        except Exception as e:
            logger.error(f"❌ [MEMORY] Ошибка проверки памяти: {e}")
            return True  # Don't fail on monitoring errors
    
    def _force_gc(self, memory_before: float):
        """
        Принудительный запуск garbage collection
        
        Args:
            memory_before: Использование памяти до GC в MB
        """
        logger.info("   🗑️ Запуск garbage collection...")
        
        collected = gc.collect()
        self.gc_runs += 1
        self.last_gc = datetime.now(timezone.utc)
        
        try:
            memory_info_after = self.process.memory_info()
            memory_after = memory_info_after.rss / 1024 / 1024
            freed = memory_before - memory_after
            
            logger.info(
                f"   ✓ GC завершён: освобождено {freed:.1f}MB, "
                f"собрано {collected} объектов"
            )
            logger.info(f"   ✓ Текущая память: {memory_after:.1f}MB")
        except Exception as e:
            logger.warning(f"   ⚠️ Не удалось получить память после GC: {e}")
    
    def should_run_gc(self) -> bool:
        """
        Проверка, нужно ли запускать GC
        
        Returns:
            bool: True если пора запустить GC
        """
        elapsed = (datetime.now(timezone.utc) - self.last_gc).total_seconds()
        return elapsed >= self.gc_interval
    
    def run_scheduled_gc(self):
        """Запуск планового GC если пришло время"""
        if self.should_run_gc():
            try:
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                logger.info(f"🗑️ [GC] Плановый GC (память: {memory_mb:.1f}MB)")
                self._force_gc(memory_mb)
            except Exception as e:
                logger.error(f"❌ [GC] Ошибка планового GC: {e}")
    
    def get_memory_mb(self) -> float:
        """
        Получить текущее использование памяти
        
        Returns:
            float: Память в MB
        """
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / 1024 / 1024
        except Exception as e:
            logger.error(f"❌ [MEMORY] Ошибка получения памяти: {e}")
            return 0.0
    
    def get_memory_percent(self) -> float:
        """
        Получить процент использования памяти от лимита
        
        Returns:
            float: Процент (0-100)
        """
        memory_mb = self.get_memory_mb()
        return (memory_mb / self.max_memory_mb) * 100 if self.max_memory_mb > 0 else 0.0
    
    def get_cpu_percent(self, interval: float = 0.1) -> float:
        """
        Получить процент использования CPU
        
        Args:
            interval: Интервал измерения в секундах
            
        Returns:
            float: Процент CPU
        """
        try:
            return self.process.cpu_percent(interval=interval)
        except Exception as e:
            logger.error(f"❌ [CPU] Ошибка получения CPU: {e}")
            return 0.0
    
    def get_thread_count(self) -> int:
        """
        Получить количество потоков
        
        Returns:
            int: Количество потоков
        """
        try:
            return self.process.num_threads()
        except Exception as e:
            logger.error(f"❌ [THREADS] Ошибка получения потоков: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получить полную статистику ресурсов
        
        Returns:
            Dict со всей статистикой
        """
        try:
            memory_mb = self.get_memory_mb()
            memory_percent_of_limit = self.get_memory_percent()
            system_memory_percent = self.process.memory_percent()
            cpu_percent = self.get_cpu_percent()
            num_threads = self.get_thread_count()
            
            # Get system-wide memory info
            system_memory = psutil.virtual_memory()
            
            return {
                'memory_mb': round(memory_mb, 2),
                'memory_percent_of_limit': round(memory_percent_of_limit, 2),
                'memory_percent_system': round(system_memory_percent, 2),
                'cpu_percent': round(cpu_percent, 2),
                'num_threads': num_threads,
                'max_memory_mb': self.max_memory_mb,
                'memory_warnings': self.memory_warnings,
                'critical_warnings': self.critical_warnings,
                'gc_runs': self.gc_runs,
                'last_gc': self.last_gc.isoformat(),
                'system_memory_total_mb': round(system_memory.total / 1024 / 1024, 2),
                'system_memory_available_mb': round(system_memory.available / 1024 / 1024, 2),
                'system_memory_percent': round(system_memory.percent, 2),
            }
        
        except Exception as e:
            logger.error(f"❌ [RESOURCE] Ошибка получения статистики: {e}")
            return {
                'error': str(e),
                'memory_warnings': self.memory_warnings,
                'critical_warnings': self.critical_warnings,
                'gc_runs': self.gc_runs,
            }
    
    def print_stats(self):
        """Вывести статистику в лог"""
        stats = self.get_stats()
        
        if 'error' in stats:
            logger.error(f"❌ [RESOURCE] Ошибка получения статистики: {stats['error']}")
            return
        
        logger.info("\n💾 [RESOURCE] Статистика ресурсов:")
        logger.info(
            f"   Память процесса: {stats['memory_mb']}MB / {stats['max_memory_mb']}MB "
            f"({stats['memory_percent_of_limit']:.1f}%)"
        )
        logger.info(f"   Память системы: {stats['memory_percent_system']:.1f}%")
        logger.info(
            f"   Система: {stats['system_memory_available_mb']:.0f}MB доступно из "
            f"{stats['system_memory_total_mb']:.0f}MB"
        )
        logger.info(f"   CPU: {stats['cpu_percent']:.1f}%")
        logger.info(f"   Потоки: {stats['num_threads']}")
        logger.info(f"   GC запусков: {stats['gc_runs']}")
        logger.info(f"   Предупреждений: {stats['memory_warnings']}")
        logger.info(f"   Критических: {stats['critical_warnings']}")
    
    def reset_warnings(self):
        """Сброс счетчиков предупреждений"""
        self.memory_warnings = 0
        self.critical_warnings = 0
        logger.info("[RESOURCE] Счетчики предупреждений сброшены")
    
    def set_memory_limit(self, max_memory_mb: int):
        """
        Установить новый лимит памяти
        
        Args:
            max_memory_mb: Новый лимит в MB
        """
        old_limit = self.max_memory_mb
        self.max_memory_mb = max_memory_mb
        logger.info(f"[RESOURCE] Лимит памяти изменён: {old_limit}MB -> {max_memory_mb}MB")
    
    def is_memory_critical(self) -> bool:
        """
        Проверка критического состояния памяти
        
        Returns:
            bool: True если память в критическом состоянии
        """
        memory_mb = self.get_memory_mb()
        return memory_mb > (self.max_memory_mb * self.critical_threshold)
    
    def is_memory_warning(self) -> bool:
        """
        Проверка предупреждающего состояния памяти
        
        Returns:
            bool: True если память в предупреждающем состоянии
        """
        memory_mb = self.get_memory_mb()
        return memory_mb > (self.max_memory_mb * self.warning_threshold)