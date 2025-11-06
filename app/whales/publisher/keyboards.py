# app/whales/publisher/keyboards.py
"""
Inline Keyboards
"""

from typing import List, Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.whales.normalize import WhaleEvent


class KeyboardBuilder:
    """Построение inline клавиатур"""
    
    @staticmethod
    def create_whale_keyboard(
        event: WhaleEvent,
        news: List[Dict]
    ) -> InlineKeyboardMarkup:
        """Создаёт inline-клавиатуру для whale события"""
        
        buttons = []
        
        row1 = []
        
        if event.links.get("tx"):
            row1.append(InlineKeyboardButton("🔗 TX", url=event.links["tx"]))
        
        if event.links.get("from"):
            row1.append(InlineKeyboardButton("📤 FROM", url=event.links["from"]))
        
        if event.links.get("to"):
            row1.append(InlineKeyboardButton("📥 TO", url=event.links["to"]))
        
        if row1:
            buttons.append(row1)
        
        if news:
            row2 = []
            for i, n in enumerate(news[:2], 1):
                title = f"📰 Новость {i}"
                row2.append(InlineKeyboardButton(title, url=n["url"]))
            buttons.append(row2)
        
        tv_symbol = KeyboardBuilder._get_tradingview_symbol(event.asset, event.chain)
        buttons.append([
            InlineKeyboardButton(
                "📊 График TradingView",
                url=f"https://www.tradingview.com/chart/?symbol={tv_symbol}"
            )
        ])
        
        row4 = []
        
        coingecko_id = KeyboardBuilder._get_coingecko_id(event.asset)
        if coingecko_id:
            row4.append(InlineKeyboardButton(
                "📈 CoinGecko",
                url=f"https://www.coingecko.com/en/coins/{coingecko_id}"
            ))
        
        row4.append(InlineKeyboardButton(
            "💹 CMC",
            url=f"https://coinmarketcap.com/currencies/{event.asset.lower()}/"
        ))
        
        if row4:
            buttons.append(row4)
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def _get_tradingview_symbol(asset: str, chain: str) -> str:
        """Получает символ для TradingView"""
        
        if chain in ['ethereum', 'bsc', 'polygon']:
            return f"BINANCE:{asset}USDT"
        elif chain == 'solana':
            return f"RAYDIUM:{asset}USDT"
        else:
            return f"BINANCE:{asset}USDT"
    
    @staticmethod
    def _get_coingecko_id(asset: str) -> Optional[str]:
        """Получает CoinGecko ID для актива"""
        
        mapping = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "SOL": "solana",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
            "DOT": "polkadot",
            "ADA": "cardano",
            "XRP": "ripple",
            "DOGE": "dogecoin",
            "SHIB": "shiba-inu",
            "LINK": "chainlink",
            "UNI": "uniswap",
            "AAVE": "aave",
            "ARB": "arbitrum",
            "OP": "optimism"
        }
        
        return mapping.get(asset, asset.lower())


__all__ = ['KeyboardBuilder']