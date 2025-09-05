#!/usr/bin/env python3
"""测试ML SuperTrend环境设置"""

import sys
print("🔄 测试基础依赖...")

try:
    import yfinance as yf
    print("✅ yfinance导入成功")
except ImportError as e:
    print(f"❌ yfinance导入失败: {e}")
    sys.exit(1)

try:
    import pandas as pd
    import numpy as np
    print("✅ pandas, numpy导入成功")
except ImportError as e:
    print(f"❌ pandas/numpy导入失败: {e}")
    sys.exit(1)

try:
    import pandas_ta as ta
    print("✅ pandas-ta导入成功")
except ImportError as e:
    print(f"❌ pandas-ta导入失败: {e}")
    sys.exit(1)

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    print("✅ plotly导入成功")
except ImportError as e:
    print(f"❌ plotly导入失败: {e}")
    sys.exit(1)

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    print("✅ scikit-learn导入成功")
except ImportError as e:
    print(f"❌ scikit-learn导入失败: {e}")
    sys.exit(1)

print("\n🔄 测试数据获取...")
try:
    ticker = yf.Ticker('QQQ')
    data = ticker.history(start='2023-01-01', end='2025-01-01', interval='1d')
    print(f"✅ 成功获取QQQ数据: {len(data)}条记录")
    print(f"📅 数据期间: {data.index[0].date()} 到 {data.index[-1].date()}")
    print(f"💲 最新价格: ${data['Close'].iloc[-1]:.2f}")
except Exception as e:
    print(f"❌ 数据获取失败: {e}")
    sys.exit(1)

print("\n🔄 测试技术指标计算...")
try:
    # 测试ATR计算
    atr = ta.atr(high=data['High'], low=data['Low'], close=data['Close'], length=14)
    print(f"✅ ATR计算成功，最新值: {atr.iloc[-1]:.2f}")
    
    # 测试RSI计算
    rsi = ta.rsi(data['Close'], length=14)
    print(f"✅ RSI计算成功，最新值: {rsi.iloc[-1]:.2f}")
    
    # 测试MACD计算
    macd_data = ta.macd(data['Close'])
    print(f"✅ MACD计算成功，列数: {len(macd_data.columns)}")
    
except Exception as e:
    print(f"❌ 技术指标计算失败: {e}")
    sys.exit(1)

print("\n🔄 测试机器学习组件...")
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    
    # 创建简单的测试数据
    X = np.random.random((100, 5))
    y = np.random.random(100)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(X_scaled, y)
    
    predictions = model.predict(X_scaled[:10])
    print(f"✅ 机器学习模型测试成功，预测数量: {len(predictions)}")
    
except Exception as e:
    print(f"❌ 机器学习测试失败: {e}")
    sys.exit(1)

print("\n🎉 所有测试通过!")
print("📋 环境准备完成，可以开始使用ML Adaptive SuperTrend Notebook")
print("📝 请在Notebook中提供Pine Script源代码以进行转换")