"""
POSITION TRACKER
Полное отслеживание торговых позиций с метриками
"""

import json
import aiosqlite
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum


class PositionStatus(Enum):
    """Статус позиции"""
    OPEN = "open"
    CLOSED = "closed"
    STOPPED = "stopped"  # Закрыта по stop-loss
    TAKEN = "taken"  # Закрыта по take-profit


class PositionType(Enum):
    """Тип позиции"""
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    """Торговая позиция"""
    id: str
    asset: str
    chain: str
    
    # Параметры позиции
    position_type: str  # 'long' or 'short'
    entry_price: float
    amount: float  # Количество актива
    amount_usd: float  # Размер позиции в USD
    
    # Stop-loss и Take-profit
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Временные метки
    opened_at: datetime = None
    closed_at: Optional[datetime] = None
    
    # Закрытие позиции
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    status: str = "open"
    
    # P&L
    realized_pnl_usd: Optional[float] = None
    realized_pnl_pct: Optional[float] = None
    
    # Текущие метрики (для открытых позиций)
    current_price: Optional[float] = None
    unrealized_pnl_usd: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    
    # Сигналы которые привели к открытию
    signals: Dict = None
    
    # Максимальная прибыль/убыток во время удержания
    max_pnl_usd: float = 0.0
    max_pnl_pct: float = 0.0
    max_drawdown_usd: float = 0.0
    max_drawdown_pct: float = 0.0
    
    # Метаданные
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.opened_at is None:
            self.opened_at = datetime.utcnow()
        if self.signals is None:
            self.signals = {}
    
    def update_current_price(self, price: float):
        """Обновление текущей цены и расчет unrealized P&L"""
        self.current_price = price
        
        if self.position_type == 'long':
            pnl_usd = (price - self.entry_price) * self.amount
            pnl_pct = ((price - self.entry_price) / self.entry_price) * 100
        else:  # short
            pnl_usd = (self.entry_price - price) * self.amount
            pnl_pct = ((self.entry_price - price) / self.entry_price) * 100
        
        self.unrealized_pnl_usd = pnl_usd
        self.unrealized_pnl_pct = pnl_pct
        
        # Обновляем максимумы/минимумы
        if pnl_usd > self.max_pnl_usd:
            self.max_pnl_usd = pnl_usd
            self.max_pnl_pct = pnl_pct
        
        if pnl_usd < -self.max_drawdown_usd:
            self.max_drawdown_usd = -pnl_usd
            self.max_drawdown_pct = -pnl_pct
    
    def should_stop_loss(self) -> bool:
        """Проверка stop-loss"""
        if not self.stop_loss or not self.current_price:
            return False
        
        if self.position_type == 'long':
            return self.current_price <= self.stop_loss
        else:
            return self.current_price >= self.stop_loss
    
    def should_take_profit(self) -> bool:
        """Проверка take-profit"""
        if not self.take_profit or not self.current_price:
            return False
        
        if self.position_type == 'long':
            return self.current_price >= self.take_profit
        else:
            return self.current_price <= self.take_profit
    
    def close(self, exit_price: float, reason: str = "manual"):
        """Закрытие позиции"""
        self.exit_price = exit_price
        self.exit_reason = reason
        self.closed_at = datetime.utcnow()
        
        # Определяем статус
        if reason == "stop_loss":
            self.status = "stopped"
        elif reason == "take_profit":
            self.status = "taken"
        else:
            self.status = "closed"
        
        # Расчет realized P&L
        if self.position_type == 'long':
            self.realized_pnl_usd = (exit_price - self.entry_price) * self.amount
            self.realized_pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:
            self.realized_pnl_usd = (self.entry_price - exit_price) * self.amount
            self.realized_pnl_pct = ((self.entry_price - exit_price) / self.entry_price) * 100
    
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        data = asdict(self)
        data['opened_at'] = self.opened_at.isoformat() if self.opened_at else None
        data['closed_at'] = self.closed_at.isoformat() if self.closed_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Position':
        """Создание из словаря"""
        data = data.copy()
        if data.get('opened_at'):
            data['opened_at'] = datetime.fromisoformat(data['opened_at'])
        if data.get('closed_at'):
            data['closed_at'] = datetime.fromisoformat(data['closed_at'])
        return cls(**data)


class PositionTracker:
    """
    Трекер торговых позиций
    
    Функции:
    - Открытие/закрытие позиций
    - Автоматический stop-loss и take-profit
    - Расчет P&L в реальном времени
    - История всех сделок
    - Детальная статистика по каждой позиции
    - Persistence в SQLite
    """
    
    def __init__(self, db_path: str = 'data/positions.db'):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Открытые позиции (в памяти для быстрого доступа)
        self.open_positions: Dict[str, Position] = {}
        
        # Инициализация DB
        self._init_db()
        
        # Загрузка открытых позиций
        self._load_open_positions()
        
        print("📊 [POSITIONS] Tracker инициализирован")
        print(f"   Открытых позиций: {len(self.open_positions)}")
    
    def _init_db(self):
        """Инициализация базы данных"""
        import sqlite3
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                asset TEXT NOT NULL,
                chain TEXT NOT NULL,
                position_type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                amount REAL NOT NULL,
                amount_usd REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                exit_price REAL,
                exit_reason TEXT,
                status TEXT NOT NULL,
                realized_pnl_usd REAL,
                realized_pnl_pct REAL,
                current_price REAL,
                unrealized_pnl_usd REAL,
                unrealized_pnl_pct REAL,
                max_pnl_usd REAL DEFAULT 0,
                max_pnl_pct REAL DEFAULT 0,
                max_drawdown_usd REAL DEFAULT 0,
                max_drawdown_pct REAL DEFAULT 0,
                signals TEXT,
                notes TEXT
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON positions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_asset ON positions(asset)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_opened_at ON positions(opened_at)')
        
        conn.commit()
        conn.close()
        
        print("✅ [POSITIONS] База данных инициализирована")
    
    def _load_open_positions(self):
        """Загрузка открытых позиций из DB"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM positions WHERE status = 'open'")
            rows = cursor.fetchall()
            
            for row in rows:
                data = dict(row)
                
                # Парсим JSON signals
                if data['signals']:
                    data['signals'] = json.loads(data['signals'])
                
                position = Position.from_dict(data)
                self.open_positions[position.id] = position
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ [POSITIONS] Ошибка загрузки позиций: {e}")
    
    async def open_position(
        self,
        asset: str,
        chain: str,
        position_type: str,
        entry_price: float,
        amount_usd: float,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        signals: Optional[Dict] = None,
        notes: Optional[str] = None
    ) -> Position:
        """
        Открытие новой позиции
        
        Args:
            asset: Символ актива
            chain: Блокчейн
            position_type: 'long' или 'short'
            entry_price: Цена входа
            amount_usd: Размер позиции в USD
            stop_loss_pct: Stop-loss в % (например, 5 для -5%)
            take_profit_pct: Take-profit в % (например, 10 для +10%)
            signals: Сигналы которые привели к открытию
            notes: Заметки
        
        Returns:
            Position
        """
        
        # Генерируем ID
        position_id = f"{asset}_{chain}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Рассчитываем количество актива
        amount = amount_usd / entry_price
        
        # Рассчитываем stop-loss и take-profit цены
        stop_loss = None
        take_profit = None
        
        if stop_loss_pct:
            if position_type == 'long':
                stop_loss = entry_price * (1 - stop_loss_pct / 100)
            else:
                stop_loss = entry_price * (1 + stop_loss_pct / 100)
        
        if take_profit_pct:
            if position_type == 'long':
                take_profit = entry_price * (1 + take_profit_pct / 100)
            else:
                take_profit = entry_price * (1 - take_profit_pct / 100)
        
        # Создаем позицию
        position = Position(
            id=position_id,
            asset=asset,
            chain=chain,
            position_type=position_type,
            entry_price=entry_price,
            amount=amount,
            amount_usd=amount_usd,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signals=signals or {},
            notes=notes
        )
        
        # Сохраняем
        self.open_positions[position_id] = position
        await self._save_position(position)
        
        print(f"✅ [POSITIONS] Открыта позиция: {position_id}")
        print(f"   {position_type.upper()} {asset} @ ${entry_price:,.2f}")
        print(f"   Размер: ${amount_usd:,.2f} ({amount:.4f} {asset})")
        if stop_loss:
            print(f"   Stop-Loss: ${stop_loss:,.2f} (-{stop_loss_pct}%)")
        if take_profit:
            print(f"   Take-Profit: ${take_profit:,.2f} (+{take_profit_pct}%)")
        
        return position
    
    async def close_position(
        self,
        position_id: str,
        exit_price: float,
        reason: str = "manual"
    ) -> Optional[Position]:
        """
        Закрытие позиции
        
        Args:
            position_id: ID позиции
            exit_price: Цена выхода
            reason: Причина закрытия
        
        Returns:
            Закрытая позиция или None
        """
        
        position = self.open_positions.get(position_id)
        
        if not position:
            print(f"⚠️ [POSITIONS] Позиция {position_id} не найдена")
            return None
        
        # Закрываем
        position.close(exit_price, reason)
        
        # Удаляем из открытых
        del self.open_positions[position_id]
        
        # Обновляем в DB
        await self._save_position(position)
        
        print(f"✅ [POSITIONS] Закрыта позиция: {position_id}")
        print(f"   {position.position_type.upper()} {position.asset}")
        print(f"   Вход: ${position.entry_price:,.2f} → Выход: ${exit_price:,.2f}")
        print(f"   P&L: ${position.realized_pnl_usd:,.2f} ({position.realized_pnl_pct:+.2f}%)")
        print(f"   Причина: {reason}")
        
        return position
    
    async def update_prices(self, prices: Dict[str, float]):
        """
        Обновление текущих цен для всех открытых позиций
        
        Args:
            prices: {asset: price}
        """
        
        positions_to_close = []
        
        for position in self.open_positions.values():
            price = prices.get(position.asset)
            
            if not price:
                continue
            
            # Обновляем цену
            position.update_current_price(price)
            
            # Проверяем stop-loss и take-profit
            if position.should_stop_loss():
                positions_to_close.append((position.id, price, "stop_loss"))
            elif position.should_take_profit():
                positions_to_close.append((position.id, price, "take_profit"))
            
            # Сохраняем обновленную позицию
            await self._save_position(position)
        
        # Закрываем позиции по stop-loss/take-profit
        for position_id, exit_price, reason in positions_to_close:
            await self.close_position(position_id, exit_price, reason)
    
    async def _save_position(self, position: Position):
        """Сохранение позиции в DB"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Сериализуем signals
            signals_json = json.dumps(position.signals) if position.signals else None
            
            cursor.execute('''
                INSERT OR REPLACE INTO positions VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            ''', (
                position.id,
                position.asset,
                position.chain,
                position.position_type,
                position.entry_price,
                position.amount,
                position.amount_usd,
                position.stop_loss,
                position.take_profit,
                position.opened_at.isoformat(),
                position.closed_at.isoformat() if position.closed_at else None,
                position.exit_price,
                position.exit_reason,
                position.status,
                position.realized_pnl_usd,
                position.realized_pnl_pct,
                position.current_price,
                position.unrealized_pnl_usd,
                position.unrealized_pnl_pct,
                position.max_pnl_usd,
                position.max_pnl_pct,
                position.max_drawdown_usd,
                position.max_drawdown_pct,
                signals_json,
                position.notes
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ [POSITIONS] Ошибка сохранения: {e}")
    
    def get_open_positions(self) -> List[Position]:
        """Получить все открытые позиции"""
        return list(self.open_positions.values())
    
    def get_position(self, position_id: str) -> Optional[Position]:
        """Получить конкретную позицию"""
        return self.open_positions.get(position_id)
    
    async def get_closed_positions(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Position]:
        """Получить закрытые позиции"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM positions 
                WHERE status != 'open' 
                ORDER BY closed_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            positions = []
            for row in rows:
                data = dict(row)
                if data['signals']:
                    data['signals'] = json.loads(data['signals'])
                positions.append(Position.from_dict(data))
            
            return positions
            
        except Exception as e:
            print(f"❌ [POSITIONS] Ошибка загрузки закрытых позиций: {e}")
            return []
    
    async def get_positions_by_asset(self, asset: str) -> List[Position]:
        """Получить все позиции по активу"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM positions 
                WHERE asset = ? 
                ORDER BY opened_at DESC
            ''', (asset,))
            
            rows = cursor.fetchall()
            conn.close()
            
            positions = []
            for row in rows:
                data = dict(row)
                if data['signals']:
                    data['signals'] = json.loads(data['signals'])
                positions.append(Position.from_dict(data))
            
            return positions
            
        except Exception as e:
            print(f"❌ [POSITIONS] Ошибка загрузки позиций по {asset}: {e}")
            return []
    
    def get_summary(self) -> Dict:
        """Краткая сводка по позициям"""
        
        total_open = len(self.open_positions)
        
        total_unrealized_pnl = sum(
            p.unrealized_pnl_usd or 0 
            for p in self.open_positions.values()
        )
        
        total_amount_usd = sum(
            p.amount_usd 
            for p in self.open_positions.values()
        )
        
        long_positions = sum(
            1 for p in self.open_positions.values() 
            if p.position_type == 'long'
        )
        
        short_positions = total_open - long_positions
        
        return {
            'total_open': total_open,
            'long_positions': long_positions,
            'short_positions': short_positions,
            'total_amount_usd': total_amount_usd,
            'total_unrealized_pnl_usd': total_unrealized_pnl,
            'unrealized_pnl_pct': (total_unrealized_pnl / total_amount_usd * 100) if total_amount_usd > 0 else 0
        }