#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版通达信SuperTrend算法
"""

import pandas as pd
import numpy as np
from my_supertrend_analyzer import MySuperTrendAnalyzer

def test_enhanced_algorithm():
    """测试增强版算法是否生效"""
    
    # 创建测试数据
    dates = pd.date_range('2025-01-01', periods=50, freq='H')
    np.random.seed(42)  # 固定随机种子确保可重现
    
    base_price = 3000
    price_data = []
    for i in range(50):
        # 模拟价格波动，包含一些跳空
        if i % 10 == 0:  # 每10个周期一个小跳空
            jump = np.random.normal(0, 20)
        else:
            jump = np.random.normal(0, 5)
        
        price = base_price + jump + i * 2
        price_data.append(price)
    
    # 构建OHLCV数据
    data = {
        'open': [p + np.random.normal(0, 2) for p in price_data],
        'high': [p + abs(np.random.normal(0, 5)) for p in price_data],
        'low': [p - abs(np.random.normal(0, 5)) for p in price_data],
        'close': price_data,
        'volume': [1000 + abs(int(np.random.normal(0, 500))) for _ in price_data]
    }
    
    df = pd.DataFrame(data, index=dates)
    
    print("🔥 测试增强版通达信SuperTrend算法")
    print(f"📊 测试数据: {len(df)} 个数据点")
    print(f"💰 价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
    
    # 创建分析器并计算
    analyzer = MySuperTrendAnalyzer(atr_period=10, multiplier=3.0)
    result = analyzer.calculate(df)
    
    # 显示结果
    print(f"\n✅ 计算完成")
    print(f"📈 数据源: {result['source']}")
    print(f"🎯 当前趋势: {result['current_trend']}")
    print(f"📊 趋势变化点: {len(result['trend_changes'])} 个")
    
    # 显示前15个SuperTrend值
    supertrend_line = result['supertrend_line']
    valid_data = [x for x in supertrend_line if x is not None]
    if valid_data:
        print(f"\n📈 SuperTrend前15个有效值:")
        print(f"   {valid_data[:15]}")
    
    return result

if __name__ == "__main__":
    test_enhanced_algorithm()