"""
PERFORMANCE STATISTICS
Детальная статистика эффективности торговли
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class PerformanceMetrics:
    """Метрики эффективности"""
    
    # Временной период
    period_start: datetime
    period_end: datetime
    
    # Общие метрики
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    
    # Win Rate
    win_rate: float  # %
    
    # P&L
    total_pnl_usd: float
    total_pnl_pct: float
    avg_pnl_per_trade_usd: float
    avg_pnl_per_trade_pct: float
    
    # Прибыльные сделки
    avg_win_usd: float
    avg_win_pct: float
    max_win_usd: float
    max_win_pct: float
    total_wins_usd: float
    
    # Убыточные сделки
    avg_loss_usd: float
    avg_loss_pct: float
    max_loss_usd: float
    max_loss_pct: float
    total_losses_usd: float
    
    # Risk/Reward
    profit_factor: float  # Total Wins / Total Losses
    avg_risk_reward_ratio: float  # Avg Win / Avg Loss
    
    # Streak
    max_consecutive_wins: int
    max_consecutive_losses: int
    current_streak: int  # Положительное = выигрыши, отрицательное = проигрыши
    
    # Drawdown
    max_drawdown_usd: float
    max_drawdown_pct: float
    current_drawdown_usd: float
    current_drawdown_pct: float
    
    # Время удержания
    avg_hold_time_hours: float
    median_hold_time_hours: float
    min_hold_time_hours: float
    max_hold_time_hours: float
    
    # По типам позиций
    long_trades: int
    long_win_rate: float
    long_pnl_usd: float
    short_trades: int
    short_win_rate: float
    short_pnl_usd: float
    
    # По активам (топ-5)
    top_assets_by_pnl: List[Tuple[str, float]]
    worst_assets_by_pnl: List[Tuple[str, float]]
    
    # Sharpe Ratio (если есть достаточно данных)
    sharpe_ratio: Optional[float] = None
    
    # Expectancy (математическое ожидание)
    expectancy: float = 0.0
    
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        data = asdict(self)
        data['period_start'] = self.period_start.isoformat()
        data['period_end'] = self.period_end.isoformat()
        return data


class PerformanceStats:
    """
    Статистика эффективности торговли
    
    Функции:
    - Расчет всех ключевых метрик
    - Win rate, profit factor, expectancy
    - Sharpe ratio, max drawdown
    - Анализ по активам, типам позиций, временным периодам
    - Экспорт отчетов
    - Визуализация (опционально)
    """
    
    def __init__(self, position_tracker):
        self.position_tracker = position_tracker
        
        # Кэш метрик
        self.cached_metrics: Dict[str, PerformanceMetrics] = {}
        self.cache_ttl = 300  # 5 минут
        
        print("📈 [PERFORMANCE] Stats инициализирован")
    
    async def calculate_metrics(
        self,
        period_days: Optional[int] = None,
        asset: Optional[str] = None
    ) -> PerformanceMetrics:
        """
        Расчет метрик производительности
        
        Args:
            period_days: Период в днях (None = все время)
            asset: Конкретный актив (None = все активы)
        
        Returns:
            PerformanceMetrics
        """
        
        # Проверяем кэш
        cache_key = f"{period_days}_{asset}"
        if cache_key in self.cached_metrics:
            cached = self.cached_metrics[cache_key]
            age = (datetime.utcnow() - cached.period_end).seconds
            if age < self.cache_ttl:
                return cached
        
        # Получаем закрытые позиции
        all_positions = await self.position_tracker.get_closed_positions(limit=10000)
        
        # Фильтруем по периоду
        if period_days:
            cutoff = datetime.utcnow() - timedelta(days=period_days)
            positions = [p for p in all_positions if p.closed_at and p.closed_at >= cutoff]
            period_start = cutoff
        else:
            positions = all_positions
            period_start = positions[-1].opened_at if positions else datetime.utcnow()
        
        # Фильтруем по активу
        if asset:
            positions = [p for p in positions if p.asset == asset]
        
        if not positions:
            return self._empty_metrics(period_start, datetime.utcnow())
        
        period_end = datetime.utcnow()
        
        # Расчет метрик
        metrics = self._calculate_all_metrics(positions, period_start, period_end)
        
        # Кэшируем
        self.cached_metrics[cache_key] = metrics
        
        return metrics
    
    def _calculate_all_metrics(
        self,
        positions: List,
        period_start: datetime,
        period_end: datetime
    ) -> PerformanceMetrics:
        """Полный расчет всех метрик"""
        
        # Базовые подсчеты
        total_trades = len(positions)
        
        winning_trades = sum(1 for p in positions if p.realized_pnl_usd and p.realized_pnl_usd > 0)
        losing_trades = sum(1 for p in positions if p.realized_pnl_usd and p.realized_pnl_usd < 0)
        breakeven_trades = sum(1 for p in positions if p.realized_pnl_usd == 0)
        
        # Win Rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # P&L
        total_pnl_usd = sum(p.realized_pnl_usd or 0 for p in positions)
        
        total_capital = sum(p.amount_usd for p in positions)
        total_pnl_pct = (total_pnl_usd / total_capital * 100) if total_capital > 0 else 0
        
        avg_pnl_per_trade_usd = total_pnl_usd / total_trades if total_trades > 0 else 0
        avg_pnl_per_trade_pct = sum(p.realized_pnl_pct or 0 for p in positions) / total_trades if total_trades > 0 else 0
        
        # Прибыльные сделки
        wins = [p for p in positions if p.realized_pnl_usd and p.realized_pnl_usd > 0]
        
        if wins:
            avg_win_usd = sum(p.realized_pnl_usd for p in wins) / len(wins)
            avg_win_pct = sum(p.realized_pnl_pct for p in wins) / len(wins)
            max_win_usd = max(p.realized_pnl_usd for p in wins)
            max_win_pct = max(p.realized_pnl_pct for p in wins)
            total_wins_usd = sum(p.realized_pnl_usd for p in wins)
        else:
            avg_win_usd = avg_win_pct = max_win_usd = max_win_pct = total_wins_usd = 0
        
        # Убыточные сделки
        losses = [p for p in positions if p.realized_pnl_usd and p.realized_pnl_usd < 0]
        
        if losses:
            avg_loss_usd = sum(p.realized_pnl_usd for p in losses) / len(losses)
            avg_loss_pct = sum(p.realized_pnl_pct for p in losses) / len(losses)
            max_loss_usd = min(p.realized_pnl_usd for p in losses)
            max_loss_pct = min(p.realized_pnl_pct for p in losses)
            total_losses_usd = sum(p.realized_pnl_usd for p in losses)
        else:
            avg_loss_usd = avg_loss_pct = max_loss_usd = max_loss_pct = total_losses_usd = 0
        
        # Profit Factor
        profit_factor = abs(total_wins_usd / total_losses_usd) if total_losses_usd != 0 else float('inf')
        
        # Risk/Reward Ratio
        avg_risk_reward_ratio = abs(avg_win_usd / avg_loss_usd) if avg_loss_usd != 0 else 0
        
        # Expectancy (математическое ожидание)
        if total_trades > 0:
            expectancy = (win_rate / 100 * avg_win_usd) + ((1 - win_rate / 100) * avg_loss_usd)
        else:
            expectancy = 0
        
        # Streak
        max_consecutive_wins, max_consecutive_losses, current_streak = self._calculate_streaks(positions)
        
        # Drawdown
        max_dd_usd, max_dd_pct, curr_dd_usd, curr_dd_pct = self._calculate_drawdown(positions)
        
        # Время удержания
        hold_times = []
        for p in positions:
            if p.opened_at and p.closed_at:
                hours = (p.closed_at - p.opened_at).total_seconds() / 3600
                hold_times.append(hours)
        
        if hold_times:
            avg_hold_time = np.mean(hold_times)
            median_hold_time = np.median(hold_times)
            min_hold_time = min(hold_times)
            max_hold_time = max(hold_times)
        else:
            avg_hold_time = median_hold_time = min_hold_time = max_hold_time = 0
        
        # По типам позиций
        long_positions = [p for p in positions if p.position_type == 'long']
        short_positions = [p for p in positions if p.position_type == 'short']
        
        long_trades = len(long_positions)
        long_wins = sum(1 for p in long_positions if p.realized_pnl_usd and p.realized_pnl_usd > 0)
        long_win_rate = (long_wins / long_trades * 100) if long_trades > 0 else 0
        long_pnl_usd = sum(p.realized_pnl_usd or 0 for p in long_positions)
        
        short_trades = len(short_positions)
        short_wins = sum(1 for p in short_positions if p.realized_pnl_usd and p.realized_pnl_usd > 0)
        short_win_rate = (short_wins / short_trades * 100) if short_trades > 0 else 0
        short_pnl_usd = sum(p.realized_pnl_usd or 0 for p in short_positions)
        
        # По активам
        asset_pnl = defaultdict(float)
        for p in positions:
            asset_pnl[p.asset] += p.realized_pnl_usd or 0
        
        sorted_assets = sorted(asset_pnl.items(), key=lambda x: x[1], reverse=True)
        top_assets = sorted_assets[:5]
        worst_assets = sorted_assets[-5:][::-1]
        
        # Sharpe Ratio (если есть достаточно данных)
        sharpe_ratio = None
        if len(positions) >= 30:
            returns = [p.realized_pnl_pct or 0 for p in positions]
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
        
        return PerformanceMetrics(
            period_start=period_start,
            period_end=period_end,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            breakeven_trades=breakeven_trades,
            win_rate=win_rate,
            total_pnl_usd=total_pnl_usd,
            total_pnl_pct=total_pnl_pct,
            avg_pnl_per_trade_usd=avg_pnl_per_trade_usd,
            avg_pnl_per_trade_pct=avg_pnl_per_trade_pct,
            avg_win_usd=avg_win_usd,
            avg_win_pct=avg_win_pct,
            max_win_usd=max_win_usd,
            max_win_pct=max_win_pct,
            total_wins_usd=total_wins_usd,
            avg_loss_usd=avg_loss_usd,
            avg_loss_pct=avg_loss_pct,
            max_loss_usd=max_loss_usd,
            max_loss_pct=max_loss_pct,
            total_losses_usd=total_losses_usd,
            profit_factor=profit_factor,
            avg_risk_reward_ratio=avg_risk_reward_ratio,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            current_streak=current_streak,
            max_drawdown_usd=max_dd_usd,
            max_drawdown_pct=max_dd_pct,
            current_drawdown_usd=curr_dd_usd,
            current_drawdown_pct=curr_dd_pct,
            avg_hold_time_hours=avg_hold_time,
            median_hold_time_hours=median_hold_time,
            min_hold_time_hours=min_hold_time,
            max_hold_time_hours=max_hold_time,
            long_trades=long_trades,
            long_win_rate=long_win_rate,
            long_pnl_usd=long_pnl_usd,
            short_trades=short_trades,
            short_win_rate=short_win_rate,
            short_pnl_usd=short_pnl_usd,
            top_assets_by_pnl=top_assets,
            worst_assets_by_pnl=worst_assets,
            sharpe_ratio=sharpe_ratio,
            expectancy=expectancy
        )
    
    def _calculate_streaks(self, positions: List) -> Tuple[int, int, int]:
        """Расчет серий побед/поражений"""
        
        max_win_streak = 0
        max_loss_streak = 0
        current_streak = 0
        
        current_win_streak = 0
        current_loss_streak = 0
        
        for p in sorted(positions, key=lambda x: x.closed_at or datetime.utcnow()):
            if p.realized_pnl_usd and p.realized_pnl_usd > 0:
                current_win_streak += 1
                current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
            elif p.realized_pnl_usd and p.realized_pnl_usd < 0:
                current_loss_streak += 1
                current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        # Текущая серия
        if current_win_streak > 0:
            current_streak = current_win_streak
        elif current_loss_streak > 0:
            current_streak = -current_loss_streak
        else:
            current_streak = 0
        
        return max_win_streak, max_loss_streak, current_streak
    
    def _calculate_drawdown(self, positions: List) -> Tuple[float, float, float, float]:
        """Расчет максимальной и текущей просадки"""
        
        # Сортируем по времени закрытия
        sorted_positions = sorted(positions, key=lambda x: x.closed_at or datetime.utcnow())
        
        # Строим кривую капитала
        cumulative_pnl = 0
        peak = 0
        max_drawdown_usd = 0
        max_drawdown_pct = 0
        
        equity_curve = []
        
        for p in sorted_positions:
            cumulative_pnl += p.realized_pnl_usd or 0
            equity_curve.append(cumulative_pnl)
            
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown_usd:
                max_drawdown_usd = drawdown
                max_drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0
        
        # Текущая просадка
        current_equity = equity_curve[-1] if equity_curve else 0
        current_peak = max(equity_curve) if equity_curve else 0
        current_drawdown_usd = current_peak - current_equity
        current_drawdown_pct = (current_drawdown_usd / current_peak * 100) if current_peak > 0 else 0
        
        return max_drawdown_usd, max_drawdown_pct, current_drawdown_usd, current_drawdown_pct
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0) -> float:
        """
        Расчет Sharpe Ratio
        
        Sharpe Ratio = (Mean Return - Risk Free Rate) / Std Dev of Returns
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        
        if std_return == 0:
            return 0.0
        
        sharpe = (mean_return - risk_free_rate) / std_return
        
        # Аннуализируем (предполагая что returns - это % за сделку)
        # Если в среднем 1 сделка в день, умножаем на sqrt(365)
        annualized_sharpe = sharpe * np.sqrt(365)
        
        return annualized_sharpe
    
    def _empty_metrics(self, start: datetime, end: datetime) -> PerformanceMetrics:
        """Пустые метрики (когда нет сделок)"""
        return PerformanceMetrics(
            period_start=start,
            period_end=end,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            breakeven_trades=0,
            win_rate=0,
            total_pnl_usd=0,
            total_pnl_pct=0,
            avg_pnl_per_trade_usd=0,
            avg_pnl_per_trade_pct=0,
            avg_win_usd=0,
            avg_win_pct=0,
            max_win_usd=0,
            max_win_pct=0,
            total_wins_usd=0,
            avg_loss_usd=0,
            avg_loss_pct=0,
            max_loss_usd=0,
            max_loss_pct=0,
            total_losses_usd=0,
            profit_factor=0,
            avg_risk_reward_ratio=0,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            current_streak=0,
            max_drawdown_usd=0,
            max_drawdown_pct=0,
            current_drawdown_usd=0,
            current_drawdown_pct=0,
            avg_hold_time_hours=0,
            median_hold_time_hours=0,
            min_hold_time_hours=0,
            max_hold_time_hours=0,
            long_trades=0,
            long_win_rate=0,
            long_pnl_usd=0,
            short_trades=0,
            short_win_rate=0,
            short_pnl_usd=0,
            top_assets_by_pnl=[],
            worst_assets_by_pnl=[]
        )
    
    async def get_equity_curve(self, period_days: Optional[int] = None) -> List[Dict]:
        """
        Получение кривой капитала
        
        Returns:
            [{'timestamp': datetime, 'equity': float, 'pnl': float}, ...]
        """
        
        positions = await self.position_tracker.get_closed_positions(limit=10000)
        
        if period_days:
            cutoff = datetime.utcnow() - timedelta(days=period_days)
            positions = [p for p in positions if p.closed_at and p.closed_at >= cutoff]
        
        sorted_positions = sorted(positions, key=lambda x: x.closed_at or datetime.utcnow())
        
        equity_curve = []
        cumulative_pnl = 0
        
        for p in sorted_positions:
            cumulative_pnl += p.realized_pnl_usd or 0
            equity_curve.append({
                'timestamp': p.closed_at,
                'equity': cumulative_pnl,
                'pnl': p.realized_pnl_usd or 0
            })
        
        return equity_curve
    
    async def export_report(self, filepath: str, period_days: Optional[int] = None):
        """
        Экспорт детального отчета в JSON
        
        Args:
            filepath: Путь к файлу
            period_days: Период в днях
        """
        
        metrics = await self.calculate_metrics(period_days)
        equity_curve = await self.get_equity_curve(period_days)
        
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'period_days': period_days,
            'metrics': metrics.to_dict(),
            'equity_curve': [
                {
                    'timestamp': point['timestamp'].isoformat(),
                    'equity': point['equity'],
                    'pnl': point['pnl']
                }
                for point in equity_curve
            ]
        }
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 [PERFORMANCE] Отчет экспортирован: {filepath}")
    
    def format_summary(self, metrics: PerformanceMetrics) -> str:
        """Форматирование краткой сводки для вывода"""
        
        summary = f"""
{'='*80}
📊 PERFORMANCE SUMMARY
{'='*80}

PERIOD: {metrics.period_start.strftime('%Y-%m-%d')} → {metrics.period_end.strftime('%Y-%m-%d')}

OVERVIEW:
  Total Trades: {metrics.total_trades}
  Win Rate: {metrics.win_rate:.2f}%
  Total P&L: ${metrics.total_pnl_usd:,.2f} ({metrics.total_pnl_pct:+.2f}%)
  
WINNING TRADES:
  Count: {metrics.winning_trades}
  Average: ${metrics.avg_win_usd:,.2f} ({metrics.avg_win_pct:+.2f}%)
  Max Win: ${metrics.max_win_usd:,.2f} ({metrics.max_win_pct:+.2f}%)
  Total: ${metrics.total_wins_usd:,.2f}
  
LOSING TRADES:
  Count: {metrics.losing_trades}
  Average: ${metrics.avg_loss_usd:,.2f} ({metrics.avg_loss_pct:.2f}%)
  Max Loss: ${metrics.max_loss_usd:,.2f} ({metrics.max_loss_pct:.2f}%)
  Total: ${metrics.total_losses_usd:,.2f}
  
RISK METRICS:
  Profit Factor: {metrics.profit_factor:.2f}
  Risk/Reward Ratio: {metrics.avg_risk_reward_ratio:.2f}
  Expectancy: ${metrics.expectancy:,.2f}
  Max Drawdown: ${metrics.max_drawdown_usd:,.2f} ({metrics.max_drawdown_pct:.2f}%)
  Current Drawdown: ${metrics.current_drawdown_usd:,.2f} ({metrics.current_drawdown_pct:.2f}%)
  {'Sharpe Ratio: ' + f'{metrics.sharpe_ratio:.2f}' if metrics.sharpe_ratio else ''}
  
STREAKS:
  Max Wins: {metrics.max_consecutive_wins}
  Max Losses: {metrics.max_consecutive_losses}
  Current: {'+'*(metrics.current_streak) if metrics.current_streak > 0 else '-'*abs(metrics.current_streak)} ({metrics.current_streak})
  
HOLD TIME:
  Average: {metrics.avg_hold_time_hours:.1f}h
  Median: {metrics.median_hold_time_hours:.1f}h
  Range: {metrics.min_hold_time_hours:.1f}h - {metrics.max_hold_time_hours:.1f}h
  
BY POSITION TYPE:
  LONG: {metrics.long_trades} trades, {metrics.long_win_rate:.1f}% WR, ${metrics.long_pnl_usd:,.2f} P&L
  SHORT: {metrics.short_trades} trades, {metrics.short_win_rate:.1f}% WR, ${metrics.short_pnl_usd:,.2f} P&L
  
TOP ASSETS:
{self._format_asset_list(metrics.top_assets_by_pnl, 'BEST')}

WORST ASSETS:
{self._format_asset_list(metrics.worst_assets_by_pnl, 'WORST')}

{'='*80}
"""
        
        return summary
    
    def _format_asset_list(self, assets: List[Tuple[str, float]], label: str) -> str:
        """Форматирование списка активов"""
        if not assets:
            return f"  {label}: No data"
        
        lines = []
        for i, (asset, pnl) in enumerate(assets, 1):
            lines.append(f"  {i}. {asset}: ${pnl:,.2f}")
        
        return '\n'.join(lines)