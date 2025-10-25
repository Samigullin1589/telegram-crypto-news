# 🧠 CRYPTO INTELLIGENCE SYSTEM v1.0

**Живая, самообучающаяся система для поиска альфа-сигналов в крипте**

---

## 🎯 ЧТО ЭТО?

Не просто новостной бот, а **искусственный аналитик** который:

- 🔍 Сам находит прибыльных трейдеров
- 🧹 Чистит базу от неактуальных
- 📊 Адаптируется под рынок
- 🎓 Учится на своих ошибках
- ✅ Публикует только проверенные сигналы

**Результат:** 5-10 качественных постов в день вместо 50+ шума

---

## 💎 3 ОСНОВНЫХ НАПРАВЛЕНИЯ

### 1. Smart Money Tracking (40%)
Отслеживание успешных трейдеров и их покупок

### 2. Mining Intelligence (40%)
Анализ поведения майнеров для предсказания движений BTC

### 3. On-Chain Signals (20%)
Потоки на биржи, киты, стейблкоины

---

## 🏗️ АРХИТЕКТУРА

```
crypto-intelligence/
│
├── app/
│   ├── core/                    # Ядро системы
│   │   ├── config.py
│   │   ├── database.py
│   │   └── api_client.py
│   │
│   ├── discovery/               # Поиск новых трейдеров
│   │   ├── wallet_discovery.py
│   │   ├── pool_discovery.py
│   │   └── token_scanner.py
│   │
│   ├── validation/              # Проверка актуальности
│   │   ├── wallet_validator.py
│   │   ├── signal_validator.py
│   │   └── cross_validator.py
│   │
│   ├── intelligence/            # Анализ и скоринг
│   │   ├── smart_money.py
│   │   ├── mining.py
│   │   ├── onchain.py
│   │   ├── scoring.py
│   │   └── patterns.py
│   │
│   ├── learning/                # Самообучение
│   │   ├── performance_tracker.py
│   │   ├── adaptive_thresholds.py
│   │   └── weight_optimizer.py
│   │
│   └── publishing/              # Публикация
│       ├── formatter.py
│       ├── telegram_bot.py
│       └── logger.py
│
├── data/
│   ├── wallets.json
│   ├── mining_pools.json
│   └── database.db
│
├── scripts/
│   ├── init_database.py
│   ├── backfill_history.py
│   └── run_discovery.py
│
├── tests/
│   └── ...
│
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 БЫСТРЫЙ СТАРТ

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
# Отредактируйте .env - добавьте API ключи
```

### 3. Инициализация базы данных

```bash
python scripts/init_database.py
```

### 4. Запуск системы

```bash
python main.py
```

---

## 🔑 НЕОБХОДИМЫЕ API КЛЮЧИ (бесплатные)

```env
# Blockchain explorers
ETHERSCAN_API_KEY=your_key
BSCSCAN_API_KEY=your_key
POLYGONSCAN_API_KEY=your_key

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHANNEL_ID=@your_channel

# Optional (все free tier)
COINGECKO_API_KEY=optional
GITHUB_TOKEN=optional
```

---

## 📊 КАК ЭТО РАБОТАЕТ

### Discovery Engine (каждые 6 часов)
```
1. Находим токены с x3+ ростом
2. Смотрим кто купил РАНО (до роста)
3. Проверяем историю этих кошельков
4. Если ROI >100% и winrate >60% → добавляем
```

### Validation Engine (каждую неделю)
```
1. Проверяем всех в базе
2. ROI <0 или winrate <50% → удаляем
3. Нет активности >60 дней → удаляем
4. Обновляем скоры актуальных
```

### Intelligence Layer (реалтайм)
```
1. Отслеживаем покупки трейдеров
2. Если 5+ купили одно → паттерн
3. Scoring 0-100 баллов
4. Публикуем только 70+
```

---

## 📈 МЕТРИКИ КАЧЕСТВА

### Целевые показатели:
- Точность сигналов: **>70%**
- Ложные срабатывания: **<15%**
- Постов в день: **5-10** (не больше!)
- Средняя оценка: **>7.5/10**

### Отслеживаем:
- Win rate каждого типа сигнала
- ROI каждого кошелька
- Точность предсказаний
- Feedback от подписчиков

---

## 🔧 КОНФИГУРАЦИЯ

Основные настройки в `app/core/config.py`:

```python
# Пороги для публикации
MIN_SCORE = 70  # Минимальная оценка сигнала
MIN_WALLETS_BUYING = 5  # Минимум кошельков для паттерна
MIN_VOLUME_USD = 1_000_000  # Минимальный объём покупок

# Discovery
DISCOVERY_INTERVAL_HOURS = 6  # Как часто ищем новых
MIN_TOKEN_GAIN = 3.0  # x3 минимум для анализа
MIN_WALLET_ROI = 1.0  # +100% ROI минимум
MIN_WALLET_WINRATE = 0.60  # 60% winrate минимум

# Validation
VALIDATION_INTERVAL_DAYS = 7  # Как часто чистим базу
MAX_INACTIVE_DAYS = 60  # Макс неактивность кошелька
MIN_SCORE_TO_KEEP = 40  # Минимальный скор для сохранения
```

---

## 📚 ДОКУМЕНТАЦИЯ

Подробная документация в `/docs`:
- `ARCHITECTURE.md` - Детальная архитектура
- `API.md` - Все API endpoints
- `ALGORITHMS.md` - Алгоритмы и формулы
- `DEPLOYMENT.md` - Гайд по деплою

---

## 🤝 CONTRIBUTING

Это твой проект! Улучшения приветствуются:
1. Новые источники данных
2. Улучшенные алгоритмы
3. Дополнительные проверки
4. Оптимизация производительности

---

## 📝 TODO (Phase 1)

- [x] Структура проекта
- [x] Конфигурация
- [ ] Database schema
- [ ] Smart Money Discovery
- [ ] Wallet Validator
- [ ] Scoring System
- [ ] Telegram Publisher
- [ ] Tests

---

## 💰 СТОИМОСТЬ

**$0/месяц** - все API бесплатные!

---

## 📞 ПОДДЕРЖКА

Вопросы? Идеи? Найденные баги?
Создавай Issue в репозитории!

---

**Let's build the smartest crypto intelligence system! 🚀**