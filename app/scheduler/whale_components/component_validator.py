# app/scheduler/whale_components/component_validator.py
"""
Component Validator
Валидация наличия и корректности всех необходимых компонентов
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ComponentValidator:
    """Валидатор компонентов системы мониторинга"""
    
    REQUIRED_COMPONENTS = [
        'scorer',
        'price_provider',
        'publisher',
        'history_manager'
    ]
    
    OPTIONAL_COMPONENTS = [
        'news_gate',
        'chart_renderer',
        'adaptive_thresholds',
        'discovery',
        'rate_limiter',
        'seen_keys',
        'pending_verification'
    ]
    
    def __init__(self, components: Dict):
        """
        Args:
            components: Словарь компонентов для валидации
        """
        self.components = components
        self.missing_components = []
        self.available_components = []
    
    def validate_required_components(self) -> bool:
        """
        Проверка наличия обязательных компонентов
        
        Returns:
            True если все компоненты на месте
            
        Raises:
            RuntimeError: Если отсутствуют критические компоненты
        """
        self.missing_components = []
        self.available_components = []
        
        for component_name in self.REQUIRED_COMPONENTS:
            component = self.components.get(component_name)
            
            if component is None:
                self.missing_components.append(component_name)
                logger.error(f"❌ [VALIDATOR] Отсутствует обязательный компонент: {component_name}")
            else:
                self.available_components.append(component_name)
                logger.debug(f"✅ [VALIDATOR] Компонент найден: {component_name}")
        
        # Проверка опциональных компонентов
        for component_name in self.OPTIONAL_COMPONENTS:
            component = self.components.get(component_name)
            
            if component is None:
                logger.warning(f"⚠️ [VALIDATOR] Опциональный компонент отсутствует: {component_name}")
            else:
                self.available_components.append(component_name)
                logger.debug(f"✅ [VALIDATOR] Опциональный компонент найден: {component_name}")
        
        if self.missing_components:
            error_msg = f"Отсутствуют критические компоненты: {', '.join(self.missing_components)}"
            logger.error(f"❌ [VALIDATOR] {error_msg}")
            raise RuntimeError(error_msg)
        
        logger.info(f"✅ [VALIDATOR] Все обязательные компоненты на месте ({len(self.available_components)} всего)")
        return True
    
    def get_validation_report(self) -> Dict:
        """
        Получение отчёта о валидации
        
        Returns:
            Dict с детальной информацией о компонентах
        """
        return {
            'all_required_present': len(self.missing_components) == 0,
            'available_components': self.available_components,
            'missing_components': self.missing_components,
            'total_components': len(self.components)
        }