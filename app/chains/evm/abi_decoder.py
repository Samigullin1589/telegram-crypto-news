# app/chains/evm/abi_decoder.py
"""
ABI DECODER для EVM chains

Декодирование Swap events, Transfer events и других событий DEX
"""

from typing import Dict, List, Optional, Tuple
from eth_abi import decode
from web3 import Web3


class ABIDecoder:
    """Декодер ABI для EVM событий"""
    
    # Event signatures
    SWAP_V2_TOPIC = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
    SWAP_V3_TOPIC = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    
    # ABI типы для декодирования
    SWAP_V2_TYPES = ['uint256', 'uint256', 'uint256', 'uint256']
    SWAP_V3_TYPES = ['int256', 'int256', 'uint160', 'uint128', 'int24']
    TRANSFER_TYPES = ['address', 'address', 'uint256']
    
    def __init__(self):
        self.w3 = Web3()
    
    def decode_swap_v2(self, log: Dict) -> Optional[Dict]:
        """
        Декодирует Uniswap V2 Swap event
        
        Event signature:
        Swap(address indexed sender, uint amount0In, uint amount1In, uint amount0Out, uint amount1Out, address indexed to)
        
        Returns:
            {
                "amount0_in": int,
                "amount1_in": int,
                "amount0_out": int,
                "amount1_out": int,
                "sender": str,
                "to": str
            }
        """
        
        topics = log.get('topics', [])
        data = log.get('data', '0x')
        
        if not topics or topics[0].lower() != self.SWAP_V2_TOPIC.lower():
            return None
        
        try:
            # Декодируем indexed параметры
            sender = '0x' + topics[1][-40:]  # последние 20 байт = адрес
            to = '0x' + topics[2][-40:]
            
            # Декодируем data (amount0In, amount1In, amount0Out, amount1Out)
            decoded = decode(self.SWAP_V2_TYPES, bytes.fromhex(data[2:]))
            
            return {
                "amount0_in": decoded[0],
                "amount1_in": decoded[1],
                "amount0_out": decoded[2],
                "amount1_out": decoded[3],
                "sender": sender.lower(),
                "to": to.lower(),
                "dex_version": "v2"
            }
        
        except Exception as e:
            print(f"⚠️  Ошибка декодирования Swap V2: {e}")
            return None
    
    def decode_swap_v3(self, log: Dict) -> Optional[Dict]:
        """
        Декодирует Uniswap V3 Swap event
        
        Event signature:
        Swap(address indexed sender, address indexed recipient, int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)
        
        Returns:
            {
                "amount0": int,
                "amount1": int,
                "sender": str,
                "recipient": str,
                "sqrt_price_x96": int,
                "liquidity": int,
                "tick": int
            }
        """
        
        topics = log.get('topics', [])
        data = log.get('data', '0x')
        
        if not topics or topics[0].lower() != self.SWAP_V3_TOPIC.lower():
            return None
        
        try:
            # Indexed параметры
            sender = '0x' + topics[1][-40:]
            recipient = '0x' + topics[2][-40:]
            
            # Data параметры
            decoded = decode(self.SWAP_V3_TYPES, bytes.fromhex(data[2:]))
            
            return {
                "amount0": decoded[0],
                "amount1": decoded[1],
                "sender": sender.lower(),
                "recipient": recipient.lower(),
                "sqrt_price_x96": decoded[2],
                "liquidity": decoded[3],
                "tick": decoded[4],
                "dex_version": "v3"
            }
        
        except Exception as e:
            print(f"⚠️  Ошибка декодирования Swap V3: {e}")
            return None
    
    def decode_transfer(self, log: Dict) -> Optional[Dict]:
        """
        Декодирует ERC20 Transfer event
        
        Event signature:
        Transfer(address indexed from, address indexed to, uint256 value)
        """
        
        topics = log.get('topics', [])
        data = log.get('data', '0x')
        
        if not topics or topics[0].lower() != self.TRANSFER_TOPIC.lower():
            return None
        
        try:
            from_addr = '0x' + topics[1][-40:]
            to_addr = '0x' + topics[2][-40:]
            
            # Value в data
            value = int(data, 16) if data != '0x' else 0
            
            return {
                "from": from_addr.lower(),
                "to": to_addr.lower(),
                "value": value,
                "token": log.get('address', '').lower()
            }
        
        except Exception as e:
            print(f"⚠️  Ошибка декодирования Transfer: {e}")
            return None
    
    def parse_swap_from_logs(self, logs: List[Dict]) -> Optional[Dict]:
        """
        Парсит swap данные из списка логов
        
        Returns:
            {
                "token_in": str,
                "token_out": str,
                "amount_in": float,
                "amount_out": float,
                "token_in_decimals": int,
                "token_out_decimals": int
            }
        """
        
        # Сначала ищем Swap events
        swap_data = None
        
        for log in logs:
            # Пробуем V3
            swap_data = self.decode_swap_v3(log)
            if swap_data:
                break
            
            # Пробуем V2
            swap_data = self.decode_swap_v2(log)
            if swap_data:
                break
        
        if not swap_data:
            return None
        
        # Теперь ищем Transfer events чтобы определить токены
        transfers = []
        for log in logs:
            transfer = self.decode_transfer(log)
            if transfer:
                transfers.append(transfer)
        
        if not transfers or len(transfers) < 2:
            return None
        
        # Определяем token_in и token_out по направлению трансферов
        # Token_in = transfer TO pool/router
        # Token_out = transfer FROM pool/router
        
        router_addresses = self._get_router_addresses(logs)
        
        token_in = None
        token_out = None
        amount_in = 0
        amount_out = 0
        
        for transfer in transfers:
            # Token_in идёт на роутер
            if transfer['to'] in router_addresses:
                token_in = transfer['token']
                amount_in = transfer['value']
            
            # Token_out идёт с роутера
            elif transfer['from'] in router_addresses:
                token_out = transfer['token']
                amount_out = transfer['value']
        
        if not token_in or not token_out:
            # Fallback: берём первые два трансфера
            token_in = transfers[0]['token']
            token_out = transfers[1]['token']
            amount_in = transfers[0]['value']
            amount_out = transfers[1]['value']
        
        return {
            "token_in": token_in,
            "token_out": token_out,
            "amount_in": amount_in,
            "amount_out": amount_out,
            "token_in_decimals": 18,  # По умолчанию, нужно будет получать реальные
            "token_out_decimals": 18,
            "swap_type": swap_data.get('dex_version', 'v2')
        }
    
    def _get_router_addresses(self, logs: List[Dict]) -> set:
        """Извлекает адреса роутеров/пулов из логов"""
        addresses = set()
        
        for log in logs:
            addr = log.get('address', '').lower()
            if addr:
                addresses.add(addr)
        
        return addresses
    
    def convert_amount_with_decimals(self, amount: int, decimals: int) -> float:
        """Конвертирует amount из wei в читаемый формат"""
        return amount / (10 ** decimals)


# ============================================================================
# TOKEN INFO CACHE
# ============================================================================

class TokenInfoCache:
    """Кэш информации о токенах (decimals, symbols)"""
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        
        # Известные токены
        self._init_known_tokens()
    
    def _init_known_tokens(self):
        """Инициализирует известные токены"""
        
        known = {
            # Ethereum
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": {"symbol": "WETH", "decimals": 18},
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": {"symbol": "USDC", "decimals": 6},
            "0xdac17f958d2ee523a2206206994597c13d831ec7": {"symbol": "USDT", "decimals": 6},
            "0x6b175474e89094c44da98b954eedeac495271d0f": {"symbol": "DAI", "decimals": 18},
            "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": {"symbol": "WBTC", "decimals": 8},
            
            # BSC
            "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c": {"symbol": "WBNB", "decimals": 18},
            "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": {"symbol": "USDC", "decimals": 18},
            "0x55d398326f99059ff775485246999027b3197955": {"symbol": "USDT", "decimals": 18},
        }
        
        for address, info in known.items():
            self.cache[address.lower()] = info
    
    def get_token_info(self, address: str) -> Dict:
        """Получает информацию о токене"""
        
        address = address.lower()
        
        if address in self.cache:
            return self.cache[address]
        
        # Если токена нет в кэше, возвращаем defaults
        return {
            "symbol": f"TOKEN_{address[:6]}",
            "decimals": 18
        }
    
    def set_token_info(self, address: str, symbol: str, decimals: int):
        """Сохраняет информацию о токене"""
        
        self.cache[address.lower()] = {
            "symbol": symbol,
            "decimals": decimals
        }
    
    async def fetch_token_info_from_chain(
        self,
        address: str,
        rpc_url: str
    ) -> Optional[Dict]:
        """
        Получает информацию о токене из блокчейна
        
        Вызывает:
        - decimals()
        - symbol()
        """
        
        from web3 import Web3
        
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # ABI для ERC20
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "symbol",
                    "outputs": [{"name": "", "type": "string"}],
                    "type": "function"
                }
            ]
            
            contract = w3.eth.contract(address=address, abi=erc20_abi)
            
            decimals = contract.functions.decimals().call()
            symbol = contract.functions.symbol().call()
            
            info = {
                "symbol": symbol,
                "decimals": decimals
            }
            
            # Сохраняем в кэш
            self.set_token_info(address, symbol, decimals)
            
            return info
        
        except Exception as e:
            print(f"⚠️  Ошибка получения token info: {e}")
            return None


# ============================================================================
# CONVENIENCE
# ============================================================================

# Глобальные instances
abi_decoder = ABIDecoder()
token_cache = TokenInfoCache()


def decode_swap_event(logs: List[Dict]) -> Optional[Dict]:
    """
    Convenience function для декодирования swap
    
    Usage:
        swap_data = decode_swap_event(receipt['logs'])
        if swap_data:
            print(f"Swapped {swap_data['amount_in']} {swap_data['token_in']} for {swap_data['amount_out']} {swap_data['token_out']}")
    """
    return abi_decoder.parse_swap_from_logs(logs)


def get_token_info(address: str) -> Dict:
    """
    Convenience function для получения token info
    
    Usage:
        info = get_token_info("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
        print(f"Symbol: {info['symbol']}, Decimals: {info['decimals']}")
    """
    return token_cache.get_token_info(address)


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    # Тестовый Swap event log
    test_log_v2 = {
        "topics": [
            "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822",
            "0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d",
            "0x000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
        ],
        "data": "0x0000000000000000000000000000000000000000000000000de0b6b3a76400000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000f4240"
    }
    
    print("🧪 Testing ABI Decoder\n")
    
    decoder = ABIDecoder()
    
    result = decoder.decode_swap_v2(test_log_v2)
    
    if result:
        print("✅ Swap V2 decoded:")
        print(f"   Amount 0 In: {result['amount0_in']}")
        print(f"   Amount 1 Out: {result['amount1_out']}")
        print(f"   Sender: {result['sender']}")
    else:
        print("❌ Failed to decode")
    
    print("\n✅ Test complete!")