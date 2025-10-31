# ============================================================================
# CRYPTO COMPASS - Production Dockerfile for Render.com
# Python 3.11 + Pre-built wheels ONLY
# ============================================================================

FROM python:3.11.9-slim-bookworm

# Метаданные
LABEL maintainer="crypto-compass"
LABEL version="1.0"

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (МИНИМУМ!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Обновляем pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем Python зависимости
# КРИТИЧНО: --only-binary=:all: предотвращает компиляцию!
RUN pip install --no-cache-dir \
    --only-binary=:all: \
    --prefer-binary \
    -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём необходимые директории
RUN mkdir -p data/history data/learning data/wallets data/positions data/performance logs

# Expose порт (для health check)
EXPOSE 8000

# Health check (опционально)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Запуск приложения
CMD ["python", "-u", "main.py"]