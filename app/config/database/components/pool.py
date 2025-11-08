"""
Database Connection Pool Configuration
Конфигурация пула соединений с продвинутыми стратегиями
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

from ..base import BaseConfig
from ..exceptions import ValidationError
from ..validators import validate_positive, validate_range

logger = logging.getLogger(__name__)


class PoolStrategy(str, Enum):
    """
    Стратегии управления пулом соединений
    
    CONSERVATIVE - Консервативная (малый pool, малый overflow)
    BALANCED - Сбалансированная (средние значения)
    AGGRESSIVE - Агрессивная (большой pool, большой overflow)
    CUSTOM - Кастомная конфигурация
    """
    CONSERVATIVE = 'CONSERVATIVE'
    BALANCED = 'BALANCED'
    AGGRESSIVE = 'AGGRESSIVE'
    CUSTOM = 'CUSTOM'


class PoolHealthStatus(str, Enum):
    """Статусы здоровья пула"""
    HEALTHY = 'HEALTHY'
    DEGRADED = 'DEGRADED'
    CRITICAL = 'CRITICAL'
    UNKNOWN = 'UNKNOWN'


@dataclass
class DatabaseConnectionPoolConfig(BaseConfig):
    """
    Конфигурация пула соединений с валидацией и стратегиями
    
    Attributes:
        pool_size: Размер постоянного пула
        max_overflow: Максимальное количество дополнительных соединений
        pool_recycle: Время переиспользования соединения (секунды)
        pool_timeout: Таймаут получения соединения (секунды)
        pool_pre_ping: Проверка соединения перед использованием
        echo: Логирование SQL запросов
        echo_pool: Логирование операций пула
        strategy: Стратегия управления пулом
    """
    
    pool_size: int = 5
    max_overflow: int = 10
    pool_recycle: int = 3600
    pool_timeout: int = 30
    pool_pre_ping: bool = True
    echo: bool = False
    echo_pool: bool = False
    strategy: PoolStrategy = PoolStrategy.BALANCED
    
    # Расширенные параметры
    pool_reset_on_return: str = 'rollback'  # rollback, commit, none
    pool_use_lifo: bool = False  # Last-in-first-out вместо FIFO
    max_identifier_length: Optional[int] = None
    
    # Метрики (заполняются во время работы)
    _current_connections: int = field(default=0, init=False, repr=False)
    _peak_connections: int = field(default=0, init=False, repr=False)
    _health_status: PoolHealthStatus = field(
        default=PoolHealthStatus.UNKNOWN, 
        init=False, 
        repr=False
    )
    
    def __post_init__(self):
        """Применение стратегии и валидация"""
        self._apply_strategy()
        super().__post_init__()
    
    def _apply_strategy(self) -> None:
        """Применение выбранной стратегии к параметрам пула"""
        if self.strategy == PoolStrategy.CONSERVATIVE:
            self.pool_size = min(self.pool_size, 3)
            self.max_overflow = min(self.max_overflow, 5)
            self.pool_timeout = max(self.pool_timeout, 10)
            logger.info("Applied CONSERVATIVE pool strategy")
        
        elif self.strategy == PoolStrategy.BALANCED:
            if self.pool_size < 3:
                self.pool_size = 5
            if self.max_overflow < 5:
                self.max_overflow = 10
            logger.info("Applied BALANCED pool strategy")
        
        elif self.strategy == PoolStrategy.AGGRESSIVE:
            self.pool_size = max(self.pool_size, 10)
            self.max_overflow = max(self.max_overflow, 20)
            self.pool_timeout = min(self.pool_timeout, 60)
            logger.info("Applied AGGRESSIVE pool strategy")
    
    def validate(self) -> bool:
        """Валидация параметров пула"""
        # Валидация pool_size
        if self.pool_size < 1:
            raise ValidationError(
                field='pool_size',
                value=self.pool_size,
                reason='must be >= 1'
            )
        
        # Валидация max_overflow
        if self.max_overflow < 0:
            raise ValidationError(
                field='max_overflow',
                value=self.max_overflow,
                reason='must be >= 0'
            )
        
        # Валидация pool_recycle
        if self.pool_recycle < 0:
            raise ValidationError(
                field='pool_recycle',
                value=self.pool_recycle,
                reason='must be >= 0 (0 = disabled)'
            )
        
        # Валидация pool_timeout
        if self.pool_timeout < 1:
            raise ValidationError(
                field='pool_timeout',
                value=self.pool_timeout,
                reason='must be >= 1'
            )
        
        # Валидация pool_reset_on_return
        valid_reset_values = ['rollback', 'commit', 'none']
        if self.pool_reset_on_return not in valid_reset_values:
            raise ValidationError(
                field='pool_reset_on_return',
                value=self.pool_reset_on_return,
                reason=f'must be one of {valid_reset_values}'
            )
        
        # Предупреждения
        total_connections = self.total_connections
        if total_connections > 100:
            logger.warning(
                f"Total connections ({total_connections}) is very high. "
                f"This may cause resource exhaustion. Recommended: <= 100"
            )
        
        if total_connections > 50 and self.pool_pre_ping:
            logger.warning(
                f"pool_pre_ping with {total_connections} connections may impact "
                f"performance. Consider disabling for large pools."
            )
        
        if self.echo and not logger.isEnabledFor(logging.DEBUG):
            logger.warning(
                "SQL echo is enabled but log level is not DEBUG. "
                "You won't see SQL queries in logs."
            )
        
        return True
    
    @property
    def total_connections(self) -> int:
        """Общее количество возможных соединений"""
        return self.pool_size + self.max_overflow
    
    @property
    def is_healthy(self) -> bool:
        """Проверка здоровья пула"""
        return self._health_status == PoolHealthStatus.HEALTHY
    
    def update_metrics(
        self, 
        current_connections: int, 
        peak_connections: Optional[int] = None
    ) -> None:
        """
        Обновление метрик пула
        
        Args:
            current_connections: Текущее количество активных соединений
            peak_connections: Пиковое количество соединений
        """
        self._current_connections = current_connections
        
        if peak_connections is not None:
            self._peak_connections = max(self._peak_connections, peak_connections)
        else:
            self._peak_connections = max(self._peak_connections, current_connections)
        
        # Обновление статуса здоровья
        utilization = current_connections / self.total_connections
        
        if utilization < 0.7:
            self._health_status = PoolHealthStatus.HEALTHY
        elif utilization < 0.9:
            self._health_status = PoolHealthStatus.DEGRADED
        else:
            self._health_status = PoolHealthStatus.CRITICAL
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик пула
        
        Returns:
            Словарь с метриками
        """
        utilization = 0.0
        if self.total_connections > 0:
            utilization = self._current_connections / self.total_connections
        
        return {
            'current_connections': self._current_connections,
            'peak_connections': self._peak_connections,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'total_capacity': self.total_connections,
            'utilization_percent': utilization * 100,
            'health_status': self._health_status.value,
            'is_healthy': self.is_healthy
        }
    
    def get_sqlalchemy_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации для SQLAlchemy
        
        Returns:
            Словарь параметров для create_engine
        """
        config = {
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'pool_pre_ping': self.pool_pre_ping,
            'echo': self.echo,
            'echo_pool': self.echo_pool,
            'pool_use_lifo': self.pool_use_lifo,
        }
        
        if self.pool_recycle > 0:
            config['pool_recycle'] = self.pool_recycle
        
        if self.pool_reset_on_return != 'rollback':  # rollback - default
            config['pool_reset_on_return'] = self.pool_reset_on_return
        
        if self.max_identifier_length:
            config['max_identifier_length'] = self.max_identifier_length
        
        return config
    
    def adjust_for_load(self, load_factor: float) -> None:
        """
        Динамическая настройка пула под нагрузку
        
        Args:
            load_factor: Коэффициент нагрузки (0.0 - 1.0+)
        """
        if load_factor > 1.5 and self.strategy != PoolStrategy.AGGRESSIVE:
            logger.info("High load detected, switching to AGGRESSIVE strategy")
            self.strategy = PoolStrategy.AGGRESSIVE
            self._apply_strategy()
            self.validate()
        
        elif load_factor < 0.3 and self.strategy != PoolStrategy.CONSERVATIVE:
            logger.info("Low load detected, switching to CONSERVATIVE strategy")
            self.strategy = PoolStrategy.CONSERVATIVE
            self._apply_strategy()
            self.validate()