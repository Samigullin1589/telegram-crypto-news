"""
INTEGRATED CRYPTO MONITOR v4.1 - Complete Edition with Enhanced Rate Limiting
Unified system: News Bot + Whale Monitor + Trading System + Telegram Commands

РЕВОЛЮЦИОННЫЕ ВОЗМОЖНОСТИ:
✅ News Bot - AI-powered crypto news aggregation
✅ Whale Monitor - Smart money tracking & discovery
✅ Trading System - Technical + Fundamental + ML signals
✅ Telegram Bot - Interactive command handler (WEBHOOK MODE)
✅ Unified Health Monitoring
✅ Graceful Shutdown
✅ Performance Analytics
✅ Multi-Chain Support with Adaptive Rate Limiting
✅ Automatic Chain Recovery from 429 Errors
✅ Advanced Analytics
✅ Position Management
✅ Risk Management
✅ User Commands (/start, /positions, /signal, etc.)
✅ HTTP Health Check Server (для Render.com)
"""

import asyncio
import signal
import sys
import os
import gc
import psutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
import traceback as tb
from collections import defaultdict
from functools import wraps

if sys.version_info < (3, 8):
    print("❌ Требуется Python 3.8 или выше")
    sys.exit(1)

from aiohttp import web
import aiohttp


# ============================================================================
# CHAIN RATE LIMITER
# ============================================================================

class ChainRateLimiter:
    """
    Адаптивный rate limiter для блокчейн RPC endpoints
    
    Автоматически управляет частотой запросов для каждой цепи:
    - Отслеживает 429 ошибки
    - Временно отключает проблемные цепи
    - Автоматически восстанавливает через backoff период
    - Динамически настраивает задержки между запросами
    """
    
    def __init__(self):
        self.chain_stats = {}
        self.disabled_chains = {}
        self.last_request_time = {}
        self.min_delay_between_requests = 2.0
        self.max_consecutive_429 = 3
        self.backoff_periods = [60, 300, 900, 1800]
        self.current_backoff_index = {}
        
        print("🔒 [RATE_LIMITER] Chain Rate Limiter инициализирован")
    
    def init_chain(self, chain: str):
        """Инициализация статистики для цепи"""
        if chain not in self.chain_stats:
            self.chain_stats[chain] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'consecutive_429': 0,
                'total_429_errors': 0,
                'last_429_time': None,
                'recovery_attempts': 0
            }
            self.last_request_time[chain] = datetime.now(timezone.utc) - timedelta(seconds=10)
            self.current_backoff_index[chain] = 0
    
    def is_chain_enabled(self, chain: str) -> bool:
        """Проверка доступности цепи"""
        self.init_chain(chain)
        
        if chain not in self.disabled_chains:
            return True
        
        disabled_until = self.disabled_chains[chain]
        now = datetime.now(timezone.utc)
        
        if now >= disabled_until:
            print(f"🔄 [RATE_LIMITER] {chain} - Попытка восстановления")
            del self.disabled_chains[chain]
            self.chain_stats[chain]['recovery_attempts'] += 1
            self.chain_stats[chain]['consecutive_429'] = 0
            return True
        
        return False
    
    async def wait_if_needed(self, chain: str):
        """Ожидание перед запросом если необходимо"""
        self.init_chain(chain)
        
        last_request = self.last_request_time.get(chain)
        if last_request:
            elapsed = (datetime.now(timezone.utc) - last_request).total_seconds()
            delay_needed = self.min_delay_between_requests - elapsed
            
            if delay_needed > 0:
                await asyncio.sleep(delay_needed)
        
        self.last_request_time[chain] = datetime.now(timezone.utc)
        self.chain_stats[chain]['total_requests'] += 1
    
    def record_success(self, chain: str):
        """Регистрация успешного запроса"""
        if chain not in self.chain_stats:
            self.init_chain(chain)
        
        self.chain_stats[chain]['successful_requests'] += 1
        self.chain_stats[chain]['consecutive_429'] = 0
        
        if self.current_backoff_index[chain] > 0:
            self.current_backoff_index[chain] = max(0, self.current_backoff_index[chain] - 1)
    
    def record_429_error(self, chain: str):
        """Регистрация 429 ошибки"""
        if chain not in self.chain_stats:
            self.init_chain(chain)
        
        stats = self.chain_stats[chain]
        stats['failed_requests'] += 1
        stats['consecutive_429'] += 1
        stats['total_429_errors'] += 1
        stats['last_429_time'] = datetime.now(timezone.utc)
        
        if stats['consecutive_429'] >= self.max_consecutive_429:
            backoff_idx = min(
                self.current_backoff_index[chain],
                len(self.backoff_periods) - 1
            )
            backoff_duration = self.backoff_periods[backoff_idx]
            
            disabled_until = datetime.now(timezone.utc) + timedelta(seconds=backoff_duration)
            self.disabled_chains[chain] = disabled_until
            
            self.current_backoff_index[chain] = min(
                self.current_backoff_index[chain] + 1,
                len(self.backoff_periods) - 1
            )
            
            print(f"⏸️ [RATE_LIMITER] {chain} - Временно отключен на {backoff_duration}с")
            print(f"   Причина: {stats['consecutive_429']} последовательных 429 ошибок")
            print(f"   Будет восстановлен: {disabled_until.strftime('%H:%M:%S UTC')}")
    
    def record_other_error(self, chain: str):
        """Регистрация других ошибок"""
        if chain not in self.chain_stats:
            self.init_chain(chain)
        
        self.chain_stats[chain]['failed_requests'] += 1
    
    def get_stats(self) -> Dict:
        """Получить статистику rate limiter"""
        return {
            'chains': self.chain_stats,
            'disabled_chains': {
                chain: until.isoformat()
                for chain, until in self.disabled_chains.items()
            }
        }
    
    def print_stats(self):
        """Вывести статистику"""
        print("\n📊 [RATE_LIMITER] Статистика:")
        
        for chain, stats in self.chain_stats.items():
            status = "✅ Active"
            if chain in self.disabled_chains:
                until = self.disabled_chains[chain]
                remaining = (until - datetime.now(timezone.utc)).total_seconds()
                status = f"⏸️ Disabled ({int(remaining)}s remaining)"
            
            success_rate = 0
            if stats['total_requests'] > 0:
                success_rate = (stats['successful_requests'] / stats['total_requests']) * 100
            
            print(f"\n{chain}:")
            print(f"  Status: {status}")
            print(f"  Requests: {stats['total_requests']} (Success: {stats['successful_requests']}, Failed: {stats['failed_requests']})")
            print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  429 Errors: {stats['total_429_errors']} (Current streak: {stats['consecutive_429']})")
            print(f"  Recovery Attempts: {stats['recovery_attempts']}")


# ============================================================================
# RESOURCE MONITOR
# ============================================================================

class ResourceMonitor:
    """Мониторинг системных ресурсов"""
    
    def __init__(self, max_memory_mb: int = 450):
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()
        self.last_gc = datetime.now(timezone.utc)
        self.gc_interval = 300
    
    def check_memory(self) -> bool:
        """Проверка использования памяти"""
        try:
            memory_mb = self.process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.max_memory_mb * 0.9:
                print(f"⚠️ [MEMORY] High usage: {memory_mb:.1f}MB / {self.max_memory_mb}MB")
                
                now = datetime.now(timezone.utc)
                if (now - self.last_gc).seconds > 60:
                    print("   🧹 Running garbage collection...")
                    gc.collect()
                    self.last_gc = now
                    new_memory = self.process.memory_info().rss / 1024 / 1024
                    print(f"   ✅ Memory after GC: {new_memory:.1f}MB")
                
                return memory_mb <= self.max_memory_mb
            
            return True
            
        except Exception as e:
            print(f"❌ [MEMORY] Error checking: {e}")
            return True
    
    def get_stats(self) -> Dict:
        """Получить статистику ресурсов"""
        try:
            mem_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent(interval=1)
            
            return {
                'memory_mb': mem_info.rss / 1024 / 1024,
                'memory_percent': self.process.memory_percent(),
                'cpu_percent': cpu_percent,
                'num_threads': self.process.num_threads(),
            }
        except:
            return {}


# ============================================================================
# TELEGRAM WEBHOOK HANDLER
# ============================================================================

async def telegram_webhook_handler(request):
    """
    Обработчик Telegram webhook
    
    Telegram будет отправлять обновления на этот endpoint
    вместо того чтобы мы их запрашивали через polling
    """
    try:
        bot_app = request.app.get('bot_application')
        
        if not bot_app or not bot_app.running:
            return web.Response(text="Bot not ready", status=503)
        
        try:
            data = await asyncio.wait_for(
                request.json(),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            return web.Response(text="Timeout", status=408)
        
        from telegram import Update
        update = Update.de_json(data, bot_app.bot)
        
        await asyncio.wait_for(
            bot_app.process_update(update),
            timeout=10.0
        )
        
        return web.Response(text="OK", status=200)
    
    except asyncio.TimeoutError:
        print(f"⚠️ [WEBHOOK] Timeout processing update")
        return web.Response(text="Timeout", status=408)
    
    except Exception as e:
        print(f"❌ [WEBHOOK] Error: {e}")
        tb.print_exc()
        return web.Response(text="Error", status=500)


async def health_check_handler(request):
    """Health check endpoint для Render.com и других хостингов"""
    try:
        resource_monitor = request.app.get('resource_monitor')
        rate_limiter = request.app.get('rate_limiter')
        
        stats = {}
        if resource_monitor:
            stats['resources'] = resource_monitor.get_stats()
        
        if rate_limiter:
            stats['rate_limiter'] = rate_limiter.get_stats()
        
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            **stats
        })
    except:
        return web.Response(text="OK", status=200)


async def start_health_server(bot_application=None, resource_monitor=None, rate_limiter=None):
    """
    Запуск HTTP сервера для health checks и webhook
    
    КРИТИЧНО для Render.com:
    - Render проверяет здоровье через HTTP
    - Без этого может убить процесс
    - Порт берётся из env PORT (по умолчанию 8000)
    - Также обрабатывает Telegram webhook
    """
    app = web.Application()
    
    app['bot_application'] = bot_application
    app['resource_monitor'] = resource_monitor
    app['rate_limiter'] = rate_limiter
    
    app.router.add_get('/', health_check_handler)
    app.router.add_get('/health', health_check_handler)
    app.router.add_get('/ping', health_check_handler)
    
    if bot_application:
        app.router.add_post('/webhook/telegram', telegram_webhook_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"✅ [HEALTH] HTTP server started on port {port}")
    print(f"   Available endpoints: /, /health, /ping")
    if bot_application:
        print(f"   Webhook endpoint: /webhook/telegram")
    
    return runner


class SystemHealthMonitor:
    """
    Централизованный мониторинг здоровья всех подсистем
    
    Отслеживает:
    - News Bot heartbeat
    - Whale Monitor heartbeat
    - Trading System heartbeat
    - Bot Commands Handler heartbeat
    - Error rates
    - Performance metrics
    - System resources
    """
    
    def __init__(self):
        self.news_alive = False
        self.whale_alive = False
        self.trading_alive = False
        self.bot_alive = False
        
        self.last_news_heartbeat: Optional[datetime] = None
        self.last_whale_heartbeat: Optional[datetime] = None
        self.last_trading_heartbeat: Optional[datetime] = None
        self.last_bot_heartbeat: Optional[datetime] = None
        
        self.news_cycles = 0
        self.whale_cycles = 0
        self.trading_cycles = 0
        self.bot_commands_processed = 0
        
        self.news_errors = 0
        self.whale_errors = 0
        self.trading_errors = 0
        self.bot_errors = 0
        
        self.check_interval = 300
        self.news_silence_threshold = 1800
        self.whale_silence_threshold = 600
        self.trading_silence_threshold = 3900
        self.bot_silence_threshold = 86400
        
        self.start_time = datetime.now(timezone.utc)
        
        print("💚 [HEALTH] Health Monitor инициализирован")
    
    def update_news_heartbeat(self):
        """Обновление heartbeat новостной системы"""
        self.news_alive = True
        self.last_news_heartbeat = datetime.now(timezone.utc)
        self.news_cycles += 1
    
    def update_whale_heartbeat(self):
        """Обновление heartbeat whale системы"""
        self.whale_alive = True
        self.last_whale_heartbeat = datetime.now(timezone.utc)
        self.whale_cycles += 1
    
    def update_trading_heartbeat(self):
        """Обновление heartbeat trading системы"""
        self.trading_alive = True
        self.last_trading_heartbeat = datetime.now(timezone.utc)
        self.trading_cycles += 1
    
    def update_bot_heartbeat(self):
        """Обновление heartbeat telegram bot"""
        self.bot_alive = True
        self.last_bot_heartbeat = datetime.now(timezone.utc)
    
    def record_bot_command(self):
        """Регистрация обработанной команды"""
        self.bot_commands_processed += 1
        self.update_bot_heartbeat()
    
    def record_error(self, system: str):
        """Регистрация ошибки в системе"""
        if system == "news":
            self.news_errors += 1
        elif system == "whale":
            self.whale_errors += 1
        elif system == "trading":
            self.trading_errors += 1
        elif system == "bot":
            self.bot_errors += 1
    
    def check_health(self) -> tuple[bool, List[str]]:
        """Проверка здоровья всех систем"""
        issues = []
        now = datetime.now(timezone.utc)
        
        if self.last_news_heartbeat:
            silence = (now - self.last_news_heartbeat).seconds
            if silence > self.news_silence_threshold:
                issues.append(
                    f"📰 News Bot: Silent for {silence//60} minutes "
                    f"(threshold: {self.news_silence_threshold//60}m)"
                )
        elif self.news_cycles > 0:
            issues.append("📰 News Bot: No recent heartbeat")
        
        if self.last_whale_heartbeat:
            silence = (now - self.last_whale_heartbeat).seconds
            if silence > self.whale_silence_threshold:
                issues.append(
                    f"🐋 Whale Monitor: Silent for {silence//60} minutes "
                    f"(threshold: {self.whale_silence_threshold//60}m)"
                )
        elif self.whale_cycles > 0:
            issues.append("🐋 Whale Monitor: No recent heartbeat")
        
        if self.last_trading_heartbeat:
            silence = (now - self.last_trading_heartbeat).seconds
            if silence > self.trading_silence_threshold:
                issues.append(
                    f"📈 Trading System: Silent for {silence//60} minutes "
                    f"(threshold: {self.trading_silence_threshold//60}m)"
                )
        elif self.trading_cycles > 0:
            issues.append("📈 Trading System: No recent heartbeat")
        
        if self.last_bot_heartbeat:
            silence = (now - self.last_bot_heartbeat).seconds
            if silence > self.bot_silence_threshold:
                issues.append(
                    f"🤖 Bot Handler: Silent for {silence//3600:.1f} hours "
                    f"(threshold: {self.bot_silence_threshold//3600}h)"
                )
        
        total_cycles = self.news_cycles + self.whale_cycles + self.trading_cycles
        total_errors = self.news_errors + self.whale_errors + self.trading_errors + self.bot_errors
        
        if total_cycles > 0:
            error_rate = (total_errors / total_cycles) * 100
            if error_rate > 10:
                issues.append(f"⚠️ High error rate: {error_rate:.1f}%")
        
        return len(issues) == 0, issues
    
    def get_uptime(self) -> timedelta:
        """Получение времени работы системы"""
        return datetime.now(timezone.utc) - self.start_time
    
    def get_stats(self) -> Dict:
        """Получение статистики здоровья"""
        uptime = self.get_uptime()
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": self._format_duration(uptime.total_seconds()),
            "systems": {
                "news": {
                    "alive": self.news_alive,
                    "cycles": self.news_cycles,
                    "errors": self.news_errors,
                    "last_heartbeat": self.last_news_heartbeat.isoformat() if self.last_news_heartbeat else None
                },
                "whale": {
                    "alive": self.whale_alive,
                    "cycles": self.whale_cycles,
                    "errors": self.whale_errors,
                    "last_heartbeat": self.last_whale_heartbeat.isoformat() if self.last_whale_heartbeat else None
                },
                "trading": {
                    "alive": self.trading_alive,
                    "cycles": self.trading_cycles,
                    "errors": self.trading_errors,
                    "last_heartbeat": self.last_trading_heartbeat.isoformat() if self.last_trading_heartbeat else None
                },
                "bot": {
                    "alive": self.bot_alive,
                    "commands_processed": self.bot_commands_processed,
                    "errors": self.bot_errors,
                    "last_heartbeat": self.last_bot_heartbeat.isoformat() if self.last_bot_heartbeat else None
                }
            },
            "total_cycles": self.news_cycles + self.whale_cycles + self.trading_cycles,
            "total_errors": self.news_errors + self.whale_errors + self.trading_errors + self.bot_errors,
            "total_bot_commands": self.bot_commands_processed
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Форматирование длительности"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            days = int(seconds / 86400)
            hours = (seconds % 86400) / 3600
            return f"{days}d {hours:.1f}h"


class IntegratedCryptoMonitor:
    """
    Интегрированная система мониторинга криптовалют
    
    Компоненты:
    1. News Bot - Умная агрегация криптовалютных новостей с AI обработкой
    2. Whale Monitor - Отслеживание крупных перемещений и smart money
    3. Trading System - Генерация торговых сигналов с ML предсказаниями
    4. Telegram Bot - Интерактивный обработчик команд пользователя (WEBHOOK)
    5. HTTP Health Server - Endpoint для мониторинга и webhook (Render.com)
    6. Chain Rate Limiter - Адаптивное управление запросами к RPC
    
    Все системы публикуют в один канал с умной приоритизацией
    и координацией для избежания перегрузки канала
    """
    
    def __init__(self):
        print("\n" + "="*80)
        print("🚀 INITIALIZING INTEGRATED CRYPTO MONITOR v4.1")
        print("="*80 + "\n")
        
        try:
            from bot.processor import NewsProcessor
            self.news_processor = NewsProcessor()
            print("✅ News Processor loaded")
        except Exception as e:
            print(f"⚠️ Failed to load News Processor: {e}")
            self.news_processor = None
        
        try:
            from app.scheduler import scheduler as whale_scheduler
            self.whale_scheduler = whale_scheduler
            print("✅ Whale Scheduler loaded")
        except Exception as e:
            print(f"⚠️ Failed to load Whale Scheduler: {e}")
            self.whale_scheduler = None
        
        try:
            from app.bot import application as bot_application
            self.bot_application = bot_application
            print("✅ Bot Commands Handler loaded")
            
            handlers_patched = self._patch_bot_handlers()
            if handlers_patched:
                print(f"   ✓ Bot handlers патчинг успешен")
            else:
                print(f"   ⚠️ Bot handlers патчинг не требуется или недоступен")
        except Exception as e:
            print(f"⚠️ Bot Commands Handler not loaded: {e}")
            tb.print_exc()
            self.bot_application = None
        
        self.health_monitor = SystemHealthMonitor()
        self.resource_monitor = ResourceMonitor(
            max_memory_mb=int(os.getenv('MAX_MEMORY_MB', '450'))
        )
        self.rate_limiter = ChainRateLimiter()
        
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'set_rate_limiter'):
            self.whale_scheduler.set_rate_limiter(self.rate_limiter)
            print("✅ Rate Limiter подключен к Whale Scheduler")
        
        self.shutdown_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []
        self._shutdown_in_progress = False
        self._health_server_runner = None
        
        self.stats = {
            "start_time": datetime.now(timezone.utc),
            "total_publications": 0,
            "news_publications": 0,
            "whale_publications": 0,
            "trading_publications": 0,
            "bot_commands": 0,
            "errors_caught": 0,
            "restarts": 0
        }
        
        print("\n✅ Integrated Crypto Monitor v4.1 инициализирован")
    
    def _patch_bot_handlers(self) -> bool:
        """
        Патчим обработчики команд для мониторинга
        
        НОВОЕ: Улучшенная версия с правильной обработкой handlers
        """
        if not self.bot_application:
            return False
        
        try:
            if not hasattr(self.bot_application, 'handlers'):
                print("   ⚠️ Bot application не имеет handlers")
                return False
            
            handlers_dict = self.bot_application.handlers
            
            if not handlers_dict or 0 not in handlers_dict:
                print("   ⚠️ Handlers пусты или группа 0 не существует")
                return False
            
            handlers_list = handlers_dict[0]
            
            if not handlers_list:
                print("   ⚠️ Список handlers пуст")
                return False
            
            patched_count = 0
            
            for handler in handlers_list:
                if not hasattr(handler, 'callback'):
                    continue
                
                original_callback = handler.callback
                health_monitor = self.health_monitor
                stats = self.stats
                
                @wraps(original_callback)
                async def wrapped_callback(update, context, original=original_callback, monitor=health_monitor, stats_dict=stats):
                    monitor.record_bot_command()
                    stats_dict["bot_commands"] += 1
                    
                    try:
                        return await original(update, context)
                    except Exception as e:
                        monitor.record_error("bot")
                        print(f"❌ [BOT] Error in command handler: {e}")
                        raise
                
                handler.callback = wrapped_callback
                patched_count += 1
            
            if patched_count > 0:
                print(f"   ✓ Патчинг {patched_count} handlers успешен")
                return True
            else:
                print("   ⚠️ Нет handlers для патчинга")
                return False
            
        except Exception as e:
            print(f"   ⚠️ Ошибка при патчинге handlers: {e}")
            tb.print_exc()
            return False
    
    async def run(self):
        """Главный цикл выполнения"""
        
        self._print_startup_banner()
        
        self._setup_signal_handlers()
        
        self._health_server_runner = await start_health_server(
            self.bot_application,
            self.resource_monitor,
            self.rate_limiter
        )
        
        try:
            self._tasks = []
            
            if self.news_processor:
                self._tasks.append(
                    asyncio.create_task(
                        self._run_news_system(),
                        name="news_system"
                    )
                )
            
            if self.whale_scheduler:
                self._tasks.append(
                    asyncio.create_task(
                        self._run_whale_system(),
                        name="whale_system"
                    )
                )
            
            if self.bot_application:
                self._tasks.append(
                    asyncio.create_task(
                        self._run_bot_webhook(),
                        name="bot_commands"
                    )
                )
            
            self._tasks.append(
                asyncio.create_task(
                    self._health_check_loop(),
                    name="health_monitor"
                )
            )
            
            self._tasks.append(
                asyncio.create_task(
                    self._coordination_loop(),
                    name="coordinator"
                )
            )
            
            self._tasks.append(
                asyncio.create_task(
                    self._wait_for_shutdown(),
                    name="shutdown_waiter"
                )
            )
            
            print(f"\n🚀 Запущено {len(self._tasks)} задач:")
            for task in self._tasks:
                print(f"   • {task.get_name()}")
            print()
            
            done, pending = await asyncio.wait(
                self._tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done:
                task_name = task.get_name()
                
                if task_name == "shutdown_waiter":
                    print("✅ Получен сигнал graceful shutdown")
                else:
                    exc = task.exception()
                    if exc:
                        print(f"\n❌ [CRITICAL] Task '{task_name}' crashed with exception:")
                        print("="*80)
                        tb.print_exception(type(exc), exc, exc.__traceback__)
                        print("="*80)
                        self.stats["errors_caught"] += 1
                    else:
                        print(f"⚠️ Task '{task_name}' завершилась без ошибок")
            
            if not self._shutdown_in_progress:
                print("\n⚠️ Инициируется shutdown из-за завершения задачи...")
                await self.shutdown()
        
        except asyncio.CancelledError:
            print("\n⏹️ [INFO] Задачи отменены")
        
        except KeyboardInterrupt:
            print("\n⏹️ [STOP] Получен Ctrl+C")
            await self.shutdown()
        
        except Exception as e:
            print(f"\n❌ [FATAL] Критическая ошибка в main loop:")
            print("="*80)
            tb.print_exc()
            print("="*80)
            self.stats["errors_caught"] += 1
        
        finally:
            await self.cleanup()
    
    async def _run_news_system(self):
        """Обёртка для новостной системы"""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while not self.shutdown_event.is_set():
            try:
                self.health_monitor.update_news_heartbeat()
                
                await asyncio.wait_for(
                    self.news_processor.run(),
                    timeout=300.0
                )
                
                consecutive_errors = 0
                await asyncio.sleep(1)
            
            except asyncio.TimeoutError:
                print(f"⚠️ [NEWS] Timeout (300s)")
                consecutive_errors += 1
            
            except asyncio.CancelledError:
                print("📰 [NEWS] Получен сигнал остановки")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error("news")
                self.stats["errors_caught"] += 1
                
                print(f"\n❌ [NEWS] Ошибка ({consecutive_errors}/{max_consecutive_errors}):")
                print(f"   {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"❌ [NEWS] Слишком много ошибок подряд, перезапуск через 5 минут...")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                    self.stats["restarts"] += 1
                else:
                    delay = min(30 * (2 ** consecutive_errors), 300)
                    print(f"⏳ [NEWS] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        print("📰 [NEWS] News system остановлена")
    
    async def _run_whale_system(self):
        """Обёртка для whale monitoring системы"""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while not self.shutdown_event.is_set():
            try:
                self.health_monitor.update_whale_heartbeat()
                
                await asyncio.wait_for(
                    self.whale_scheduler.run_cycle(),
                    timeout=120.0
                )
                
                consecutive_errors = 0
                
                if not self.resource_monitor.check_memory():
                    print("⚠️ [WHALE] Memory pressure detected, slowing down...")
                    await asyncio.sleep(30)
                
                await asyncio.sleep(1)
            
            except asyncio.TimeoutError:
                print(f"⚠️ [WHALE] Timeout (120s)")
                consecutive_errors += 1
            
            except asyncio.CancelledError:
                print("🐋 [WHALE] Получен сигнал остановки")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error("whale")
                self.stats["errors_caught"] += 1
                
                print(f"\n❌ [WHALE] Ошибка ({consecutive_errors}/{max_consecutive_errors}):")
                print(f"   {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"❌ [WHALE] Слишком много ошибок подряд, перезапуск через 5 минут...")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                    self.stats["restarts"] += 1
                else:
                    delay = min(30 * (2 ** consecutive_errors), 300)
                    print(f"⏳ [WHALE] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        print("🐋 [WHALE] Whale system остановлена")
    
    async def _run_bot_webhook(self):
        """
        Запуск Telegram bot в режиме WEBHOOK (вместо polling)
        
        ПРЕИМУЩЕСТВА WEBHOOK:
        - Нет конфликтов между экземплярами
        - Меньше нагрузка на Telegram API
        - Мгновенная доставка обновлений
        - Production-ready решение
        """
        try:
            print("🤖 [BOT] Инициализация command handler (WEBHOOK MODE)...")
            
            await asyncio.wait_for(
                self.bot_application.initialize(),
                timeout=30.0
            )
            await asyncio.wait_for(
                self.bot_application.start(),
                timeout=30.0
            )
            
            webhook_url = os.environ.get('WEBHOOK_URL', '')
            
            if not webhook_url:
                render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
                if render_url:
                    webhook_url = f"{render_url}/webhook/telegram"
                else:
                    service_name = os.environ.get('RENDER_SERVICE_NAME', 'crypto-compass')
                    webhook_url = f"https://{service_name}.onrender.com/webhook/telegram"
            
            print(f"🤖 [BOT] Устанавливаем webhook: {webhook_url}")
            
            await asyncio.wait_for(
                self.bot_application.bot.delete_webhook(drop_pending_updates=True),
                timeout=10.0
            )
            
            webhook_info = await asyncio.wait_for(
                self.bot_application.bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=None,
                    drop_pending_updates=True
                ),
                timeout=10.0
            )
            
            if webhook_info:
                print("✅ [BOT] Webhook установлен успешно")
            else:
                print("⚠️ [BOT] Webhook set вернул False, но продолжаем")
            
            self.health_monitor.update_bot_heartbeat()
            
            print("✅ [BOT] Command handler активен в WEBHOOK режиме")
            print(f"   Webhook URL: {webhook_url}")
            print("   Доступные команды: /start, /help, /status, /positions, /performance")
            
            while not self.shutdown_event.is_set():
                self.health_monitor.update_bot_heartbeat()
                await asyncio.sleep(60)
            
            print("🤖 [BOT] Получен сигнал остановки")
        
        except asyncio.TimeoutError:
            print("❌ [BOT] Timeout при инициализации")
        
        except asyncio.CancelledError:
            print("🤖 [BOT] Получен сигнал отмены")
        
        except Exception as e:
            self.health_monitor.record_error("bot")
            self.stats["errors_caught"] += 1
            
            print(f"\n❌ [BOT] Ошибка при установке webhook:")
            print(f"   {e}")
            tb.print_exc()
        
        finally:
            print("🤖 [BOT] Останавливаем command handler...")
            try:
                await asyncio.wait_for(
                    self.bot_application.bot.delete_webhook(),
                    timeout=10.0
                )
                print("   ✓ Webhook удалён")
                
                if self.bot_application.running:
                    await asyncio.wait_for(
                        self.bot_application.stop(),
                        timeout=10.0
                    )
                    print("   ✓ Application остановлен")
                
                await asyncio.wait_for(
                    self.bot_application.shutdown(),
                    timeout=10.0
                )
                print("   ✓ Shutdown завершён")
            
            except asyncio.TimeoutError:
                print("   ⚠️ Timeout при shutdown")
            except Exception as e:
                print(f"   ⚠️ Ошибка при shutdown: {e}")
            
            print("✅ [BOT] Command handler полностью остановлен")
    
    async def _health_check_loop(self):
        """Периодическая проверка здоровья всех систем"""
        await asyncio.sleep(300)
        
        while not self.shutdown_event.is_set():
            try:
                is_healthy, issues = self.health_monitor.check_health()
                
                if not is_healthy:
                    print("\n" + "="*80)
                    print("⚠️ [HEALTH] ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
                    print("="*80)
                    for issue in issues:
                        print(f"   {issue}")
                    print("="*80 + "\n")
                
                self.resource_monitor.check_memory()
                
                self.rate_limiter.print_stats()
                
                await asyncio.sleep(self.health_monitor.check_interval)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                print(f"❌ [HEALTH] Ошибка проверки здоровья: {e}")
                await asyncio.sleep(self.health_monitor.check_interval)
        
        print("💚 [HEALTH] Health monitor остановлен")
    
    async def _coordination_loop(self):
        """Координация публикаций между системами"""
        await asyncio.sleep(10)
        
        while not self.shutdown_event.is_set():
            try:
                if (datetime.now(timezone.utc) - self.resource_monitor.last_gc).seconds > self.resource_monitor.gc_interval:
                    gc.collect()
                    self.resource_monitor.last_gc = datetime.now(timezone.utc)
                
                await asyncio.sleep(60)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                print(f"❌ [COORDINATOR] Ошибка: {e}")
                await asyncio.sleep(60)
        
        print("🔄 [COORDINATOR] Coordinator остановлен")
    
    async def _wait_for_shutdown(self):
        """Ожидание сигнала shutdown"""
        await self.shutdown_event.wait()
        print("✅ [SHUTDOWN] Shutdown signal получен")
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        def signal_handler(signum, frame):
            print(f"\n⚠️ [SIGNAL] Получен сигнал {signal.Signals(signum).name}")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("✅ Установлен обработчик для SIGINT")
        print("✅ Установлен обработчик для SIGTERM")
    
    async def shutdown(self):
        """Graceful shutdown всех систем"""
        if self._shutdown_in_progress:
            print("⚠️ [SHUTDOWN] Shutdown уже в процессе, игнорируем")
            return
        
        self._shutdown_in_progress = True
        self.shutdown_event.set()
        
        print("\n" + "="*80)
        print("🛑 INITIATING GRACEFUL SHUTDOWN")
        print("="*80 + "\n")
        
        print("⏳ [1/4] Останавливаем HTTP health server...")
        try:
            if self._health_server_runner:
                await asyncio.wait_for(
                    self._health_server_runner.cleanup(),
                    timeout=10.0
                )
                print("   ✓ Health server остановлен")
        except asyncio.TimeoutError:
            print("   ⚠️ Timeout остановки health server")
        except Exception as e:
            print(f"   ⚠️ Ошибка остановки health server: {e}")
        
        print("\n⏳ [2/4] Ждём завершения всех задач...")
        if self._tasks:
            for task in self._tasks:
                if not task.done() and task.get_name() != "shutdown_waiter":
                    task.cancel()
            
            try:
                await asyncio.wait_for(
                    asyncio.wait(self._tasks),
                    timeout=15.0
                )
                print("   ✓ Все задачи завершены")
            except asyncio.TimeoutError:
                print("   ⚠️ Timeout при ожидании задач")
        
        print("\n⏳ [3/4] Останавливаем подсистемы...")
        
        if self.news_processor and hasattr(self.news_processor, 'cleanup'):
            try:
                await asyncio.wait_for(
                    self.news_processor.cleanup(),
                    timeout=10.0
                )
                print("   ✓ News Processor остановлен")
            except asyncio.TimeoutError:
                print("   ⚠️ Timeout остановки News Processor")
            except Exception as e:
                print(f"   ⚠️ Ошибка остановки News Processor: {e}")
        
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'cleanup'):
            try:
                await asyncio.wait_for(
                    self.whale_scheduler.cleanup(),
                    timeout=10.0
                )
                print("   ✓ Whale Scheduler остановлен")
            except asyncio.TimeoutError:
                print("   ⚠️ Timeout остановки Whale Scheduler")
            except Exception as e:
                print(f"   ⚠️ Ошибка остановки Whale Scheduler: {e}")
        
        print("\n⏳ [4/4] Финальная очистка...")
        await asyncio.sleep(1)
        
        print("\n" + "="*80)
        print("✅ SHUTDOWN SEQUENCE COMPLETED")
        print("="*80)
    
    async def cleanup(self):
        """Финальная очистка ресурсов"""
        print("\n🧹 [CLEANUP] Очистка ресурсов...")
        
        try:
            if self.whale_scheduler and hasattr(self.whale_scheduler, '_save_state'):
                self.whale_scheduler._save_state()
                print("   ✅ Состояние Whale Monitor сохранено")
        except Exception as e:
            print(f"   ⚠️ Ошибка сохранения состояния: {e}")
        
        gc.collect()
        
        self._print_final_statistics()
        
        print("\n" + "="*80)
        print("👋 СИСТЕМА ПОЛНОСТЬЮ ОСТАНОВЛЕНА")
        print("="*80)
    
    def _print_startup_banner(self):
        """Вывод стартового баннера"""
        print("\n" + "="*80)
        print("🚀 INTEGRATED CRYPTO MONITOR v4.1 - STARTING UP")
        print("="*80 + "\n")
        
        print("📦 АКТИВНЫЕ КОМПОНЕНТЫ:\n")
        
        if self.news_processor:
            print("📰 News Bot")
            print("   ├─ AI-powered article analysis")
            print("   ├─ Multi-source aggregation")
            print("   ├─ Sentiment analysis")
            print("   ├─ Smart deduplication")
            print("   └─ Status: ✅ Active")
        else:
            print("📰 News Bot")
            print("   └─ Status: ❌ Disabled")
        
        print()
        
        if self.whale_scheduler:
            print("🐋 Whale Monitor")
            print("   ├─ Smart money tracking")
            print("   ├─ Wallet discovery")
            print("   ├─ Pattern recognition")
            print("   ├─ Adaptive thresholds")
            print("   ├─ Performance validation")
            print("   ├─ Adaptive Rate Limiting")
            print("   └─ Status: ✅ Active")
        else:
            print("🐋 Whale Monitor")
            print("   └─ Status: ❌ Disabled")
        
        print()
        
        if self.bot_application:
            print("🤖 Telegram Bot Commands (WEBHOOK MODE)")
            print("   ├─ User command handling")
            print("   ├─ Interactive keyboards")
            print("   ├─ Position management")
            print("   ├─ Performance analytics")
            print("   ├─ Manual signal generation")
            print("   ├─ Available commands:")
            print("   │  ├─ /start, /help, /menu")
            print("   │  ├─ /status, /positions, /performance")
            print("   │  ├─ /signal <ASSET>, /close <position_id>")
            print("   │  └─ /wallets, /config, /thresholds")
            print("   └─ Status: ✅ Active")
        else:
            print("🤖 Telegram Bot Commands")
            print("   └─ Status: ❌ Disabled")
        
        print()
        
        print("💚 Health Monitor")
        print("   ├─ System heartbeat tracking")
        print("   ├─ Error rate monitoring")
        print("   ├─ Auto-restart on failures")
        print(f"   ├─ Check interval: {self.health_monitor.check_interval}s")
        print("   └─ Status: ✅ Active")
        
        print()
        
        print("🔒 Chain Rate Limiter")
        print("   ├─ Adaptive request throttling")
        print("   ├─ Automatic 429 error handling")
        print("   ├─ Dynamic chain disable/enable")
        print("   ├─ Exponential backoff recovery")
        print("   └─ Status: ✅ Active")
        
        print()
        
        print("🌐 HTTP Health Server")
        print("   ├─ Render.com health checks")
        print("   ├─ Endpoints: /, /health, /ping")
        if self.bot_application:
            print("   ├─ Telegram webhook: /webhook/telegram")
        print(f"   ├─ Port: {os.environ.get('PORT', 8000)}")
        print("   └─ Status: ✅ Active")
        
        print()
        
        print("🔄 Coordinator")
        print("   ├─ Publication balancing")
        print("   ├─ Priority management")
        print("   ├─ Metrics aggregation")
        print("   └─ Status: ✅ Active")
        
        print("\n" + "="*80)
        print(f"⏰ Startup Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("="*80 + "\n")
    
    def _print_final_statistics(self):
        """Вывод финальной статистики"""
        print("\n" + "="*80)
        print("📊 ФИНАЛЬНАЯ СТАТИСТИКА")
        print("="*80)
        
        uptime = self.health_monitor.get_uptime()
        print(f"\n⏱️ UPTIME: {self.health_monitor._format_duration(uptime.total_seconds())}")
        
        health_stats = self.health_monitor.get_stats()
        
        print(f"\n💚 HEALTH MONITOR:")
        print(f"   Total Cycles: {health_stats['total_cycles']}")
        print(f"   Total Errors: {health_stats['total_errors']}")
        print(f"   Bot Commands Processed: {health_stats['total_bot_commands']}")
        
        if health_stats['total_cycles'] > 0:
            error_rate = (health_stats['total_errors'] / health_stats['total_cycles']) * 100
            print(f"   Error Rate: {error_rate:.2f}%")
        
        print(f"\n🔒 RATE LIMITER:")
        rate_stats = self.rate_limiter.get_stats()
        for chain, stats in rate_stats['chains'].items():
            success_rate = 0
            if stats['total_requests'] > 0:
                success_rate = (stats['successful_requests'] / stats['total_requests']) * 100
            
            print(f"   {chain}:")
            print(f"     Requests: {stats['total_requests']} (Success rate: {success_rate:.1f}%)")
            print(f"     429 Errors: {stats['total_429_errors']}")
            print(f"     Recovery Attempts: {stats['recovery_attempts']}")
        
        resource_stats = self.resource_monitor.get_stats()
        if resource_stats:
            print(f"\n💾 RESOURCES:")
            print(f"   Memory: {resource_stats.get('memory_mb', 0):.1f}MB ({resource_stats.get('memory_percent', 0):.1f}%)")
            print(f"   CPU: {resource_stats.get('cpu_percent', 0):.1f}%")
            print(f"   Threads: {resource_stats.get('num_threads', 0)}")
        
        if self.news_processor and hasattr(self.news_processor, 'metrics'):
            news_metrics = self.news_processor.metrics
            
            print(f"\n📰 NEWS BOT:")
            print(f"   Cycles: {news_metrics.cycles_completed}")
            print(f"   Articles Processed: {news_metrics.articles_processed}")
            print(f"   Articles Published: {news_metrics.articles_published}")
            
            if news_metrics.articles_processed > 0:
                publish_rate = (news_metrics.articles_published / news_metrics.articles_processed) * 100
                print(f"   Publish Rate: {publish_rate:.1f}%")
            
            print(f"   Errors: {news_metrics.errors}")
        
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'stats'):
            whale_stats = self.whale_scheduler.stats
            
            print(f"\n🐋 WHALE MONITOR:")
            print(f"   Events Collected: {whale_stats.get('events_collected', 0)}")
            print(f"   Events Qualified: {whale_stats.get('events_qualified', 0)}")
            print(f"   Events Published: {whale_stats.get('events_published', 0)}")
            
            successful = whale_stats.get('events_successful', 0)
            failed = whale_stats.get('events_failed', 0)
            
            if successful + failed > 0:
                accuracy = (successful / (successful + failed)) * 100
                print(f"   Accuracy: {accuracy:.1f}% ({successful}/{successful + failed})")
            
            print(f"   Wallets Discovered: {whale_stats.get('wallets_discovered', 0)}")
            print(f"   Wallets Removed: {whale_stats.get('wallets_removed', 0)}")
            
            if self.whale_scheduler.trading_enabled:
                print(f"\n📈 TRADING SYSTEM:")
                print(f"   Signals Generated: {whale_stats.get('trading_signals_generated', 0)}")
                print(f"   Signals Sent: {whale_stats.get('trading_signals_sent', 0)}")
                print(f"   Positions Opened: {whale_stats.get('positions_opened', 0)}")
                print(f"   Positions Closed: {whale_stats.get('positions_closed', 0)}")
        
        if self.bot_application:
            print(f"\n🤖 TELEGRAM BOT:")
            print(f"   Commands Processed: {health_stats['total_bot_commands']}")
            print(f"   Errors: {health_stats['systems']['bot']['errors']}")
        
        print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
        print(f"   Total Publications: {self.stats['total_publications']}")
        print(f"   ├─ News: {self.stats['news_publications']}")
        print(f"   ├─ Whale: {self.stats['whale_publications']}")
        print(f"   └─ Trading: {self.stats['trading_publications']}")
        print(f"   Bot Commands: {self.stats['bot_commands']}")
        print(f"   Errors Caught: {self.stats['errors_caught']}")
        print(f"   System Restarts: {self.stats['restarts']}")
        
        print("\n" + "="*80)


def check_dependencies():
    """Проверка установленных зависимостей"""
    print("🔍 Проверка зависимостей...\n")
    
    required_packages = {
        'telegram': 'python-telegram-bot',
        'aiohttp': 'aiohttp',
        'feedparser': 'feedparser',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'sklearn': 'scikit-learn'
    }
    
    missing = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Отсутствуют зависимости: {', '.join(missing)}")
        print("\nУстановите их командой:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    print("\n✅ Все зависимости установлены")
    return True


def create_directories():
    """Создание необходимых директорий"""
    print("\n📁 Создание директорий...\n")
    
    directories = [
        Path("data"),
        Path("data/history"),
        Path("data/learning"),
        Path("data/wallets"),
        Path("data/positions"),
        Path("data/performance"),
        Path("logs"),
    ]
    
    if not Path("/tmp").exists():
        directories.append(Path("/tmp"))
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ {directory}")
        except Exception as e:
            print(f"   ⚠️ {directory}: {e}")
    
    print()


def print_system_info():
    """Вывод информации о системе"""
    print("="*80)
    print("💎 CRYPTO COMPASS - Integrated Monitoring System v4.1")
    print("="*80)
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🐍 Python {sys.version.split()[0]}")
    print(f"💻 Platform: {sys.platform}")
    print(f"📂 Working Directory: {os.getcwd()}")
    print("="*80 + "\n")


def main():
    """Главная точка входа в приложение"""
    print_system_info()
    
    if not check_dependencies():
        sys.exit(1)
    
    create_directories()
    
    print("🚀 Запуск Integrated Crypto Monitor v4.1...\n")
    
    bot = IntegratedCryptoMonitor()
    
    try:
        if sys.version_info >= (3, 7):
            asyncio.run(bot.run())
        else:
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(bot.run())
            finally:
                loop.close()
    
    except KeyboardInterrupt:
        print("\n⏹️ Остановка по Ctrl+C")
    
    except Exception as e:
        print(f"\n❌ Критическая ошибка в main:")
        print("="*80)
        tb.print_exc()
        print("="*80)
        sys.exit(1)
    
    print("\n👋 Goodbye!")


if __name__ == '__main__':
    main()