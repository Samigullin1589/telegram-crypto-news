# app/config/telegram_config.py
"""
Telegram Configuration Module
Конфигурация Telegram бота и каналов
"""

import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class TelegramConfig:
    """
    Конфигурация Telegram бота
    Настройки токена, каналов и ограничений API
    """
    
    def __init__(self):
        """Инициализация Telegram конфигурации"""
        self._load_credentials()
        self._setup_limits()
        self._setup_behavior()
        self._setup_notification_channels()
        self._validate()
        self._log_initialization()
    
    def _load_credentials(self):
        """Загрузка учетных данных"""
        self.bot_token = self._get_required_env('TELEGRAM_BOT_TOKEN')
        self.channel_id = self._get_required_env('TELEGRAM_CHANNEL_ID')
        self.admin_chat_id = os.getenv('ADMIN_CHAT_ID', self.channel_id)
    
    def _setup_limits(self):
        """Настройка лимитов Telegram API"""
        self.max_message_length = 4096
        self.max_caption_length = 1024
        self.max_photo_size_mb = 10
        self.max_file_size_mb = 50
        self.max_inline_buttons = 8
        self.max_callback_data_length = 64
    
    def _setup_behavior(self):
        """Настройка поведения бота"""
        self.retry_after_delay = 5
        self.rate_limit_delay = 1
        self.send_timeout = 30
        self.connect_timeout = 10
        self.read_timeout = 30
        self.write_timeout = 30
        self.pool_timeout = 10
        
        self.parse_mode = 'Markdown'
        self.disable_web_page_preview = False
        self.disable_notification = False
        self.allow_sending_without_reply = True
        self.protect_content = False
    
    def _setup_notification_channels(self):
        """Настройка каналов уведомлений"""
        self.notification_channels = {
            'whale_alerts': self.channel_id,
            'news': self.channel_id,
            'analytics': self.channel_id,
            'errors': self.admin_chat_id,
            'health': self.admin_chat_id,
            'trading': self.channel_id,
            'system': self.admin_chat_id,
            'warnings': self.admin_chat_id,
        }
    
    @staticmethod
    def _get_required_env(key: str) -> str:
        """
        Получение обязательной переменной окружения
        
        Args:
            key: Имя переменной
            
        Returns:
            Значение переменной
            
        Raises:
            ValueError: Если переменная не установлена
        """
        value = os.getenv(key)
        if not value:
            raise ValueError(f"❌ Missing required environment variable: {key}")
        return value
    
    def _validate(self):
        """Валидация конфигурации"""
        if not self.channel_id.startswith(('@', '-')):
            logger.warning(
                f"⚠️ [TELEGRAM] Channel ID '{self.channel_id}' "
                f"может быть некорректным (должен начинаться с @ или -)"
            )
        
        if len(self.bot_token) < 30:
            logger.warning("⚠️ [TELEGRAM] Bot token выглядит слишком коротким")
        
        if ':' not in self.bot_token:
            logger.warning("⚠️ [TELEGRAM] Bot token имеет неправильный формат")
    
    def _log_initialization(self):
        """Логирование успешной инициализации"""
        logger.info(f"✅ [TELEGRAM] Канал: {self.channel_id}")
        logger.info(f"✅ [TELEGRAM] Админ: {self.admin_chat_id}")
    
    def get_channel_for_type(self, notification_type: str) -> str:
        """
        Получение канала для типа уведомления
        
        Args:
            notification_type: Тип уведомления
            
        Returns:
            ID канала
        """
        return self.notification_channels.get(
            notification_type,
            self.channel_id
        )
    
    def should_notify_admin(self, notification_type: str) -> bool:
        """
        Проверка необходимости уведомления админа
        
        Args:
            notification_type: Тип уведомления
            
        Returns:
            True если нужно уведомить админа
        """
        admin_types = {'errors', 'health', 'critical', 'system', 'warnings'}
        return notification_type in admin_types
    
    def format_message(self, text: str, max_length: int = None) -> str:
        """
        Форматирование сообщения с учетом ограничений
        
        Args:
            text: Текст сообщения
            max_length: Максимальная длина (по умолчанию max_message_length)
            
        Returns:
            Отформатированный текст
        """
        limit = max_length or self.max_message_length
        
        if len(text) <= limit:
            return text
        
        return text[:limit-3] + '...'
    
    def split_long_message(self, text: str, max_length: int = None) -> list:
        """
        Разбиение длинного сообщения на части
        
        Args:
            text: Текст сообщения
            max_length: Максимальная длина части
            
        Returns:
            Список частей сообщения
        """
        limit = max_length or self.max_message_length
        
        if len(text) <= limit:
            return [text]
        
        parts = []
        current_part = ""
        
        for line in text.split('\n'):
            if len(current_part) + len(line) + 1 <= limit:
                current_part += line + '\n'
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = line + '\n'
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def validate_channel_id(self, channel_id: str) -> bool:
        """
        Валидация ID канала
        
        Args:
            channel_id: ID канала для проверки
            
        Returns:
            True если ID валиден
        """
        if not channel_id:
            return False
        
        return channel_id.startswith(('@', '-'))
    
    def get_timeout_config(self) -> Dict[str, int]:
        """
        Получение конфигурации таймаутов
        
        Returns:
            Словарь с настройками таймаутов
        """
        return {
            'connect_timeout': self.connect_timeout,
            'read_timeout': self.read_timeout,
            'write_timeout': self.write_timeout,
            'pool_timeout': self.pool_timeout,
        }
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'bot_token': '***' if self.bot_token else None,
            'channel_id': self.channel_id,
            'admin_chat_id': self.admin_chat_id,
            'max_message_length': self.max_message_length,
            'max_caption_length': self.max_caption_length,
            'notification_channels': self.notification_channels,
            'timeouts': self.get_timeout_config(),
        }