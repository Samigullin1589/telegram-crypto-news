# core/components/status.py
"""
Component Status Management
Управление статусом компонентов
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ComponentInfo:
    """Информация о компоненте"""
    name: str
    enabled: bool
    instance: Optional[Any] = None
    loaded_at: Optional[datetime] = None
    error: Optional[str] = None
    
    @property
    def is_available(self) -> bool:
        """Проверка доступности компонента"""
        return self.enabled and self.instance is not None
    
    @property
    def status_emoji(self) -> str:
        """Emoji статуса компонента"""
        return "✅" if self.is_available else "❌"
    
    @property
    def status_text(self) -> str:
        """Текстовый статус компонента"""
        if self.is_available:
            return "Активен"
        elif self.error:
            return f"Ошибка: {self.error}"
        elif not self.enabled:
            return "Отключен"
        else:
            return "Недоступен"


class ComponentStatusManager:
    """Управление статусом компонентов"""
    
    def __init__(self):
        """Инициализация менеджера статусов"""
        self._components: Dict[str, ComponentInfo] = {
            'news_processor': ComponentInfo('news_processor', False),
            'whale_scheduler': ComponentInfo('whale_scheduler', False),
            'bot_application': ComponentInfo('bot_application', False),
            'trading_system': ComponentInfo('trading_system', False),
            'hyperliquid_system': ComponentInfo('hyperliquid_system', False)
        }
        self._display_names = {
            'news_processor': 'News Bot',
            'whale_scheduler': 'Whale Monitor',
            'bot_application': 'Bot Commands',
            'trading_system': 'Trading System',
            'hyperliquid_system': 'Hyperliquid DEX'
        }
    
    def update(
        self,
        name: str,
        enabled: bool = False,
        instance: Optional[Any] = None,
        error: Optional[str] = None
    ) -> None:
        """Обновление информации о компоненте"""
        if name in self._components:
            self._components[name] = ComponentInfo(
                name=name,
                enabled=enabled,
                instance=instance,
                loaded_at=datetime.now() if instance else None,
                error=error
            )
    
    def get(self, name: str) -> Optional[ComponentInfo]:
        """Получение информации о компоненте"""
        return self._components.get(name)
    
    def is_available(self, name: str) -> bool:
        """Проверка доступности компонента"""
        component = self.get(name)
        return component.is_available if component else False
    
    def active_count(self) -> int:
        """Количество активных компонентов"""
        return sum(1 for comp in self._components.values() if comp.is_available)
    
    def has_any_active(self) -> bool:
        """Есть ли хотя бы один активный компонент"""
        return self.active_count() > 0
    
    def print_status(self) -> None:
        """Вывод статуса всех компонентов"""
        logger.info("\n" + "="*80)
        logger.info("📊 COMPONENT STATUS SUMMARY")
        logger.info("="*80)
        
        for name, component in self._components.items():
            display_name = self._display_names.get(name, name)
            logger.info(
                f"   {display_name:20} {component.status_emoji} {component.status_text}"
            )
        
        active = self.active_count()
        total = len(self._components)
        logger.info(f"\n   Активно компонентов: {active}/{total}")
        
        if not self.has_any_active():
            logger.warning("   ⚠️  Нет активных компонентов!")
        
        logger.info("="*80 + "\n")
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для API"""
        return {
            name: {
                'enabled': comp.enabled,
                'available': comp.is_available,
                'status': comp.status_text,
                'loaded_at': comp.loaded_at.isoformat() if comp.loaded_at else None,
                'error': comp.error
            }
            for name, comp in self._components.items()
        }