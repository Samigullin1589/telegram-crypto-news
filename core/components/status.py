# core/components/status.py
"""
Component Status Management
Управление статусом компонентов
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
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


class ComponentStatus:
    """
    Управление статусом всех компонентов системы
    
    Отслеживает:
    - Какие компоненты загружены
    - Статус каждого компонента
    - Время загрузки
    - Ошибки загрузки
    """
    
    def __init__(self):
        """Инициализация менеджера статусов"""
        self._components: Dict[str, ComponentInfo] = {}
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Инициализация списка компонентов"""
        component_names = [
            'news_processor',
            'whale_scheduler',
            'bot_application',
            'trading_system'
        ]
        
        for name in component_names:
            self._components[name] = ComponentInfo(
                name=name,
                enabled=False,
                instance=None,
                loaded_at=None,
                error=None
            )
    
    def update_component(
        self,
        name: str,
        enabled: bool = False,
        instance: Optional[Any] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Обновление информации о компоненте
        
        Args:
            name: Название компонента
            enabled: Включен ли компонент
            instance: Экземпляр компонента
            error: Текст ошибки (если есть)
        """
        if name not in self._components:
            logger.warning(f"Unknown component: {name}")
            return
        
        self._components[name] = ComponentInfo(
            name=name,
            enabled=enabled,
            instance=instance,
            loaded_at=datetime.now() if instance else None,
            error=error
        )
    
    def get_component(self, name: str) -> Optional[ComponentInfo]:
        """
        Получение информации о компоненте
        
        Args:
            name: Название компонента
            
        Returns:
            ComponentInfo или None
        """
        return self._components.get(name)
    
    def is_component_available(self, name: str) -> bool:
        """
        Проверка доступности компонента
        
        Args:
            name: Название компонента
            
        Returns:
            True если компонент доступен
        """
        component = self.get_component(name)
        return component.is_available if component else False
    
    def get_active_components_count(self) -> int:
        """
        Получение количества активных компонентов
        
        Returns:
            Количество активных компонентов
        """
        return sum(
            1 for comp in self._components.values()
            if comp.is_available
        )
    
    def is_any_component_active(self) -> bool:
        """
        Проверка наличия хотя бы одного активного компонента
        
        Returns:
            True если есть хотя бы один активный компонент
        """
        return self.get_active_components_count() > 0
    
    def get_all_components(self) -> Dict[str, ComponentInfo]:
        """
        Получение информации о всех компонентах
        
        Returns:
            Словарь с информацией о компонентах
        """
        return self._components.copy()
    
    def get_status_dict(self) -> Dict[str, Any]:
        """
        Получение статуса в виде словаря для API
        
        Returns:
            Словарь со статусом всех компонентов
        """
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
    
    def print_status(self) -> None:
        """Вывод статуса всех компонентов в лог"""
        logger.info("\n" + "="*80)
        logger.info("📊 COMPONENT STATUS SUMMARY")
        logger.info("="*80)
        
        # Форматированные названия для вывода
        display_names = {
            'news_processor': 'News Bot',
            'whale_scheduler': 'Whale Monitor',
            'bot_application': 'Bot Commands',
            'trading_system': 'Trading System'
        }
        
        for name, component in self._components.items():
            display_name = display_names.get(name, name)
            logger.info(
                f"   {display_name:20} {component.status_emoji} {component.status_text}"
            )
        
        # Общая статистика
        active_count = self.get_active_components_count()
        total_count = len(self._components)
        
        logger.info(f"\n   Активно компонентов: {active_count}/{total_count}")
        
        if not self.is_any_component_active():
            logger.warning("   ⚠️  Нет активных компонентов!")
        
        logger.info("="*80 + "\n")