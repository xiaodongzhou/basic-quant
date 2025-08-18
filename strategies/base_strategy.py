"""
基础策略类
所有策略都应该继承此类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np

class BaseStrategy(ABC):
    """基础策略类"""
    
    def __init__(self, name: str, symbol: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.symbol = symbol
        self.parameters = parameters or {}
        
        # 策略状态
        self.active = False
        self.trading = True
        
        # 数据相关
        self.bars: List = []
        self.bar_df: pd.DataFrame = pd.DataFrame()
        self.current_bar = None
        
        # 持仓和统计
        self.position_size = 0.0
        self.total_trades = 0
        self.win_trades = 0
        self.total_pnl = 0.0
        
        # 技术指标缓存
        self.indicators: Dict[str, Any] = {}
        
        print(f"策略 {self.name} 初始化完成")
    
    @abstractmethod
    def calculate_indicators(self):
        """计算技术指标"""
        pass
    
    @abstractmethod
    def on_bar(self, bar):
        """K线数据回调"""
        pass
    
    def add_bar(self, bar):
        """添加新的K线数据"""
        self.bars.append(bar)
        self.current_bar = bar
        
        # 更新DataFrame（简化版本）
        bar_dict = {
            'datetime': bar.get('datetime', datetime.now()),
            'open': bar.get('open_price', 0),
            'high': bar.get('high_price', 0),
            'low': bar.get('low_price', 0),
            'close': bar.get('close_price', 0),
            'volume': bar.get('volume', 0)
        }
        
        if self.bar_df.empty:
            self.bar_df = pd.DataFrame([bar_dict])
        else:
            self.bar_df = pd.concat([self.bar_df, pd.DataFrame([bar_dict])], ignore_index=True)
        
        # 限制数据长度
        max_bars = self.parameters.get('max_bars', 1000)
        if len(self.bars) > max_bars:
            self.bars = self.bars[-max_bars:]
            self.bar_df = self.bar_df.tail(max_bars).reset_index(drop=True)
        
        # 计算技术指标
        self.calculate_indicators()
        
        # 执行策略逻辑
        if self.active and self.trading:
            self.on_bar(bar)
    
    def buy(self, price: float, volume: float):
        """买入信号"""
        signal = {
            'symbol': self.symbol,
            'direction': 'LONG',
            'price': price,
            'volume': volume,
            'type': 'MARKET'
        }
        print(f"策略 {self.name} 生成买入信号: {volume}@{price}")
        return signal
    
    def sell(self, price: float, volume: float):
        """卖出信号"""
        signal = {
            'symbol': self.symbol,
            'direction': 'SHORT', 
            'price': price,
            'volume': volume,
            'type': 'MARKET'
        }
        print(f"策略 {self.name} 生成卖出信号: {volume}@{price}")
        return signal
    
    def start(self):
        """启动策略"""
        self.active = True
        print(f"策略 {self.name} 已启动")
    
    def stop(self):
        """停止策略"""
        self.active = False
        print(f"策略 {self.name} 已停止")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取策略表现统计"""
        win_rate = self.win_trades / self.total_trades if self.total_trades > 0 else 0
        
        stats = {
            'strategy_name': self.name,
            'symbol': self.symbol,
            'total_trades': self.total_trades,
            'win_trades': self.win_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'position_size': self.position_size
        }
        
        return stats
    
    def reset(self):
        """重置策略状态"""
        self.bars.clear()
        self.bar_df = pd.DataFrame()
        self.current_bar = None
        self.position_size = 0.0
        self.total_trades = 0
        self.win_trades = 0
        self.total_pnl = 0.0
        self.indicators.clear()
        
        print(f"策略 {self.name} 状态已重置")
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """获取策略参数"""
        return self.parameters.get(key, default)
    
    def get_indicator_value(self, name: str, index: int = -1) -> Any:
        """获取技术指标值"""
        if name in self.indicators:
            indicator = self.indicators[name]
            if isinstance(indicator, (list, np.ndarray)) and len(indicator) > abs(index):
                return indicator[index]
            return indicator
        return None