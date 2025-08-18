"""
策略测试文件
"""
import sys
from pathlib import Path
import unittest
from datetime import datetime

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from strategies import MovingAverageStrategy, RSIStrategy
from utils.data_generator import generate_test_data


class TestStrategies(unittest.TestCase):
    """策略测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_data = generate_test_data("random", days=50, start_price=100)
    
    def test_moving_average_strategy(self):
        """测试移动平均策略"""
        strategy = MovingAverageStrategy(
            name="Test_MA",
            symbol="TEST",
            parameters={'fast_ma_period': 5, 'slow_ma_period': 10}
        )
        
        # 测试策略初始化
        self.assertEqual(strategy.name, "Test_MA")
        self.assertEqual(strategy.symbol, "TEST")
        self.assertEqual(strategy.get_parameter('fast_ma_period'), 5)
        
        # 测试添加数据
        strategy.start()
        for bar in self.test_data:
            strategy.add_bar(bar)
        
        # 验证策略状态
        self.assertTrue(strategy.active)
        self.assertEqual(len(strategy.bars), len(self.test_data))
        strategy.stop()
    
    def test_rsi_strategy(self):
        """测试RSI策略"""
        strategy = RSIStrategy(
            name="Test_RSI",
            symbol="TEST",
            parameters={'rsi_period': 14, 'oversold': 30, 'overbought': 70}
        )
        
        # 测试策略初始化
        self.assertEqual(strategy.name, "Test_RSI")
        self.assertEqual(strategy.get_parameter('rsi_period'), 14)
        
        # 测试添加数据
        strategy.start()
        for bar in self.test_data:
            strategy.add_bar(bar)
        
        # 验证RSI计算
        if len(strategy.bars) > 20:  # 确保有足够数据计算RSI
            rsi_value = strategy.get_indicator_value('rsi')
            if rsi_value is not None:
                self.assertGreaterEqual(rsi_value, 0)
                self.assertLessEqual(rsi_value, 100)
        
        strategy.stop()
    
    def test_strategy_reset(self):
        """测试策略重置功能"""
        strategy = MovingAverageStrategy("Test", "TEST")
        
        # 添加一些数据
        for bar in self.test_data[:10]:
            strategy.add_bar(bar)
        
        # 验证有数据
        self.assertGreater(len(strategy.bars), 0)
        
        # 重置策略
        strategy.reset()
        
        # 验证重置后状态
        self.assertEqual(len(strategy.bars), 0)
        self.assertTrue(strategy.bar_df.empty)
        self.assertEqual(strategy.total_trades, 0)


if __name__ == '__main__':
    unittest.main()