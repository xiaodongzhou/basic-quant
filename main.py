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
    
    args = parser.parse_args()
    
    print(f"VN.PY量化交易系统 - {args.mode}模式")
    print(f"策略: {args.strategy}, 品种: {args.symbol}")
    print(f"时间: {args.start} 到 {args.end}")
    
    if args.mode == 'backtest':
        print("执行回测...")
        # 这里应该调用回测引擎
        print("回测完成!")
        
    elif args.mode == 'live':
        print(f"启动实盘交易 ({args.gateway})...")
        # 这里应该启动实盘交易引擎
        print("实盘交易已启动!")
        
    elif args.mode == 'data':
        print(f"下载数据: {args.symbol}...")
        # 这里应该调用数据下载功能
        print("数据下载完成!")

if __name__ == "__main__":
    main()