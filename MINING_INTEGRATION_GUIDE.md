# ⛏️ MINING INTEGRATION - QUICK START

## 🎯 Что это?

**Mining Integration** связывает твой `mining_tracker.py` с системой самообучения.

Теперь система:
- ✅ Отслеживает результаты mining сигналов
- ✅ Рассчитывает точность mining индикаторов
- ✅ Оптимизирует веса (difficulty, hashrate, block_time, revenue)
- ✅ Находит успешные mining паттерны
- ✅ Улучшает качество mining сигналов

---

## 📋 КАК ИСПОЛЬЗОВАТЬ

### Вариант 1: Автоматическая интеграция (в scheduler)

Scheduler **уже интегрирован**! Просто запусти:

```bash
python main.py
```

Mining события автоматически:
1. Конвертируются в формат learning system
2. Отправляются в PerformanceTracker
3. Проверяются через 24 часа
4. Используются для обучения

### Вариант 2: Ручная интеграция

В твоём `mining_tracker.py` добавь:

```python
from app.whales.mining_integration import convert_mining_to_performance_format
from app.whales.performance_tracker import PerformanceTracker

# Когда обнаружено mining событие:
mining_event = {
    "asset": "BTC",
    "difficulty_change": 5.2,
    "hashrate_change": 7.8,
    "block_time_change": -2.1,
    "miner_revenue_change": 3.5,
    "price": 68500
}

# Конвертируй и отслеживай
signal_data = convert_mining_to_performance_format(mining_event)

if signal_data:
    # Добавь в tracker
    tracker = PerformanceTracker()
    tracker.track_signal(**signal_data)
    
    print(f"✅ Mining сигнал добавлен в отслеживание: {signal_data['verdict']}")
```

---

## 📊 МОНИТОРИНГ ПРОИЗВОДИТЕЛЬНОСТИ

### Получить отчёт по mining:

```python
from app.whales.mining_integration import MiningIntegration
from app.whales.performance_tracker import PerformanceTracker

# Загрузи историю
tracker = PerformanceTracker()
performance_data = [s.to_dict() for s in tracker.tracked_signals]

# Создай отчёт
integration = MiningIntegration()
report = integration.generate_mining_report(performance_data)

print(report)
```

**Пример отчёта:**

```
================================================================================
⛏️  MINING PERFORMANCE REPORT
================================================================================

📊 ОБЩАЯ СТАТИСТИКА
   Всего mining сигналов: 45
   Общая точность: 72.5%

📈 ТОЧНОСТЬ ПО ИНДИКАТОРАМ

   DIFFICULTY:
     weak: 65.0% (n=10)
     medium: 75.5% (n=20)
     strong: 80.0% (n=15)

   HASHRATE:
     weak: 60.0% (n=8)
     medium: 72.0% (n=22)
     strong: 85.0% (n=15)

⚙️  ОПТИМАЛЬНЫЕ ПОРОГИ
   difficulty_change: 5%
   hashrate_change: 6%

🔍 ОБНАРУЖЕННЫЕ ПАТТЕРНЫ: 2
   • Хешрейт растёт быстрее сложности: 78.5% (n=14)
   • Падение дохода при росте сложности: 81.0% (n=11)

⚖️  ТЕКУЩИЕ ВЕСА ИНДИКАТОРОВ
   difficulty: 30.0%
   hashrate: 35.0%
   block_time: 20.0%
   miner_revenue: 15.0%

================================================================================
```

---

## 🎓 ОПТИМИЗАЦИЯ ВЕСОВ

Система автоматически оптимизирует веса, но можно запустить вручную:

```python
from app.whales.mining_integration import MiningIntegration
from app.whales.performance_tracker import PerformanceTracker

# Загрузи данные
tracker = PerformanceTracker()
performance_data = [s.to_dict() for s in tracker.tracked_signals]

# Оптимизируй
integration = MiningIntegration()
new_weights = integration.optimize_indicator_weights(performance_data)

print("Новые веса:")
for indicator, weight in new_weights.items():
    print(f"  {indicator}: {weight:.1%}")
```

---

## ⚙️ НАСТРОЙКА

В `.env` уже есть все параметры:

```env
# Mining веса в learning system
LEARNING_WEIGHT_MINING=0.30  # Вес mining сигналов (30%)

# Performance tracking для mining
PERFORMANCE_TRACKING_ENABLED=1
PERFORMANCE_CHECK_INTERVALS=1,6,24
```

Можешь настроить в `mining_integration.py`:

```python
class MiningIntegration:
    def __init__(self):
        # Начальные веса индикаторов
        self.indicator_weights = {
            "difficulty": 0.30,      # ← Измени если нужно
            "hashrate": 0.35,        # ← Измени если нужно
            "block_time": 0.20,      # ← Измени если нужно
            "miner_revenue": 0.15    # ← Измени если нужно
        }
```

---

## 🧪 ТЕСТИРОВАНИЕ

Запусти тест:

```bash
python -m app.whales.mining_integration
```

Увидишь:

```
🧪 TESTING MINING INTEGRATION

1. Конвертация mining события...
   ✅ Создан сигнал: BTC bullish (confidence: 78)
   Формат для tracker:
   {
     "signal_id": "mining_BTC_1729950000",
     "asset": "BTC",
     "chain": "bitcoin",
     "verdict": "bullish",
     "confidence": 78,
     ...
   }

2. Тест расчёта verdict...
   Verdict: bullish, Confidence: 78

✅ Тестирование завершено!
```

---

## 🔗 ИНТЕГРАЦИЯ С SCHEDULER

Scheduler автоматически:

1. **При запуске** - инициализирует MiningIntegration
2. **При mining событии** - конвертирует и отслеживает
3. **Каждый час** - проверяет результаты mining сигналов
4. **Каждую неделю** - обучает веса индикаторов
5. **В daily stats** - включает mining статистику

**Всё работает автоматически!** 🎉

---

## 📈 ЧТО ОЖИДАТЬ

### Через 24 часа:
- Первые проверенные mining сигналы
- Первая статистика точности

### Через 7 дней:
- Оптимизированные веса индикаторов
- Обнаруженные успешные паттерны
- Точность mining >70%

### Через 30 дней:
- Идеально настроенная система
- Точность mining >75%
- Автоматическая адаптация к изменениям

---

## 🐛 TROUBLESHOOTING

### Mining сигналы не отслеживаются

**Причина:** Mining events не передаются в integration

**Решение:**
```python
# В твоём mining_tracker.py, когда создаёшь событие:
signal_data = convert_mining_to_performance_format(mining_event)
if signal_data:
    tracker.track_signal(**signal_data)
```

### Недостаточно данных для оптимизации

**Причина:** Мало mining сигналов (<20)

**Решение:** Подожди пока накопится история, или понизь пороги в mining_tracker

### Веса не обновляются

**Причина:** `LEARNING_SYSTEM_ENABLED=0`

**Решение:**
```env
LEARNING_SYSTEM_ENABLED=1
```

---

## 🎉 ГОТОВО!

Mining теперь **полностью интегрирован** с системой самообучения!

Система будет автоматически:
- ✅ Улучшать качество mining сигналов
- ✅ Находить лучшие индикаторы
- ✅ Обнаруживать успешные паттерны

**Наслаждайся!** ⛏️🚀