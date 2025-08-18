"""
移动平均策略
双均线交叉策略实现
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

from .base_strategy import BaseStrategy


class MovingAverageStrategy(BaseStrategy):
    """移动平均策略"""
    
    def __init__(self, name: str = "MA策略", symbol: str = "BTCUSDT", parameters: Dict[str, Any] = None):
        # 默认参数
        default_params = {
            'fast_ma_period': 10,    # 快速均线周期
            'slow_ma_period': 30,    # 慢速均线周期
            'volume': 1.0,           # 交易数量
            'max_bars': 500          # 最大K线数量
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name, symbol, default_params)
        
        # 策略特定变量
        self.last_signal = None
        
        print(f"移动平均策略初始化: 快线{self.get_parameter('fast_ma_period')}, "
              f"慢线{self.get_parameter('slow_ma_period')}")
    
    def calculate_indicators(self):
        """计算技术指标"""
        if len(self.bar_df) < 2:
            return
        
        fast_period = self.get_parameter('fast_ma_period')
        slow_period = self.get_parameter('slow_ma_period')
        
        # 计算移动平均线
        if len(self.bar_df) >= fast_period:
            self.indicators['fast_ma'] = self.bar_df['close'].rolling(fast_period).mean().tolist()
        
        if len(self.bar_df) >= slow_period:
            self.indicators['slow_ma'] = self.bar_df['close'].rolling(slow_period).mean().tolist()
    
    def on_bar(self, bar):
        """K线数据处理"""
        # 确保有足够的数据
        slow_period = self.get_parameter('slow_ma_period')
        if len(self.bar_df) < slow_period + 1:
            return
        
        # 获取当前指标值
        fast_ma = self.get_indicator_value('fast_ma')
        slow_ma = self.get_indicator_value('slow_ma')
        fast_ma_prev = self.get_indicator_value('fast_ma', -2)
        slow_ma_prev = self.get_indicator_value('slow_ma', -2)
        
        if None in [fast_ma, slow_ma, fast_ma_prev, slow_ma_prev]:
            return
        
        current_price = bar.get('close_price', 0)
        volume = self.get_parameter('volume')
        
        # 均线交叉信号
        signal = None
        
        # 金叉：快线上穿慢线
        if fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma:
            signal = "BUY"
            print(f"检测到金叉信号: 快线{fast_ma:.4f}, 慢线{slow_ma:.4f}")
        
        # 死叉：快线下穿慢线
        elif fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma:
            signal = "SELL"
            print(f"检测到死叉信号: 快线{fast_ma:.4f}, 慢线{slow_ma:.4f}")
        
        # 执行交易信号
        if signal and signal != self.last_signal:
            if signal == "BUY":
                buy_signal = self.buy(current_price, volume)
                print(f"执行买入: {buy_signal}")
            elif signal == "SELL":
                sell_signal = self.sell(current_price, volume)
                print(f"执行卖出: {sell_signal}")
            
            self.last_signal = signal
    
    def get_current_signals(self) -> Dict[str, Any]:
        """获取当前信号状态"""
        fast_ma = self.get_indicator_value('fast_ma')
        slow_ma = self.get_indicator_value('slow_ma')
        
        signals = {
            'fast_ma': fast_ma,
            'slow_ma': slow_ma,
            'trend': 'UP' if fast_ma and slow_ma and fast_ma > slow_ma else 'DOWN',
            'last_signal': self.last_signal,
            'position_size': self.position_size
        }
        
        return signals