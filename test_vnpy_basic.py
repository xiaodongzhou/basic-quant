#!/usr/bin/env python3
"""
VN.PY基础功能测试（无GUI版本）
"""

import sys

def test_basic_imports():
    """测试基础导入"""
    try:
        import vnpy
        print(f"✅ VN.PY版本: {vnpy.__version__}")
        
        # 测试基础模块导入（不涉及GUI）
        from vnpy.trader.object import TickData, BarData
        from vnpy.trader.constant import Exchange, Direction
        print("✅ 基础数据结构导入成功")
        
        # 测试事件引擎（不启动GUI）
        from vnpy.event import Event
        print("✅ 事件系统导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 基础导入失败: {e}")
        return False

def test_talib():
    """测试技术指标"""
    try:
        import talib
        import numpy as np
        
        # 测试MA计算
        prices = np.array([3500, 3510, 3505, 3520, 3515], dtype=float)
        ma = talib.SMA(prices, 3)
        
        print(f"✅ TA-Lib测试成功: MA3 = {ma[-1]:.2f}")
        return True
    except Exception as e:
        print(f"❌ TA-Lib测试失败: {e}")
        return False

def test_data_structures():
    """测试数据结构创建"""
    try:
        from vnpy.trader.object import TickData
        from vnpy.trader.constant import Exchange
        from datetime import datetime
        
        tick = TickData(
            symbol="rb2405",
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            name="螺纹钢2405",
            volume=100,
            turnover=1000000,
            open_interest=50000,
            last_price=3500.0,
            gateway_name="test"
        )
        
        print(f"✅ TickData创建成功: {tick.symbol}@{tick.last_price}")
        return True
    except Exception as e:
        print(f"❌ 数据结构测试失败: {e}")
        return False

def main():
    print("VN.PY基础环境测试")
    print("-" * 30)
    
    tests = [
        test_basic_imports,
        test_talib,
        test_data_structures
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 VN.PY基础环境可用！")
    else:
        print("⚠️  部分功能不可用")
    
    return passed == total

if __name__ == "__main__":
    main()