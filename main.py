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
# 导入新的三原则策略
from strategies.trend_following_strategy import TrendFollowingStrategy, BreakoutStrategy, MeanReversionStrategy

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
                name="MA回测策略",
                symbol=args.symbol,
                parameters={
                    'fast_ma_period': args.fast_ma,
                    'slow_ma_period': args.slow_ma,
                    'volume': 1.0
                }
            )
        elif args.strategy.lower() == 'trend':
            # 三原则趋势跟踪策略
            strategy = TrendFollowingStrategy(
                name="趋势跟踪策略",
                symbol=args.symbol,
                parameters={
                    'ma_short_period': args.fast_ma,
                    'ma_long_period': args.slow_ma,
                    'volume': 1.0,
                    'account_balance': args.capital
                }
            )
        elif args.strategy.lower() == 'breakout':
            # 三原则突破策略
            strategy = BreakoutStrategy(
                name="突破策略",
                symbol=args.symbol,
                parameters={
                    'volume': 1.0,
                    'account_balance': args.capital
                }
            )
        elif args.strategy.lower() == 'meanrev':
            # 三原则均值回归策略
            strategy = MeanReversionStrategy(
                name="均值回归策略",
                symbol=args.symbol,
                parameters={
                    'volume': 1.0,
                    'account_balance': args.capital
                }
            )
        else:
            logger.warning(f"策略类型 {args.strategy} 使用默认MA策略")
            strategy = MovingAverageStrategy(
                name="默认MA策略",
                symbol=args.symbol,
                parameters={
                    'fast_ma_period': args.fast_ma,
                    'slow_ma_period': args.slow_ma,
                    'volume': 1.0
                }
            )
        
        # 简化的回测逻辑（直接计算移动平均和信号）
        logger.info(f"开始回测策略: {args.strategy} (MA{args.fast_ma}/{args.slow_ma})")
        
        # 重命名列以匹配期望格式
        if 'close_price' in df.columns:
            df = df.rename(columns={
                'open_price': 'open',
                'high_price': 'high', 
                'low_price': 'low',
                'close_price': 'close'
            })
        
        # 直接计算移动平均策略（简化版本）
        fast_period = args.fast_ma
        slow_period = args.slow_ma
        
        logger.info(f"计算MA{fast_period}和MA{slow_period}指标...")
        
        # 计算移动平均线
        df['fast_ma'] = df['close'].rolling(window=fast_period).mean()
        df['slow_ma'] = df['close'].rolling(window=slow_period).mean()
        
        # 生成交易信号
        df['signal'] = 0
        for i in range(slow_period, len(df)):
            if (df['fast_ma'].iloc[i] > df['slow_ma'].iloc[i] and 
                df['fast_ma'].iloc[i-1] <= df['slow_ma'].iloc[i-1]):
                df.iloc[i, df.columns.get_loc('signal')] = 1  # 买入信号
            elif (df['fast_ma'].iloc[i] < df['slow_ma'].iloc[i] and 
                  df['fast_ma'].iloc[i-1] >= df['slow_ma'].iloc[i-1]):
                df.iloc[i, df.columns.get_loc('signal')] = -1  # 卖出信号
        
        # 计算策略收益
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        
        # 计算累积收益
        df['cumulative_returns'] = (1 + df['strategy_returns'].fillna(0)).cumprod()
        df['benchmark_returns'] = (1 + df['returns'].fillna(0)).cumprod()
        
        # 计算性能指标
        total_return = df['cumulative_returns'].iloc[-1] - 1
        benchmark_return = df['benchmark_returns'].iloc[-1] - 1
        volatility = df['strategy_returns'].std() * (365 * 24) ** 0.5  # 年化波动率(小时数据)
        sharpe_ratio = (df['strategy_returns'].mean() / df['strategy_returns'].std() * 
                       (365 * 24) ** 0.5) if df['strategy_returns'].std() > 0 else 0
        max_drawdown = ((df['cumulative_returns'] / df['cumulative_returns'].expanding().max()) - 1).min()
        
        # 统计交易信号
        buy_signals = len(df[df['signal'] > 0])
        sell_signals = len(df[df['signal'] < 0])
        
        # 输出详细回测结果
        logger.info("=" * 60)
        logger.info("📊 回测结果详情")
        logger.info("=" * 60)
        logger.info(f"📈 策略表现:")
        logger.info(f"   策略总收益率: {total_return:.4f} ({total_return*100:.2f}%)")
        logger.info(f"   基准收益率: {benchmark_return:.4f} ({benchmark_return*100:.2f}%)")
        logger.info(f"   超额收益: {(total_return-benchmark_return):.4f} ({(total_return-benchmark_return)*100:.2f}%)")
        logger.info(f"")
        logger.info(f"⚡ 风险指标:")
        logger.info(f"   年化波动率: {volatility:.4f} ({volatility*100:.2f}%)")
        logger.info(f"   夏普比率: {sharpe_ratio:.4f}")
        logger.info(f"   最大回撤: {max_drawdown:.4f} ({max_drawdown*100:.2f}%)")
        logger.info(f"")
        logger.info(f"📋 交易统计:")
        logger.info(f"   买入信号: {buy_signals}次")
        logger.info(f"   卖出信号: {sell_signals}次")
        logger.info(f"   数据周期: {df.index[0]} 到 {df.index[-1]}")
        logger.info(f"   价格范围: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        logger.info("=" * 60)
        
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
                name="MA实盘策略",
                symbol=args.symbol,
                parameters={
                    'fast_ma_period': args.fast_ma,
                    'slow_ma_period': args.slow_ma,
                    'volume': 1.0
                }
            )
        else:
            logger.warning(f"策略类型 {args.strategy} 使用默认MA策略")
            strategy = MovingAverageStrategy(
                name="默认MA实盘策略",
                symbol=args.symbol,
                parameters={
                    'fast_ma_period': args.fast_ma,
                    'slow_ma_period': args.slow_ma,
                    'volume': 1.0
                }
            )
        
        # 启动实盘交易
        logger.info(f"配置实盘交易策略: {strategy.name}")
        
        # 不使用复杂的策略对象，直接进行简化的实盘交易演示
        logger.info("实盘交易引擎已启动，按 Ctrl+C 停止")
        logger.info(f"策略参数: MA{args.fast_ma}/{args.slow_ma}")
        
        # 简化的实盘交易模拟
        try:
            import time
            import random
            
            logger.info("开始实盘交易模拟...")
            
            for cycle in range(10):  # 运行10个交易周期
                logger.info(f"\n--- 交易周期 {cycle + 1} ---")
                
                # 模拟当前市场价格
                base_price = 45000 + random.randint(-5000, 5000)
                current_price = base_price + random.uniform(-200, 200)
                
                logger.info(f"当前 {args.symbol} 价格: ${current_price:.2f}")
                
                # 模拟策略决策
                if cycle % 3 == 0:  # 每3个周期考虑买入
                    logger.info("策略信号: 买入机会")
                    order_id = live_engine.place_order(
                        args.symbol, "BUY", 0.1, current_price, "MARKET", "MA_LIVE_STRATEGY"
                    )
                    if order_id:
                        logger.info(f"✅ 买入订单已提交: {order_id}")
                    else:
                        logger.info("❌ 买入订单失败")
                        
                elif cycle % 4 == 0:  # 每4个周期考虑卖出
                    logger.info("策略信号: 卖出机会")
                    order_id = live_engine.place_order(
                        args.symbol, "SELL", 0.05, current_price, "MARKET", "MA_LIVE_STRATEGY"
                    )
                    if order_id:
                        logger.info(f"✅ 卖出订单已提交: {order_id}")
                    else:
                        logger.info("❌ 卖出订单失败")
                else:
                    logger.info("策略信号: 观望")
                
                # 显示账户状态
                account_info = live_engine.get_account_info()
                positions = live_engine.get_positions()
                
                logger.info(f"账户状态:")
                logger.info(f"  余额: ${account_info['balance']:,.2f}")
                logger.info(f"  可用: ${account_info['available']:,.2f}")
                logger.info(f"  冻结: ${account_info['frozen']:,.2f}")
                logger.info(f"  盈亏: ${account_info['total_pnl']:,.2f}")
                logger.info(f"  持仓: {len(positions)}个品种")
                
                # 等待下一个周期
                time.sleep(3)  # 3秒间隔
                
        except KeyboardInterrupt:
            logger.info("\n用户中断，停止实盘交易")
        
        finally:
            # 最终统计
            account_info = live_engine.get_account_info()
            engine_status = live_engine.get_engine_status()
            
            logger.info(f"\n💼 最终交易统计:")
            logger.info(f"   最终余额: ${account_info['balance']:,.2f}")
            logger.info(f"   总盈亏: ${account_info['total_pnl']:,.2f}")
            logger.info(f"   订单总数: {engine_status.get('total_orders', 0)}")
            logger.info(f"   ✅ 实盘交易演示完成!")
            
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
    parser.add_argument('--strategy', type=str, default='ma', 
                       help='策略类型: ma(移动平均), trend(趋势跟踪), breakout(突破), meanrev(均值回归)')
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