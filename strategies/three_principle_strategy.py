"""
三原则策略框架 (Three-Principle Strategy Framework)
基于 Direction-Position-Signal 架构的量化交易策略基类

三原则：
1. Direction (方向): 判断市场趋势方向
2. Position (位置): 计算入场和出场位置
3. Signal (信号): 生成具体的交易信号
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from .base_strategy import BaseStrategy


class TrendDirection(Enum):
    """趋势方向枚举"""
    UP = "UP"           # 上涨
    DOWN = "DOWN"       # 下跌
    SIDEWAYS = "SIDEWAYS"  # 横盘
    UNKNOWN = "UNKNOWN"    # 未知


class SignalType(Enum):
    """信号类型枚举"""
    ENTRY_LONG = "ENTRY_LONG"      # 做多入场
    ENTRY_SHORT = "ENTRY_SHORT"    # 做空入场
    EXIT_LONG = "EXIT_LONG"        # 多头出场
    EXIT_SHORT = "EXIT_SHORT"      # 空头出场
    HOLD = "HOLD"                  # 持仓
    NO_SIGNAL = "NO_SIGNAL"        # 无信号


class PositionStatus(Enum):
    """仓位状态枚举"""
    NO_POSITION = "NO_POSITION"    # 无仓位
    LONG = "LONG"                  # 多头
    SHORT = "SHORT"                # 空头


class Position:
    """持仓信息类"""
    
    def __init__(self, direction: str, size: float, entry_price: float, 
                 entry_time: datetime = None, stop_loss: float = None, 
                 take_profit: float = None):
        self.direction = direction  # LONG or SHORT
        self.size = size           # 持仓数量
        self.entry_price = entry_price  # 入场价格
        self.entry_time = entry_time or datetime.now()  # 入场时间
        self.stop_loss = stop_loss      # 止损价格
        self.take_profit = take_profit  # 止盈价格
        self.unrealized_pnl = 0.0      # 未实现盈亏
        
    def update_pnl(self, current_price: float):
        """更新未实现盈亏"""
        if self.direction == "LONG":
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        elif self.direction == "SHORT":
            self.unrealized_pnl = (self.entry_price - current_price) * self.size


class TradingSignal:
    """交易信号类"""
    
    def __init__(self, signal_type: SignalType, confidence: float, 
                 price: float, reason: str = "", metadata: Dict[str, Any] = None):
        self.signal_type = signal_type
        self.confidence = confidence    # 信号置信度 (0-1)
        self.price = price             # 信号价格
        self.reason = reason           # 信号原因
        self.metadata = metadata or {} # 其他信息
        self.timestamp = datetime.now()


class DirectionAnalyzer(ABC):
    """方向分析器抽象基类"""
    
    @abstractmethod
    def analyze_direction(self, df: pd.DataFrame, **kwargs) -> TrendDirection:
        """分析市场方向"""
        pass
    
    def get_direction_confidence(self) -> float:
        """获取方向判断的置信度"""
        return 0.0


class PositionManager(ABC):
    """位置管理器抽象基类"""
    
    @abstractmethod
    def calculate_entry_position(self, df: pd.DataFrame, direction: TrendDirection, **kwargs) -> Dict[str, float]:
        """计算入场位置"""
        pass
    
    @abstractmethod  
    def calculate_exit_position(self, df: pd.DataFrame, position: Position, **kwargs) -> Dict[str, float]:
        """计算出场位置"""
        pass


class SignalGenerator(ABC):
    """信号生成器抽象基类"""
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, direction: TrendDirection, 
                       entry_levels: Dict[str, float], exit_levels: Dict[str, float],
                       current_position: Optional[Position] = None, **kwargs) -> TradingSignal:
        """生成交易信号"""
        pass


class ThreePrincipleStrategy(BaseStrategy):
    """三原则策略基类
    
    整合Direction-Position-Signal三个组件，实现完整的交易策略
    """
    
    def __init__(self, name: str, symbol: str, parameters: Dict[str, Any] = None):
        super().__init__(name, symbol, parameters)
        
        # 三原则组件
        self.direction_analyzer: Optional[DirectionAnalyzer] = None
        self.position_manager: Optional[PositionManager] = None  
        self.signal_generator: Optional[SignalGenerator] = None
        
        # 策略状态
        self.current_direction = TrendDirection.UNKNOWN
        self.current_position: Optional[Position] = None
        self.entry_levels: Dict[str, float] = {}
        self.exit_levels: Dict[str, float] = {}
        
        # 统计信息
        self.signal_count = 0
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.closed_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_balance = 0.0
        
        # 风险管理
        self.max_position_size = parameters.get('max_position_size', 1.0)
        self.account_balance = parameters.get('account_balance', 100000.0)
        
        logger.info(f"三原则策略 {name} 初始化完成")
    
    def set_components(self, direction_analyzer: DirectionAnalyzer, 
                      position_manager: PositionManager, 
                      signal_generator: SignalGenerator):
        """设置策略组件"""
        self.direction_analyzer = direction_analyzer
        self.position_manager = position_manager
        self.signal_generator = signal_generator
        logger.info("策略组件设置完成")
    
    def calculate_indicators(self):
        """计算技术指标（由具体组件实现）"""
        pass
    
    def on_bar(self, df: pd.DataFrame):
        """K线数据更新处理"""
        if len(df) < 50:  # 确保有足够的历史数据
            return
        
        try:
            # 1. 方向分析
            if self.direction_analyzer:
                new_direction = self.direction_analyzer.analyze_direction(df)
                self.current_direction = new_direction
            
            # 2. 位置管理
            if self.position_manager:
                # 计算入场位置
                self.entry_levels = self.position_manager.calculate_entry_position(df, self.current_direction)
                
                # 如果有持仓，计算出场位置
                if self.current_position:
                    self.exit_levels = self.position_manager.calculate_exit_position(df, self.current_position)
            
            # 3. 信号生成
            if self.signal_generator:
                signal = self.signal_generator.generate_signal(
                    df, self.current_direction, self.entry_levels, 
                    self.exit_levels, self.current_position
                )
                
                # 处理信号
                self._process_signal(signal, df)
            
            # 更新持仓盈亏
            if self.current_position:
                current_price = df['close'].iloc[-1]
                self.current_position.update_pnl(current_price)
                
        except Exception as e:
            logger.error(f"K线处理失败: {e}")
    
    def _process_signal(self, signal: TradingSignal, df: pd.DataFrame):
        """处理交易信号"""
        if signal.signal_type == SignalType.NO_SIGNAL:
            return
        
        self.signal_count += 1
        current_price = df['close'].iloc[-1]
        
        # 处理入场信号
        if signal.signal_type == SignalType.ENTRY_LONG and not self.current_position:
            size = self._calculate_position_size(signal.price)
            if size > 0:
                self._execute_entry_long(size, signal.price)
                logger.info(f"执行做多入场: {size}@{signal.price}")
                
        elif signal.signal_type == SignalType.ENTRY_SHORT and not self.current_position:
            size = self._calculate_position_size(signal.price)
            if size > 0:
                self._execute_entry_short(size, signal.price)
                logger.info(f"执行做空入场: {size}@{signal.price}")
        
        # 处理出场信号
        elif signal.signal_type == SignalType.EXIT_LONG and self.current_position and self.current_position.direction == "LONG":
            self._execute_exit(signal.price, signal.reason)
            
        elif signal.signal_type == SignalType.EXIT_SHORT and self.current_position and self.current_position.direction == "SHORT":
            self._execute_exit(signal.price, signal.reason)
    
    def _calculate_position_size(self, price: float) -> float:
        """计算仓位大小"""
        if not self.entry_levels or 'entry_price' not in self.entry_levels:
            return 0.0
        
        # 基于风险的仓位计算
        entry_price = self.entry_levels['entry_price']
        stop_loss = self.entry_levels.get('stop_loss', entry_price)
        
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return 0.0
        
        # 限制每笔交易风险不超过账户的1%
        max_risk = self.account_balance * 0.01
        position_size = max_risk / risk_per_share
        
        # 限制最大仓位
        max_size = self.max_position_size
        return min(position_size, max_size)
    
    def _execute_entry_long(self, size: float, price: float):
        """执行做多入场"""
        stop_loss = self.entry_levels.get('stop_loss')
        take_profit = self.entry_levels.get('take_profit')
        
        self.current_position = Position(
            direction="LONG",
            size=size,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.trade_count += 1
        
    def _execute_entry_short(self, size: float, price: float):
        """执行做空入场"""
        stop_loss = self.entry_levels.get('stop_loss')
        take_profit = self.entry_levels.get('take_profit')
        
        self.current_position = Position(
            direction="SHORT",
            size=size,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.trade_count += 1
    
    def _execute_exit(self, price: float, reason: str = ""):
        """执行出场"""
        if not self.current_position:
            return
        
        # 计算盈亏
        if self.current_position.direction == "LONG":
            pnl = (price - self.current_position.entry_price) * self.current_position.size
        else:
            pnl = (self.current_position.entry_price - price) * self.current_position.size
        
        self.total_pnl += pnl
        self.closed_pnl += pnl
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        logger.info(f"执行出场: {self.current_position.direction} {self.current_position.size}@{price}, PNL: {pnl:.2f}")
        
        # 清空持仓
        self.current_position = None
        self.entry_levels = {}
        self.exit_levels = {}
    
    def start(self):
        """启动策略"""
        self.active = True
        logger.info(f"策略 {self.name} 已启动")
    
    def stop(self):
        """停止策略"""
        self.active = False
        
        # 如果有持仓，强制平仓
        if self.current_position:
            logger.warning("策略停止时仍有持仓，强制平仓")
            # 这里应该有平仓逻辑
        
        logger.info(f"策略 {self.name} 已停止")
    
    def get_current_position(self) -> Optional[Position]:
        """获取当前持仓"""
        return self.current_position
    
    def get_strategy_state(self) -> Dict[str, Any]:
        """获取策略状态"""
        return {
            'name': self.name,
            'symbol': self.symbol,
            'active': self.active,
            'current_direction': self.current_direction.value,
            'has_position': self.current_position is not None,
            'position_direction': self.current_position.direction if self.current_position else None,
            'position_size': self.current_position.size if self.current_position else 0.0,
            'signal_count': self.signal_count,
            'trade_count': self.trade_count,
            'total_pnl': self.total_pnl,
            'closed_pnl': self.closed_pnl,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades
        }
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """获取性能指标"""
        total_trades = self.winning_trades + self.losing_trades
        win_rate = self.winning_trades / total_trades if total_trades > 0 else 0.0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': 0.0,  # 需要更复杂的计算
            'profit_factor': 1.0,  # 需要盈利/亏损统计
        }