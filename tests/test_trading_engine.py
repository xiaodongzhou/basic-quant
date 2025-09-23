#!/usr/bin/env python3
"""
TradingEngine模块单元测试
测试订单管理、持仓管理和交易执行功能

Milestone 2.1 测试套件
"""

import unittest
import threading
import time
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.trading_engine import (
    TradingEngine, OrderManager, PositionManager, TradeExecutor,
    create_sample_trading_signal
)
from core.connection_manager import ConnectionManager
from core.data_types import (
    TradingSignal, TradingSignalAction, OrderRequest, OrderData, TradeData, 
    PositionData, Direction, OrderType, OrderStatus, Offset, Exchange
)


class TestOrderManager(unittest.TestCase):
    """订单管理器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.order_manager = OrderManager()
    
    def test_order_creation(self):
        """测试订单创建"""
        request = OrderRequest(
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=1,
            price=3500.0,
            offset=Offset.OPEN
        )
        
        order = self.order_manager.create_order(request)
        
        self.assertIsNotNone(order)
        self.assertIsInstance(order.orderid, str)
        self.assertEqual(order.symbol, "rb2310")
        self.assertEqual(order.direction, Direction.LONG)
        self.assertEqual(order.volume, 1)
        self.assertEqual(order.price, 3500.0)
        self.assertEqual(order.status, OrderStatus.SUBMITTING)
        self.assertEqual(order.traded, 0)
        
        # 检查订单是否存储
        stored_order = self.order_manager.get_order(order.orderid)
        self.assertIsNotNone(stored_order)
        self.assertEqual(stored_order.orderid, order.orderid)
    
    def test_order_id_generation(self):
        """测试订单ID生成唯一性"""
        order_ids = set()
        
        # 生成多个订单ID
        for _ in range(100):
            order_id = self.order_manager.generate_order_id()
            self.assertNotIn(order_id, order_ids)
            order_ids.add(order_id)
        
        self.assertEqual(len(order_ids), 100)
    
    def test_order_status_update(self):
        """测试订单状态更新"""
        request = OrderRequest(
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=1,
            price=3500.0
        )
        
        order = self.order_manager.create_order(request)
        order_id = order.orderid
        
        # 更新状态为未成交
        success = self.order_manager.update_order_status(order_id, OrderStatus.NOTTRADED)
        self.assertTrue(success)
        
        updated_order = self.order_manager.get_order(order_id)
        self.assertEqual(updated_order.status, OrderStatus.NOTTRADED)
        
        # 更新状态为全部成交（应移至历史）
        success = self.order_manager.update_order_status(order_id, OrderStatus.ALLTRADED)
        self.assertTrue(success)
        
        # 检查活跃订单中不存在
        active_orders = self.order_manager.get_active_orders()
        active_order_ids = [o.orderid for o in active_orders]
        self.assertNotIn(order_id, active_order_ids)
        
        # 但历史中应该存在
        historical_order = self.order_manager.get_order(order_id)
        self.assertIsNotNone(historical_order)
        self.assertEqual(historical_order.status, OrderStatus.ALLTRADED)
    
    def test_order_traded_update(self):
        """测试订单成交数量更新"""
        request = OrderRequest(
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=10,
            price=3500.0
        )
        
        order = self.order_manager.create_order(request)
        order_id = order.orderid
        
        # 部分成交
        success = self.order_manager.update_order_traded(order_id, 3)
        self.assertTrue(success)
        
        updated_order = self.order_manager.get_order(order_id)
        self.assertEqual(updated_order.traded, 3)
        self.assertEqual(updated_order.status, OrderStatus.PARTTRADED)
        
        # 继续成交至全部成交
        success = self.order_manager.update_order_traded(order_id, 7)
        self.assertTrue(success)
        
        # 订单应移至历史
        final_order = self.order_manager.get_order(order_id)
        self.assertEqual(final_order.traded, 10)
        self.assertEqual(final_order.status, OrderStatus.ALLTRADED)
    
    def test_cancel_order(self):
        """测试订单取消"""
        request = OrderRequest(
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=1,
            price=3500.0
        )
        
        order = self.order_manager.create_order(request)
        order_id = order.orderid
        
        # 设置为未成交状态
        self.order_manager.update_order_status(order_id, OrderStatus.NOTTRADED)
        
        # 取消订单
        success = self.order_manager.cancel_order(order_id)
        self.assertTrue(success)
        
        # 检查状态
        cancelled_order = self.order_manager.get_order(order_id)
        self.assertEqual(cancelled_order.status, OrderStatus.CANCELLED)


class TestPositionManager(unittest.TestCase):
    """持仓管理器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.position_manager = PositionManager()
    
    def test_open_position(self):
        """测试开仓"""
        trade = TradeData(
            tradeid="TRADE_001",
            orderid="ORDER_001",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            volume=2,
            price=3500.0,
            datetime=datetime.now(),
            offset=Offset.OPEN
        )
        
        self.position_manager.update_position(trade)
        
        position = self.position_manager.get_position("rb2310", Direction.LONG)
        self.assertIsNotNone(position)
        self.assertEqual(position.volume, 2)
        self.assertEqual(position.price, 3500.0)
        self.assertEqual(position.direction, Direction.LONG)
    
    def test_multiple_open_positions(self):
        """测试多次开仓"""
        # 第一次开仓
        trade1 = TradeData(
            tradeid="TRADE_001",
            orderid="ORDER_001",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            volume=2,
            price=3500.0,
            datetime=datetime.now(),
            offset=Offset.OPEN
        )
        
        self.position_manager.update_position(trade1)
        
        # 第二次开仓
        trade2 = TradeData(
            tradeid="TRADE_002",
            orderid="ORDER_002",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            volume=3,
            price=3600.0,
            datetime=datetime.now(),
            offset=Offset.OPEN
        )
        
        self.position_manager.update_position(trade2)
        
        position = self.position_manager.get_position("rb2310", Direction.LONG)
        self.assertIsNotNone(position)
        self.assertEqual(position.volume, 5)  # 2 + 3
        
        # 计算期望均价: (2 * 3500 + 3 * 3600) / 5 = 3560
        expected_price = (2 * 3500.0 + 3 * 3600.0) / 5
        self.assertAlmostEqual(position.price, expected_price, places=2)
    
    def test_close_position(self):
        """测试平仓"""
        # 先开仓
        open_trade = TradeData(
            tradeid="TRADE_OPEN",
            orderid="ORDER_OPEN",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            volume=5,
            price=3500.0,
            datetime=datetime.now(),
            offset=Offset.OPEN
        )
        
        self.position_manager.update_position(open_trade)
        
        # 部分平仓
        close_trade = TradeData(
            tradeid="TRADE_CLOSE",
            orderid="ORDER_CLOSE",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,  # 平多头仍然是LONG方向的持仓
            volume=2,
            price=3600.0,
            datetime=datetime.now(),
            offset=Offset.CLOSE
        )
        
        self.position_manager.update_position(close_trade)
        
        position = self.position_manager.get_position("rb2310", Direction.LONG)
        self.assertIsNotNone(position)
        self.assertEqual(position.volume, 3)  # 5 - 2
        
        # 检查平仓盈亏: (3600 - 3500) * 2 = 200
        expected_pnl = (3600.0 - 3500.0) * 2
        self.assertAlmostEqual(position.pnl, expected_pnl, places=2)
    
    def test_close_all_position(self):
        """测试全部平仓"""
        # 开仓
        open_trade = TradeData(
            tradeid="TRADE_OPEN",
            orderid="ORDER_OPEN",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            volume=3,
            price=3500.0,
            datetime=datetime.now(),
            offset=Offset.OPEN
        )
        
        self.position_manager.update_position(open_trade)
        
        # 全部平仓
        close_trade = TradeData(
            tradeid="TRADE_CLOSE_ALL",
            orderid="ORDER_CLOSE_ALL",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            volume=3,
            price=3600.0,
            datetime=datetime.now(),
            offset=Offset.CLOSE
        )
        
        self.position_manager.update_position(close_trade)
        
        # 持仓应该被删除
        position = self.position_manager.get_position("rb2310", Direction.LONG)
        self.assertIsNone(position)
        
        # 检查总盈亏
        total_pnl = self.position_manager.calculate_total_pnl()
        expected_pnl = (3600.0 - 3500.0) * 3  # 300
        self.assertAlmostEqual(total_pnl, expected_pnl, places=2)
    
    def test_multiple_symbols_positions(self):
        """测试多品种持仓"""
        # 螺纹钢多头
        trade_rb = TradeData(
            tradeid="TRADE_RB",
            orderid="ORDER_RB",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            volume=2,
            price=3500.0,
            datetime=datetime.now(),
            offset=Offset.OPEN
        )
        
        # 铁矿石空头
        trade_i = TradeData(
            tradeid="TRADE_I",
            orderid="ORDER_I",
            symbol="i2310",
            exchange=Exchange.DCE,
            direction=Direction.SHORT,
            volume=3,
            price=800.0,
            datetime=datetime.now(),
            offset=Offset.OPEN
        )
        
        self.position_manager.update_position(trade_rb)
        self.position_manager.update_position(trade_i)
        
        # 检查持仓
        all_positions = self.position_manager.get_all_positions()
        self.assertEqual(len(all_positions), 2)
        
        rb_position = self.position_manager.get_position("rb2310", Direction.LONG)
        i_position = self.position_manager.get_position("i2310", Direction.SHORT)
        
        self.assertIsNotNone(rb_position)
        self.assertIsNotNone(i_position)
        self.assertEqual(rb_position.volume, 2)
        self.assertEqual(i_position.volume, 3)


class TestTradeExecutor(unittest.TestCase):
    """交易执行器测试"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建模拟连接管理器
        with open('/home/user/webapp/system_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.connection_manager = ConnectionManager(config)
        self.trade_executor = TradeExecutor(self.connection_manager)
        
        # 用于收集回调数据
        self.received_trades = []
    
    def trade_callback(self, trade: TradeData):
        """测试回调函数"""
        self.received_trades.append(trade)
    
    def test_trade_callback_registration(self):
        """测试成交回调注册"""
        self.trade_executor.register_trade_callback(self.trade_callback)
        
        # 检查回调是否注册成功
        self.assertEqual(len(self.trade_executor.trade_callbacks), 1)
    
    def test_simulation_execution(self):
        """测试模拟执行"""
        self.trade_executor.register_trade_callback(self.trade_callback)
        
        # 创建测试订单
        order = OrderData(
            orderid="TEST_ORDER_001",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            type=OrderType.MARKET,
            volume=1,
            traded=0,
            status=OrderStatus.SUBMITTING,
            datetime=datetime.now(),
            price=3500.0,
            offset=Offset.OPEN
        )
        
        # 执行订单
        success = self.trade_executor.execute_order(order)
        self.assertTrue(success)
        
        # 等待模拟执行完成
        time.sleep(0.5)
        
        # 检查是否有成交回调
        self.assertGreater(len(self.received_trades), 0)
        
        trade = self.received_trades[0]
        self.assertEqual(trade.orderid, "TEST_ORDER_001")
        self.assertEqual(trade.symbol, "rb2310")
        self.assertEqual(trade.direction, Direction.LONG)
        self.assertEqual(trade.volume, 1)
        self.assertGreater(trade.price, 0)


class TestTradingEngine(unittest.TestCase):
    """交易引擎集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        # 加载配置
        with open('/home/user/webapp/system_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.connection_manager = ConnectionManager(config)
        self.trading_engine = TradingEngine(self.connection_manager, config)
        
        # 连接管理器
        self.connection_manager.connect_gateway()
        
        # 用于收集回调数据
        self.received_trades = []
        self.received_orders = []
    
    def trade_callback(self, trade: TradeData):
        """交易回调"""
        self.received_trades.append(trade)
    
    def order_callback(self, order: OrderData):
        """订单回调"""
        self.received_orders.append(order)
    
    def test_trading_engine_initialization(self):
        """测试交易引擎初始化"""
        self.assertIsNotNone(self.trading_engine.order_manager)
        self.assertIsNotNone(self.trading_engine.position_manager)
        self.assertIsNotNone(self.trading_engine.trade_executor)
        self.assertIsNotNone(self.trading_engine.connection_manager)
    
    def test_send_long_signal(self):
        """测试发送开多信号"""
        # 注册回调
        self.trading_engine.register_trade_callback(self.trade_callback)
        
        # 创建开多信号
        signal = TradingSignal(
            symbol="rb2310",
            action=TradingSignalAction.OPEN_LONG,
            volume=1,
            price=0.0,  # 市价
            timestamp=datetime.now(),
            strategy="test_strategy",
            reason="测试开多"
        )
        
        # 发送订单
        result = self.trading_engine.send_order(signal)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.orderid)
        self.assertEqual(result.message, "订单发送成功")
        
        # 等待执行
        time.sleep(0.5)
        
        # 检查订单
        order = self.trading_engine.get_order(result.orderid)
        self.assertIsNotNone(order)
        self.assertEqual(order.symbol, "rb2310")
        self.assertEqual(order.direction, Direction.LONG)
        
        # 检查成交
        self.assertGreater(len(self.received_trades), 0)
        trade = self.received_trades[0]
        self.assertEqual(trade.orderid, result.orderid)
    
    def test_send_short_signal(self):
        """测试发送开空信号"""
        self.trading_engine.register_trade_callback(self.trade_callback)
        
        signal = TradingSignal(
            symbol="rb2310",
            action=TradingSignalAction.OPEN_SHORT,
            volume=2,
            price=3600.0,  # 限价
            timestamp=datetime.now(),
            strategy="test_strategy",
            reason="测试开空"
        )
        
        result = self.trading_engine.send_order(signal)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.orderid)
        
        # 等待执行
        time.sleep(0.5)
        
        # 检查订单
        order = self.trading_engine.get_order(result.orderid)
        self.assertEqual(order.direction, Direction.SHORT)
        self.assertEqual(order.volume, 2)
        self.assertEqual(order.type, OrderType.LIMIT)
    
    def test_complete_trading_workflow(self):
        """测试完整的交易流程"""
        self.trading_engine.register_trade_callback(self.trade_callback)
        
        # Step 1: 开多头
        open_signal = TradingSignal(
            symbol="rb2310",
            action=TradingSignalAction.OPEN_LONG,
            volume=3,
            price=0.0,
            timestamp=datetime.now(),
            strategy="test_workflow",
            reason="测试开仓"
        )
        
        open_result = self.trading_engine.send_order(open_signal)
        self.assertTrue(open_result.success)
        
        # 等待开仓成交
        time.sleep(0.5)
        
        # 检查持仓
        positions = self.trading_engine.get_position("rb2310", Direction.LONG)
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].volume, 3)
        
        # Step 2: 部分平仓
        close_signal = TradingSignal(
            symbol="rb2310",
            action=TradingSignalAction.CLOSE_LONG,
            volume=1,
            price=0.0,
            timestamp=datetime.now(),
            strategy="test_workflow",
            reason="测试平仓"
        )
        
        close_result = self.trading_engine.send_order(close_signal)
        self.assertTrue(close_result.success)
        
        # 等待平仓成交
        time.sleep(0.5)
        
        # 检查持仓
        positions = self.trading_engine.get_position("rb2310", Direction.LONG)
        self.assertEqual(positions[0].volume, 2)  # 3 - 1 = 2
        
        # 检查成交记录
        self.assertEqual(len(self.received_trades), 2)  # 开仓 + 平仓
    
    def test_account_info(self):
        """测试账户信息"""
        account = self.trading_engine.get_account_info()
        
        self.assertIsNotNone(account)
        self.assertEqual(account.accountid, "SIM_ACCOUNT_001")
        self.assertEqual(account.balance, 1000000.0)
        self.assertEqual(account.available, 1000000.0)
    
    def test_engine_status(self):
        """测试引擎状态"""
        status = self.trading_engine.get_status()
        
        self.assertIn("ready", status)
        self.assertIn("connection_status", status)
        self.assertIn("active_orders_count", status)
        self.assertIn("positions_count", status)
        self.assertIn("account_balance", status)
    
    def test_invalid_signal(self):
        """测试无效信号处理"""
        # 创建无效的交易信号
        invalid_signal = TradingSignal(
            symbol="",  # 空符号
            action=TradingSignalAction.OPEN_LONG,
            volume=0,   # 无效数量
            timestamp=datetime.now(),
            strategy="test_invalid"
        )
        
        result = self.trading_engine.send_order(invalid_signal)
        
        # 应该处理失败但不崩溃
        self.assertFalse(result.success)
        self.assertIn("异常", result.message)


class TestSignalConversion(unittest.TestCase):
    """交易信号转换测试"""
    
    def test_sample_signal_creation(self):
        """测试示例信号创建"""
        signal = create_sample_trading_signal(
            symbol="rb2310",
            action=TradingSignalAction.OPEN_LONG,
            volume=2
        )
        
        self.assertEqual(signal.symbol, "rb2310")
        self.assertEqual(signal.action, TradingSignalAction.OPEN_LONG)
        self.assertEqual(signal.volume, 2)
        self.assertEqual(signal.price, 0.0)  # 市价
        self.assertEqual(signal.strategy, "sample_strategy")


def run_trading_engine_tests():
    """运行TradingEngine模块所有测试"""
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加OrderManager测试
    test_suite.addTest(TestOrderManager('test_order_creation'))
    test_suite.addTest(TestOrderManager('test_order_id_generation'))
    test_suite.addTest(TestOrderManager('test_order_status_update'))
    test_suite.addTest(TestOrderManager('test_order_traded_update'))
    test_suite.addTest(TestOrderManager('test_cancel_order'))
    
    # 添加PositionManager测试
    test_suite.addTest(TestPositionManager('test_open_position'))
    test_suite.addTest(TestPositionManager('test_multiple_open_positions'))
    test_suite.addTest(TestPositionManager('test_close_position'))
    test_suite.addTest(TestPositionManager('test_close_all_position'))
    test_suite.addTest(TestPositionManager('test_multiple_symbols_positions'))
    
    # 添加TradeExecutor测试
    test_suite.addTest(TestTradeExecutor('test_trade_callback_registration'))
    test_suite.addTest(TestTradeExecutor('test_simulation_execution'))
    
    # 添加TradingEngine集成测试
    test_suite.addTest(TestTradingEngine('test_trading_engine_initialization'))
    test_suite.addTest(TestTradingEngine('test_send_long_signal'))
    test_suite.addTest(TestTradingEngine('test_send_short_signal'))
    test_suite.addTest(TestTradingEngine('test_complete_trading_workflow'))
    test_suite.addTest(TestTradingEngine('test_account_info'))
    test_suite.addTest(TestTradingEngine('test_engine_status'))
    test_suite.addTest(TestTradingEngine('test_invalid_signal'))
    
    # 添加信号转换测试
    test_suite.addTest(TestSignalConversion('test_sample_signal_creation'))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result


if __name__ == '__main__':
    print("="*80)
    print("TradingEngine模块单元测试")
    print("Testing TradingEngine Module")
    print("="*80)
    
    # 更改工作目录到项目根目录
    import os
    os.chdir('/home/user/webapp')
    
    # 运行测试
    test_result = run_trading_engine_tests()
    
    print("\n" + "="*80)
    print("TradingEngine测试总结 (Test Summary)")
    print("="*80)
    print(f"总测试数: {test_result.testsRun}")
    print(f"成功: {test_result.testsRun - len(test_result.failures) - len(test_result.errors)}")
    print(f"失败: {len(test_result.failures)}")
    print(f"错误: {len(test_result.errors)}")
    
    if test_result.failures:
        print("\n失败的测试:")
        for failure in test_result.failures:
            print(f"- {failure[0]}")
    
    if test_result.errors:
        print("\n错误的测试:")
        for error in test_result.errors:
            print(f"- {error[0]}")
    
    success_rate = ((test_result.testsRun - len(test_result.failures) - len(test_result.errors)) / 
                   test_result.testsRun * 100) if test_result.testsRun > 0 else 0
    print(f"\n总体成功率: {success_rate:.1f}%")
    
    if success_rate >= 95.0:
        print("🎉 TradingEngine模块测试通过！")
    else:
        print("⚠️ 部分测试未通过，需要进一步调试")