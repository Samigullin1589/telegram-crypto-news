"""
Компонент мониторинга здоровья и производительности БД

Архитектурные решения:
- Непрерывный мониторинг критических метрик
- Обнаружение аномалий и деградации производительности
- Предсказание проблем на основе трендов
- Алертинг по пороговым значениям
- Корреляция метрик для выявления первопричин
"""

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Deque, Tuple


class HealthStatus(Enum):
    """Статус здоровья"""
    HEALTHY = 'healthy'
    WARNING = 'warning'
    CRITICAL = 'critical'
    UNKNOWN = 'unknown'


class AlertSeverity(Enum):
    """Серьезность алерта"""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


@dataclass
class MetricThreshold:
    """Пороги для метрики"""
    name: str
    warning_threshold: float
    critical_threshold: float
    comparison: str = 'gt'  # 'gt' (greater than) or 'lt' (less than)
    window_seconds: int = 300  # Окно для расчета среднего
    
    def check(self, value: float) -> Optional[AlertSeverity]:
        """
        Проверка значения на превышение порогов
        
        Args:
            value: Текущее значение
            
        Returns:
            Серьезность или None если в норме
        """
        if self.comparison == 'gt':
            if value >= self.critical_threshold:
                return AlertSeverity.CRITICAL
            elif value >= self.warning_threshold:
                return AlertSeverity.WARNING
        else:  # 'lt'
            if value <= self.critical_threshold:
                return AlertSeverity.CRITICAL
            elif value <= self.warning_threshold:
                return AlertSeverity.WARNING
        
        return None


@dataclass
class MetricDataPoint:
    """Точка данных метрики"""
    timestamp: float
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Алерт"""
    id: str
    severity: AlertSeverity
    metric_name: str
    message: str
    current_value: float
    threshold_value: float
    created_at: float
    resolved_at: Optional[float] = None
    acknowledged: bool = False
    
    @property
    def is_active(self) -> bool:
        """Активен ли алерт"""
        return self.resolved_at is None
    
    @property
    def duration_seconds(self) -> float:
        """Длительность алерта"""
        end_time = self.resolved_at or time.time()
        return end_time - self.created_at


@dataclass
class PerformanceBaseline:
    """Baseline производительности"""
    metric_name: str
    avg_value: float
    min_value: float
    max_value: float
    std_dev: float
    sample_count: int
    calculated_at: float
    
    def is_anomaly(self, value: float, sigma: float = 2.0) -> bool:
        """
        Проверка на аномалию (отклонение от baseline)
        
        Args:
            value: Текущее значение
            sigma: Количество стандартных отклонений
            
        Returns:
            True если значение аномально
        """
        lower_bound = self.avg_value - (sigma * self.std_dev)
        upper_bound = self.avg_value + (sigma * self.std_dev)
        return value < lower_bound or value > upper_bound


class DatabaseMonitor:
    """
    Мониторинг здоровья и производительности БД
    
    Ответственности:
    - Сбор метрик в реальном времени
    - Обнаружение аномалий
    - Генерация алертов
    - Расчет baseline производительности
    - Предсказание проблем
    """
    
    def __init__(
        self,
        enabled: bool = True,
        
        # Сбор метрик
        collection_interval_seconds: int = 60,
        history_retention_hours: int = 24,
        
        # Baseline
        baseline_calculation_hours: int = 168,  # 7 дней
        recalculate_baseline_hours: int = 24,
        
        # Аномалии
        anomaly_detection_enabled: bool = True,
        anomaly_sensitivity: float = 2.0,  # Количество sigma
        
        # Алерты
        alerting_enabled: bool = True,
        alert_cooldown_seconds: int = 300,  # Cooldown между повторными алертами
        auto_resolve_alerts: bool = True,
        
        # Предсказания
        trend_analysis_enabled: bool = True,
        prediction_window_hours: int = 6
    ):
        self.enabled = enabled
        self.collection_interval_seconds = collection_interval_seconds
        self.history_retention_hours = history_retention_hours
        
        self.baseline_calculation_hours = baseline_calculation_hours
        self.recalculate_baseline_hours = recalculate_baseline_hours
        
        self.anomaly_detection_enabled = anomaly_detection_enabled
        self.anomaly_sensitivity = anomaly_sensitivity
        
        self.alerting_enabled = alerting_enabled
        self.alert_cooldown_seconds = alert_cooldown_seconds
        self.auto_resolve_alerts = auto_resolve_alerts
        
        self.trend_analysis_enabled = trend_analysis_enabled
        self.prediction_window_hours = prediction_window_hours
        
        # Хранение метрик (циклические буферы)
        self._metrics_history: Dict[str, Deque[MetricDataPoint]] = {}
        self._max_datapoints = (history_retention_hours * 3600) // collection_interval_seconds
        
        # Baselines
        self._baselines: Dict[str, PerformanceBaseline] = {}
        self._last_baseline_calculation: Optional[float] = None
        
        # Пороги
        self._thresholds: Dict[str, MetricThreshold] = {}
        self._initialize_default_thresholds()
        
        # Алерты
        self._active_alerts: Dict[str, Alert] = {}  # metric_name -> Alert
        self._alert_history: Deque[Alert] = deque(maxlen=1000)
        self._last_alert_time: Dict[str, float] = {}  # metric_name -> timestamp
        
        # Статистика
        self._total_alerts_generated = 0
        self._total_alerts_resolved = 0
        self._total_anomalies_detected = 0
        self._last_collection_time: Optional[float] = None
        
        # Здоровье компонентов
        self._component_health: Dict[str, HealthStatus] = {}
        self._overall_health: HealthStatus = HealthStatus.UNKNOWN
    
    def _initialize_default_thresholds(self) -> None:
        """Инициализация пороговых значений по умолчанию"""
        self._thresholds = {
            # Connection pool
            'connection_utilization_percent': MetricThreshold(
                name='connection_utilization_percent',
                warning_threshold=80.0,
                critical_threshold=95.0,
                comparison='gt'
            ),
            
            # Queries
            'slow_queries_per_minute': MetricThreshold(
                name='slow_queries_per_minute',
                warning_threshold=10.0,
                critical_threshold=50.0,
                comparison='gt'
            ),
            
            # Locks
            'lock_wait_time_ms': MetricThreshold(
                name='lock_wait_time_ms',
                warning_threshold=100.0,
                critical_threshold=1000.0,
                comparison='gt'
            ),
            
            # Deadlocks
            'deadlocks_per_hour': MetricThreshold(
                name='deadlocks_per_hour',
                warning_threshold=1.0,
                critical_threshold=5.0,
                comparison='gt'
            ),
            
            # Cache
            'cache_hit_rate_percent': MetricThreshold(
                name='cache_hit_rate_percent',
                warning_threshold=80.0,
                critical_threshold=60.0,
                comparison='lt'
            ),
            
            # Bloat
            'table_bloat_percent': MetricThreshold(
                name='table_bloat_percent',
                warning_threshold=20.0,
                critical_threshold=40.0,
                comparison='gt'
            ),
            
            # Replication lag
            'replication_lag_seconds': MetricThreshold(
                name='replication_lag_seconds',
                warning_threshold=10.0,
                critical_threshold=60.0,
                comparison='gt'
            ),
            
            # Disk
            'disk_usage_percent': MetricThreshold(
                name='disk_usage_percent',
                warning_threshold=80.0,
                critical_threshold=90.0,
                comparison='gt'
            ),
            
            # CPU
            'cpu_usage_percent': MetricThreshold(
                name='cpu_usage_percent',
                warning_threshold=70.0,
                critical_threshold=90.0,
                comparison='gt'
            ),
            
            # Memory
            'memory_usage_percent': MetricThreshold(
                name='memory_usage_percent',
                warning_threshold=80.0,
                critical_threshold=95.0,
                comparison='gt'
            )
        }
    
    def record_metric(
        self,
        name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Запись значения метрики
        
        Args:
            name: Имя метрики
            value: Значение
            metadata: Дополнительные данные
        """
        if not self.enabled:
            return
        
        current_time = time.time()
        
        # Создание истории для метрики если не существует
        if name not in self._metrics_history:
            self._metrics_history[name] = deque(maxlen=self._max_datapoints)
        
        # Добавление точки данных
        datapoint = MetricDataPoint(
            timestamp=current_time,
            value=value,
            metadata=metadata or {}
        )
        self._metrics_history[name].append(datapoint)
        
        # Проверка порогов
        if self.alerting_enabled and name in self._thresholds:
            self._check_threshold(name, value, current_time)
        
        # Обнаружение аномалий
        if self.anomaly_detection_enabled and name in self._baselines:
            self._check_anomaly(name, value, current_time)
        
        self._last_collection_time = current_time
    
    def _check_threshold(self, metric_name: str, value: float, timestamp: float) -> None:
        """
        Проверка пороговых значений
        
        Args:
            metric_name: Имя метрики
            value: Значение
            timestamp: Время
        """
        threshold = self._thresholds[metric_name]
        
        # Проверка cooldown
        if metric_name in self._last_alert_time:
            time_since_last = timestamp - self._last_alert_time[metric_name]
            if time_since_last < self.alert_cooldown_seconds:
                return
        
        # Проверка порога
        severity = threshold.check(value)
        
        if severity:
            # Создание алерта
            alert_id = f"{metric_name}_{int(timestamp)}"
            
            alert = Alert(
                id=alert_id,
                severity=severity,
                metric_name=metric_name,
                message=self._generate_alert_message(metric_name, value, threshold),
                current_value=value,
                threshold_value=threshold.warning_threshold if severity == AlertSeverity.WARNING else threshold.critical_threshold,
                created_at=timestamp
            )
            
            self._active_alerts[metric_name] = alert
            self._alert_history.append(alert)
            self._last_alert_time[metric_name] = timestamp
            self._total_alerts_generated += 1
        
        elif self.auto_resolve_alerts and metric_name in self._active_alerts:
            # Автоматическое разрешение алерта
            alert = self._active_alerts[metric_name]
            alert.resolved_at = timestamp
            del self._active_alerts[metric_name]
            self._total_alerts_resolved += 1
    
    def _check_anomaly(self, metric_name: str, value: float, timestamp: float) -> None:
        """
        Проверка на аномалию
        
        Args:
            metric_name: Имя метрики
            value: Значение
            timestamp: Время
        """
        baseline = self._baselines[metric_name]
        
        if baseline.is_anomaly(value, self.anomaly_sensitivity):
            self._total_anomalies_detected += 1
            
            # Можно создать алерт для аномалии
            if self.alerting_enabled:
                alert_key = f"{metric_name}_anomaly"
                
                if alert_key not in self._last_alert_time or \
                   (timestamp - self._last_alert_time[alert_key]) > self.alert_cooldown_seconds:
                    
                    alert_id = f"{alert_key}_{int(timestamp)}"
                    alert = Alert(
                        id=alert_id,
                        severity=AlertSeverity.WARNING,
                        metric_name=metric_name,
                        message=f"Anomaly detected: {metric_name} = {value:.2f} (baseline: {baseline.avg_value:.2f} ± {baseline.std_dev:.2f})",
                        current_value=value,
                        threshold_value=baseline.avg_value,
                        created_at=timestamp
                    )
                    
                    self._alert_history.append(alert)
                    self._last_alert_time[alert_key] = timestamp
    
    def _generate_alert_message(
        self,
        metric_name: str,
        value: float,
        threshold: MetricThreshold
    ) -> str:
        """Генерация сообщения алерта"""
        comparison_text = "above" if threshold.comparison == 'gt' else "below"
        
        return (
            f"{metric_name} is {comparison_text} threshold: "
            f"current={value:.2f}, warning={threshold.warning_threshold:.2f}, "
            f"critical={threshold.critical_threshold:.2f}"
        )
    
    def calculate_baseline(self, metric_name: str) -> Optional[PerformanceBaseline]:
        """
        Расчет baseline для метрики
        
        Args:
            metric_name: Имя метрики
            
        Returns:
            Baseline или None
        """
        if metric_name not in self._metrics_history:
            return None
        
        history = self._metrics_history[metric_name]
        
        # Нужно достаточно данных
        min_samples = (self.baseline_calculation_hours * 3600) // self.collection_interval_seconds
        if len(history) < min_samples:
            return None
        
        # Извлечение значений
        values = [dp.value for dp in history]
        
        # Расчет статистики
        n = len(values)
        avg = sum(values) / n
        min_val = min(values)
        max_val = max(values)
        
        # Стандартное отклонение
        variance = sum((x - avg) ** 2 for x in values) / n
        std_dev = variance ** 0.5
        
        baseline = PerformanceBaseline(
            metric_name=metric_name,
            avg_value=avg,
            min_value=min_val,
            max_value=max_val,
            std_dev=std_dev,
            sample_count=n,
            calculated_at=time.time()
        )
        
        self._baselines[metric_name] = baseline
        self._last_baseline_calculation = time.time()
        
        return baseline
    
    def calculate_all_baselines(self) -> int:
        """
        Расчет baselines для всех метрик
        
        Returns:
            Количество рассчитанных baselines
        """
        calculated = 0
        
        for metric_name in self._metrics_history.keys():
            if self.calculate_baseline(metric_name):
                calculated += 1
        
        return calculated
    
    def should_recalculate_baselines(self) -> bool:
        """Нужно ли пересчитывать baselines"""
        if not self._last_baseline_calculation:
            return True
        
        hours_since = (time.time() - self._last_baseline_calculation) / 3600
        return hours_since >= self.recalculate_baseline_hours
    
    def get_metric_trend(
        self,
        metric_name: str,
        window_minutes: int = 60
    ) -> Optional[Dict[str, Any]]:
        """
        Получение тренда метрики
        
        Args:
            metric_name: Имя метрики
            window_minutes: Окно для анализа в минутах
            
        Returns:
            Словарь с информацией о тренде
        """
        if metric_name not in self._metrics_history:
            return None
        
        history = self._metrics_history[metric_name]
        if len(history) < 2:
            return None
        
        # Фильтрация по времени
        cutoff_time = time.time() - (window_minutes * 60)
        recent_points = [dp for dp in history if dp.timestamp >= cutoff_time]
        
        if len(recent_points) < 2:
            return None
        
        # Расчет тренда (простая линейная регрессия)
        n = len(recent_points)
        x_values = list(range(n))
        y_values = [dp.value for dp in recent_points]
        
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        # Slope
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Направление тренда
        if abs(slope) < 0.01:
            direction = 'stable'
        elif slope > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'
        
        # Прогноз
        predicted_value = y_values[-1] + (slope * (self.prediction_window_hours * 60 / window_minutes))
        
        return {
            'metric_name': metric_name,
            'direction': direction,
            'slope': slope,
            'current_value': y_values[-1],
            'predicted_value': predicted_value,
            'prediction_hours_ahead': self.prediction_window_hours,
            'sample_count': n,
            'window_minutes': window_minutes
        }
    
    def predict_issues(self) -> List[Dict[str, Any]]:
        """
        Предсказание потенциальных проблем на основе трендов
        
        Returns:
            Список предсказанных проблем
        """
        if not self.trend_analysis_enabled:
            return []
        
        predictions = []
        
        for metric_name, threshold in self._thresholds.items():
            trend = self.get_metric_trend(metric_name, window_minutes=60)
            
            if not trend:
                continue
            
            predicted = trend['predicted_value']
            
            # Проверка прогноза на пороги
            if threshold.comparison == 'gt':
                if predicted >= threshold.critical_threshold:
                    predictions.append({
                        'metric': metric_name,
                        'severity': 'critical',
                        'current': trend['current_value'],
                        'predicted': predicted,
                        'threshold': threshold.critical_threshold,
                        'hours_ahead': self.prediction_window_hours,
                        'message': f"{metric_name} predicted to reach critical threshold"
                    })
                elif predicted >= threshold.warning_threshold:
                    predictions.append({
                        'metric': metric_name,
                        'severity': 'warning',
                        'current': trend['current_value'],
                        'predicted': predicted,
                        'threshold': threshold.warning_threshold,
                        'hours_ahead': self.prediction_window_hours,
                        'message': f"{metric_name} predicted to reach warning threshold"
                    })
            else:  # 'lt'
                if predicted <= threshold.critical_threshold:
                    predictions.append({
                        'metric': metric_name,
                        'severity': 'critical',
                        'current': trend['current_value'],
                        'predicted': predicted,
                        'threshold': threshold.critical_threshold,
                        'hours_ahead': self.prediction_window_hours,
                        'message': f"{metric_name} predicted to fall below critical threshold"
                    })
                elif predicted <= threshold.warning_threshold:
                    predictions.append({
                        'metric': metric_name,
                        'severity': 'warning',
                        'current': trend['current_value'],
                        'predicted': predicted,
                        'threshold': threshold.warning_threshold,
                        'hours_ahead': self.prediction_window_hours,
                        'message': f"{metric_name} predicted to fall below warning threshold"
                    })
        
        return predictions
    
    def assess_component_health(
        self,
        component_name: str,
        metrics: Dict[str, float]
    ) -> HealthStatus:
        """
        Оценка здоровья компонента
        
        Args:
            component_name: Имя компонента
            metrics: Метрики компонента
            
        Returns:
            Статус здоровья
        """
        if not metrics:
            return HealthStatus.UNKNOWN
        
        has_critical = False
        has_warning = False
        
        for metric_name, value in metrics.items():
            if metric_name in self._thresholds:
                severity = self._thresholds[metric_name].check(value)
                
                if severity == AlertSeverity.CRITICAL:
                    has_critical = True
                elif severity == AlertSeverity.WARNING:
                    has_warning = True
        
        if has_critical:
            status = HealthStatus.CRITICAL
        elif has_warning:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY
        
        self._component_health[component_name] = status
        return status
    
    def calculate_overall_health(self) -> HealthStatus:
        """
        Расчет общего здоровья БД
        
        Returns:
            Статус здоровья
        """
        if not self._component_health:
            return HealthStatus.UNKNOWN
        
        # Если хотя бы один компонент критичен - вся система критична
        if any(status == HealthStatus.CRITICAL for status in self._component_health.values()):
            self._overall_health = HealthStatus.CRITICAL
        # Если есть предупреждения - предупреждение
        elif any(status == HealthStatus.WARNING for status in self._component_health.values()):
            self._overall_health = HealthStatus.WARNING
        # Если все здоровы - здорово
        elif all(status == HealthStatus.HEALTHY for status in self._component_health.values()):
            self._overall_health = HealthStatus.HEALTHY
        else:
            self._overall_health = HealthStatus.UNKNOWN
        
        return self._overall_health
    
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """
        Получение активных алертов
        
        Args:
            severity: Фильтр по серьезности
            
        Returns:
            Список активных алертов
        """
        alerts = list(self._active_alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    def get_alert_history(
        self,
        hours: int = 24,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """
        Получение истории алертов
        
        Args:
            hours: Количество часов истории
            severity: Фильтр по серьезности
            
        Returns:
            Список алертов
        """
        cutoff_time = time.time() - (hours * 3600)
        
        alerts = [a for a in self._alert_history if a.created_at >= cutoff_time]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    def acknowledge_alert(self, metric_name: str) -> bool:
        """
        Подтверждение алерта
        
        Args:
            metric_name: Имя метрики
            
        Returns:
            True если подтвержден
        """
        if metric_name in self._active_alerts:
            self._active_alerts[metric_name].acknowledged = True
            return True
        return False
    
    def resolve_alert(self, metric_name: str) -> bool:
        """
        Ручное разрешение алерта
        
        Args:
            metric_name: Имя метрики
            
        Returns:
            True если разрешен
        """
        if metric_name in self._active_alerts:
            alert = self._active_alerts[metric_name]
            alert.resolved_at = time.time()
            del self._active_alerts[metric_name]
            self._total_alerts_resolved += 1
            return True
        return False
    
    def get_metric_summary(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        Получение сводки по метрике
        
        Args:
            metric_name: Имя метрики
            
        Returns:
            Словарь со сводкой
        """
        if metric_name not in self._metrics_history:
            return None
        
        history = self._metrics_history[metric_name]
        if not history:
            return None
        
        values = [dp.value for dp in history]
        
        summary = {
            'metric_name': metric_name,
            'current_value': values[-1],
            'min_value': min(values),
            'max_value': max(values),
            'avg_value': sum(values) / len(values),
            'sample_count': len(values),
            'has_baseline': metric_name in self._baselines,
            'has_active_alert': metric_name in self._active_alerts,
            'data_points': len(history)
        }
        
        # Добавление baseline если есть
        if metric_name in self._baselines:
            baseline = self._baselines[metric_name]
            summary['baseline'] = {
                'avg': baseline.avg_value,
                'std_dev': baseline.std_dev,
                'is_anomaly': baseline.is_anomaly(values[-1], self.anomaly_sensitivity)
            }
        
        # Добавление тренда
        trend = self.get_metric_trend(metric_name)
        if trend:
            summary['trend'] = trend
        
        return summary
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик мониторинга"""
        hours_since_collection = 0.0
        if self._last_collection_time:
            hours_since_collection = (time.time() - self._last_collection_time) / 3600
        
        hours_since_baseline = 0.0
        if self._last_baseline_calculation:
            hours_since_baseline = (time.time() - self._last_baseline_calculation) / 3600
        
        return {
            'enabled': self.enabled,
            'overall_health': self._overall_health.value,
            
            # Метрики
            'tracked_metrics': len(self._metrics_history),
            'total_datapoints': sum(len(h) for h in self._metrics_history.values()),
            'hours_since_collection': hours_since_collection,
            
            # Baselines
            'baselines_count': len(self._baselines),
            'hours_since_baseline_calc': hours_since_baseline,
            'should_recalculate': self.should_recalculate_baselines(),
            
            # Алерты
            'active_alerts': len(self._active_alerts),
            'critical_alerts': len([a for a in self._active_alerts.values() if a.severity == AlertSeverity.CRITICAL]),
            'warning_alerts': len([a for a in self._active_alerts.values() if a.severity == AlertSeverity.WARNING]),
            'total_alerts_generated': self._total_alerts_generated,
            'total_alerts_resolved': self._total_alerts_resolved,
            
            # Аномалии
            'anomaly_detection_enabled': self.anomaly_detection_enabled,
            'total_anomalies_detected': self._total_anomalies_detected,
            
            # Компоненты
            'monitored_components': len(self._component_health),
            'healthy_components': len([s for s in self._component_health.values() if s == HealthStatus.HEALTHY]),
            'warning_components': len([s for s in self._component_health.values() if s == HealthStatus.WARNING]),
            'critical_components': len([s for s in self._component_health.values() if s == HealthStatus.CRITICAL])
        }