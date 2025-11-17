"""
Application validators v5.3
Валидаторы для проверки готовности приложения к запуску

ИСПРАВЛЕНО v5.3:
- Поддержка Monitor v5.3 архитектуры (business layer)
- Проверка monitor.business.component_manager вместо monitor.component_manager
- Исправлено имя атрибута: bot_application вместо bot_app
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class ApplicationValidator:
    """
    Валидатор готовности приложения
    
    Проверяет все необходимые зависимости и конфигурации
    перед запуском приложения
    """
    
    def __init__(self, config: Any, monitor: Any, db_manager: Any):
        """
        Инициализация валидатора
        
        Args:
            config: Конфигурация приложения
            monitor: Монитор системы
            db_manager: Менеджер базы данных
        """
        self.config = config
        self.monitor = monitor
        self.db_manager = db_manager
    
    def validate_all(self) -> Tuple[bool, List[str]]:
        """
        Полная валидация приложения
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []
        
        # Проверка конфигурации
        config_valid, config_errors = self._validate_config()
        if not config_valid:
            errors.extend(config_errors)
        
        # Проверка монитора
        monitor_valid, monitor_errors = self._validate_monitor()
        if not monitor_valid:
            errors.extend(monitor_errors)
        
        # Проверка базы данных
        db_valid, db_errors = self._validate_database()
        if not db_valid:
            errors.extend(db_errors)
        
        # Проверка компонентов
        components_valid, components_errors = self._validate_components()
        if not components_valid:
            errors.extend(components_errors)
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("✅ All application validations passed")
        else:
            logger.error(f"❌ Application validation failed: {len(errors)} errors")
            for error in errors:
                logger.error(f"   - {error}")
        
        return is_valid, errors
    
    def _validate_config(self) -> Tuple[bool, List[str]]:
        """Валидация конфигурации"""
        errors = []
        
        if not self.config:
            errors.append("Configuration not initialized")
            return False, errors
        
        # Проверка обязательных атрибутов
        required_attrs = ['features', 'telegram', 'paths', 'database']
        for attr in required_attrs:
            if not hasattr(self.config, attr):
                errors.append(f"Missing required config attribute: {attr}")
        
        # Проверка features
        if hasattr(self.config, 'features'):
            if not hasattr(self.config.features, 'is_enabled'):
                errors.append("FeaturesConfig missing is_enabled() method")
            
            if not self.config.features.is_any_feature_enabled():
                errors.append("No features enabled")
        
        return len(errors) == 0, errors
    
    def _validate_monitor(self) -> Tuple[bool, List[str]]:
        """
        Валидация монитора v5.3

        ИСПРАВЛЕНО v5.3:
        - Проверка monitor.business.component_manager вместо monitor.component_manager
        - Поддержка архитектуры Monitor v5.3 (business layer)
        """
        errors = []

        if not self.monitor:
            errors.append("Monitor not initialized")
            return False, errors

        # Проверка business layer (Monitor v5.3)
        if not hasattr(self.monitor, 'business'):
            errors.append("Monitor missing business layer")
            return False, errors

        # Проверка component_manager в business layer
        if not hasattr(self.monitor.business, 'component_manager'):
            errors.append("Monitor business layer missing component_manager")

        return len(errors) == 0, errors
    
    def _validate_database(self) -> Tuple[bool, List[str]]:
        """Валидация базы данных"""
        errors = []
        
        if not self.db_manager:
            errors.append("Database manager not initialized")
            return False, errors
        
        # Проверка методов
        required_methods = ['initialize', 'shutdown']
        for method in required_methods:
            if not hasattr(self.db_manager, method):
                errors.append(f"DatabaseManager missing method: {method}")
        
        return len(errors) == 0, errors
    
    def _validate_components(self) -> Tuple[bool, List[str]]:
        """
        Валидация загруженных компонентов v5.3

        ИСПРАВЛЕНО v5.3:
        - Доступ через monitor.business.component_manager (не напрямую)
        - Проверка business layer перед доступом к component_manager
        """
        errors = []

        # Проверка наличия business layer
        if not hasattr(self.monitor, 'business') or not self.monitor.business:
            errors.append("Monitor business layer not available")
            return False, errors

        # Проверка наличия component_manager
        if not hasattr(self.monitor.business, 'component_manager'):
            errors.append("Component manager not available in business layer")
            return False, errors

        component_manager = self.monitor.business.component_manager

        # Проверка что component_manager инициализирован
        if not component_manager:
            errors.append("Component manager is None")
            return False, errors

        # Проверка что хотя бы один компонент загружен
        loaded_count = sum([
            component_manager.news_processor is not None,
            component_manager.whale_scheduler is not None,
            component_manager.bot_application is not None,  # ИСПРАВЛЕНО: bot_application, не bot_app
            component_manager.trading_system is not None
        ])

        if loaded_count == 0:
            errors.append("No components loaded successfully")

        return len(errors) == 0, errors
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Получение информации о системе
        
        Returns:
            Dict: Информация о состоянии системы
        """
        return {
            'config_valid': self._validate_config()[0],
            'monitor_valid': self._validate_monitor()[0],
            'database_valid': self._validate_database()[0],
            'components_valid': self._validate_components()[0],
            'enabled_features': self.config.features.get_enabled_features() if self.config else {}
        }


__all__ = ['ApplicationValidator']