# app/chains/evm/parser_improved.py
"""
УЛУЧШЕННЫЙ EVM CHAIN PARSER

Полная реализация парсинга с:
- ABI декодированием Swap events
- Реальными ценами токенов
- Batch обработкой
- Error handling
- Rate limiting
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from web3 import Web3

from app.chains.base import ChainBase, ChainType, TransactionEvent, create_transaction_event
from app.chains.evm.abi_decoder import abi_decoder, token_cache


class EVMChainImproved(ChainBase):
    """
    Улучшенный EVM chain parser
    
    Новые возможности:
    - Полное декодирование Swap events
    - Автоматическое получение token decimals
    - Batch запросы для оптимизации
    - Retry логика с exponential backoff
    """
    
    def __init__(
        self, 
        name: str,
        rpc_urls: List[str],
        explorer_api_url: str,
        explorer_api_key: Optional[str] = None,
        native_token: str = "ETH",
        chain_id: int = 1
    ):
        super().__init__(rpc_urls, explorer_api_key)
        
        self.chain_type = ChainType.EVM
        self.name = name
        self.native_token = native_token
        self.chain_id = chain_id
        self.explorer_api_url = explorer_api_url
        
        # Web3 instance
        self.w3 = Web3(Web3.HTTPProvider(self.get_rpc_url()))
        
        # DEXes будут установлены в наследниках
        self.known_dexes: Dict[str, str] = {}
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.2
    
    # ========================================================================
    # MAIN METHODS (IMPROVED)
    # ========================================================================
    
    async def parse_transaction(self, tx_hash: str) -> Optional[TransactionEvent]:
        """
        Парсит EVM транзакцию с полным декодированием
        
        Args:
            tx_hash: Transaction hash (0x...)
        
        Returns:
            TransactionEvent или None
        """
        
        try:
            # Retry логика
            max_retries = 3
            retry_delay = 1
            
            for attempt in range(max_retries):
                try:
                    # Получаем transaction и receipt
                    tx, receipt = await asyncio.gather(
                        self._get_transaction(tx_hash),
                        self._get_transaction_receipt(tx_hash)
                    )
                    
                    if tx and receipt:
                        break
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
            
            if not tx or not receipt:
                return None
            
            # Проверяем успешность
            if receipt.get("status") != 1:
                return None
            
            # Определяем DEX
            to_address = tx.get("to", "").lower()
            dex_name = self.detect_dex(to_address)
            
            if not dex_name:
                # Не DEX транзакция
                return None
            
            # Парсим swap events из logs с ABI декодированием
            swap_data = await self._parse_swap_from_logs_improved(receipt.get("logs", []))
            
            if not swap_data:
                return None
            
            # Получаем timestamp
            block = await self._get_block(tx.get("blockNumber"))
            timestamp = datetime.fromtimestamp(block.get("timestamp", 0)) if block else datetime.utcnow()
            
            # Создаём событие
            event = create_transaction_event(
                chain=self.name,
                tx_hash=tx_hash,
                block_number=int(tx.get("blockNumber", 0), 16),
                from_address=tx.get("from", ""),
                to_address=to_address,
                dex_name=dex_name,
                dex_address=to_address,
                token_in=swap_data['token_in'],
                token_out=swap_data['token_out'],
                amount_in=swap_data['amount_in'],
                amount_out=swap_data['amount_out'],
                amount_in_usd=swap_data['amount_in_usd'],
                amount_out_usd=swap_data['amount_out_usd'],
                timestamp=timestamp,
                event_type="swap",
                gas_used=int(receipt.get("gasUsed", "0"), 16),
                success=True,
                raw_data={
                    "tx": tx,
                    "receipt": receipt,
                    "token_in_symbol": swap_data.get('token_in_symbol', ''),
                    "token_out_symbol": swap_data.get('token_out_symbol', '')
                }
            )
            
            return event
        
        except Exception as e:
            print(f"❌ Error parsing {self.name} transaction: {e}")
            return None
    
    async def _parse_swap_from_logs_improved(self, logs: List[Dict]) -> Optional[Dict]:
        """
        Улучшенный парсинг swap events с ABI декодером
        """
        
        try:
            swap_data = abi_decoder.parse_swap_from_logs(logs)
            
            if not swap_data:
                return None
            
            # Получаем информацию о токенах
            token_in_info = token_cache.get_token_info(swap_data['token_in'])
            token_out_info = token_cache.get_token_info(swap_data['token_out'])
            
            # Если информации нет в кэше, пробуем получить из chain
            if token_in_info['symbol'].startswith('TOKEN_'):
                info = await token_cache.fetch_token_info_from_chain(
                    swap_data['token_in'],
                    self.get_rpc_url()
                )
                if info:
                    token_in_info = info
            
            if token_out_info['symbol'].startswith('TOKEN_'):
                info = await token_cache.fetch_token_info_from_chain(
                    swap_data['token_out'],
                    self.get_rpc_url()
                )
                if info:
                    token_out_info = info
            
            # Конвертируем amounts
            amount_in = abi_decoder.convert_amount_with_decimals(
                swap_data['amount_in'],
                token_in_info['decimals']
            )
            
            amount_out = abi_decoder.convert_amount_with_decimals(
                swap_data['amount_out'],
                token_out_info['decimals']
            )
            
            # Получаем цены токенов
            token_in_price = await self._get_token_price_async(token_in_info['symbol'])
            token_out_price = await self._get_token_price_async(token_out_info['symbol'])
            
            amount_in_usd = amount_in * token_in_price
            amount_out_usd = amount_out * token_out_price
            
            return {
                "token_in": swap_data['token_in'],
                "token_out": swap_data['token_out'],
                "amount_in": amount_in,
                "amount_out": amount_out,
                "amount_in_usd": amount_in_usd,
                "amount_out_usd": amount_out_usd,
                "token_in_symbol": token_in_info['symbol'],
                "token_out_symbol": token_out_info['symbol']
            }
        
        except Exception as e:
            print(f"❌ Error in improved swap parsing: {e}")
            return None
    
    async def _get_token_price_async(self, symbol: str) -> float:
        """
        Асинхронно получает цену токена
        
        Источники (в порядке приоритета):
        1. CoinGecko API
        2. Binance API
        3. Fallback prices
        """
        
        try:
            # Попытка 1: CoinGecko
            price = await self._fetch_price_coingecko(symbol)
            if price:
                return price
            
            # Попытка 2: Binance
            price = await self._fetch_price_binance(symbol)
            if price:
                return price
        
        except Exception:
            pass
        
        # Fallback
        from app import settings
        return settings.FALLBACK_PRICES.get(symbol, 1.0)
    
    async def _fetch_price_coingecko(self, symbol: str) -> Optional[float]:
        """Получает цену с CoinGecko"""
        
        # Маппинг символов в CoinGecko IDs
        symbol_to_id = {
            "WETH": "weth",
            "ETH": "ethereum",
            "USDC": "usd-coin",
            "USDT": "tether",
            "DAI": "dai",
            "WBTC": "wrapped-bitcoin",
            "BTC": "bitcoin"
        }
        
        coin_id = symbol_to_id.get(symbol)
        if not coin_id:
            return None
        
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if coin_id in data and "usd" in data[coin_id]:
                            return data[coin_id]["usd"]
        
        except Exception:
            pass
        
        return None
    
    async def _fetch_price_binance(self, symbol: str) -> Optional[float]:
        """Получает цену с Binance"""
        
        try:
            pair = f"{symbol}USDT"
            url = f"https://api.binance.com/api/v3/ticker/price"
            params = {"symbol": pair}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return float(data.get("price", 0))
        
        except Exception:
            pass
        
        return None
    
    # ========================================================================
    # BATCH OPERATIONS (IMPROVED)
    # ========================================================================
    
    async def parse_transactions_batch_improved(
        self,
        tx_hashes: List[str],
        max_concurrent: int = 10
    ) -> List[TransactionEvent]:
        """
        Оптимизированный batch парсинг с контролем concurrency
        
        Args:
            tx_hashes: Список транзакций
            max_concurrent: Максимум одновременных запросов
        
        Returns:
            Список событий
        """
        
        events = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def parse_with_semaphore(tx_hash):
            async with semaphore:
                return await self.parse_transaction(tx_hash)
        
        tasks = [parse_with_semaphore(tx_hash) for tx_hash in tx_hashes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, TransactionEvent):
                events.append(result)
            elif isinstance(result, Exception):
                print(f"⚠️  Batch parsing error: {result}")
        
        return events
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    
    async def _rate_limit(self):
        """Применяет rate limiting"""
        
        import time
        
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    # ========================================================================
    # RPC METHODS (WITH RATE LIMITING)
    # ========================================================================
    
    async def _get_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Получает транзакцию с rate limiting"""
        await self._rate_limit()
        return await self.call_rpc_with_fallback("eth_getTransactionByHash", [tx_hash])
    
    async def _get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Получает receipt с rate limiting"""
        await self._rate_limit()
        return await self.call_rpc_with_fallback("eth_getTransactionReceipt", [tx_hash])
    
    async def _get_block(self, block_number: any) -> Optional[Dict]:
        """Получает блок с rate limiting"""
        await self._rate_limit()
        return await self.call_rpc_with_fallback("eth_getBlockByNumber", [block_number, False])


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    async def test():
        print("🧪 Testing Improved EVM Parser\n")
        
        # Создаём instance
        parser = EVMChainImproved(
            name="ethereum",
            rpc_urls=["https://eth.llamarpc.com"],
            explorer_api_url="https://api.etherscan.io/api",
            native_token="ETH",
            chain_id=1
        )
        
        parser.known_dexes = {
            "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2"
        }
        
        # Тестовая транзакция (Uniswap V2 swap)
        test_tx = "0x..."  # Вставить реальный tx hash
        
        print(f"Парсим транзакцию: {test_tx}\n")
        
        event = await parser.parse_transaction(test_tx)
        
        if event:
            print("✅ Транзакция успешно распарсена:")
            print(f"   DEX: {event.dex_name}")
            print(f"   Token In: {event.token_in}")
            print(f"   Token Out: {event.token_out}")
            print(f"   Amount In: {event.amount_in} (${event.amount_in_usd:,.2f})")
            print(f"   Amount Out: {event.amount_out} (${event.amount_out_usd:,.2f})")
        else:
            print("❌ Не удалось распарсить транзакцию")
        
        print("\n✅ Test complete!")
    
    asyncio.run(test())