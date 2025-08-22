"""
VN.PY量化交易系统主程序
整合回测、实盘交易、策略管理功能
"""
import sys
import argparse
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from datetime import datetime
from loguru import logger

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

# 导入系统模块
from data.data_manager import DataManager
from trading.live_engine import LiveEngine
from strategies.moving_average_strategy import MovingAverageStrategy
from strategies.base_strategy import BaseStrategy

def run_backtest(args):
    """运行回测"""
    try:
        # 初始化数据管理器
        data_manager = DataManager()
        logger.info(f"开始下载数据: {args.symbol} ({args.start} to {args.end})")
        
        # 下载数据
        df = data_manager.download_data(
            symbol=args.symbol,
            start_date=args.start,
            end_date=args.end,
            interval=args.interval,
            exchange=args.source
        )
        
        if df.empty:
            logger.error("未获取到数据，请检查参数设置")
            return
        
        logger.info(f"数据下载完成，共{len(df)}条记录")
        
        # 选择策略
        if args.strategy.lower() == 'ma':
            strategy = MovingAverageStrategy(
                fast_period=args.fast_ma,
                slow_period=args.slow_ma
            )
        else:
            logger.warning(f"策略类型 {args.strategy} 使用默认MA策略")
            strategy = MovingAverageStrategy(
                fast_period=args.fast_ma,
                slow_period=args.slow_ma
            )
        
        # 简单回测逻辑（由于BacktestEngine模块缺失，这里实现基本回测）
        logger.info(f"开始回测策略: {args.strategy}")
        
        # 初始化策略
        strategy.initialize(df)
        
        # 计算信号
        signals = []
        for i in range(len(df)):
            current_data = df.iloc[:i+1]
            signal = strategy.generate_signal(current_data.iloc[-1] if len(current_data) > 0 else None, current_data)
            signals.append(signal)
        
        df['signal'] = signals
        
        # 计算简单回报
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        
        total_return = (1 + df['strategy_returns'].fillna(0)).prod() - 1
        volatility = df['strategy_returns'].std() * (252 ** 0.5)  # 年化波动率
        sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * (252 ** 0.5) if df['strategy_returns'].std() > 0 else 0
        
        # 输出结果
        logger.info("=" * 50)
        logger.info("回测结果:")
        logger.info(f"总回报率: {total_return:.4f}")
        logger.info(f"年化波动率: {volatility:.4f}")
        logger.info(f"夏普比率: {sharpe_ratio:.4f}")
        logger.info(f"信号数量: {len([s for s in signals if s != 0])}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"回测执行出错: {e}")

def run_live_trading(args):
    """运行实盘交易"""
    try:
        logger.info(f"启动实盘交易模式 - {args.gateway}")
        
        # 初始化实盘交易引擎
        live_engine = LiveEngine(initial_balance=args.capital)
        
        # 选择策略
        if args.strategy.lower() == 'ma':
            strategy = MovingAverageStrategy(
                fast_period=args.fast_ma,
                slow_period=args.slow_ma
            )
        else:
            logger.warning(f"策略类型 {args.strategy} 使用默认MA策略")
            strategy = MovingAverageStrategy(
                fast_period=args.fast_ma,
                slow_period=args.slow_ma
            )
        
        # 启动实盘交易
        live_engine.start_trading([args.symbol], strategy)
        
        logger.info("实盘交易引擎已启动，按 Ctrl+C 停止")
        
        # 保持运行状态
        try:
            while True:
                # 显示实时状态
                account = live_engine.get_account()
                positions = live_engine.get_positions()
                
                logger.info(f"账户余额: {account.balance:.2f}, 可用资金: {account.available:.2f}")
                logger.info(f"总盈亏: {account.total_pnl:.2f}, 持仓数: {len(positions)}")
                
                import time
                time.sleep(30)  # 每30秒显示一次状态
                
        except KeyboardInterrupt:
            logger.info("用户中断，停止实盘交易")
            live_engine.stop_trading()
            
    except Exception as e:
        logger.error(f"实盘交易执行出错: {e}")

def download_data(args):
    """下载数据"""
    try:
        logger.info(f"开始下载数据: {args.symbol}")
        
        # 初始化数据管理器
        data_manager = DataManager()
        
        # 下载数据
        df = data_manager.download_data(
            symbol=args.symbol,
            start_date=args.start,
            end_date=args.end,
            interval=args.interval,
            exchange=args.source,
            force_update=True  # 强制更新
        )
        
        if not df.empty:
            logger.info(f"数据下载完成!")
            logger.info(f"时间范围: {df.index[0]} 到 {df.index[-1]}")
            logger.info(f"数据条数: {len(df)}")
            # 检查列名并使用正确的列
            if 'close_price' in df.columns:
                logger.info(f"最新价格: {df['close_price'].iloc[-1]:.4f}")
            elif 'close' in df.columns:
                logger.info(f"最新价格: {df['close'].iloc[-1]:.4f}")
            else:
                logger.info(f"可用列: {list(df.columns)}")
        else:
            logger.error("数据下载失败，请检查网络连接和参数设置")
            
    except Exception as e:
        logger.error(f"数据下载出错: {e}")

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description="VN.PY量化交易系统")
    parser.add_argument('mode', choices=['backtest', 'live', 'data'], 
                       help='运行模式: backtest(回测), live(实盘), data(数据下载)')
    
    # 回测参数
    parser.add_argument('--strategy', type=str, default='bb', 
                       help='策略类型: ma, rsi, bb')
    parser.add_argument('--symbol', type=str, default='BTCUSDT',
                       help='交易品种')
    parser.add_argument('--start', type=str, default='2023-01-01',
                       help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2023-12-31',
                       help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=100000,
                       help='初始资金')
    
    # 实盘参数
    parser.add_argument('--gateway', type=str, default='BINANCE',
                       help='交易接口: BINANCE, CTP')
    
    # 数据参数
    parser.add_argument('--source', type=str, default='BINANCE',
                       help='数据源: BINANCE, YAHOO')
    parser.add_argument('--interval', type=str, default='1h',
                       help='数据间隔: 1m, 5m, 15m, 1h, 4h, 1d')
    
    # 策略参数
    parser.add_argument('--fast-ma', type=int, default=10,
                       help='快速均线周期')
    parser.add_argument('--slow-ma', type=int, default=30,
                       help='慢速均线周期')
    
    args = parser.parse_args()
    
    # 配置日志
    logger.add("logs/trading_{time}.log", rotation="1 day", retention="30 days")
    
    logger.info("=" * 60)
    logger.info(f"VN.PY量化交易系统 - {args.mode.upper()}模式")
    logger.info(f"策略: {args.strategy.upper()}, 品种: {args.symbol}")
    logger.info(f"时间范围: {args.start} 到 {args.end}")
    logger.info(f"数据间隔: {args.interval}, 初始资金: {args.capital:,.2f}")
    logger.info("=" * 60)
    
    # 创建必要的目录
    Path("logs").mkdir(exist_ok=True)
    Path("data/database").mkdir(parents=True, exist_ok=True)
    
    try:
        if args.mode == 'backtest':
            run_backtest(args)
            
        elif args.mode == 'live':
            run_live_trading(args)
            
        elif args.mode == 'data':
            download_data(args)
            
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        raise

if __name__ == "__main__":
    main()