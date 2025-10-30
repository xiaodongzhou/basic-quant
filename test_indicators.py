"""
测试指标计算函数
"""
import pandas as pd
import numpy as np
import yfinance as yf
from strategies.indicators import calculate_adx

def test_adx():
    """测试ADX计算"""
    print("测试ADX计算...")
    
    # 获取测试数据
    ticker = yf.Ticker("QQQ")
    data = ticker.history(start='2023-01-01', end='2023-06-01', interval='1d')
    
    high = data['High']
    low = data['Low']
    close = data['Close']
    
    print(f"数据长度: {len(data)}")
    print(f"数据范围: {data.index[0]} 到 {data.index[-1]}")
    
    # 检查输入数据
    print(f"High 样本: {high.head()}")
    print(f"Low 样本: {low.head()}")
    print(f"Close 样本: {close.head()}")
    
    print(f"High 有NaN: {high.isna().sum()}")
    print(f"Low 有NaN: {low.isna().sum()}")
    print(f"Close 有NaN: {close.isna().sum()}")
    
    # 计算ADX
    try:
        adx, plus_di, minus_di = calculate_adx(high, low, close, 14)
        
        print(f"ADX 类型: {type(adx)}")
        print(f"ADX 长度: {len(adx) if hasattr(adx, '__len__') else 'scalar'}")
        print(f"ADX 前10个值:")
        print(adx.head(10))
        print(f"ADX NaN 数量: {adx.isna().sum()}")
        print(f"ADX 非NaN值范围: {adx.min():.2f} - {adx.max():.2f}")
        
        # 检查中间步骤
        print("\n检查计算过程...")
        
        # 计算真实范围
        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        print(f"TR 前10个值: {tr.head(10)}")
        print(f"TR NaN数量: {tr.isna().sum()}")
        
        # 计算方向性移动
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        print(f"Up move 前10个值: {up_move.head(10)}")
        print(f"Down move 前10个值: {down_move.head(10)}")
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        print(f"Plus DM 前10个值: {plus_dm[:10]}")
        print(f"Minus DM 前10个值: {minus_dm[:10]}")
        
    except Exception as e:
        print(f"ADX计算出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_adx()