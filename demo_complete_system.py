#!/usr/bin/env python3
"""
完整量化交易系统演示
展示数据管理、策略回测、实盘交易模拟的完整流程
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import time

# 导入我们的模块
from data.data_manager import DataManager
from trading.live_engine import LiveEngine
from strategies.moving_average_strategy import MovingAverageStrategy

def generate_demo_data(symbol: str, days: int = 30) -> pd.DataFrame:
    """生成演示用的模拟市场数据"""
    logger.info(f"生成{days}天的{symbol}模拟数据")
    
    # 生成时间序列
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_range = pd.date_range(start=start_date, end=end_date, freq='1H')
    
    # 模拟价格数据（布朗运动）
    np.random.seed(42)  # 确保结果可重现
    n_periods = len(date_range)
    
    # 初始价格
    base_price = 50000  # BTC基准价格
    
    # 生成价格序列（几何布朗运动）
    returns = np.random.normal(0.0001, 0.02, n_periods)  # 小的正期望回报，2%的波动率
    prices = [base_price]
    
    for i in range(1, n_periods):
        new_price = prices[-1] * (1 + returns[i])
        prices.append(new_price)
    
    # 生成OHLC数据
    data = []
    for i, (timestamp, close) in enumerate(zip(date_range, prices)):
        # 模拟开高低收
        noise = abs(np.random.normal(0, close * 0.005))  # 0.5%的价格噪声
        high = close + noise
        low = close - noise
        open_price = prices[i-1] if i > 0 else close
        
        # 确保价格关系合理
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        volume = np.random.uniform(1000, 10000)  # 随机成交量
        
        data.append({
            'datetime': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)
    
    logger.info(f"生成了{len(df)}条数据记录")
    logger.info(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
    
    return df

def demo_data_management():
    """演示数据管理功能"""
    logger.info("=" * 60)
    logger.info("1. 数据管理功能演示")
    logger.info("=" * 60)
    
    # 生成模拟数据
    demo_data = generate_demo_data("BTCUSDT", days=7)
    
    # 初始化数据管理器
    data_manager = DataManager()
    
    # 存储数据到数据库
    logger.info("存储数据到数据库...")
    # 将DataFrame转换为字典列表格式
    bars_data = []
    for timestamp, row in demo_data.iterrows():
        bars_data.append({
            "symbol": "BTCUSDT",
            "exchange": "DEMO",
            "datetime": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "interval": "1h",
            "open_price": row['open'],
            "high_price": row['high'],
            "low_price": row['low'],
            "close_price": row['close'],
            "volume": row['volume'],
            "turnover": 0,
            "open_interest": 0
        })
    
    data_manager.db_manager.save_bars(bars_data)
    
    # 从数据库读取数据
    logger.info("从数据库读取数据...")
    retrieved_data = data_manager.db_manager.load_bars(
        "BTCUSDT", "DEMO", 
        demo_data.index[0].strftime('%Y-%m-%d %H:%M:%S'),
        demo_data.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
        "1h"
    )
    
    logger.info(f"成功从数据库读取{len(retrieved_data)}条记录")
    logger.info(f"数据时间范围: {retrieved_data.index[0]} 到 {retrieved_data.index[-1]}")
    logger.info(f"数据列名: {list(retrieved_data.columns)}")
    
    # 重命名列以匹配期望的格式
    if 'close_price' in retrieved_data.columns:
        retrieved_data = retrieved_data.rename(columns={
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close'
        })
    
    return retrieved_data

def demo_strategy_backtest(data: pd.DataFrame):
    """演示策略回测功能"""
    logger.info("=" * 60)
    logger.info("2. 策略回测功能演示")
    logger.info("=" * 60)
    
    logger.info("计算移动平均策略信号...")
    
    # 手动计算移动平均指标和信号（简化版）
    fast_period = 5
    slow_period = 20
    
    # 计算移动平均线
    data = data.copy()
    data['fast_ma'] = data['close'].rolling(window=fast_period).mean()
    data['slow_ma'] = data['close'].rolling(window=slow_period).mean()
    
    # 生成交易信号
    # 1: 买入信号 (快线上穿慢线)
    # -1: 卖出信号 (快线下穿慢线)
    # 0: 无信号
    data['signal'] = 0
    
    for i in range(slow_period, len(data)):
        if (data['fast_ma'].iloc[i] > data['slow_ma'].iloc[i] and 
            data['fast_ma'].iloc[i-1] <= data['slow_ma'].iloc[i-1]):
            data.iloc[i, data.columns.get_loc('signal')] = 1  # 买入信号
        elif (data['fast_ma'].iloc[i] < data['slow_ma'].iloc[i] and 
              data['fast_ma'].iloc[i-1] >= data['slow_ma'].iloc[i-1]):
            data.iloc[i, data.columns.get_loc('signal')] = -1  # 卖出信号
    
    # 计算策略收益率
    data['returns'] = data['close'].pct_change()
    data['strategy_returns'] = data['signal'].shift(1) * data['returns']
    data['cumulative_returns'] = (1 + data['strategy_returns'].fillna(0)).cumprod()
    
    # 计算性能指标
    total_return = data['cumulative_returns'].iloc[-1] - 1
    volatility = data['strategy_returns'].std() * np.sqrt(24 * 365)  # 年化波动率（假设小时数据）
    sharpe_ratio = data['strategy_returns'].mean() / data['strategy_returns'].std() * np.sqrt(24 * 365) if data['strategy_returns'].std() > 0 else 0
    
    max_drawdown = ((data['cumulative_returns'] / data['cumulative_returns'].expanding().max()) - 1).min()
    
    # 输出回测结果
    logger.info("回测结果:")
    logger.info(f"数据范围: {data.index[0]} 到 {data.index[-1]}")
    logger.info(f"总收益率: {total_return:.4f} ({total_return*100:.2f}%)")
    logger.info(f"年化波动率: {volatility:.4f} ({volatility*100:.2f}%)")
    logger.info(f"夏普比率: {sharpe_ratio:.4f}")
    logger.info(f"最大回撤: {max_drawdown:.4f} ({max_drawdown*100:.2f}%)")
    
    # 统计交易信号
    buy_signals = len(data[data['signal'] > 0])
    sell_signals = len(data[data['signal'] < 0])
    logger.info(f"买入信号: {buy_signals}次, 卖出信号: {sell_signals}次")
    
    # 显示最后几个价格和指标
    logger.info("最近5个交易日指标:")
    for i in range(max(0, len(data)-5), len(data)):
        row = data.iloc[i]
        logger.info(f"  {row.name.strftime('%m-%d %H:%M')}: 价格={row['close']:.2f}, "
                   f"快线={row['fast_ma']:.2f}, 慢线={row['slow_ma']:.2f}, 信号={row['signal']}")
    
    return data

def demo_live_trading():
    """演示实盘交易功能"""
    logger.info("=" * 60)
    logger.info("3. 实盘交易模拟演示")
    logger.info("=" * 60)
    
    # 初始化实盘交易引擎
    live_engine = LiveEngine(initial_balance=100000)
    
    # 创建策略（这里简化为策略名称）
    strategy_name = "MA_STRATEGY"
    
    logger.info("启动实盘交易模拟...")
    logger.info("模拟交易5个周期...")
    
    # 模拟实时交易过程
    for i in range(5):
        logger.info(f"\n--- 第{i+1}个交易周期 ---")
        
        # 模拟获取实时数据
        current_price = 50000 + np.random.normal(0, 1000)  # 模拟当前价格
        volume = 1.0  # 交易数量
        
        logger.info(f"当前价格: {current_price:.2f}")
        
        # 模拟交易决策
        if i % 2 == 0:  # 买入
            logger.info("策略信号: 买入")
            order_id = live_engine.place_order("BTCUSDT", "BUY", volume, current_price, "MARKET", strategy_name)
            if order_id:
                logger.info(f"买入订单已提交: {order_id}")
        else:  # 卖出
            logger.info("策略信号: 卖出")
            order_id = live_engine.place_order("BTCUSDT", "SELL", volume, current_price, "MARKET", strategy_name)
            if order_id:
                logger.info(f"卖出订单已提交: {order_id}")
        
        # 显示账户状态
        account_info = live_engine.get_account_info()
        positions = live_engine.get_positions()
        
        logger.info(f"账户余额: {account_info['balance']:.2f}")
        logger.info(f"可用资金: {account_info['available']:.2f}")
        logger.info(f"总盈亏: {account_info['total_pnl']:.2f}")
        logger.info(f"持仓数量: {len(positions)}")
        
        if positions:
            for symbol, pos_info in positions.items():
                logger.info(f"  {symbol}: 数量={pos_info.get('volume', 0):.4f}, "
                           f"均价={pos_info.get('avg_price', 0):.2f}, "
                           f"盈亏={pos_info.get('pnl', 0):.2f}")
        
        # 显示引擎状态
        engine_status = live_engine.get_engine_status()
        logger.info(f"引擎状态: {engine_status.get('status', 'unknown')}")
        logger.info(f"总订单数: {engine_status.get('total_orders', 0)}")
        
        time.sleep(1)  # 模拟时间间隔
    
    # 最终统计
    logger.info("\n最终交易统计:")
    engine_status = live_engine.get_engine_status()
    account_info = live_engine.get_account_info()
    
    logger.info(f"总订单数: {engine_status.get('total_orders', 0)}")
    logger.info(f"成功交易数: {engine_status.get('filled_orders', 0)}")
    logger.info(f"引擎运行时间: {engine_status.get('uptime', 'unknown')}")
    
    logger.info(f"最终账户余额: {account_info['balance']:.2f}")
    logger.info(f"总盈亏: {account_info['total_pnl']:.2f}")

def main():
    """主演示程序"""
    logger.add("logs/demo_{time}.log", rotation="1 day")
    
    print("🚀 VN.PY量化交易系统完整功能演示")
    print("=" * 80)
    
    try:
        # 1. 数据管理演示
        demo_data = demo_data_management()
        
        # 2. 策略回测演示
        backtest_data = demo_strategy_backtest(demo_data)
        
        # 3. 实盘交易演示
        demo_live_trading()
        
        logger.info("=" * 60)
        logger.info("✅ 完整系统演示成功完成!")
        logger.info("=" * 60)
        
        print("\n✅ 演示完成！系统包含以下核心功能:")
        print("📊 数据管理 - 市场数据获取、存储和检索")
        print("🧠 策略实现 - 移动平均等技术指标策略")
        print("📈 回测功能 - 历史数据回测和性能分析")
        print("💰 实盘交易 - 订单管理和实时交易模拟")
        
        print(f"\n📝 详细日志已保存到 logs/ 目录")
        print("🔗 可以查看各个模块的源码了解实现细节")
        
    except Exception as e:
        logger.error(f"演示过程中出现错误: {e}")
        raise

if __name__ == "__main__":
    main()