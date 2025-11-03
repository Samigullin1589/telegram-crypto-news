"""
WALLET VALIDATION MODULE

Проверяет активность и производительность отслеживаемых кошельков.
Удаляет неактивных и неэффективных.
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class WalletValidator:
    """
    Система валидации кошельков
    """
    
    def __init__(self):
        # Пороги для деактивации
        self.max_days_inactive = 60
        self.min_score = 30
        self.min_roi = -0.20
        
        # Кэш результатов валидации
        self.validation_cache: Dict[str, Dict] = {}
        self.cache_ttl = timedelta(hours=6)
    
    async def validate_wallet(
        self,
        address: str,
        chain: str,
        current_data: Dict
    ) -> Dict:
        """
        Валидирует кошелёк
        
        Returns:
            {
                "is_valid": bool,
                "reason": str,
                "score_update": bool,
                "new_score": int
            }
        """
        
        # Проверяем кэш
        cache_key = f"{chain}_{address}"
        if cache_key in self.validation_cache:
            cached_result, cached_at = self.validation_cache[cache_key]
            if datetime.utcnow() - cached_at < self.cache_ttl:
                return cached_result
        
        result = {
            "is_valid": True,
            "reason": "",
            "score_update": False,
            "new_score": current_data.get("score", 50),
            "warnings": []
        }
        
        # Проверка 1: Неактивность
        last_trade_str = current_data.get("last_trade_at")
        
        if last_trade_str:
            last_trade = datetime.fromisoformat(last_trade_str)
            days_inactive = (datetime.utcnow() - last_trade).days
            
            if days_inactive > self.max_days_inactive:
                result["is_valid"] = False
                result["reason"] = f"Неактивен {days_inactive} дней"
                self.validation_cache[cache_key] = (result, datetime.utcnow())
                return result
            
            # Предупреждение при приближении к лимиту
            if days_inactive > self.max_days_inactive * 0.75:
                result["warnings"].append(f"Низкая активность: {days_inactive} дней")
        else:
            result["is_valid"] = False
            result["reason"] = "Нет данных о последней сделке"
            return result
        
        # Проверка 2: Низкий скор
        score = current_data.get("score", 50)
        if score < self.min_score:
            result["is_valid"] = False
            result["reason"] = f"Низкий скор ({score})"
            self.validation_cache[cache_key] = (result, datetime.utcnow())
            return result
        
        # Предупреждение при низком скоре
        if score < self.min_score * 1.5:
            result["warnings"].append(f"Скор близок к критическому: {score}")
        
        # Проверка 3: Отрицательный ROI
        roi = current_data.get("roi_30d", 0)
        if roi < self.min_roi:
            result["is_valid"] = False
            result["reason"] = f"Плохой ROI ({roi:.1%})"
            self.validation_cache[cache_key] = (result, datetime.utcnow())
            return result
        
        # Предупреждение при низком ROI
        if roi < 0:
            result["warnings"].append(f"Отрицательный ROI: {roi:.1%}")
        
        # Проверка 4: Win rate
        win_rate = current_data.get("win_rate", 0.5)
        if win_rate < 0.40:
            result["is_valid"] = False
            result["reason"] = f"Низкий win rate ({win_rate:.1%})"
            self.validation_cache[cache_key] = (result, datetime.utcnow())
            return result
        
        # Проверка 5: Обновление скора на основе активности
        if days_inactive > 30:
            # Снижаем скор за неактивность
            penalty = int((days_inactive - 30) / 10) * 5
            new_score = max(0, score - penalty)
            
            if new_score != score:
                result["score_update"] = True
                result["new_score"] = new_score
                result["warnings"].append(f"Скор снижен из-за неактивности: {score} → {new_score}")
        
        # Проверка 6: Количество сделок
        total_trades = current_data.get("total_trades", 0)
        if total_trades < 5:
            result["warnings"].append(f"Мало сделок: {total_trades}")
        
        # Проверка 7: Объём торговли
        total_volume = current_data.get("total_volume_30d", 0)
        if total_volume < 10000:
            result["warnings"].append(f"Низкий объём торговли: ${total_volume:,.0f}")
        
        # Кэшируем результат
        self.validation_cache[cache_key] = (result, datetime.utcnow())
        
        return result
    
    async def batch_validate(
        self,
        wallets: List[Dict]
    ) -> Dict[str, Dict]:
        """
        Валидирует несколько кошельков параллельно
        
        Returns:
            {address: validation_result}
        """
        
        results = {}
        
        for wallet in wallets:
            address = wallet["address"]
            chain = wallet["chain"]
            
            validation = await self.validate_wallet(address, chain, wallet)
            results[address] = validation
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.01)
        
        return results
    
    async def validate_with_onchain_check(
        self,
        address: str,
        chain: str,
        current_data: Dict,
        session: aiohttp.ClientSession,
        explorer_api_key: str = None
    ) -> Dict:
        """
        Расширенная валидация с проверкой в блокчейне
        
        Returns:
            Результат валидации с onchain данными
        """
        
        # Базовая валидация
        result = await self.validate_wallet(address, chain, current_data)
        
        # Если уже невалидный - не проверяем onchain
        if not result["is_valid"]:
            return result
        
        # Проверяем в блокчейне
        onchain_data = await self._check_onchain_activity(
            address, chain, session, explorer_api_key
        )
        
        if onchain_data:
            # Дополнительные проверки
            tx_count = onchain_data.get("tx_count_30d", 0)
            
            if tx_count == 0:
                result["is_valid"] = False
                result["reason"] = "Нет активности в блокчейне за 30 дней"
            elif tx_count < 3:
                result["warnings"].append(f"Низкая onchain активность: {tx_count} транзакций")
            
            # Обновляем данные
            result["onchain_data"] = onchain_data
        
        return result
    
    async def _check_onchain_activity(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        api_key: str = None
    ) -> Optional[Dict]:
        """
        Проверяет активность кошелька в блокчейне
        
        Returns:
            Данные активности или None
        """
        
        if chain not in ["ethereum", "bsc", "polygon", "base", "arbitrum", "optimism"]:
            return None
        
        api_configs = {
            "ethereum": "https://api.etherscan.io/api",
            "bsc": "https://api.bscscan.com/api",
            "polygon": "https://api.polygonscan.com/api",
            "base": "https://api.basescan.org/api",
            "arbitrum": "https://api.arbiscan.io/api",
            "optimism": "https://api-optimistic.etherscan.io/api"
        }
        
        api_url = api_configs.get(chain)
        
        if not api_url or not api_key:
            return None
        
        try:
            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": 100,
                "sort": "desc",
                "apikey": api_key
            }
            
            async with session.get(api_url, params=params, timeout=30) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                
                if data.get("status") != "1":
                    return None
                
                transactions = data.get("result", [])
                
                if not transactions:
                    return {
                        "tx_count_30d": 0,
                        "last_tx_timestamp": None,
                        "is_active": False
                    }
                
                # Анализируем транзакции
                cutoff = datetime.utcnow() - timedelta(days=30)
                recent_txs = [
                    tx for tx in transactions
                    if datetime.fromtimestamp(int(tx.get("timeStamp", 0))) >= cutoff
                ]
                
                last_tx = transactions[0]
                last_tx_timestamp = datetime.fromtimestamp(int(last_tx.get("timeStamp", 0)))
                
                return {
                    "tx_count_30d": len(recent_txs),
                    "tx_count_total": len(transactions),
                    "last_tx_timestamp": last_tx_timestamp,
                    "is_active": len(recent_txs) > 0
                }
        
        except Exception as e:
            print(f"⚠️  Ошибка проверки onchain активности: {e}")
            return None
    
    def generate_validation_report(self, validation_results: Dict[str, Dict]) -> str:
        """
        Генерирует отчёт о валидации
        
        Args:
            validation_results: Результаты валидации {address: result}
        
        Returns:
            Текстовый отчёт
        """
        
        valid_count = sum(1 for r in validation_results.values() if r["is_valid"])
        invalid_count = len(validation_results) - valid_count
        
        warnings_count = sum(
            1 for r in validation_results.values()
            if r.get("warnings")
        )
        
        lines = [
            "=" * 80,
            "🧹 WALLET VALIDATION REPORT",
            "=" * 80,
            "",
            f"📊 СТАТИСТИКА",
            f"   Проверено кошельков: {len(validation_results)}",
            f"   ✅ Валидных: {valid_count}",
            f"   ❌ Невалидных: {invalid_count}",
            f"   ⚠️  С предупреждениями: {warnings_count}",
            ""
        ]
        
        if invalid_count > 0:
            lines.extend([
                "❌ НЕВАЛИДНЫЕ КОШЕЛЬКИ:",
                ""
            ])
            
            for address, result in validation_results.items():
                if not result["is_valid"]:
                    lines.append(f"   {address[:10]}...{address[-6:]}")
                    lines.append(f"      Причина: {result['reason']}")
                    lines.append("")
        
        if warnings_count > 0:
            lines.extend([
                "⚠️  ПРЕДУПРЕЖДЕНИЯ:",
                ""
            ])
            
            for address, result in validation_results.items():
                if result.get("warnings"):
                    lines.append(f"   {address[:10]}...{address[-6:]}")
                    for warning in result["warnings"]:
                        lines.append(f"      • {warning}")
                    lines.append("")
        
        lines.extend([
            "=" * 80
        ])
        
        return "\n".join(lines)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def validate_wallet_list(
    wallets: List[Dict],
    validator: WalletValidator = None
) -> Dict[str, Dict]:
    """
    Convenience function для валидации списка кошельков
    
    Usage:
        from app.mining.validation import validate_wallet_list
        
        results = await validate_wallet_list(wallets)
        for address, result in results.items():
            if not result["is_valid"]:
                print(f"Remove {address}: {result['reason']}")
    """
    
    if validator is None:
        validator = WalletValidator()
    
    return await validator.batch_validate(wallets)


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    
    async def main():
        print("🧪 TESTING WALLET VALIDATOR\n")
        
        validator = WalletValidator()
        
        # Тестовые кошельки
        test_wallets = [
            {
                "address": "0x1234567890abcdef1234567890abcdef12345678",
                "chain": "ethereum",
                "score": 75,
                "roi_30d": 0.45,
                "win_rate": 0.68,
                "total_trades": 25,
                "total_volume_30d": 150000,
                "last_trade_at": (datetime.utcnow() - timedelta(days=5)).isoformat()
            },
            {
                "address": "0xabcdef1234567890abcdef1234567890abcdef12",
                "chain": "ethereum",
                "score": 25,
                "roi_30d": -0.30,
                "win_rate": 0.35,
                "total_trades": 8,
                "total_volume_30d": 5000,
                "last_trade_at": (datetime.utcnow() - timedelta(days=70)).isoformat()
            },
            {
                "address": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                "chain": "ethereum",
                "score": 50,
                "roi_30d": 0.15,
                "win_rate": 0.55,
                "total_trades": 15,
                "total_volume_30d": 50000,
                "last_trade_at": (datetime.utcnow() - timedelta(days=35)).isoformat()
            }
        ]
        
        print("📊 Валидация кошельков...\n")
        
        results = await validator.batch_validate(test_wallets)
        
        for wallet in test_wallets:
            address = wallet["address"]
            result = results[address]
            
            status = "✅ VALID" if result["is_valid"] else "❌ INVALID"
            
            print(f"{status}: {address[:10]}...{address[-6:]}")
            
            if not result["is_valid"]:
                print(f"   Причина: {result['reason']}")
            
            if result.get("warnings"):
                print(f"   Предупреждения:")
                for warning in result["warnings"]:
                    print(f"     • {warning}")
            
            if result["score_update"]:
                print(f"   Скор обновлён: {wallet['score']} → {result['new_score']}")
            
            print()
        
        # Генерируем отчёт
        report = validator.generate_validation_report(results)
        print(report)
        
        print("✅ Тестирование завершено!")
    
    asyncio.run(main())