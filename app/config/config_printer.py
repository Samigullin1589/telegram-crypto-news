"""
Configuration Printer
Модуль вывода информации о конфигурации
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Config

logger = logging.getLogger(__name__)


class ConfigPrinter:
    """Принтер конфигурации"""
    
    def __init__(self, config: 'Config'):
        """
        Инициализация принтера
        
        Args:
            config: Экземпляр главной конфигурации
        """
        self.config = config
    
    def print_initialization_header(self) -> None:
        """Вывод заголовка инициализации"""
        print("\n" + "=" * 80)
        print(f"⚙️  CRYPTO COMPASS - CONFIGURATION INITIALIZATION v{self.config.base.APP_VERSION}")
        print("=" * 80 + "\n")
    
    def print_configuration_summary(self) -> None:
        """Вывод полной сводки конфигурации"""
        print("\n" + "=" * 80)
        print("📊 CONFIGURATION SUMMARY")
        print("=" * 80)
        
        self._print_base_config()
        self._print_paths_config()
        self._print_api_config()
        self._print_telegram_config()
        self._print_feeds_config()
        self._print_blockchain_config()
        self._print_features_config()
        self._print_database_config()
        self._print_rate_limiting_config()
        
        print("=" * 80 + "\n")
    
    def _print_base_config(self) -> None:
        """Вывод базовой конфигурации"""
        print(f"\n📋 Основные настройки:")
        print(f"   • Окружение: {self.config.base.ENVIRONMENT}")
        print(f"   • Приложение: {self.config.base.APP_NAME} v{self.config.base.APP_VERSION}")
        print(f"   • Debug режим: {'✅ Включен' if self.config.base.DEBUG_MODE else '❌ Отключен'}")
        print(f"   • Log Level: {self.config.base.LOG_LEVEL}")
        print(f"   • Порт: {self.config.base.PORT}")
        print(f"   • Health Check: {'✅ Включен' if self.config.base.HEALTH_CHECK_ENABLED else '❌ Отключен'}")
        print(f"   • Метрики: {'✅ Включены' if self.config.base.METRICS_ENABLED else '❌ Отключены'}")
    
    def _print_paths_config(self) -> None:
        """Вывод конфигурации путей"""
        print(f"\n📁 Пути:")
        print(f"   • Data директория: {self.config.paths.data_dir}")
        print(f"   • База данных: {self.config.paths.db_path}")
        print(f"   • State файл: {self.config.paths.state_file}")
    
    def _print_api_config(self) -> None:
        """Вывод конфигурации API"""
        print(f"\n🔑 API конфигурация:")
        print(f"   • AI Provider: {self.config.api.get_ai_provider() or '❌ Не настроен'}")
        
        if self.config.api.openai_api_key:
            print(f"   • OpenAI: ✅ Настроен")
        if self.config.api.gemini_api_key:
            print(f"   • Gemini: ✅ Настроен")
        if self.config.api.anthropic_api_key:
            print(f"   • Anthropic: ✅ Настроен")
        if self.config.api.coingecko_api_key:
            print(f"   • CoinGecko: ✅ Настроен")
        if self.config.api.alchemy_api_key:
            print(f"   • Alchemy: ✅ Настроен")
        if self.config.api.coinmarketcap_api_key:
            print(f"   • CoinMarketCap: ✅ Настроен")
    
    def _print_telegram_config(self) -> None:
        """Вывод конфигурации Telegram"""
        print(f"\n📱 Telegram:")
        print(f"   • Bot Token: {'✅ Настроен' if self.config.telegram.bot_token else '❌ Отсутствует'}")
        print(f"   • Канал ID: {self.config.telegram.channel_id or '❌ Не указан'}")
        print(f"   • Admin Chat ID: {self.config.telegram.admin_chat_id or '❌ Не указан'}")
        print(f"   • Режим парсинга: {self.config.telegram.parse_mode}")
    
    def _print_feeds_config(self) -> None:
        """Вывод конфигурации фидов"""
        enabled_feeds = self.config.feeds.get_enabled_feeds()
        total_feeds = len(self.config.feeds.feeds)
        
        print(f"\n📰 RSS Фиды:")
        print(f"   • Всего источников: {total_feeds}")
        print(f"   • Активных: {len(enabled_feeds)}")
        print(f"   • Интервал проверки: {self.config.feeds.fetch_interval} секунд")
        print(f"   • Лимит постов в час: {self.config.feeds.posts_per_hour_cap}")
        
        if enabled_feeds:
            print(f"   • Активные источники:")
            for feed_name in sorted(enabled_feeds.keys()):
                print(f"      - {feed_name}")
    
    def _print_blockchain_config(self) -> None:
        """Вывод конфигурации блокчейнов"""
        print(f"\n⛓️  Блокчейны:")
        print(f"   • Включенные сети: {', '.join(self.config.blockchain.enabled_chains)}")
        print(f"   • Минимальная сумма (USD): ${self.config.blockchain.min_usd:,.0f}")
        
        # Вывод whale thresholds для каждого блокчейна
        print(f"   • Whale пороги:")
        for chain in self.config.blockchain.enabled_chains:
            thresholds = self.config.blockchain.get_whale_threshold(chain)
            symbol = self.config.blockchain.get_chain_symbol(chain)
            print(
                f"      - {chain.upper()}: "
                f"Whale ${thresholds['whale']:,.0f}, "
                f"Mega Whale ${thresholds['mega_whale']:,.0f}"
            )
    
    def _print_features_config(self) -> None:
        """Вывод конфигурации функциональных модулей"""
        print(f"\n🎯 Функциональные модули:")
        print(f"   • Whale Monitor: {'✅ Включен' if self.config.features.whale_enabled else '❌ Отключен'}")
        print(f"   • News Bot: {'✅ Включен' if self.config.features.news_enabled else '❌ Отключен'}")
        print(f"   • Analytics: {'✅ Включен' if self.config.features.analytics_enabled else '❌ Отключен'}")
        print(f"   • Trading System: {'✅ Включен' if self.config.features.trading_enabled else '❌ Отключен'}")
        print(f"   • Hyperliquid: {'✅ Включен' if self.config.features.hyperliquid_enabled else '❌ Отключен'}")
    
    def _print_database_config(self) -> None:
        """Вывод конфигурации базы данных"""
        print(f"\n💾 База данных:")
        print(f"   • Путь: {self.config.database.db_path}")
        print(f"   • Pool size: {self.config.database.pool_size}")
        print(f"   • Max overflow: {self.config.database.max_overflow}")
        print(f"   • Бэкапы: {'✅ Включены' if self.config.database.backup_enabled else '❌ Отключены'}")
        
        if self.config.database.backup_enabled:
            print(f"   • Интервал бэкапа: {self.config.database.backup_interval_hours} часов")
            print(f"   • Хранение бэкапов: {self.config.database.backup_retention_days} дней")
    
    def _print_rate_limiting_config(self) -> None:
        """Вывод конфигурации rate limiting"""
        print(f"\n⏱️  Rate Limiting:")
        print(f"   • Статус: {'✅ Включен' if self.config.rate_limiting.enabled else '❌ Отключен'}")
        
        if self.config.rate_limiting.enabled:
            print(f"   • Лимит: {self.config.rate_limiting.max_requests_per_minute} запросов/минута")
            print(f"   • Burst size: {self.config.rate_limiting.burst_size}")