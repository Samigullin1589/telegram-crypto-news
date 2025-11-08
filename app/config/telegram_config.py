"""
Telegram Configuration Module
Конфигурация Telegram бота с валидацией

Включает проверку формата токена и ID каналов.
"""

import os
import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TelegramConfig:
    """
    Конфигурация Telegram бота
    
    Содержит настройки токена, каналов, форматирования
    и webhook. Включает валидацию формата токена.
    """
    
    def __init__(self):
        """Инициализация Telegram настроек"""
        
        # ====================================================================
        # ТОКЕН И ИДЕНТИФИКАТОРЫ
        # ====================================================================
        
        # Bot token
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        
        # Валидация формата токена
        if self.bot_token:
            self._validate_bot_token()
        
        # Channel и Admin IDs
        self.channel_id = os.getenv('TELEGRAM_CHANNEL_ID', '')
        self.admin_chat_id = os.getenv('ADMIN_CHAT_ID', self.channel_id)
        
        # Валидация channel IDs
        if self.channel_id:
            self._validate_channel_id('TELEGRAM_CHANNEL_ID', self.channel_id)
        if self.admin_chat_id:
            self._validate_channel_id('ADMIN_CHAT_ID', self.admin_chat_id)
        
        # ====================================================================
        # ФОРМАТИРОВАНИЕ
        # ====================================================================
        
        # Режим парсинга (Markdown, HTML, MarkdownV2)
        self.parse_mode = os.getenv('TELEGRAM_PARSE_MODE', 'Markdown')
        
        # Отключить превью ссылок
        self.disable_web_page_preview = self._get_bool_env('TELEGRAM_DISABLE_WEB_PAGE_PREVIEW', True)
        
        # Отключить нотификации
        self.disable_notification = self._get_bool_env('TELEGRAM_DISABLE_NOTIFICATION', False)
        
        # ====================================================================
        # ЛИМИТЫ И ТАЙМАУТЫ
        # ====================================================================
        
        # Максимальная длина сообщения (Telegram лимит: 4096)
        self.max_message_length = self._get_int_env('TELEGRAM_MAX_MESSAGE_LENGTH', 4096)
        
        # Таймаут для API запросов
        self.api_timeout = self._get_int_env('TELEGRAM_API_TIMEOUT', 30)
        
        # Задержка между сообщениями (антиспам)
        self.message_delay = self._get_float_env('TELEGRAM_MESSAGE_DELAY', 1.0)
        
        # Максимум попыток отправки
        self.max_send_retries = self._get_int_env('TELEGRAM_MAX_SEND_RETRIES', 3)
        
        # ====================================================================
        # WEBHOOK (опционально)
        # ====================================================================
        
        self.webhook_enabled = self._get_bool_env('TELEGRAM_WEBHOOK_ENABLED', False)
        self.webhook_url = os.getenv('TELEGRAM_WEBHOOK_URL', '')
        self.webhook_path = os.getenv('TELEGRAM_WEBHOOK_PATH', '/webhook')
        self.webhook_secret_token = os.getenv('TELEGRAM_WEBHOOK_SECRET', '')
        
        # ====================================================================
        # ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
        # ====================================================================
        
        # Разрешить обновления от других ботов
        self.allow_bot_updates = self._get_bool_env('TELEGRAM_ALLOW_BOT_UPDATES', False)
        
        # Типы обновлений для получения
        self.allowed_updates = self._parse_list_env('TELEGRAM_ALLOWED_UPDATES', ['message', 'callback_query'])
        
        # Rate limiting для отправки
        self.rate_limit_enabled = self._get_bool_env('TELEGRAM_RATE_LIMIT_ENABLED', True)
        self.rate_limit_messages_per_second = self._get_int_env('TELEGRAM_RATE_LIMIT_MSG_PER_SEC', 30)
        
        logger.debug("TelegramConfig инициализирован")
    
    # ========================================================================
    # ВАЛИДАЦИЯ
    # ========================================================================
    
    def _validate_bot_token(self) -> None:
        """
        Валидация формата Telegram bot token
        
        Формат: <bot_id>:<bot_hash>
        Пример: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz-123456789
        """
        # Паттерн Telegram bot token
        pattern = r'^\d+:[A-Za-z0-9_-]{35,}$'
        
        if not re.match(pattern, self.bot_token):
            logger.warning(
                "TELEGRAM_BOT_TOKEN имеет нестандартный формат. "
                "Ожидается: <числа>:<буквы/цифры>. "
                "Токен может быть некорректным"
            )
        else:
            # Извлекаем bot ID
            bot_id = self.bot_token.split(':')[0]
            logger.debug(f"Telegram Bot ID: {bot_id}")
    
    def _validate_channel_id(self, name: str, value: str) -> None:
        """
        Валидация формата channel ID
        
        Args:
            name: Название параметра
            value: Значение для проверки
        """
        # Может быть @username или числовой ID
        if value.startswith('@'):
            # Username формат
            if len(value) < 6:  # @ + минимум 5 символов
                logger.warning(f"{name}: username {value} выглядит слишком коротким")
        elif value.startswith('-') or value.lstrip('-').isdigit():
            # Числовой ID
            logger.debug(f"{name}: числовой ID формат")
        else:
            logger.warning(
                f"{name}: неожиданный формат '{value}'. "
                f"Ожидается @username или числовой ID"
            )
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================
    
    @staticmethod
    def _get_bool_env(key: str, default: bool = False) -> bool:
        """Получение boolean переменной окружения"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """Получение integer переменной окружения"""
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            logger.warning(f"Некорректное значение для {key}, используется default: {default}")
            return default
    
    @staticmethod
    def _get_float_env(key: str, default: float) -> float:
        """Получение float переменной окружения"""
        try:
            return float(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            logger.warning(f"Некорректное значение для {key}, используется default: {default}")
            return default
    
    @staticmethod
    def _parse_list_env(key: str, default: list) -> list:
        """Парсинг списка из переменной окружения"""
        value = os.getenv(key, '')
        if not value:
            return default
        return [item.strip() for item in value.split(',') if item.strip()]
    
    # ========================================================================
    # ПРОВЕРКИ
    # ========================================================================
    
    def has_bot_token(self) -> bool:
        """Проверка наличия bot token"""
        return bool(self.bot_token)
    
    def has_channel_id(self) -> bool:
        """Проверка наличия channel ID"""
        return bool(self.channel_id)
    
    def has_admin_chat_id(self) -> bool:
        """Проверка наличия admin chat ID"""
        return bool(self.admin_chat_id)
    
    def is_webhook_configured(self) -> bool:
        """Проверка настроен ли webhook"""
        return self.webhook_enabled and bool(self.webhook_url)
    
    def get_bot_id(self) -> Optional[str]:
        """
        Получение Bot ID из токена
        
        Returns:
            Bot ID или None если токен некорректный
        """
        if not self.bot_token or ':' not in self.bot_token:
            return None
        return self.bot_token.split(':')[0]
    
    # ========================================================================
    # СЕРИАЛИЗАЦИЯ
    # ========================================================================
    
    def to_dict(self) -> Dict:
        """
        Конвертация в словарь
        
        Bot token маскируется для безопасности.
        
        Returns:
            Словарь с настройками Telegram
        """
        # Маскируем токен для безопасности
        masked_token = ''
        if self.bot_token:
            parts = self.bot_token.split(':')
            if len(parts) == 2:
                masked_token = f"{parts[0]}:{'*' * len(parts[1])}"
            else:
                masked_token = '*' * len(self.bot_token)
        
        return {
            # Идентификаторы (токен маскирован)
            'bot_token': masked_token,
            'has_bot_token': self.has_bot_token(),
            'bot_id': self.get_bot_id(),
            'channel_id': self.channel_id,
            'admin_chat_id': self.admin_chat_id,
            
            # Форматирование
            'parse_mode': self.parse_mode,
            'disable_web_page_preview': self.disable_web_page_preview,
            'disable_notification': self.disable_notification,
            
            # Лимиты
            'max_message_length': self.max_message_length,
            'api_timeout': self.api_timeout,
            'message_delay': self.message_delay,
            'max_send_retries': self.max_send_retries,
            
            # Webhook
            'webhook_enabled': self.webhook_enabled,
            'webhook_configured': self.is_webhook_configured(),
            
            # Rate limiting
            'rate_limit_enabled': self.rate_limit_enabled,
            'rate_limit_messages_per_second': self.rate_limit_messages_per_second,
        }
    
    def __repr__(self) -> str:
        """Строковое представление"""
        bot_id = self.get_bot_id() or 'Unknown'
        return f"TelegramConfig(bot_id={bot_id}, channel={self.channel_id})"