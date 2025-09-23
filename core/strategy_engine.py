#!/usr/bin/env python3
"""
StrategyEngine - 策略引擎模块
负责策略加载、管理和事件分发

Milestone 2.2 核心模块 - 实现策略框架管理功能
"""

import json
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Type
from dataclasses import dataclass
from enum import Enum
import inspect

from .data_types import (
    TickData, BarData, TradingSignal, TradingResult, 
    PositionData, OrderData, TradeData, Direction
)
from .trading_engine import TradingEngine
from .market_data_manager import MarketDataManager


class StrategyStatus(Enum):
    """策略状态枚举"""
    INACTIVE = "inactive"      # 未激活
    LOADING = "loading"        # 加载中
    LOADED = "loaded"          # 已加载
    STARTING = "starting"      # 启动中
    RUNNING = "running"        # 运行中
    STOPPING = "stopping"      # 停止中
    STOPPED = "stopped"        # 已停止
    ERROR = "error"           # 错误状态


class StrategyEvent(Enum):
    """策略事件类型"""
    TICK = "tick"             # Tick数据事件
    BAR = "bar"               # Bar数据事件
    TRADE = "trade"           # 成交事件
    ORDER = "order"           # 订单事件
    POSITION = "position"     # 持仓事件
    TIMER = "timer"           # 定时器事件


@dataclass
class StrategyConfig:
    """
    策略配置数据结构
    """
    name: str                     # 策略名称
    symbols: List[str]           # 关注的合约列表
    class_name: str              # 策略类名
    
    # 策略参数
    parameters: Dict[str, Any] = None
    
    # 运行控制
    enabled: bool = True         # 是否启用
    auto_start: bool = False     # 是否自动启动
    
    # 资金管理
    initial_capital: float = 100000.0    # 初始资金
    max_position_size: int = 10          # 最大持仓手数
    
    # 风险控制
    stop_loss: float = 0.05      # 止损比例 (5%)
    take_profit: float = 0.10    # 止盈比例 (10%)
    
    # 其他配置
    description: str = ""        # 策略描述
    version: str = "1.0.0"      # 策略版本


class StrategyBase(ABC):
    """
    策略基类
    所有自定义策略都需要继承此类并实现抽象方法
    """
    
    def __init__(self, strategy_name: str, config: StrategyConfig, 
                 trading_engine: TradingEngine):
        """
        初始化策略基类
        
        Args:
            strategy_name: 策略名称
            config: 策略配置
            trading_engine: 交易引擎
        """
        self.strategy_name = strategy_name
        self.config = config
        self.trading_engine = trading_engine
        
        # 策略状态
        self.status = StrategyStatus.INACTIVE
        self.start_time: Optional[datetime] = None
        self.stop_time: Optional[datetime] = None
        
        # 数据存储
        self.tick_data: Dict[str, List[TickData]] = {}
        self.bar_data: Dict[str, List[BarData]] = {}
        
        # 交易记录
        self.trades: List[TradeData] = []
        self.positions: Dict[str, PositionData] = {}
        self.orders: Dict[str, OrderData] = {}
        
        # 策略指标和信号
        self.indicators: Dict[str, Any] = {}
        self.signals: List[TradingSignal] = []
        
        # 绩效统计
        self.total_pnl = 0.0
        self.total_trades = 0
        self.win_trades = 0
        self.loss_trades = 0
        
        # 线程锁
        self.lock = threading.Lock()
        
        print(f"✅ 策略基类初始化完成: {strategy_name}")
    
    # 抽象方法 - 子类必须实现
    @abstractmethod
    def on_init(self) -> None:
        """
        策略初始化回调
        在策略加载时调用，用于初始化策略参数、指标等
        """
        pass
    
    @abstractmethod
    def on_start(self) -> None:
        """
        策略启动回调
        在策略开始运行时调用
        """
        pass
    
    @abstractmethod
    def on_stop(self) -> None:
        """
        策略停止回调
        在策略停止运行时调用
        """
        pass
    
    @abstractmethod
    def on_tick(self, tick: TickData) -> None:
        """
        Tick数据回调
        
        Args:
            tick: Tick数据
        """
        pass
    
    @abstractmethod
    def on_bar(self, bar: BarData) -> None:
        """
        Bar数据回调
        
        Args:
            bar: Bar数据
        """
        pass
    
    @abstractmethod
    def on_trade(self, trade: TradeData) -> None:
        """
        成交回调
        
        Args:
            trade: 成交数据
        """
        pass
    
    # 通用方法 - 子类可以使用
    def send_signal(self, signal: TradingSignal) -> TradingResult:
        """
        发送交易信号
        
        Args:
            signal: 交易信号
            
        Returns:
            TradingResult: 交易结果
        """
        with self.lock:
            # 记录信号
            self.signals.append(signal)
            
            # 发送给交易引擎
            result = self.trading_engine.send_order(signal)
            
            if result.success:
                print(f"🎯 策略信号发送成功: {self.strategy_name} -> {signal.symbol} "
                      f"{signal.action.value} {signal.volume}手")
            else:
                print(f"❌ 策略信号发送失败: {self.strategy_name} -> {result.message}")
            
            return result
    
    def get_position(self, symbol: str, direction: Direction = None) -> List[PositionData]:
        """获取持仓信息"""
        return self.trading_engine.get_position(symbol, direction)
    
    def get_account_info(self):
        """获取账户信息"""
        return self.trading_engine.get_account_info()
    
    def add_tick_data(self, tick: TickData, max_length: int = 1000) -> None:
        """
        添加Tick数据到策略缓存
        
        Args:
            tick: Tick数据
            max_length: 最大缓存长度
        """
        with self.lock:
            symbol = tick.symbol
            if symbol not in self.tick_data:
                self.tick_data[symbol] = []
            
            self.tick_data[symbol].append(tick)
            
            # 限制缓存长度
            if len(self.tick_data[symbol]) > max_length:
                self.tick_data[symbol] = self.tick_data[symbol][-max_length:]
    
    def add_bar_data(self, bar: BarData, max_length: int = 1000) -> None:
        """
        添加Bar数据到策略缓存
        
        Args:
            bar: Bar数据
            max_length: 最大缓存长度
        """
        with self.lock:
            symbol = bar.symbol
            if symbol not in self.bar_data:
                self.bar_data[symbol] = []
            
            self.bar_data[symbol].append(bar)
            
            # 限制缓存长度
            if len(self.bar_data[symbol]) > max_length:
                self.bar_data[symbol] = self.bar_data[symbol][-max_length:]
    
    def get_recent_ticks(self, symbol: str, count: int = 100) -> List[TickData]:
        """获取最近的Tick数据"""
        with self.lock:
            if symbol in self.tick_data:
                return self.tick_data[symbol][-count:]
            return []
    
    def get_recent_bars(self, symbol: str, count: int = 100) -> List[BarData]:
        """获取最近的Bar数据"""
        with self.lock:
            if symbol in self.bar_data:
                return self.bar_data[symbol][-count:]
            return []
    
    def calculate_ma(self, symbol: str, period: int, data_type: str = "close") -> Optional[float]:
        """
        计算移动平均线
        
        Args:
            symbol: 合约代码
            period: 周期
            data_type: 数据类型 (close/open/high/low)
            
        Returns:
            float: MA值，数据不足时返回None
        """
        recent_bars = self.get_recent_bars(symbol, period)
        
        if len(recent_bars) < period:
            return None
        
        # 根据数据类型获取价格
        if data_type == "close":
            prices = [bar.close_price for bar in recent_bars[-period:]]
        elif data_type == "open":
            prices = [bar.open_price for bar in recent_bars[-period:]]
        elif data_type == "high":
            prices = [bar.high_price for bar in recent_bars[-period:]]
        elif data_type == "low":
            prices = [bar.low_price for bar in recent_bars[-period:]]
        else:
            prices = [bar.close_price for bar in recent_bars[-period:]]
        
        return sum(prices) / len(prices)
    
    def update_statistics(self, trade: TradeData) -> None:
        """更新策略统计信息"""
        with self.lock:
            self.trades.append(trade)
            self.total_trades += 1
            
            # 这里简化处理，实际应该根据开平仓计算盈亏
            if hasattr(trade, 'pnl') and trade.pnl > 0:
                self.win_trades += 1
            elif hasattr(trade, 'pnl') and trade.pnl < 0:
                self.loss_trades += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取策略统计信息"""
        with self.lock:
            win_rate = self.win_trades / self.total_trades if self.total_trades > 0 else 0
            
            return {
                "strategy_name": self.strategy_name,
                "status": self.status.value,
                "start_time": self.start_time,
                "total_trades": self.total_trades,
                "win_trades": self.win_trades,
                "loss_trades": self.loss_trades,
                "win_rate": win_rate,
                "total_pnl": self.total_pnl,
                "signals_count": len(self.signals)
            }
    
    def _set_status(self, status: StrategyStatus) -> None:
        """设置策略状态"""
        old_status = self.status
        self.status = status
        print(f"🔄 策略状态变更: {self.strategy_name} {old_status.value} -> {status.value}")


class DataEventDispatcher:
    """
    数据事件分发器
    负责将市场数据事件分发给各个策略
    """
    
    def __init__(self):
        """初始化事件分发器"""
        self.strategy_subscribers: Dict[StrategyEvent, List[StrategyBase]] = {
            StrategyEvent.TICK: [],
            StrategyEvent.BAR: [],
            StrategyEvent.TRADE: [],
            StrategyEvent.ORDER: [],
            StrategyEvent.POSITION: [],
            StrategyEvent.TIMER: []
        }
        
        self.symbol_subscribers: Dict[str, List[StrategyBase]] = {}
        self.lock = threading.Lock()
        
        print("✅ 数据事件分发器初始化完成")
    
    def subscribe_strategy(self, strategy: StrategyBase, events: List[StrategyEvent]) -> None:
        """
        订阅策略事件
        
        Args:
            strategy: 策略实例
            events: 事件类型列表
        """
        with self.lock:
            for event in events:
                if event in self.strategy_subscribers:
                    if strategy not in self.strategy_subscribers[event]:
                        self.strategy_subscribers[event].append(strategy)
            
            # 订阅策略关注的合约
            for symbol in strategy.config.symbols:
                if symbol not in self.symbol_subscribers:
                    self.symbol_subscribers[symbol] = []
                if strategy not in self.symbol_subscribers[symbol]:
                    self.symbol_subscribers[symbol].append(strategy)
        
        print(f"✅ 策略事件订阅: {strategy.strategy_name} -> {[e.value for e in events]}")
    
    def unsubscribe_strategy(self, strategy: StrategyBase) -> None:
        """取消策略订阅"""
        with self.lock:
            # 从事件订阅中移除
            for event_list in self.strategy_subscribers.values():
                if strategy in event_list:
                    event_list.remove(strategy)
            
            # 从合约订阅中移除
            for symbol_list in self.symbol_subscribers.values():
                if strategy in symbol_list:
                    symbol_list.remove(strategy)
        
        print(f"✅ 取消策略订阅: {strategy.strategy_name}")
    
    def dispatch_tick(self, tick: TickData) -> None:
        """分发Tick数据事件"""
        strategies_to_notify = []
        
        with self.lock:
            # 获取订阅tick事件的策略
            tick_strategies = self.strategy_subscribers.get(StrategyEvent.TICK, [])
            
            # 获取订阅该合约的策略
            symbol_strategies = self.symbol_subscribers.get(tick.symbol, [])
            
            # 合并并去重
            strategies_to_notify = list(set(tick_strategies) & set(symbol_strategies))
        
        # 分发事件（在锁外执行，避免阻塞）
        for strategy in strategies_to_notify:
            try:
                strategy.add_tick_data(tick)
                strategy.on_tick(tick)
            except Exception as e:
                print(f"❌ 策略Tick事件处理失败: {strategy.strategy_name} -> {e}")
    
    def dispatch_bar(self, bar: BarData) -> None:
        """分发Bar数据事件"""
        strategies_to_notify = []
        
        with self.lock:
            # 获取订阅bar事件的策略
            bar_strategies = self.strategy_subscribers.get(StrategyEvent.BAR, [])
            
            # 获取订阅该合约的策略
            symbol_strategies = self.symbol_subscribers.get(bar.symbol, [])
            
            # 合并并去重
            strategies_to_notify = list(set(bar_strategies) & set(symbol_strategies))
        
        # 分发事件
        for strategy in strategies_to_notify:
            try:
                strategy.add_bar_data(bar)
                strategy.on_bar(bar)
            except Exception as e:
                print(f"❌ 策略Bar事件处理失败: {strategy.strategy_name} -> {e}")
    
    def dispatch_trade(self, trade: TradeData) -> None:
        """分发成交事件"""
        with self.lock:
            trade_strategies = self.strategy_subscribers.get(StrategyEvent.TRADE, [])
        
        # 分发到所有订阅成交事件的策略
        for strategy in trade_strategies:
            try:
                strategy.update_statistics(trade)
                strategy.on_trade(trade)
            except Exception as e:
                print(f"❌ 策略Trade事件处理失败: {strategy.strategy_name} -> {e}")


class StrategyManager:
    """
    策略管理器
    负责策略的加载、启动、停止和监控
    """
    
    def __init__(self, trading_engine: TradingEngine):
        """
        初始化策略管理器
        
        Args:
            trading_engine: 交易引擎
        """
        self.trading_engine = trading_engine
        self.strategies: Dict[str, StrategyBase] = {}
        self.strategy_configs: Dict[str, StrategyConfig] = {}
        self.lock = threading.Lock()
        
        print("✅ 策略管理器初始化完成")
    
    def register_strategy_class(self, strategy_class: Type[StrategyBase]) -> None:
        """
        注册策略类
        
        Args:
            strategy_class: 策略类
        """
        class_name = strategy_class.__name__
        print(f"✅ 策略类注册: {class_name}")
    
    def load_strategy(self, strategy_class: Type[StrategyBase], config: StrategyConfig) -> bool:
        """
        加载策略
        
        Args:
            strategy_class: 策略类
            config: 策略配置
            
        Returns:
            bool: 是否加载成功
        """
        try:
            with self.lock:
                strategy_name = config.name
                
                if strategy_name in self.strategies:
                    print(f"❌ 策略已存在: {strategy_name}")
                    return False
                
                # 创建策略实例
                strategy = strategy_class(strategy_name, config, self.trading_engine)
                strategy._set_status(StrategyStatus.LOADING)
                
                # 调用策略初始化
                strategy.on_init()
                
                # 存储策略
                self.strategies[strategy_name] = strategy
                self.strategy_configs[strategy_name] = config
                
                strategy._set_status(StrategyStatus.LOADED)
                
                print(f"✅ 策略加载成功: {strategy_name}")
                return True
                
        except Exception as e:
            print(f"❌ 策略加载失败: {config.name} -> {e}")
            return False
    
    def start_strategy(self, strategy_name: str) -> bool:
        """
        启动策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            bool: 是否启动成功
        """
        try:
            with self.lock:
                if strategy_name not in self.strategies:
                    print(f"❌ 策略不存在: {strategy_name}")
                    return False
                
                strategy = self.strategies[strategy_name]
                
                if strategy.status != StrategyStatus.LOADED:
                    print(f"❌ 策略状态不正确: {strategy_name} -> {strategy.status.value}")
                    return False
                
                strategy._set_status(StrategyStatus.STARTING)
                
                # 调用策略启动
                strategy.on_start()
                strategy.start_time = datetime.now()
                
                strategy._set_status(StrategyStatus.RUNNING)
                
                print(f"✅ 策略启动成功: {strategy_name}")
                return True
                
        except Exception as e:
            print(f"❌ 策略启动失败: {strategy_name} -> {e}")
            if strategy_name in self.strategies:
                self.strategies[strategy_name]._set_status(StrategyStatus.ERROR)
            return False
    
    def stop_strategy(self, strategy_name: str) -> bool:
        """
        停止策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            bool: 是否停止成功
        """
        try:
            with self.lock:
                if strategy_name not in self.strategies:
                    print(f"❌ 策略不存在: {strategy_name}")
                    return False
                
                strategy = self.strategies[strategy_name]
                
                if strategy.status != StrategyStatus.RUNNING:
                    print(f"❌ 策略未在运行: {strategy_name} -> {strategy.status.value}")
                    return False
                
                strategy._set_status(StrategyStatus.STOPPING)
                
                # 调用策略停止
                strategy.on_stop()
                strategy.stop_time = datetime.now()
                
                strategy._set_status(StrategyStatus.STOPPED)
                
                print(f"✅ 策略停止成功: {strategy_name}")
                return True
                
        except Exception as e:
            print(f"❌ 策略停止失败: {strategy_name} -> {e}")
            if strategy_name in self.strategies:
                self.strategies[strategy_name]._set_status(StrategyStatus.ERROR)
            return False
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """
        移除策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            bool: 是否移除成功
        """
        try:
            with self.lock:
                if strategy_name not in self.strategies:
                    print(f"❌ 策略不存在: {strategy_name}")
                    return False
                
                strategy = self.strategies[strategy_name]
                
                # 如果策略在运行，先停止
                if strategy.status == StrategyStatus.RUNNING:
                    self.stop_strategy(strategy_name)
                
                # 移除策略
                del self.strategies[strategy_name]
                del self.strategy_configs[strategy_name]
                
                print(f"✅ 策略移除成功: {strategy_name}")
                return True
                
        except Exception as e:
            print(f"❌ 策略移除失败: {strategy_name} -> {e}")
            return False
    
    def get_strategy(self, strategy_name: str) -> Optional[StrategyBase]:
        """获取策略实例"""
        with self.lock:
            return self.strategies.get(strategy_name)
    
    def get_active_strategies(self) -> Dict[str, StrategyBase]:
        """获取运行中的策略"""
        with self.lock:
            return {name: strategy for name, strategy in self.strategies.items() 
                   if strategy.status == StrategyStatus.RUNNING}
    
    def get_all_strategies(self) -> Dict[str, StrategyBase]:
        """获取所有策略"""
        with self.lock:
            return self.strategies.copy()
    
    def get_strategy_statistics(self) -> Dict[str, Dict[str, Any]]:
        """获取所有策略统计信息"""
        with self.lock:
            return {name: strategy.get_statistics() 
                   for name, strategy in self.strategies.items()}


class StrategyEngine:
    """
    策略引擎主类
    集成策略管理、数据分发和交易执行功能
    """
    
    def __init__(self, trading_engine: TradingEngine, market_data_manager: MarketDataManager):
        """
        初始化策略引擎
        
        Args:
            trading_engine: 交易引擎
            market_data_manager: 市场数据管理器
        """
        self.trading_engine = trading_engine
        self.market_data_manager = market_data_manager
        
        # 初始化子模块
        self.strategy_manager = StrategyManager(trading_engine)
        self.event_dispatcher = DataEventDispatcher()
        
        # 注册数据回调
        self._register_data_callbacks()
        
        print("🚀 策略引擎初始化完成")
    
    def _register_data_callbacks(self) -> None:
        """注册数据回调"""
        # 注册市场数据回调
        self.market_data_manager.register_tick_callback(self.event_dispatcher.dispatch_tick)
        self.market_data_manager.register_bar_callback(self.event_dispatcher.dispatch_bar)
        
        # 注册交易回调
        self.trading_engine.register_trade_callback(self.event_dispatcher.dispatch_trade)
        
        print("✅ 数据回调注册完成")
    
    def load_strategy(self, strategy_class: Type[StrategyBase], config: StrategyConfig) -> bool:
        """加载策略"""
        success = self.strategy_manager.load_strategy(strategy_class, config)
        
        if success:
            # 订阅策略事件
            strategy = self.strategy_manager.get_strategy(config.name)
            if strategy:
                events = [StrategyEvent.TICK, StrategyEvent.BAR, StrategyEvent.TRADE]
                self.event_dispatcher.subscribe_strategy(strategy, events)
        
        return success
    
    def start_strategy(self, strategy_name: str) -> bool:
        """启动策略"""
        return self.strategy_manager.start_strategy(strategy_name)
    
    def stop_strategy(self, strategy_name: str) -> bool:
        """停止策略"""
        success = self.strategy_manager.stop_strategy(strategy_name)
        
        if success:
            # 取消事件订阅
            strategy = self.strategy_manager.get_strategy(strategy_name)
            if strategy:
                self.event_dispatcher.unsubscribe_strategy(strategy)
        
        return success
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """移除策略"""
        # 先取消订阅
        strategy = self.strategy_manager.get_strategy(strategy_name)
        if strategy:
            self.event_dispatcher.unsubscribe_strategy(strategy)
        
        return self.strategy_manager.remove_strategy(strategy_name)
    
    @property
    def active_strategies(self) -> Dict[str, StrategyBase]:
        """获取运行中的策略"""
        return self.strategy_manager.get_active_strategies()
    
    def get_strategy_statistics(self) -> Dict[str, Dict[str, Any]]:
        """获取策略统计信息"""
        return self.strategy_manager.get_strategy_statistics()
    
    def is_ready(self) -> bool:
        """检查策略引擎是否就绪"""
        return (self.trading_engine.is_ready() and 
                self.market_data_manager is not None)
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略引擎状态"""
        active_strategies = self.active_strategies
        
        return {
            "ready": self.is_ready(),
            "total_strategies": len(self.strategy_manager.get_all_strategies()),
            "active_strategies": len(active_strategies),
            "active_strategy_names": list(active_strategies.keys()),
            "trading_engine_ready": self.trading_engine.is_ready(),
            "market_data_ready": self.market_data_manager is not None
        }


# 示例策略类
class MockStrategy(StrategyBase):
    """
    示例策略类
    用于测试策略框架功能
    """
    
    def __init__(self, strategy_name: str, config: StrategyConfig, trading_engine: TradingEngine):
        super().__init__(strategy_name, config, trading_engine)
        self.tick_count = 0
        self.bar_count = 0
        
    def on_init(self) -> None:
        """策略初始化"""
        print(f"📊 MockStrategy初始化: {self.strategy_name}")
        print(f"   关注合约: {self.config.symbols}")
        print(f"   策略参数: {self.config.parameters}")
    
    def on_start(self) -> None:
        """策略启动"""
        print(f"🚀 MockStrategy启动: {self.strategy_name}")
    
    def on_stop(self) -> None:
        """策略停止"""
        print(f"🛑 MockStrategy停止: {self.strategy_name}")
        print(f"   处理Tick: {self.tick_count}个")
        print(f"   处理Bar: {self.bar_count}个")
    
    def on_tick(self, tick: TickData) -> None:
        """处理Tick数据"""
        self.tick_count += 1
        
        # 简单的演示逻辑
        if self.tick_count % 50 == 0:
            print(f"📈 MockStrategy处理Tick: {tick.symbol} @ {tick.last_price:.2f} (第{self.tick_count}个)")
    
    def on_bar(self, bar: BarData) -> None:
        """处理Bar数据"""
        self.bar_count += 1
        print(f"📊 MockStrategy处理Bar: {bar.symbol} Close={bar.close_price:.2f} (第{self.bar_count}个)")
    
    def on_trade(self, trade: TradeData) -> None:
        """处理成交数据"""
        print(f"💰 MockStrategy处理成交: {trade.symbol} {trade.direction.value} "
              f"{trade.volume}手@{trade.price:.2f}")


def create_sample_strategy_config(name: str = "test_strategy", 
                                symbols: List[str] = None) -> StrategyConfig:
    """
    创建示例策略配置
    
    Args:
        name: 策略名称
        symbols: 合约列表
        
    Returns:
        StrategyConfig: 策略配置
    """
    if symbols is None:
        symbols = ["rb2310", "i2310"]
    
    return StrategyConfig(
        name=name,
        symbols=symbols,
        class_name="MockStrategy",
        parameters={"param1": "value1", "param2": 42},
        enabled=True,
        auto_start=False,
        initial_capital=100000.0,
        max_position_size=5,
        description="示例测试策略",
        version="1.0.0"
    )