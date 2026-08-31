# core/health_server.py
"""
Health Check Server Module
===========================

HTTP endpoint для health checks и мониторинга сервиса.

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
from typing import Dict, Any, Optional
from aiohttp import web

logger = logging.getLogger(__name__)


class HealthServer:
    """
    HTTP сервер для health checks
    
    Предоставляет HTTP endpoints для проверки здоровья сервиса.
    Используется Render.com для мониторинга состояния приложения.
    
    Responsibilities:
    -----------------
    - Обработка health check запросов
    - Предоставление статуса системы
    - Graceful shutdown
    - Совместимость с Render.com
    
    Attributes:
        port: Порт сервера
        host: Хост для привязки
        app: aiohttp application
        runner: aiohttp runner
        site: aiohttp TCPSite
    """
    
    def __init__(
        self,
        port: int = 8080,
        host: str = '0.0.0.0',
        monitor: Optional[Any] = None,
        config: Optional[Any] = None
    ):
        """
        Инициализация health server
        
        Args:
            port: Порт сервера (по умолчанию 8080)
            host: Хост для привязки (по умолчанию 0.0.0.0)
            monitor: Монитор приложения (для расширенных health checks)
            config: Конфигурация приложения
        """
        self.port = int(port)
        self.host = host
        self.monitor = monitor
        self.config = config
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        logger.debug(f"HealthServer initialized on {host}:{port}")
    
    async def start(self, port: Optional[int] = None) -> None:
        """
        Запуск health server
        
        Создает и запускает aiohttp сервер с health check endpoints.
        
        Raises:
            Exception: При ошибках запуска сервера
        """
        try:
            if port is not None:
                self.port = int(port)

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
        Получение статуса здоровья системы
        
        Возвращает текущий статус приложения.
        В будущем можно добавить проверки:
        - Состояние базы данных
        - Статус фоновых задач
        - Доступность внешних сервисов
        
        Returns:
            Dict[str, Any]: Статус приложения с полями:
                - status: healthy/unhealthy
                - service: имя сервиса
                - version: версия приложения
        """
        return {
            'status': 'healthy',
            'service': 'crypto-compass',
            'version': '3.0.0'
        }


__all__ = ['HealthServer']