#!/usr/bin/env python3
"""
VN.PY最小化测试 - 专注于量化交易核心功能
Milestone 1.1 验证脚本
"""

import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # 避免GUI问题

def test_core_vnpy():
    """测试VN.PY核心功能"""
    print("🔍 测试VN.PY核心功能...")
    
    try:
        # 基础导入
        import vnpy
        print(f"✅ VN.PY版本: {vnpy.__version__}")
        
        # 导入核心交易对象
        from vnpy.trader.object import (
            TickData, BarData, OrderData, TradeData, 
            PositionData, AccountData
        )
        print("✅ 核心交易对象导入成功")
        
        # 导入常量
        from vnpy.trader.constant import (
            Exchange, Direction, OrderType, Status, Offset
        )
        print("✅ 交易常量导入成功")
        
        # 导入事件系统
        from vnpy.event import EventEngine, Event
        print("✅ 事件系统导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ VN.PY核心功能测试失败: {e}")
        return False

def test_event_system():
    """测试事件系统"""
    print("\n🔍 测试事件系统...")
    
    try:
        from vnpy.event import EventEngine, Event
        
        # 创建事件引擎（不启动）
        event_engine = EventEngine()
        print("✅ 事件引擎创建成功")
        
        # 测试事件注册
        events_received = []
        
        def test_handler(event):
            events_received.append(event.type)
        
        event_engine.register("test", test_handler)
        print("✅ 事件注册成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 事件系统测试失败: {e}")
        return False

def test_data_objects():
    """测试数据对象创建"""
    print("\n🔍 测试数据对象创建...")
    
    try:
        from vnpy.trader.object import TickData, BarData
        from vnpy.trader.constant import Exchange
        from datetime import datetime
        
        # 创建Tick数据
        tick = TickData(
            symbol="rb2405",
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            name="螺纹钢2405",
            volume=100,
            turnover=1000000,
            open_interest=50000,
            last_price=3500.0,
            limit_up=3850.0,
            limit_down=3150.0,
            open_price=3480.0,
            high_price=3520.0,
            low_price=3475.0,
            pre_close=3495.0,
            bid_price_1=3499.0,
            ask_price_1=3501.0,
            bid_volume_1=10,
            ask_volume_1=8,
            gateway_name="test"
        )
        print(f"✅ TickData创建成功: {tick.symbol} @ {tick.last_price}")
        
        # 创建Bar数据
        bar = BarData(
            symbol="rb2405",
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            interval="1m",
            volume=1000,
            turnover=3500000,
            open_interest=50000,
            open_price=3480.0,
            high_price=3520.0,
            low_price=3475.0,
            close_price=3500.0,
            gateway_name="test"
        )
        print(f"✅ BarData创建成功: {bar.symbol} OHLC: {bar.open_price}/{bar.high_price}/{bar.low_price}/{bar.close_price}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据对象测试失败: {e}")
        return False

def test_pandas_integration():
    """测试Pandas集成"""
    print("\n🔍 测试Pandas集成...")
    
    try:
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # 创建模拟价格数据
        dates = [datetime.now() - timedelta(minutes=i) for i in range(100, 0, -1)]
        prices = np.random.normal(3500, 50, 100).cumsum()
        prices = np.abs(prices)  # 确保价格为正
        
        df = pd.DataFrame({
            'datetime': dates,
            'close': prices,
            'volume': np.random.randint(100, 1000, 100)
        })
        
        # 计算简单移动平均
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        
        print(f"✅ Pandas数据处理成功: 数据点数={len(df)}")
        print(f"✅ 技术指标计算成功: MA5={df['ma5'].iloc[-1]:.2f}, MA20={df['ma20'].iloc[-1]:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Pandas集成测试失败: {e}")
        return False

def test_config_setup():
    """测试配置文件支持"""
    print("\n🔍 测试配置文件支持...")
    
    try:
        import json
        from pathlib import Path
        
        # 创建测试配置
        config = {
            "gateway": {
                "name": "CTP",
                "settings": {
                    "用户名": "simulation_user", 
                    "密码": "simulation_pass",
                    "经纪商代码": "9999",
                    "交易服务器": "tcp://180.168.146.187:10130",
                    "行情服务器": "tcp://180.168.146.187:10131"
                }
            },
            "symbols": ["rb2405", "i2405", "j2405"],
            "strategy": {
                "name": "ma_strategy",
                "fast_ma": 10,
                "slow_ma": 30
            }
        }
        
        # 保存配置文件
        with open("test_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 读取配置文件
        with open("test_config.json", "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
        
        assert loaded_config["gateway"]["name"] == "CTP"
        print("✅ 配置文件读写成功")
        
        # 清理测试文件
        Path("test_config.json").unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ 配置文件测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("VN.PY最小化环境测试 - Milestone 1.1")
    print("专注于量化交易核心功能验证")
    print("=" * 60)
    
    tests = [
        ("VN.PY核心功能", test_core_vnpy),
        ("事件系统", test_event_system),
        ("数据对象创建", test_data_objects), 
        ("Pandas集成", test_pandas_integration),
        ("配置文件支持", test_config_setup)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\n📊 总体结果: {passed}/{total} 测试通过")
    
    if passed >= 4:  # 至少4个核心测试通过
        print("\n🎉 Milestone 1.1 验证成功!")
        print("✅ VN.PY环境搭建完成")
        print("✅ 核心功能可用")
        print("✅ 可以进入下一阶段开发")
        return True
    else:
        print("\n⚠️  Milestone 1.1 未完全通过")
        print("需要解决基础环境问题")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)