#!/usr/bin/env python3
"""
基础SuperTrend演示 - 在等待Pine Script代码期间的功能展示
"""

import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

def basic_supertrend(high, low, close, period=14, multiplier=3.0):
    """
    基础SuperTrend计算（标准算法）
    """
    # 计算ATR
    atr = ta.atr(high=high, low=low, close=close, length=period)
    
    # 计算HL2
    hl2 = (high + low) / 2
    
    # 初始化输出
    supertrend_upper = pd.Series(np.nan, index=close.index)
    supertrend_lower = pd.Series(np.nan, index=close.index)
    supertrend = pd.Series(np.nan, index=close.index)
    trend = pd.Series(1, index=close.index)
    
    for i in range(len(close)):
        if i == 0 or pd.isna(atr.iloc[i]):
            continue
            
        # 基础上下轨
        basic_upper = hl2.iloc[i] + multiplier * atr.iloc[i]
        basic_lower = hl2.iloc[i] - multiplier * atr.iloc[i]
        
        # 上轨处理
        if i > 0 and not pd.isna(supertrend_upper.iloc[i-1]):
            if basic_upper < supertrend_upper.iloc[i-1] or close.iloc[i-1] > supertrend_upper.iloc[i-1]:
                supertrend_upper.iloc[i] = basic_upper
            else:
                supertrend_upper.iloc[i] = supertrend_upper.iloc[i-1]
        else:
            supertrend_upper.iloc[i] = basic_upper
        
        # 下轨处理
        if i > 0 and not pd.isna(supertrend_lower.iloc[i-1]):
            if basic_lower > supertrend_lower.iloc[i-1] or close.iloc[i-1] < supertrend_lower.iloc[i-1]:
                supertrend_lower.iloc[i] = basic_lower
            else:
                supertrend_lower.iloc[i] = supertrend_lower.iloc[i-1]
        else:
            supertrend_lower.iloc[i] = basic_lower
        
        # 趋势判断
        if i > 0:
            if close.iloc[i] <= supertrend_lower.iloc[i]:
                trend.iloc[i] = -1
            elif close.iloc[i] >= supertrend_upper.iloc[i]:
                trend.iloc[i] = 1
            else:
                trend.iloc[i] = trend.iloc[i-1]
        
        # SuperTrend值
        if trend.iloc[i] == 1:
            supertrend.iloc[i] = supertrend_lower.iloc[i]
        else:
            supertrend.iloc[i] = supertrend_upper.iloc[i]
    
    return {
        'supertrend': supertrend,
        'supertrend_upper': supertrend_upper,
        'supertrend_lower': supertrend_lower,
        'trend': trend,
        'atr': atr
    }

def demonstrate_ml_features(data):
    """
    演示机器学习特征工程
    """
    print("🧠 ML特征工程演示...")
    
    features = pd.DataFrame(index=data.index)
    
    # 价格特征
    features['rsi'] = ta.rsi(data['Close'], length=14)
    macd_data = ta.macd(data['Close'])
    features['macd'] = macd_data['MACD_12_26_9']
    
    # 波动性特征
    features['atr'] = ta.atr(high=data['High'], low=data['Low'], close=data['Close'], length=14)
    features['volatility'] = data['Close'].rolling(20).std()
    
    # 趋势特征
    features['sma_20'] = data['Close'].rolling(20).mean()
    features['ema_12'] = data['Close'].ewm(span=12).mean()
    
    # 价格位置
    features['price_position'] = (data['Close'] - data['Low'].rolling(20).min()) / \
                                (data['High'].rolling(20).max() - data['Low'].rolling(20).min())
    
    # 成交量特征
    features['volume_sma'] = data['Volume'].rolling(20).mean()
    features['volume_ratio'] = data['Volume'] / features['volume_sma']
    
    features = features.fillna(method='ffill').fillna(0)
    
    print(f"✅ 生成{len(features.columns)}个ML特征")
    print("特征列表:", list(features.columns))
    
    return features

def main():
    print("🎯 ML Adaptive SuperTrend 基础功能演示")
    print("=" * 50)
    
    # 获取数据
    print("📊 获取QQQ数据...")
    ticker = yf.Ticker('QQQ')
    data = ticker.history(start='2023-01-01', end='2025-01-01', interval='1d')
    print(f"✅ 获取{len(data)}条数据")
    
    # 计算基础SuperTrend
    print("\n📈 计算基础SuperTrend...")
    st_results = basic_supertrend(
        data['High'], data['Low'], data['Close'],
        period=14, multiplier=3.0
    )
    
    # 添加结果到数据
    for key, value in st_results.items():
        data[key] = value
    
    print(f"✅ SuperTrend计算完成")
    print(f"有效数据点: {data['supertrend'].count()}")
    
    # ML特征演示
    print("\n🤖 机器学习特征演示...")
    features = demonstrate_ml_features(data)
    
    # 简单的自适应乘数预测演示
    print("\n🔬 自适应参数预测演示...")
    
    # 使用历史波动率作为目标
    target = data['Close'].rolling(14).std() / data['Close'] * 10 + 2.0
    
    # 准备训练数据
    train_size = min(200, len(features) - 50)
    if train_size > 50:
        X_train = features.iloc[-train_size-50:-50].fillna(0)
        y_train = target.iloc[-train_size-50:-50].fillna(3.0)
        
        # 训练模型
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_train)
        
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X_scaled, y_train)
        
        # 预测最近的乘数
        X_recent = features.iloc[-50:].fillna(0)
        X_recent_scaled = scaler.transform(X_recent)
        predicted_multipliers = model.predict(X_recent_scaled)
        predicted_multipliers = np.clip(predicted_multipliers, 1.5, 5.0)
        
        print(f"✅ ML模型训练完成")
        print(f"预测乘数范围: {predicted_multipliers.min():.2f} - {predicted_multipliers.max():.2f}")
        print(f"平均预测乘数: {predicted_multipliers.mean():.2f}")
        
        # 计算自适应SuperTrend（使用最后一个预测乘数作为示例）
        adaptive_multiplier = predicted_multipliers[-1]
        adaptive_st = basic_supertrend(
            data['High'].tail(100), 
            data['Low'].tail(100), 
            data['Close'].tail(100),
            period=14, 
            multiplier=adaptive_multiplier
        )
        
        print(f"✅ 自适应SuperTrend计算完成 (乘数: {adaptive_multiplier:.2f})")
    
    # 性能统计
    print("\n📊 性能统计...")
    data['signal'] = 0
    data.loc[data['trend'] == 1, 'signal'] = 1
    data.loc[data['trend'] == -1, 'signal'] = -1
    
    data['signal_change'] = data['signal'].diff()
    buy_signals = data[data['signal_change'] == 2]
    sell_signals = data[data['signal_change'] == -2]
    
    print(f"上升趋势天数: {(data['trend'] == 1).sum()} ({(data['trend'] == 1).sum()/len(data)*100:.1f}%)")
    print(f"下降趋势天数: {(data['trend'] == -1).sum()} ({(data['trend'] == -1).sum()/len(data)*100:.1f}%)")
    print(f"买入信号次数: {len(buy_signals)}")
    print(f"卖出信号次数: {len(sell_signals)}")
    
    if len(buy_signals) > 0:
        print(f"最近买入信号: {buy_signals.index[-1].date()}")
    if len(sell_signals) > 0:
        print(f"最近卖出信号: {sell_signals.index[-1].date()}")
    
    # 当前状态
    print(f"\n📋 当前状态:")
    print(f"当前价格: ${data['Close'].iloc[-1]:.2f}")
    print(f"当前SuperTrend: ${data['supertrend'].iloc[-1]:.2f}")
    print(f"当前趋势: {'上升' if data['trend'].iloc[-1] == 1 else '下降'}")
    print(f"当前ATR: {data['atr'].iloc[-1]:.2f}")
    
    # 保存结果
    output_file = 'demo_results.csv'
    columns_to_save = ['Close', 'supertrend', 'trend', 'signal', 'atr']
    data[columns_to_save].to_csv(output_file)
    print(f"\n💾 演示结果已保存到: {output_file}")
    
    print("\n🎉 基础功能演示完成！")
    print("📝 准备好接收Pine Script代码进行精确转换...")

if __name__ == "__main__":
    main()