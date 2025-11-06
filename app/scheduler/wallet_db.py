# app/scheduler/wallet_db.py
"""
Wallet Database Management
Simple JSON-based storage for tracked wallets
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from app.config import config

logger = logging.getLogger(__name__)


class WalletDatabase:
    """База данных отслеживаемых кошельков с простым JSON хранилищем"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = config.database.wallet_db_path
        
        self.db_path = Path(db_path)
        self.wallets: List[Dict] = []
        self._load()
    
    def _load(self):
        """Загрузка базы данных"""
        try:
            if self.db_path.exists():
                with open(self.db_path, 'r') as f:
                    self.wallets = json.load(f)
                logger.info(f"📂 [WALLET_DB] Загружено {len(self.wallets)} кошельков")
            else:
                logger.info("📂 [WALLET_DB] Новая база данных")
                self.wallets = []
                self._save()
        except Exception as e:
            logger.error(f"⚠️ [WALLET_DB] Ошибка загрузки: {e}")
            self.wallets = []
    
    def _save(self):
        """Сохранение базы данных"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.db_path, 'w') as f:
                json.dump(self.wallets, f, indent=2)
        except Exception as e:
            logger.error(f"⚠️ [WALLET_DB] Ошибка сохранения: {e}")
    
    def add_wallet(self, wallet_stats) -> bool:
        """Добавление кошелька"""
        existing = self.get_wallet(wallet_stats.address, wallet_stats.chain)
        if existing:
            return False
        
        wallet_data = {
            "address": wallet_stats.address,
            "chain": wallet_stats.chain,
            "roi_30d": wallet_stats.roi_30d,
            "roi_90d": getattr(wallet_stats, 'roi_90d', 0),
            "win_rate": wallet_stats.win_rate,
            "total_trades": wallet_stats.total_trades,
            "specialization": getattr(wallet_stats, 'specialization', 'general'),
            "discovered_at": datetime.utcnow().isoformat(),
            "discovered_via": wallet_stats.best_trades[0]["token"] if hasattr(wallet_stats, 'best_trades') and wallet_stats.best_trades else "unknown",
            "last_trade_at": wallet_stats.last_trade_at.isoformat() if hasattr(wallet_stats.last_trade_at, 'isoformat') else str(wallet_stats.last_trade_at),
            "is_active": True,
            "score": 50
        }
        
        self.wallets.append(wallet_data)
        self._save()
        
        logger.info(f"✅ [WALLET_DB] Добавлен: {wallet_stats.address[:10]}... (ROI: {wallet_stats.roi_30d:.1%})")
        return True
    
    def get_wallet(self, address: str, chain: str) -> Optional[Dict]:
        """Получение кошелька"""
        for wallet in self.wallets:
            if wallet["address"].lower() == address.lower() and wallet["chain"] == chain:
                return wallet
        return None
    
    def get_active_wallets(self) -> List[Dict]:
        """Получение активных кошельков"""
        return [w for w in self.wallets if w.get("is_active", True)]
    
    def deactivate_wallet(self, address: str, chain: str, reason: str):
        """Деактивация кошелька"""
        wallet = self.get_wallet(address, chain)
        if wallet:
            wallet["is_active"] = False
            wallet["deactivated_at"] = datetime.utcnow().isoformat()
            wallet["deactivation_reason"] = reason
            self._save()
            logger.info(f"❌ [WALLET_DB] Деактивирован: {address[:10]}... ({reason})")
    
    def update_wallet_score(self, address: str, chain: str, new_score: int):
        """Обновление скора кошелька"""
        wallet = self.get_wallet(address, chain)
        if wallet:
            old_score = wallet.get("score", 50)
            wallet["score"] = max(0, min(100, new_score))
            wallet["score_updated_at"] = datetime.utcnow().isoformat()
            self._save()
            
            if abs(new_score - old_score) > 10:
                logger.info(f"📊 [WALLET_DB] Скор обновлён: {address[:10]}... {old_score} → {new_score}")