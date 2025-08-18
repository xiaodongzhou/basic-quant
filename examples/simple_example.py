"""
简单示例
演示如何使用移动平均策略
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from strategies.moving_average_strategy import MovingAverageStrategy
from datetime import datetime

def run_simple_backtest():
    """运行简单回测示例"""
    print("VN.PY量化交易系统 - 简单示例")
    print("="*50)
    
    # 创建策略
    strategy = MovingAverageStrategy(
        name="MA10_30_BTCUSDT",
        symbol="BTCUSDT",
        parameters={
            'fast_ma_period': 10,
            'slow_ma_period': 30,
            'volume': 1.0
        }
    )
    
    # 启动策略
    strategy.start()
    
    # 模拟一些K线数据
    sample_data = [
        {'datetime': datetime(2023, 1, 1), 'open_price': 16500, 'high_price': 16600, 'low_price': 16400, 'close_price': 16550, 'volume': 100},
        {'datetime': datetime(2023, 1, 2), 'open_price': 16550, 'high_price': 16700, 'low_price': 16500, 'close_price': 16650, 'volume': 120},
        {'datetime': datetime(2023, 1, 3), 'open_price': 16650, 'high_price': 16800, 'low_price': 16600, 'close_price': 16750, 'volume': 110},
        {'datetime': datetime(2023, 1, 4), 'open_price': 16750, 'high_price': 16900, 'low_price': 16700, 'close_price': 16850, 'volume': 130},
        {'datetime': datetime(2023, 1, 5), 'open_price': 16850, 'high_price': 17000, 'low_price': 16800, 'close_price': 16950, 'volume': 140},
    ]
    
    # 添加更多数据以满足均线计算需求
    for i in range(35):
        sample_data.append({
            'datetime': datetime(2023, 1, 6 + i),
            'open_price': 16950 + i * 10,
            'high_price': 17000 + i * 10,
            'low_price': 16900 + i * 10,
            'close_price': 16975 + i * 10,
            'volume': 100 + i
        })
    
    print(f"开始处理{len(sample_data)}条K线数据...")
    
    # 逐个添加K线数据
    for bar in sample_data:
        strategy.add_bar(bar)
    
    # 获取策略状态
    signals = strategy.get_current_signals()
    stats = strategy.get_performance_stats()
    
    print("\n策略运行结果:")
    print(f"当前趋势: {signals.get('trend', 'N/A')}")
    print(f"快线MA: {signals.get('fast_ma', 0):.2f}")
    print(f"慢线MA: {signals.get('slow_ma', 0):.2f}")
    print(f"最后信号: {signals.get('last_signal', 'N/A')}")
    
    print(f"\n策略统计:")
    print(f"策略名称: {stats['strategy_name']}")
    print(f"交易品种: {stats['symbol']}")
    print(f"总交易次数: {stats['total_trades']}")
    print(f"当前持仓: {stats['position_size']}")
    
    strategy.stop()
    print("\n示例运行完成!")

if __name__ == "__main__":
    run_simple_backtest()