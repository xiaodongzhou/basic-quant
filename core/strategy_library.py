#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy Library Module - 策略库模块

实现丰富的策略模板库，包括：
- 趋势跟踪策略 (海龟交易法则、动量策略)
- 均值回归策略 (布林带策略、RSI策略) 
- 套利策略 (跨期套利、跨品种套利)
- 机器学习策略 (基于ML的价格预测)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
import json

from .technical_indicators import TechnicalIndicators, DEFAULT_INDICATOR_PARAMS
from .data_types import TradingSignalAction

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """策略类型枚举"""
    TREND_FOLLOWING = "趋势跟踪"
    MEAN_REVERSION = "均值回归" 
    ARBITRAGE = "套利策略"
    MACHINE_LEARNING = "机器学习"
    MOMENTUM = "动量策略"
    BREAKOUT = "突破策略"


class SignalStrength(Enum):
    """信号强度枚举"""
    WEAK = "弱信号"
    MEDIUM = "中等信号"
    STRONG = "强信号"
    VERY_STRONG = "极强信号"


@dataclass
class StrategySignal:
    """策略信号数据结构"""
    symbol: str
    timestamp: datetime
    action: TradingSignalAction
    strength: SignalStrength
    price: float
    confidence: float  # 0-1之间的置信度
    strategy_name: str
    parameters: Dict[str, Any]
    description: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class BacktestMetrics:
    """回测指标数据结构"""
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_loss_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_duration: float
    volatility: float
    calmar_ratio: float


class StrategyTemplate:
    """策略模板基类"""
    
    def __init__(self, name: str, description: str, strategy_type: StrategyType, parameters: Dict[str, Any]):
        self.name = name
        self.description = description
        self.strategy_type = strategy_type
        self.parameters = parameters
        self.required_data_length = parameters.get('required_data_length', 100)
        
    def validate_data(self, data: pd.DataFrame) -> bool:
        """验证数据完整性"""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required_columns):
            return False
        if len(data) < self.required_data_length:
            return False
        return True
    
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """生成交易信号 - 子类需要实现此方法"""
        raise NotImplementedError("子类必须实现generate_signals方法")
    
    def calculate_position_size(self, signal: StrategySignal, account_value: float, risk_per_trade: float = 0.02) -> int:
        """计算仓位大小"""
        if signal.stop_loss:
            risk_per_unit = abs(signal.price - signal.stop_loss)
            if risk_per_unit > 0:
                risk_amount = account_value * risk_per_trade
                position_size = int(risk_amount / risk_per_unit)
                return max(1, position_size)
        return 1
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> BacktestMetrics:
        """回测策略表现"""
        signals = self.generate_signals(data)
        return self._run_backtest(data, signals, initial_capital)
    
    def _run_backtest(self, data: pd.DataFrame, signals: List[StrategySignal], initial_capital: float) -> BacktestMetrics:
        """执行回测计算"""
        portfolio_value = [initial_capital]
        position = 0
        entry_price = 0
        trades = []
        
        signal_index = 0
        
        for i, (timestamp, row) in enumerate(data.iterrows()):
            current_price = row['close']
            
            # 检查是否有新信号
            if signal_index < len(signals) and timestamp >= signals[signal_index].timestamp:
                signal = signals[signal_index]
                
                if signal.action == TradingSignalAction.OPEN_LONG and position <= 0:
                    if position < 0:  # 平空仓
                        pnl = (entry_price - current_price) * abs(position)
                        trades.append(pnl)
                    position = 1
                    entry_price = current_price
                elif signal.action == TradingSignalAction.OPEN_SHORT and position >= 0:
                    if position > 0:  # 平多仓
                        pnl = (current_price - entry_price) * position
                        trades.append(pnl)
                    position = -1
                    entry_price = current_price
                elif (signal.action == TradingSignalAction.CLOSE_LONG or signal.action == TradingSignalAction.CLOSE_SHORT) and position != 0:
                    if position > 0:
                        pnl = (current_price - entry_price) * position
                    else:
                        pnl = (entry_price - current_price) * abs(position)
                    trades.append(pnl)
                    position = 0
                    entry_price = 0
                
                signal_index += 1
            
            # 计算当前持仓价值
            if position != 0:
                if position > 0:
                    unrealized_pnl = (current_price - entry_price) * position
                else:
                    unrealized_pnl = (entry_price - current_price) * abs(position)
            else:
                unrealized_pnl = 0
            
            current_portfolio_value = initial_capital + sum(trades) + unrealized_pnl
            portfolio_value.append(current_portfolio_value)
        
        # 计算回测指标
        returns = pd.Series(portfolio_value).pct_change().dropna()
        
        if len(trades) == 0:
            return BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        total_return = (portfolio_value[-1] - initial_capital) / initial_capital
        annualized_return = (1 + total_return) ** (252 / len(data)) - 1
        
        if returns.std() > 0:
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        peak = np.maximum.accumulate(portfolio_value)
        drawdown = (np.array(portfolio_value) - peak) / peak
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
        
        # 交易统计
        winning_trades = len([t for t in trades if t > 0])
        losing_trades = len([t for t in trades if t < 0])
        win_rate = winning_trades / len(trades) if len(trades) > 0 else 0
        
        avg_win = np.mean([t for t in trades if t > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([t for t in trades if t < 0]) if losing_trades > 0 else 0
        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        volatility = returns.std() * np.sqrt(252)
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
        
        return BacktestMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            total_trades=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_trade_duration=len(data) / len(trades) if len(trades) > 0 else 0,
            volatility=volatility,
            calmar_ratio=calmar_ratio
        )
    
    def optimize_parameters(self, data: pd.DataFrame, parameter_ranges: Dict[str, List]) -> Dict[str, Any]:
        """参数优化 - 网格搜索"""
        best_params = self.parameters.copy()
        best_sharpe = -float('inf')
        
        # 生成参数组合
        param_combinations = []
        
        def generate_combinations(params, ranges, current_combo={}):
            if not ranges:
                param_combinations.append(current_combo.copy())
                return
            
            param_name = list(ranges.keys())[0]
            param_values = ranges[param_name]
            remaining_ranges = {k: v for k, v in ranges.items() if k != param_name}
            
            for value in param_values:
                current_combo[param_name] = value
                generate_combinations(params, remaining_ranges, current_combo)
                del current_combo[param_name]
        
        generate_combinations(self.parameters, parameter_ranges)
        
        # 测试每个参数组合
        for combo in param_combinations[:50]:  # 限制组合数量以避免过度计算
            test_params = self.parameters.copy()
            test_params.update(combo)
            
            # 临时更新参数
            old_params = self.parameters
            self.parameters = test_params
            
            try:
                metrics = self.backtest(data)
                if metrics.sharpe_ratio > best_sharpe:
                    best_sharpe = metrics.sharpe_ratio
                    best_params = test_params.copy()
            except Exception as e:
                logger.error(f"参数优化失败: {combo}, 错误: {e}")
            
            # 恢复原参数
            self.parameters = old_params
        
        return best_params


class TurtleTradingStrategy(StrategyTemplate):
    """海龟交易法则策略"""
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'donchian_entry': 20,    # 唐奇安通道入场周期
            'donchian_exit': 10,     # 唐奇安通道出场周期
            'atr_period': 14,        # ATR周期
            'atr_multiplier': 2.0,   # ATR止损倍数
            'required_data_length': 50
        }
        if parameters:
            default_params.update(parameters)
            
        super().__init__(
            name="海龟交易法则",
            description="基于唐奇安通道突破的趋势跟踪策略，使用ATR动态止损",
            strategy_type=StrategyType.TREND_FOLLOWING,
            parameters=default_params
        )
    
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """生成海龟交易信号"""
        if not self.validate_data(data):
            return []
        
        signals = []
        
        # 计算唐奇安通道
        entry_period = self.parameters['donchian_entry']
        exit_period = self.parameters['donchian_exit']
        
        high_entry = data['high'].rolling(window=entry_period).max()
        low_entry = data['low'].rolling(window=entry_period).min()
        high_exit = data['high'].rolling(window=exit_period).max()
        low_exit = data['low'].rolling(window=exit_period).min()
        
        # 计算ATR
        atr_period = self.parameters['atr_period']
        tr = pd.concat([
            data['high'] - data['low'],
            abs(data['high'] - data['close'].shift()),
            abs(data['low'] - data['close'].shift())
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=atr_period).mean()
        
        position = 0  # 0: 无仓位, 1: 多仓, -1: 空仓
        
        for i in range(entry_period, len(data)):
            timestamp = data.index[i]
            current_price = data.iloc[i]['close']
            current_high = data.iloc[i]['high']
            current_low = data.iloc[i]['low']
            current_atr = atr.iloc[i]
            
            # 入场信号
            if position == 0:
                # 多头入场：突破20日高点
                if current_high > high_entry.iloc[i-1]:
                    stop_loss = current_price - self.parameters['atr_multiplier'] * current_atr
                    take_profit = current_price + self.parameters['atr_multiplier'] * current_atr * 2
                    
                    signal = StrategySignal(
                        symbol=f"CONTRACT_{i}",
                        timestamp=timestamp,
                        action=TradingSignalAction.OPEN_LONG,
                        strength=SignalStrength.MEDIUM,
                        price=current_price,
                        confidence=0.7,
                        strategy_name=self.name,
                        parameters=self.parameters,
                        description=f"突破{entry_period}日高点 {high_entry.iloc[i-1]:.2f}",
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )
                    signals.append(signal)
                    position = 1
                
                # 空头入场：跌破20日低点
                elif current_low < low_entry.iloc[i-1]:
                    stop_loss = current_price + self.parameters['atr_multiplier'] * current_atr
                    take_profit = current_price - self.parameters['atr_multiplier'] * current_atr * 2
                    
                    signal = StrategySignal(
                        symbol=f"CONTRACT_{i}",
                        timestamp=timestamp,
                        action=TradingSignalAction.OPEN_SHORT,
                        strength=SignalStrength.MEDIUM,
                        price=current_price,
                        confidence=0.7,
                        strategy_name=self.name,
                        parameters=self.parameters,
                        description=f"跌破{entry_period}日低点 {low_entry.iloc[i-1]:.2f}",
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )
                    signals.append(signal)
                    position = -1
            
            # 出场信号
            elif position == 1:  # 多仓出场
                if current_low < low_exit.iloc[i-1]:
                    signal = StrategySignal(
                        symbol=f"CONTRACT_{i}",
                        timestamp=timestamp,
                        action=TradingSignalAction.CLOSE_LONG if position > 0 else TradingSignalAction.CLOSE_SHORT,
                        strength=SignalStrength.MEDIUM,
                        price=current_price,
                        confidence=0.8,
                        strategy_name=self.name,
                        parameters=self.parameters,
                        description=f"跌破{exit_period}日低点 {low_exit.iloc[i-1]:.2f}"
                    )
                    signals.append(signal)
                    position = 0
            
            elif position == -1:  # 空仓出场
                if current_high > high_exit.iloc[i-1]:
                    signal = StrategySignal(
                        symbol=f"CONTRACT_{i}",
                        timestamp=timestamp,
                        action=TradingSignalAction.CLOSE_LONG if position > 0 else TradingSignalAction.CLOSE_SHORT,
                        strength=SignalStrength.MEDIUM,
                        price=current_price,
                        confidence=0.8,
                        strategy_name=self.name,
                        parameters=self.parameters,
                        description=f"突破{exit_period}日高点 {high_exit.iloc[i-1]:.2f}"
                    )
                    signals.append(signal)
                    position = 0
        
        return signals


class BollingerBandsStrategy(StrategyTemplate):
    """布林带均值回归策略"""
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'bb_period': 20,         # 布林带周期
            'bb_std': 2.0,          # 标准差倍数
            'rsi_period': 14,       # RSI周期
            'rsi_oversold': 30,     # RSI超卖线
            'rsi_overbought': 70,   # RSI超买线
            'required_data_length': 50
        }
        if parameters:
            default_params.update(parameters)
            
        super().__init__(
            name="布林带均值回归策略",
            description="基于布林带和RSI的均值回归策略，在极端位置寻找反转机会",
            strategy_type=StrategyType.MEAN_REVERSION,
            parameters=default_params
        )
    
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """生成布林带均值回归信号"""
        if not self.validate_data(data):
            return []
        
        signals = []
        
        # 计算布林带
        bb_data = TechnicalIndicators.calculate_bollinger_bands(
            data, 
            period=self.parameters['bb_period'],
            std_dev=self.parameters['bb_std']
        )
        
        # 计算RSI
        rsi = TechnicalIndicators.calculate_rsi(
            data, 
            period=self.parameters['rsi_period']
        )
        
        if not bb_data or len(rsi) == 0:
            return []
        
        upper_band = bb_data['upper']
        lower_band = bb_data['lower']
        middle_band = bb_data['middle']
        
        position = 0
        
        for i in range(self.parameters['bb_period'], len(data)):
            timestamp = data.index[i]
            current_price = data.iloc[i]['close']
            current_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
            
            # 多头信号：价格触及下轨且RSI超卖
            if (position <= 0 and 
                current_price <= lower_band.iloc[i] and 
                current_rsi <= self.parameters['rsi_oversold']):
                
                stop_loss = lower_band.iloc[i] * 0.98
                take_profit = middle_band.iloc[i]
                
                confidence = min(0.9, 0.5 + (self.parameters['rsi_oversold'] - current_rsi) / 20)
                
                signal = StrategySignal(
                    symbol=f"CONTRACT_{i}",
                    timestamp=timestamp,
                    action=PositionAction.OPEN_LONG,
                    strength=SignalStrength.STRONG if confidence > 0.8 else SignalStrength.MEDIUM,
                    price=current_price,
                    confidence=confidence,
                    strategy_name=self.name,
                    parameters=self.parameters,
                    description=f"价格触及下轨{lower_band.iloc[i]:.2f}, RSI超卖{current_rsi:.1f}",
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                signals.append(signal)
                position = 1
            
            # 空头信号：价格触及上轨且RSI超买
            elif (position >= 0 and 
                  current_price >= upper_band.iloc[i] and 
                  current_rsi >= self.parameters['rsi_overbought']):
                
                stop_loss = upper_band.iloc[i] * 1.02
                take_profit = middle_band.iloc[i]
                
                confidence = min(0.9, 0.5 + (current_rsi - self.parameters['rsi_overbought']) / 20)
                
                signal = StrategySignal(
                    symbol=f"CONTRACT_{i}",
                    timestamp=timestamp,
                    action=PositionAction.OPEN_SHORT,
                    strength=SignalStrength.STRONG if confidence > 0.8 else SignalStrength.MEDIUM,
                    price=current_price,
                    confidence=confidence,
                    strategy_name=self.name,
                    parameters=self.parameters,
                    description=f"价格触及上轨{upper_band.iloc[i]:.2f}, RSI超买{current_rsi:.1f}",
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                signals.append(signal)
                position = -1
            
            # 平仓信号：价格回归中轨
            elif position != 0:
                close_threshold = 0.005  # 0.5%的容忍度
                
                if (position == 1 and current_price >= middle_band.iloc[i] * (1 - close_threshold)) or \
                   (position == -1 and current_price <= middle_band.iloc[i] * (1 + close_threshold)):
                    
                    signal = StrategySignal(
                        symbol=f"CONTRACT_{i}",
                        timestamp=timestamp,
                        action=TradingSignalAction.CLOSE_LONG if position > 0 else TradingSignalAction.CLOSE_SHORT,
                        strength=SignalStrength.MEDIUM,
                        price=current_price,
                        confidence=0.7,
                        strategy_name=self.name,
                        parameters=self.parameters,
                        description=f"价格回归中轨附近{middle_band.iloc[i]:.2f}"
                    )
                    signals.append(signal)
                    position = 0
        
        return signals


class MomentumStrategy(StrategyTemplate):
    """动量策略"""
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'momentum_period': 10,   # 动量计算周期
            'sma_short': 5,         # 短期移动平均
            'sma_long': 20,         # 长期移动平均
            'momentum_threshold': 0.02,  # 动量阈值
            'required_data_length': 30
        }
        if parameters:
            default_params.update(parameters)
            
        super().__init__(
            name="动量策略",
            description="基于价格动量和移动平均线的趋势策略",
            strategy_type=StrategyType.MOMENTUM,
            parameters=default_params
        )
    
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """生成动量信号"""
        if not self.validate_data(data):
            return []
        
        signals = []
        
        # 计算动量指标
        momentum_period = self.parameters['momentum_period']
        momentum = (data['close'] / data['close'].shift(momentum_period) - 1)
        
        # 计算移动平均线
        sma_short = data['close'].rolling(window=self.parameters['sma_short']).mean()
        sma_long = data['close'].rolling(window=self.parameters['sma_long']).mean()
        
        position = 0
        
        for i in range(self.parameters['sma_long'], len(data)):
            timestamp = data.index[i]
            current_price = data.iloc[i]['close']
            current_momentum = momentum.iloc[i]
            current_sma_short = sma_short.iloc[i]
            current_sma_long = sma_long.iloc[i]
            
            # 多头信号：正动量 + 短均线上穿长均线
            if (position <= 0 and 
                current_momentum > self.parameters['momentum_threshold'] and
                current_sma_short > current_sma_long and
                sma_short.iloc[i-1] <= sma_long.iloc[i-1]):
                
                stop_loss = current_price * 0.95
                take_profit = current_price * 1.10
                
                confidence = min(0.9, 0.6 + current_momentum * 10)
                
                signal = StrategySignal(
                    symbol=f"CONTRACT_{i}",
                    timestamp=timestamp,
                    action=PositionAction.OPEN_LONG,
                    strength=SignalStrength.STRONG if confidence > 0.8 else SignalStrength.MEDIUM,
                    price=current_price,
                    confidence=confidence,
                    strategy_name=self.name,
                    parameters=self.parameters,
                    description=f"正动量{current_momentum:.2%}, 均线金叉",
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                signals.append(signal)
                position = 1
            
            # 空头信号：负动量 + 短均线下穿长均线
            elif (position >= 0 and 
                  current_momentum < -self.parameters['momentum_threshold'] and
                  current_sma_short < current_sma_long and
                  sma_short.iloc[i-1] >= sma_long.iloc[i-1]):
                
                stop_loss = current_price * 1.05
                take_profit = current_price * 0.90
                
                confidence = min(0.9, 0.6 + abs(current_momentum) * 10)
                
                signal = StrategySignal(
                    symbol=f"CONTRACT_{i}",
                    timestamp=timestamp,
                    action=PositionAction.OPEN_SHORT,
                    strength=SignalStrength.STRONG if confidence > 0.8 else SignalStrength.MEDIUM,
                    price=current_price,
                    confidence=confidence,
                    strategy_name=self.name,
                    parameters=self.parameters,
                    description=f"负动量{current_momentum:.2%}, 均线死叉",
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                signals.append(signal)
                position = -1
            
            # 平仓信号：动量衰减
            elif position != 0:
                momentum_decay_threshold = self.parameters['momentum_threshold'] / 3
                
                if (position == 1 and current_momentum < momentum_decay_threshold) or \
                   (position == -1 and current_momentum > -momentum_decay_threshold):
                    
                    signal = StrategySignal(
                        symbol=f"CONTRACT_{i}",
                        timestamp=timestamp,
                        action=TradingSignalAction.CLOSE_LONG if position > 0 else TradingSignalAction.CLOSE_SHORT,
                        strength=SignalStrength.MEDIUM,
                        price=current_price,
                        confidence=0.7,
                        strategy_name=self.name,
                        parameters=self.parameters,
                        description=f"动量衰减{current_momentum:.2%}"
                    )
                    signals.append(signal)
                    position = 0
        
        return signals


class StrategyLibrary:
    """策略库管理器"""
    
    def __init__(self):
        self.strategies = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """注册默认策略"""
        # 趋势跟踪策略
        self.register_strategy("turtle_trading", TurtleTradingStrategy)
        
        # 均值回归策略
        self.register_strategy("bollinger_bands", BollingerBandsStrategy)
        
        # 动量策略
        self.register_strategy("momentum", MomentumStrategy)
    
    def register_strategy(self, strategy_id: str, strategy_class):
        """注册策略"""
        self.strategies[strategy_id] = strategy_class
    
    def get_strategy(self, strategy_id: str, parameters: Dict[str, Any] = None) -> Optional[StrategyTemplate]:
        """获取策略实例"""
        if strategy_id not in self.strategies:
            return None
        
        strategy_class = self.strategies[strategy_id]
        return strategy_class(parameters)
    
    def list_strategies(self) -> Dict[str, Dict[str, Any]]:
        """列出所有可用策略"""
        strategy_info = {}
        
        for strategy_id, strategy_class in self.strategies.items():
            # 创建临时实例获取信息
            temp_instance = strategy_class()
            strategy_info[strategy_id] = {
                'name': temp_instance.name,
                'description': temp_instance.description,
                'type': temp_instance.strategy_type.value,
                'default_parameters': temp_instance.parameters
            }
        
        return strategy_info
    
    def run_strategy_comparison(self, data: pd.DataFrame, strategy_ids: List[str]) -> Dict[str, BacktestMetrics]:
        """策略比较分析"""
        results = {}
        
        for strategy_id in strategy_ids:
            strategy = self.get_strategy(strategy_id)
            if strategy:
                try:
                    metrics = strategy.backtest(data)
                    results[strategy_id] = metrics
                except Exception as e:
                    logger.error(f"策略{strategy_id}回测失败: {e}")
                    results[strategy_id] = None
        
        return results
    
    def get_best_strategy(self, data: pd.DataFrame, strategy_ids: List[str] = None, metric: str = 'sharpe_ratio') -> Tuple[str, BacktestMetrics]:
        """获取最佳策略"""
        if strategy_ids is None:
            strategy_ids = list(self.strategies.keys())
        
        results = self.run_strategy_comparison(data, strategy_ids)
        
        best_strategy = None
        best_value = -float('inf')
        best_metrics = None
        
        for strategy_id, metrics in results.items():
            if metrics and hasattr(metrics, metric):
                value = getattr(metrics, metric)
                if value > best_value:
                    best_value = value
                    best_strategy = strategy_id
                    best_metrics = metrics
        
        return best_strategy, best_metrics


# 全局策略库实例
strategy_library = StrategyLibrary()


def format_signals_for_api(signals: List[StrategySignal]) -> List[Dict[str, Any]]:
    """格式化信号数据用于API响应"""
    formatted_signals = []
    
    for signal in signals:
        formatted_signal = {
            'symbol': signal.symbol,
            'timestamp': signal.timestamp.isoformat(),
            'action': signal.action.value,
            'strength': signal.strength.value,
            'price': signal.price,
            'confidence': signal.confidence,
            'strategy_name': signal.strategy_name,
            'description': signal.description,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit
        }
        formatted_signals.append(formatted_signal)
    
    return formatted_signals


def format_backtest_metrics_for_api(metrics: BacktestMetrics) -> Dict[str, Any]:
    """格式化回测指标用于API响应"""
    return {
        'total_return': round(metrics.total_return * 100, 2),
        'annualized_return': round(metrics.annualized_return * 100, 2),
        'sharpe_ratio': round(metrics.sharpe_ratio, 2),
        'max_drawdown': round(metrics.max_drawdown * 100, 2),
        'win_rate': round(metrics.win_rate * 100, 2),
        'profit_loss_ratio': round(metrics.profit_loss_ratio, 2),
        'total_trades': metrics.total_trades,
        'winning_trades': metrics.winning_trades,
        'losing_trades': metrics.losing_trades,
        'avg_trade_duration': round(metrics.avg_trade_duration, 1),
        'volatility': round(metrics.volatility * 100, 2),
        'calmar_ratio': round(metrics.calmar_ratio, 2)
    }


if __name__ == "__main__":
    # 测试策略库
    
    # 生成测试数据
    dates = pd.date_range('2024-01-01', periods=200, freq='D')
    np.random.seed(42)
    
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 200)
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    test_data = pd.DataFrame({
        'open': np.array(prices) * np.random.uniform(0.98, 1.02, 200),
        'high': np.array(prices) * np.random.uniform(1.00, 1.05, 200),
        'low': np.array(prices) * np.random.uniform(0.95, 1.00, 200),
        'close': prices,
        'volume': np.random.randint(1000, 10000, 200)
    }, index=dates)
    
    # 测试策略
    library = StrategyLibrary()
    
    print("📊 策略库测试")
    print("=" * 50)
    
    # 列出所有策略
    strategies = library.list_strategies()
    print(f"可用策略: {len(strategies)}个")
    for sid, info in strategies.items():
        print(f"- {sid}: {info['name']} ({info['type']})")
    
    print()
    
    # 策略比较
    comparison_results = library.run_strategy_comparison(test_data, list(strategies.keys()))
    print("策略比较结果:")
    for strategy_id, metrics in comparison_results.items():
        if metrics:
            print(f"- {strategy_id}: 夏普比率={metrics.sharpe_ratio:.2f}, 总收益={metrics.total_return:.1%}")
    
    print()
    
    # 最佳策略
    best_strategy, best_metrics = library.get_best_strategy(test_data)
    print(f"最佳策略: {best_strategy}")
    print(f"夏普比率: {best_metrics.sharpe_ratio:.2f}")
    print(f"总收益率: {best_metrics.total_return:.1%}")
    print(f"胜率: {best_metrics.win_rate:.1%}")
    
    print("\n✅ 策略库测试完成!")