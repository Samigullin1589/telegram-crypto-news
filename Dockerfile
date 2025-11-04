# Dockerfile - Production-Ready Multi-Stage Build для Render.com
# Оптимизирован для Python 3.11 и минимального размера образа

# ============================================================================
# STAGE 1: Builder - Компиляция зависимостей
# ============================================================================
FROM python:3.11-slim-bookworm AS builder

# Метаданные
LABEL maintainer="Crypto Compass Team"
LABEL version="4.3.0"
LABEL description="Integrated Crypto Monitoring System"

# Установка build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости
# --no-cache-dir экономит место
# --disable-pip-version-check ускоряет установку
RUN pip install --no-cache-dir --disable-pip-version-check --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# ============================================================================
# STAGE 2: Runtime - Финальный образ
# ============================================================================
FROM python:3.11-slim-bookworm

# Установка runtime dependencies только
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копируем виртуальное окружение из builder
COPY --from=builder /opt/venv /opt/venv

# Устанавливаем PATH
ENV PATH="/opt/venv/bin:$PATH"

# Создаём непривилегированного пользователя для безопасности
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Рабочая директория
WORKDIR /app

# Копируем код приложения
COPY --chown=appuser:appuser . .

# Создаём необходимые директории с правильными permissions
RUN mkdir -p /app/data /app/data/history /app/data/learning /app/data/wallets \
    /app/data/positions /app/data/performance /app/logs && \
    chown -R appuser:appuser /app/data /app/logs

# Python оптимизации
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    # Отключаем .pyc файлы для экономии места
    PYTHONDONTWRITEBYTECODE=1 \
    # Pip оптимизации
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Asyncio оптимизации
    PYTHONASYNCIODEBUG=0

# Порт для health checks (Render требует bind на 0.0.0.0)
EXPOSE 8000

# Healthcheck для Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Переключаемся на непривилегированного пользователя
USER appuser

# Точка входа
ENTRYPOINT ["python", "-u", "main.py"]

# Метаданные для Render
LABEL com.render.service="crypto-compass"
LABEL com.render.type="web"
LABEL com.render.python.version="3.11"