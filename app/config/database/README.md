# Database Optimization System

Комплексная система оптимизации и управления базой данных PostgreSQL.

## Архитектура

Система состоит из следующих компонентов:

### Компоненты оптимизации (`components/`)

1. **backup.py** - Управление бэкапами
   - Стратегии: FULL, INCREMENTAL, DIFFERENTIAL
   - Автоматическое расписание
   - Ротация старых бэкапов

2. **pool.py** - Управление пулом соединений
   - Динамическое масштабирование
   - Health checks
   - Приоритизация соединений

3. **pragma.py** - Оптимизация PostgreSQL PRAGMA
   - work_mem, maintenance_work_mem
   - effective_cache_size
   - random_page_cost, WAL настройки

4. **indexes.py** - Управление индексами
   - Обнаружение неиспользуемых индексов
   - Обнаружение дубликатов
   - Рекомендации по созданию

5. **partitions.py** - Партиционирование таблиц
   - Автосоздание партиций
   - Удаление устаревших
   - Балансировка данных

6. **vacuum.py** - VACUUM операции
   - Интеллектуальное планирование
   - Адаптивный выбор стратегии
   - Координация с autovacuum

7. **cache.py** - Кэширование
   - Многоуровневое (memory/Redis)
   - Адаптивное TTL
   - LRU/LFU эвикция

8. **monitoring.py** - Мониторинг
   - Сбор метрик в реальном времени
   - Обнаружение аномалий
   - Генерация алертов

9. **statistics.py** - Статистика
   - Агрегация по периодам
   - Анализ запросов
   - Генерация отчетов

10. **query_analyzer.py** - Анализ запросов
    - EXPLAIN ANALYZE
    - Обнаружение N+1 queries
    - Рекомендации по оптимизации

### Главный оркестратор

**optimizer.py** - Координирует все компоненты:
- Планирование операций
- Предотвращение конфликтов
- Адаптивная оптимизация

### API и интеграция

**DatabaseManager** - Главный API для работы с системой:
```python
from app.config.database import get_db_manager

# Получение менеджера
db_manager = get_db_manager()

# Инициализация
await db_manager.initialize()

# Запуск оптимизации
result = await db_manager.run_optimization()

# Получение статуса
status = db_manager.get_status()

# Получение рекомендаций
recommendations = db_manager.get_recommendations()
```

## CLI Команды
```bash
# Запуск оптимизации
python -m app.config.database.commands optimize

# Просмотр статуса
python -m app.config.database.commands status

# Просмотр метрик
python -m app.config.database.commands metrics

# Просмотр рекомендаций
python -m app.config.database.commands recommendations

# Просмотр алертов
python -m app.config.database.commands alerts

# Генерация отчета
python -m app.config.database.commands report --output report.md
```

## Использование в коде

### Базовое использование
```python
from app.config.database import DatabaseManager

async def optimize_database():
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Запуск оптимизации
    result = await db_manager.run_optimization()
    
    if result['status'] == 'completed':
        print(f"Optimization completed in {result['duration_seconds']}s")
        print(f"Operations executed: {result['operations_executed']}")
```

### Мониторинг
```python
# Получение метрик
metrics = db_manager.get_metrics()

# Кэш hit rate
cache_hit_rate = metrics['cache']['hit_rate_percent']

# Утилизация пула
pool_utilization = metrics['pool']['utilization_percent']

# Получение алертов
alerts = db_manager.get_alerts(active_only=True)

if alerts['critical'] > 0:
    print(f"CRITICAL: {alerts['critical']} critical alerts!")
```

### Рекомендации
```python
# Получение всех рекомендаций
recommendations = db_manager.get_recommendations()

# Высокоприоритетные рекомендации
high_priority = db_manager.get_recommendations(severity='high')

# Рекомендации по индексам
index_recs = recommendations['indexes']
for rec in index_recs:
    print(f"{rec.severity}: {rec.recommendation}")
```

## Автоматическая оптимизация

Система интегрируется с task manager и запускается автоматически:
```python
from core.tasks import TaskManager

# При старте приложения
task_manager = TaskManager()
await task_manager.start_all()

# database_optimization задача запустится автоматически
```

Конфигурация через environment variables:
```bash
# Включение оптимизации
DATABASE_ENABLE_OPTIMIZATION=true

# Интервал оптимизации (часы)
DATABASE_OPTIMIZATION_INTERVAL_HOURS=1

# Мониторинг
DATABASE_ENABLE_MONITORING=true
DATABASE_MONITORING_INTERVAL_SECONDS=60

# Статистика
DATABASE_ENABLE_STATISTICS=true
DATABASE_STATISTICS_RETENTION_DAYS=30

# Автообслуживание
DATABASE_ENABLE_AUTO_VACUUM=true
DATABASE_ENABLE_AUTO_ANALYZE=true
DATABASE_ENABLE_AUTO_BACKUP=true
```

## Health Checks

Быстрые проверки здоровья БД:
```python
from app.config.database.health_checks import DatabaseHealthChecker

checker = DatabaseHealthChecker()

# Запуск всех проверок
results = await checker.run_all_checks()

# Получение общего статуса
overall_status = checker.get_overall_status(results)

if overall_status == HealthCheckStatus.UNHEALTHY:
    print("Database is unhealthy!")
```

## Утилиты
```python
from app.config.database.utils import (
    bytes_to_human_readable,
    format_duration,
    calculate_bloat_ratio,
    estimate_index_size
)

# Форматирование размеров
size = bytes_to_human_readable(1024 * 1024 * 100)  # "100.00 MB"

# Форматирование длительности
duration = format_duration(3665)  # "1h 1m 5s"

# Расчет bloat
bloat = calculate_bloat_ratio(
    table_size_bytes=1024 * 1024 * 500,
    live_tuples=100000,
    dead_tuples=20000
)
```

## Лучшие практики

1. **Запускайте оптимизацию в maintenance window**
   - Настройте `maintenance_start_hour` и `maintenance_end_hour`

2. **Мониторьте алерты**
   - Настройте автоматическую отправку критических алертов

3. **Регулярно проверяйте рекомендации**
   - Применяйте рекомендации по индексам и запросам

4. **Следите за метриками**
   - Cache hit rate должен быть > 90%
   - Pool utilization < 80%
   - Нет активных критических алертов

5. **Используйте health checks в production**
   - Интегрируйте с вашим мониторингом
   - Настройте автоматический restart при failures

## Troubleshooting

### Оптимизация не запускается

Проверьте:
- Инициализирован ли менеджер: `db_manager._initialized`
- Включена ли оптимизация: `config.enable_optimization`
- Нет ли высокой нагрузки: проверьте current_load_percent

### Много критических алертов

1. Проверьте метрики: `db_manager.get_metrics()`
2. Посмотрите рекомендации: `db_manager.get_recommendations()`
3. Запустите health check: `checker.run_all_checks()`

### Медленная оптимизация

- Уменьшите `max_concurrent_operations`
- Увеличьте `optimization_interval_hours`
- Проверьте размеры таблиц для VACUUM

## Архитектурные решения

### Почему используется асинхронность?

Оптимизация может занимать значительное время. Асинхронность позволяет:
- Не блокировать основной поток
- Выполнять операции параллельно
- Graceful shutdown

### Почему отдельные компоненты?

Модульность обеспечивает:
- Легкую замену компонентов
- Независимое тестирование
- Переиспользование кода

### Почему централизованный оркестратор?

DatabaseOptimizer координирует компоненты для:
- Предотвращения конфликтов
- Приоритизации операций
- Адаптивного планирования

## Production Checklist

- [ ] Настроены environment variables
- [ ] Указано maintenance window
- [ ] Настроены пороги алертов
- [ ] Интегрирован с мониторингом
- [ ] Health checks в readiness probe
- [ ] Логи оптимизации в centralized logging
- [ ] Метрики экспортируются в Prometheus/Grafana
- [ ] Алерты отправляются в Slack/PagerDuty
- [ ] Backup хранится offsite
- [ ] Протестировано восстановление из backup