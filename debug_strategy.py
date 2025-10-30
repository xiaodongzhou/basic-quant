"""
调试策略脚本 - 检查指标和信号生成情况
"""
import pandas as pd
import numpy as np
import yfinance as yf
from strategies.indicators import calculate_ema, calculate_atr, calculate_adx

def debug_strategy():
    """调试策略逻辑"""
    print("开始调试策略...")
    
    # 下载数据
    ticker = yf.Ticker("QQQ")
    data = ticker.history(start='2023-01-01', end='2024-01-01', interval='1d')
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    data.columns = ['open', 'high', 'low', 'close', 'volume']
    
    # 计算指标
    data['ema20'] = calculate_ema(data['close'], 20)
    data['ema60'] = calculate_ema(data['close'], 60)
    data['atr'] = calculate_atr(data['high'], data['low'], data['close'], 14)
    
    adx, plus_di, minus_di = calculate_adx(data['high'], data['low'], data['close'], 14)
    data['adx'] = adx
    data['plus_di'] = plus_di
    data['minus_di'] = minus_di
    
    # 测试策略逻辑
    from simple_qqq_test import SimpleEMAStrategy
    strategy = SimpleEMAStrategy()
    
    print("\n检查趋势和入场信号:")
    print("索引\t日期\t\t收盘价\tEMA20\t\tEMA60\t\tADX\t趋势\t入场信号")
    print("-" * 100)
    
    trend_count = {"UP": 0, "DOWN": 0, "SIDEWAYS": 0}
    signal_count = {"LONG": 0, "SHORT": 0, "NONE": 0}
    
    for i in range(60, min(160, len(data))):  # 检查60-160索引
        date = data.index[i].strftime('%Y-%m-%d')
        close = data['close'].iloc[i]
        ema20 = data['ema20'].iloc[i]
        ema60 = data['ema60'].iloc[i]
        adx_val = data['adx'].iloc[i]
        
        # 趋势判断
        trend = strategy.analyze_trend(data, i)
        trend_count[trend] += 1
        
        # 入场信号
        entry_signal = strategy.check_entry_signal(data, i, trend)
        signal_count[entry_signal] += 1
        
        if i % 10 == 0 or entry_signal != "NONE":  # 每10个打印一次，或有信号时打印
            print(f"{i}\t{date}\t{close:.2f}\t{ema20:.2f}\t\t{ema60:.2f}\t\t{adx_val:.2f}\t{trend}\t{entry_signal}")
    
    print(f"\n趋势统计: {trend_count}")
    print(f"信号统计: {signal_count}")
    
    # 检查ADX值的分布
    adx_values = data['adx'].dropna()
    print(f"\nADX统计:")
    print(f"  平均值: {adx_values.mean():.2f}")
    print(f"  中位数: {adx_values.median():.2f}")
    print(f"  最大值: {adx_values.max():.2f}")
    print(f"  最小值: {adx_values.min():.2f}")
    print(f"  > 20的比例: {(adx_values > 20).mean():.2%}")
    print(f"  > 25的比例: {(adx_values > 25).mean():.2%}")
    
    # 检查EMA交叉情况
    ema_diff = data['ema20'] - data['ema60']
    crossovers = []
    for i in range(1, len(ema_diff)):
        if not pd.isna(ema_diff.iloc[i]) and not pd.isna(ema_diff.iloc[i-1]):
            if ema_diff.iloc[i-1] < 0 and ema_diff.iloc[i] > 0:
                crossovers.append(('GOLDEN', data.index[i], data['close'].iloc[i]))
            elif ema_diff.iloc[i-1] > 0 and ema_diff.iloc[i] < 0:
                crossovers.append(('DEATH', data.index[i], data['close'].iloc[i]))
    
    print(f"\nEMA交叉统计:")
    print(f"  总交叉次数: {len(crossovers)}")
    print("  最近5次交叉:")
    for cross_type, date, price in crossovers[-5:]:
        print(f"    {cross_type}: {date.strftime('%Y-%m-%d')}, 价格: {price:.2f}")
    
    return data

if __name__ == "__main__":
    data = debug_strategy()