# app/whales/monitor/solana_components/solana_transaction_parser.py
"""
Solana Transaction Parser
Парсинг Solana транзакций в whale события
"""

import logging
from typing import Optional
from datetime import datetime

from app.config import config
from app.whales.normalize import WhaleEvent
from app.whales.monitor.dex_detector import DEXDetector
from .solana_config import SolanaConfig
from .solana_price_provider import SolanaPriceProvider

logger = logging.getLogger(__name__)


class SolanaTransactionParser:
    """Парсер Solana транзакций"""
    
    def __init__(self, dex_detector: DEXDetector, price_provider: SolanaPriceProvider):
        """
        Args:
            dex_detector: Детектор DEX
            price_provider: Провайдер цен
        """
        self.dex_detector = dex_detector
        self.price_provider = price_provider
    
    async def parse_transaction(self, tx_data: dict) -> Optional[WhaleEvent]:
        """
        Парсинг Solana транзакции
        
        Args:
            tx_data: Данные транзакции из RPC
            
        Returns:
            WhaleEvent или None
        """
        try:
            # Проверка на ошибку в транзакции
            meta = tx_data.get("meta", {})
            
            if meta.get("err"):
                logger.debug("🚫 [SOLANA PARSE] Транзакция с ошибкой, пропускаю")
                return None
            
            # Извлечение данных транзакции
            transaction = tx_data.get("transaction", {})
            message = transaction.get("message", {})
            
            # Анализ изменений балансов
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])
            
            if not pre_balances or not post_balances:
                return None
            
            # Поиск максимального изменения баланса
            transfer_info = self._find_max_transfer(pre_balances, post_balances)
            
            if not transfer_info:
                return None
            
            # Конвертация в SOL
            amount_lamports = transfer_info["amount"]
            amount_sol = amount_lamports / (10 ** SolanaConfig.DECIMALS)
            
            # Минимальный порог для предварительной фильтрации
            if amount_sol < 10:  # Меньше 10 SOL
                return None
            
            # Получение реальной цены SOL
            sol_price = await self.price_provider.get_token_price("SOL")
            amount_usd = amount_sol * sol_price
            
            # Получение адресов
            account_keys = message.get("accountKeys", [])
            
            from_addr = self._get_account_address(
                account_keys, 
                transfer_info["from_index"]
            )
            to_addr = self._get_account_address(
                account_keys,
                transfer_info["to_index"]
            )
            
            # Получение времени блока
            block_time = tx_data.get("blockTime")
            tx_time = datetime.utcfromtimestamp(block_time) if block_time else datetime.utcnow()
            
            # Детекция DEX
            dex = self._detect_dex(message) or None
            
            # Получение подписи
            signatures = transaction.get("signatures", [])
            tx_hash = signatures[0] if signatures else ""
            
            # Создание события
            event = WhaleEvent(
                chain="solana",
                asset="SOL",
                from_address=from_addr,
                to_address=to_addr,
                amount_native=amount_sol,
                amount_usd=amount_usd,
                price_usd=sol_price,
                tx_hash=tx_hash,
                direction="unknown",
                phase="execution",
                dex=dex,
                is_internal=False,
                is_bridge=False,
                is_reorg=False,
                tx_time_utc=tx_time
            )
            
            logger.debug(
                f"✅ [SOLANA PARSE] SOL: {amount_sol:.4f} "
                f"(${amount_usd:,.0f}) от {from_addr[:16]}... к {to_addr[:16]}..."
            )
            
            return event
        
        except Exception as e:
            logger.debug(f"⚠️ [SOLANA PARSE] Ошибка парсинга: {e}")
            return None
    
    def _find_max_transfer(
        self,
        pre_balances: list,
        post_balances: list
    ) -> Optional[dict]:
        """
        Поиск максимального перевода в транзакции
        
        Args:
            pre_balances: Балансы до транзакции
            post_balances: Балансы после транзакции
            
        Returns:
            Dict с информацией о переводе или None
        """
        max_amount = 0
        from_index = -1
        to_index = -1
        
        for i in range(min(len(pre_balances), len(post_balances))):
            change = post_balances[i] - pre_balances[i]
            abs_change = abs(change)
            
            if abs_change > max_amount:
                max_amount = abs_change
                
                if change < 0:
                    # Баланс уменьшился - это отправитель
                    from_index = i
                elif change > 0:
                    # Баланс увеличился - это получатель
                    to_index = i
        
        if max_amount == 0:
            return None
        
        # Если нашли только отправителя или получателя, ищем парный индекс
        if from_index >= 0 and to_index < 0:
            # Ищем получателя
            for i in range(len(post_balances)):
                if i != from_index and post_balances[i] > pre_balances[i]:
                    to_index = i
                    break
        
        elif to_index >= 0 and from_index < 0:
            # Ищем отправителя
            for i in range(len(pre_balances)):
                if i != to_index and post_balances[i] < pre_balances[i]:
                    from_index = i
                    break
        
        if from_index < 0 or to_index < 0:
            return None
        
        return {
            "amount": max_amount,
            "from_index": from_index,
            "to_index": to_index
        }
    
    def _get_account_address(
        self,
        account_keys: list,
        index: int
    ) -> str:
        """
        Получение адреса аккаунта по индексу
        
        Args:
            account_keys: Список ключей аккаунтов
            index: Индекс аккаунта
            
        Returns:
            Адрес или "unknown"
        """
        if 0 <= index < len(account_keys):
            account = account_keys[index]
            
            if isinstance(account, dict):
                return account.get("pubkey", "unknown")
            elif isinstance(account, str):
                return account
        
        return "unknown"
    
    def _detect_dex(self, message: dict) -> Optional[str]:
        """
        Детекция DEX в транзакции
        
        Args:
            message: Message часть транзакции
            
        Returns:
            Название DEX или None
        """
        # Проверка инструкций на наличие DEX программ
        instructions = message.get("instructions", [])
        
        for instruction in instructions:
            program_id = instruction.get("programId")
            
            if program_id and SolanaConfig.is_dex_program(program_id):
                dex_name = SolanaConfig.get_dex_name(program_id)
                logger.debug(f"🔍 [SOLANA PARSE] Обнаружен DEX: {dex_name}")
                return dex_name
        
        # Fallback на dex_detector
        account_keys = message.get("accountKeys", [])
        
        if account_keys and self.dex_detector:
            addresses = [
                self._get_account_address(account_keys, i)
                for i in range(len(account_keys))
            ]
            
            dex = self.dex_detector.detect_solana_dex(addresses)
            if dex:
                return dex
        
        return None