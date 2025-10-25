# 🚀 БЫСТРЫЙ СТАРТ

Инструкция для запуска Crypto Intelligence System за 5 минут.

---

## ⚡ ШАГ 1: УСТАНОВКА

### 1.1 Клонируйте проект

```bash
git clone https://github.com/your-repo/crypto-intelligence.git
cd crypto-intelligence
```

### 1.2 Создайте виртуальное окружение

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 1.3 Установите зависимости

```bash
pip install -r requirements.txt
```

---

## 🔑 ШАГ 2: API КЛЮЧИ

### 2.1 Создайте .env файл

```bash
cp .env.example .env
```

### 2.2 Получите бесплатные API ключи

#### Etherscan (обязательно)
1. Перейдите: https://etherscan.io/apis
2. Зарегистрируйтесь
3. Создайте API ключ (бесплатно)
4. Вставьте в `.env`:
```env
ETHERSCAN_API_KEY=ваш_ключ_здесь
```

#### Telegram Bot (обязательно)
1. Откройте Telegram, найдите @BotFather
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен и вставьте в `.env`:
```env
TELEGRAM_BOT_TOKEN=ваш_токен_здесь
TELEGRAM_CHANNEL_ID=@ваш_канал
```

#### Дополнительные (опционально)
- BSCScan: https://bscscan.com/apis (для BSC сети)
- PolygonScan: https://polygonscan.com/apis (для Polygon)

---

## 🗄️ ШАГ 3: ИНИЦИАЛИЗАЦИЯ БД

```bash
python scripts/init_database.py
```

Вы увидите:
```
🗄️  ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
📋 Создание таблиц...
   ✅ Таблицы созданы
⚙️  Начальная конфигурация...
   ✅ Конфигурация создана
⛏️  Добавление майнинг пулов...
   ✅ Добавлено 5 майнинг пулов
👛 Добавление seed кошельков...
   ✅ Добавлено 2 seed кошельков
✅ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА
```

---

## 🏃 ШАГ 4: ЗАПУСК

```bash
python main.py
```

Система запустится и начнёт работу!

---

## 📊 ЧТО ПРОИСХОДИТ?

### При первом запуске:

```
⚙️  КОНФИГУРАЦИЯ CRYPTO INTELLIGENCE SYSTEM
🔑 API КЛЮЧИ:
   Etherscan: ✅
   Telegram: ✅

🔍 DISCOVERY ENGINE
   Ищу токены с резким ростом...
   Анализирую ранних покупателей...
   Найдено 3 новых успешных трейдера!

✅ VALIDATION ENGINE  
   Проверяю 5 кошельков в базе...
   Удалено 1 неактивных
   
🧠 INTELLIGENCE LAYER
   Отслеживаю покупки...
   Найден паттерн: 5 кошельков купили PEPE
   Score: 85/100 🔥🔥🔥
   
📢 PUBLISHING
   Публикую сигнал в Telegram...
   ✅ Опубликовано!
```

---

## 🎛️ НАСТРОЙКА

### Основные параметры в `.env`:

```env
# Как часто искать новых трейдеров (часы)
DISCOVERY_INTERVAL_HOURS=6

# Минимальный рост токена для анализа
MIN_TOKEN_GAIN=3.0  # x3

# Минимальная оценка для публикации
MIN_SCORE_TO_PUBLISH=70

# Максимум постов в день
MAX_POSTS_PER_DAY=10
```

---

## 🔧 TROUBLESHOOTING

### Проблема: "API ключ не установлен"
**Решение:** Проверьте `.env` файл, убедитесь что ключи скопированы правильно

### Проблема: "Database not found"
**Решение:** Запустите `python scripts/init_database.py`

### Проблема: "Rate limit exceeded"
**Решение:** Увеличьте `API_DELAY_SECONDS` в `.env`

### Проблема: "No wallets found"
**Решение:** Подождите несколько часов, discovery engine найдёт новых трейдеров

---

## 📚 ДАЛЬШЕ

### Проверить статус системы:
```bash
python scripts/status.py
```

### Запустить discovery вручную:
```bash
python scripts/run_discovery.py
```

### Посмотреть логи:
```bash
tail -f logs/system.log
```

---

## 🎯 РЕЖИМЫ РАБОТЫ

### Development (разработка)
```env
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```
- Подробные логи
- Тестовые данные
- Локальная БД

### Production (продакшн)
```env
ENVIRONMENT=production
LOG_LEVEL=INFO
```
- Минимальные логи
- Реальные данные
- Оптимизация производительности

---

## 💡 СОВЕТЫ

### 1. Начните с тестового режима
Первые 24 часа работы в `development` режиме, чтобы убедиться что всё работает

### 2. Мониторьте точность
Проверяйте accuracy сигналов через 7 дней работы

### 3. Настройте пороги
Если много ложных сигналов → увеличьте `MIN_SCORE_TO_PUBLISH`

### 4. Backup базы данных
```bash
cp data/database.db data/database_backup.db
```

---

## ❓ ВОПРОСЫ?

- 📖 Полная документация: `README.md`
- 🏗️ Архитектура: `docs/ARCHITECTURE.md`
- 🐛 Нашли баг? Создайте Issue

---

**Готово! Система запущена и работает! 🎉**

Первые сигналы появятся через 6-12 часов, когда discovery engine найдёт актуальных трейдеров.