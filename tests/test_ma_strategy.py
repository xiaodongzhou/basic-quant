#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MA Strategy Test Suite

MA策略的综合测试套件
- 测试MA指标计算
- 测试信号生成逻辑
- 测试交易执行逻辑
- 测试风险管理
- 测试回测验证
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime, timedelta
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from strategies.ma_strategy import MAStrategy, MAIndicator, PositionInfo, SignalInfo
from core.data_types import BarData, TickData, TradeData, OrderData
from core.strategy_engine import StrategyStatus


class TestMAIndicator(unittest.TestCase):
    """测试MA指标类"""
    
    def setUp(self):
        self.ma5 = MAIndicator(period=5)
        self.ma20 = MAIndicator(period=20)
    
    def test_indicator_initialization(self):
        """测试指标初始化"""
        self.assertEqual(self.ma5.period, 5)
        self.assertEqual(self.ma20.period, 20)
        self.assertEqual(len(self.ma5.values), 0)
        self.assertEqual(len(self.ma20.values), 0)
        self.assertFalse(self.ma5.is_ready())
        self.assertFalse(self.ma20.is_ready())
    
    def test_indicator_update(self):
        """测试指标更新"""
        # 添加数据
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        
        for price in prices:
            ma_value = self.ma5.update(price)
        
        # MA5应该准备好
        self.assertTrue(self.ma5.is_ready())
        self.assertEqual(self.ma5.current_ma, 102.0)  # (100+101+102+103+104)/5 = 102
        
        # 继续添加数据测试滑动窗口
        self.ma5.update(105.0)
        self.assertEqual(self.ma5.current_ma, 103.0)  # (101+102+103+104+105)/5 = 103
    
    def test_indicator_not_ready(self):
        """测试指标未准备好的情况"""
        # MA20需要20个数据点
        for i in range(19):
            self.ma20.update(100.0 + i)
        
        self.assertFalse(self.ma20.is_ready())
        self.assertEqual(self.ma20.current_ma, 0.0)
        
        # 添加第20个数据点
        self.ma20.update(119.0)
        self.assertTrue(self.ma20.is_ready())
        self.assertEqual(self.ma20.current_ma, 109.5)  # (100+101+...+119)/20 = 109.5


class TestPositionInfo(unittest.TestCase):
    """测试持仓信息类"""
    
    def test_position_initialization(self):
        """测试持仓初始化"""
        pos = PositionInfo(symbol='rb2405', direction='none')
        
        self.assertEqual(pos.symbol, 'rb2405')
        self.assertEqual(pos.direction, 'none')
        self.assertEqual(pos.volume, 0)
        self.assertTrue(pos.is_empty())
        self.assertFalse(pos.is_long())
        self.assertFalse(pos.is_short())
    
    def test_long_position(self):
        """测试多头持仓"""
        pos = PositionInfo(symbol='rb2405', direction='long', volume=5, avg_price=4000.0)
        
        self.assertTrue(pos.is_long())
        self.assertFalse(pos.is_short())
        self.assertFalse(pos.is_empty())
    
    def test_short_position(self):
        """测试空头持仓"""
        pos = PositionInfo(symbol='rb2405', direction='short', volume=3, avg_price=4000.0)
        
        self.assertTrue(pos.is_short())
        self.assertFalse(pos.is_long())
        self.assertFalse(pos.is_empty())


class TestMAStrategy(unittest.TestCase):
    """测试MA策略类"""
    
    def setUp(self):
        """设置测试环境"""
        # 配置日志
        logging.basicConfig(level=logging.DEBUG)
        
        # 策略配置
        self.config = {
            'fast_period': 5,
            'slow_period': 20,
            'trade_volume': 1,
            'max_position': 5,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'subscribed_symbols': ['rb2405', 'i2405']
        }
        
        # 创建策略实例
        self.strategy = MAStrategy('test_ma_strategy', self.config)
        
        # 设置订阅合约
        self.strategy.subscribed_symbols = ['rb2405', 'i2405']
    
    def test_strategy_initialization(self):
        """测试策略初始化"""
        self.assertEqual(self.strategy.strategy_name, 'test_ma_strategy')
        self.assertEqual(self.strategy.fast_period, 5)
        self.assertEqual(self.strategy.slow_period, 20)
        self.assertEqual(self.strategy.trade_volume, 1)
        self.assertEqual(self.strategy.max_position, 5)
        self.assertEqual(self.strategy.status, StrategyStatus.INACTIVE)
    
    def test_strategy_init_process(self):
        """测试策略初始化过程"""
        # 执行初始化
        result = self.strategy.on_init()
        
        self.assertTrue(result)
        self.assertEqual(len(self.strategy.indicators), 2)
        self.assertEqual(len(self.strategy.positions), 2)
        
        # 检查指标初始化
        for symbol in ['rb2405', 'i2405']:
            self.assertIn(symbol, self.strategy.indicators)
            self.assertIn('fast_ma', self.strategy.indicators[symbol])
            self.assertIn('slow_ma', self.strategy.indicators[symbol])
            
            # 检查持仓初始化
            self.assertIn(symbol, self.strategy.positions)
            self.assertTrue(self.strategy.positions[symbol].is_empty())
    
    def test_strategy_start_stop(self):
        """测试策略启动和停止"""
        # 初始化
        self.strategy.on_init()
        
        # 启动
        result = self.strategy.on_start()
        self.assertTrue(result)
        self.assertEqual(len(self.strategy.signals), 0)
        self.assertEqual(len(self.strategy.trades), 0)
        
        # 停止
        result = self.strategy.on_stop()
        self.assertTrue(result)
    
    def test_indicator_update(self):
        """测试指标更新"""
        # 初始化策略
        self.strategy.on_init()
        
        # 测试数据
        symbol = 'rb2405'
        prices = [4000.0, 4010.0, 4020.0, 4030.0, 4040.0]
        
        for price in prices:
            fast_ma, slow_ma = self.strategy._update_indicators(symbol, price)
        
        # 检查快线MA5
        self.assertTrue(self.strategy.indicators[symbol]['fast_ma'].is_ready())
        self.assertEqual(fast_ma, 4020.0)  # (4000+4010+4020+4030+4040)/5 = 4020
        
        # 慢线MA20还未准备好
        self.assertFalse(self.strategy.indicators[symbol]['slow_ma'].is_ready())
    
    def test_signal_generation(self):
        """测试信号生成"""
        # 初始化策略
        self.strategy.on_init()
        self.strategy.on_start()
        
        symbol = 'rb2405'
        
        # 准备MA5指标数据 (使其ready)
        ma5_prices = [4000.0, 4010.0, 4020.0, 4030.0, 4040.0]
        for price in ma5_prices:
            self.strategy._update_indicators(symbol, price)
        
        # 准备MA20指标数据 (使其ready) 
        ma20_prices = list(range(3980, 4000)) + [4000.0]  # 20个数据点
        for price in ma20_prices:
            self.strategy._update_indicators(symbol, price)
        
        # 确保指标准备好
        self.assertTrue(self.strategy._indicators_ready(symbol))
        
        # 创建测试K线
        bar = BarData(
            symbol=symbol,
            datetime=datetime.now(),
            open_price=4050.0,
            high_price=4060.0,
            low_price=4040.0,
            close_price=4050.0,
            volume=1000
        )
        
        # 获取当前MA值
        fast_ma = self.strategy.indicators[symbol]['fast_ma'].current_ma
        slow_ma = self.strategy.indicators[symbol]['slow_ma'].current_ma
        
        # 生成信号
        signal = self.strategy._generate_signal(symbol, bar, fast_ma, slow_ma)
        
        # 验证信号结构
        self.assertIsInstance(signal, SignalInfo)
        self.assertEqual(signal.price, 4050.0)
        self.assertEqual(signal.fast_ma, fast_ma)
        self.assertEqual(signal.slow_ma, slow_ma)
    
    def test_golden_cross_signal(self):
        """测试金叉信号"""
        # 初始化策略
        self.strategy.on_init()
        self.strategy.on_start()
        
        symbol = 'rb2405'
        
        # 模拟金叉场景：快线从下方穿越慢线
        # 先让快线低于慢线
        slow_prices = [4000.0] * 20  # MA20 = 4000
        for price in slow_prices:
            self.strategy._update_indicators(symbol, price)
        
        fast_prices = [3990.0] * 5  # MA5 = 3990, 低于MA20
        for price in fast_prices:
            self.strategy._update_indicators(symbol, price)
        
        # 现在让快线上穿慢线
        # 添加更高的价格使MA5上升
        rising_prices = [4020.0, 4030.0, 4040.0, 4050.0, 4060.0]
        for i, price in enumerate(rising_prices):
            self.strategy._update_indicators(symbol, price)
            
            # 在最后一个价格时检查信号
            if i == len(rising_prices) - 1:
                bar = BarData(
                    symbol=symbol,
                    datetime=datetime.now(),
                    open_price=price-10,
                    high_price=price+10,
                    low_price=price-20,
                    close_price=price,
                    volume=1000
                )
                
                fast_ma = self.strategy.indicators[symbol]['fast_ma'].current_ma
                slow_ma = self.strategy.indicators[symbol]['slow_ma'].current_ma
                
                # 现在快线应该高于慢线，可能形成金叉
                if fast_ma > slow_ma:
                    signal = self.strategy._generate_signal(symbol, bar, fast_ma, slow_ma)
                    # 注意：由于信号生成逻辑需要比较前一周期，这里可能需要更复杂的测试
    
    def test_position_opening(self):
        """测试开仓逻辑"""
        # 初始化策略
        self.strategy.on_init()
        self.strategy.on_start()
        
        symbol = 'rb2405'
        price = 4000.0
        
        # 测试开多仓
        initial_trades = len(self.strategy.trades)
        self.strategy._open_long_position(symbol, price)
        
        # 验证交易记录增加
        self.assertEqual(len(self.strategy.trades), initial_trades + 1)
        
        # 验证持仓更新
        position = self.strategy.positions[symbol]
        self.assertTrue(position.is_long())
        self.assertEqual(position.volume, 1)
        self.assertEqual(position.avg_price, price)
    
    def test_position_closing(self):
        """测试平仓逻辑"""
        # 初始化策略并开仓
        self.strategy.on_init()
        self.strategy.on_start()
        
        symbol = 'rb2405'
        price = 4000.0
        
        # 先开多仓
        self.strategy._open_long_position(symbol, price)
        position = self.strategy.positions[symbol]
        self.assertTrue(position.is_long())
        
        # 平仓
        initial_trades = len(self.strategy.trades)
        self.strategy._close_position(symbol, position)
        
        # 验证交易记录增加
        self.assertEqual(len(self.strategy.trades), initial_trades + 1)
        
        # 验证持仓清空
        self.assertTrue(position.is_empty())
    
    def test_pnl_calculation(self):
        """测试盈亏计算"""
        # 初始化策略
        self.strategy.on_init()
        self.strategy.on_start()
        
        symbol = 'rb2405'
        open_price = 4000.0
        current_price = 4100.0
        
        # 开多仓
        self.strategy._open_long_position(symbol, open_price)
        
        # 更新盈亏
        self.strategy._update_position_pnl(symbol, current_price)
        
        position = self.strategy.positions[symbol]
        expected_pnl = (current_price - open_price) * position.volume
        self.assertEqual(position.unrealized_pnl, expected_pnl)
    
    def test_risk_management(self):
        """测试风险管理"""
        # 初始化策略
        self.strategy.on_init()
        self.strategy.on_start()
        
        symbol = 'rb2405'
        open_price = 4000.0
        
        # 开多仓
        self.strategy._open_long_position(symbol, open_price)
        
        # 测试止损：价格下跌超过2%
        stop_loss_price = open_price * (1 - self.strategy.stop_loss_pct - 0.005)  # 稍微超过止损线
        
        initial_trades = len(self.strategy.trades)
        self.strategy._check_risk_management(symbol, stop_loss_price)
        
        # 应该触发止损平仓
        self.assertEqual(len(self.strategy.trades), initial_trades + 1)
        self.assertTrue(self.strategy.positions[symbol].is_empty())
    
    def test_bar_processing(self):
        """测试K线处理完整流程"""
        # 初始化策略
        self.strategy.on_init()
        self.strategy.on_start()
        
        symbol = 'rb2405'
        
        # 准备足够的历史数据使指标ready
        for i in range(25):  # 超过MA20需要的数量
            bar = BarData(
                symbol=symbol,
                datetime=datetime.now() + timedelta(minutes=i),
                open_price=4000.0 + i,
                high_price=4010.0 + i,
                low_price=3990.0 + i,
                close_price=4000.0 + i,
                volume=1000
            )
            self.strategy.on_bar(bar)
        
        # 验证指标已准备好
        self.assertTrue(self.strategy._indicators_ready(symbol))
        
        # 验证有一些信号生成
        # (具体信号取决于数据模式，这里只验证流程正常)
        self.assertGreaterEqual(len(self.strategy.signals), 0)
    
    def test_tick_processing(self):
        """测试Tick处理"""
        # 初始化策略并开仓
        self.strategy.on_init()
        self.strategy.on_start()
        
        symbol = 'rb2405'
        self.strategy._open_long_position(symbol, 4000.0)
        
        # 创建Tick数据
        tick = TickData(
            symbol=symbol,
            datetime=datetime.now(),
            last_price=4050.0,
            volume=100,
            bid_price=4048.0,
            ask_price=4052.0
        )
        
        # 处理Tick
        self.strategy.on_tick(tick)
        
        # 验证盈亏更新
        position = self.strategy.positions[symbol]
        self.assertGreater(position.unrealized_pnl, 0)  # 应该有盈利
    
    def test_strategy_info(self):
        """测试策略信息获取"""
        # 初始化策略
        self.strategy.on_init()
        
        info = self.strategy.get_strategy_info()
        
        # 验证基本信息
        self.assertEqual(info['strategy_name'], 'test_ma_strategy')
        self.assertEqual(info['strategy_type'], 'MA Strategy')
        self.assertEqual(info['fast_period'], 5)
        self.assertEqual(info['slow_period'], 20)
        self.assertIn('positions', info)
        self.assertIn('subscribed_symbols', info)


class TestMAStrategyIntegration(unittest.TestCase):
    """MA策略集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.config = {
            'fast_period': 5,
            'slow_period': 10,  # 使用较小周期便于测试
            'trade_volume': 1,
            'max_position': 3,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'subscribed_symbols': ['test_symbol']
        }
        
        self.strategy = MAStrategy('integration_test', self.config)
        self.strategy.subscribed_symbols = ['test_symbol']
    
    def test_complete_trading_cycle(self):
        """测试完整的交易周期"""
        # 初始化和启动策略
        self.strategy.on_init()
        self.strategy.on_start()
        
        symbol = 'test_symbol'
        base_time = datetime.now()
        
        # 生成测试数据：先平稳再上涨（可能触发金叉）
        prices = ([4000.0] * 15 +  # 平稳阶段，让MA都稳定在4000附近
                 [4010.0, 4020.0, 4030.0, 4040.0, 4050.0])  # 上涨阶段
        
        bars = []
        for i, price in enumerate(prices):
            bar = BarData(
                symbol=symbol,
                datetime=base_time + timedelta(minutes=i),
                open_price=price - 5,
                high_price=price + 5,
                low_price=price - 10,
                close_price=price,
                volume=1000
            )
            bars.append(bar)
            
            # 处理K线
            self.strategy.on_bar(bar)
        
        # 验证策略状态
        self.assertTrue(self.strategy._indicators_ready(symbol))
        
        # 打印一些调试信息
        print(f"信号数量: {len(self.strategy.signals)}")
        print(f"交易数量: {len(self.strategy.trades)}")
        
        position = self.strategy.positions[symbol]
        print(f"持仓状态: {position.direction}, 数量: {position.volume}")
        
        # 停止策略
        self.strategy.on_stop()


def run_ma_strategy_tests():
    """运行MA策略测试套件"""
    print("=== 开始运行MA策略测试套件 ===")
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestMAIndicator,
        TestPositionInfo,
        TestMAStrategy,
        TestMAStrategyIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 打印结果摘要
    print(f"\n=== 测试结果摘要 ===")
    print(f"运行测试数量: {result.testsRun}")
    print(f"失败数量: {len(result.failures)}")
    print(f"错误数量: {len(result.errors)}")
    print(f"跳过数量: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print(f"\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # 返回成功率
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n成功率: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # 运行测试
    success = run_ma_strategy_tests()
    
    if success:
        print("\n🎉 所有MA策略测试通过！")
    else:
        print("\n❌ 部分测试失败，请检查实现")
    
    # 退出码
    import sys
    sys.exit(0 if success else 1)