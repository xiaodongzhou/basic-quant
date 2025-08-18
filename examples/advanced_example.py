"""
高级示例
演示如何使用回测引擎和多种策略
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from strategies.moving_average_strategy import MovingAverageStrategy
from strategies.rsi_strategy import RSIStrategy
from backtest.simple_backtest import run_simple_backtest
import numpy as np


def generate_sample_data(days: int = 100, start_price: float = 16500) -> list:
    """生成模拟价格数据"""
    data = []
    current_price = start_price
    start_date = datetime(2023, 1, 1)
    
    for i in range(days):
        # 简单的随机游走价格
        change = np.random.normal(0, 0.02)  # 2%的标准差
        current_price *= (1 + change)
        
        # 确保价格合理
        current_price = max(current_price, start_price * 0.5)
        current_price = min(current_price, start_price * 2.0)
        
        # 生成OHLC数据
        high = current_price * (1 + abs(np.random.normal(0, 0.01)))
        low = current_price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = current_price * (1 + np.random.normal(0, 0.005))
        
        bar = {
            'datetime': start_date + timedelta(days=i),
            'open_price': open_price,
            'high_price': high,
            'low_price': low,
            'close_price': current_price,
            'volume': np.random.randint(100, 1000)
        }
        
        data.append(bar)
    
    return data


def run_strategy_comparison():
    """运行策略对比测试"""
    print("VN.PY量化交易系统 - 高级示例")
    print("="*60)
    
    # 生成测试数据
    print("生成模拟数据...")
    sample_data = generate_sample_data(days=200, start_price=16500)
    print(f"生成了{len(sample_data)}条数据，时间范围: {sample_data[0]['datetime']} 到 {sample_data[-1]['datetime']}")
    
    # 创建不同策略
    strategies = [
        MovingAverageStrategy(
            name="MA_5_20",
            symbol="BTCUSDT",
            parameters={'fast_ma_period': 5, 'slow_ma_period': 20, 'volume': 1.0}
        ),
        MovingAverageStrategy(
            name="MA_10_30",
            symbol="BTCUSDT", 
            parameters={'fast_ma_period': 10, 'slow_ma_period': 30, 'volume': 1.0}
        ),
        RSIStrategy(
            name="RSI_14",
            symbol="BTCUSDT",
            parameters={'rsi_period': 14, 'oversold': 30, 'overbought': 70, 'volume': 1.0}
        ),
        RSIStrategy(
            name="RSI_21",
            symbol="BTCUSDT",
            parameters={'rsi_period': 21, 'oversold': 25, 'overbought': 75, 'volume': 1.0}
        )
    ]
    
    print(f"\n开始测试{len(strategies)}个策略...")
    print("="*60)
    
    results = {}
    
    # 逐个测试策略
    for strategy in strategies:
        print(f"\n测试策略: {strategy.name}")
        print("-" * 40)
        
        try:
            result = run_simple_backtest(strategy, sample_data, initial_capital=100000)
            results[strategy.name] = result
            
            # 打印结果
            print(f"总收益率: {result.get('total_return_pct', 0):.2f}%")
            print(f"最大回撤: {result.get('max_drawdown_pct', 0):.2f}%")
            print(f"夏普比率: {result.get('sharpe_ratio', 0):.3f}")
            print(f"交易次数: {result.get('total_trades', 0)}")
            print(f"胜率: {result.get('win_rate_pct', 0):.2f}%")
            print(f"最终资金: {result.get('final_capital', 0):,.2f}")
            
        except Exception as e:
            print(f"策略测试失败: {e}")
            results[strategy.name] = None
    
    # 对比结果
    print("\n" + "="*60)
    print("策略对比结果")
    print("="*60)
    
    valid_results = {k: v for k, v in results.items() if v is not None}
    
    if valid_results:
        print(f"{'策略名称':<15} {'收益率(%)':<10} {'回撤(%)':<10} {'夏普比':<8} {'交易次数':<8} {'胜率(%)':<8}")
        print("-" * 70)
        
        for name, result in valid_results.items():
            print(f"{name:<15} {result.get('total_return_pct', 0):<10.2f} "
                  f"{result.get('max_drawdown_pct', 0):<10.2f} "
                  f"{result.get('sharpe_ratio', 0):<8.3f} "
                  f"{result.get('total_trades', 0):<8} "
                  f"{result.get('win_rate_pct', 0):<8.2f}")
        
        # 找出最佳策略
        best_strategy = max(valid_results.items(), 
                          key=lambda x: x[1].get('sharpe_ratio', 0))
        
        print(f"\n最佳策略（按夏普比率）: {best_strategy[0]}")
        print(f"夏普比率: {best_strategy[1].get('sharpe_ratio', 0):.3f}")
        print(f"总收益率: {best_strategy[1].get('total_return_pct', 0):.2f}%")
        
    else:
        print("所有策略测试失败")
    
    print("\n高级示例运行完成!")


def test_single_strategy_detailed():
    """详细测试单个策略"""
    print("\n" + "="*60)
    print("单策略详细测试")
    print("="*60)
    
    # 生成数据
    data = generate_sample_data(days=150, start_price=17000)
    
    # 创建策略
    strategy = MovingAverageStrategy(
        name="MA_Detail_Test",
        symbol="BTCUSDT",
        parameters={
            'fast_ma_period': 8,
            'slow_ma_period': 21,
            'volume': 2.0  # 加大交易量
        }
    )
    
    print(f"策略参数: 快线={strategy.get_parameter('fast_ma_period')}, "
          f"慢线={strategy.get_parameter('slow_ma_period')}")
    
    # 运行回测
    result = run_simple_backtest(strategy, data, initial_capital=50000)
    
    # 详细结果
    print(f"\n详细回测结果:")
    print(f"回测期间: {result.get('start_date')} 到 {result.get('end_date')}")
    print(f"初始资金: {result.get('initial_capital', 0):,.2f}")
    print(f"最终资金: {result.get('final_capital', 0):,.2f}")
    print(f"绝对收益: {result.get('final_capital', 0) - result.get('initial_capital', 0):,.2f}")
    print(f"收益率: {result.get('total_return_pct', 0):.2f}%")
    print(f"最大回撤: {result.get('max_drawdown_pct', 0):.2f}%")
    print(f"夏普比率: {result.get('sharpe_ratio', 0):.3f}")
    print(f"总交易次数: {result.get('total_trades', 0)}")
    print(f"盈利交易: {result.get('winning_trades', 0)}")
    print(f"胜率: {result.get('win_rate_pct', 0):.2f}%")
    
    # 显示部分交易记录
    trades = result.get('trades', [])
    if trades:
        print(f"\n前5笔交易记录:")
        for i, trade in enumerate(trades[:5]):
            print(f"{i+1}. {trade['timestamp'].strftime('%Y-%m-%d')} "
                  f"{trade['direction']} {trade['volume']}@{trade['price']:.2f}")


if __name__ == "__main__":
    try:
        # 运行策略对比
        run_strategy_comparison()
        
        # 运行详细测试
        test_single_strategy_detailed()
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序执行失败: {e}")
        import traceback
        traceback.print_exc()