# app/config/telegram_config.py
"""
Telegram Configuration Module
Конфигурация Telegram бота и каналов
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TelegramConfig:
    """
    Конфигурация Telegram бота
    Настройки токена, каналов и ограничений API
    """
    
    def __init__(self):
        """Инициализация Telegram конфигурации"""
        
        self.bot_token = self._get_required_env('TELEGRAM_BOT_TOKEN')
        self.channel_id = self._get_required_env('TELEGRAM_CHANNEL_ID')
        self.admin_chat_id = os.getenv('ADMIN_CHAT_ID', self.channel_id)
        
        self.max_message_length = 4096
        self.max_caption_length = 1024
        self.max_photo_size_mb = 10
        
        self.retry_after_delay = 5
        self.rate_limit_delay = 1
        self.send_timeout = 30
        
        self.parse_mode = 'Markdown'
        self.disable_web_page_preview = False
        self.disable_notification = False
        
        self.notification_channels = {
            'whale_alerts': self.channel_id,
            'news': self.channel_id,
            'analytics': self.channel_id,
            'errors': self.admin_chat_id,
            'health': self.admin_chat_id,
            'trading': self.channel_id
        }
        
        self._validate()
        
        logger.info(f"✅ [TELEGRAM] Канал: {self.channel_id}")
        logger.info(f"✅ [TELEGRAM] Админ: {self.admin_chat_id}")
    
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
        """Проверка необходимости уведомления админа"""
        admin_types = {'errors', 'health', 'critical'}
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
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'bot_token': '***' if self.bot_token else None,
            'channel_id': self.channel_id,
            'admin_chat_id': self.admin_chat_id,
            'max_message_length': self.max_message_length,
            'notification_channels': self.notification_channels
        }