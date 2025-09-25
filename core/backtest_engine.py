#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest Engine - 回测引擎

为多策略组合提供历史数据回测功能
- 历史数据管理和时间序列模拟
- 多策略组合回测执行
- 性能分析和指标计算
- 回测结果报告生成
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

# 条件导入以支持直接运行和模块导入
try:
    from .strategy_engine import StrategyBase, StrategyEvent
    from .multi_strategy_manager import MultiStrategyManager, StrategyAllocation
    from .strategy_portfolio_config import PortfolioConfig, ConfigManager
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.strategy_engine import StrategyBase, StrategyEvent
    from core.multi_strategy_manager import MultiStrategyManager, StrategyAllocation
    from core.strategy_portfolio_config import PortfolioConfig, ConfigManager


class BacktestState(Enum):
    """回测状态"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running" 
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class MarketData:
    """市场数据结构"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    turnover: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'turnover': self.turnover
        }


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: datetime
    end_date: datetime
    initial_capital: float = 1000000.0
    benchmark: Optional[str] = None
    commission_rate: float = 0.0002  # 万2手续费
    slippage_rate: float = 0.0001    # 滑点率
    
    # 数据配置
    data_frequency: str = "1m"  # 1m, 5m, 15m, 1h, 1d
    symbols: List[str] = field(default_factory=list)
    
    # 回测参数
    match_mode: str = "next_tick"  # 成交模式: next_tick, current_tick
    price_mode: str = "close"      # 价格模式: close, open, vwap
    
    # 风险参数
    max_single_position: float = 0.2  # 单品种最大仓位比例
    max_total_position: float = 0.95   # 总仓位比例
    stop_loss_pct: float = 0.05        # 止损比例


@dataclass 
class Trade:
    """交易记录"""
    trade_id: str
    strategy_name: str
    symbol: str
    direction: str  # "long" 或 "short"
    open_time: datetime
    open_price: float
    quantity: int
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    pnl: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0
    
    @property
    def is_closed(self) -> bool:
        """是否已平仓"""
        return self.close_time is not None
    
    def close_trade(self, close_time: datetime, close_price: float, commission: float = 0.0):
        """平仓交易"""
        self.close_time = close_time
        self.close_price = close_price
        self.commission += commission
        
        # 计算PnL
        if self.direction == "long":
            self.pnl = (close_price - self.open_price) * self.quantity - self.commission - self.slippage
        else:
            self.pnl = (self.open_price - close_price) * self.quantity - self.commission - self.slippage


@dataclass
class PositionInfo:
    """持仓信息"""
    symbol: str
    strategy_name: str
    direction: str
    quantity: int
    avg_price: float
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    
    def update_market_value(self, current_price: float):
        """更新市值和浮动盈亏"""
        self.market_value = current_price * abs(self.quantity)
        
        if self.direction == "long":
            self.unrealized_pnl = (current_price - self.avg_price) * self.quantity
        else:
            self.unrealized_pnl = (self.avg_price - current_price) * self.quantity


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_return: float = 0.0
    annual_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    avg_trade_return: float = 0.0
    avg_winning_trade: float = 0.0
    avg_losing_trade: float = 0.0
    
    # 风险指标
    var_95: float = 0.0  # 95% VaR
    cvar_95: float = 0.0  # 95% CVaR
    calmar_ratio: float = 0.0  # Calmar比率
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式"""
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'win_rate': self.win_rate,
            'profit_loss_ratio': self.profit_loss_ratio,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'avg_trade_return': self.avg_trade_return,
            'avg_winning_trade': self.avg_winning_trade,
            'avg_losing_trade': self.avg_losing_trade,
            'var_95': self.var_95,
            'cvar_95': self.cvar_95,
            'calmar_ratio': self.calmar_ratio
        }


class HistoricalDataManager:
    """历史数据管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.logger = logging.getLogger(__name__)
        
    def load_data(self, symbol: str, start_date: datetime, end_date: datetime,
                  frequency: str = "1m") -> pd.DataFrame:
        """加载历史数据"""
        
        cache_key = f"{symbol}_{frequency}_{start_date.date()}_{end_date.date()}"
        
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        # 尝试从文件加载数据
        file_path = self.data_dir / f"{symbol}_{frequency}.csv"
        
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
                
                # 过滤日期范围
                df = df[(df.index >= start_date) & (df.index <= end_date)]
                
                # 确保数据完整性
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in required_columns:
                    if col not in df.columns:
                        if col == 'volume':
                            df[col] = 0
                        else:
                            df[col] = df.get('close', 0)
                
                # 缓存数据
                self.data_cache[cache_key] = df
                
                self.logger.info(f"加载历史数据 {symbol}: {len(df)} 条记录")
                return df
                
            except Exception as e:
                self.logger.error(f"加载数据文件失败 {file_path}: {e}")
        
        # 如果文件不存在，生成模拟数据
        return self._generate_mock_data(symbol, start_date, end_date, frequency)
    
    def _generate_mock_data(self, symbol: str, start_date: datetime, 
                          end_date: datetime, frequency: str) -> pd.DataFrame:
        """生成模拟数据用于测试"""
        
        self.logger.warning(f"生成模拟数据 {symbol} ({frequency})")
        
        # 根据频率生成时间序列
        freq_map = {
            '1m': '1T',
            '5m': '5T', 
            '15m': '15T',
            '1h': '1H',
            '1d': '1D'
        }
        
        freq_str = freq_map.get(frequency, '1T')
        dates = pd.date_range(start=start_date, end=end_date, freq=freq_str)
        
        # 生成价格数据 (随机游走模型)
        np.random.seed(42)  # 确保可重现性
        
        base_price = 3500.0  # 螺纹钢基准价格
        if 'i' in symbol.lower():
            base_price = 800.0   # 铁矿石
        elif 'j' in symbol.lower():
            base_price = 2000.0  # 焦炭
        
        n_periods = len(dates)
        returns = np.random.normal(0, 0.02, n_periods)  # 2%波动率
        prices = [base_price]
        
        for i in range(1, n_periods):
            price = prices[-1] * (1 + returns[i])
            prices.append(max(price, base_price * 0.5))  # 限制最低价格
        
        # 生成OHLC数据
        data = []
        for i, (timestamp, close) in enumerate(zip(dates, prices)):
            high = close * (1 + abs(np.random.normal(0, 0.005)))
            low = close * (1 - abs(np.random.normal(0, 0.005)))
            open_price = close + np.random.normal(0, close * 0.002)
            
            # 确保价格逻辑正确
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = max(100, int(np.random.normal(1000, 300)))
            
            data.append({
                'open': round(open_price, 1),
                'high': round(high, 1),
                'low': round(low, 1), 
                'close': round(close, 1),
                'volume': volume,
                'turnover': round(close * volume, 2)
            })
        
        df = pd.DataFrame(data, index=dates)
        
        # 缓存生成的数据
        cache_key = f"{symbol}_{frequency}_{start_date.date()}_{end_date.date()}"
        self.data_cache[cache_key] = df
        
        return df


class BacktestPortfolioManager:
    """回测专用的投资组合管理器"""
    
    def __init__(self, portfolio_name: str, total_capital: float, allocation_method: str):
        self.portfolio_name = portfolio_name
        self.total_capital = total_capital
        self.allocation_method = allocation_method
        self.strategies: Dict[str, Any] = {}
        self.allocations: Dict[str, StrategyAllocation] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_strategy(self, strategy: StrategyBase, allocation: StrategyAllocation) -> bool:
        """添加策略到组合"""
        try:
            self.strategies[strategy.strategy_name] = strategy
            self.allocations[strategy.strategy_name] = allocation
            self.logger.info(f"回测组合添加策略: {strategy.strategy_name}")
            return True
        except Exception as e:
            self.logger.error(f"添加策略失败: {e}")
            return False


class BacktestEngine:
    """回测引擎核心类"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.state = BacktestState.IDLE
        
        # 核心组件
        self.data_manager = HistoricalDataManager()
        self.portfolio_manager: Optional[MultiStrategyManager] = None
        
        # 回测数据
        self.current_time: Optional[datetime] = None
        self.current_data: Dict[str, MarketData] = {}
        
        # 交易和持仓
        self.trades: List[Trade] = []
        self.positions: Dict[str, PositionInfo] = {}
        self.portfolio_values: List[Tuple[datetime, float]] = []
        
        # 性能统计
        self.performance_metrics: Optional[PerformanceMetrics] = None
        
        # 日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
    def initialize_portfolio(self, portfolio_config: PortfolioConfig) -> bool:
        """初始化投资组合"""
        
        try:
            self.state = BacktestState.INITIALIZING
            
            # 为回测创建简化的投资组合管理器
            # 在回测模式下，我们不需要实际的MultiStrategyManager
            # 而是使用一个简化的策略容器
            self.portfolio_manager = BacktestPortfolioManager(
                portfolio_name=portfolio_config.portfolio_name,
                total_capital=self.config.initial_capital,
                allocation_method=portfolio_config.allocation_method
            )
            
            # 添加策略到组合
            for strategy_config in portfolio_config.strategies:
                
                # 创建模拟策略实例 (这里需要根据实际策略类动态创建)
                strategy_instance = self._create_strategy_instance(strategy_config)
                
                if strategy_instance is None:
                    self.logger.error(f"无法创建策略实例: {strategy_config.strategy_name}")
                    continue
                
                # 获取分配信息
                allocation = next(
                    (alloc for alloc in portfolio_config.strategy_allocations 
                     if alloc.strategy_name == strategy_config.strategy_name),
                    None
                )
                
                if allocation is None:
                    self.logger.warning(f"策略 {strategy_config.strategy_name} 没有分配信息，使用默认分配")
                    default_ratio = 1.0 / len(portfolio_config.strategies)
                    allocation = StrategyAllocation(
                        strategy_name=strategy_config.strategy_name,
                        allocation_amount=self.config.initial_capital * default_ratio,
                        allocation_ratio=default_ratio,
                        max_position_ratio=0.8,
                        risk_budget=0.02
                    )
                
                # 添加策略
                success = self.portfolio_manager.add_strategy(
                    strategy=strategy_instance,
                    allocation=allocation
                )
                
                if not success:
                    self.logger.error(f"添加策略失败: {strategy_config.strategy_name}")
                    return False
            
            self.logger.info(f"投资组合初始化完成: {len(portfolio_config.strategies)} 个策略")
            return True
            
        except Exception as e:
            self.logger.error(f"投资组合初始化失败: {e}")
            self.state = BacktestState.ERROR
            return False
    
    def _create_strategy_instance(self, strategy_config) -> Optional[StrategyBase]:
        """创建策略实例 (模拟实现)"""
        
        try:
            # 这里应该根据strategy_config.strategy_class动态导入和创建
            # 为了演示，我们创建一个简单的模拟策略
            
            class MockStrategy(StrategyBase):
                def __init__(self, name: str, parameters: Dict[str, Any]):
                    super().__init__(name, parameters)
                    self.fast_period = parameters.get('fast_period', 5)
                    self.slow_period = parameters.get('slow_period', 20)
                    
                def on_data(self, data: Dict[str, Any]):
                    """处理数据 (模拟MA策略逻辑)"""
                    # 简化的MA策略信号生成逻辑
                    pass
                
                def on_order(self, order_data: Dict[str, Any]):
                    """处理订单"""
                    pass
                    
                def on_trade(self, trade_data: Dict[str, Any]):
                    """处理成交"""
                    pass
            
            return MockStrategy(strategy_config.strategy_name, strategy_config.parameters)
            
        except Exception as e:
            self.logger.error(f"创建策略实例失败 {strategy_config.strategy_name}: {e}")
            return None
    
    def run_backtest(self) -> bool:
        """运行回测"""
        
        if self.portfolio_manager is None:
            self.logger.error("投资组合未初始化")
            return False
        
        try:
            self.state = BacktestState.RUNNING
            self.logger.info("开始回测...")
            
            # 加载历史数据
            historical_data = {}
            for symbol in self.config.symbols:
                data = self.data_manager.load_data(
                    symbol=symbol,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                    frequency=self.config.data_frequency
                )
                historical_data[symbol] = data
            
            if not historical_data:
                self.logger.error("没有可用的历史数据")
                return False
            
            # 合并所有时间戳
            all_timestamps = set()
            for df in historical_data.values():
                all_timestamps.update(df.index)
            
            timestamps = sorted(all_timestamps)
            self.logger.info(f"回测时间范围: {timestamps[0]} 到 {timestamps[-1]}, 共 {len(timestamps)} 个时点")
            
            # 初始化投资组合价值记录
            initial_value = self.config.initial_capital
            self.portfolio_values = [(timestamps[0], initial_value)]
            
            # 逐时点回测
            for i, timestamp in enumerate(timestamps):
                
                self.current_time = timestamp
                
                # 更新当前市场数据
                self._update_market_data(timestamp, historical_data)
                
                # 更新持仓市值和浮动盈亏
                self._update_positions()
                
                # 策略信号处理 (简化实现)
                self._process_strategy_signals()
                
                # 记录投资组合价值
                portfolio_value = self._calculate_portfolio_value()
                self.portfolio_values.append((timestamp, portfolio_value))
                
                # 进度报告
                if i % 1000 == 0 or i == len(timestamps) - 1:
                    progress = (i + 1) / len(timestamps) * 100
                    self.logger.info(f"回测进度: {progress:.1f}% ({i+1}/{len(timestamps)})")
            
            self.state = BacktestState.COMPLETED
            self.logger.info("回测完成")
            
            # 计算性能指标
            self._calculate_performance_metrics()
            
            return True
            
        except Exception as e:
            self.logger.error(f"回测执行失败: {e}")
            self.state = BacktestState.ERROR
            return False
    
    def _update_market_data(self, timestamp: datetime, historical_data: Dict[str, pd.DataFrame]):
        """更新当前市场数据"""
        
        self.current_data.clear()
        
        for symbol, df in historical_data.items():
            if timestamp in df.index:
                row = df.loc[timestamp]
                
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(row['volume']),
                    turnover=float(row.get('turnover', 0))
                )
                
                self.current_data[symbol] = market_data
    
    def _update_positions(self):
        """更新持仓信息"""
        
        for symbol, market_data in self.current_data.items():
            position_key = f"{symbol}_long"  # 简化为只考虑多头持仓
            
            if position_key in self.positions:
                position = self.positions[position_key]
                position.update_market_value(market_data.close)
    
    def _process_strategy_signals(self):
        """处理策略信号 (简化实现)"""
        
        # 这里应该调用具体策略的信号生成逻辑
        # 为了演示，我们实现一个简单的随机交易逻辑
        
        if len(self.current_data) > 0 and self.current_time:
            
            # 每100个时点随机产生一个交易信号 (演示用)
            if np.random.random() < 0.01:  # 1%概率
                
                symbol = list(self.current_data.keys())[0]
                market_data = self.current_data[symbol]
                
                # 简单的买入逻辑
                if symbol + "_long" not in self.positions:
                    self._open_position(
                        symbol=symbol,
                        direction="long",
                        price=market_data.close,
                        quantity=100,
                        strategy_name="demo_strategy"
                    )
    
    def _open_position(self, symbol: str, direction: str, price: float, 
                      quantity: int, strategy_name: str):
        """开仓"""
        
        try:
            # 创建交易记录
            trade_id = f"{symbol}_{direction}_{self.current_time.strftime('%Y%m%d_%H%M%S')}"
            
            trade = Trade(
                trade_id=trade_id,
                strategy_name=strategy_name,
                symbol=symbol,
                direction=direction,
                open_time=self.current_time,
                open_price=price,
                quantity=quantity,
                commission=price * quantity * self.config.commission_rate,
                slippage=price * quantity * self.config.slippage_rate
            )
            
            self.trades.append(trade)
            
            # 更新持仓
            position_key = f"{symbol}_{direction}"
            
            if position_key in self.positions:
                # 加仓
                position = self.positions[position_key]
                total_quantity = position.quantity + quantity
                total_value = position.avg_price * position.quantity + price * quantity
                position.avg_price = total_value / total_quantity
                position.quantity = total_quantity
            else:
                # 新建持仓
                position = PositionInfo(
                    symbol=symbol,
                    strategy_name=strategy_name,
                    direction=direction,
                    quantity=quantity,
                    avg_price=price
                )
                self.positions[position_key] = position
            
            self.logger.debug(f"开仓: {symbol} {direction} {quantity}@{price}")
            
        except Exception as e:
            self.logger.error(f"开仓失败: {e}")
    
    def _calculate_portfolio_value(self) -> float:
        """计算投资组合总价值"""
        
        total_value = self.config.initial_capital
        
        # 加上所有持仓的市值
        for position in self.positions.values():
            total_value += position.unrealized_pnl
        
        # 加上已实现盈亏
        realized_pnl = sum(trade.pnl for trade in self.trades if trade.is_closed)
        total_value += realized_pnl
        
        return total_value
    
    def _calculate_performance_metrics(self):
        """计算性能指标"""
        
        if len(self.portfolio_values) < 2:
            return
        
        # 转换为DataFrame进行分析
        values_df = pd.DataFrame(self.portfolio_values, columns=['timestamp', 'portfolio_value'])
        values_df.set_index('timestamp', inplace=True)
        
        # 计算收益率序列
        returns = values_df['portfolio_value'].pct_change().dropna()
        
        # 基本收益指标
        total_return = (values_df['portfolio_value'].iloc[-1] / values_df['portfolio_value'].iloc[0]) - 1
        
        # 年化收益率
        days = (values_df.index[-1] - values_df.index[0]).days
        annual_return = (1 + total_return) ** (365.25 / max(days, 1)) - 1 if days > 0 else 0
        
        # 波动率
        volatility = returns.std() * np.sqrt(252 * 24 * 60 / self._get_frequency_minutes())  # 年化波动率
        
        # 夏普比率 (假设无风险利率为3%)
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 最大回撤
        peak = values_df['portfolio_value'].expanding().max()
        drawdown = (values_df['portfolio_value'] - peak) / peak
        max_drawdown = abs(drawdown.min())
        
        # 最大回撤持续期
        drawdown_duration = self._calculate_max_drawdown_duration(drawdown)
        
        # 交易统计
        closed_trades = [trade for trade in self.trades if trade.is_closed]
        total_trades = len(closed_trades)
        
        if total_trades > 0:
            winning_trades = len([t for t in closed_trades if t.pnl > 0])
            losing_trades = total_trades - winning_trades
            win_rate = winning_trades / total_trades
            
            avg_winning_trade = np.mean([t.pnl for t in closed_trades if t.pnl > 0]) if winning_trades > 0 else 0
            avg_losing_trade = np.mean([t.pnl for t in closed_trades if t.pnl <= 0]) if losing_trades > 0 else 0
            profit_loss_ratio = abs(avg_winning_trade / avg_losing_trade) if avg_losing_trade != 0 else 0
            avg_trade_return = np.mean([t.pnl for t in closed_trades])
        else:
            winning_trades = losing_trades = 0
            win_rate = profit_loss_ratio = avg_trade_return = 0
            avg_winning_trade = avg_losing_trade = 0
        
        # 风险指标
        var_95 = np.percentile(returns, 5) if len(returns) > 0 else 0
        cvar_95 = returns[returns <= var_95].mean() if len(returns) > 0 and var_95 != 0 else 0
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        # 创建性能指标对象
        self.performance_metrics = PerformanceMetrics(
            total_return=total_return,
            annual_return=annual_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=drawdown_duration,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_trade_return=avg_trade_return,
            avg_winning_trade=avg_winning_trade,
            avg_losing_trade=avg_losing_trade,
            var_95=var_95,
            cvar_95=cvar_95,
            calmar_ratio=calmar_ratio
        )
        
        self.logger.info("性能指标计算完成")
    
    def _get_frequency_minutes(self) -> int:
        """获取数据频率对应的分钟数"""
        freq_map = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '1d': 1440
        }
        return freq_map.get(self.config.data_frequency, 1)
    
    def _calculate_max_drawdown_duration(self, drawdown: pd.Series) -> int:
        """计算最大回撤持续期"""
        
        is_drawdown = drawdown < 0
        drawdown_periods = []
        current_period = 0
        
        for in_drawdown in is_drawdown:
            if in_drawdown:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0
        
        if current_period > 0:
            drawdown_periods.append(current_period)
        
        return max(drawdown_periods) if drawdown_periods else 0
    
    def get_backtest_results(self) -> Dict[str, Any]:
        """获取回测结果"""
        
        results = {
            'config': {
                'start_date': self.config.start_date.isoformat(),
                'end_date': self.config.end_date.isoformat(),
                'initial_capital': self.config.initial_capital,
                'symbols': self.config.symbols,
                'commission_rate': self.config.commission_rate,
                'data_frequency': self.config.data_frequency
            },
            'portfolio_values': [
                {'timestamp': ts.isoformat(), 'value': val} 
                for ts, val in self.portfolio_values
            ],
            'trades': [
                {
                    'trade_id': trade.trade_id,
                    'strategy_name': trade.strategy_name,
                    'symbol': trade.symbol,
                    'direction': trade.direction,
                    'open_time': trade.open_time.isoformat(),
                    'open_price': trade.open_price,
                    'quantity': trade.quantity,
                    'close_time': trade.close_time.isoformat() if trade.close_time else None,
                    'close_price': trade.close_price,
                    'pnl': trade.pnl,
                    'commission': trade.commission
                }
                for trade in self.trades
            ],
            'positions': [
                {
                    'symbol': pos.symbol,
                    'strategy_name': pos.strategy_name,
                    'direction': pos.direction,
                    'quantity': pos.quantity,
                    'avg_price': pos.avg_price,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl
                }
                for pos in self.positions.values()
            ],
            'performance_metrics': self.performance_metrics.to_dict() if self.performance_metrics else {},
            'state': self.state.value
        }
        
        return results
    
    def save_results(self, filepath: str):
        """保存回测结果到文件"""
        
        results = self.get_backtest_results()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"回测结果已保存到: {filepath}")


# 便捷函数
def run_portfolio_backtest(portfolio_config: PortfolioConfig,
                         backtest_config: BacktestConfig) -> Dict[str, Any]:
    """运行投资组合回测的便捷函数"""
    
    engine = BacktestEngine(backtest_config)
    
    # 初始化投资组合
    if not engine.initialize_portfolio(portfolio_config):
        raise RuntimeError("投资组合初始化失败")
    
    # 运行回测
    if not engine.run_backtest():
        raise RuntimeError("回测执行失败")
    
    return engine.get_backtest_results()


if __name__ == "__main__":
    # 测试代码
    from datetime import datetime
    
    # 创建回测配置
    backtest_config = BacktestConfig(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 3, 31),
        initial_capital=1000000.0,
        symbols=['rb2405', 'i2405'],
        data_frequency='1h',
        commission_rate=0.0002
    )
    
    print("🚀 回测引擎测试")
    print(f"回测配置: {backtest_config.start_date} 到 {backtest_config.end_date}")
    print(f"初始资金: {backtest_config.initial_capital:,.0f}")
    print(f"交易品种: {backtest_config.symbols}")
    
    # 测试历史数据管理器
    data_manager = HistoricalDataManager()
    
    for symbol in backtest_config.symbols:
        data = data_manager.load_data(
            symbol=symbol,
            start_date=backtest_config.start_date,
            end_date=backtest_config.end_date,
            frequency=backtest_config.data_frequency
        )
        
        print(f"\n✅ {symbol} 数据加载成功:")
        print(f"   数据量: {len(data)} 条")
        print(f"   时间范围: {data.index[0]} 到 {data.index[-1]}")
        print(f"   价格范围: {data['close'].min():.1f} - {data['close'].max():.1f}")
        
    print("\n🎯 回测引擎核心架构测试完成!")