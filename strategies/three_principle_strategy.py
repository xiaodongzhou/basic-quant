"""
三原则策略框架
基于方向-位置-信号的策略框架实现
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np
from dataclasses import dataclass
from loguru import logger

from .base_strategy import BaseStrategy

class TrendDirection(Enum):
    """趋势方向枚举"""
    UP = "UP"           # 上涨趋势
    DOWN = "DOWN"       # 下跌趋势
    SIDEWAYS = "SIDEWAYS"   # 横盘整理
    UNKNOWN = "UNKNOWN"     # 未知方向

class SignalType(Enum):
    """信号类型枚举"""
    ENTRY_LONG = "ENTRY_LONG"       # 做多入场
    ENTRY_SHORT = "ENTRY_SHORT"     # 做空入场
    EXIT_LONG = "EXIT_LONG"         # 做多出场
    EXIT_SHORT = "EXIT_SHORT"       # 做空出场
    HOLD = "HOLD"                   # 持有
    NO_SIGNAL = "NO_SIGNAL"         # 无信号

class PositionStatus(Enum):
    """仓位状态枚举"""
    NO_POSITION = "NO_POSITION"     # 无仓位
    LONG = "LONG"                   # 持有多头
    SHORT = "SHORT"                 # 持有空头

@dataclass
class Position:
    """仓位信息"""
    symbol: str
    direction: str          # LONG/SHORT
    size: float            # 仓位大小
    entry_price: float     # 入场价格
    entry_time: datetime   # 入场时间
    current_price: float = 0.0   # 当前价格
    unrealized_pnl: float = 0.0  # 未实现盈亏
    
    def update_current_price(self, price: float):
        """更新当前价格和未实现盈亏"""
        self.current_price = price
        if self.direction == "LONG":
            self.unrealized_pnl = (price - self.entry_price) * self.size
        elif self.direction == "SHORT":
            self.unrealized_pnl = (self.entry_price - price) * self.size

@dataclass
class TradingSignal:
    """交易信号"""
    signal_type: SignalType
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    confidence: float = 1.0     # 信号置信度 0-1
    stop_loss: float = None     # 止损价位
    take_profit: float = None   # 止盈价位
    reason: str = ""           # 信号原因

class DirectionAnalyzer(ABC):
    """方向分析器抽象基类"""
    
    @abstractmethod
    def analyze_direction(self, df: pd.DataFrame, **kwargs) -> TrendDirection:
        """分析市场方向"""
        pass
    
    @abstractmethod
    def get_direction_confidence(self) -> float:
        """获取方向判断的置信度"""
        pass

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
    """
    三原则策略基类
    整合方向分析、位置管理、信号生成三个核心组件
    """
    
    def __init__(self, name: str, symbol: str, parameters: Dict[str, Any] = None):
        super().__init__(name, symbol, parameters)
        
        # 三个核心组件
        self.direction_analyzer: Optional[DirectionAnalyzer] = None
        self.position_manager: Optional[PositionManager] = None
        self.signal_generator: Optional[SignalGenerator] = None
        
        # 策略状态
        self.current_direction = TrendDirection.UNKNOWN
        self.current_position: Optional[Position] = None
        self.position_status = PositionStatus.NO_POSITION
        
        # 交易记录
        self.signals_history: List[TradingSignal] = []
        self.trades_history: List[Dict] = []
        
        # 风险管理参数
        self.max_position_size = self.get_parameter('max_position_size', 1.0)
        self.risk_per_trade = self.get_parameter('risk_per_trade', 0.02)  # 2%
        self.max_drawdown = self.get_parameter('max_drawdown', 0.1)       # 10%
        
        logger.info(f"三原则策略 {self.name} 初始化完成")
    
    def set_components(self, direction_analyzer: DirectionAnalyzer,
                      position_manager: PositionManager,
                      signal_generator: SignalGenerator):
        """设置三个核心组件"""
        self.direction_analyzer = direction_analyzer
        self.position_manager = position_manager
        self.signal_generator = signal_generator
        logger.info(f"策略组件设置完成")
    
    def calculate_indicators(self):
        """计算技术指标（子类可扩展）"""
        if len(self.bar_df) < 2:
            return
        
        # 基础指标
        self.indicators['close'] = self.bar_df['close'].tolist()
        self.indicators['high'] = self.bar_df['high'].tolist()
        self.indicators['low'] = self.bar_df['low'].tolist()
        self.indicators['volume'] = self.bar_df['volume'].tolist()
        
        # 可被子类重写以添加更多指标
        self.calculate_custom_indicators()
    
    def calculate_custom_indicators(self):
        """计算自定义指标（子类重写）"""
        pass
    
    def on_bar(self, bar):
        """K线数据处理 - 三原则策略核心逻辑"""
        try:
            # 检查组件是否完整
            if not self._check_components():
                return
            
            current_price = bar.get('close_price', 0)
            current_time = bar.get('datetime', datetime.now())
            
            # 更新当前持仓的价格
            if self.current_position:
                self.current_position.update_current_price(current_price)
            
            # 第一原则：分析方向
            self.current_direction = self.direction_analyzer.analyze_direction(self.bar_df)
            direction_confidence = self.direction_analyzer.get_direction_confidence()
            
            # 第二原则：确定位置
            entry_levels = {}
            exit_levels = {}
            
            if self.current_position is None:
                # 无仓位时计算入场位置
                entry_levels = self.position_manager.calculate_entry_position(
                    self.bar_df, self.current_direction
                )
            else:
                # 有仓位时计算出场位置
                exit_levels = self.position_manager.calculate_exit_position(
                    self.bar_df, self.current_position
                )
            
            # 第三原则：生成信号
            signal = self.signal_generator.generate_signal(
                df=self.bar_df,
                direction=self.current_direction,
                entry_levels=entry_levels,
                exit_levels=exit_levels,
                current_position=self.current_position
            )
            
            # 处理信号
            if signal.signal_type != SignalType.NO_SIGNAL:
                self._process_trading_signal(signal, current_price, current_time)
                
        except Exception as e:
            logger.error(f"策略执行出错: {e}")
    
    def _check_components(self) -> bool:
        """检查三个组件是否都已设置"""
        return all([
            self.direction_analyzer is not None,
            self.position_manager is not None,
            self.signal_generator is not None
        ])
    
    def _process_trading_signal(self, signal: TradingSignal, current_price: float, current_time: datetime):
        """处理交易信号"""
        self.signals_history.append(signal)
        
        if signal.signal_type == SignalType.ENTRY_LONG:
            self._execute_entry_long(signal, current_price, current_time)
            
        elif signal.signal_type == SignalType.ENTRY_SHORT:
            self._execute_entry_short(signal, current_price, current_time)
            
        elif signal.signal_type == SignalType.EXIT_LONG:
            if self.current_position and self.current_position.direction == "LONG":
                self._execute_exit(signal, current_price, current_time)
                
        elif signal.signal_type == SignalType.EXIT_SHORT:
            if self.current_position and self.current_position.direction == "SHORT":
                self._execute_exit(signal, current_price, current_time)
    
    def _execute_entry_long(self, signal: TradingSignal, price: float, timestamp: datetime):
        """执行做多入场"""
        if self.current_position is not None:
            logger.warning("已有持仓，忽略入场信号")
            return
        
        # 风险管理：计算仓位大小
        position_size = self._calculate_position_size(price, signal.stop_loss)
        
        # 创建持仓
        self.current_position = Position(
            symbol=self.symbol,
            direction="LONG",
            size=position_size,
            entry_price=price,
            entry_time=timestamp,
            current_price=price
        )
        
        self.position_status = PositionStatus.LONG
        self.position_size = position_size
        
        # 记录交易
        trade_record = {
            'type': 'ENTRY_LONG',
            'symbol': self.symbol,
            'price': price,
            'size': position_size,
            'timestamp': timestamp,
            'signal_reason': signal.reason
        }
        self.trades_history.append(trade_record)
        
        # 生成买入信号（给外部系统）
        buy_signal = self.buy(price, position_size)
        logger.info(f"执行做多入场: {position_size}@{price}")
        
        return buy_signal
    
    def _execute_entry_short(self, signal: TradingSignal, price: float, timestamp: datetime):
        """执行做空入场"""
        if self.current_position is not None:
            logger.warning("已有持仓，忽略入场信号")
            return
        
        # 风险管理：计算仓位大小
        position_size = self._calculate_position_size(price, signal.stop_loss)
        
        # 创建持仓
        self.current_position = Position(
            symbol=self.symbol,
            direction="SHORT",
            size=position_size,
            entry_price=price,
            entry_time=timestamp,
            current_price=price
        )
        
        self.position_status = PositionStatus.SHORT
        self.position_size = -position_size  # 负数表示空头
        
        # 记录交易
        trade_record = {
            'type': 'ENTRY_SHORT',
            'symbol': self.symbol,
            'price': price,
            'size': position_size,
            'timestamp': timestamp,
            'signal_reason': signal.reason
        }
        self.trades_history.append(trade_record)
        
        # 生成卖出信号（给外部系统）
        sell_signal = self.sell(price, position_size)
        logger.info(f"执行做空入场: {position_size}@{price}")
        
        return sell_signal
    
    def _execute_exit(self, signal: TradingSignal, price: float, timestamp: datetime):
        """执行出场"""
        if self.current_position is None:
            logger.warning("无持仓，忽略出场信号")
            return
        
        # 计算盈亏
        pnl = self.current_position.unrealized_pnl
        self.total_pnl += pnl
        
        # 记录交易
        trade_record = {
            'type': f'EXIT_{self.current_position.direction}',
            'symbol': self.symbol,
            'entry_price': self.current_position.entry_price,
            'exit_price': price,
            'size': self.current_position.size,
            'pnl': pnl,
            'entry_time': self.current_position.entry_time,
            'exit_time': timestamp,
            'signal_reason': signal.reason
        }
        self.trades_history.append(trade_record)
        
        # 更新统计
        self.total_trades += 1
        if pnl > 0:
            self.win_trades += 1
        
        # 生成相反方向的信号（平仓）
        if self.current_position.direction == "LONG":
            exit_signal = self.sell(price, self.current_position.size)
        else:
            exit_signal = self.buy(price, self.current_position.size)
        
        logger.info(f"执行出场: {self.current_position.direction} {self.current_position.size}@{price}, PNL: {pnl:.2f}")
        
        # 清除持仓
        self.current_position = None
        self.position_status = PositionStatus.NO_POSITION
        self.position_size = 0.0
        
        return exit_signal
    
    def _calculate_position_size(self, entry_price: float, stop_loss: float = None) -> float:
        """计算仓位大小（基于风险管理）"""
        base_size = self.get_parameter('volume', 1.0)
        
        if stop_loss is None:
            return min(base_size, self.max_position_size)
        
        # 基于风险百分比计算仓位
        # 假设账户资金为100000（可参数化）
        account_balance = self.get_parameter('account_balance', 100000)
        risk_amount = account_balance * self.risk_per_trade
        
        # 计算风险距离
        risk_distance = abs(entry_price - stop_loss)
        if risk_distance <= 0:
            return min(base_size, self.max_position_size)
        
        # 仓位大小 = 风险金额 / 风险距离
        calculated_size = risk_amount / risk_distance
        
        # 限制最大仓位
        return min(calculated_size, self.max_position_size)
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        status = {
            'strategy_name': self.name,
            'symbol': self.symbol,
            'current_direction': self.current_direction.value,
            'position_status': self.position_status.value,
            'current_position': None,
            'total_signals': len(self.signals_history),
            'total_trades': len(self.trades_history),
            'total_pnl': self.total_pnl,
            'win_rate': self.win_trades / self.total_trades if self.total_trades > 0 else 0
        }
        
        if self.current_position:
            status['current_position'] = {
                'direction': self.current_position.direction,
                'size': self.current_position.size,
                'entry_price': self.current_position.entry_price,
                'current_price': self.current_position.current_price,
                'unrealized_pnl': self.current_position.unrealized_pnl,
                'entry_time': self.current_position.entry_time.isoformat() if isinstance(self.current_position.entry_time, datetime) else str(self.current_position.entry_time)
            }
        
        return status
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """获取交易记录DataFrame"""
        if not self.trades_history:
            return pd.DataFrame()
        
        return pd.DataFrame(self.trades_history)
    
    def get_signals_dataframe(self) -> pd.DataFrame:
        """获取信号记录DataFrame"""
        if not self.signals_history:
            return pd.DataFrame()
        
        signals_data = []
        for signal in self.signals_history:
            signals_data.append({
                'timestamp': signal.timestamp,
                'signal_type': signal.signal_type.value,
                'symbol': signal.symbol,
                'price': signal.price,
                'volume': signal.volume,
                'confidence': signal.confidence,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'reason': signal.reason
            })
        
        return pd.DataFrame(signals_data)
    
    def reset(self):
        """重置策略状态"""
        super().reset()
        self.current_direction = TrendDirection.UNKNOWN
        self.current_position = None
        self.position_status = PositionStatus.NO_POSITION
        self.signals_history.clear()
        self.trades_history.clear()
        
        logger.info(f"三原则策略 {self.name} 状态已重置")