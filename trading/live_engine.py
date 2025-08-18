"""
实盘交易引擎
模拟实盘交易环境
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from loguru import logger

from .order_manager import OrderManager, OrderDirection, OrderType
from data.data_manager import DataManager
from config.settings import GATEWAY_CONFIG, RISK_CONFIG


class Account:
    """账户信息"""
    
    def __init__(self, initial_balance: float = 100000):
        self.balance = initial_balance  # 账户余额
        self.available = initial_balance  # 可用资金
        self.frozen = 0.0  # 冻结资金
        self.pnl = 0.0  # 当日盈亏
        self.total_pnl = 0.0  # 总盈亏
        
    def freeze_balance(self, amount: float) -> bool:
        """冻结资金"""
        if self.available >= amount:
            self.available -= amount
            self.frozen += amount
            return True
        return False
    
    def unfreeze_balance(self, amount: float):
        """解冻资金"""
        unfreeze_amount = min(amount, self.frozen)
        self.frozen -= unfreeze_amount
        self.available += unfreeze_amount
    
    def update_balance(self, amount: float):
        """更新余额"""
        self.balance += amount
        self.available += amount
        self.total_pnl += amount
        self.pnl += amount


class Position:
    """持仓信息"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.size = 0.0  # 持仓数量
        self.avg_price = 0.0  # 平均成本价
        self.market_value = 0.0  # 市值
        self.pnl = 0.0  # 浮动盈亏
        self.realized_pnl = 0.0  # 已实现盈亏
        
    @property
    def is_long(self) -> bool:
        return self.size > 0
    
    @property
    def is_short(self) -> bool:
        return self.size < 0
    
    @property
    def is_empty(self) -> bool:
        return abs(self.size) < 1e-6
    
    def update_position(self, trade_volume: float, trade_price: float):
        """更新持仓"""
        if self.is_empty:
            # 开仓
            self.size = trade_volume
            self.avg_price = trade_price
        else:
            # 加仓或平仓
            if (self.size > 0 and trade_volume > 0) or (self.size < 0 and trade_volume < 0):
                # 加仓
                total_cost = abs(self.size) * self.avg_price + abs(trade_volume) * trade_price
                self.size += trade_volume
                if abs(self.size) > 1e-6:
                    self.avg_price = total_cost / abs(self.size)
            else:
                # 平仓
                close_volume = min(abs(trade_volume), abs(self.size))
                # 计算平仓盈亏
                if self.size > 0:  # 平多仓
                    self.realized_pnl += close_volume * (trade_price - self.avg_price)
                else:  # 平空仓
                    self.realized_pnl += close_volume * (self.avg_price - trade_price)
                
                # 更新持仓
                if abs(trade_volume) >= abs(self.size):
                    # 完全平仓
                    remaining_volume = abs(trade_volume) - abs(self.size)
                    self.size = remaining_volume if trade_volume > 0 else -remaining_volume
                    if abs(self.size) > 1e-6:
                        self.avg_price = trade_price
                    else:
                        self.size = 0
                        self.avg_price = 0
                else:
                    # 部分平仓
                    self.size += trade_volume
    
    def update_market_value(self, current_price: float):
        """更新市值和浮动盈亏"""
        if not self.is_empty:
            self.market_value = abs(self.size) * current_price
            if self.size > 0:
                self.pnl = self.size * (current_price - self.avg_price)
            else:
                self.pnl = -self.size * (self.avg_price - current_price)
        else:
            self.market_value = 0
            self.pnl = 0


class LiveEngine:
    """实盘交易引擎（模拟）"""
    
    def __init__(self, initial_balance: float = 100000):
        self.account = Account(initial_balance)
        self.order_manager = OrderManager()
        self.data_manager = DataManager()
        
        # 持仓管理
        self.positions: Dict[str, Position] = {}
        
        # 策略管理
        self.strategies: Dict[str, Any] = {}
        
        # 引擎状态
        self.is_running = False
        self.is_trading = True
        
        # 价格订阅
        self.subscribed_symbols: Dict[str, float] = {}  # symbol -> last_price
        self.price_update_thread = None
        
        logger.info(f"实盘交易引擎初始化完成，初始资金: {initial_balance}")
    
    def add_strategy(self, strategy) -> bool:
        """添加策略"""
        if strategy.name in self.strategies:
            logger.warning(f"策略已存在: {strategy.name}")
            return False
        
        self.strategies[strategy.name] = strategy
        
        # 订阅策略品种的价格
        self.subscribe_symbol(strategy.symbol)
        
        logger.info(f"添加策略: {strategy.name}")
        return True
    
    def subscribe_symbol(self, symbol: str):
        """订阅品种价格"""
        if symbol not in self.subscribed_symbols:
            self.subscribed_symbols[symbol] = 0.0
            # 获取初始价格
            try:
                ticker = self.data_manager.get_latest_price(symbol)
                if ticker:
                    self.subscribed_symbols[symbol] = ticker.get('price', 0)
                    logger.info(f"订阅品种价格: {symbol} @ {self.subscribed_symbols[symbol]}")
            except Exception as e:
                logger.warning(f"获取{symbol}初始价格失败: {e}")
    
    def start_engine(self):
        """启动交易引擎"""
        if self.is_running:
            logger.warning("交易引擎已在运行")
            return
        
        self.is_running = True
        
        # 启动价格更新线程
        self.price_update_thread = threading.Thread(target=self._price_update_loop, daemon=True)
        self.price_update_thread.start()
        
        logger.info("实盘交易引擎已启动")
    
    def stop_engine(self):
        """停止交易引擎"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.is_trading = False
        
        # 取消所有活跃订单
        self.order_manager.cancel_all_orders()
        
        logger.info("实盘交易引擎已停止")
    
    def _price_update_loop(self):
        """价格更新循环"""
        while self.is_running:
            try:
                for symbol in list(self.subscribed_symbols.keys()):
                    # 模拟价格更新（实际应该从实时数据源获取）
                    current_price = self.subscribed_symbols[symbol]
                    if current_price > 0:
                        # 简单的价格波动模拟
                        import random
                        change_percent = random.uniform(-0.001, 0.001)  # ±0.1%的随机波动
                        new_price = current_price * (1 + change_percent)
                        self.subscribed_symbols[symbol] = new_price
                        
                        # 更新持仓市值
                        self._update_positions_pnl(symbol, new_price)
                        
                        # 处理订单成交
                        self._process_orders(symbol, new_price)
                
                time.sleep(1)  # 每秒更新一次
                
            except Exception as e:
                logger.error(f"价格更新循环错误: {e}")
                time.sleep(5)
    
    def _update_positions_pnl(self, symbol: str, current_price: float):
        """更新持仓盈亏"""
        if symbol in self.positions:
            self.positions[symbol].update_market_value(current_price)
    
    def _process_orders(self, symbol: str, current_price: float):
        """处理订单成交"""
        if not self.is_trading:
            return
        
        active_orders = self.order_manager.get_active_orders(symbol)
        
        for order in active_orders:
            # 简化的成交逻辑
            should_fill = False
            fill_price = current_price
            
            if order.order_type == OrderType.MARKET:
                # 市价单立即成交
                should_fill = True
                fill_price = current_price
            elif order.order_type == OrderType.LIMIT:
                # 限价单检查价格条件
                if order.direction == OrderDirection.BUY and current_price <= order.price:
                    should_fill = True
                    fill_price = order.price
                elif order.direction == OrderDirection.SELL and current_price >= order.price:
                    should_fill = True
                    fill_price = order.price
            
            if should_fill:
                # 执行成交
                trade = self.order_manager.fill_order(order.order_id, order.volume, fill_price)
                if trade:
                    self._process_trade(trade)
    
    def _process_trade(self, trade):
        """处理成交"""
        symbol = trade.symbol
        
        # 确保持仓对象存在
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        
        # 更新持仓
        trade_volume = trade.volume if trade.direction == OrderDirection.BUY else -trade.volume
        self.positions[symbol].update_position(trade_volume, trade.price)
        
        # 更新账户资金
        trade_value = trade.volume * trade.price
        if trade.direction == OrderDirection.BUY:
            # 买入：减少资金，增加持仓
            self.account.unfreeze_balance(trade_value + trade.commission)
            self.account.update_balance(-(trade_value + trade.commission))
        else:
            # 卖出：增加资金，减少持仓
            trade_pnl = self.positions[symbol].realized_pnl
            self.account.update_balance(trade_value - trade.commission + trade_pnl)
        
        logger.info(f"处理成交: {trade.symbol} {trade.direction.value} {trade.volume}@{trade.price}")
    
    def place_order(self, symbol: str, direction: str, volume: float, 
                   price: float = 0, order_type: str = "MARKET", 
                   strategy_name: str = "") -> Optional[str]:
        """下单"""
        if not self.is_trading:
            logger.warning("交易已暂停，无法下单")
            return None
        
        # 风险检查
        if direction.upper() == "BUY":
            required_margin = volume * (price if price > 0 else self.subscribed_symbols.get(symbol, 0))
            if not self.account.freeze_balance(required_margin):
                logger.warning(f"资金不足，无法买入 {symbol}")
                return None
        
        # 创建订单
        order = self.order_manager.create_order(
            symbol, direction, volume, price, order_type, strategy_name
        )
        
        # 提交订单
        if self.order_manager.submit_order(order.order_id):
            logger.info(f"下单成功: {order.order_id}")
            return order.order_id
        else:
            logger.error(f"订单提交失败: {order.order_id}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        return self.order_manager.cancel_order(order_id)
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        # 计算总市值
        total_market_value = sum(pos.market_value for pos in self.positions.values())
        # 计算总浮动盈亏
        total_unrealized_pnl = sum(pos.pnl for pos in self.positions.values())
        # 计算总已实现盈亏
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        
        return {
            'balance': self.account.balance,
            'available': self.account.available,
            'frozen': self.account.frozen,
            'market_value': total_market_value,
            'total_equity': self.account.balance + total_unrealized_pnl,
            'pnl_today': self.account.pnl,
            'total_pnl': total_realized_pnl + total_unrealized_pnl,
            'unrealized_pnl': total_unrealized_pnl,
            'realized_pnl': total_realized_pnl
        }
    
    def get_positions(self) -> Dict[str, Dict]:
        """获取持仓信息"""
        return {
            symbol: {
                'symbol': pos.symbol,
                'size': pos.size,
                'avg_price': pos.avg_price,
                'market_value': pos.market_value,
                'pnl': pos.pnl,
                'realized_pnl': pos.realized_pnl,
                'is_long': pos.is_long,
                'is_short': pos.is_short
            }
            for symbol, pos in self.positions.items()
            if not pos.is_empty
        }
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            'is_running': self.is_running,
            'is_trading': self.is_trading,
            'strategies_count': len(self.strategies),
            'subscribed_symbols': list(self.subscribed_symbols.keys()),
            'current_prices': self.subscribed_symbols.copy(),
            'order_stats': self.order_manager.get_statistics(),
            'account_info': self.get_account_info()
        }
    
    def close(self):
        """关闭引擎"""
        self.stop_engine()
        self.data_manager.close()
        logger.info("实盘交易引擎已关闭")