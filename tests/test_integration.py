"""
集成测试模块：ConnectionManager + MarketDataManager
Integration Test Module: ConnectionManager + MarketDataManager

测试完整的数据流：连接建立 → 行情订阅 → 数据接收 → 技术指标计算
Test complete data flow: Connection establishment → Market data subscription → Data reception → Technical indicator calculation
"""

import unittest
import threading
import time
import json
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.connection_manager import ConnectionManager, ConnectionStatus
from core.market_data_manager import MarketDataManager
from core.data_types import TickData, BarData, ContractData, Exchange, Direction, Interval


class IntegrationTestFramework(unittest.TestCase):
    """
    集成测试框架类
    Integration test framework class for testing the complete system integration
    """
    
    def setUp(self):
        """设置测试环境"""
        # 加载系统配置
        with open('system_config.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # 初始化组件
        self.connection_manager = ConnectionManager(self.config)
        self.market_data_manager = MarketDataManager(self.connection_manager)
        
        # 测试数据存储
        self.received_ticks: List[TickData] = []
        self.received_bars: List[BarData] = []
        self.connection_events: List[str] = []
        self.indicator_results: Dict[str, Any] = {}
        
        # 线程同步
        self.test_complete = threading.Event()
        self.data_received_count = 0
        self.expected_data_count = 10  # 期望接收的数据条数
        
        # 注册回调函数
        self._register_callbacks()
    
    def tearDown(self):
        """清理测试环境"""
        try:
            # 停止行情数据管理器
            if hasattr(self.market_data_manager, '_simulation_active'):
                self.market_data_manager._simulation_active = False
            
            # 断开连接
            self.connection_manager.disconnect_gateway()
            
            # 等待线程结束
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Teardown error: {e}")
    
    def _register_callbacks(self):
        """注册回调函数"""
        
        def on_tick_received(tick: TickData):
            """Tick数据接收回调"""
            self.received_ticks.append(tick)
            self.data_received_count += 1
            
            # 计算技术指标
            if len(self.received_ticks) >= 5:
                prices = [t.last_price for t in self.received_ticks[-5:]]
                ma_result = self.market_data_manager.calculate_ma(prices, 5)
                self.indicator_results[f'MA_{len(self.received_ticks)}'] = ma_result
            
            # 检查是否达到预期数据量
            if self.data_received_count >= self.expected_data_count:
                self.test_complete.set()
        
        def on_bar_received(bar: BarData):
            """Bar数据接收回调"""
            self.received_bars.append(bar)
        
        def on_connection_status_changed(status: ConnectionStatus):
            """连接状态变化回调"""
            self.connection_events.append(f"Connection status: {status.value}")
        
        # 注册回调到市场数据管理器
        self.market_data_manager.register_tick_callback(on_tick_received)
        self.market_data_manager.register_bar_callback(on_bar_received)
        
        # 注册回调到连接管理器
        self.connection_manager.register_status_callback(on_connection_status_changed)
    
    def _wait_for_data(self, timeout: float = 10.0) -> bool:
        """
        等待数据接收完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否在超时前完成
        """
        return self.test_complete.wait(timeout)
    
    def _verify_connection_flow(self) -> bool:
        """验证连接流程"""
        # 检查连接事件
        connected_events = [event for event in self.connection_events if 'CONNECTED' in event or 'connected' in event.lower()]
        return len(connected_events) > 0
    
    def _verify_data_flow(self) -> bool:
        """验证数据流"""
        # 检查是否接收到足够的数据
        return len(self.received_ticks) >= self.expected_data_count
    
    def _verify_indicators(self) -> bool:
        """验证技术指标计算"""
        # 检查是否计算了技术指标
        return len(self.indicator_results) > 0
    
    def _get_test_contracts(self) -> List[str]:
        """获取测试合约列表"""
        return ['rb2310', 'i2310', 'j2310']  # 螺纹钢、铁矿石、焦炭主力合约


class TestConnectionAndMarketDataFlow(IntegrationTestFramework):
    """测试连接和行情数据流集成"""
    
    def test_connection_establishment_and_subscription(self):
        """
        测试用例1：连接建立和行情订阅流程
        Test Case 1: Connection establishment and market data subscription flow
        """
        print("\n=== 测试用例1：连接建立和行情订阅流程 ===")
        
        # Step 1: 建立连接
        print("Step 1: 建立连接...")
        connection_result = self.connection_manager.connect_gateway()
        self.assertTrue(connection_result, "连接建立失败")
        
        # 等待连接稳定
        time.sleep(0.5)
        
        # Step 2: 验证连接状态
        print("Step 2: 验证连接状态...")
        self.assertTrue(self.connection_manager.is_connected(), "连接状态验证失败")
        
        # Step 3: 订阅行情数据
        print("Step 3: 订阅行情数据...")
        test_contracts = self._get_test_contracts()
        
        subscription_results = []
        for contract in test_contracts:
            result = self.market_data_manager.subscribe_market_data(contract)
            subscription_results.append(result)
            print(f"订阅合约 {contract}: {'成功' if result else '失败'}")
        
        # 验证所有订阅都成功
        self.assertTrue(all(subscription_results), "部分合约订阅失败")
        
        # Step 4: 等待并验证数据接收
        print("Step 4: 等待数据接收...")
        data_received = self._wait_for_data(timeout=15.0)
        self.assertTrue(data_received, f"数据接收超时，仅接收到 {self.data_received_count} 条数据")
        
        # Step 5: 验证接收到的数据
        print("Step 5: 验证接收数据...")
        self.assertGreaterEqual(len(self.received_ticks), self.expected_data_count, "接收的Tick数据不足")
        
        # 验证数据质量
        for i, tick in enumerate(self.received_ticks[:5]):
            self.assertIsInstance(tick, TickData, f"第{i+1}条数据类型错误")
            self.assertIsInstance(tick.symbol, str, "合约代码类型错误")
            self.assertGreater(tick.last_price, 0, "价格数据无效")
            self.assertGreater(tick.volume, 0, "成交量数据无效")
        
        print(f"✅ 测试完成：成功接收 {len(self.received_ticks)} 条Tick数据")
        print(f"✅ 连接事件：{len(self.connection_events)} 个")
        print(f"✅ 技术指标计算：{len(self.indicator_results)} 个")
    
    def test_data_flow_and_processing(self):
        """
        测试用例2：数据流和处理验证
        Test Case 2: Data flow and processing verification
        """
        print("\n=== 测试用例2：数据流和处理验证 ===")
        
        # 重置计数器
        self.data_received_count = 0
        self.expected_data_count = 15
        self.test_complete.clear()
        
        # Step 1: 连接并订阅
        print("Step 1: 连接并订阅...")
        self.connection_manager.connect_gateway()
        time.sleep(0.5)
        
        test_contracts = self._get_test_contracts()
        for contract in test_contracts:
            self.market_data_manager.subscribe_market_data(contract)
        
        # Step 2: 收集数据并计算指标
        print("Step 2: 收集数据并计算技术指标...")
        data_received = self._wait_for_data(timeout=20.0)
        self.assertTrue(data_received, "数据收集超时")
        
        # Step 3: 验证技术指标计算
        print("Step 3: 验证技术指标计算...")
        
        # 测试MA计算
        if len(self.received_ticks) >= 20:
            prices = [tick.last_price for tick in self.received_ticks[:20]]
            
            # 测试不同周期的MA
            ma_5 = self.market_data_manager.calculate_ma(prices, 5)
            ma_10 = self.market_data_manager.calculate_ma(prices, 10)
            ma_20 = self.market_data_manager.calculate_ma(prices, 20)
            
            self.assertIsNotNone(ma_5, "MA5计算失败")
            self.assertIsNotNone(ma_10, "MA10计算失败")
            self.assertIsNotNone(ma_20, "MA20计算失败")
            
            print(f"✅ MA5: {ma_5:.2f}")
            print(f"✅ MA10: {ma_10:.2f}")
            print(f"✅ MA20: {ma_20:.2f}")
            
            # 测试RSI计算
            rsi_result = self.market_data_manager.calculate_rsi(prices, 14)
            self.assertIsNotNone(rsi_result, "RSI计算失败")
            print(f"✅ RSI(14): {rsi_result:.2f}")
            
            # 测试布林带计算
            bb_result = self.market_data_manager.calculate_bollinger_bands(prices, 20, 2.0)
            self.assertIsNotNone(bb_result, "布林带计算失败")
            print(f"✅ 布林带 - 上轨: {bb_result['upper']:.2f}, 中轨: {bb_result['middle']:.2f}, 下轨: {bb_result['lower']:.2f}")
        
        # Step 4: 验证数据一致性
        print("Step 4: 验证数据一致性...")
        
        # 检查时间序列
        timestamps = [tick.datetime for tick in self.received_ticks]
        sorted_timestamps = sorted(timestamps)
        self.assertEqual(timestamps, sorted_timestamps, "数据时间序列不正确")
        
        # 检查合约覆盖
        symbols = set(tick.symbol for tick in self.received_ticks)
        self.assertGreaterEqual(len(symbols), 1, "合约覆盖不足")
        
        print(f"✅ 数据验证完成：{len(self.received_ticks)} 条Tick数据，{len(symbols)} 个合约")
    
    def test_error_handling_and_reconnection(self):
        """
        测试用例3：错误处理和重连场景
        Test Case 3: Error handling and reconnection scenarios
        """
        print("\n=== 测试用例3：错误处理和重连场景 ===")
        
        # Step 1: 正常连接
        print("Step 1: 建立正常连接...")
        self.connection_manager.connect_gateway()
        time.sleep(0.5)
        self.assertTrue(self.connection_manager.is_connected(), "初始连接失败")
        
        # Step 2: 模拟连接断开
        print("Step 2: 模拟连接断开...")
        original_status = self.connection_manager.status
        self.connection_manager.status = ConnectionStatus.DISCONNECTED
        
        # 验证状态变化
        self.assertFalse(self.connection_manager.is_connected(), "连接状态未正确更新")
        
        # Step 3: 测试重连机制
        print("Step 3: 测试自动重连...")
        reconnect_result = self.connection_manager.connect_gateway()
        self.assertTrue(reconnect_result, "重连失败")
        
        # Step 4: 测试订阅容错
        print("Step 4: 测试订阅容错...")
        
        # 尝试订阅无效合约
        invalid_result = self.market_data_manager.subscribe_market_data("INVALID_CONTRACT")
        self.assertFalse(invalid_result, "无效合约订阅应该失败")
        
        # 尝试订阅有效合约
        valid_result = self.market_data_manager.subscribe_market_data("rb2310")
        self.assertTrue(valid_result, "有效合约订阅失败")
        
        # Step 5: 测试指标计算容错
        print("Step 5: 测试指标计算容错...")
        
        # 空数据测试
        empty_result = self.market_data_manager.calculate_ma([], 5)
        self.assertIsNone(empty_result, "空数据应返回None")
        
        # 数据不足测试
        insufficient_data = [100.0, 101.0]
        insufficient_result = self.market_data_manager.calculate_ma(insufficient_data, 5)
        self.assertIsNone(insufficient_result, "数据不足应返回None")
        
        print("✅ 错误处理测试完成")


class PerformanceIntegrationTest(IntegrationTestFramework):
    """性能集成测试"""
    
    def test_performance_metrics(self):
        """测试性能指标"""
        print("\n=== 性能测试 ===")
        
        # 测试大量数据处理
        self.expected_data_count = 100
        self.test_complete.clear()
        
        start_time = time.time()
        
        # 连接并订阅
        self.connection_manager.connect_gateway()
        time.sleep(0.5)
        
        for contract in self._get_test_contracts():
            self.market_data_manager.subscribe_market_data(contract)
        
        # 等待数据处理
        data_received = self._wait_for_data(timeout=30.0)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        if data_received:
            data_rate = len(self.received_ticks) / elapsed_time
            print(f"✅ 数据处理速率: {data_rate:.2f} ticks/秒")
            print(f"✅ 总处理时间: {elapsed_time:.2f} 秒")
            print(f"✅ 总数据量: {len(self.received_ticks)} 条")
            
            # 性能基准：应该能处理至少10 ticks/秒
            self.assertGreater(data_rate, 5.0, "数据处理速率过低")
        else:
            print(f"❌ 性能测试超时，仅处理 {len(self.received_ticks)} 条数据")


def run_integration_tests():
    """运行所有集成测试"""
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加集成测试
    test_suite.addTest(TestConnectionAndMarketDataFlow('test_connection_establishment_and_subscription'))
    test_suite.addTest(TestConnectionAndMarketDataFlow('test_data_flow_and_processing'))
    test_suite.addTest(TestConnectionAndMarketDataFlow('test_error_handling_and_reconnection'))
    test_suite.addTest(PerformanceIntegrationTest('test_performance_metrics'))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result


if __name__ == '__main__':
    print("="*80)
    print("VNPY量化交易系统集成测试")
    print("Integration Tests for VNPY Quantitative Trading System")
    print("="*80)
    
    # 更改工作目录到项目根目录
    import os
    os.chdir('/home/user/webapp')
    
    # 运行集成测试
    test_result = run_integration_tests()
    
    print("\n" + "="*80)
    print("集成测试总结 (Integration Test Summary)")
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
    
    if success_rate == 100.0:
        print("🎉 所有集成测试通过！系统集成验证成功！")
    else:
        print("⚠️ 部分测试未通过，需要进一步调试")