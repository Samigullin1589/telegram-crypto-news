# core/health_server.py
"""
Health Check Server - HTTP endpoint для Render
Обеспечивает healthcheck для мониторинга Render.com
"""

import asyncio
from aiohttp import web
from typing import Dict, Any
from core.logging_config import get_logger

logger = get_logger(__name__)


class HealthCheckServer:
    """
    Простой HTTP сервер для health checks
    
    Render.com требует HTTP endpoint для проверки здоровья
    """
    
    def __init__(self, port: int = 8080, host: str = '0.0.0.0'):
        """
        Args:
            port: Порт сервера
            host: Хост для привязки
        """
        self.port = port
        self.host = host
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
    
    async def start(self) -> None:
        """Запуск сервера"""
        try:
            # Создаем приложение
            self.app = web.Application()
            self.app.router.add_get('/', self._health_handler)
            self.app.router.add_get('/health', self._health_handler)
            self.app.router.add_get('/healthz', self._health_handler)
            
            # Запускаем сервер
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(
                self.runner,
                self.host,
                self.port
            )
            await self.site.start()
            
            logger.info(f"✅ Health server listening on {self.host}:{self.port}")
        
        except Exception as e:
            logger.error(f"Cannot start health server: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Остановка сервера"""
        try:
            if self.runner:
                await self.runner.cleanup()
            logger.info("✅ Health server stopped")
        
        except Exception as e:
            logger.error(f"Error stopping health server: {e}", exc_info=True)
    
    async def _health_handler(self, request: web.Request) -> web.Response:
        """
        Health check endpoint
        
        Args:
            request: HTTP request
        
        Returns:
            web.Response: JSON ответ со статусом
        """
        health_status = self._get_health_status()
        
        return web.json_response(
            health_status,
            status=200 if health_status['status'] == 'healthy' else 503
        )
    
    def _get_health_status(self) -> Dict[str, Any]:
        """
        Получение статуса здоровья
        
        Returns:
            Dict[str, Any]: Статус приложения
        """
        # Базовый health check
        # Можно расширить проверками БД, задач и т.д.
        return {
            'status': 'healthy',
            'service': 'crypto-monitor',
            'version': '4.5'
        }