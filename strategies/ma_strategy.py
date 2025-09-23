#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MA Strategy Implementation

移动平均线交易策略实现
- 使用MA5和MA20进行金叉死叉判断
- 金叉做多，死叉做空
- 支持风险管理和仓位控制
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import threading
from datetime import datetime

from core.strategy_engine import StrategyBase
from core.data_types import BarData, TickData, TradeData, OrderData, Exchange, Direction


@dataclass
class MAIndicator:
    """移动平均线指标"""
    period: int
    current_ma: float = 0.0
    
    def __post_init__(self):
        self.values = deque(maxlen=self.period)
    
    def update(self, price: float) -> float:
        """更新MA值"""
        self.values.append(price)
        if len(self.values) >= self.period:
            self.current_ma = sum(self.values) / len(self.values)
        return self.current_ma
    
    def is_ready(self) -> bool:
        """判断指标是否准备好"""
        return len(self.values) >= self.period


@dataclass
class PositionInfo:
    """持仓信息"""
    symbol: str
    direction: str  # 'long', 'short', 'none'
    volume: int = 0
    avg_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    def is_long(self) -> bool:
        return self.direction == 'long' and self.volume > 0
    
    def is_short(self) -> bool:
        return self.direction == 'short' and self.volume > 0
    
    def is_empty(self) -> bool:
        return self.direction == 'none' or self.volume == 0


@dataclass 
class SignalInfo:
    """信号信息"""
    timestamp: datetime
    signal_type: str  # 'golden_cross', 'death_cross', 'none'
    fast_ma: float
    slow_ma: float
    price: float
    confidence: float = 1.0


class MAStrategy(StrategyBase):
    """移动平均线交易策略"""
    
    def __init__(self, strategy_name: str, config, trading_engine=None):
        # 处理不同类型的配置 - 兼容字典和StrategyConfig对象
        if isinstance(config, dict):
            # 字典类型配置 - 多策略管理器使用
            config_dict = config
            # 创建一个简化的配置对象供父类使用
            class SimpleConfig:
                def __init__(self, d):
                    # 设置基本属性
                    self.name = strategy_name
                    self.symbols = d.get('subscribed_symbols', [])
                    self.class_name = "MAStrategy" 
                    self.parameters = d
                    self.enabled = True
                    self.auto_start = False
                    self.initial_capital = 100000.0
                    self.max_position_size = 10
                    self.stop_loss = 0.05
                    self.take_profit = 0.10
                    self.description = "MA Strategy"
                    self.version = "1.0.0"
                    # 复制其他属性
                    for k, v in d.items():
                        if not hasattr(self, k):
                            setattr(self, k, v)
            config_obj = SimpleConfig(config_dict)
        else:
            # StrategyConfig对象 - 策略引擎使用
            config_obj = config
            config_dict = config.parameters if hasattr(config, 'parameters') and config.parameters else {}
        
        super().__init__(strategy_name, config_obj, trading_engine)
        
        # 策略参数
        self.fast_period = config_dict.get('fast_period', 5)  # 快线周期
        self.slow_period = config_dict.get('slow_period', 20)  # 慢线周期
        self.trade_volume = config_dict.get('trade_volume', 1)  # 交易手数
        self.max_position = config_dict.get('max_position', 5)  # 最大持仓
        
        # 订阅的合约列表 - 支持从配置获取
        self.subscribed_symbols = config_dict.get('subscribed_symbols', [])
        if hasattr(config_obj, 'symbols') and config_obj.symbols:
            self.subscribed_symbols = config_obj.symbols
        
        # 风险管理参数
        self.stop_loss_pct = config_dict.get('stop_loss_pct', 0.02)  # 止损百分比
        self.take_profit_pct = config_dict.get('take_profit_pct', 0.04)  # 止盈百分比
        
        # 指标实例
        self.indicators: Dict[str, Dict[str, MAIndicator]] = {}
        
        # 持仓管理
        self.positions: Dict[str, PositionInfo] = {}
        
        # 信号历史
        self.signals: List[SignalInfo] = []
        
        # 交易记录
        self.trades: List[TradeData] = []
        self.orders: Dict[str, OrderData] = {}
        
        # 统计信息
        self.total_trades = 0
        self.win_trades = 0
        self.total_pnl = 0.0
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 日志
        self.logger = logging.getLogger(f"MAStrategy.{strategy_name}")
        
        self.logger.info(f"MA策略初始化完成 - 快线:{self.fast_period}, 慢线:{self.slow_period}")
    
    def on_init(self) -> None:
        """策略初始化"""
        try:
            self.logger.info("开始初始化MA策略...")
            
            # 初始化订阅的合约指标
            for symbol in self.subscribed_symbols:
                self.indicators[symbol] = {
                    'fast_ma': MAIndicator(self.fast_period),
                    'slow_ma': MAIndicator(self.slow_period)
                }
                
                # 初始化持仓信息
                self.positions[symbol] = PositionInfo(
                    symbol=symbol,
                    direction='none'
                )
            
            self.logger.info(f"MA策略初始化完成，订阅合约: {self.subscribed_symbols}")
            
        except Exception as e:
            self.logger.error(f"MA策略初始化失败: {e}")
            raise
    
    def on_start(self) -> None:
        """策略启动"""
        try:
            self.logger.info("MA策略启动中...")
            
            # 清理历史数据
            self.signals.clear()
            self.trades.clear() 
            self.orders.clear()
            
            # 重置统计
            self.total_trades = 0
            self.win_trades = 0
            self.total_pnl = 0.0
            
            self.logger.info("MA策略启动完成")
            
        except Exception as e:
            self.logger.error(f"MA策略启动失败: {e}")
            raise
    
    def on_stop(self) -> None:
        """策略停止"""
        try:
            self.logger.info("MA策略停止中...")
            
            # 平仓所有持仓
            for symbol, position in self.positions.items():
                if not position.is_empty():
                    self._close_position(symbol, position)
            
            # 打印统计信息
            self._print_statistics()
            
            self.logger.info("MA策略停止完成")
            
        except Exception as e:
            self.logger.error(f"MA策略停止失败: {e}")
            raise
    
    def on_tick(self, tick: TickData) -> None:
        """处理Tick数据"""
        try:
            with self._lock:
                # 更新持仓盈亏
                self._update_position_pnl(tick.symbol, tick.last_price)
                
                # 检查风险控制
                self._check_risk_management(tick.symbol, tick.last_price)
                
        except Exception as e:
            self.logger.error(f"处理Tick数据失败 {tick.symbol}: {e}")
    
    def on_bar(self, bar: BarData) -> None:
        """处理K线数据 - 主要交易逻辑"""
        try:
            with self._lock:
                symbol = bar.symbol
                
                # 更新MA指标
                fast_ma, slow_ma = self._update_indicators(symbol, bar.close_price)
                
                # 检查是否可以生成信号
                if not self._indicators_ready(symbol):
                    return
                
                # 生成交易信号
                signal = self._generate_signal(symbol, bar, fast_ma, slow_ma)
                
                if signal.signal_type != 'none':
                    self.signals.append(signal)
                    self.logger.info(f"生成信号: {symbol} - {signal.signal_type}, MA({fast_ma:.2f}, {slow_ma:.2f})")
                
                # 执行交易逻辑
                self._execute_trading_logic(symbol, signal, bar.close_price)
                
        except Exception as e:
            self.logger.error(f"处理K线数据失败 {bar.symbol}: {e}")
    
    def on_trade(self, trade: TradeData) -> None:
        """处理成交数据"""
        try:
            with self._lock:
                self.trades.append(trade)
                
                # 更新持仓信息
                self._update_position(trade)
                
                # 更新统计
                self._update_statistics(trade)
                
                self.logger.info(f"成交回报: {trade.symbol} {trade.direction} {trade.volume}@{trade.price}")
                
        except Exception as e:
            self.logger.error(f"处理成交数据失败: {e}")
    
    def handle_order(self, order: OrderData) -> None:
        """处理订单数据"""
        try:
            with self._lock:
                self.orders[order.order_id] = order
                
                if order.status == 'rejected':
                    self.logger.warning(f"订单被拒绝: {order.symbol} {order.direction} {order.volume}")
                elif order.status == 'cancelled':
                    self.logger.info(f"订单已撤销: {order.symbol} {order.direction} {order.volume}")
                    
        except Exception as e:
            self.logger.error(f"处理订单数据失败: {e}")
    
    def _update_indicators(self, symbol: str, price: float) -> Tuple[float, float]:
        """更新MA指标"""
        indicators = self.indicators.get(symbol, {})
        
        fast_ma = indicators['fast_ma'].update(price)
        slow_ma = indicators['slow_ma'].update(price)
        
        return fast_ma, slow_ma
    
    def _indicators_ready(self, symbol: str) -> bool:
        """检查指标是否准备好"""
        indicators = self.indicators.get(symbol, {})
        return (indicators['fast_ma'].is_ready() and 
                indicators['slow_ma'].is_ready())
    
    def _generate_signal(self, symbol: str, bar: BarData, fast_ma: float, slow_ma: float) -> SignalInfo:
        """生成交易信号"""
        signal_type = 'none'
        
        # 检查是否有历史MA值用于比较
        if hasattr(self, '_prev_mas') and symbol in self._prev_mas:
            prev_fast, prev_slow = self._prev_mas[symbol]
            
            # 金叉：快线从下方穿越慢线
            if prev_fast <= prev_slow and fast_ma > slow_ma:
                signal_type = 'golden_cross'
                self.logger.info(f"检测到金叉: {symbol} - 前快线:{prev_fast:.2f}, 前慢线:{prev_slow:.2f}, 当前快线:{fast_ma:.2f}, 当前慢线:{slow_ma:.2f}")
            # 死叉：快线从上方穿越慢线
            elif prev_fast >= prev_slow and fast_ma < slow_ma:
                signal_type = 'death_cross'
                self.logger.info(f"检测到死叉: {symbol} - 前快线:{prev_fast:.2f}, 前慢线:{prev_slow:.2f}, 当前快线:{fast_ma:.2f}, 当前慢线:{slow_ma:.2f}")
        
        # 保存当前MA值用于下次比较
        if not hasattr(self, '_prev_mas'):
            self._prev_mas = {}
        self._prev_mas[symbol] = (fast_ma, slow_ma)
        
        return SignalInfo(
            timestamp=bar.datetime,
            signal_type=signal_type,
            fast_ma=fast_ma,
            slow_ma=slow_ma,
            price=bar.close_price,
            confidence=1.0
        )
    
    def _execute_trading_logic(self, symbol: str, signal: SignalInfo, current_price: float) -> None:
        """执行交易逻辑"""
        position = self.positions.get(symbol)
        if not position:
            return
        
        # 金叉信号 - 做多
        if signal.signal_type == 'golden_cross':
            if position.is_empty():
                # 开多仓
                self._open_long_position(symbol, current_price)
            elif position.is_short():
                # 先平空仓，再开多仓
                self._close_position(symbol, position)
                self._open_long_position(symbol, current_price)
        
        # 死叉信号 - 做空 
        elif signal.signal_type == 'death_cross':
            if position.is_empty():
                # 开空仓
                self._open_short_position(symbol, current_price)
            elif position.is_long():
                # 先平多仓，再开空仓
                self._close_position(symbol, position)
                self._open_short_position(symbol, current_price)
    
    def _open_long_position(self, symbol: str, price: float) -> None:
        """开多仓"""
        position = self.positions[symbol]
        
        # 检查最大持仓限制
        if position.volume >= self.max_position:
            self.logger.warning(f"达到最大持仓限制: {symbol}")
            return
        
        # 发送买入订单 (这里是模拟，实际需要调用交易接口)
        self.logger.info(f"开多仓: {symbol} {self.trade_volume}手 @{price}")
        
        # 模拟成交
        trade = TradeData(
            tradeid=f"trade_{len(self.trades)+1}",
            orderid=f"order_{len(self.trades)+1}",
            symbol=symbol,
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            volume=self.trade_volume,
            price=price,
            datetime=datetime.now()
        )
        
        # 直接处理成交
        self.on_trade(trade)
    
    def _open_short_position(self, symbol: str, price: float) -> None:
        """开空仓"""
        position = self.positions[symbol]
        
        # 检查最大持仓限制
        if position.volume >= self.max_position:
            self.logger.warning(f"达到最大持仓限制: {symbol}")
            return
        
        # 发送卖出订单
        self.logger.info(f"开空仓: {symbol} {self.trade_volume}手 @{price}")
        
        # 模拟成交
        trade = TradeData(
            tradeid=f"trade_{len(self.trades)+1}",
            orderid=f"order_{len(self.trades)+1}",
            symbol=symbol,
            exchange=Exchange.SHFE,
            direction=Direction.SHORT,
            volume=self.trade_volume,
            price=price,
            datetime=datetime.now()
        )
        
        self.on_trade(trade)
    
    def _close_position(self, symbol: str, position: PositionInfo) -> None:
        """平仓"""
        if position.is_empty():
            return
        
        if position.is_long():
            # 平多仓 - 卖出
            self.logger.info(f"平多仓: {symbol} {position.volume}手")
            direction = 'sell'
        else:
            # 平空仓 - 买入
            self.logger.info(f"平空仓: {symbol} {position.volume}手") 
            direction = 'buy'
        
        # 模拟成交 - 使用当前持仓量
        trade_direction = Direction.SHORT if direction == 'sell' else Direction.LONG
        trade = TradeData(
            tradeid=f"trade_{len(self.trades)+1}",
            orderid=f"order_{len(self.trades)+1}",
            symbol=symbol,
            exchange=Exchange.SHFE,
            direction=trade_direction,
            volume=position.volume,
            price=0.0,  # 实际应该是当前市价
            datetime=datetime.now()
        )
        
        self.on_trade(trade)
    
    def _update_position(self, trade: TradeData) -> None:
        """更新持仓信息"""
        position = self.positions[trade.symbol]
        
        if trade.direction == Direction.LONG:
            if position.direction == 'short':
                # 平空仓
                position.volume -= trade.volume
                if position.volume <= 0:
                    position.direction = 'none'
                    position.volume = 0
                    position.avg_price = 0.0
            else:
                # 开多仓或加仓
                old_cost = position.volume * position.avg_price
                new_cost = trade.volume * trade.price
                total_volume = position.volume + trade.volume
                
                position.avg_price = (old_cost + new_cost) / total_volume if total_volume > 0 else 0.0
                position.volume = total_volume
                position.direction = 'long'
        
        elif trade.direction == Direction.SHORT:
            if position.direction == 'long':
                # 平多仓
                position.volume -= trade.volume
                if position.volume <= 0:
                    position.direction = 'none'
                    position.volume = 0
                    position.avg_price = 0.0
            else:
                # 开空仓或加仓
                old_cost = position.volume * position.avg_price
                new_cost = trade.volume * trade.price
                total_volume = position.volume + trade.volume
                
                position.avg_price = (old_cost + new_cost) / total_volume if total_volume > 0 else 0.0
                position.volume = total_volume
                position.direction = 'short'
    
    def _update_position_pnl(self, symbol: str, current_price: float) -> None:
        """更新持仓盈亏"""
        position = self.positions.get(symbol)
        if not position or position.is_empty():
            return
        
        if position.is_long():
            position.unrealized_pnl = (current_price - position.avg_price) * position.volume
        elif position.is_short():
            position.unrealized_pnl = (position.avg_price - current_price) * position.volume
    
    def _check_risk_management(self, symbol: str, current_price: float) -> None:
        """检查风险管理"""
        position = self.positions.get(symbol)
        if not position or position.is_empty():
            return
        
        # 计算当前盈亏百分比
        pnl_pct = position.unrealized_pnl / (position.avg_price * position.volume)
        
        # 止损检查
        if pnl_pct <= -self.stop_loss_pct:
            self.logger.warning(f"触发止损: {symbol}, 盈亏:{pnl_pct:.2%}")
            self._close_position(symbol, position)
        
        # 止盈检查  
        elif pnl_pct >= self.take_profit_pct:
            self.logger.info(f"触发止盈: {symbol}, 盈亏:{pnl_pct:.2%}")
            self._close_position(symbol, position)
    
    def _update_statistics(self, trade: TradeData) -> None:
        """更新统计信息"""
        # 简单统计逻辑
        self.total_trades += 1
    
    def _print_statistics(self) -> None:
        """打印策略统计信息"""
        self.logger.info("=== MA策略统计信息 ===")
        self.logger.info(f"总交易次数: {self.total_trades}")
        self.logger.info(f"胜率: {self.win_trades/self.total_trades:.2%}" if self.total_trades > 0 else "胜率: 0%")
        self.logger.info(f"总盈亏: {self.total_pnl:.2f}")
        self.logger.info(f"信号数量: {len(self.signals)}")
        self.logger.info("==================")
    
    def get_strategy_info(self) -> dict:
        """获取策略信息"""
        return {
            'strategy_name': self.strategy_name,
            'strategy_type': 'MA Strategy',
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'trade_volume': self.trade_volume,
            'max_position': self.max_position,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'total_trades': self.total_trades,
            'win_trades': self.win_trades,
            'total_pnl': self.total_pnl,
            'signals_count': len(self.signals),
            'positions': {symbol: {
                'direction': pos.direction,
                'volume': pos.volume,
                'avg_price': pos.avg_price,
                'unrealized_pnl': pos.unrealized_pnl
            } for symbol, pos in self.positions.items()},
            'subscribed_symbols': self.subscribed_symbols,
            'status': self.status
        }