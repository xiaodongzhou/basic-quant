"""
订单管理器
负责订单的创建、执行、跟踪和管理
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from loguru import logger


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"          # 待提交
    SUBMITTED = "SUBMITTED"      # 已提交
    PARTIAL_FILLED = "PARTIAL_FILLED"  # 部分成交
    FILLED = "FILLED"           # 完全成交
    CANCELLED = "CANCELLED"     # 已取消
    REJECTED = "REJECTED"       # 被拒绝


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"           # 市价单
    LIMIT = "LIMIT"             # 限价单
    STOP = "STOP"               # 止损单
    STOP_LIMIT = "STOP_LIMIT"   # 止损限价单


class OrderDirection(Enum):
    """订单方向"""
    BUY = "BUY"    # 买入
    SELL = "SELL"  # 卖出


class Order:
    """订单对象"""
    
    def __init__(self, symbol: str, direction: OrderDirection, volume: float, 
                 price: float = 0, order_type: OrderType = OrderType.MARKET,
                 strategy_name: str = ""):
        self.order_id = str(uuid.uuid4())[:8]  # 简短的订单ID
        self.symbol = symbol
        self.direction = direction
        self.volume = volume
        self.price = price
        self.order_type = order_type
        self.strategy_name = strategy_name
        self.status = OrderStatus.PENDING
        
        # 执行信息
        self.filled_volume = 0.0
        self.avg_price = 0.0
        self.commission = 0.0
        
        # 时间信息
        self.create_time = datetime.now()
        self.submit_time: Optional[datetime] = None
        self.fill_time: Optional[datetime] = None
        self.cancel_time: Optional[datetime] = None
        
        # 额外信息
        self.error_msg = ""
        
    @property
    def is_active(self) -> bool:
        """是否为活跃订单"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]
    
    @property
    def is_filled(self) -> bool:
        """是否完全成交"""
        return self.status == OrderStatus.FILLED
    
    @property
    def remaining_volume(self) -> float:
        """剩余数量"""
        return self.volume - self.filled_volume
    
    def update_fill(self, fill_volume: float, fill_price: float, commission: float = 0):
        """更新成交信息"""
        self.filled_volume += fill_volume
        self.commission += commission
        
        # 更新平均成交价
        if self.filled_volume > 0:
            total_turnover = self.avg_price * (self.filled_volume - fill_volume) + fill_price * fill_volume
            self.avg_price = total_turnover / self.filled_volume
        
        # 更新状态
        if abs(self.filled_volume - self.volume) < 1e-6:
            self.status = OrderStatus.FILLED
            self.fill_time = datetime.now()
        else:
            self.status = OrderStatus.PARTIAL_FILLED
    
    def cancel(self):
        """取消订单"""
        if self.is_active:
            self.status = OrderStatus.CANCELLED
            self.cancel_time = datetime.now()
    
    def reject(self, reason: str = ""):
        """拒绝订单"""
        self.status = OrderStatus.REJECTED
        self.error_msg = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'direction': self.direction.value,
            'volume': self.volume,
            'price': self.price,
            'order_type': self.order_type.value,
            'strategy_name': self.strategy_name,
            'status': self.status.value,
            'filled_volume': self.filled_volume,
            'avg_price': self.avg_price,
            'commission': self.commission,
            'create_time': self.create_time.isoformat(),
            'error_msg': self.error_msg
        }


class Trade:
    """成交记录"""
    
    def __init__(self, trade_id: str, order_id: str, symbol: str,
                 direction: OrderDirection, volume: float, price: float):
        self.trade_id = trade_id
        self.order_id = order_id
        self.symbol = symbol
        self.direction = direction
        self.volume = volume
        self.price = price
        self.trade_time = datetime.now()
        self.commission = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'trade_id': self.trade_id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'direction': self.direction.value,
            'volume': self.volume,
            'price': self.price,
            'commission': self.commission,
            'trade_time': self.trade_time.isoformat()
        }


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        
        # 统计信息
        self.total_orders = 0
        self.filled_orders = 0
        self.cancelled_orders = 0
        self.rejected_orders = 0
        
        logger.info("订单管理器初始化完成")
    
    def create_order(self, symbol: str, direction: str, volume: float, 
                    price: float = 0, order_type: str = "MARKET",
                    strategy_name: str = "") -> Order:
        """创建订单"""
        # 转换字符串为枚举
        direction_enum = OrderDirection.BUY if direction.upper() == "BUY" else OrderDirection.SELL
        type_enum = OrderType.MARKET if order_type.upper() == "MARKET" else OrderType.LIMIT
        
        order = Order(symbol, direction_enum, volume, price, type_enum, strategy_name)
        self.orders[order.order_id] = order
        self.total_orders += 1
        
        logger.info(f"创建订单: {order.order_id} {symbol} {direction} {volume}@{price}")
        return order
    
    def submit_order(self, order_id: str) -> bool:
        """提交订单"""
        order = self.orders.get(order_id)
        if not order:
            logger.error(f"订单不存在: {order_id}")
            return False
        
        if order.status != OrderStatus.PENDING:
            logger.warning(f"订单状态不正确: {order_id} {order.status}")
            return False
        
        order.status = OrderStatus.SUBMITTED
        order.submit_time = datetime.now()
        
        logger.info(f"提交订单: {order_id}")
        return True
    
    def fill_order(self, order_id: str, fill_volume: float, fill_price: float, 
                  commission_rate: float = 0.001) -> Optional[Trade]:
        """模拟订单成交"""
        order = self.orders.get(order_id)
        if not order:
            logger.error(f"订单不存在: {order_id}")
            return None
        
        if not order.is_active:
            logger.warning(f"订单不是活跃状态: {order_id}")
            return None
        
        # 计算手续费
        commission = fill_volume * fill_price * commission_rate
        
        # 更新订单
        order.update_fill(fill_volume, fill_price, commission)
        
        # 创建成交记录
        trade_id = f"trade_{len(self.trades) + 1}"
        trade = Trade(trade_id, order_id, order.symbol, order.direction, 
                     fill_volume, fill_price)
        trade.commission = commission
        self.trades.append(trade)
        
        if order.is_filled:
            self.filled_orders += 1
        
        logger.info(f"订单成交: {order_id} {fill_volume}@{fill_price}")
        return trade
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        order = self.orders.get(order_id)
        if not order:
            logger.error(f"订单不存在: {order_id}")
            return False
        
        if not order.is_active:
            logger.warning(f"订单无法取消: {order_id} {order.status}")
            return False
        
        order.cancel()
        self.cancelled_orders += 1
        
        logger.info(f"取消订单: {order_id}")
        return True
    
    def get_active_orders(self, symbol: str = None) -> List[Order]:
        """获取活跃订单"""
        active_orders = [order for order in self.orders.values() if order.is_active]
        
        if symbol:
            active_orders = [order for order in active_orders if order.symbol == symbol]
        
        return active_orders
    
    def get_order_history(self, symbol: str = None, strategy_name: str = None) -> List[Order]:
        """获取订单历史"""
        orders = list(self.orders.values())
        
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        
        if strategy_name:
            orders = [order for order in orders if order.strategy_name == strategy_name]
        
        # 按创建时间排序
        orders.sort(key=lambda x: x.create_time, reverse=True)
        return orders
    
    def get_trades(self, symbol: str = None) -> List[Trade]:
        """获取成交记录"""
        trades = self.trades
        
        if symbol:
            trades = [trade for trade in trades if trade.symbol == symbol]
        
        return trades
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        active_count = len([o for o in self.orders.values() if o.is_active])
        
        stats = {
            'total_orders': self.total_orders,
            'active_orders': active_count,
            'filled_orders': self.filled_orders,
            'cancelled_orders': self.cancelled_orders,
            'rejected_orders': self.rejected_orders,
            'total_trades': len(self.trades),
            'fill_rate': self.filled_orders / self.total_orders if self.total_orders > 0 else 0,
            'cancel_rate': self.cancelled_orders / self.total_orders if self.total_orders > 0 else 0
        }
        
        return stats
    
    def cancel_all_orders(self, symbol: str = None):
        """取消所有活跃订单"""
        active_orders = self.get_active_orders(symbol)
        
        for order in active_orders:
            self.cancel_order(order.order_id)
        
        logger.info(f"取消了{len(active_orders)}个活跃订单")
    
    def reset(self):
        """重置订单管理器"""
        self.cancel_all_orders()
        self.orders.clear()
        self.trades.clear()
        self.total_orders = 0
        self.filled_orders = 0
        self.cancelled_orders = 0
        self.rejected_orders = 0
        
        logger.info("订单管理器已重置")