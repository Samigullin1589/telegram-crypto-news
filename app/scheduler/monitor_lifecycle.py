# app/scheduler/monitor_lifecycle.py
"""
Whale Monitor Lifecycle Management
Управление жизненным циклом монитора
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MonitorLifecycle:
    """
    Управление жизненным циклом монитора
    
    Отвечает за:
    - Валидацию компонентов
    - Инициализацию подсистем
    - Cleanup при завершении
    """
    
    def __init__(self, components: Dict[str, Any]):
        """
        Инициализация lifecycle
        
        Args:
            components: Словарь с компонентами системы
        """
        self.components = components
        self.is_valid = False
        
        # Валидация компонентов
        self._validate_components()
        
        # Инициализация подсистем
        if self.is_valid:
            self._initialize_subsystems()
    
    def _validate_components(self):
        """Валидация необходимых компонентов"""
        try:
            from .whale_components import ComponentValidator
            
            validator = ComponentValidator(self.components)
            self.is_valid = validator.validate_required_components()
            
            if self.is_valid:
                logger.debug("✅ [LIFECYCLE] Components validated")
            else:
                logger.warning("⚠️  [LIFECYCLE] Some components missing")
        
        except ImportError:
            logger.warning("⚠️  [LIFECYCLE] ComponentValidator not available")
            # Продолжаем без валидации
            self.is_valid = True
        
        except Exception as e:
            logger.error(f"❌ [LIFECYCLE] Validation error: {e}")
            self.is_valid = False
    
    def _initialize_subsystems(self):
        """Инициализация подсистем"""
        try:
            # Здесь можно добавить инициализацию дополнительных подсистем
            logger.debug("🔧 [LIFECYCLE] Subsystems initialized")
        
        except Exception as e:
            logger.error(f"❌ [LIFECYCLE] Subsystem init error: {e}")
    
    def get_components_status(self) -> Dict[str, bool]:
        """
        Получение статуса компонентов
        
        Returns:
            Dict с доступностью компонентов
        """
        return {
            'event_filter': 'event_filter' in self.components,
            'event_enricher': 'event_enricher' in self.components,
            'scorer': 'scorer' in self.components,
            'rate_limiter': 'rate_limiter' in self.components,
            'telegram_bot': 'telegram_bot' in self.components
        }
    
    async def cleanup(self):
        """Cleanup компонентов"""
        logger.debug("🧹 [LIFECYCLE] Cleaning up components...")
        
        # Cleanup отдельных компонентов если нужно
        for name, component in self.components.items():
            if hasattr(component, 'cleanup'):
                try:
                    await component.cleanup()
                    logger.debug(f"   ✓ {name} cleaned up")
                except Exception as e:
                    logger.debug(f"   ⚠️  {name} cleanup error: {e}")


__all__ = ['MonitorLifecycle']