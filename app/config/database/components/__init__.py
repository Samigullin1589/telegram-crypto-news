"""
Экспорт всех компонентов оптимизации БД

Этот модуль предоставляет единую точку импорта для всех компонентов
системы оптимизации базы данных.
"""

from .backup import (
    BackupConfig,
    BackupStrategy,
    BackupSchedule
)

from .pool import (
    ConnectionPoolConfig,
    PoolStrategy,
    HealthCheckConfig
)

from .pragma import (
    PragmaConfig,
    PragmaSettings,
    WorkMemConfig,
    MaintenanceWorkMemConfig,
    EffectiveCacheConfig,
    RandomPageCostConfig,
    WalConfig
)

from .indexes import (
    IndexConfig,
    IndexType,
    IndexHealth,
    IndexMetrics,
    IndexRecommendation
)

from .partitions import (
    PartitionConfig,
    PartitionStrategy,
    PartitionPeriod,
    PartitionInfo
)

from .vacuum import (
    VacuumConfig,
    VacuumStrategy,
    VacuumPriority,
    TableVacuumMetrics,
    VacuumOperation
)

from .cache import (
    CacheConfig,
    CacheLevel,
    EvictionPolicy,
    CacheEntry,
    HotKey
)

from .monitoring import (
    DatabaseMonitor,
    HealthStatus,
    AlertSeverity,
    MetricThreshold,
    MetricDataPoint,
    Alert,
    PerformanceBaseline
)

from .statistics import (
    DatabaseStatistics,
    StatisticsPeriod,
    QueryStatistics,
    TableStatistics,
    ConnectionStatistics
)

from .query_analyzer import (
    QueryAnalyzer,
    QueryType,
    QueryIssue,
    QueryPlan,
    QueryRecommendation
)

__all__ = [
    # Backup
    'BackupConfig',
    'BackupStrategy',
    'BackupSchedule',
    
    # Pool
    'ConnectionPoolConfig',
    'PoolStrategy',
    'HealthCheckConfig',
    
    # Pragma
    'PragmaConfig',
    'PragmaSettings',
    'WorkMemConfig',
    'MaintenanceWorkMemConfig',
    'EffectiveCacheConfig',
    'RandomPageCostConfig',
    'WalConfig',
    
    # Indexes
    'IndexConfig',
    'IndexType',
    'IndexHealth',
    'IndexMetrics',
    'IndexRecommendation',
    
    # Partitions
    'PartitionConfig',
    'PartitionStrategy',
    'PartitionPeriod',
    'PartitionInfo',
    
    # Vacuum
    'VacuumConfig',
    'VacuumStrategy',
    'VacuumPriority',
    'TableVacuumMetrics',
    'VacuumOperation',
    
    # Cache
    'CacheConfig',
    'CacheLevel',
    'EvictionPolicy',
    'CacheEntry',
    'HotKey',
    
    # Monitoring
    'DatabaseMonitor',
    'HealthStatus',
    'AlertSeverity',
    'MetricThreshold',
    'MetricDataPoint',
    'Alert',
    'PerformanceBaseline',
    
    # Statistics
    'DatabaseStatistics',
    'StatisticsPeriod',
    'QueryStatistics',
    'TableStatistics',
    'ConnectionStatistics',
    
    # Query Analyzer
    'QueryAnalyzer',
    'QueryType',
    'QueryIssue',
    'QueryPlan',
    'QueryRecommendation'
]