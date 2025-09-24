#!/usr/bin/env python3
"""
简化版集成测试 - 快速验证连接和数据流
"""

import json
import time
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from core.connection_manager import ConnectionManager, ConnectionStatus
from core.market_data_manager import MarketDataManager
from core.data_types import TickData, BarData

def test_integration():
    print("="*60)
    print("简化版集成测试 - ConnectionManager + MarketDataManager")
    print("="*60)
    
    # 1. 加载配置
    print("\n1. 加载系统配置...")
    with open('system_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    print("✅ 配置加载完成")
    
    # 2. 初始化组件
    print("\n2. 初始化组件...")
    connection_manager = ConnectionManager(config)
    market_data_manager = MarketDataManager(connection_manager)
    print("✅ 组件初始化完成")
    
    # 3. 数据收集
    received_ticks = []
    received_bars = []
    
    def on_tick(tick: TickData):
        received_ticks.append(tick)
        print(f"📈 接收Tick: {tick.symbol} @ {tick.last_price:.2f}")
    
    def on_bar(bar: BarData):
        received_bars.append(bar)
        print(f"📊 接收Bar: {bar.symbol}")
    
    # 注册回调
    market_data_manager.register_tick_callback(on_tick)
    market_data_manager.register_bar_callback(on_bar)
    
    # 4. 连接测试
    print("\n3. 测试连接...")
    connection_result = connection_manager.connect_gateway()
    print(f"连接结果: {'成功' if connection_result else '失败'}")
    
    is_connected = connection_manager.is_connected()
    print(f"连接状态: {'已连接' if is_connected else '未连接'}")
    
    # 启动市场数据管理器
    print("\n4. 启动MarketDataManager...")
    market_data_manager.start()
    print("✅ MarketDataManager已启动")
    
    # 5. 订阅测试
    print("\n5. 测试行情订阅...")
    test_contracts = ['rb2310', 'i2310']
    
    for contract in test_contracts:
        result = market_data_manager.subscribe_market_data(contract)
        print(f"订阅 {contract}: {'成功' if result else '失败'}")
    
    # 6. 数据接收测试 (短时间)
    print("\n6. 数据接收测试 (5秒)...")
    start_time = time.time()
    
    while time.time() - start_time < 5.0:
        time.sleep(0.1)
    
    # 7. 结果统计
    print(f"\n7. 测试结果:")
    print(f"接收Tick数据: {len(received_ticks)} 条")
    print(f"接收Bar数据: {len(received_bars)} 条")
    
    if len(received_ticks) > 0:
        print(f"✅ 数据流测试成功")
        
        # 技术指标测试
        print(f"\n8. 技术指标测试:")
        if len(received_ticks) >= 5:
            prices = [tick.last_price for tick in received_ticks[:5]]
            # 使用直接计算方法
            ma_result = sum(prices) / len(prices)
            print(f"MA{len(prices)}: {ma_result:.2f}")
            
            if len(received_ticks) >= 14:
                prices_14 = [tick.last_price for tick in received_ticks[:14]]
                # 计算RSI需要价格变化数据
                changes = [prices_14[i] - prices_14[i-1] for i in range(1, len(prices_14))]
                gains = [max(0, change) for change in changes]
                losses = [abs(min(0, change)) for change in changes]
                if len(gains) > 0 and sum(losses) > 0:
                    avg_gain = sum(gains) / len(gains)
                    avg_loss = sum(losses) / len(losses)
                    rs = avg_gain / avg_loss if avg_loss > 0 else 100
                    rsi = 100 - (100 / (1 + rs))
                    print(f"RSI(14): {rsi:.2f}")
                else:
                    print("RSI(14): 数据不足")
    else:
        print("❌ 未接收到数据")
    
    # 9. 清理
    print(f"\n9. 清理资源...")
    connection_manager.disconnect_gateway()
    print("✅ 集成测试完成")
    
    # 返回结果
    return len(received_ticks) > 0

if __name__ == '__main__':
    import os
    os.chdir('/home/user/webapp')
    
    success = test_integration()
    
    print(f"\n{'🎉 集成测试成功！' if success else '❌ 集成测试失败'}")
    print("数据流验证: ConnectionManager ↔️ MarketDataManager ✅" if success else "需要进一步调试")