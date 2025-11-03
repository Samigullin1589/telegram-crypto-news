"""
WALLET VALIDATOR v1.0

Автоматическая валидация и очистка базы отслеживаемых кошельков.

Проверяет:
- Активность кошелька (последняя сделка)
- Производительность (ROI, winrate)
- Скор и репутацию
- Соответствие критериям

Рекомендует:
- Сохранить (активный успешный)
- Предупредить (деградация)
- Удалить (неактуален)
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app import settings


class ValidationResult(Enum):
    """Результат валидации кошелька"""
    KEEP = "keep"
    WARNING = "warning"
    REMOVE = "remove"


@dataclass
class ValidationReport:
    """Отчёт о валидации кошелька"""
    address: str
    chain: str
    result: ValidationResult
    score: int
    issues: List[str]
    recommendations: List[str]
    new_score: Optional[int] = None
    
    def __str__(self):
        emoji = {
            ValidationResult.KEEP: "✅",
            ValidationResult.WARNING: "⚠️",
            ValidationResult.REMOVE: "❌"
        }
        
        lines = [
            f"{emoji[self.result]} {self.address[:10]}...{self.address[-6:]} ({self.chain})",
            f"   Скор: {self.score}/100 → {self.new_score or self.score}/100",
            f"   Результат: {self.result.value.upper()}"
        ]
        
        if self.issues:
            lines.append(f"   Проблемы:")
            for issue in self.issues:
                lines.append(f"     • {issue}")
        
        if self.recommendations:
            lines.append(f"   Рекомендации:")
            for rec in self.recommendations:
                lines.append(f"     • {rec}")
        
        return "\n".join(lines)


class WalletValidator:
    """
    Валидатор кошельков с многоуровневой проверкой
    """
    
    def __init__(self, etherscan_key: str = None):
        self.etherscan_key = etherscan_key or settings.ETHERSCAN_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        
        self.max_inactive_days = settings.VALIDATION_MAX_INACTIVE_DAYS
        self.min_score_to_keep = settings.VALIDATION_MIN_SCORE_TO_KEEP
        self.min_roi_to_keep = settings.VALIDATION_MIN_ROI_TO_KEEP
        
        self.warning_inactive_days = self.max_inactive_days // 2
        self.warning_score = self.min_score_to_keep + 10
        
        # Кэш для blockchain данных
        self.blockchain_cache: Dict[str, Tuple[Dict, datetime]] = {}
        self.cache_ttl = timedelta(hours=1)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    # ========================================================================
    # MAIN VALIDATION
    # ========================================================================
    
    async def validate_wallet(self, wallet_data: Dict) -> ValidationReport:
        """
        Полная валидация кошелька
        
        Args:
            wallet_data: Данные кошелька из базы
        
        Returns:
            ValidationReport с результатами проверки
        """
        
        address = wallet_data["address"]
        chain = wallet_data["chain"]
        current_score = wallet_data.get("score", 50)
        
        issues = []
        recommendations = []
        score_adjustments = []
        
        # ПРОВЕРКА 1: АКТИВНОСТЬ
        activity_check = self._check_activity(wallet_data)
        
        if activity_check["status"] == "inactive":
            issues.append(f"Неактивен {activity_check['days_inactive']} дней")
            score_adjustments.append(-20)
            recommendations.append("Удалить из отслеживания")
        
        elif activity_check["status"] == "warning":
            issues.append(f"Низкая активность ({activity_check['days_inactive']} дней)")
            score_adjustments.append(-5)
            recommendations.append("Мониторить активность")
        
        else:
            recommendations.append("Активность в норме")
        
        # ПРОВЕРКА 2: ПРОИЗВОДИТЕЛЬНОСТЬ
        performance_check = self._check_performance(wallet_data)
        
        if performance_check["status"] == "poor":
            issues.append(f"Плохая производительность (ROI: {performance_check['roi_30d']:.1%})")
            score_adjustments.append(-15)
            recommendations.append("Удалить из-за низкой эффективности")
        
        elif performance_check["status"] == "warning":
            issues.append(f"Снижение производительности (WinRate: {performance_check['win_rate']:.1%})")
            score_adjustments.append(-5)
            recommendations.append("Проверить последние сделки")
        
        else:
            score_adjustments.append(+3)
            recommendations.append("Производительность в норме")
        
        # ПРОВЕРКА 3: СКОР
        score_check = self._check_score(wallet_data)
        
        if score_check["status"] == "critical":
            issues.append(f"Критически низкий скор ({current_score}/100)")
            recommendations.append("Удалить из-за низкого рейтинга")
        
        elif score_check["status"] == "warning":
            issues.append(f"Низкий скор ({current_score}/100)")
            recommendations.append("Повысить скор или удалить")
        
        # ПРОВЕРКА 4: СПЕЦИАЛИЗАЦИЯ
        specialization = wallet_data.get("specialization", [])
        if not specialization or specialization == ["Other"]:
            issues.append("Нет чёткой специализации")
            score_adjustments.append(-2)
            recommendations.append("Определить профиль кошелька")
        
        # ПРОВЕРКА 5: ВОЗРАСТ В СИСТЕМЕ
        discovered_at = datetime.fromisoformat(wallet_data.get("discovered_at", datetime.utcnow().isoformat()))
        days_tracked = (datetime.utcnow() - discovered_at).days
        
        if days_tracked < 7:
            recommendations.append(f"Новый кошелёк ({days_tracked} дней), даём время")
            score_adjustments = [x // 2 for x in score_adjustments]
        
        # ПРОВЕРКА 6: ОБЪЁМЫ ТОРГОВЛИ
        total_volume = wallet_data.get("total_volume_30d", 0)
        if total_volume < 10000:  # Минимум $10k за 30 дней
            issues.append(f"Низкий объём торговли (${total_volume:,.0f})")
            score_adjustments.append(-3)
            recommendations.append("Увеличить активность или удалить")
        
        # ПРОВЕРКА 7: КОНСИСТЕНТНОСТЬ
        consistency_check = self._check_consistency(wallet_data)
        if consistency_check["status"] == "inconsistent":
            issues.append("Нестабильные результаты")
            score_adjustments.append(-5)
            recommendations.append("Требуется больше данных для оценки")
        
        # ФИНАЛЬНАЯ ОЦЕНКА
        new_score = current_score + sum(score_adjustments)
        new_score = max(0, min(100, new_score))
        
        # Определяем результат
        if activity_check["status"] == "inactive" or performance_check["status"] == "poor" or score_check["status"] == "critical":
            result = ValidationResult.REMOVE
        
        elif new_score < self.warning_score or activity_check["status"] == "warning" or performance_check["status"] == "warning":
            result = ValidationResult.WARNING
        
        else:
            result = ValidationResult.KEEP
        
        return ValidationReport(
            address=address,
            chain=chain,
            result=result,
            score=current_score,
            issues=issues,
            recommendations=recommendations,
            new_score=new_score
        )
    
    # ========================================================================
    # INDIVIDUAL CHECKS
    # ========================================================================
    
    def _check_activity(self, wallet_data: Dict) -> Dict:
        """
        Проверка активности кошелька
        
        Returns:
            {"status": "active" | "warning" | "inactive", "days_inactive": int}
        """
        
        last_trade_str = wallet_data.get("last_trade_at")
        
        if not last_trade_str:
            return {"status": "inactive", "days_inactive": 999}
        
        last_trade = datetime.fromisoformat(last_trade_str)
        days_inactive = (datetime.utcnow() - last_trade).days
        
        if days_inactive > self.max_inactive_days:
            return {"status": "inactive", "days_inactive": days_inactive}
        
        elif days_inactive > self.warning_inactive_days:
            return {"status": "warning", "days_inactive": days_inactive}
        
        else:
            return {"status": "active", "days_inactive": days_inactive}
    
    def _check_performance(self, wallet_data: Dict) -> Dict:
        """
        Проверка производительности
        
        Returns:
            {"status": "good" | "warning" | "poor", "roi_30d": float, "win_rate": float}
        """
        
        roi_30d = wallet_data.get("roi_30d", 0)
        win_rate = wallet_data.get("win_rate", 0)
        
        if roi_30d < self.min_roi_to_keep or win_rate < 0.40:
            return {"status": "poor", "roi_30d": roi_30d, "win_rate": win_rate}
        
        elif roi_30d < 0.20 or win_rate < 0.55:
            return {"status": "warning", "roi_30d": roi_30d, "win_rate": win_rate}
        
        else:
            return {"status": "good", "roi_30d": roi_30d, "win_rate": win_rate}
    
    def _check_score(self, wallet_data: Dict) -> Dict:
        """
        Проверка скора
        
        Returns:
            {"status": "good" | "warning" | "critical"}
        """
        
        score = wallet_data.get("score", 50)
        
        if score < self.min_score_to_keep:
            return {"status": "critical"}
        
        elif score < self.warning_score:
            return {"status": "warning"}
        
        else:
            return {"status": "good"}
    
    def _check_consistency(self, wallet_data: Dict) -> Dict:
        """
        Проверка консистентности результатов
        
        Returns:
            {"status": "consistent" | "inconsistent", "volatility": float}
        """
        
        # Получаем последние результаты
        recent_trades = wallet_data.get("recent_trades", [])
        
        if len(recent_trades) < 5:
            return {"status": "consistent", "volatility": 0.0}
        
        # Рассчитываем волатильность результатов
        profits = [t.get("profit_pct", 0) for t in recent_trades[-10:]]
        
        if not profits:
            return {"status": "consistent", "volatility": 0.0}
        
        import statistics
        
        mean_profit = statistics.mean(profits)
        
        if len(profits) > 1:
            stdev = statistics.stdev(profits)
            
            # Высокая волатильность = нестабильные результаты
            if stdev > 50:  # >50% стандартное отклонение
                return {"status": "inconsistent", "volatility": stdev}
        
        return {"status": "consistent", "volatility": 0.0}
    
    # ========================================================================
    # BATCH VALIDATION
    # ========================================================================
    
    async def validate_all_wallets(self, wallets: List[Dict]) -> Dict:
        """
        Валидация всех кошельков
        
        Args:
            wallets: Список кошельков из базы
        
        Returns:
            Результаты валидации
        """
        
        print(f"\n{'=' * 80}")
        print(f"🧹 WALLET VALIDATION ENGINE")
        print(f"{'=' * 80}")
        print(f"Проверяю {len(wallets)} кошельков...\n")
        
        reports = []
        
        for i, wallet in enumerate(wallets, 1):
            try:
                print(f"[{i}/{len(wallets)}] {wallet['address'][:10]}...", end=" ")
                
                report = await self.validate_wallet(wallet)
                reports.append(report)
                
                emoji = {
                    ValidationResult.KEEP: "✅",
                    ValidationResult.WARNING: "⚠️",
                    ValidationResult.REMOVE: "❌"
                }
                
                print(f"{emoji[report.result]} {report.result.value} (score: {report.score}→{report.new_score})")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                continue
        
        # Статистика
        summary = {
            "keep": sum(1 for r in reports if r.result == ValidationResult.KEEP),
            "warning": sum(1 for r in reports if r.result == ValidationResult.WARNING),
            "remove": sum(1 for r in reports if r.result == ValidationResult.REMOVE)
        }
        
        print(f"\n{'=' * 80}")
        print(f"📊 РЕЗУЛЬТАТЫ ВАЛИДАЦИИ")
        print(f"{'=' * 80}")
        print(f"✅ Сохранить: {summary['keep']} кошельков")
        print(f"⚠️  Предупреждение: {summary['warning']} кошельков")
        print(f"❌ Удалить: {summary['remove']} кошельков")
        print(f"{'=' * 80}\n")
        
        return {
            "reports": reports,
            "summary": summary
        }
    
    # ========================================================================
    # ADVANCED: ONCHAIN VERIFICATION
    # ========================================================================
    
    async def verify_wallet_onchain(self, address: str, chain: str) -> Dict:
        """
        Проверка кошелька в блокчейне (дополнительная верификация)
        
        Проверяет:
        - Последнюю активность
        - Баланс
        - Количество транзакций
        
        Returns:
            Данные из блокчейна
        """
        
        # Проверяем кэш
        cache_key = f"{chain}_{address}"
        if cache_key in self.blockchain_cache:
            cached_data, cached_at = self.blockchain_cache[cache_key]
            if datetime.utcnow() - cached_at < self.cache_ttl:
                return cached_data
        
        if chain not in ["ethereum", "bsc", "polygon", "base", "arbitrum", "optimism"]:
            return None
        
        api_configs = {
            "ethereum": ("https://api.etherscan.io/api", self.etherscan_key),
            "bsc": ("https://api.bscscan.com/api", self.etherscan_key),
            "polygon": ("https://api.polygonscan.com/api", self.etherscan_key),
            "base": ("https://api.basescan.org/api", self.etherscan_key),
            "arbitrum": ("https://api.arbiscan.io/api", self.etherscan_key),
            "optimism": ("https://api-optimistic.etherscan.io/api", self.etherscan_key)
        }
        
        api_url, api_key = api_configs.get(chain, (None, None))
        
        if not api_url or not api_key:
            return None
        
        try:
            # Получаем последние транзакции
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
            
            async with self.session.get(api_url, params=params, timeout=30) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                
                if data.get("status") != "1":
                    return None
                
                transactions = data.get("result", [])
                
                if not transactions:
                    result = {
                        "is_active": False,
                        "last_tx_timestamp": None,
                        "tx_count_30d": 0,
                        "tx_count_total": 0,
                        "balance_eth": 0
                    }
                else:
                    # Последняя транзакция
                    last_tx = transactions[0]
                    last_tx_timestamp = datetime.fromtimestamp(int(last_tx.get("timeStamp", 0)))
                    
                    # Считаем транзакции за 30 дней
                    cutoff = datetime.utcnow() - timedelta(days=30)
                    tx_count_30d = sum(
                        1 for tx in transactions 
                        if datetime.fromtimestamp(int(tx.get("timeStamp", 0))) >= cutoff
                    )
                    
                    # Проверяем активность
                    days_since_tx = (datetime.utcnow() - last_tx_timestamp).days
                    is_active = days_since_tx <= 30 and tx_count_30d >= 5
                    
                    result = {
                        "is_active": is_active,
                        "last_tx_timestamp": last_tx_timestamp,
                        "tx_count_30d": tx_count_30d,
                        "tx_count_total": len(transactions),
                        "balance_eth": 0
                    }
                
                # Получаем баланс
                balance_params = {
                    "module": "account",
                    "action": "balance",
                    "address": address,
                    "tag": "latest",
                    "apikey": api_key
                }
                
                async with self.session.get(api_url, params=balance_params, timeout=10) as balance_resp:
                    if balance_resp.status == 200:
                        balance_data = await balance_resp.json()
                        if balance_data.get("status") == "1":
                            balance_wei = int(balance_data.get("result", 0))
                            result["balance_eth"] = balance_wei / 1e18
                
                # Кэшируем
                self.blockchain_cache[cache_key] = (result, datetime.utcnow())
                
                return result
        
        except Exception as e:
            print(f"⚠️  Ошибка onchain проверки: {e}")
            return None
    
    # ========================================================================
    # SCORING UPDATES
    # ========================================================================
    
    def apply_score_decay(self, wallet_data: Dict) -> int:
        """
        Применяет деградацию скора за неактивность
        
        Args:
            wallet_data: Данные кошелька
        
        Returns:
            Новый скор после деградации
        """
        
        current_score = wallet_data.get("score", 50)
        last_trade_str = wallet_data.get("last_trade_at")
        
        if not last_trade_str:
            return current_score
        
        last_trade = datetime.fromisoformat(last_trade_str)
        days_inactive = (datetime.utcnow() - last_trade).days
        
        decay_per_day = settings.WALLET_SCORE_DECAY_PER_DAY
        
        decay_total = days_inactive * decay_per_day
        new_score = current_score - decay_total
        
        return max(0, int(new_score))
    
    def calculate_performance_score(self, wallet_data: Dict) -> int:
        """
        Рассчитывает скор на основе производительности
        
        Args:
            wallet_data: Данные кошелька с метриками
        
        Returns:
            Скор 0-100
        """
        
        roi_30d = wallet_data.get("roi_30d", 0)
        win_rate = wallet_data.get("win_rate", 0.5)
        total_trades = wallet_data.get("total_trades", 0)
        total_volume = wallet_data.get("total_volume_30d", 0)
        
        # ROI компонент (max 40 баллов)
        roi_score = min(40, max(0, roi_30d * 40))
        
        # Win rate компонент (max 40 баллов)
        winrate_score = win_rate * 40
        
        # Объём торговли компонент (max 10 баллов)
        volume_score = min(10, total_volume / 100000)
        
        # Количество сделок компонент (max 10 баллов)
        trades_score = min(10, total_trades / 5)
        
        final_score = roi_score + winrate_score + volume_score + trades_score
        
        return int(final_score)
    
    def suggest_score_adjustment(self, wallet_data: Dict, validation_report: ValidationReport) -> int:
        """
        Предлагает корректировку скора на основе валидации
        
        Returns:
            Рекомендуемый новый скор
        """
        
        # Начинаем с текущего скора
        current_score = wallet_data.get("score", 50)
        
        # Применяем деградацию
        score_with_decay = self.apply_score_decay(wallet_data)
        
        # Применяем корректировки из валидации
        if validation_report.new_score is not None:
            adjusted_score = validation_report.new_score
        else:
            adjusted_score = score_with_decay
        
        # Рассчитываем performance-based score
        performance_score = self.calculate_performance_score(wallet_data)
        
        # Берём среднее между adjusted и performance
        final_score = int((adjusted_score + performance_score) / 2)
        
        return max(0, min(100, final_score))


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def run_validation(wallets: List[Dict], etherscan_key: str = None) -> Dict:
    """
    Convenience function для запуска валидации
    
    Usage:
        from app.whales.validator import run_validation
        
        result = await run_validation(
            wallets=wallet_db.get_active_wallets(),
            etherscan_key=settings.ETHERSCAN_API_KEY
        )
        
        # Применяем результаты
        for report in result["reports"]:
            if report.result == ValidationResult.REMOVE:
                wallet_db.deactivate_wallet(report.address, report.chain, "Failed validation")
            elif report.new_score:
                wallet_db.update_wallet_score(report.address, report.chain, report.new_score)
    """
    
    async with WalletValidator(etherscan_key) as validator:
        return await validator.validate_all_wallets(wallets)


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    import sys
    
    async def main():
        print("🧪 TESTING WALLET VALIDATOR\n")
        
        test_wallets = [
            {
                "address": "0x1234567890abcdef1234567890abcdef12345678",
                "chain": "ethereum",
                "roi_30d": 0.85,
                "roi_90d": 1.45,
                "win_rate": 0.72,
                "total_trades": 15,
                "total_volume_30d": 250000,
                "score": 75,
                "specialization": ["DeFi"],
                "discovered_at": (datetime.utcnow() - timedelta(days=20)).isoformat(),
                "last_trade_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "is_active": True,
                "recent_trades": [
                    {"profit_pct": 15.2},
                    {"profit_pct": 8.5},
                    {"profit_pct": -3.2},
                    {"profit_pct": 22.1},
                    {"profit_pct": 11.8}
                ]
            },
            {
                "address": "0xabcdef1234567890abcdef1234567890abcdef12",
                "chain": "ethereum",
                "roi_30d": -0.15,
                "roi_90d": 0.20,
                "win_rate": 0.45,
                "total_trades": 8,
                "total_volume_30d": 5000,
                "score": 35,
                "specialization": ["Memecoins"],
                "discovered_at": (datetime.utcnow() - timedelta(days=45)).isoformat(),
                "last_trade_at": (datetime.utcnow() - timedelta(days=25)).isoformat(),
                "is_active": True,
                "recent_trades": []
            },
            {
                "address": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                "chain": "ethereum",
                "roi_30d": 0.05,
                "roi_90d": 0.15,
                "win_rate": 0.52,
                "total_trades": 20,
                "total_volume_30d": 50000,
                "score": 55,
                "specialization": ["DeFi", "Gaming"],
                "discovered_at": (datetime.utcnow() - timedelta(days=70)).isoformat(),
                "last_trade_at": (datetime.utcnow() - timedelta(days=70)).isoformat(),
                "is_active": True,
                "recent_trades": []
            }
        ]
        
        etherscan_key = input("Etherscan API Key (или Enter для пропуска): ").strip()
        
        if not etherscan_key:
            etherscan_key = "DEMO_KEY"
        
        result = await run_validation(test_wallets, etherscan_key)
        
        print("\n📋 ДЕТАЛЬНЫЕ ОТЧЁТЫ:\n")
        for report in result["reports"]:
            print(report)
            print()
        
        print("✅ Валидация завершена!")
    
    asyncio.run(main())