"""
Утилиты для работы с базой данных

Вспомогательные функции для:
- Форматирования SQL
- Работы с метриками
- Конвертации единиц измерения
- Генерации отчетов
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple


def bytes_to_human_readable(bytes_value: int) -> str:
    """
    Конвертация байтов в человекочитаемый формат
    
    Args:
        bytes_value: Количество байтов
        
    Returns:
        Строка формата "10.5 MB"
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    size = float(bytes_value)
    unit_index = 0
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"


def human_readable_to_bytes(human_readable: str) -> int:
    """
    Конвертация человекочитаемого формата в байты
    
    Args:
        human_readable: Строка формата "10.5 MB"
        
    Returns:
        Количество байтов
    """
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'PB': 1024 ** 5
    }
    
    match = re.match(r'([\d.]+)\s*([A-Z]+)', human_readable.upper())
    if not match:
        raise ValueError(f"Invalid format: {human_readable}")
    
    value, unit = match.groups()
    
    if unit not in units:
        raise ValueError(f"Unknown unit: {unit}")
    
    return int(float(value) * units[unit])


def format_duration(seconds: float) -> str:
    """
    Форматирование длительности в человекочитаемый вид
    
    Args:
        seconds: Длительность в секундах
        
    Returns:
        Строка формата "1h 23m 45s"
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    
    if minutes < 60:
        return f"{minutes}m {remaining_seconds}s"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    return f"{hours}h {remaining_minutes}m {remaining_seconds}s"


def format_sql(sql: str, max_length: int = 100) -> str:
    """
    Форматирование SQL запроса для отображения
    
    Args:
        sql: SQL запрос
        max_length: Максимальная длина
        
    Returns:
        Отформатированный SQL
    """
    # Удаление лишних пробелов
    sql = re.sub(r'\s+', ' ', sql.strip())
    
    # Обрезка если нужно
    if len(sql) > max_length:
        sql = sql[:max_length - 3] + '...'
    
    return sql


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Расчет процентного изменения
    
    Args:
        old_value: Старое значение
        new_value: Новое значение
        
    Returns:
        Процент изменения
    """
    if old_value == 0:
        return 100.0 if new_value > 0 else 0.0
    
    return ((new_value - old_value) / old_value) * 100


def aggregate_metrics(
    metrics: List[Dict[str, Any]],
    time_window_minutes: int = 60
) -> Dict[str, Any]:
    """
    Агрегация метрик за временное окно
    
    Args:
        metrics: Список метрик с timestamp
        time_window_minutes: Размер окна в минутах
        
    Returns:
        Агрегированные метрики
    """
    if not metrics:
        return {}
    
    cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
    
    # Фильтрация по времени
    recent_metrics = [
        m for m in metrics
        if datetime.fromtimestamp(m.get('timestamp', 0)) >= cutoff_time
    ]
    
    if not recent_metrics:
        return {}
    
    # Агрегация
    aggregated = {
        'count': len(recent_metrics),
        'time_window_minutes': time_window_minutes
    }
    
    # Для каждой числовой метрики
    numeric_fields = set()
    for metric in recent_metrics:
        for key, value in metric.items():
            if isinstance(value, (int, float)) and key != 'timestamp':
                numeric_fields.add(key)
    
    for field in numeric_fields:
        values = [m[field] for m in recent_metrics if field in m]
        
        if values:
            aggregated[field] = {
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'current': values[-1]
            }
    
    return aggregated


def generate_markdown_report(
    title: str,
    sections: Dict[str, Any]
) -> str:
    """
    Генерация отчета в формате Markdown
    
    Args:
        title: Заголовок отчета
        sections: Секции отчета
        
    Returns:
        Markdown текст
    """
    lines = [
        f"# {title}",
        "",
        f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        ""
    ]
    
    for section_title, section_data in sections.items():
        lines.append(f"## {section_title}")
        lines.append("")
        
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                if isinstance(value, dict):
                    lines.append(f"### {key}")
                    for sub_key, sub_value in value.items():
                        lines.append(f"- **{sub_key}**: {sub_value}")
                else:
                    lines.append(f"- **{key}**: {value}")
        elif isinstance(section_data, list):
            for item in section_data:
                if isinstance(item, dict):
                    lines.append("")
                    for key, value in item.items():
                        lines.append(f"- **{key}**: {value}")
                else:
                    lines.append(f"- {item}")
        else:
            lines.append(str(section_data))
        
        lines.append("")
    
    return "\n".join(lines)


def parse_postgres_interval(interval_str: str) -> timedelta:
    """
    Парсинг PostgreSQL интервала в timedelta
    
    Args:
        interval_str: Строка интервала PostgreSQL
        
    Returns:
        timedelta объект
    """
    # Паттерны для различных форматов
    patterns = [
        (r'(\d+)\s*days?', 'days'),
        (r'(\d+)\s*hours?', 'hours'),
        (r'(\d+)\s*minutes?', 'minutes'),
        (r'(\d+)\s*seconds?', 'seconds')
    ]
    
    kwargs = {}
    
    for pattern, unit in patterns:
        match = re.search(pattern, interval_str.lower())
        if match:
            kwargs[unit] = int(match.group(1))
    
    return timedelta(**kwargs) if kwargs else timedelta()


def sanitize_identifier(identifier: str) -> str:
    """
    Санитизация SQL идентификатора
    
    Args:
        identifier: Имя таблицы/колонки/индекса
        
    Returns:
        Безопасный идентификатор
    """
    # Удаление опасных символов
    identifier = re.sub(r'[^\w.]', '', identifier)
    
    # Ограничение длины (PostgreSQL лимит 63 символа)
    if len(identifier) > 63:
        identifier = identifier[:63]
    
    return identifier


def estimate_index_size(
    table_rows: int,
    column_size_bytes: int,
    fill_factor: float = 0.9
) -> int:
    """
    Оценка размера индекса
    
    Args:
        table_rows: Количество строк в таблице
        column_size_bytes: Размер колонки в байтах
        fill_factor: Фактор заполнения
        
    Returns:
        Оценочный размер индекса в байтах
    """
    # Упрощенная формула для B-tree индекса
    # Реальный расчет сложнее и зависит от типа индекса
    
    # Размер одной записи в индексе
    index_entry_size = column_size_bytes + 8  # +8 для указателя на строку
    
    # Размер листовых страниц
    page_size = 8192  # PostgreSQL default
    entries_per_page = int((page_size * fill_factor) / index_entry_size)
    
    if entries_per_page == 0:
        entries_per_page = 1
    
    leaf_pages = (table_rows + entries_per_page - 1) // entries_per_page
    
    # Внутренние страницы (приблизительно 1% от листовых)
    internal_pages = max(1, int(leaf_pages * 0.01))
    
    total_pages = leaf_pages + internal_pages
    total_size = total_pages * page_size
    
    return total_size


def calculate_bloat_ratio(
    table_size_bytes: int,
    live_tuples: int,
    dead_tuples: int,
    avg_tuple_size: int = 100
) -> float:
    """
    Расчет bloat ratio для таблицы
    
    Args:
        table_size_bytes: Размер таблицы
        live_tuples: Живые кортежи
        dead_tuples: Мертвые кортежи
        avg_tuple_size: Средний размер кортежа
        
    Returns:
        Процент bloat
    """
    if table_size_bytes == 0:
        return 0.0
    
    # Оценка идеального размера
    ideal_size = (live_tuples * avg_tuple_size)
    
    # Добавляем overhead (заголовки страниц, выравнивание)
    ideal_size = int(ideal_size * 1.2)
    
    if ideal_size == 0:
        return 0.0
    
    bloat_size = table_size_bytes - ideal_size
    
    if bloat_size < 0:
        return 0.0
    
    return (bloat_size / table_size_bytes) * 100


def prioritize_maintenance_operations(
    operations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Приоритизация операций обслуживания
    
    Args:
        operations: Список операций с метаданными
        
    Returns:
        Отсортированный список операций
    """
    # Веса приоритетов
    priority_weights = {
        'critical': 0,
        'high': 1,
        'medium': 2,
        'low': 3
    }
    
    # Веса типов операций
    operation_weights = {
        'backup': 0,
        'vacuum_freeze': 1,
        'vacuum_full': 2,
        'reindex': 3,
        'vacuum': 4,
        'analyze': 5,
        'partition_drop': 6,
        'partition_create': 7
    }
    
    def operation_sort_key(op: Dict[str, Any]) -> Tuple[int, int, float]:
        priority = priority_weights.get(op.get('priority', 'medium'), 2)
        op_type = operation_weights.get(op.get('type', 'analyze'), 5)
        scheduled_time = op.get('scheduled_time', 0.0)
        
        return (priority, op_type, scheduled_time)
    
    return sorted(operations, key=operation_sort_key)


__all__ = [
    'bytes_to_human_readable',
    'human_readable_to_bytes',
    'format_duration',
    'format_sql',
    'calculate_percentage_change',
    'aggregate_metrics',
    'generate_markdown_report',
    'parse_postgres_interval',
    'sanitize_identifier',
    'estimate_index_size',
    'calculate_bloat_ratio',
    'prioritize_maintenance_operations'
]