#!/usr/bin/env python3
"""
VN.PY环境测试脚本
用于验证Milestone 1.1: VN.PY环境搭建
"""

import sys
import traceback
from datetime import datetime

def test_vnpy_import():
    """测试VN.PY基础组件导入"""
    try:
        import vnpy
        print(f"✅ VN.PY版本: {vnpy.__version__}")
        
        from vnpy.event import EventEngine
        print("✅ EventEngine导入成功")
        
        from vnpy.trader.engine import MainEngine
        print("✅ MainEngine导入成功")
        
        return True
    except Exception as e:
        print(f"❌ VN.PY导入失败: {e}")
        traceback.print_exc()
        return False

def test_event_engine():
    """测试事件引擎"""
    try:
        from vnpy.event import EventEngine, Event
        
        # 创建事件引擎
        event_engine = EventEngine()
        print("✅ 事件引擎创建成功")
        
        # 测试事件注册和处理
        test_events = []
        
        def test_handler(event: Event):
            test_events.append(event.type)
        
        event_engine.register("test_event", test_handler)
        
        # 启动事件引擎
        event_engine.start()
        print("✅ 事件引擎启动成功")
        
        # 发送测试事件
        test_event = Event("test_event", {"test": "data"})
        event_engine.put(test_event)
        
        # 等待事件处理
        import time
        time.sleep(0.1)
        
        # 停止事件引擎
        event_engine.stop()
        print("✅ 事件引擎停止成功")
        
        if test_events:
            print("✅ 事件处理测试通过")
            return True
        else:
            print("❌ 事件处理测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 事件引擎测试失败: {e}")
        traceback.print_exc()
        return False

def test_main_engine():
    """测试主引擎"""
    try:
        from vnpy.event import EventEngine
        from vnpy.trader.engine import MainEngine
        
        # 创建事件引擎
        event_engine = EventEngine()
        
        # 创建主引擎
        main_engine = MainEngine(event_engine)
        print("✅ 主引擎创建成功")
        
        # 检查主引擎基本功能
        gateways = main_engine.get_all_gateway_names()
        print(f"✅ 可用网关: {gateways}")
        
        return True
        
    except Exception as e:
        print(f"❌ 主引擎测试失败: {e}")
        traceback.print_exc()
        return False

def test_ctp_gateway():
    """测试CTP网关（如果可用）"""
    try:
        # 尝试导入CTP网关
        try:
            from vnpy.gateway.ctp import CtpGateway
            print("✅ CTP网关导入成功")
            ctp_available = True
        except ImportError:
            print("⚠️  CTP网关未安装，将使用模拟模式")
            ctp_available = False
        
        return ctp_available
        
    except Exception as e:
        print(f"❌ CTP网关测试失败: {e}")
        traceback.print_exc()
        return False

def test_basic_data_structures():
    """测试基础数据结构"""
    try:
        from vnpy.trader.object import (
            TickData, BarData, OrderData, TradeData, 
            PositionData, AccountData, ContractData
        )
        from vnpy.trader.constant import (
            Exchange, Direction, OrderType, Status, Offset
        )
        
        print("✅ 基础数据结构导入成功")
        
        # 测试创建基础数据对象
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
        print("✅ TickData创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据结构测试失败: {e}")
        traceback.print_exc()
        return False

def test_technical_indicators():
    """测试技术指标库"""
    try:
        import talib
        print("✅ TA-Lib技术指标库可用")
        
        # 测试简单的MA计算
        import numpy as np
        test_prices = np.array([3500, 3510, 3505, 3520, 3515, 3525, 3530, 3520, 3535, 3540], dtype=float)
        ma5 = talib.SMA(test_prices, 5)
        
        if not np.isnan(ma5[-1]):
            print(f"✅ MA指标计算成功: {ma5[-1]:.2f}")
            return True
        else:
            print("❌ MA指标计算失败")
            return False
            
    except Exception as e:
        print(f"❌ 技术指标测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("VN.PY环境测试 - Milestone 1.1")
    print(f"测试时间: {datetime.now()}")
    print("=" * 50)
    
    tests = [
        ("VN.PY基础组件导入", test_vnpy_import),
        ("事件引擎功能", test_event_engine),
        ("主引擎功能", test_main_engine),
        ("CTP网关检查", test_ctp_gateway),
        ("基础数据结构", test_basic_data_structures),
        ("技术指标库", test_technical_indicators),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 测试: {test_name}")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
        print(f"结果: {'✅ 通过' if result else '❌ 失败'}")
    
    print("\n" + "=" * 50)
    print("测试总结:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 Milestone 1.1: VN.PY环境搭建 - 验证成功！")
        return True
    else:
        print("⚠️  部分测试失败，需要检查环境配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)