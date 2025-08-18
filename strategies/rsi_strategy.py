"""
RSI策略
基于相对强弱指数的交易策略
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

from .base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """RSI策略"""
    
    def __init__(self, name: str = "RSI策略", symbol: str = "BTCUSDT", parameters: Dict[str, Any] = None):
        # 默认参数
        default_params = {
            'rsi_period': 14,        # RSI计算周期
            'oversold': 30,          # 超卖阈值
            'overbought': 70,        # 超买阈值
            'volume': 1.0,           # 交易数量
            'max_bars': 500          # 最大K线数量
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name, symbol, default_params)
        
        # 策略特定变量
        self.last_rsi_signal = None
        
        print(f"RSI策略初始化: 周期{self.get_parameter('rsi_period')}, "
              f"超卖{self.get_parameter('oversold')}, 超买{self.get_parameter('overbought')}")
    
    def calculate_indicators(self):
        """计算RSI指标"""
        if len(self.bar_df) < 2:
            return
        
        period = self.get_parameter('rsi_period')
        
        if len(self.bar_df) >= period + 1:
            # 计算价格变化
            close_prices = self.bar_df['close'].values
            price_changes = np.diff(close_prices)
            
            # 分离上涨和下跌
            gains = np.where(price_changes > 0, price_changes, 0)
            losses = np.where(price_changes < 0, -price_changes, 0)
            
            # 计算RSI
            rsi_values = []
            
            for i in range(len(gains)):
                if i < period - 1:
                    rsi_values.append(np.nan)
                    continue
                
                if i == period - 1:
                    # 第一个RSI值使用简单平均
                    avg_gain = np.mean(gains[i-period+1:i+1])
                    avg_loss = np.mean(losses[i-period+1:i+1])
                else:
                    # 后续RSI值使用平滑平均
                    prev_avg_gain = avg_gain
                    prev_avg_loss = avg_loss
                    avg_gain = (prev_avg_gain * (period - 1) + gains[i]) / period
                    avg_loss = (prev_avg_loss * (period - 1) + losses[i]) / period
                
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                
                rsi_values.append(rsi)
            
            self.indicators['rsi'] = rsi_values
    
    def on_bar(self, bar):
        """K线数据处理"""
        # 确保有足够的数据
        period = self.get_parameter('rsi_period')
        if len(self.bar_df) < period + 5:
            return
        
        # 获取RSI值
        rsi = self.get_indicator_value('rsi')
        rsi_prev = self.get_indicator_value('rsi', -2)
        
        if rsi is None or pd.isna(rsi) or rsi_prev is None or pd.isna(rsi_prev):
            return
        
        current_price = bar.get('close_price', 0)
        oversold = self.get_parameter('oversold')
        overbought = self.get_parameter('overbought')
        volume = self.get_parameter('volume')
        
        # RSI交易信号
        signal = None
        
        # 超卖反弹信号
        if rsi_prev <= oversold and rsi > oversold:
            signal = "BUY"
            print(f"RSI超卖反弹信号: RSI从{rsi_prev:.2f}上升到{rsi:.2f}")
        
        # 超买回调信号
        elif rsi_prev >= overbought and rsi < overbought:
            signal = "SELL"
            print(f"RSI超买回调信号: RSI从{rsi_prev:.2f}下降到{rsi:.2f}")
        
        # 执行交易信号
        if signal and signal != self.last_rsi_signal:
            if signal == "BUY":
                buy_signal = self.buy(current_price, volume)
                print(f"RSI信号买入: {buy_signal}")
            elif signal == "SELL":
                sell_signal = self.sell(current_price, volume)
                print(f"RSI信号卖出: {sell_signal}")
            
            self.last_rsi_signal = signal
    
    def get_current_signals(self) -> Dict[str, Any]:
        """获取当前信号状态"""
        rsi = self.get_indicator_value('rsi')
        oversold = self.get_parameter('oversold')
        overbought = self.get_parameter('overbought')
        
        # 判断RSI状态
        rsi_status = "NEUTRAL"
        if rsi is not None and not pd.isna(rsi):
            if rsi <= oversold:
                rsi_status = "OVERSOLD"
            elif rsi >= overbought:
                rsi_status = "OVERBOUGHT"
        
        signals = {
            'rsi': rsi,
            'rsi_status': rsi_status,
            'oversold_level': oversold,
            'overbought_level': overbought,
            'last_signal': self.last_rsi_signal,
            'position_size': self.position_size
        }
        
        return signals