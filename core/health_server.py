# core/health_server.py
"""
Health Check Server Module v5.3
================================

HTTP endpoint для health checks и мониторинга сервиса.

ИСПРАВЛЕНО v5.3:
- Совместимость с Application v5.1
- Принимает monitor и config параметры
- Расширенный статус с информацией о компонентах

Components:
-----------
- HealthServer: HTTP сервер для health checks

Architecture:
-------------
Обеспечивает:
- HTTP endpoints для проверки здоровья сервиса
- Интеграция с Render.com health checks
- Статус различных компонентов системы
- Graceful shutdown

Production Ready:
-----------------
- Полная обработка ошибок
- Корректная остановка сервера
- Метрики и мониторинг
- Совместимость с Render.com
"""

import asyncio
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from aiohttp import web

if TYPE_CHECKING:
    from core.monitor import IntegratedCryptoMonitor

logger = logging.getLogger(__name__)


class HealthServer:
    """
    HTTP сервер для health checks v5.3

    ИСПРАВЛЕНО v5.3:
    - Принимает monitor и config для расширенного статуса
    - Извлекает порт из конфигурации
    - Отображает статус компонентов Monitor

    Предоставляет HTTP endpoints для проверки здоровья сервиса.
    Используется Render.com для мониторинга состояния приложения.

    Responsibilities:
    -----------------
    - Обработка health check запросов
    - Предоставление статуса системы
    - Graceful shutdown
    - Совместимость с Render.com

    Attributes:
        monitor: IntegratedCryptoMonitor (опционально)
        config: Конфигурация приложения (опционально)
        port: Порт сервера
        host: Хост для привязки
        app: aiohttp application
        runner: aiohttp runner
        site: aiohttp TCPSite
    """

    def __init__(
        self,
        monitor: Optional['IntegratedCryptoMonitor'] = None,
        config: Optional[Any] = None,
        port: Optional[int] = None,
        host: str = '0.0.0.0'
    ):
        """
        Инициализация health server v5.3

        ИСПРАВЛЕНО v5.3:
        - Принимает monitor и config от Application
        - Автоматическое извлечение порта из config.base.PORT
        - Обратная совместимость через опциональные параметры

        Args:
            monitor: Монитор для отображения статуса компонентов (опционально)
            config: Конфигурация приложения (опционально)
            port: Порт сервера (если None, берется из config или 8080)
            host: Хост для привязки (по умолчанию 0.0.0.0)
        """
        self.monitor = monitor
        self.config = config

        # Определение порта
        if port is not None:
            self.port = port
        elif config and hasattr(config, 'base') and hasattr(config.base, 'PORT'):
            self.port = config.base.PORT
        else:
            self.port = 8080

        self.host = host
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

        logger.debug(
            f"HealthServer v5.3 initialized on {host}:{self.port} "
            f"(monitor={'available' if monitor else 'none'})"
        )
    
    async def start(self) -> None:
        """
        Запуск health server
        
        Создает и запускает aiohttp сервер с health check endpoints.
        
        Raises:
            Exception: При ошибках запуска сервера
        """
        try:
            logger.info("🏥 [HEALTH] Starting Health Check Server...")
            
            # Создание application
            self.app = web.Application()
            
            # Регистрация routes
            self._register_routes()
            
            # Запуск runner
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            # Создание TCP site
            self.site = web.TCPSite(
                self.runner,
                self.host,
                self.port
            )
            await self.site.start()
            
            logger.info(f"✅ [HEALTH] Health server listening on {self.host}:{self.port}")
        
        except Exception as e:
            logger.error(f"❌ [HEALTH] Cannot start health server: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """
        Остановка health server
        
        Выполняет graceful shutdown aiohttp сервера.
        
        Raises:
            Exception: При ошибках остановки сервера
        """
        try:
            logger.info("🛑 [HEALTH] Stopping Health Check Server...")
            
            if self.runner:
                await self.runner.cleanup()
            
            logger.info("✅ [HEALTH] Health server stopped")
        
        except Exception as e:
            logger.error(f"❌ [HEALTH] Error stopping health server: {e}", exc_info=True)
    
    def _register_routes(self):
        """
        Регистрация HTTP routes
        
        Регистрирует endpoints для health checks:
        - / - корневой endpoint
        - /health - стандартный health check
        - /healthz - Kubernetes-style health check
        """
        self.app.router.add_get('/', self._health_handler)
        self.app.router.add_get('/health', self._health_handler)
        self.app.router.add_get('/healthz', self._health_handler)
        
        logger.debug("[HEALTH] Routes registered: /, /health, /healthz")
    
    async def _health_handler(self, request: web.Request) -> web.Response:
        """
        Health check endpoint handler
        
        Обрабатывает запросы health checks и возвращает статус системы.
        
        Args:
            request: HTTP request
        
        Returns:
            web.Response: JSON ответ со статусом системы
        """
        try:
            # Получение статуса здоровья
            health_status = self._get_health_status()
            
            # Определение HTTP status code
            http_status = 200 if health_status['status'] == 'healthy' else 503
            
            return web.json_response(
                health_status,
                status=http_status
            )
        
        except Exception as e:
            logger.error(f"❌ [HEALTH] Error in health handler: {e}", exc_info=True)
            
            return web.json_response(
                {
                    'status': 'error',
                    'error': str(e)
                },
                status=500
            )
    
    def _get_health_status(self) -> Dict[str, Any]:
        """
        Получение статуса здоровья системы v5.3

        ИСПРАВЛЕНО v5.3:
        - Интеграция с Monitor для детального статуса
        - Отображение количества активных компонентов
        - Проверка инициализации Monitor

        Возвращает текущий статус приложения включая:
        - Состояние Monitor
        - Количество активных компонентов
        - Статус инициализации

        Returns:
            Dict[str, Any]: Статус приложения с полями:
                - status: healthy/degraded/unhealthy
                - service: имя сервиса
                - version: версия приложения
                - monitor: статус мониторинга (если доступен)
                - components_active: количество активных компонентов
        """
        status_response = {
            'status': 'healthy',
            'service': 'crypto-compass',
            'version': '5.3.0'
        }

        # Расширенная информация если доступен Monitor
        if self.monitor:
            try:
                # Проверка инициализации Monitor
                is_initialized = getattr(self.monitor, '_fully_initialized', False)
                status_response['monitor_initialized'] = is_initialized

                # Статус компонентов
                if hasattr(self.monitor, 'business') and self.monitor.business:
                    business = self.monitor.business
                    if hasattr(business, 'component_manager'):
                        cm = business.component_manager
                        if cm:
                            active_count = cm.get_active_components_count()
                            status_response['components_active'] = active_count
                            status_response['components_status'] = cm.get_status_dict()

                            # Определение общего статуса
                            if not is_initialized:
                                status_response['status'] = 'unhealthy'
                            elif active_count == 0:
                                status_response['status'] = 'unhealthy'
                            elif active_count < 4:
                                status_response['status'] = 'degraded'
                            else:
                                status_response['status'] = 'healthy'

            except Exception as e:
                logger.debug(f"Could not get detailed monitor status: {e}")
                status_response['status'] = 'degraded'
                status_response['monitor_error'] = str(e)

        return status_response


__all__ = ['HealthServer']