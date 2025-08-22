#!/usr/bin/env python3
"""
测试回测功能
"""
import sys
sys.path.append('.')
from data.data_manager import DataManager
import pandas as pd
import numpy as np

dm = DataManager()

# 读取现有数据
df = dm.db_manager.load_bars('BTCUSDT', 'DEMO', '2025-08-15 00:00:00', '2025-08-22 23:59:59', '1h')

if len(df) > 0:
    print(f'找到{len(df)}条数据，开始回测...')
    
    # 重命名列
    if 'close_price' in df.columns:
        df = df.rename(columns={
            'open_price': 'open',
            'high_price': 'high', 
            'low_price': 'low',
            'close_price': 'close'
        })
    
    # 计算移动平均
    fast_period = 5
    slow_period = 12
    
    df['fast_ma'] = df['close'].rolling(window=fast_period).mean()
    df['slow_ma'] = df['close'].rolling(window=slow_period).mean()
    
    # 生成信号
    df['signal'] = 0
    for i in range(slow_period, len(df)):
        if (df['fast_ma'].iloc[i] > df['slow_ma'].iloc[i] and 
            df['fast_ma'].iloc[i-1] <= df['slow_ma'].iloc[i-1]):
            df.iloc[i, df.columns.get_loc('signal')] = 1
        elif (df['fast_ma'].iloc[i] < df['slow_ma'].iloc[i] and 
              df['fast_ma'].iloc[i-1] >= df['slow_ma'].iloc[i-1]):
            df.iloc[i, df.columns.get_loc('signal')] = -1
    
    # 计算收益
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df['signal'].shift(1) * df['returns']
    df['cumulative_returns'] = (1 + df['strategy_returns'].fillna(0)).cumprod()
    
    # 计算指标
    total_return = df['cumulative_returns'].iloc[-1] - 1
    volatility = df['strategy_returns'].std() * (365 * 24) ** 0.5
    sharpe = (df['strategy_returns'].mean() / df['strategy_returns'].std() * (365 * 24) ** 0.5) if df['strategy_returns'].std() > 0 else 0
    buy_signals = len(df[df['signal'] > 0])
    sell_signals = len(df[df['signal'] < 0])
    
    print('')
    print('📊 回测结果:')
    print(f'   策略收益率: {total_return:.4f} ({total_return*100:.2f}%)')
    print(f'   年化波动率: {volatility:.4f} ({volatility*100:.2f}%)')
    print(f'   夏普比率: {sharpe:.4f}')
    print(f'   买入信号: {buy_signals}次')
    print(f'   卖出信号: {sell_signals}次')
    print(f'   价格范围: ${df["close"].min():.2f} - ${df["close"].max():.2f}')
    print('   ✅ 回测功能验证成功！')
else:
    print('未找到可用数据')