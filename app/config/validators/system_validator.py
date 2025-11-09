"""
System Validator
Валидация системных настроек

Проверяет:
- Базовую конфигурацию (окружение, порт, debug)
- Пути к файлам и директориям
- Telegram настройки
- RSS фиды
- База данных
- Rate limiting
"""

import logging
from typing import TYPE_CHECKING, Any
from pathlib import Path

from .base_validator import BaseValidator

if TYPE_CHECKING:
    from .. import Config

logger = logging.getLogger(__name__)


class SystemValidator(BaseValidator):
    """
    Валидатор системных настроек
    
    Объединяет проверки всех базовых системных параметров,
    необходимых для работы приложения.
    """
    
    def validate(self) -> list:
        """
        Выполнить валидацию системы
        
        Returns:
            Список всех сообщений валидации
        """
        logger.debug("Запуск валидации системных настроек...")
        
        self.clear_messages()
        
        self._validate_base_config()
        self._validate_paths()
        self._validate_telegram()
        self._validate_feeds()
        self._validate_database()
        self._validate_rate_limiting()
        
        logger.debug(
            f"Валидация системы завершена: "
            f"{len(self.errors)} ошибок, {len(self.warnings)} предупреждений"
        )
        
        return self.get_all_messages()
    
    # ========================================================================
    # БАЗОВАЯ КОНФИГУРАЦИЯ
    # ========================================================================
    
    def _validate_base_config(self) -> None:
        """Валидация базовой конфигурации окружения"""
        logger.debug("Проверка базовой конфигурации...")
        
        valid_environments = ['production', 'staging', 'development']
        current_env = self.config.base.ENVIRONMENT.lower()
        
        if current_env not in valid_environments:
            self._add_warning(
                f"Неизвестное окружение: {self.config.base.ENVIRONMENT}. "
                f"Допустимые: {', '.join(valid_environments)}. "
                f"Будет использовано поведение по умолчанию"
            )
        else:
            self._add_info(f"Окружение: {self.config.base.ENVIRONMENT}")
        
        if self.config.base.is_production() and self.config.base.DEBUG_MODE:
            self._add_warning(
                "DEBUG режим включен в production окружении! "
                "Это снижает производительность и может раскрывать конфиденциальную информацию. "
                "Рекомендуется отключить: установите DEBUG_MODE=false"
            )
        
        if self._validate_port(self.config.base.PORT, name="Системный порт"):
            self._add_info(f"Порт: {self.config.base.PORT}")
        
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.config.base.LOG_LEVEL not in valid_log_levels:
            self._add_warning(
                f"Некорректный уровень логирования: {self.config.base.LOG_LEVEL}. "
                f"Допустимые: {', '.join(valid_log_levels)}"
            )
        else:
            self._add_info(f"Уровень логирования: {self.config.base.LOG_LEVEL}")
    
    # ========================================================================
    # ПУТИ
    # ========================================================================
    
    def _validate_paths(self) -> None:
        """Валидация путей к файлам и директориям"""
        logger.debug("Проверка путей...")
        
        data_dir = self.config.paths.data_dir
        
        if not data_dir.exists():
            self._add_warning(
                f"Data директория не существует: {data_dir}. "
                f"Будет создана автоматически при первом запуске"
            )
        else:
            if not data_dir.is_dir():
                self._add_error(
                    f"Путь {data_dir} существует, но не является директорией. "
                    f"Удалите файл или измените путь DATA_DIR"
                )
            elif not self._can_write_to_directory(data_dir):
                self._add_error(
                    f"Нет прав на запись в data директорию: {data_dir}. "
                    f"Проверьте права доступа к файловой системе"
                )
            else:
                self._add_info(f"Data директория: {data_dir}")
        
        self._validate_database_paths()
        
        if hasattr(self.config.paths, 'wallets_dir'):
            wallets_dir = self.config.paths.wallets_dir
            if not wallets_dir.exists():
                self._add_info(
                    f"Wallets директория будет создана: {wallets_dir}"
                )
    
    def _validate_database_paths(self) -> None:
        """Валидация путей к файлам баз данных"""
        db_paths = {
            'Основная БД': self.config.paths.db_path,
            'News БД': self.config.paths.news_db_path,
        }
        
        for name, db_path in db_paths.items():
            if db_path.exists():
                if not db_path.is_file():
                    self._add_error(
                        f"{name}: путь {db_path} не является файлом"
                    )
                elif not self._can_write_to_file(db_path):
                    self._add_error(
                        f"{name}: нет прав на запись в файл {db_path}"
                    )
                else:
                    size_mb = db_path.stat().st_size / (1024 * 1024)
                    if size_mb > 100:
                        self._add_warning(
                            f"{name}: большой размер файла ({size_mb:.1f} MB). "
                            f"Рекомендуется регулярная очистка старых данных"
                        )
            else:
                parent_dir = db_path.parent
                if not parent_dir.exists():
                    self._add_warning(
                        f"{name}: родительская директория не существует: {parent_dir}. "
                        f"Будет создана автоматически"
                    )
                elif not self._can_write_to_directory(parent_dir):
                    self._add_error(
                        f"{name}: нет прав на создание файла в директории {parent_dir}"
                    )
    
    # ========================================================================
    # TELEGRAM
    # ========================================================================
    
    def _validate_telegram(self) -> None:
        """Валидация Telegram настроек"""
        logger.debug("Проверка Telegram...")
        
        if not self.config.telegram.bot_token:
            self._add_error(
                "Отсутствует TELEGRAM_BOT_TOKEN! "
                "Бот не сможет работать без токена. "
                "Получите токен у @BotFather в Telegram"
            )
            return
        
        token = self.config.telegram.bot_token
        if len(token) < 40:
            self._add_warning(
                f"TELEGRAM_BOT_TOKEN выглядит слишком коротким ({len(token)} символов). "
                f"Типичная длина: 45-50 символов"
            )
        
        if ':' not in token:
            self._add_error(
                "TELEGRAM_BOT_TOKEN имеет неожиданный формат. "
                "Ожидается формат: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz. "
                "Проверьте правильность токена"
            )
        else:
            bot_id = token.split(':')[0]
            self._add_info(f"Telegram Bot ID: {bot_id}")
        
        if not self.config.telegram.channel_id:
            self._add_error(
                "Отсутствует TELEGRAM_CHANNEL_ID. "
                "Бот не сможет публиковать сообщения. "
                "Укажите ID канала или @username"
            )
        else:
            self._validate_telegram_id('TELEGRAM_CHANNEL_ID', self.config.telegram.channel_id)
        
        if not self.config.telegram.admin_chat_id:
            self._add_warning(
                "Отсутствует ADMIN_CHAT_ID. "
                "Системные уведомления и ошибки не будут отправляться администратору"
            )
        else:
            self._validate_telegram_id('ADMIN_CHAT_ID', self.config.telegram.admin_chat_id)
        
        if hasattr(self.config.telegram, 'webhook_url') and self.config.telegram.webhook_url:
            if not self._validate_url(self.config.telegram.webhook_url, "Telegram Webhook", require_https=True):
                self._add_error(
                    "Telegram Webhook URL должен использовать HTTPS для безопасности"
                )
    
    def _validate_telegram_id(self, name: str, value: Any) -> None:
        """
        Валидация Telegram ID или username
        
        Args:
            name: Название параметра
            value: Значение ID для проверки
        """
        value_str = str(value)
        
        if value_str.startswith('@'):
            if len(value_str) < 6:
                self._add_warning(
                    f"{name}: username {value_str} выглядит слишком коротким"
                )
            else:
                self._add_info(f"{name}: username формат ({value_str})")
        elif value_str.startswith('-') or value_str.lstrip('-').isdigit():
            self._add_info(f"{name}: числовой ID формат")
        else:
            self._add_warning(
                f"{name}: неожиданный формат значения '{value_str}'. "
                f"Ожидается @username или числовой ID"
            )
    
    # ========================================================================
    # RSS ФИДЫ
    # ========================================================================
    
    def _validate_feeds(self) -> None:
        """Валидация RSS фидов"""
        logger.debug("Проверка RSS фидов...")
        
        active_feeds = self.config.feeds.get_enabled_feeds()
        total_feeds = len(self.config.feeds.feeds)
        
        if len(active_feeds) == 0:
            self._add_error(
                "Нет активных RSS источников новостей. "
                "Новостной модуль не сможет получать контент. "
                "Проверьте конфигурацию RSS_FEEDS"
            )
            return
        
        if len(active_feeds) < 3:
            self._add_warning(
                f"Мало активных RSS источников: {len(active_feeds)} из {total_feeds}. "
                f"Рекомендуется минимум 3-5 источников для разнообразия контента и надежности"
            )
        else:
            self._add_info(
                f"Активных RSS источников: {len(active_feeds)} из {total_feeds}"
            )
        
        for feed_name, feed_config in active_feeds.items():
            self._validate_single_feed(feed_name, feed_config)
    
    def _validate_single_feed(self, name: str, config: Any) -> None:
        """
        Валидация одного RSS фида
        
        Args:
            name: Название фида
            config: Конфигурация фида
        """
        if not config.url:
            self._add_error(f"Фид '{name}': отсутствует URL")
            return
        
        if not self._validate_url(config.url, f"RSS фид '{name}'"):
            return
        
        if hasattr(config, 'priority'):
            if not self._validate_range(config.priority, 1, 100, f"Приоритет фида '{name}'"):
                pass
        
        if hasattr(config, 'category'):
            valid_categories = ['news', 'analysis', 'defi', 'nft', 'bitcoin', 'ethereum', 'altcoins']
            if config.category and config.category.lower() not in valid_categories:
                self._add_info(
                    f"Фид '{name}': нестандартная категория '{config.category}'"
                )
    
    # ========================================================================
    # БАЗА ДАННЫХ
    # ========================================================================
    
    def _validate_database(self) -> None:
        """Валидация настроек базы данных"""
        logger.debug("Проверка базы данных...")
        
        # ИСПРАВЛЕНО: используем pool.min_size
        if hasattr(self.config.database, 'pool') and hasattr(self.config.database.pool, 'min_size'):
            pool_size = self.config.database.pool.min_size
            
            if not self._validate_positive(pool_size, "Database pool_size", allow_zero=False):
                return
            
            if pool_size > 20:
                self._add_warning(
                    f"Очень большой connection pool: {pool_size}. "
                    f"На Render.com с ограниченной памятью рекомендуется 5-10. "
                    f"Это может привести к избыточному потреблению ресурсов"
                )
            else:
                self._add_info(f"Database connection pool: {pool_size}")
        
        # Max overflow
        if hasattr(self.config.database, 'max_overflow'):
            if not self._validate_positive(
                self.config.database.max_overflow, 
                "Database max_overflow", 
                allow_zero=True
            ):
                return
        
        # ИСПРАВЛЕНО: используем enable_auto_backup
        if hasattr(self.config.database, 'enable_auto_backup') and self.config.database.enable_auto_backup:
            self._validate_backup_settings()
        else:
            self._add_warning(
                "Database backup отключен. "
                "Рекомендуется включить автоматическое резервное копирование"
            )
        
        # ИСПРАВЛЕНО: используем pool.timeout
        if hasattr(self.config.database, 'pool') and hasattr(self.config.database.pool, 'timeout'):
            if self.config.database.pool.timeout < 5:
                self._add_warning(
                    f"Слишком короткий pool_timeout: {self.config.database.pool.timeout} секунд. "
                    f"Это может привести к таймаутам при высокой нагрузке"
                )
    
    def _validate_backup_settings(self) -> None:
        """Валидация настроек резервного копирования"""
        # ИСПРАВЛЕНО: убрана проверка backup_interval_hours, которого нет в DatabaseConfig
        
        if not hasattr(self.config.database, 'backup_retention_days'):
            return
        
        retention = self.config.database.backup_retention_days
        
        if retention < 1:
            self._add_error(f"backup_retention_days должен быть >= 1: {retention}")
        elif retention < 3:
            self._add_warning(
                f"Короткий срок хранения backup: {retention} дней. "
                f"Рекомендуется минимум 7 дней"
            )
        else:
            self._add_info(f"Database backup retention: {retention} дней")
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    
    def _validate_rate_limiting(self) -> None:
        """Валидация rate limiting"""
        logger.debug("Проверка rate limiting...")
        
        if not self.config.rate_limiting.enabled:
            self._add_warning(
                "Rate limiting отключен. "
                "Это может привести к превышению лимитов внешних API и блокировке. "
                "Настоятельно рекомендуется включить: RATE_LIMITING_ENABLED=true"
            )
            return
        
        rpm = self.config.rate_limiting.max_requests_per_minute
        
        if not self._validate_positive(rpm, "Rate limit", allow_zero=False):
            return
        
        if rpm < 10:
            self._add_warning(
                f"Очень строгий rate limit: {rpm} запросов/минуту. "
                f"Это может существенно замедлить работу системы. "
                f"Рекомендуется 30-60 запросов/минуту"
            )
        elif rpm > 300:
            self._add_warning(
                f"Очень высокий rate limit: {rpm} запросов/минуту. "
                f"Убедитесь что внешние API поддерживают такую нагрузку. "
                f"Многие бесплатные API ограничивают до 100-300 req/min"
            )
        else:
            self._add_info(f"Rate limit: {rpm} запросов/минуту")
        
        if hasattr(self.config.rate_limiting, 'burst_size'):
            burst = self.config.rate_limiting.burst_size
            if burst < 1:
                self._add_error("burst_size должен быть >= 1")
            elif burst > rpm:
                self._add_warning(
                    f"burst_size ({burst}) больше max_requests_per_minute ({rpm}). "
                    f"Это приведет к превышению минутного лимита"
                )
        
        if self.config.blockchain.is_chain_enabled('solana'):
            self._validate_solana_rate_limits()
    
    def _validate_solana_rate_limits(self) -> None:
        """Валидация rate limits для Solana"""
        if not hasattr(self.config.rate_limiting, 'solana_requests_per_second'):
            self._add_warning(
                "Solana включена, но не настроены специфичные rate limits для Solana RPC"
            )
            return
        
        solana_rps = self.config.rate_limiting.solana_requests_per_second
        
        if not self._validate_positive(solana_rps, "Solana RPS", allow_zero=False):
            return
        
        if solana_rps > 50:
            self._add_warning(
                f"Очень высокий лимит для Solana RPC: {solana_rps} запросов/секунду. "
                f"Helius API (бесплатный план) обычно ограничивает до 25 req/sec. "
                f"Проверьте лимиты вашего RPC провайдера"
            )
        elif solana_rps < 5:
            self._add_warning(
                f"Низкий лимит для Solana RPC: {solana_rps} запросов/секунду. "
                f"Это может замедлить мониторинг Solana транзакций"
            )
        else:
            self._add_info(f"Solana rate limit: {solana_rps} запросов/секунду")