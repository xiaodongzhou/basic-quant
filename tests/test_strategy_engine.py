#!/usr/bin/env python3
"""
StrategyEngine模块单元测试
测试策略加载、管理和事件分发功能

Milestone 2.2 测试套件
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

from core.strategy_engine import (
    StrategyEngine, StrategyManager, DataEventDispatcher, StrategyBase,
    StrategyConfig, StrategyStatus, StrategyEvent, MockStrategy,
    create_sample_strategy_config
)
from core.trading_engine import TradingEngine
from core.connection_manager import ConnectionManager
from core.market_data_manager import MarketDataManager
from core.data_types import (
    TickData, BarData, TradeData, TradingSignal, TradingSignalAction,
    Direction, Exchange, Interval
)


class TestStrategyBase(unittest.TestCase):
    """策略基类测试"""
    
    def setUp(self):
        """设置测试环境"""
        # 加载配置
        with open('/home/user/webapp/system_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.connection_manager = ConnectionManager(config)
        self.trading_engine = TradingEngine(self.connection_manager, config)
        
        # 创建策略配置
        self.strategy_config = create_sample_strategy_config("test_strategy", ["rb2310"])
        
        # 创建策略实例
        self.strategy = MockStrategy("test_strategy", self.strategy_config, self.trading_engine)
    
    def test_strategy_initialization(self):
        """测试策略初始化"""
        self.assertEqual(self.strategy.strategy_name, "test_strategy")
        self.assertEqual(self.strategy.config.name, "test_strategy")
        self.assertEqual(self.strategy.status, StrategyStatus.INACTIVE)
        self.assertIsNone(self.strategy.start_time)
        self.assertIsNone(self.strategy.stop_time)
        
        # 检查数据存储初始化
        self.assertIsInstance(self.strategy.tick_data, dict)
        self.assertIsInstance(self.strategy.bar_data, dict)
        self.assertIsInstance(self.strategy.trades, list)
        self.assertIsInstance(self.strategy.signals, list)
    
    def test_strategy_lifecycle_methods(self):
        """测试策略生命周期方法"""
        # 测试初始化
        self.strategy.on_init()
        
        # 测试启动
        self.strategy._set_status(StrategyStatus.RUNNING)
        self.strategy.start_time = datetime.now()
        self.strategy.on_start()
        
        # 测试停止
        self.strategy.stop_time = datetime.now()
        self.strategy.on_stop()
        
        # 验证状态变化
        self.assertEqual(self.strategy.status, StrategyStatus.RUNNING)
    
    def test_tick_data_management(self):
        """测试Tick数据管理"""
        # 创建测试Tick数据
        tick = TickData(
            symbol="rb2310",
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            name="螺纹钢2310",
            volume=100,
            turnover=350000.0,
            open_interest=50000,
            last_price=3500.0
        )
        
        # 添加Tick数据
        self.strategy.add_tick_data(tick)
        
        # 验证数据存储
        self.assertIn("rb2310", self.strategy.tick_data)
        self.assertEqual(len(self.strategy.tick_data["rb2310"]), 1)
        self.assertEqual(self.strategy.tick_data["rb2310"][0], tick)
        
        # 测试获取最近数据
        recent_ticks = self.strategy.get_recent_ticks("rb2310", 10)
        self.assertEqual(len(recent_ticks), 1)
        self.assertEqual(recent_ticks[0], tick)
    
    def test_bar_data_management(self):
        """测试Bar数据管理"""
        # 创建测试Bar数据
        bar = BarData(
            symbol="rb2310",
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            interval=Interval.MINUTE,
            volume=1000,
            turnover=3500000.0,
            open_interest=50000,
            open_price=3490.0,
            high_price=3510.0,
            low_price=3485.0,
            close_price=3505.0
        )
        
        # 添加Bar数据
        self.strategy.add_bar_data(bar)
        
        # 验证数据存储
        self.assertIn("rb2310", self.strategy.bar_data)
        self.assertEqual(len(self.strategy.bar_data["rb2310"]), 1)
        self.assertEqual(self.strategy.bar_data["rb2310"][0], bar)
        
        # 测试获取最近数据
        recent_bars = self.strategy.get_recent_bars("rb2310", 10)
        self.assertEqual(len(recent_bars), 1)
        self.assertEqual(recent_bars[0], bar)
    
    def test_ma_calculation(self):
        """测试移动平均线计算"""
        # 创建多个Bar数据
        prices = [3500.0, 3510.0, 3495.0, 3520.0, 3505.0]
        
        for i, price in enumerate(prices):
            bar = BarData(
                symbol="rb2310",
                exchange=Exchange.SHFE,
                datetime=datetime.now(),
                interval=Interval.MINUTE,
                volume=1000,
                turnover=price * 1000,
                open_interest=50000,
                open_price=price - 5,
                high_price=price + 5,
                low_price=price - 10,
                close_price=price
            )
            self.strategy.add_bar_data(bar)
        
        # 计算MA
        ma_5 = self.strategy.calculate_ma("rb2310", 5, "close")
        expected_ma = sum(prices) / len(prices)
        
        self.assertIsNotNone(ma_5)
        self.assertAlmostEqual(ma_5, expected_ma, places=2)
        
        # 测试数据不足的情况
        ma_10 = self.strategy.calculate_ma("rb2310", 10, "close")
        self.assertIsNone(ma_10)
    
    def test_signal_sending(self):
        """测试交易信号发送"""
        # 连接交易引擎
        self.connection_manager.connect_gateway()
        
        # 创建交易信号
        signal = TradingSignal(
            symbol="rb2310",
            action=TradingSignalAction.OPEN_LONG,
            volume=1,
            price=0.0,
            timestamp=datetime.now(),
            strategy="test_strategy",
            reason="测试信号"
        )
        
        # 发送信号
        result = self.strategy.send_signal(signal)
        
        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.orderid)
        
        # 验证信号记录
        self.assertEqual(len(self.strategy.signals), 1)
        self.assertEqual(self.strategy.signals[0], signal)
    
    def test_statistics_update(self):
        """测试统计信息更新"""
        # 创建成交数据
        trade = TradeData(
            tradeid="TEST_TRADE_001",
            orderid="TEST_ORDER_001",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            volume=1,
            price=3500.0,
            datetime=datetime.now()
        )
        
        # 更新统计
        self.strategy.update_statistics(trade)
        
        # 验证统计信息
        stats = self.strategy.get_statistics()
        self.assertEqual(stats["total_trades"], 1)
        self.assertEqual(stats["strategy_name"], "test_strategy")
        self.assertEqual(len(self.strategy.trades), 1)


class TestDataEventDispatcher(unittest.TestCase):
    """数据事件分发器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.dispatcher = DataEventDispatcher()
        
        # 创建测试策略
        with open('/home/user/webapp/system_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.connection_manager = ConnectionManager(config)
        self.trading_engine = TradingEngine(self.connection_manager, config)
        
        self.strategy_config = create_sample_strategy_config("test_strategy", ["rb2310"])
        self.strategy = MockStrategy("test_strategy", self.strategy_config, self.trading_engine)
        
        # 重置计数器
        self.strategy.tick_count = 0
        self.strategy.bar_count = 0
    
    def test_strategy_subscription(self):
        """测试策略订阅"""
        events = [StrategyEvent.TICK, StrategyEvent.BAR]
        
        # 订阅事件
        self.dispatcher.subscribe_strategy(self.strategy, events)
        
        # 验证订阅
        self.assertIn(self.strategy, self.dispatcher.strategy_subscribers[StrategyEvent.TICK])
        self.assertIn(self.strategy, self.dispatcher.strategy_subscribers[StrategyEvent.BAR])
        self.assertIn(self.strategy, self.dispatcher.symbol_subscribers["rb2310"])
    
    def test_tick_dispatch(self):
        """测试Tick事件分发"""
        # 订阅事件
        events = [StrategyEvent.TICK]
        self.dispatcher.subscribe_strategy(self.strategy, events)
        
        # 创建Tick数据
        tick = TickData(
            symbol="rb2310",
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            name="螺纹钢2310",
            volume=100,
            turnover=350000.0,
            open_interest=50000,
            last_price=3500.0
        )
        
        # 分发事件
        self.dispatcher.dispatch_tick(tick)
        
        # 验证事件处理
        self.assertEqual(self.strategy.tick_count, 1)
        self.assertIn("rb2310", self.strategy.tick_data)
        self.assertEqual(len(self.strategy.tick_data["rb2310"]), 1)
    
    def test_bar_dispatch(self):
        """测试Bar事件分发"""
        # 订阅事件
        events = [StrategyEvent.BAR]
        self.dispatcher.subscribe_strategy(self.strategy, events)
        
        # 创建Bar数据
        bar = BarData(
            symbol="rb2310",
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            interval=Interval.MINUTE,
            volume=1000,
            turnover=3500000.0,
            open_interest=50000,
            open_price=3490.0,
            high_price=3510.0,
            low_price=3485.0,
            close_price=3505.0
        )
        
        # 分发事件
        self.dispatcher.dispatch_bar(bar)
        
        # 验证事件处理
        self.assertEqual(self.strategy.bar_count, 1)
        self.assertIn("rb2310", self.strategy.bar_data)
        self.assertEqual(len(self.strategy.bar_data["rb2310"]), 1)
    
    def test_trade_dispatch(self):
        """测试Trade事件分发"""
        # 订阅事件
        events = [StrategyEvent.TRADE]
        self.dispatcher.subscribe_strategy(self.strategy, events)
        
        # 创建Trade数据
        trade = TradeData(
            tradeid="TEST_TRADE_001",
            orderid="TEST_ORDER_001",
            symbol="rb2310",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            volume=1,
            price=3500.0,
            datetime=datetime.now()
        )
        
        # 分发事件
        self.dispatcher.dispatch_trade(trade)
        
        # 验证事件处理
        self.assertEqual(len(self.strategy.trades), 1)
        self.assertEqual(self.strategy.total_trades, 1)
    
    def test_unsubscribe_strategy(self):
        """测试取消策略订阅"""
        # 先订阅
        events = [StrategyEvent.TICK, StrategyEvent.BAR]
        self.dispatcher.subscribe_strategy(self.strategy, events)
        
        # 验证订阅成功
        self.assertIn(self.strategy, self.dispatcher.strategy_subscribers[StrategyEvent.TICK])
        
        # 取消订阅
        self.dispatcher.unsubscribe_strategy(self.strategy)
        
        # 验证取消成功
        self.assertNotIn(self.strategy, self.dispatcher.strategy_subscribers[StrategyEvent.TICK])
        self.assertNotIn(self.strategy, self.dispatcher.strategy_subscribers[StrategyEvent.BAR])


class TestStrategyManager(unittest.TestCase):
    """策略管理器测试"""
    
    def setUp(self):
        """设置测试环境"""
        # 加载配置
        with open('/home/user/webapp/system_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.connection_manager = ConnectionManager(config)
        self.trading_engine = TradingEngine(self.connection_manager, config)
        self.strategy_manager = StrategyManager(self.trading_engine)
        
        # 创建策略配置
        self.strategy_config = create_sample_strategy_config("test_strategy", ["rb2310"])
    
    def test_load_strategy(self):
        """测试策略加载"""
        # 加载策略
        success = self.strategy_manager.load_strategy(MockStrategy, self.strategy_config)
        
        self.assertTrue(success)
        self.assertIn("test_strategy", self.strategy_manager.strategies)
        
        # 获取策略
        strategy = self.strategy_manager.get_strategy("test_strategy")
        self.assertIsNotNone(strategy)
        self.assertEqual(strategy.strategy_name, "test_strategy")
        self.assertEqual(strategy.status, StrategyStatus.LOADED)
    
    def test_duplicate_strategy_loading(self):
        """测试重复策略加载"""
        # 第一次加载
        success1 = self.strategy_manager.load_strategy(MockStrategy, self.strategy_config)
        self.assertTrue(success1)
        
        # 第二次加载相同名称的策略
        success2 = self.strategy_manager.load_strategy(MockStrategy, self.strategy_config)
        self.assertFalse(success2)
    
    def test_start_stop_strategy(self):
        """测试策略启动和停止"""
        # 先加载策略
        self.strategy_manager.load_strategy(MockStrategy, self.strategy_config)
        
        # 启动策略
        start_success = self.strategy_manager.start_strategy("test_strategy")
        self.assertTrue(start_success)
        
        strategy = self.strategy_manager.get_strategy("test_strategy")
        self.assertEqual(strategy.status, StrategyStatus.RUNNING)
        self.assertIsNotNone(strategy.start_time)
        
        # 停止策略
        stop_success = self.strategy_manager.stop_strategy("test_strategy")
        self.assertTrue(stop_success)
        
        self.assertEqual(strategy.status, StrategyStatus.STOPPED)
        self.assertIsNotNone(strategy.stop_time)
    
    def test_start_nonexistent_strategy(self):
        """测试启动不存在的策略"""
        success = self.strategy_manager.start_strategy("nonexistent_strategy")
        self.assertFalse(success)
    
    def test_start_unloaded_strategy(self):
        """测试启动未加载的策略"""
        # 创建策略但不设置为LOADED状态
        strategy = MockStrategy("test_strategy", self.strategy_config, self.trading_engine)
        strategy._set_status(StrategyStatus.INACTIVE)
        self.strategy_manager.strategies["test_strategy"] = strategy
        
        success = self.strategy_manager.start_strategy("test_strategy")
        self.assertFalse(success)
    
    def test_remove_strategy(self):
        """测试移除策略"""
        # 先加载并启动策略
        self.strategy_manager.load_strategy(MockStrategy, self.strategy_config)
        self.strategy_manager.start_strategy("test_strategy")
        
        # 移除策略
        success = self.strategy_manager.remove_strategy("test_strategy")
        self.assertTrue(success)
        
        # 验证策略已被移除
        self.assertNotIn("test_strategy", self.strategy_manager.strategies)
        strategy = self.strategy_manager.get_strategy("test_strategy")
        self.assertIsNone(strategy)
    
    def test_get_active_strategies(self):
        """测试获取活跃策略"""
        # 加载两个策略
        config1 = create_sample_strategy_config("strategy1", ["rb2310"])
        config2 = create_sample_strategy_config("strategy2", ["i2310"])
        
        self.strategy_manager.load_strategy(MockStrategy, config1)
        self.strategy_manager.load_strategy(MockStrategy, config2)
        
        # 只启动一个策略
        self.strategy_manager.start_strategy("strategy1")
        
        # 获取活跃策略
        active_strategies = self.strategy_manager.get_active_strategies()
        self.assertEqual(len(active_strategies), 1)
        self.assertIn("strategy1", active_strategies)
        self.assertNotIn("strategy2", active_strategies)
    
    def test_strategy_statistics(self):
        """测试策略统计信息"""
        # 加载并启动策略
        self.strategy_manager.load_strategy(MockStrategy, self.strategy_config)
        self.strategy_manager.start_strategy("test_strategy")
        
        # 获取统计信息
        statistics = self.strategy_manager.get_strategy_statistics()
        
        self.assertIn("test_strategy", statistics)
        stats = statistics["test_strategy"]
        
        self.assertEqual(stats["strategy_name"], "test_strategy")
        self.assertEqual(stats["status"], "running")
        self.assertIsNotNone(stats["start_time"])


class TestStrategyEngine(unittest.TestCase):
    """策略引擎集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        # 加载配置
        with open('/home/user/webapp/system_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.connection_manager = ConnectionManager(config)
        self.trading_engine = TradingEngine(self.connection_manager, config)
        self.market_data_manager = MarketDataManager(self.connection_manager)
        self.strategy_engine = StrategyEngine(self.trading_engine, self.market_data_manager)
        
        # 连接交易网关
        self.connection_manager.connect_gateway()
    
    def test_strategy_engine_initialization(self):
        """测试策略引擎初始化"""
        self.assertIsNotNone(self.strategy_engine.strategy_manager)
        self.assertIsNotNone(self.strategy_engine.event_dispatcher)
        self.assertIsNotNone(self.strategy_engine.trading_engine)
        self.assertIsNotNone(self.strategy_engine.market_data_manager)
    
    def test_load_and_start_strategy(self):
        """测试加载和启动策略"""
        # 创建策略配置
        config = create_sample_strategy_config("test_strategy", ["rb2310"])
        
        # 加载策略
        load_success = self.strategy_engine.load_strategy(MockStrategy, config)
        self.assertTrue(load_success)
        
        # 检查活跃策略（应该为空，因为还没启动）
        active_strategies = self.strategy_engine.active_strategies
        self.assertEqual(len(active_strategies), 0)
        
        # 启动策略
        start_success = self.strategy_engine.start_strategy("test_strategy")
        self.assertTrue(start_success)
        
        # 检查活跃策略
        active_strategies = self.strategy_engine.active_strategies
        self.assertEqual(len(active_strategies), 1)
        self.assertIn("test_strategy", active_strategies)
    
    def test_strategy_with_market_data(self):
        """测试策略与市场数据集成"""
        # 加载并启动策略
        config = create_sample_strategy_config("test_strategy", ["rb2310"])
        self.strategy_engine.load_strategy(MockStrategy, config)
        self.strategy_engine.start_strategy("test_strategy")
        
        # 启动市场数据管理器
        self.market_data_manager.start()
        
        # 订阅市场数据
        self.market_data_manager.subscribe_market_data("rb2310")
        
        # 等待一段时间让数据流动
        time.sleep(2)
        
        # 获取策略实例
        strategy = self.strategy_engine.strategy_manager.get_strategy("test_strategy")
        
        # 验证策略接收到了数据
        self.assertGreater(strategy.tick_count, 0)
        self.assertIn("rb2310", strategy.tick_data)
        self.assertGreater(len(strategy.tick_data["rb2310"]), 0)
    
    def test_stop_and_remove_strategy(self):
        """测试停止和移除策略"""
        # 加载并启动策略
        config = create_sample_strategy_config("test_strategy", ["rb2310"])
        self.strategy_engine.load_strategy(MockStrategy, config)
        self.strategy_engine.start_strategy("test_strategy")
        
        # 验证策略在运行
        self.assertIn("test_strategy", self.strategy_engine.active_strategies)
        
        # 停止策略
        stop_success = self.strategy_engine.stop_strategy("test_strategy")
        self.assertTrue(stop_success)
        
        # 验证策略不再活跃
        self.assertNotIn("test_strategy", self.strategy_engine.active_strategies)
        
        # 移除策略
        remove_success = self.strategy_engine.remove_strategy("test_strategy")
        self.assertTrue(remove_success)
        
        # 验证策略完全移除
        strategy = self.strategy_engine.strategy_manager.get_strategy("test_strategy")
        self.assertIsNone(strategy)
    
    def test_strategy_engine_status(self):
        """测试策略引擎状态"""
        # 获取初始状态
        status = self.strategy_engine.get_status()
        
        self.assertIn("ready", status)
        self.assertIn("total_strategies", status)
        self.assertIn("active_strategies", status)
        self.assertIn("trading_engine_ready", status)
        self.assertIn("market_data_ready", status)
        
        # 加载策略后检查状态
        config = create_sample_strategy_config("test_strategy", ["rb2310"])
        self.strategy_engine.load_strategy(MockStrategy, config)
        self.strategy_engine.start_strategy("test_strategy")
        
        updated_status = self.strategy_engine.get_status()
        self.assertEqual(updated_status["total_strategies"], 1)
        self.assertEqual(updated_status["active_strategies"], 1)
        self.assertIn("test_strategy", updated_status["active_strategy_names"])
    
    def test_strategy_config_creation(self):
        """测试策略配置创建"""
        config = create_sample_strategy_config("my_strategy", ["rb2310", "i2310"])
        
        self.assertEqual(config.name, "my_strategy")
        self.assertEqual(config.symbols, ["rb2310", "i2310"])
        self.assertEqual(config.class_name, "MockStrategy")
        self.assertTrue(config.enabled)
        self.assertFalse(config.auto_start)
        self.assertEqual(config.initial_capital, 100000.0)


def run_strategy_engine_tests():
    """运行StrategyEngine模块所有测试"""
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加StrategyBase测试
    test_suite.addTest(TestStrategyBase('test_strategy_initialization'))
    test_suite.addTest(TestStrategyBase('test_strategy_lifecycle_methods'))
    test_suite.addTest(TestStrategyBase('test_tick_data_management'))
    test_suite.addTest(TestStrategyBase('test_bar_data_management'))
    test_suite.addTest(TestStrategyBase('test_ma_calculation'))
    test_suite.addTest(TestStrategyBase('test_signal_sending'))
    test_suite.addTest(TestStrategyBase('test_statistics_update'))
    
    # 添加DataEventDispatcher测试
    test_suite.addTest(TestDataEventDispatcher('test_strategy_subscription'))
    test_suite.addTest(TestDataEventDispatcher('test_tick_dispatch'))
    test_suite.addTest(TestDataEventDispatcher('test_bar_dispatch'))
    test_suite.addTest(TestDataEventDispatcher('test_trade_dispatch'))
    test_suite.addTest(TestDataEventDispatcher('test_unsubscribe_strategy'))
    
    # 添加StrategyManager测试
    test_suite.addTest(TestStrategyManager('test_load_strategy'))
    test_suite.addTest(TestStrategyManager('test_duplicate_strategy_loading'))
    test_suite.addTest(TestStrategyManager('test_start_stop_strategy'))
    test_suite.addTest(TestStrategyManager('test_start_nonexistent_strategy'))
    test_suite.addTest(TestStrategyManager('test_start_unloaded_strategy'))
    test_suite.addTest(TestStrategyManager('test_remove_strategy'))
    test_suite.addTest(TestStrategyManager('test_get_active_strategies'))
    test_suite.addTest(TestStrategyManager('test_strategy_statistics'))
    
    # 添加StrategyEngine集成测试
    test_suite.addTest(TestStrategyEngine('test_strategy_engine_initialization'))
    test_suite.addTest(TestStrategyEngine('test_load_and_start_strategy'))
    test_suite.addTest(TestStrategyEngine('test_strategy_with_market_data'))
    test_suite.addTest(TestStrategyEngine('test_stop_and_remove_strategy'))
    test_suite.addTest(TestStrategyEngine('test_strategy_engine_status'))
    test_suite.addTest(TestStrategyEngine('test_strategy_config_creation'))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result


if __name__ == '__main__':
    print("="*80)
    print("StrategyEngine模块单元测试")
    print("Testing StrategyEngine Module")
    print("="*80)
    
    # 更改工作目录到项目根目录
    import os
    os.chdir('/home/user/webapp')
    
    # 运行测试
    test_result = run_strategy_engine_tests()
    
    print("\n" + "="*80)
    print("StrategyEngine测试总结 (Test Summary)")
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
        print("🎉 StrategyEngine模块测试通过！")
    else:
        print("⚠️ 部分测试未通过，需要进一步调试")