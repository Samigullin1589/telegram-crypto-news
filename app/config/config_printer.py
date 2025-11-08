"""
Configuration Printer
Отказоустойчивый модуль вывода информации о конфигурации

Этот модуль предоставляет красиво отформатированный вывод
конфигурации системы с полной защитой от AttributeError.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import Config

logger = logging.getLogger(__name__)


class ConfigPrinter:
    """
    Принтер конфигурации
    
    Предоставляет методы для красивого вывода информации о конфигурации.
    Все методы защищены от AttributeError и работают даже при
    неполной инициализации конфигурации.
    """
    
    def __init__(self, config: 'Config'):
        """
        Инициализация принтера
        
        Args:
            config: Экземпляр главной конфигурации
        """
        self.config = config
    
    def print_initialization_header(self) -> None:
        """Вывод заголовка инициализации"""
        try:
            version = self._safe_get('base.APP_VERSION', '3.0.0')
            app_name = self._safe_get('base.APP_NAME', 'CRYPTO COMPASS')
            
            print("\n" + "=" * 80)
            print(f"⚙️  {app_name} - CONFIGURATION INITIALIZATION v{version}")
            print("=" * 80 + "\n")
        except Exception as e:
            logger.error(f"Ошибка вывода заголовка: {e}")
            print("\n" + "=" * 80)
            print("⚙️  CONFIGURATION INITIALIZATION")
            print("=" * 80 + "\n")
    
    def print_configuration_summary(self) -> None:
        """Вывод полной сводки конфигурации"""
        try:
            print("\n" + "=" * 80)
            print("📊 CONFIGURATION SUMMARY")
            print("=" * 80)
            
            # Вывод каждого блока с обработкой ошибок
            self._safe_print_section(self._print_base_config, "Base Config")
            self._safe_print_section(self._print_paths_config, "Paths Config")
            self._safe_print_section(self._print_api_config, "API Config")
            self._safe_print_section(self._print_telegram_config, "Telegram Config")
            self._safe_print_section(self._print_feeds_config, "Feeds Config")
            self._safe_print_section(self._print_blockchain_config, "Blockchain Config")
            self._safe_print_section(self._print_features_config, "Features Config")
            self._safe_print_section(self._print_database_config, "Database Config")
            self._safe_print_section(self._print_rate_limiting_config, "Rate Limiting Config")
            
            print("=" * 80 + "\n")
            
        except Exception as e:
            logger.error(f"Ошибка вывода сводки конфигурации: {e}")
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================
    
    def _safe_get(self, path: str, default: Any = None) -> Any:
        """
        Безопасное получение значения из конфигурации
        
        Args:
            path: Путь к значению через точку (например: 'base.ENVIRONMENT')
            default: Значение по умолчанию
            
        Returns:
            Значение или default
        """
        try:
            parts = path.split('.')
            obj = self.config
            for part in parts:
                obj = getattr(obj, part, None)
                if obj is None:
                    return default
            return obj
        except Exception:
            return default
    
    def _safe_print_section(self, print_func, section_name: str) -> None:
        """
        Безопасный вывод секции с обработкой ошибок
        
        Args:
            print_func: Функция вывода секции
            section_name: Название секции для логирования
        """
        try:
            print_func()
        except Exception as e:
            logger.error(f"Ошибка вывода секции {section_name}: {e}")
            print(f"\n❌ Ошибка вывода секции {section_name}")
    
    # ========================================================================
    # СЕКЦИИ ВЫВОДА
    # ========================================================================
    
    def _print_base_config(self) -> None:
        """Вывод базовой конфигурации"""
        environment = self._safe_get('base.ENVIRONMENT', 'production')
        app_name = self._safe_get('base.APP_NAME', 'Crypto Compass')
        app_version = self._safe_get('base.APP_VERSION', '3.0.0')
        debug_mode = self._safe_get('base.DEBUG_MODE', False)
        log_level = self._safe_get('base.LOG_LEVEL', 'INFO')
        port = self._safe_get('base.PORT', 8000)
        health_check = self._safe_get('base.HEALTH_CHECK_ENABLED', True)
        metrics = self._safe_get('base.METRICS_ENABLED', False)
        
        print(f"\n📋 Основные настройки:")
        print(f"   • Окружение: {environment}")
        print(f"   • Приложение: {app_name} v{app_version}")
        print(f"   • Debug режим: {'✅ Включен' if debug_mode else '❌ Отключен'}")
        print(f"   • Log Level: {log_level}")
        print(f"   • Порт: {port}")
        print(f"   • Health Check: {'✅ Включен' if health_check else '❌ Отключен'}")
        print(f"   • Метрики: {'✅ Включены' if metrics else '❌ Отключены'}")
    
    def _print_paths_config(self) -> None:
        """Вывод конфигурации путей"""
        data_dir = self._safe_get('paths.data_dir', 'data')
        db_path = self._safe_get('paths.db_path', 'data/crypto_monitor.db')
        state_file = self._safe_get('paths.state_file', 'data/state.json')
        
        print(f"\n📁 Пути:")
        print(f"   • Data директория: {data_dir}")
        print(f"   • База данных: {db_path}")
        print(f"   • State файл: {state_file}")
    
    def _print_api_config(self) -> None:
        """Вывод конфигурации API"""
        print(f"\n🔑 API конфигурация:")
        
        # AI Provider
        ai_provider = 'Не настроен'
        if hasattr(self.config, 'api') and hasattr(self.config.api, 'get_ai_provider'):
            provider = self.config.api.get_ai_provider()
            if provider:
                ai_provider = provider.capitalize()
        
        print(f"   • AI Provider: {ai_provider}")
        
        # Проверка отдельных API ключей
        api_keys = {
            'OpenAI': 'openai_api_key',
            'Gemini': 'gemini_api_key',
            'Anthropic': 'anthropic_api_key',
            'CoinGecko': 'coingecko_api_key',
            'Alchemy': 'alchemy_api_key',
            'CoinMarketCap': 'coinmarketcap_api_key',
            'Helius': 'helius_api_key',
        }
        
        for name, key in api_keys.items():
            if self._safe_get(f'api.{key}'):
                print(f"   • {name}: ✅ Настроен")
    
    def _print_telegram_config(self) -> None:
        """Вывод конфигурации Telegram"""
        bot_token = self._safe_get('telegram.bot_token')
        channel_id = self._safe_get('telegram.channel_id')
        admin_chat_id = self._safe_get('telegram.admin_chat_id')
        parse_mode = self._safe_get('telegram.parse_mode', 'Markdown')
        
        print(f"\n📱 Telegram:")
        print(f"   • Bot Token: {'✅ Настроен' if bot_token else '❌ Отсутствует'}")
        print(f"   • Канал ID: {channel_id or '❌ Не указан'}")
        print(f"   • Admin Chat ID: {admin_chat_id or '❌ Не указан'}")
        print(f"   • Режим парсинга: {parse_mode}")
    
    def _print_feeds_config(self) -> None:
        """Вывод конфигурации фидов"""
        total_feeds = 0
        enabled_count = 0
        enabled_feeds = {}
        
        if hasattr(self.config, 'feeds'):
            if hasattr(self.config.feeds, 'feeds'):
                total_feeds = len(self.config.feeds.feeds)
            if hasattr(self.config.feeds, 'get_enabled_feeds'):
                enabled_feeds = self.config.feeds.get_enabled_feeds()
                enabled_count = len(enabled_feeds)
        
        fetch_interval = self._safe_get('feeds.fetch_interval', 300)
        posts_per_hour = self._safe_get('feeds.posts_per_hour_cap', 3)
        
        print(f"\n📰 RSS Фиды:")
        print(f"   • Всего источников: {total_feeds}")
        print(f"   • Активных: {enabled_count}")
        print(f"   • Интервал проверки: {fetch_interval} секунд")
        print(f"   • Лимит постов в час: {posts_per_hour}")
        
        if enabled_feeds and enabled_count <= 10:
            print(f"   • Активные источники:")
            for feed_name in sorted(enabled_feeds.keys()):
                print(f"      - {feed_name}")
        elif enabled_count > 10:
            print(f"   • (Слишком много для вывода: {enabled_count} источников)")
    
    def _print_blockchain_config(self) -> None:
        """Вывод конфигурации блокчейнов"""
        enabled_chains = self._safe_get('blockchain.enabled_chains', [])
        min_usd = self._safe_get('blockchain.min_usd', 100000)
        
        print(f"\n⛓️  Блокчейны:")
        
        if enabled_chains:
            chains_str = ', '.join(enabled_chains)
            print(f"   • Включенные сети: {chains_str}")
        else:
            print(f"   • Включенные сети: ❌ Не настроены")
        
        print(f"   • Минимальная сумма (USD): ${min_usd:,.0f}")
        
        # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: используем правильные ключи
        if enabled_chains and len(enabled_chains) <= 5:
            print(f"   • Whale пороги:")
            for chain in enabled_chains:
                try:
                    if hasattr(self.config.blockchain, 'get_whale_threshold'):
                        thresholds = self.config.blockchain.get_whale_threshold(chain)
                        
                        # ✅ ПРАВИЛЬНЫЕ КЛЮЧИ!
                        whale_threshold = thresholds.get('whale_threshold_usd', 0)
                        mega_whale_threshold = thresholds.get('mega_whale_threshold_usd', 0)
                        
                        if whale_threshold > 0:
                            print(
                                f"      - {chain.upper()}: "
                                f"Whale ${whale_threshold:,.0f}, "
                                f"Mega Whale ${mega_whale_threshold:,.0f}"
                            )
                except Exception as e:
                    logger.debug(f"Не удалось получить thresholds для {chain}: {e}")
    
    def _print_features_config(self) -> None:
        """Вывод конфигурации функциональных модулей"""
        whale_enabled = self._safe_get('features.whale_enabled', False)
        news_enabled = self._safe_get('features.news_enabled', False)
        analytics_enabled = self._safe_get('features.analytics_enabled', False)
        trading_enabled = self._safe_get('features.trading_enabled', False)
        hyperliquid_enabled = self._safe_get('features.hyperliquid_enabled', False)
        
        print(f"\n🎯 Функциональные модули:")
        print(f"   • Whale Monitor: {'✅ Включен' if whale_enabled else '❌ Отключен'}")
        print(f"   • News Bot: {'✅ Включен' if news_enabled else '❌ Отключен'}")
        print(f"   • Analytics: {'✅ Включен' if analytics_enabled else '❌ Отключен'}")
        print(f"   • Trading System: {'✅ Включен' if trading_enabled else '❌ Отключен'}")
        print(f"   • Hyperliquid: {'✅ Включен' if hyperliquid_enabled else '❌ Отключен'}")
    
    def _print_database_config(self) -> None:
        """Вывод конфигурации базы данных"""
        db_path = self._safe_get('database.db_path', 'data/crypto_monitor.db')
        pool_size = self._safe_get('database.pool_size', 5)
        max_overflow = self._safe_get('database.max_overflow', 10)
        backup_enabled = self._safe_get('database.backup_enabled', False)
        
        print(f"\n💾 База данных:")
        print(f"   • Путь: {db_path}")
        print(f"   • Pool size: {pool_size}")
        print(f"   • Max overflow: {max_overflow}")
        print(f"   • Бэкапы: {'✅ Включены' if backup_enabled else '❌ Отключены'}")
        
        if backup_enabled:
            backup_interval = self._safe_get('database.backup_interval_hours', 24)
            backup_retention = self._safe_get('database.backup_retention_days', 7)
            print(f"   • Интервал бэкапа: {backup_interval} часов")
            print(f"   • Хранение бэкапов: {backup_retention} дней")
    
    def _print_rate_limiting_config(self) -> None:
        """Вывод конфигурации rate limiting"""
        enabled = self._safe_get('rate_limiting.enabled', True)
        
        print(f"\n⏱️  Rate Limiting:")
        print(f"   • Статус: {'✅ Включен' if enabled else '❌ Отключен'}")
        
        if enabled:
            max_rpm = self._safe_get('rate_limiting.max_requests_per_minute', 60)
            burst_size = self._safe_get('rate_limiting.burst_size', 10)
            print(f"   • Лимит: {max_rpm} запросов/минута")
            print(f"   • Burst size: {burst_size}")
            
            # Solana specific
            solana_rps = self._safe_get('rate_limiting.solana_requests_per_second')
            if solana_rps:
                print(f"   • Solana RPC: {solana_rps} запросов/секунда")
    
    def __repr__(self) -> str:
        """Строковое представление принтера"""
        return f"ConfigPrinter(config={self.config.__class__.__name__})"