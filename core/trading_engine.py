#!/usr/bin/env python3
"""
TradingEngine - 交易引擎模块
负责订单管理、持仓管理和交易执行

Milestone 2.1 核心模块 - 实现完整的交易功能
"""

import json
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
import uuid

from .data_types import (
    OrderRequest, OrderData, TradeData, PositionData, AccountData,
    TradingSignal, TradingResult, OrderType, OrderStatus, Direction, 
    Offset, Exchange, TradingSignalAction
)
from .connection_manager import ConnectionManager

class OrderManager:
    """
    订单管理器
    负责订单的创建、跟踪和状态管理
    """
    
    def __init__(self):
        """初始化订单管理器"""
        self.orders: Dict[str, OrderData] = {}           # 活跃订单字典
        self.order_history: Dict[str, OrderData] = {}     # 历史订单字典
        self.next_order_id = 1                           # 下一个订单ID
        self.lock = threading.Lock()                     # 线程锁
        
        print("✅ OrderManager初始化完成")
    
    def generate_order_id(self) -> str:
        """生成唯一订单ID"""
        with self.lock:
            order_id = f"ORDER_{self.next_order_id:06d}_{int(time.time())}"
            self.next_order_id += 1
            return order_id
    
    def create_order(self, request: OrderRequest) -> OrderData:
        """
        创建订单对象
        
        Args:
            request: 订单请求
            
        Returns:
            OrderData: 创建的订单对象
        """
        order_id = self.generate_order_id()
        
        order = OrderData(
            orderid=order_id,
            symbol=request.symbol,
            exchange=request.exchange,
            direction=request.direction,
            type=request.type,
            volume=request.volume,
            traded=0,
            status=OrderStatus.SUBMITTING,
            datetime=datetime.now(),
            price=request.price,
            offset=request.offset,
            reference=request.reference,
            gateway_name=request.gateway_name
        )
        
        with self.lock:
            self.orders[order_id] = order
        
        print(f"📝 创建订单: {order_id} {request.symbol} {request.direction.value} {request.volume}手")
        return order
    
    def update_order_status(self, orderid: str, status: OrderStatus) -> bool:
        """
        更新订单状态
        
        Args:
            orderid: 订单ID
            status: 新状态
            
        Returns:
            bool: 是否更新成功
        """
        with self.lock:
            if orderid in self.orders:
                old_status = self.orders[orderid].status
                self.orders[orderid].status = status
                
                # 如果订单完结，移至历史
                if status in [OrderStatus.ALLTRADED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                    self.order_history[orderid] = self.orders[orderid]
                    del self.orders[orderid]
                
                print(f"🔄 订单状态更新: {orderid} {old_status.value} → {status.value}")
                return True
            
        return False
    
    def update_order_traded(self, orderid: str, traded_volume: int) -> bool:
        """
        更新订单成交数量
        
        Args:
            orderid: 订单ID  
            traded_volume: 新增成交数量
            
        Returns:
            bool: 是否更新成功
        """
        with self.lock:
            if orderid in self.orders:
                order = self.orders[orderid]
                order.traded += traded_volume
                
                # 检查是否全部成交
                if order.traded >= order.volume:
                    order.status = OrderStatus.ALLTRADED
                    self.order_history[orderid] = order
                    del self.orders[orderid]
                    print(f"✅ 订单全部成交: {orderid} {order.traded}/{order.volume}手")
                elif order.traded > 0:
                    order.status = OrderStatus.PARTTRADED
                    print(f"🔸 订单部分成交: {orderid} {order.traded}/{order.volume}手")
                
                return True
        
        return False
    
    def get_order(self, orderid: str) -> Optional[OrderData]:
        """获取订单信息"""
        with self.lock:
            # 先查活跃订单
            if orderid in self.orders:
                return self.orders[orderid]
            # 再查历史订单  
            if orderid in self.order_history:
                return self.order_history[orderid]
        return None
    
    def get_active_orders(self, symbol: str = None) -> List[OrderData]:
        """获取活跃订单列表"""
        with self.lock:
            orders = list(self.orders.values())
            if symbol:
                orders = [order for order in orders if order.symbol == symbol]
            return orders
    
    def cancel_order(self, orderid: str) -> bool:
        """取消订单"""
        with self.lock:
            if orderid in self.orders:
                order = self.orders[orderid]
                if order.status in [OrderStatus.NOTTRADED, OrderStatus.PARTTRADED]:
                    self.update_order_status(orderid, OrderStatus.CANCELLED)
                    print(f"❌ 订单已取消: {orderid}")
                    return True
        return False


class PositionManager:
    """
    持仓管理器
    负责持仓的计算、更新和查询
    """
    
    def __init__(self):
        """初始化持仓管理器"""
        self.positions: Dict[str, PositionData] = {}      # 持仓字典 key: symbol_direction
        self.lock = threading.Lock()                      # 线程锁
        
        print("✅ PositionManager初始化完成")
    
    def _get_position_key(self, symbol: str, direction: Direction) -> str:
        """生成持仓键值"""
        return f"{symbol}_{direction.value}"
    
    def update_position(self, trade: TradeData) -> None:
        """
        根据成交更新持仓
        
        Args:
            trade: 成交数据
        """
        position_key = self._get_position_key(trade.symbol, trade.direction)
        
        with self.lock:
            if position_key not in self.positions:
                # 创建新持仓
                self.positions[position_key] = PositionData(
                    symbol=trade.symbol,
                    exchange=trade.exchange,
                    direction=trade.direction,
                    volume=0,
                    frozen=0,
                    price=0.0,
                    pnl=0.0,
                    gateway_name=trade.gateway_name
                )
            
            position = self.positions[position_key]
            
            if trade.offset == Offset.OPEN:
                # 开仓：增加持仓
                old_volume = position.volume
                old_price = position.price
                new_volume = old_volume + trade.volume
                
                # 计算新的持仓均价
                if new_volume > 0:
                    position.price = ((old_volume * old_price) + (trade.volume * trade.price)) / new_volume
                
                position.volume = new_volume
                print(f"📈 开仓更新: {trade.symbol} {trade.direction.value} "
                      f"数量:{old_volume}→{new_volume}手 均价:{position.price:.2f}")
                
            elif trade.offset in [Offset.CLOSE, Offset.CLOSETODAY, Offset.CLOSEYESTERDAY]:
                # 平仓：减少持仓
                old_volume = position.volume
                position.volume = max(0, old_volume - trade.volume)
                
                # 计算平仓盈亏
                if trade.direction == Direction.LONG:
                    close_pnl = (trade.price - position.price) * trade.volume
                else:
                    close_pnl = (position.price - trade.price) * trade.volume
                
                position.pnl += close_pnl
                
                print(f"📉 平仓更新: {trade.symbol} {trade.direction.value} "
                      f"数量:{old_volume}→{position.volume}手 平仓盈亏:{close_pnl:.2f}")
                
                # 如果持仓为0，删除持仓记录
                if position.volume == 0:
                    del self.positions[position_key]
                    print(f"🔄 持仓清零，移除记录: {trade.symbol} {trade.direction.value}")
    
    def get_position(self, symbol: str, direction: Direction) -> Optional[PositionData]:
        """获取指定持仓"""
        position_key = self._get_position_key(symbol, direction)
        with self.lock:
            return self.positions.get(position_key)
    
    def get_all_positions(self) -> List[PositionData]:
        """获取所有持仓"""
        with self.lock:
            return list(self.positions.values())
    
    def get_symbol_positions(self, symbol: str) -> List[PositionData]:
        """获取指定合约的所有持仓"""
        with self.lock:
            return [pos for pos in self.positions.values() if pos.symbol == symbol]
    
    def calculate_total_pnl(self) -> float:
        """计算总持仓盈亏"""
        with self.lock:
            return sum(pos.pnl for pos in self.positions.values())


class TradeExecutor:
    """
    交易执行器
    负责将交易信号转换为具体订单并执行
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        """
        初始化交易执行器
        
        Args:
            connection_manager: 连接管理器
        """
        self.connection_manager = connection_manager
        self.simulation_mode = True                       # 模拟模式
        self.trade_callbacks: List[Callable] = []        # 成交回调
        self.lock = threading.Lock()
        
        # 模拟交易参数
        self.simulation_delay = 0.1                       # 模拟延迟(秒)
        self.simulation_slippage = 0.5                    # 模拟滑点
        
        print("✅ TradeExecutor初始化完成 (模拟模式)")
    
    def register_trade_callback(self, callback: Callable[[TradeData], None]) -> None:
        """注册成交回调"""
        with self.lock:
            self.trade_callbacks.append(callback)
            print(f"✅ 成交回调注册成功: {callback.__name__}")
    
    def execute_order(self, order: OrderData) -> bool:
        """
        执行订单
        
        Args:
            order: 订单对象
            
        Returns:
            bool: 是否执行成功
        """
        if self.simulation_mode:
            return self._simulate_order_execution(order)
        else:
            return self._real_order_execution(order)
    
    def _simulate_order_execution(self, order: OrderData) -> bool:
        """
        模拟订单执行
        
        Args:
            order: 订单对象
            
        Returns:
            bool: 是否执行成功
        """
        def simulate_execution():
            try:
                # 模拟网络延迟
                time.sleep(self.simulation_delay)
                
                # 模拟成交价格（添加滑点）
                if order.type == OrderType.MARKET:
                    # 市价单：使用当前价格+滑点
                    execution_price = order.price + self.simulation_slippage
                else:
                    # 限价单：使用委托价格
                    execution_price = order.price
                
                # 创建成交记录
                trade = TradeData(
                    tradeid=f"TRADE_{order.orderid}_{int(time.time())}",
                    orderid=order.orderid,
                    symbol=order.symbol,
                    exchange=order.exchange,
                    direction=order.direction,
                    volume=order.volume,
                    price=execution_price,
                    datetime=datetime.now(),
                    offset=order.offset,
                    gateway_name=order.gateway_name
                )
                
                # 通知成交回调
                with self.lock:
                    for callback in self.trade_callbacks:
                        try:
                            callback(trade)
                        except Exception as e:
                            print(f"❌ 成交回调执行失败: {e}")
                
                print(f"🎯 模拟成交: {trade.tradeid} {trade.symbol} "
                      f"{trade.direction.value} {trade.volume}手@{trade.price:.2f}")
                
                return True
                
            except Exception as e:
                print(f"❌ 模拟执行失败: {e}")
                return False
        
        # 启动异步执行线程
        execution_thread = threading.Thread(target=simulate_execution)
        execution_thread.daemon = True
        execution_thread.start()
        
        return True
    
    def _real_order_execution(self, order: OrderData) -> bool:
        """
        真实订单执行（预留接口）
        
        Args:
            order: 订单对象
            
        Returns:
            bool: 是否执行成功
        """
        # TODO: 实现真实的CTP订单发送
        print("🚧 真实交易模式暂未实现")
        return False


class TradingEngine:
    """
    交易引擎主类
    集成订单管理、持仓管理和交易执行功能
    """
    
    def __init__(self, connection_manager: ConnectionManager, config: dict = None):
        """
        初始化交易引擎
        
        Args:
            connection_manager: 连接管理器
            config: 配置参数
        """
        self.connection_manager = connection_manager
        self.config = config or {}
        
        # 初始化子模块
        self.order_manager = OrderManager()
        self.position_manager = PositionManager()
        self.trade_executor = TradeExecutor(connection_manager)
        
        # 账户信息
        self.account_data: Optional[AccountData] = None
        
        # 回调函数
        self.order_callbacks: List[Callable] = []
        self.trade_callbacks: List[Callable] = []
        
        # 注册内部回调
        self.trade_executor.register_trade_callback(self._on_trade)
        
        self.lock = threading.Lock()
        print("🚀 TradingEngine初始化完成")
    
    def _on_trade(self, trade: TradeData) -> None:
        """内部成交回调处理"""
        # 更新订单状态
        self.order_manager.update_order_traded(trade.orderid, trade.volume)
        
        # 更新持仓
        self.position_manager.update_position(trade)
        
        # 通知外部回调
        with self.lock:
            for callback in self.trade_callbacks:
                try:
                    callback(trade)
                except Exception as e:
                    print(f"❌ 交易回调执行失败: {e}")
    
    def send_order(self, signal: TradingSignal) -> TradingResult:
        """
        发送交易订单
        
        Args:
            signal: 交易信号
            
        Returns:
            TradingResult: 交易结果
        """
        try:
            # 将交易信号转换为订单请求
            request = self._signal_to_order_request(signal)
            if not request:
                return TradingResult(
                    success=False,
                    message="无法转换交易信号为订单请求",
                    timestamp=datetime.now()
                )
            
            # 创建订单
            order = self.order_manager.create_order(request)
            
            # 执行订单
            success = self.trade_executor.execute_order(order)
            
            if success:
                # 更新订单状态为已提交
                self.order_manager.update_order_status(order.orderid, OrderStatus.NOTTRADED)
                
                return TradingResult(
                    success=True,
                    orderid=order.orderid,
                    message="订单发送成功",
                    timestamp=datetime.now()
                )
            else:
                # 更新订单状态为拒绝
                self.order_manager.update_order_status(order.orderid, OrderStatus.REJECTED)
                
                return TradingResult(
                    success=False,
                    orderid=order.orderid,
                    message="订单执行失败",
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            return TradingResult(
                success=False,
                message=f"发送订单异常: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _signal_to_order_request(self, signal: TradingSignal) -> Optional[OrderRequest]:
        """
        将交易信号转换为订单请求
        
        Args:
            signal: 交易信号
            
        Returns:
            OrderRequest: 订单请求（失败时返回None）
        """
        try:
            # 解析交易动作
            if signal.action == TradingSignalAction.OPEN_LONG:
                direction = Direction.LONG
                offset = Offset.OPEN
            elif signal.action == TradingSignalAction.OPEN_SHORT:
                direction = Direction.SHORT
                offset = Offset.OPEN
            elif signal.action == TradingSignalAction.CLOSE_LONG:
                direction = Direction.SHORT  # 平多头需要卖出
                offset = Offset.CLOSE
            elif signal.action == TradingSignalAction.CLOSE_SHORT:
                direction = Direction.LONG   # 平空头需要买入
                offset = Offset.CLOSE
            else:
                print(f"❌ 未知的交易动作: {signal.action}")
                return None
            
            # 确定订单类型
            order_type = OrderType.MARKET if signal.price == 0.0 else OrderType.LIMIT
            
            # 创建订单请求
            request = OrderRequest(
                symbol=signal.symbol,
                exchange=Exchange.SHFE,  # 默认使用SHFE，实际应从合约信息获取
                direction=direction,
                type=order_type,
                volume=signal.volume,
                price=signal.price if signal.price > 0 else 3500.0,  # 默认价格用于市价单
                offset=offset,
                reference=f"Strategy:{signal.strategy}",
                gateway_name=self.connection_manager.gateway_name
            )
            
            return request
            
        except Exception as e:
            print(f"❌ 信号转换失败: {e}")
            return None
    
    def cancel_order(self, orderid: str) -> TradingResult:
        """取消订单"""
        success = self.order_manager.cancel_order(orderid)
        
        return TradingResult(
            success=success,
            orderid=orderid,
            message="订单取消成功" if success else "订单取消失败",
            timestamp=datetime.now()
        )
    
    def get_order(self, orderid: str) -> Optional[OrderData]:
        """获取订单信息"""
        return self.order_manager.get_order(orderid)
    
    def get_position(self, symbol: str, direction: Direction = None) -> List[PositionData]:
        """获取持仓信息"""
        if direction:
            position = self.position_manager.get_position(symbol, direction)
            return [position] if position else []
        else:
            return self.position_manager.get_symbol_positions(symbol)
    
    def get_all_positions(self) -> List[PositionData]:
        """获取所有持仓"""
        return self.position_manager.get_all_positions()
    
    def get_active_orders(self, symbol: str = None) -> List[OrderData]:
        """获取活跃订单"""
        return self.order_manager.get_active_orders(symbol)
    
    def register_order_callback(self, callback: Callable[[OrderData], None]) -> None:
        """注册订单回调"""
        with self.lock:
            self.order_callbacks.append(callback)
            print(f"✅ 订单回调注册成功: {callback.__name__}")
    
    def register_trade_callback(self, callback: Callable[[TradeData], None]) -> None:
        """注册成交回调"""
        with self.lock:
            self.trade_callbacks.append(callback)
            print(f"✅ 交易回调注册成功: {callback.__name__}")
    
    def get_account_info(self) -> Optional[AccountData]:
        """获取账户信息"""
        # TODO: 实现账户信息获取
        if not self.account_data:
            # 创建模拟账户数据
            self.account_data = AccountData(
                accountid="SIM_ACCOUNT_001",
                balance=1000000.0,      # 100万初始资金
                frozen=0.0,
                available=1000000.0,
                gateway_name=self.connection_manager.gateway_name
            )
        return self.account_data
    
    def is_ready(self) -> bool:
        """检查交易引擎是否就绪"""
        return self.connection_manager.is_connected()
    
    def get_status(self) -> Dict[str, Any]:
        """获取交易引擎状态"""
        return {
            "ready": self.is_ready(),
            "connection_status": self.connection_manager.get_connection_status(),
            "active_orders_count": len(self.order_manager.orders),
            "positions_count": len(self.position_manager.positions),
            "account_balance": self.account_data.balance if self.account_data else 0.0
        }


def create_sample_trading_signal(symbol: str = "rb2310", 
                               action: TradingSignalAction = TradingSignalAction.OPEN_LONG,
                               volume: int = 1) -> TradingSignal:
    """
    创建示例交易信号
    
    Args:
        symbol: 合约代码
        action: 交易动作
        volume: 交易数量
        
    Returns:
        TradingSignal: 交易信号
    """
    return TradingSignal(
        symbol=symbol,
        action=action,
        volume=volume,
        price=0.0,  # 市价单
        timestamp=datetime.now(),
        strategy="sample_strategy",
        reason="示例交易信号"
    )