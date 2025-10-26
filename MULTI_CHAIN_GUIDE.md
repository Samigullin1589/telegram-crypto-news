# 🌐 MULTI-CHAIN SUPPORT - Complete Guide

## 🎯 Что создано?

**Multi-Chain System** - универсальная система для мониторинга **6 блокчейнов** и **15+ DEXes**.

---

## 📦 ПОДДЕРЖИВАЕМЫЕ CHAINS

### ⚡ Solana
- **Type:** Non-EVM (Rust)
- **Native Token:** SOL
- **DEXes:**
  - Raydium AMM
  - Raydium CLMM
  - Orca Whirlpools
  - Jupiter Aggregator

### 🔷 Base (Coinbase L2)
- **Type:** EVM (Optimistic Rollup)
- **Native Token:** ETH
- **DEXes:**
  - Uniswap V3
  - Aerodrome
  - BaseSwap

### 🟣 Arbitrum One
- **Type:** EVM (Optimistic Rollup)
- **Native Token:** ETH
- **DEXes:**
  - Uniswap V3
  - Camelot
  - Sushiswap
  - GMX

### 🔴 Optimism
- **Type:** EVM (Optimistic Rollup)
- **Native Token:** ETH
- **DEXes:**
  - Uniswap V3
  - Velodrome
  - Sushiswap

### 🟠 Avalanche C-Chain
- **Type:** EVM
- **Native Token:** AVAX
- **DEXes:**
  - Trader Joe
  - Pangolin
  - Sushiswap

### ⭕ Polygon PoS
- **Type:** EVM (Sidechain)
- **Native Token:** MATIC
- **DEXes:**
  - Uniswap V3
  - QuickSwap
  - Sushiswap
  - Balancer

---

## 🚀 QUICK START

### Шаг 1: Инициализация

```python
from app.chains import initialize_all_chains, unified_api

# Инициализация всех chains
initialize_all_chains(
    api_keys={
        "base": "YOUR_BASESCAN_KEY",
        "arbitrum": "YOUR_ARBISCAN_KEY",
        "optimism": "YOUR_OPTIMISM_KEY",
        "avalanche": "YOUR_SNOWTRACE_KEY",
        "polygon": "YOUR_POLYGONSCAN_KEY"
    }
)

# Проверка
from app.chains import get_supported_chains
print(get_supported_chains())
# ['solana', 'base', 'arbitrum', 'optimism', 'avalanche', 'polygon']
```

### Шаг 2: Парсинг транзакций

```python
# Solana transaction
event = await unified_api.parse_transaction(
    "solana",
    "5x7jG..."  # Solana signature
)

# Base transaction
event = await unified_api.parse_transaction(
    "base",
    "0x123..."  # Transaction hash
)

# Результат - нормализованный TransactionEvent
print(event.chain)          # "base"
print(event.dex_name)       # "Uniswap V3"
print(event.amount_out_usd) # 15000.0
```

### Шаг 3: Cross-Chain Analysis

```python
# Анализ кошелька на ВСЕХ chains
analysis = await unified_api.analyze_wallet_cross_chain("0xABC...")

print(f"Active on: {analysis['active_chains']}")
# ['ethereum', 'base', 'arbitrum']

print(f"Total volume: ${analysis['total_volume_usd']:.0f}")
# Total volume: $1,250,000

print(f"Favorite DEXes: {analysis['favorite_dexes']}")
# {'Uniswap V3': 45, 'Raydium': 12, 'Aerodrome': 8}

print(f"Cross-chain tokens: {analysis['cross_chain_tokens']}")
# ['USDC', 'WETH']  # Покупал на разных chains

print(f"Risk score: {analysis['risk_score']}/100")
# Risk score: 85/100  # Опытный трейдер
```

---

## 📚 API REFERENCE

### UnifiedChainAPI

#### parse_transaction()
```python
event = await unified_api.parse_transaction(chain, tx_hash)

# Returns: TransactionEvent or None
# - chain: str - Название блокчейна
# - tx_hash: str - Hash транзакции
```

#### get_token_price()
```python
price = await unified_api.get_token_price(chain, token_address)

# Returns: float (USD) or None
# - chain: str
# - token_address: str
```

#### get_wallet_balance()
```python
balance = await unified_api.get_wallet_balance(chain, wallet, token)

# Returns: float
# - chain: str
# - wallet: str
# - token: str (optional, None = native token)
```

#### monitor_wallet_all_chains()
```python
events = await unified_api.monitor_wallet_all_chains(wallet_address)

# Returns: Dict[str, List[TransactionEvent]]
# {
#     "ethereum": [...],
#     "solana": [...],
#     ...
# }
```

#### analyze_wallet_cross_chain()
```python
analysis = await unified_api.analyze_wallet_cross_chain(wallet_address)

# Returns: Dict
# {
#     "total_volume_usd": float,
#     "active_chains": List[str],
#     "favorite_dexes": Dict[str, int],
#     "cross_chain_tokens": List[str],
#     "risk_score": int,
#     "is_sophisticated": bool
# }
```

---

## 🎯 USE CASES

### Use Case 1: Мониторинг кита на всех chains

```python
import asyncio
from app.chains import unified_api

async def monitor_whale(wallet_address):
    """Мониторит активность кита на всех chains"""
    
    print(f"🐋 Monitoring whale: {wallet_address}")
    
    # Получаем события на всех chains
    all_events = await unified_api.monitor_wallet_all_chains(wallet_address)
    
    # Анализируем
    for chain, events in all_events.items():
        if events:
            total_volume = sum(e.amount_out_usd for e in events)
            print(f"  {chain}: {len(events)} trades, ${total_volume:,.0f}")
    
    # Cross-chain анализ
    analysis = await unified_api.analyze_wallet_cross_chain(wallet_address)
    
    if analysis["is_sophisticated"]:
        print(f"  ⚠️ SOPHISTICATED TRADER!")
        print(f"  Active on {analysis['active_chains_count']} chains")
        print(f"  Cross-chain tokens: {analysis['cross_chain_tokens']}")

# Запуск
asyncio.run(monitor_whale("0x123..."))
```

### Use Case 2: Поиск арбитража между chains

```python
async def find_arbitrage_opportunities():
    """Ищет одинаковые токены на разных chains"""
    
    wallets = ["0xWallet1...", "0xWallet2...", ...]
    
    for wallet in wallets:
        analysis = await unified_api.analyze_wallet_cross_chain(wallet)
        
        # Если покупает одинаковый токен на разных chains - арбитраж?
        if analysis["cross_chain_tokens"]:
            print(f"🔍 Potential arbitrage: {wallet}")
            print(f"   Tokens: {analysis['cross_chain_tokens']}")
            print(f"   Chains: {analysis['active_chains']}")
```

### Use Case 3: Сравнение цен на DEXes

```python
async def compare_token_prices(token_address):
    """Сравнивает цену токена на всех chains"""
    
    chains = ["base", "arbitrum", "optimism", "polygon"]
    
    prices = {}
    
    for chain in chains:
        price = await unified_api.get_token_price(chain, token_address)
        if price:
            prices[chain] = price
    
    # Находим лучшую цену
    best_chain = min(prices, key=prices.get)
    worst_chain = max(prices, key=prices.get)
    
    spread = (prices[worst_chain] - prices[best_chain]) / prices[best_chain] * 100
    
    print(f"💰 {token_address}")
    print(f"   Best: {best_chain} @ ${prices[best_chain]:.4f}")
    print(f"   Worst: {worst_chain} @ ${prices[worst_chain]:.4f}")
    print(f"   Spread: {spread:.2f}%")
```

---

## 🔧 НАСТРОЙКА

### Добавление своих RPC

```python
# Solana с кастомными RPC
initialize_all_chains(
    solana_rpc=[
        "https://your-custom-rpc.com",
        "https://backup-rpc.com"
    ]
)
```

### Добавление explorer API keys

```python
# Для лучших rate limits
initialize_all_chains(
    api_keys={
        "base": "BASESCAN_API_KEY",
        "arbitrum": "ARBISCAN_API_KEY",
        "optimism": "OPTIMISM_API_KEY",
        "avalanche": "SNOWTRACE_API_KEY",
        "polygon": "POLYGONSCAN_API_KEY"
    }
)
```

Получить ключи:
- Base: https://basescan.org/apis
- Arbitrum: https://arbiscan.io/apis
- Optimism: https://optimistic.etherscan.io/apis
- Avalanche: https://snowtrace.io/apis
- Polygon: https://polygonscan.com/apis

---

## 🎓 ADVANCED

### Добавление своего chain

```python
from app.chains.base import ChainBase, ChainType, ChainRegistry

class MyCustomChain(ChainBase):
    def __init__(self, rpc_urls):
        super().__init__(rpc_urls)
        self.name = "my_chain"
        self.chain_type = ChainType.EVM
        self.native_token = "CUSTOM"
    
    async def parse_transaction(self, tx_hash):
        # Твоя логика
        pass
    
    async def get_token_price(self, token_address):
        # Твоя логика
        pass
    
    # ... другие методы

# Регистрация
custom_chain = MyCustomChain(["https://rpc.mychain.com"])
ChainRegistry.register("my_chain", custom_chain)
```

### Добавление своего DEX

```python
from app.chains.evm.parser import BaseChain

class MyBaseChain(BaseChain):
    def __init__(self, api_key=None):
        super().__init__(api_key)
        
        # Добавляем свой DEX
        self.known_dexes["0xYOUR_DEX_ADDRESS"] = "My DEX"
```

---

## 🧪 ТЕСТИРОВАНИЕ

### Тест парсинга

```python
import asyncio
from app.chains import initialize_all_chains, unified_api

async def test():
    initialize_all_chains()
    
    # Solana
    event = await unified_api.parse_transaction(
        "solana",
        "REAL_SOLANA_SIGNATURE"
    )
    print(f"Solana: {event}")
    
    # Base
    event = await unified_api.parse_transaction(
        "base",
        "0xREAL_BASE_TX_HASH"
    )
    print(f"Base: {event}")

asyncio.run(test())
```

### Тест cross-chain analysis

```python
async def test_cross_chain():
    initialize_all_chains()
    
    # Известный кит
    whale = "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8"  # Binance Hot Wallet
    
    analysis = await unified_api.analyze_wallet_cross_chain(whale)
    
    print(f"Chains: {analysis['active_chains_count']}")
    print(f"Volume: ${analysis['total_volume_usd']:,.0f}")
    print(f"Risk score: {analysis['risk_score']}")

asyncio.run(test_cross_chain())
```

---

## 📊 ИНТЕГРАЦИЯ С СИСТЕМОЙ

### В scheduler

```python
# app/scheduler.py

from app.chains import initialize_all_chains, unified_api

class WhaleScheduler:
    def __init__(self):
        # Инициализация multi-chain
        initialize_all_chains(
            api_keys={
                "base": settings.BASESCAN_API_KEY,
                "arbitrum": settings.ARBISCAN_API_KEY,
                # ...
            }
        )
    
    async def monitor_cycle(self):
        """Расширенный цикл мониторинга"""
        
        # Мониторим кошельки на ВСЕХ chains
        for wallet_data in self.wallet_db.get_active_wallets():
            address = wallet_data["address"]
            
            # Cross-chain мониторинг
            events = await unified_api.monitor_wallet_all_chains(address)
            
            # Обрабатываем события со всех chains
            for chain, chain_events in events.items():
                for event in chain_events:
                    await self.process_whale_event(event)
```

---

## 🎉 ПОЗДРАВЛЯЮ!

Теперь система мониторит **6 блокчейнов** и **15+ DEXes**!

### Что дальше:

1. **Добавить больше chains** - zkSync, Blast, Fantom
2. **Улучшить парсинг** - более точное извлечение amounts
3. **Кэширование цен** - Redis для token prices
4. **WebSocket мониторинг** - real-time events
5. **ML для cross-chain паттернов** - автоматическое обнаружение

**Система готова к работе! 🚀**