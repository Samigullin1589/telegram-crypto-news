# app/config/database/protocols/__init__.py
"""
Database Configuration Protocols Package
Полный набор протоколов и интерфейсов для типизации
"""

from .base import (
    Validatable,
    Serializable,
    Updatable,
    Configurable,
    Cloneable,
    Comparable,
    Hashable as ConfigHashable
)

from .config import (
    DatabaseConfigProtocol,
    PoolConfigProtocol,
    SSLConfigProtocol,
    TimeoutConfigProtocol,
    RetryConfigProtocol,
    MonitoringConfigProtocol
)

from .database import (
    DatabaseConnectionProtocol,
    DatabaseTransactionProtocol,
    DatabaseCursorProtocol,
    DatabasePoolProtocol,
    DatabaseEngineProtocol
)

from .lifecycle import (
    Initializable,
    Shutdownable,
    Restartable,
    Pauseable,
    Resumable,
    LifecycleManaged
)

from .monitoring import (
    Monitorable,
    HealthCheckable,
    MetricsCollectable,
    Alertable,
    Loggable,
    Traceable
)

from .timing import (
    TimeBasedCheck,
    ScheduledOperation,
    ThrottledOperation,
    RateLimited,
    TimedExecution
)

from .validation import (
    ValidationRule,
    ValidatorProtocol,
    AsyncValidatorProtocol,
    ChainableValidator,
    ConditionalValidator
)

__all__ = [
    # Base protocols
    'Validatable',
    'Serializable',
    'Updatable',
    'Configurable',
    'Cloneable',
    'Comparable',
    'ConfigHashable',
    
    # Config protocols
    'DatabaseConfigProtocol',
    'PoolConfigProtocol',
    'SSLConfigProtocol',
    'TimeoutConfigProtocol',
    'RetryConfigProtocol',
    'MonitoringConfigProtocol',
    
    # Database protocols
    'DatabaseConnectionProtocol',
    'DatabaseTransactionProtocol',
    'DatabaseCursorProtocol',
    'DatabasePoolProtocol',
    'DatabaseEngineProtocol',
    
    # Lifecycle protocols
    'Initializable',
    'Shutdownable',
    'Restartable',
    'Pauseable',
    'Resumable',
    'LifecycleManaged',
    
    # Monitoring protocols
    'Monitorable',
    'HealthCheckable',
    'MetricsCollectable',
    'Alertable',
    'Loggable',
    'Traceable',
    
    # Timing protocols
    'TimeBasedCheck',
    'ScheduledOperation',
    'ThrottledOperation',
    'RateLimited',
    'TimedExecution',
    
    # Validation protocols
    'ValidationRule',
    'ValidatorProtocol',
    'AsyncValidatorProtocol',
    'ChainableValidator',
    'ConditionalValidator',
]