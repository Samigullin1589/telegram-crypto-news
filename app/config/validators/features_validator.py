"""
Features Validator
Валидация функциональных модулей системы

Проверяет:
- Хотя бы один модуль включен
- Зависимости между модулями
- Необходимые условия для работы каждого модуля
- Согласованность настроек модулей
"""

import logging
from typing import TYPE_CHECKING, Dict, List

from .base_validator import BaseValidator

if TYPE_CHECKING:
    from .. import Config

logger = logging.getLogger(__name__)


class FeaturesValidator(BaseValidator):
    """
    Валидатор функциональных модулей
    
    Проверяет настройки и зависимости основных модулей системы:
    - Whale мониторинг
    - News агрегация
    - Analytics
    - Trading система
    - Hyperliquid интеграция
    """
    
    def validate(self) -> list:
        """
        Выполнить валидацию функциональных модулей
        
        Returns:
            Список всех сообщений валидации
        """
        logger.debug("Запуск валидации функциональных модулей...")
        
        # Очистка предыдущих результатов
        self.clear_messages()
        
        # Проверка что хотя бы один модуль включен
        if not self._validate_at_least_one_enabled():
            # Критическая ошибка - нечего делать дальше
            return self.get_all_messages()
        
        # Вывод информации о включенных модулях
        self._print_enabled_modules()
        
        # Проверка зависимостей между модулями
        self._validate_module_dependencies()
        
        # Проверка условий для каждого включенного модуля
        if self.config.features.whale_enabled:
            self._validate_whale_module()
        
        if self.config.features.news_enabled:
            self._validate_news_module()
        
        if self.config.features.analytics_enabled:
            self._validate_analytics_module()
        
        if self.config.features.trading_enabled:
            self._validate_trading_module()
        
        if self.config.features.hyperliquid_enabled:
            self._validate_hyperliquid_module()
        
        logger.debug(f"Валидация модулей завершена: {len(self.errors)} ошибок, {len(self.warnings)} предупреждений")
        
        return self.get_all_messages()
    
    # ========================================================================
    # БАЗОВЫЕ ПРОВЕРКИ
    # ========================================================================
    
    def _validate_at_least_one_enabled(self) -> bool:
        """
        Проверка что хотя бы один модуль включен
        
        Returns:
            True если есть хотя бы один включенный модуль
        """
        if not self.config.features.is_any_feature_enabled():
            self._add_error(
                "Все функциональные модули отключены! "
                "Бот не будет выполнять никаких действий. "
                "Включите хотя бы один модуль через переменные окружения: "
                "WHALE_ENABLED, NEWS_ENABLED, ANALYTICS_ENABLED, TRADING_ENABLED, HYPERLIQUID_ENABLED"
            )
            return False
        
        return True
    
    def _print_enabled_modules(self) -> None:
        """Вывод информации о включенных модулях"""
        enabled = self.config.features.get_enabled_features()
        enabled_names = [name for name, status in enabled.items() if status]
        
        if enabled_names:
            self._add_info(f"Включенные модули: {', '.join(enabled_names)}")
        
        # Подробная информация о каждом включенном модуле
        for name in enabled_names:
            module_info = self._get_module_description(name)
            logger.debug(f"Модуль '{name}': {module_info}")
    
    def _get_module_description(self, module_name: str) -> str:
        """
        Получение описания модуля
        
        Args:
            module_name: Название модуля
            
        Returns:
            Краткое описание функционала модуля
        """
        descriptions = {
            'whale': 'Мониторинг крупных транзакций на блокчейнах',
            'news': 'Агрегация и AI-обработка криптовалютных новостей',
            'analytics': 'Анализ sentiment, корреляций и рисков',
            'trading': 'Генерация торговых сигналов и мониторинг позиций',
            'hyperliquid': 'Мониторинг perpetual futures и ликвидаций'
        }
        return descriptions.get(module_name, 'Неизвестный модуль')
    
    # ========================================================================
    # ЗАВИСИМОСТИ МОДУЛЕЙ
    # ========================================================================
    
    def _validate_module_dependencies(self) -> None:
        """
        Проверка зависимостей между модулями
        
        Некоторые модули требуют или рекомендуют наличие других модулей
        для полноценной работы.
        """
        logger.debug("Проверка зависимостей между модулями...")
        
        # Analytics зависит от данных из News или Whale
        if self.config.features.analytics_enabled:
            if not self.config.features.news_enabled and not self.config.features.whale_enabled:
                self._add_error(
                    "Analytics модуль включен, но отключены источники данных (News и Whale). "
                    "Analytics требует хотя бы один источник данных для анализа"
                )
            elif not self.config.features.news_enabled:
                self._add_warning(
                    "Analytics модуль работает без News модуля. "
                    "Sentiment анализ и анализ новостей будут недоступны"
                )
        
        # Trading рекомендуется с Whale мониторингом
        if self.config.features.trading_enabled and not self.config.features.whale_enabled:
            self._add_warning(
                "Trading модуль включен без Whale мониторинга. "
                "Рекомендуется включить whale мониторинг для генерации более точных торговых сигналов "
                "на основе активности крупных игроков"
            )
        
        # Trading рекомендуется с Analytics
        if self.config.features.trading_enabled and not self.config.features.analytics_enabled:
            self._add_warning(
                "Trading модуль работает без Analytics. "
                "Risk scoring и sentiment анализ улучшат качество торговых сигналов"
            )
        
        # Hyperliquid может работать с Trading для дополнительных сигналов
        if self.config.features.hyperliquid_enabled and self.config.features.trading_enabled:
            self._add_info(
                "Hyperliquid и Trading модули работают вместе. "
                "Данные о ликвидациях будут учитываться в торговых сигналах"
            )
    
    # ========================================================================
    # WHALE MODULE
    # ========================================================================
    
    def _validate_whale_module(self) -> None:
        """Валидация модуля whale мониторинга"""
        logger.debug("Валидация Whale модуля...")
        
        # Проверка наличия активных блокчейнов
        if len(self.config.blockchain.enabled_chains) == 0:
            self._add_error(
                "Whale мониторинг включен, но нет активных блокчейнов. "
                "Установите переменную ENABLED_CHAINS"
            )
            return
        
        # Проверка CoinGecko для получения цен
        if not self.config.has_coingecko():
            self._add_warning(
                "Whale мониторинг работает без CoinGecko API ключа. "
                "Получение цен токенов будет работать с ограничениями. "
                "Некоторые транзакции могут быть пропущены из-за невозможности определить USD стоимость"
            )
        
        # Проверка scanner ключей для включенных chains
        missing_scanner_keys = self.config.get_missing_scanner_keys()
        if missing_scanner_keys:
            enabled_without_keys = [
                chain for chain in self.config.blockchain.enabled_chains 
                if chain in missing_scanner_keys
            ]
            if enabled_without_keys:
                self._add_warning(
                    f"Whale мониторинг: отсутствуют scanner ключи для активных chains: "
                    f"{', '.join(enabled_without_keys)}. "
                    f"Мониторинг этих сетей будет работать с ограничениями rate limit"
                )
        
        # Проверка Helius для Solana
        if self.config.blockchain.is_chain_enabled('solana'):
            if not self.config.api.helius_api_key:
                self._add_warning(
                    "Whale мониторинг Solana включен без Helius API ключа. "
                    "Настоятельно рекомендуется получить бесплатный ключ на helius.dev "
                    "для стабильной работы с Solana"
                )
        
        self._add_info("Whale мониторинг: все необходимые условия проверены")
    
    # ========================================================================
    # NEWS MODULE
    # ========================================================================
    
    def _validate_news_module(self) -> None:
        """Валидация модуля новостей"""
        logger.debug("Валидация News модуля...")
        
        # Проверка наличия RSS фидов
        active_feeds = self.config.feeds.get_enabled_feeds()
        if len(active_feeds) == 0:
            self._add_error(
                "News модуль включен, но нет активных RSS источников. "
                "Модуль не сможет получать новости. "
                "Проверьте конфигурацию RSS_FEEDS"
            )
            return
        
        # Проверка AI провайдера
        if not self.config.api.has_ai_provider():
            self._add_warning(
                "News модуль работает без AI провайдера. "
                "AI-обработка новостей (улучшение форматирования, анализ тональности) будет недоступна. "
                "Новости будут публиковаться в сыром виде. "
                "Установите один из ключей: OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY"
            )
        else:
            ai_provider = self.config.api.get_ai_provider()
            self._add_info(f"News модуль: будет использоваться AI провайдер {ai_provider}")
        
        # Проверка лимитов публикации
        if hasattr(self.config.features, 'news_posts_per_hour'):
            posts_limit = self.config.features.news_posts_per_hour
            if posts_limit < 1:
                self._add_error(
                    f"News модуль: некорректный лимит публикаций {posts_limit} постов/час. "
                    f"Должен быть >= 1"
                )
            elif posts_limit > 10:
                self._add_warning(
                    f"News модуль: высокий лимит публикаций ({posts_limit} постов/час). "
                    f"Это может привести к спаму в канале"
                )
        
        self._add_info("News модуль: проверка завершена")
    
    # ========================================================================
    # ANALYTICS MODULE
    # ========================================================================
    
    def _validate_analytics_module(self) -> None:
        """Валидация модуля аналитики"""
        logger.debug("Валидация Analytics модуля...")
        
        # Проверка источников данных
        has_news = self.config.features.news_enabled
        has_whale = self.config.features.whale_enabled
        
        if not has_news and not has_whale:
            self._add_error(
                "Analytics модуль включен без источников данных (News и Whale отключены). "
                "Analytics не сможет выполнять анализ. "
                "Включите хотя бы один источник данных"
            )
            return
        
        # Информация о доступных типах анализа
        available_analytics = []
        
        if has_news:
            available_analytics.extend([
                'Sentiment анализ новостей',
                'Трендовый анализ тем'
            ])
        
        if has_whale:
            available_analytics.extend([
                'Анализ активности крупных кошельков',
                'Корреляция whale движений с ценами'
            ])
        
        if has_news and has_whale:
            available_analytics.append('Кросс-анализ новостей и whale активности')
        
        self._add_info(
            f"Analytics модуль: доступные типы анализа - {', '.join(available_analytics)}"
        )
    
    # ========================================================================
    # TRADING MODULE
    # ========================================================================
    
    def _validate_trading_module(self) -> None:
        """Валидация торговой системы"""
        logger.debug("Валидация Trading модуля...")
        
        # Проверка наличия данных для генерации сигналов
        has_data_sources = False
        data_sources = []
        
        if self.config.features.whale_enabled:
            has_data_sources = True
            data_sources.append('Whale транзакции')
        
        if self.config.features.analytics_enabled:
            has_data_sources = True
            data_sources.append('Analytics данные')
        
        if self.config.features.hyperliquid_enabled:
            has_data_sources = True
            data_sources.append('Hyperliquid данные')
        
        if not has_data_sources:
            self._add_warning(
                "Trading модуль работает без дополнительных источников данных. "
                "Качество торговых сигналов будет базовым. "
                "Рекомендуется включить: Whale мониторинг, Analytics или Hyperliquid"
            )
        else:
            self._add_info(
                f"Trading модуль: источники данных для сигналов - {', '.join(data_sources)}"
            )
        
        # Проверка API для получения рыночных данных
        if not self.config.has_coingecko() and not self.config.has_coinmarketcap():
            self._add_warning(
                "Trading модуль: отсутствуют API для получения рыночных данных. "
                "Настройте CoinGecko или CoinMarketCap API ключи"
            )
    
    # ========================================================================
    # HYPERLIQUID MODULE
    # ========================================================================
    
    def _validate_hyperliquid_module(self) -> None:
        """Валидация Hyperliquid интеграции"""
        logger.debug("Валидация Hyperliquid модуля...")
        
        # Проверка API URL
        if hasattr(self.config.api, 'hyperliquid_api_url'):
            api_url = self.config.api.hyperliquid_api_url
            if not api_url:
                self._add_error(
                    "Hyperliquid модуль включен, но не настроен API URL. "
                    "Установите HYPERLIQUID_API_URL"
                )
            elif not self._validate_url(api_url, "Hyperliquid API", require_https=True):
                pass  # Ошибка уже добавлена
            else:
                self._add_info(f"Hyperliquid API URL: {api_url}")
        else:
            self._add_warning(
                "Hyperliquid модуль включен, но API URL не настроен в конфигурации"
            )
        
        # Проверка интеграции с Trading
        if self.config.features.trading_enabled:
            self._add_info(
                "Hyperliquid модуль интегрирован с Trading системой. "
                "Данные о ликвидациях будут использоваться в торговых сигналах"
            )
    
    # ========================================================================
    # СВОДКА
    # ========================================================================
    
    def get_summary(self) -> Dict[str, any]:
        """
        Получить сводку валидации модулей
        
        Returns:
            Словарь со статистикой
        """
        enabled_features = self.config.features.get_enabled_features()
        
        return {
            'total_enabled': sum(1 for v in enabled_features.values() if v),
            'enabled_modules': [k for k, v in enabled_features.items() if v],
            'disabled_modules': [k for k, v in enabled_features.items() if not v],
            'has_errors': self.has_errors(),
            'has_warnings': self.has_warnings(),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
        }