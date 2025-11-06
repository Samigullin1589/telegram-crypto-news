"""
Chain Rate Limiter v2.1 - Production Grade

Adaptive rate limiting для blockchain RPC endpoints с:
- Индивидуальными задержками для каждой цепи
- Экспоненциальным backoff при 429 ошибках
- Автоматическим восстановлением цепей
- Thread-safe операциями
- Специальной обработкой Solana (Helius API)
"""

import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ChainRateLimiter:
    """
    Production-grade adaptive rate limiter для блокчейн RPC endpoints
    
    Features:
    - Per-chain delay configuration
    - Exponential backoff with jitter
    - Automatic chain recovery
    - 429 error tracking and handling
    - Thread-safe async operations
    """
    
    def __init__(self):
        self.chain_stats: Dict[str, Dict[str, Any]] = {}
        self.disabled_chains: Dict[str, datetime] = {}
        self.last_request_time: Dict[str, datetime] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        
        # Chain-specific delays (seconds between requests)
        self.chain_delays = {
            'solana': 5.0,      # Helius has strict limits
            'ethereum': 2.0,
            'bsc': 2.0,
            'polygon': 2.0,
            'arbitrum': 2.0,
            'base': 2.0,
            'tron': 3.0,
            'optimism': 2.0,
            'avalanche': 2.0,
        }
        
        # Backoff configuration
        self.max_consecutive_429 = 2
        self.backoff_periods = [120, 300, 600, 1200, 1800, 3600]  # seconds
        self.current_backoff_index: Dict[str, int] = {}
        
        logger.info("🔒 [RATE_LIMITER] Chain Rate Limiter v2.1 инициализирован")
        logger.info(f"   Solana delay: {self.chain_delays['solana']}s")
        logger.info(f"   Default delay: {self.chain_delays.get('ethereum', 2.0)}s")
        logger.info(f"   Max consecutive 429s: {self.max_consecutive_429}")
    
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
                'recovery_attempts': 0,
                'last_success_time': None,
            }
            self.last_request_time[chain] = datetime.now(timezone.utc) - timedelta(seconds=10)
            self.current_backoff_index[chain] = 0
            self._locks[chain] = asyncio.Lock()
            
            logger.debug(f"[RATE_LIMITER] Initialized chain: {chain}")
    
    def is_chain_enabled(self, chain: str) -> bool:
        """
        Проверка доступности цепи
        
        Args:
            chain: Название цепи
            
        Returns:
            bool: True если цепь доступна, False если отключена
        """
        self.init_chain(chain)
        
        if chain not in self.disabled_chains:
            return True
        
        disabled_until = self.disabled_chains[chain]
        now = datetime.now(timezone.utc)
        
        if now >= disabled_until:
            logger.info(f"🔄 [RATE_LIMITER] {chain} - Попытка восстановления")
            del self.disabled_chains[chain]
            self.chain_stats[chain]['recovery_attempts'] += 1
            self.chain_stats[chain]['consecutive_429'] = 0
            return True
        
        remaining = (disabled_until - now).total_seconds()
        logger.debug(f"[RATE_LIMITER] {chain} disabled for {int(remaining)}s more")
        return False
    
    async def wait_if_needed(self, chain: str):
        """
        Ожидание перед запросом если необходимо
        
        Args:
            chain: Название цепи
        """
        self.init_chain(chain)
        
        async with self._locks[chain]:
            min_delay = self.chain_delays.get(chain, 2.0)
            
            last_request = self.last_request_time.get(chain)
            if last_request:
                elapsed = (datetime.now(timezone.utc) - last_request).total_seconds()
                delay_needed = min_delay - elapsed
                
                if delay_needed > 0:
                    logger.debug(
                        f"[RATE_LIMITER] {chain} - Waiting {delay_needed:.2f}s "
                        f"(min delay: {min_delay}s)"
                    )
                    await asyncio.sleep(delay_needed)
            
            self.last_request_time[chain] = datetime.now(timezone.utc)
            self.chain_stats[chain]['total_requests'] += 1
    
    def record_success(self, chain: str):
        """
        Регистрация успешного запроса
        
        Args:
            chain: Название цепи
        """
        if chain not in self.chain_stats:
            self.init_chain(chain)
        
        self.chain_stats[chain]['successful_requests'] += 1
        self.chain_stats[chain]['consecutive_429'] = 0
        self.chain_stats[chain]['last_success_time'] = datetime.now(timezone.utc)
        
        # Gradually reduce backoff level on success
        if self.current_backoff_index[chain] > 0:
            self.current_backoff_index[chain] = max(
                0, 
                self.current_backoff_index[chain] - 1
            )
            logger.debug(
                f"[RATE_LIMITER] {chain} - Backoff level reduced to "
                f"{self.current_backoff_index[chain]}"
            )
    
    def record_429_error(self, chain: str):
        """
        Регистрация 429 ошибки с экспоненциальным backoff
        
        Args:
            chain: Название цепи
        """
        if chain not in self.chain_stats:
            self.init_chain(chain)
        
        stats = self.chain_stats[chain]
        stats['failed_requests'] += 1
        stats['consecutive_429'] += 1
        stats['total_429_errors'] += 1
        stats['last_429_time'] = datetime.now(timezone.utc)
        
        logger.warning(
            f"⚠️ [RATE_LIMITER] {chain} - 429 error "
            f"(consecutive: {stats['consecutive_429']})"
        )
        
        # Disable chain if too many consecutive 429s
        if stats['consecutive_429'] >= self.max_consecutive_429:
            backoff_idx = min(
                self.current_backoff_index[chain],
                len(self.backoff_periods) - 1
            )
            backoff_duration = self.backoff_periods[backoff_idx]
            
            # Add jitter to prevent thundering herd
            jitter = random.uniform(0.8, 1.2)
            backoff_duration = int(backoff_duration * jitter)
            
            disabled_until = datetime.now(timezone.utc) + timedelta(seconds=backoff_duration)
            self.disabled_chains[chain] = disabled_until
            
            # Increase backoff level
            self.current_backoff_index[chain] = min(
                self.current_backoff_index[chain] + 1,
                len(self.backoff_periods) - 1
            )
            
            logger.warning(
                f"⏸️ [RATE_LIMITER] {chain} - ВРЕМЕННО ОТКЛЮЧЕН на {backoff_duration}с"
            )
            logger.warning(
                f"   Причина: {stats['consecutive_429']} последовательных 429 ошибок"
            )
            logger.warning(
                f"   Backoff level: {backoff_idx + 1}/{len(self.backoff_periods)}"
            )
            logger.info(
                f"   Восстановление: {disabled_until.strftime('%H:%M:%S UTC')}"
            )
    
    def record_other_error(self, chain: str):
        """
        Регистрация других ошибок (не 429)
        
        Args:
            chain: Название цепи
        """
        if chain not in self.chain_stats:
            self.init_chain(chain)
        
        self.chain_stats[chain]['failed_requests'] += 1
        logger.debug(f"[RATE_LIMITER] {chain} - Recorded non-429 error")
    
    def get_chain_delay(self, chain: str) -> float:
        """
        Получить текущую задержку для цепи
        
        Args:
            chain: Название цепи
            
        Returns:
            float: Задержка в секундах
        """
        return self.chain_delays.get(chain, 2.0)
    
    def set_chain_delay(self, chain: str, delay: float):
        """
        Установить задержку для цепи
        
        Args:
            chain: Название цепи
            delay: Задержка в секундах
        """
        self.chain_delays[chain] = delay
        logger.info(f"[RATE_LIMITER] {chain} delay set to {delay}s")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику rate limiter
        
        Returns:
            Dict со статистикой всех цепей
        """
        return {
            'chains': self.chain_stats.copy(),
            'disabled_chains': {
                chain: until.isoformat()
                for chain, until in self.disabled_chains.items()
            },
            'chain_delays': self.chain_delays.copy(),
        }
    
    def get_chain_stats(self, chain: str) -> Dict[str, Any]:
        """
        Получить статистику конкретной цепи
        
        Args:
            chain: Название цепи
            
        Returns:
            Dict со статистикой цепи
        """
        self.init_chain(chain)
        
        stats = self.chain_stats[chain].copy()
        stats['is_enabled'] = self.is_chain_enabled(chain)
        stats['current_delay'] = self.get_chain_delay(chain)
        
        if chain in self.disabled_chains:
            disabled_until = self.disabled_chains[chain]
            remaining = (disabled_until - datetime.now(timezone.utc)).total_seconds()
            stats['disabled_for'] = max(0, int(remaining))
        
        return stats
    
    def print_stats(self):
        """Вывести детальную статистику в лог"""
        logger.info("\n📊 [RATE_LIMITER] Статистика:")
        
        if not self.chain_stats:
            logger.info("   Нет данных")
            return
        
        for chain, stats in self.chain_stats.items():
            # Determine status
            status = "✅ Active"
            if chain in self.disabled_chains:
                until = self.disabled_chains[chain]
                remaining = (until - datetime.now(timezone.utc)).total_seconds()
                status = f"⏸️ Disabled ({int(remaining)}s remaining)"
            
            # Calculate success rate
            success_rate = 0.0
            if stats['total_requests'] > 0:
                success_rate = (stats['successful_requests'] / stats['total_requests']) * 100
            
            # Log chain info
            logger.info(f"\n{chain.upper()}:")
            logger.info(f"  Status: {status}")
            logger.info(f"  Delay: {self.chain_delays.get(chain, 2.0)}s")
            logger.info(
                f"  Requests: {stats['total_requests']} "
                f"(✅ {stats['successful_requests']} / ❌ {stats['failed_requests']})"
            )
            logger.info(f"  Success Rate: {success_rate:.1f}%")
            logger.info(
                f"  429 Errors: {stats['total_429_errors']} "
                f"(Current streak: {stats['consecutive_429']})"
            )
            logger.info(f"  Recovery Attempts: {stats['recovery_attempts']}")
            
            if stats['last_success_time']:
                elapsed = (datetime.now(timezone.utc) - stats['last_success_time']).total_seconds()
                logger.info(f"  Last Success: {int(elapsed)}s ago")
    
    def reset_chain(self, chain: str):
        """
        Сброс статистики и состояния цепи
        
        Args:
            chain: Название цепи
        """
        if chain in self.disabled_chains:
            del self.disabled_chains[chain]
        
        if chain in self.chain_stats:
            self.chain_stats[chain]['consecutive_429'] = 0
            self.current_backoff_index[chain] = 0
        
        logger.info(f"[RATE_LIMITER] {chain} - Статистика сброшена")
    
    def reset_all(self):
        """Сброс всей статистики"""
        self.disabled_chains.clear()
        for chain in self.chain_stats:
            self.chain_stats[chain]['consecutive_429'] = 0
            self.current_backoff_index[chain] = 0
        
        logger.info("[RATE_LIMITER] Вся статистика сброшена")