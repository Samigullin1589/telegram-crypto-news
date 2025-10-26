# app/mining/integration.py
"""
MINING SYSTEM INTEGRATION v2.0

Полная интеграция системы автоматического обнаружения успешных трейдеров
с основным scheduler'ом.

Возможности:
- Автоматическое обнаружение кошельков
- Валидация и очистка базы
- Интеграция с performance tracking
- Обновление скоров на основе результатов
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

try:
    from app.mining.discovery import WalletDiscovery
    DISCOVERY_AVAILABLE = True
except ImportError:
    DISCOVERY_AVAILABLE = False

try:
    from app.mining.validation import WalletValidator
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False


class MiningSystem:
    """
    Система управления mining процессом
    
    Интегрирует discovery и validation с основным scheduler'ом
    """
    
    def __init__(self, wallet_db):
        """
        Args:
            wallet_db: WalletDatabase instance из scheduler
        """
        self.wallet_db = wallet_db
        
        # Инициализация компонентов
        self.discovery = WalletDiscovery() if DISCOVERY_AVAILABLE else None
        self.validator = WalletValidator() if VALIDATOR_AVAILABLE else None
        
        # Статистика
        self.stats = {
            "total_discovered": 0,
            "total_validated": 0,
            "total_removed": 0,
            "last_discovery": None,
            "last_validation": None
        }
        
        if not DISCOVERY_AVAILABLE or not VALIDATOR_AVAILABLE:
            print("⚠️  Mining System: Некоторые компоненты недоступны")
            print(f"   Discovery: {'✅' if DISCOVERY_AVAILABLE else '❌'}")
            print(f"   Validator: {'✅' if VALIDATOR_AVAILABLE else '❌'}")
        else:
            print("✅ Mining System: Полностью загружен")
    
    # ========================================================================
    # DISCOVERY
    # ========================================================================
    
    async def run_discovery_cycle(
        self,
        chains: List[str] = None,
        max_wallets: int = 50
    ) -> Dict:
        """
        Запускает цикл обнаружения новых кошельков
        
        Args:
            chains: Список chains для поиска (None = все)
            max_wallets: Максимум кошельков для добавления
        
        Returns:
            {
                "discovered": int,
                "added": int,
                "skipped": int,
                "errors": int
            }
        """
        
        if not DISCOVERY_AVAILABLE or not self.discovery:
            print("⚠️  Discovery недоступен")
            return {"discovered": 0, "added": 0, "skipped": 0, "errors": 0}
        
        print(f"\n{'=' * 80}")
        print(f"🔍 [MINING] Discovery Cycle Start")
        print(f"{'=' * 80}")
        
        start_time = datetime.utcnow()
        
        result = {
            "discovered": 0,
            "added": 0,
            "skipped": 0,
            "errors": 0
        }
        
        try:
            # Устанавливаем параметры
            if chains:
                self.discovery.target_chains = chains
            
            # Запускаем discovery
            print(f"🔍 Ищем успешных трейдеров...")
            print(f"   Target chains: {self.discovery.target_chains}")
            print(f"   Min trades: {self.discovery.min_trades}")
            print(f"   Min ROI: {self.discovery.min_roi_30d:.1%}")
            
            discovered_wallets = await self.discovery.discover_wallets(
                max_results=max_wallets
            )
            
            result["discovered"] = len(discovered_wallets)
            
            print(f"\n✅ Найдено: {len(discovered_wallets)} кошельков")
            
            # Добавляем в базу
            for wallet in discovered_wallets:
                try:
                    # Проверяем дубликаты
                    existing = self.wallet_db.get_wallet(wallet.address, wallet.chain)
                    
                    if existing:
                        result["skipped"] += 1
                        continue
                    
                    # Добавляем новый
                    if self.wallet_db.add_wallet(wallet):
                        result["added"] += 1
                        
                        print(f"   ✅ {wallet.address[:10]}... | "
                              f"ROI: {wallet.roi_30d:+.1%} | "
                              f"WinRate: {wallet.win_rate:.1%} | "
                              f"{wallet.chain}")
                
                except Exception as e:
                    print(f"   ⚠️  Ошибка добавления кошелька: {e}")
                    result["errors"] += 1
            
            # Обновляем статистику
            self.stats["total_discovered"] += result["added"]
            self.stats["last_discovery"] = datetime.utcnow()
            
            elapsed = (datetime.utcnow() - start_time).seconds
            
            print(f"\n{'=' * 80}")
            print(f"✅ [MINING] Discovery Complete ({elapsed}s)")
            print(f"   Найдено: {result['discovered']}")
            print(f"   Добавлено: {result['added']}")
            print(f"   Пропущено (дубли): {result['skipped']}")
            print(f"   Ошибки: {result['errors']}")
            print(f"   Всего в базе: {len(self.wallet_db.get_active_wallets())} активных")
            print(f"{'=' * 80}\n")
        
        except Exception as e:
            print(f"❌ [MINING] Discovery Error: {e}")
            import traceback
            traceback.print_exc()
            result["errors"] += 1
        
        return result
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    async def run_validation_cycle(self) -> Dict:
        """
        Запускает цикл валидации и очистки базы
        
        Returns:
            {
                "checked": int,
                "removed": int,
                "updated": int,
                "errors": int
            }
        """
        
        if not VALIDATOR_AVAILABLE or not self.validator:
            print("⚠️  Validator недоступен")
            return {"checked": 0, "removed": 0, "updated": 0, "errors": 0}
        
        print(f"\n{'=' * 80}")
        print(f"🧹 [MINING] Validation Cycle Start")
        print(f"{'=' * 80}")
        
        start_time = datetime.utcnow()
        
        result = {
            "checked": 0,
            "removed": 0,
            "updated": 0,
            "errors": 0
        }
        
        try:
            active_wallets = self.wallet_db.get_active_wallets()
            result["checked"] = len(active_wallets)
            
            print(f"🧹 Проверяю {len(active_wallets)} активных кошельков...")
            
            for wallet_data in active_wallets:
                try:
                    address = wallet_data["address"]
                    chain = wallet_data["chain"]
                    
                    # Валидация
                    validation = await self.validator.validate_wallet(
                        address=address,
                        chain=chain,
                        current_data=wallet_data
                    )
                    
                    # Решение на основе валидации
                    if not validation["is_valid"]:
                        # Деактивируем
                        self.wallet_db.deactivate_wallet(
                            address,
                            chain,
                            validation["reason"]
                        )
                        result["removed"] += 1
                        
                        print(f"   ❌ Removed: {address[:10]}... ({validation['reason']})")
                    
                    elif validation["score_update"]:
                        # Обновляем скор
                        new_score = validation["new_score"]
                        self.wallet_db.update_wallet_score(
                            address,
                            chain,
                            new_score
                        )
                        result["updated"] += 1
                
                except Exception as e:
                    print(f"   ⚠️  Ошибка валидации: {e}")
                    result["errors"] += 1
            
            # Обновляем статистику
            self.stats["total_validated"] += result["checked"]
            self.stats["total_removed"] += result["removed"]
            self.stats["last_validation"] = datetime.utcnow()
            
            elapsed = (datetime.utcnow() - start_time).seconds
            
            print(f"\n{'=' * 80}")
            print(f"✅ [MINING] Validation Complete ({elapsed}s)")
            print(f"   Проверено: {result['checked']}")
            print(f"   Удалено: {result['removed']}")
            print(f"   Обновлено: {result['updated']}")
            print(f"   Ошибки: {result['errors']}")
            print(f"   Осталось активных: {len(self.wallet_db.get_active_wallets())}")
            print(f"{'=' * 80}\n")
        
        except Exception as e:
            print(f"❌ [MINING] Validation Error: {e}")
            import traceback
            traceback.print_exc()
            result["errors"] += 1
        
        return result
    
    # ========================================================================
    # PERFORMANCE INTEGRATION
    # ========================================================================
    
    async def update_wallet_from_performance(
        self,
        address: str,
        chain: str,
        performance_data: Dict
    ):
        """
        Обновляет данные кошелька на основе результатов трекинга
        
        Args:
            address: Адрес кошелька
            chain: Блокчейн
            performance_data: {
                "roi": float,
                "win_rate": float,
                "total_trades": int,
                "success": bool
            }
        """
        
        wallet = self.wallet_db.get_wallet(address, chain)
        
        if not wallet:
            return
        
        try:
            # Обновляем метрики
            current_score = wallet.get("score", 50)
            
            # Пересчитываем скор на основе новых данных
            roi = performance_data.get("roi", 0)
            win_rate = performance_data.get("win_rate", 0.5)
            
            # Простая формула (можно улучшить)
            roi_component = min(50, int(roi * 100))  # ROI влияет до +50
            winrate_component = int(win_rate * 50)   # WinRate влияет до +50
            
            new_score = max(0, min(100, roi_component + winrate_component))
            
            # Обновляем
            self.wallet_db.update_wallet_score(address, chain, new_score)
            
            print(f"📊 [MINING] Score updated: {address[:10]}... {current_score} → {new_score}")
        
        except Exception as e:
            print(f"⚠️  [MINING] Error updating wallet: {e}")
    
    # ========================================================================
    # STATS & REPORTING
    # ========================================================================
    
    def get_stats(self) -> Dict:
        """Получает статистику mining системы"""
        
        active_wallets = self.wallet_db.get_active_wallets()
        
        # Распределение по chains
        chain_distribution = defaultdict(int)
        for wallet in active_wallets:
            chain_distribution[wallet["chain"]] += 1
        
        # Распределение по скорам
        score_ranges = {
            "excellent (80+)": 0,
            "good (60-79)": 0,
            "average (40-59)": 0,
            "poor (<40)": 0
        }
        
        for wallet in active_wallets:
            score = wallet.get("score", 50)
            if score >= 80:
                score_ranges["excellent (80+)"] += 1
            elif score >= 60:
                score_ranges["good (60-79)"] += 1
            elif score >= 40:
                score_ranges["average (40-59)"] += 1
            else:
                score_ranges["poor (<40)"] += 1
        
        return {
            **self.stats,
            "active_wallets": len(active_wallets),
            "chain_distribution": dict(chain_distribution),
            "score_distribution": score_ranges,
            "discovery_available": DISCOVERY_AVAILABLE,
            "validator_available": VALIDATOR_AVAILABLE
        }
    
    def print_stats(self):
        """Выводит статистику в консоль"""
        
        stats = self.get_stats()
        
        print("\n" + "=" * 80)
        print("📊 MINING SYSTEM STATISTICS")
        print("=" * 80)
        
        print(f"\n🔍 Discovery:")
        print(f"   Total discovered: {stats['total_discovered']}")
        print(f"   Last run: {stats['last_discovery'] or 'Never'}")
        
        print(f"\n🧹 Validation:")
        print(f"   Total validated: {stats['total_validated']}")
        print(f"   Total removed: {stats['total_removed']}")
        print(f"   Last run: {stats['last_validation'] or 'Never'}")
        
        print(f"\n👛 Active Wallets: {stats['active_wallets']}")
        
        if stats['chain_distribution']:
            print(f"\n📊 By Chain:")
            for chain, count in sorted(stats['chain_distribution'].items(), key=lambda x: x[1], reverse=True):
                print(f"   {chain}: {count}")
        
        print(f"\n🎯 By Score:")
        for range_name, count in stats['score_distribution'].items():
            print(f"   {range_name}: {count}")
        
        print("\n" + "=" * 80 + "\n")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_mining_system(wallet_db) -> MiningSystem:
    """
    Создаёт instance Mining System
    
    Usage:
        from app.mining.integration import create_mining_system
        
        mining = create_mining_system(scheduler.wallet_db)
        result = await mining.run_discovery_cycle()
    """
    return MiningSystem(wallet_db)


async def quick_discovery(wallet_db, max_wallets: int = 20) -> Dict:
    """
    Quick discovery helper
    
    Usage:
        from app.mining.integration import quick_discovery
        
        result = await quick_discovery(wallet_db, max_wallets=20)
        print(f"Added {result['added']} wallets")
    """
    
    mining = create_mining_system(wallet_db)
    return await mining.run_discovery_cycle(max_wallets=max_wallets)


async def quick_validation(wallet_db) -> Dict:
    """
    Quick validation helper
    
    Usage:
        from app.mining.integration import quick_validation
        
        result = await quick_validation(wallet_db)
        print(f"Removed {result['removed']} wallets")
    """
    
    mining = create_mining_system(wallet_db)
    return await mining.run_validation_cycle()