"""
简单回测引擎
基本的策略回测功能
"""
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class SimpleBacktestEngine:
    """简单回测引擎"""
    
    def __init__(self, initial_capital: float = 100000, commission_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.current_capital = initial_capital
        
        # 交易记录
        self.trades = []
        self.positions = []
        self.equity_curve = [initial_capital]
        
        # 统计
        self.total_trades = 0
        self.win_trades = 0
        self.total_pnl = 0.0
        
        print(f"回测引擎初始化: 初始资金{initial_capital}, 手续费率{commission_rate}")
    
    def run_backtest(self, strategy, data: List[Dict]) -> Dict[str, Any]:
        """运行回测"""
        print(f"开始回测策略: {strategy.name}")
        print(f"数据长度: {len(data)}条")
        
        # 重置策略和引擎状态
        strategy.reset()
        strategy.start()
        
        self.current_capital = self.initial_capital
        self.trades.clear()
        self.positions.clear()
        self.equity_curve = [self.initial_capital]
        
        # 逐K线回测
        for i, bar in enumerate(data):
            # 记录当前策略状态
            prev_signal = getattr(strategy, 'last_signal', None) if hasattr(strategy, 'last_signal') else getattr(strategy, 'last_rsi_signal', None)
            
            # 添加K线到策略
            strategy.add_bar(bar)
            
            # 检查是否产生新信号
            current_signal = getattr(strategy, 'last_signal', None) if hasattr(strategy, 'last_signal') else getattr(strategy, 'last_rsi_signal', None)
            
            # 如果产生了新信号，记录交易
            if current_signal != prev_signal and current_signal is not None:
                self._record_trade(bar, current_signal, strategy.get_parameter('volume', 1.0))
            
            # 更新权益曲线
            current_equity = self._calculate_current_equity(bar.get('close_price', 0))
            self.equity_curve.append(current_equity)
        
        strategy.stop()
        
        # 计算最终结果
        results = self._calculate_results()
        return results
    
    def _record_trade(self, bar: Dict, signal: str, volume: float):
        """记录交易"""
        price = bar.get('close_price', 0)
        timestamp = bar.get('datetime', datetime.now())
        
        trade = {
            'timestamp': timestamp,
            'price': price,
            'volume': volume,
            'direction': signal,
            'commission': price * volume * self.commission_rate
        }
        
        self.trades.append(trade)
        self.total_trades += 1
        
        print(f"记录交易: {timestamp} {signal} {volume}@{price}")
    
    def _calculate_current_equity(self, current_price: float) -> float:
        """计算当前权益"""
        # 简化计算：假设所有交易都是即时成交的
        cash = self.initial_capital
        position = 0
        
        for trade in self.trades:
            if trade['direction'] == 'BUY':
                cash -= trade['price'] * trade['volume'] + trade['commission']
                position += trade['volume']
            elif trade['direction'] == 'SELL':
                cash += trade['price'] * trade['volume'] - trade['commission']
                position -= trade['volume']
        
        # 当前权益 = 现金 + 持仓价值
        position_value = position * current_price
        return cash + position_value
    
    def _calculate_results(self) -> Dict[str, Any]:
        """计算回测结果"""
        if not self.equity_curve:
            return {}
        
        # 基本指标
        final_capital = self.equity_curve[-1]
        total_return = (final_capital - self.initial_capital) / self.initial_capital
        
        # 收益率序列
        equity_series = np.array(self.equity_curve)
        returns = np.diff(equity_series) / equity_series[:-1]
        returns = returns[~np.isnan(returns)]  # 移除NaN值
        
        # 最大回撤
        peak = np.maximum.accumulate(equity_series)
        drawdown = (peak - equity_series) / peak
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # 夏普比率（简化）
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # 交易统计
        winning_trades = 0
        if len(self.trades) >= 2:
            for i in range(0, len(self.trades) - 1, 2):
                if i + 1 < len(self.trades):
                    buy_trade = self.trades[i]
                    sell_trade = self.trades[i + 1]
                    if buy_trade['direction'] == 'BUY' and sell_trade['direction'] == 'SELL':
                        pnl = (sell_trade['price'] - buy_trade['price']) * buy_trade['volume']
                        pnl -= buy_trade['commission'] + sell_trade['commission']
                        if pnl > 0:
                            winning_trades += 1
        
        win_rate = winning_trades / (len(self.trades) / 2) if len(self.trades) >= 2 else 0
        
        results = {
            'start_date': self.trades[0]['timestamp'].strftime('%Y-%m-%d') if self.trades else 'N/A',
            'end_date': self.trades[-1]['timestamp'].strftime('%Y-%m-%d') if self.trades else 'N/A',
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(self.trades),
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'win_rate_pct': win_rate * 100,
            'equity_curve': self.equity_curve.copy(),
            'trades': self.trades.copy()
        }
        
        return results


def run_simple_backtest(strategy, data: List[Dict], initial_capital: float = 100000) -> Dict[str, Any]:
    """运行简单回测的便捷函数"""
    engine = SimpleBacktestEngine(initial_capital)
    return engine.run_backtest(strategy, data)