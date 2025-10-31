FROM python:3.11.9-slim-bookworm

LABEL maintainer="crypto-compass"
LABEL version="1.0"
LABEL description="Crypto Compass - AI-powered crypto monitoring"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .

RUN pip install --no-cache-dir \
    --only-binary=:all: \
    --prefer-binary \
    -r requirements.txt

COPY . .

RUN mkdir -p \
    data/history \
    data/learning \
    data/wallets \
    data/positions \
    data/performance \
    logs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "-u", "main.py"]