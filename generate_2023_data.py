#!/usr/bin/env python3
"""
生成2023年的BTCUSDT模拟数据用于回测
"""
import sys
sys.path.append('.')
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.data_manager import DataManager

def generate_2023_btc_data():
    """生成2023年的BTC价格数据"""
    print("生成2023年BTCUSDT数据...")
    
    # 生成2023年全年的小时数据
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31, 23, 59, 59)
    date_range = pd.date_range(start=start_date, end=end_date, freq='h')
    
    # 设置随机种子确保结果可重现
    np.random.seed(42)
    n_hours = len(date_range)
    
    # BTC 2023年的大致价格走势：从15000涨到42000
    start_price = 16500  # 2023年初价格
    end_price = 42000    # 2023年末价格
    
    # 生成价格趋势
    trend = np.linspace(0, np.log(end_price/start_price), n_hours)
    
    # 添加波动性
    volatility = 0.025  # 2.5%的小时波动率
    random_walk = np.cumsum(np.random.normal(0, volatility, n_hours))
    
    # 添加季节性和周期性
    # 模拟一些大事件的影响
    seasonal = 0.1 * np.sin(2 * np.pi * np.arange(n_hours) / (24 * 30))  # 月度周期
    
    # 合成价格变化
    log_returns = trend + random_walk + seasonal
    log_returns = np.cumsum(log_returns - log_returns[0])  # 标准化起点
    
    # 生成价格序列
    prices = start_price * np.exp(log_returns)
    
    # 确保价格合理
    prices = np.clip(prices, start_price * 0.3, start_price * 5)
    
    # 生成OHLC数据
    data = []
    for i, (timestamp, close_price) in enumerate(zip(date_range, prices)):
        if i == 0:
            open_price = close_price
        else:
            open_price = prices[i-1]
        
        # 生成高低价
        price_range = abs(close_price - open_price) + abs(np.random.normal(0, close_price * 0.01))
        high_price = max(open_price, close_price) + abs(np.random.normal(0, price_range * 0.3))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, price_range * 0.3))
        
        # 确保价格关系合理
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # 生成成交量
        price_volatility = abs((close_price - open_price) / open_price) if open_price > 0 else 0
        base_volume = 1000 + price_volatility * 8000
        volume = max(100, np.random.gamma(2, base_volume/2))
        
        data.append({
            'symbol': 'BTCUSDT',
            'exchange': 'BINANCE',
            'datetime': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'interval': '1h',
            'open_price': open_price,
            'high_price': high_price,
            'low_price': low_price,
            'close_price': close_price,
            'volume': volume,
            'turnover': 0,
            'open_interest': 0
        })
    
    return data

# 生成并保存数据
if __name__ == "__main__":
    print("🚀 开始生成2023年BTCUSDT数据...")
    
    # 生成数据
    bars_data = generate_2023_btc_data()
    
    # 保存到数据库
    dm = DataManager()
    dm.db_manager.save_bars(bars_data)
    
    print(f"✅ 成功生成并保存{len(bars_data)}条2023年BTCUSDT数据")
    print(f"   时间范围: {bars_data[0]['datetime']} 到 {bars_data[-1]['datetime']}")
    print(f"   价格范围: ${bars_data[0]['close_price']:.2f} 到 ${bars_data[-1]['close_price']:.2f}")
    print(f"")
    print("现在您可以运行回测了:")
    print("python main.py backtest --strategy ma --symbol BTCUSDT --capital 100000 --fast-ma 10 --slow-ma 30")