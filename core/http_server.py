"""
HTTP Server - Production Grade

HTTP сервер для:
- Health check endpoints (для Render.com и мониторинга)
- Telegram webhook обработки
- Статистика и метрики
- Graceful shutdown
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Any
import traceback as tb

from aiohttp import web

logger = logging.getLogger(__name__)


class HTTPServer:
    """
    Production-ready HTTP сервер для health checks и webhooks
    
    Features:
    - Health check endpoint (GET / или /health)
    - Telegram webhook endpoint (POST /webhook/telegram)
    - Metrics endpoint (GET /metrics)
    - Graceful startup and shutdown
    - Error handling and logging
    """
    
    def __init__(
        self,
        health_monitor: Any,
        resource_monitor: Any,
        rate_limiter: Any,
        bot_application: Optional[Any] = None,
        port: Optional[int] = None
    ):
        """
        Инициализация HTTP сервера
        
        Args:
            health_monitor: SystemHealthMonitor instance
            resource_monitor: ResourceMonitor instance
            rate_limiter: ChainRateLimiter instance
            bot_application: Telegram bot application (optional)
            port: HTTP port. The monitor passes METRICS_PORT explicitly;
                standalone use falls back to PORT or 8000.
        """
        self.health_monitor = health_monitor
        self.resource_monitor = resource_monitor
        self.rate_limiter = rate_limiter
        self.bot_application = bot_application
        
        self.port = port or int(os.environ.get('PORT', 8000))
        
        # Server components
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        
        # Request tracking
        self.total_requests = 0
        self.health_requests = 0
        self.webhook_requests = 0
        self.metrics_requests = 0
        self.error_requests = 0
        
        logger.info("🌐 [HTTP] HTTP Server инициализирован")
        logger.info(f"   Port: {self.port}")
    
    async def start(self):
        """
        Запуск HTTP сервера
        
        Правильная последовательность:
        1. Создание Application
        2. Регистрация routes
        3. Создание AppRunner
        4. Setup runner
        5. Создание TCPSite
        6. Start site
        """
        try:
            logger.info("🌐 [HTTP] Инициализация health server...")
            
            # Create application
            self._app = web.Application()
            
            # Register routes
            self._app.router.add_get('/', self._health_handler)
            self._app.router.add_get('/health', self._health_handler)
            self._app.router.add_get('/metrics', self._metrics_handler)
            self._app.router.add_post('/webhook/telegram', self._webhook_handler)
            
            # Optional: Add status endpoint
            self._app.router.add_get('/status', self._status_handler)
            
            # Create and setup runner
            self._runner = web.AppRunner(self._app)
            await self._runner.setup()
            
            # Create and start site
            self._site = web.TCPSite(
                self._runner,
                '0.0.0.0',
                self.port
            )
            
            await self._site.start()
            
            logger.info(f"🌐 [HTTP] Health server запущен на порту {self.port}")
            logger.info("   Endpoints:")
            logger.info("   • GET  / или /health - Health check")
            logger.info("   • GET  /metrics - Metrics")
            logger.info("   • GET  /status - Detailed status")
            logger.info("   • POST /webhook/telegram - Telegram webhook")
            
        except OSError as e:
            logger.error(f"❌ [HTTP] Ошибка привязки к порту {self.port}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ [HTTP] Ошибка запуска сервера: {e}")
            tb.print_exc()
            raise
    
    async def stop(self):
        """
        Остановка HTTP сервера
        
        Правильная последовательность:
        1. Stop site
        2. Cleanup runner
        3. Shutdown application
        4. Cleanup application
        """
        try:
            logger.info("🌐 [HTTP] Останавливаем health server...")
            
            if self._site:
                await self._site.stop()
                logger.info("   ✓ Site остановлен")
                self._site = None
            
            if self._runner:
                await self._runner.cleanup()
                logger.info("   ✓ Runner очищен")
                self._runner = None
            
            if self._app:
                await self._app.shutdown()
                await self._app.cleanup()
                logger.info("   ✓ Application очищен")
                self._app = None
            
            logger.info("✅ [HTTP] Health server остановлен")
        
        except Exception as e:
            logger.warning(f"⚠️ [HTTP] Ошибка остановки сервера: {e}")
            tb.print_exc()
    
    async def _health_handler(self, request: web.Request) -> web.Response:
        """
        Health check endpoint handler
        
        Возвращает базовую информацию о состоянии системы
        """
        try:
            self.total_requests += 1
            self.health_requests += 1
            
            # Basic health status
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'crypto-compass-v4.5',
                'version': '4.5.0',
                'port': self.port,
            }
            
            # Add resource stats
            if self.resource_monitor:
                resource_stats = self.resource_monitor.get_stats()
                health_status['resources'] = {
                    'memory_mb': resource_stats.get('memory_mb', 0),
                    'memory_percent': resource_stats.get('memory_percent_of_limit', 0),
                    'cpu_percent': resource_stats.get('cpu_percent', 0),
                }
            
            # Add rate limiter status
            if self.rate_limiter:
                rate_stats = self.rate_limiter.get_stats()
                health_status['rate_limiter'] = {
                    'active_chains': len([
                        c for c in rate_stats['chains'] 
                        if c not in rate_stats['disabled_chains']
                    ]),
                    'disabled_chains': list(rate_stats['disabled_chains'].keys()),
                }
            
            # Add uptime
            if self.health_monitor:
                health_stats = self.health_monitor.get_stats()
                health_status['uptime'] = health_stats['uptime_formatted']
                health_status['total_cycles'] = health_stats['total_cycles']
                health_status['total_errors'] = health_stats['total_errors']
            
            return web.json_response(health_status, status=200)
        
        except Exception as e:
            self.error_requests += 1
            logger.error(f"❌ [HTTP] Error in health handler: {e}")
            tb.print_exc()
            
            return web.json_response({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, status=500)
    
    async def _metrics_handler(self, request: web.Request) -> web.Response:
        """
        Metrics endpoint handler
        
        Возвращает детальную метрику системы
        """
        try:
            self.total_requests += 1
            self.metrics_requests += 1
            
            metrics = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'crypto-compass-v4.5',
                'version': '4.5.0',
            }
            
            # HTTP metrics
            metrics['http'] = {
                'total_requests': self.total_requests,
                'health_requests': self.health_requests,
                'webhook_requests': self.webhook_requests,
                'metrics_requests': self.metrics_requests,
                'error_requests': self.error_requests,
            }
            
            # Health monitor metrics
            if self.health_monitor:
                metrics['health'] = self.health_monitor.get_stats()
            
            # Resource metrics
            if self.resource_monitor:
                metrics['resources'] = self.resource_monitor.get_stats()
            
            # Rate limiter metrics
            if self.rate_limiter:
                metrics['rate_limiter'] = self.rate_limiter.get_stats()
            
            return web.json_response(metrics, status=200)
        
        except Exception as e:
            self.error_requests += 1
            logger.error(f"❌ [HTTP] Error in metrics handler: {e}")
            tb.print_exc()
            
            return web.json_response({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, status=500)
    
    async def _status_handler(self, request: web.Request) -> web.Response:
        """
        Detailed status endpoint handler
        
        Возвращает полную информацию о состоянии всех систем
        """
        try:
            self.total_requests += 1
            
            status = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'crypto-compass-v4.5',
                'version': '4.5.0',
            }
            
            # Check overall health
            if self.health_monitor:
                is_healthy, issues = self.health_monitor.check_health()
                status['is_healthy'] = is_healthy
                status['issues'] = issues
                status['systems'] = self.health_monitor.get_stats()['systems']
            
            # Resource status
            if self.resource_monitor:
                resource_stats = self.resource_monitor.get_stats()
                status['resources'] = resource_stats
                status['memory_critical'] = self.resource_monitor.is_memory_critical()
                status['memory_warning'] = self.resource_monitor.is_memory_warning()
            
            # Rate limiter status
            if self.rate_limiter:
                rate_stats = self.rate_limiter.get_stats()
                status['chains'] = {}
                for chain in rate_stats['chains'].keys():
                    status['chains'][chain] = self.rate_limiter.get_chain_stats(chain)
            
            # Bot status
            if self.bot_application:
                status['bot'] = {
                    'running': getattr(self.bot_application, 'running', False),
                    'initialized': True,
                }
            
            return web.json_response(status, status=200)
        
        except Exception as e:
            self.error_requests += 1
            logger.error(f"❌ [HTTP] Error in status handler: {e}")
            tb.print_exc()
            
            return web.json_response({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, status=500)
    
    async def _webhook_handler(self, request: web.Request) -> web.Response:
        """
        Telegram webhook endpoint handler
        
        Обрабатывает входящие обновления от Telegram
        """
        try:
            self.total_requests += 1
            self.webhook_requests += 1
            
            # Check if bot is available
            if not self.bot_application:
                logger.error("❌ [WEBHOOK] Bot not initialized")
                return web.json_response({
                    'ok': False,
                    'error': 'Bot not initialized'
                }, status=503)
            
            # Parse update data
            try:
                update_data = await request.json()
            except json.JSONDecodeError as e:
                logger.error(f"❌ [WEBHOOK] Invalid JSON: {e}")
                self.error_requests += 1
                return web.json_response({
                    'ok': False,
                    'error': 'Invalid JSON'
                }, status=400)
            
            # Process update
            try:
                from telegram import Update
                update = Update.de_json(update_data, self.bot_application.bot)
                
                # Process update asynchronously
                await self.bot_application.process_update(update)
                
                logger.debug(f"[WEBHOOK] Update processed: {update.update_id}")
                
                return web.json_response({'ok': True}, status=200)
            
            except Exception as e:
                logger.error(f"❌ [WEBHOOK] Error processing update: {e}")
                tb.print_exc()
                self.error_requests += 1
                
                return web.json_response({
                    'ok': False,
                    'error': f'Processing error: {str(e)}'
                }, status=500)
        
        except Exception as e:
            self.error_requests += 1
            logger.error(f"❌ [WEBHOOK] Ошибка обработки webhook: {e}")
            tb.print_exc()
            
            return web.json_response({
                'ok': False,
                'error': str(e)
            }, status=500)
    
    def get_stats(self) -> dict:
        """
        Получить статистику HTTP сервера
        
        Returns:
            Dict со статистикой запросов
        """
        return {
            'total_requests': self.total_requests,
            'health_requests': self.health_requests,
            'webhook_requests': self.webhook_requests,
            'metrics_requests': self.metrics_requests,
            'error_requests': self.error_requests,
            'port': self.port,
            'is_running': self._site is not None,
        }
    
    def print_stats(self):
        """Вывести статистику в лог"""
        stats = self.get_stats()
        
        logger.info("\n🌐 [HTTP] Статистика сервера:")
        logger.info(f"   Port: {stats['port']}")
        logger.info(f"   Running: {stats['is_running']}")
        logger.info(f"   Total Requests: {stats['total_requests']}")
        logger.info(f"   ├─ Health: {stats['health_requests']}")
        logger.info(f"   ├─ Webhook: {stats['webhook_requests']}")
        logger.info(f"   ├─ Metrics: {stats['metrics_requests']}")
        logger.info(f"   └─ Errors: {stats['error_requests']}")
    
    def reset_stats(self):
        """Сброс статистики запросов"""
        self.total_requests = 0
        self.health_requests = 0
        self.webhook_requests = 0
        self.metrics_requests = 0
        self.error_requests = 0
        logger.info("[HTTP] Статистика сброшена")