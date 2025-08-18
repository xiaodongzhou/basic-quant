"""
VN.PY量化交易系统主程序
整合回测、实盘交易、策略管理功能
"""
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description="VN.PY量化交易系统")
    parser.add_argument('mode', choices=['backtest', 'live', 'data'], 
                       help='运行模式: backtest(回测), live(实盘), data(数据下载)')
    
    # 回测参数
    parser.add_argument('--strategy', type=str, default='ma', 
                       help='策略类型: ma, rsi, bb')
    parser.add_argument('--symbol', type=str, default='BTCUSDT',
                       help='交易品种')
    parser.add_argument('--start', type=str, default='2023-01-01',
                       help='开始日期')
    parser.add_argument('--end', type=str, default='2023-12-31',
                       help='结束日期')
    parser.add_argument('--capital', type=float, default=1000000,
                       help='初始资金')
    
    # 实盘参数
    parser.add_argument('--gateway', type=str, default='BINANCE',
                       help='交易接口: BINANCE, CTP')
    
    # 数据参数
    parser.add_argument('--source', type=str, default='BINANCE',
                       help='数据源: BINANCE, YAHOO')
    parser.add_argument('--interval', type=str, default='1m',
                       help='数据间隔: 1m, 5m, 1h, 1d')
    
    # 策略参数
    parser.add_argument('--fast-ma', type=int, default=10,
                       help='快速均线周期')
    parser.add_argument('--slow-ma', type=int, default=30,
                       help='慢速均线周期')
    parser.add_argument('--rsi-period', type=int, default=14,
                       help='RSI周期')
    
    args = parser.parse_args()
    
    print(f"VN.PY量化交易系统 - {args.mode}模式")
    print(f"策略: {args.strategy}, 品种: {args.symbol}")
    print(f"时间: {args.start} 到 {args.end}")
    
    if args.mode == 'backtest':
        print("执行回测...")
        try:
            from strategies import MovingAverageStrategy, RSIStrategy
            from backtest import run_simple_backtest
            from utils.data_generator import generate_test_data
            
            # 生成测试数据
            data = generate_test_data("mixed", days=100, start_price=16500)
            
            # 创建策略
            if args.strategy == 'ma':
                strategy = MovingAverageStrategy(
                    name=f"MA_{args.fast_ma}_{args.slow_ma}",
                    symbol=args.symbol,
                    parameters={'fast_ma_period': args.fast_ma, 'slow_ma_period': args.slow_ma}
                )
            elif args.strategy == 'rsi':
                strategy = RSIStrategy(
                    name="RSI_Strategy",
                    symbol=args.symbol,
                    parameters={'rsi_period': 14, 'oversold': 30, 'overbought': 70}
                )
            else:
                print(f"不支持的策略类型: {args.strategy}")
                return
            
            # 运行回测
            result = run_simple_backtest(strategy, data, args.capital)
            
            # 显示结果
            print(f"回测结果:")
            print(f"总收益率: {result.get('total_return_pct', 0):.2f}%")
            print(f"最大回撤: {result.get('max_drawdown_pct', 0):.2f}%")
            print(f"夏普比率: {result.get('sharpe_ratio', 0):.3f}")
            print(f"交易次数: {result.get('total_trades', 0)}")
            
        except ImportError as e:
            print(f"模块导入错误: {e}")
        except Exception as e:
            print(f"回测执行错误: {e}")
        
    elif args.mode == 'live':
        print(f"启动实盘交易 ({args.gateway})...")
        print("实盘交易功能尚未完全实现，请参考示例代码")
        
    elif args.mode == 'data':
        print(f"生成模拟数据: {args.symbol}...")
        try:
            from utils.data_generator import generate_test_data
            
            data = generate_test_data("mixed", days=200, start_price=16500)
            print(f"生成了{len(data)}条模拟数据")
            print(f"时间范围: {data[0]['datetime']} 到 {data[-1]['datetime']}")
            print(f"价格范围: {data[0]['close_price']:.2f} 到 {data[-1]['close_price']:.2f}")
            
        except Exception as e:
            print(f"数据生成错误: {e}")

if __name__ == "__main__":
    main()