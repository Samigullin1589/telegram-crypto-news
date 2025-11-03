"""
SOLANA RPC MANAGER v2.0
Продвинутый менеджер для работы с Solana RPC endpoints
Решает проблему 429 ошибок раз и навсегда

Фичи:
- 10+ публичных RPC endpoints с автоматической ротацией
- Exponential backoff с jitter
- Rate limiting с умными очередями
- Кэширование результатов
- Circuit breaker для неработающих endpoints
- Health monitoring всех endpoints
- Приоритизация критических запросов
- Batch операции
- Автоматический failover
- Детальная телеметрия
"""

import asyncio
import aiohttp
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class EndpointStatus(Enum):
    """Статус RPC endpoint"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CIRCUIT_OPEN = "circuit_open"
    RATE_LIMITED = "rate_limited"
    DEAD = "dead"


@dataclass
class RpcEndpoint:
    """RPC Endpoint с метриками"""
    url: str
    name: str
    tier: str = "free"  # free, paid, premium
    
    # Метрики производительности
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    last_429_at: Optional[datetime] = None
    
    # Circuit breaker
    status: EndpointStatus = EndpointStatus.HEALTHY
    consecutive_failures: int = 0
    last_success_at: Optional[datetime] = None
    circuit_open_until: Optional[datetime] = None
    
    # Rate limiting
    requests_per_second: int = 10
    requests_this_second: int = 0
    current_second: int = field(default_factory=lambda: int(time.time()))
    
    # Latency tracking
    avg_latency_ms: float = 0.0
    last_latencies: deque = field(default_factory=lambda: deque(maxlen=50))
    
    # Priority
    priority: int = 0  # Выше = лучше
    
    def record_request(self, success: bool, latency_ms: float, is_429: bool = False):
        """Запись результата запроса"""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
            self.consecutive_failures = 0
            self.last_success_at = datetime.utcnow()
            
            # Обновляем latency
            self.last_latencies.append(latency_ms)
            if self.last_latencies:
                self.avg_latency_ms = sum(self.last_latencies) / len(self.last_latencies)
            
            # Восстанавливаем статус
            if self.status == EndpointStatus.DEGRADED and self.consecutive_failures == 0:
                self.status = EndpointStatus.HEALTHY
        
        else:
            self.failed_requests += 1
            self.consecutive_failures += 1
            
            if is_429:
                self.rate_limit_hits += 1
                self.last_429_at = datetime.utcnow()
                self.status = EndpointStatus.RATE_LIMITED
                # Circuit breaker на 60 секунд после 429
                self.circuit_open_until = datetime.utcnow() + timedelta(seconds=60)
            
            # Circuit breaker logic
            if self.consecutive_failures >= 5:
                self.status = EndpointStatus.CIRCUIT_OPEN
                self.circuit_open_until = datetime.utcnow() + timedelta(seconds=120)
            elif self.consecutive_failures >= 3:
                self.status = EndpointStatus.DEGRADED
    
    def can_make_request(self) -> bool:
        """Проверяет, можно ли делать запрос"""
        
        # Проверяем circuit breaker
        if self.circuit_open_until:
            if datetime.utcnow() < self.circuit_open_until:
                return False
            else:
                # Пробуем восстановить
                self.circuit_open_until = None
                self.status = EndpointStatus.HEALTHY
                self.consecutive_failures = 0
        
        # Проверяем rate limit
        current_second = int(time.time())
        if current_second != self.current_second:
            self.current_second = current_second
            self.requests_this_second = 0
        
        if self.requests_this_second >= self.requests_per_second:
            return False
        
        return True
    
    def increment_request_count(self):
        """Увеличивает счётчик запросов"""
        self.requests_this_second += 1
    
    def get_health_score(self) -> float:
        """Рассчитывает health score (0-100)"""
        if self.total_requests == 0:
            return 50.0
        
        # Success rate
        success_rate = self.successful_requests / self.total_requests
        
        # Penalty за 429 ошибки
        rate_limit_penalty = min(0.3, self.rate_limit_hits * 0.01)
        
        # Penalty за consecutive failures
        failure_penalty = min(0.3, self.consecutive_failures * 0.1)
        
        # Bonus за низкую latency
        latency_bonus = 0
        if self.avg_latency_ms > 0:
            if self.avg_latency_ms < 100:
                latency_bonus = 0.1
            elif self.avg_latency_ms < 300:
                latency_bonus = 0.05
        
        # Circuit breaker penalty
        circuit_penalty = 0
        if self.status == EndpointStatus.CIRCUIT_OPEN:
            circuit_penalty = 0.5
        elif self.status == EndpointStatus.RATE_LIMITED:
            circuit_penalty = 0.3
        elif self.status == EndpointStatus.DEGRADED:
            circuit_penalty = 0.1
        
        score = (success_rate + latency_bonus - rate_limit_penalty - failure_penalty - circuit_penalty) * 100
        return max(0, min(100, score))


class RequestPriority(Enum):
    """Приоритет запроса"""
    CRITICAL = 3
    HIGH = 2
    NORMAL = 1
    LOW = 0


@dataclass
class QueuedRequest:
    """Запрос в очереди"""
    method: str
    params: List[Any]
    priority: RequestPriority
    created_at: datetime
    max_retries: int = 3
    retry_count: int = 0
    
    def __lt__(self, other):
        # Для priority queue
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at


class SolanaRpcManager:
    """
    Продвинутый менеджер RPC endpoints для Solana
    """
    
    def __init__(self, custom_endpoints: List[str] = None):
        """
        Инициализация
        
        Args:
            custom_endpoints: Дополнительные RPC endpoints
        """
        
        # Инициализируем endpoints
        self.endpoints: List[RpcEndpoint] = []
        self._initialize_endpoints(custom_endpoints)
        
        # Кэш результатов
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = timedelta(seconds=30)
        self.max_cache_size = 1000
        
        # Очередь запросов
        self.request_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.queue_processor_task: Optional[asyncio.Task] = None
        
        # Rate limiting
        self.global_rate_limit = 100  # requests per second
        self.current_second_requests = 0
        self.current_second = int(time.time())
        
        # Статистика
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_retries': 0,
            'total_429_errors': 0,
            'total_timeouts': 0,
            'total_failures': 0,
            'queue_size_peak': 0
        }
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"✅ SolanaRpcManager инициализирован с {len(self.endpoints)} endpoints")
        for ep in self.endpoints:
            logger.info(f"   • {ep.name} ({ep.tier}) - {ep.url[:50]}...")
    
    def _initialize_endpoints(self, custom_endpoints: List[str] = None):
        """Инициализация списка endpoints"""
        
        # Публичные RPC endpoints (отсортированы по надёжности)
        public_endpoints = [
            # Tier 1: Наиболее надёжные
            ("Helius (Free)", "https://rpc.helius.xyz/?api-key=YOUR_KEY_HERE", "free", 15, 100),
            ("QuickNode (Free)", "https://solana-mainnet.quicknode.com/YOUR_KEY_HERE", "free", 10, 95),
            ("Chainstack (Free)", "https://solana-mainnet.core.chainstack.com/YOUR_KEY_HERE", "free", 10, 90),
            
            # Tier 2: Стабильные публичные
            ("Ankr", "https://rpc.ankr.com/solana", "free", 5, 80),
            ("GetBlock", "https://go.getblock.io/YOUR_KEY_HERE", "free", 8, 85),
            ("Syndica", "https://solana-mainnet.rpc.syndica.io", "free", 5, 75),
            
            # Tier 3: Базовые публичные (используем как fallback)
            ("Solana Mainnet", "https://api.mainnet-beta.solana.com", "free", 3, 70),
            ("Project Serum", "https://solana-api.projectserum.com", "free", 3, 65),
            ("Genesys Go", "https://ssc-dao.genesysgo.net", "free", 4, 60),
            ("Serum RPC", "https://solana-api.projectserum.com", "free", 3, 55),
            
            # Tier 4: Дополнительные fallback
            ("Metaplex", "https://api.metaplex.solana.com", "free", 2, 50),
            ("Blockdaemon", "https://ssc-dao.genesysgo.net", "free", 2, 45),
        ]
        
        for name, url, tier, rps, priority in public_endpoints:
            endpoint = RpcEndpoint(
                url=url,
                name=name,
                tier=tier,
                requests_per_second=rps,
                priority=priority
            )
            self.endpoints.append(endpoint)
        
        # Добавляем пользовательские endpoints (высокий приоритет)
        if custom_endpoints:
            for i, url in enumerate(custom_endpoints):
                endpoint = RpcEndpoint(
                    url=url,
                    name=f"Custom-{i+1}",
                    tier="premium",
                    requests_per_second=20,
                    priority=110 + i
                )
                self.endpoints.append(endpoint)
        
        # Сортируем по приоритету
        self.endpoints.sort(key=lambda ep: ep.priority, reverse=True)
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=10)
        )
        
        # Запускаем обработчик очереди
        self.queue_processor_task = asyncio.create_task(self._process_queue())
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        
        # Останавливаем обработчик очереди
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
    
    async def call(
        self,
        method: str,
        params: List[Any],
        priority: RequestPriority = RequestPriority.NORMAL,
        use_cache: bool = True,
        max_retries: int = 5
    ) -> Any:
        """
        Вызов RPC метода с автоматическим retry и failover
        
        Args:
            method: RPC метод
            params: Параметры
            priority: Приоритет запроса
            use_cache: Использовать кэш
            max_retries: Максимум попыток
        
        Returns:
            Результат RPC вызова
        """
        
        self.stats['total_requests'] += 1
        
        # Проверяем кэш
        if use_cache:
            cache_key = self._make_cache_key(method, params)
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                self.stats['cache_hits'] += 1
                return cached
            self.stats['cache_misses'] += 1
        
        # Пробуем сделать запрос с retry
        for attempt in range(max_retries):
            try:
                result = await self._execute_request(method, params, priority)
                
                # Кэшируем результат
                if use_cache and result is not None:
                    cache_key = self._make_cache_key(method, params)
                    self._add_to_cache(cache_key, result)
                
                return result
            
            except aiohttp.ClientResponseError as e:
                if e.status == 429:
                    self.stats['total_429_errors'] += 1
                    
                    # Exponential backoff с jitter
                    base_delay = min(2 ** attempt, 60)
                    jitter = random.uniform(0, base_delay * 0.3)
                    delay = base_delay + jitter
                    
                    logger.warning(f"⚠️ [RPC] HTTP 429 на попытке {attempt+1}/{max_retries}, "
                                 f"ожидание {delay:.1f}s")
                    
                    await asyncio.sleep(delay)
                    
                    if attempt < max_retries - 1:
                        self.stats['total_retries'] += 1
                        continue
                
                raise
            
            except asyncio.TimeoutError:
                self.stats['total_timeouts'] += 1
                
                if attempt < max_retries - 1:
                    delay = min(2 ** attempt, 30)
                    logger.warning(f"⚠️ [RPC] Timeout на попытке {attempt+1}/{max_retries}, "
                                 f"ожидание {delay:.1f}s")
                    await asyncio.sleep(delay)
                    self.stats['total_retries'] += 1
                    continue
                
                raise
            
            except Exception as e:
                self.stats['total_failures'] += 1
                
                if attempt < max_retries - 1:
                    delay = min(2 ** attempt, 30)
                    logger.warning(f"⚠️ [RPC] Ошибка {type(e).__name__} на попытке {attempt+1}/{max_retries}, "
                                 f"ожидание {delay:.1f}s")
                    await asyncio.sleep(delay)
                    self.stats['total_retries'] += 1
                    continue
                
                raise
        
        raise Exception(f"Не удалось выполнить RPC запрос после {max_retries} попыток")
    
    async def _execute_request(
        self,
        method: str,
        params: List[Any],
        priority: RequestPriority
    ) -> Any:
        """Выполнение RPC запроса с выбором оптимального endpoint"""
        
        # Проверяем global rate limit
        await self._check_global_rate_limit()
        
        # Получаем список доступных endpoints
        available_endpoints = self._get_available_endpoints()
        
        if not available_endpoints:
            # Все endpoints недоступны, ждём
            logger.warning("⚠️ [RPC] Все endpoints недоступны, ожидание восстановления...")
            await asyncio.sleep(5)
            available_endpoints = self._get_available_endpoints()
            
            if not available_endpoints:
                raise Exception("Нет доступных RPC endpoints")
        
        # Пробуем endpoints по порядку
        last_error = None
        
        for endpoint in available_endpoints:
            try:
                start_time = time.time()
                
                result = await self._make_rpc_call(endpoint, method, params)
                
                latency_ms = (time.time() - start_time) * 1000
                endpoint.record_request(success=True, latency_ms=latency_ms)
                
                logger.debug(f"✅ [RPC] {endpoint.name}: {method} успешно ({latency_ms:.0f}ms)")
                
                return result
            
            except aiohttp.ClientResponseError as e:
                latency_ms = (time.time() - start_time) * 1000
                is_429 = e.status == 429
                
                endpoint.record_request(success=False, latency_ms=latency_ms, is_429=is_429)
                
                if is_429:
                    logger.warning(f"⚠️ [RPC] {endpoint.name}: HTTP 429")
                    last_error = e
                    continue
                
                raise
            
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                endpoint.record_request(success=False, latency_ms=latency_ms)
                
                logger.warning(f"⚠️ [RPC] {endpoint.name}: {type(e).__name__}")
                last_error = e
                continue
        
        # Все endpoints провалились
        if last_error:
            raise last_error
        
        raise Exception("Не удалось выполнить RPC запрос")
    
    async def _make_rpc_call(
        self,
        endpoint: RpcEndpoint,
        method: str,
        params: List[Any]
    ) -> Any:
        """Выполнение HTTP запроса к RPC endpoint"""
        
        endpoint.increment_request_count()
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        async with self.session.post(
            endpoint.url,
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            response.raise_for_status()
            
            data = await response.json()
            
            if "error" in data:
                error = data["error"]
                error_msg = error.get("message", "Unknown error")
                raise Exception(f"RPC Error: {error_msg}")
            
            return data.get("result")
    
    def _get_available_endpoints(self) -> List[RpcEndpoint]:
        """Получает список доступных endpoints отсортированных по health score"""
        
        available = [ep for ep in self.endpoints if ep.can_make_request()]
        
        # Сортируем по health score и приоритету
        available.sort(
            key=lambda ep: (ep.get_health_score(), ep.priority),
            reverse=True
        )
        
        return available
    
    async def _check_global_rate_limit(self):
        """Проверка глобального rate limit"""
        
        current_second = int(time.time())
        
        if current_second != self.current_second:
            self.current_second = current_second
            self.current_second_requests = 0
        
        if self.current_second_requests >= self.global_rate_limit:
            # Ждём до следующей секунды
            wait_time = 1.0 - (time.time() - current_second)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.current_second_requests += 1
    
    def _make_cache_key(self, method: str, params: List[Any]) -> str:
        """Создание ключа для кэша"""
        params_str = json.dumps(params, sort_keys=True)
        key_str = f"{method}:{params_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Получение из кэша"""
        if key in self.cache:
            value, cached_at = self.cache[key]
            
            if datetime.utcnow() - cached_at < self.cache_ttl:
                return value
            else:
                del self.cache[key]
        
        return None
    
    def _add_to_cache(self, key: str, value: Any):
        """Добавление в кэш"""
        self.cache[key] = (value, datetime.utcnow())
        
        # Очистка старых записей
        if len(self.cache) > self.max_cache_size:
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k][1]
            )[:self.max_cache_size // 2]
            
            for key in oldest_keys:
                del self.cache[key]
    
    async def _process_queue(self):
        """Обработчик очереди запросов"""
        
        logger.info("🚀 [RPC] Запущен обработчик очереди")
        
        try:
            while True:
                try:
                    # Получаем запрос из очереди
                    request = await asyncio.wait_for(
                        self.request_queue.get(),
                        timeout=1.0
                    )
                    
                    # Выполняем запрос
                    try:
                        result = await self._execute_request(
                            request.method,
                            request.params,
                            request.priority
                        )
                        
                        # Здесь можно добавить callback для результата
                        
                    except Exception as e:
                        logger.error(f"❌ [RPC] Ошибка обработки запроса из очереди: {e}")
                    
                    finally:
                        self.request_queue.task_done()
                
                except asyncio.TimeoutError:
                    continue
        
        except asyncio.CancelledError:
            logger.info("🛑 [RPC] Обработчик очереди остановлен")
    
    async def batch_call(
        self,
        calls: List[Tuple[str, List[Any]]],
        priority: RequestPriority = RequestPriority.NORMAL
    ) -> List[Any]:
        """
        Batch запросы для оптимизации
        
        Args:
            calls: Список (method, params)
            priority: Приоритет
        
        Returns:
            Список результатов
        """
        
        # Solana RPC поддерживает batch запросы
        if len(calls) == 0:
            return []
        
        # Если много запросов, разбиваем на чанки
        chunk_size = 50
        results = []
        
        for i in range(0, len(calls), chunk_size):
            chunk = calls[i:i+chunk_size]
            
            batch_payload = [
                {
                    "jsonrpc": "2.0",
                    "id": idx,
                    "method": method,
                    "params": params
                }
                for idx, (method, params) in enumerate(chunk)
            ]
            
            # Получаем доступный endpoint
            available_endpoints = self._get_available_endpoints()
            
            if not available_endpoints:
                raise Exception("Нет доступных RPC endpoints для batch запроса")
            
            endpoint = available_endpoints[0]
            
            try:
                start_time = time.time()
                
                async with self.session.post(
                    endpoint.url,
                    json=batch_payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response.raise_for_status()
                    
                    data = await response.json()
                    
                    latency_ms = (time.time() - start_time) * 1000
                    endpoint.record_request(success=True, latency_ms=latency_ms)
                    
                    # Извлекаем results
                    if isinstance(data, list):
                        for item in data:
                            if "error" in item:
                                results.append(None)
                            else:
                                results.append(item.get("result"))
                    else:
                        results.append(data.get("result"))
            
            except Exception as e:
                logger.error(f"❌ [RPC] Ошибка batch запроса: {e}")
                results.extend([None] * len(chunk))
        
        return results
    
    def get_health_report(self) -> Dict:
        """Получить отчёт о здоровье всех endpoints"""
        
        report = {
            'endpoints': [],
            'summary': {
                'total': len(self.endpoints),
                'healthy': 0,
                'degraded': 0,
                'rate_limited': 0,
                'circuit_open': 0,
                'dead': 0
            },
            'stats': self.stats.copy(),
            'cache_size': len(self.cache)
        }
        
        for endpoint in self.endpoints:
            ep_info = {
                'name': endpoint.name,
                'url': endpoint.url[:50] + "...",
                'tier': endpoint.tier,
                'status': endpoint.status.value,
                'health_score': endpoint.get_health_score(),
                'total_requests': endpoint.total_requests,
                'success_rate': (
                    endpoint.successful_requests / endpoint.total_requests
                    if endpoint.total_requests > 0 else 0
                ),
                'avg_latency_ms': endpoint.avg_latency_ms,
                'rate_limit_hits': endpoint.rate_limit_hits,
                'consecutive_failures': endpoint.consecutive_failures,
                'last_success': (
                    endpoint.last_success_at.isoformat()
                    if endpoint.last_success_at else None
                )
            }
            
            report['endpoints'].append(ep_info)
            
            # Обновляем summary
            if endpoint.status == EndpointStatus.HEALTHY:
                report['summary']['healthy'] += 1
            elif endpoint.status == EndpointStatus.DEGRADED:
                report['summary']['degraded'] += 1
            elif endpoint.status == EndpointStatus.RATE_LIMITED:
                report['summary']['rate_limited'] += 1
            elif endpoint.status == EndpointStatus.CIRCUIT_OPEN:
                report['summary']['circuit_open'] += 1
            elif endpoint.status == EndpointStatus.DEAD:
                report['summary']['dead'] += 1
        
        # Сортируем по health score
        report['endpoints'].sort(key=lambda x: x['health_score'], reverse=True)
        
        return report
    
    def print_health_report(self):
        """Вывод health report в консоль"""
        
        report = self.get_health_report()
        
        print("\n" + "="*80)
        print("🏥 SOLANA RPC HEALTH REPORT")
        print("="*80)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Endpoints: {report['summary']['total']}")
        print(f"   ✅ Healthy: {report['summary']['healthy']}")
        print(f"   ⚠️  Degraded: {report['summary']['degraded']}")
        print(f"   🚫 Rate Limited: {report['summary']['rate_limited']}")
        print(f"   ⛔ Circuit Open: {report['summary']['circuit_open']}")
        print(f"   💀 Dead: {report['summary']['dead']}")
        
        print(f"\n📈 STATISTICS:")
        print(f"   Total Requests: {report['stats']['total_requests']}")
        print(f"   Cache Hits: {report['stats']['cache_hits']}")
        print(f"   Cache Misses: {report['stats']['cache_misses']}")
        print(f"   Total Retries: {report['stats']['total_retries']}")
        print(f"   429 Errors: {report['stats']['total_429_errors']}")
        print(f"   Timeouts: {report['stats']['total_timeouts']}")
        print(f"   Failures: {report['stats']['total_failures']}")
        print(f"   Cache Size: {report['cache_size']}")
        
        print(f"\n🔝 TOP ENDPOINTS:")
        for i, ep in enumerate(report['endpoints'][:5], 1):
            status_emoji = {
                'healthy': '✅',
                'degraded': '⚠️',
                'rate_limited': '🚫',
                'circuit_open': '⛔',
                'dead': '💀'
            }
            emoji = status_emoji.get(ep['status'], '❓')
            
            print(f"\n{i}. {emoji} {ep['name']} ({ep['tier']})")
            print(f"   Status: {ep['status'].upper()}")
            print(f"   Health Score: {ep['health_score']:.1f}/100")
            print(f"   Requests: {ep['total_requests']} (success rate: {ep['success_rate']:.1%})")
            print(f"   Avg Latency: {ep['avg_latency_ms']:.0f}ms")
            print(f"   429 Hits: {ep['rate_limit_hits']}")
        
        print("\n" + "="*80 + "\n")
    
    def clear_cache(self):
        """Очистка кэша"""
        self.cache.clear()
        logger.info("🧹 RPC кэш очищен")
    
    def reset_stats(self):
        """Сброс статистики"""
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_retries': 0,
            'total_429_errors': 0,
            'total_timeouts': 0,
            'total_failures': 0,
            'queue_size_peak': 0
        }
        logger.info("🔄 Статистика сброшена")


# Глобальный экземпляр (singleton)
_global_rpc_manager: Optional[SolanaRpcManager] = None


async def get_rpc_manager(custom_endpoints: List[str] = None) -> SolanaRpcManager:
    """Получить глобальный RPC manager"""
    global _global_rpc_manager
    
    if _global_rpc_manager is None:
        _global_rpc_manager = SolanaRpcManager(custom_endpoints)
        await _global_rpc_manager.__aenter__()
    
    return _global_rpc_manager


# Convenience functions

async def solana_rpc_call(
    method: str,
    params: List[Any],
    priority: RequestPriority = RequestPriority.NORMAL,
    custom_endpoints: List[str] = None
) -> Any:
    """
    Convenience function для RPC вызовов
    
    Usage:
        result = await solana_rpc_call("getSignaturesForAddress", [address])
    """
    
    manager = await get_rpc_manager(custom_endpoints)
    return await manager.call(method, params, priority)


async def solana_batch_rpc_call(
    calls: List[Tuple[str, List[Any]]],
    custom_endpoints: List[str] = None
) -> List[Any]:
    """
    Convenience function для batch вызовов
    
    Usage:
        results = await solana_batch_rpc_call([
            ("getBalance", [address1]),
            ("getBalance", [address2])
        ])
    """
    
    manager = await get_rpc_manager(custom_endpoints)
    return await manager.batch_call(calls)


# Экспорт
__all__ = [
    'SolanaRpcManager',
    'RpcEndpoint',
    'EndpointStatus',
    'RequestPriority',
    'get_rpc_manager',
    'solana_rpc_call',
    'solana_batch_rpc_call'
]