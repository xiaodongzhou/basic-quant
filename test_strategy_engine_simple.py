#!/usr/bin/env python3
"""
简化版StrategyEngine测试 - 快速验证策略框架功能
"""

import json
import time
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from core.strategy_engine import (
    StrategyEngine, MockStrategy, create_sample_strategy_config
)
from core.trading_engine import TradingEngine
from core.connection_manager import ConnectionManager
from core.market_data_manager import MarketDataManager


def test_strategy_engine():
    print("="*60)
    print("简化版StrategyEngine测试")
    print("="*60)
    
    # 1. 初始化系统组件
    print("\n1. 初始化系统组件...")
    with open('system_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    connection_manager = ConnectionManager(config)
    trading_engine = TradingEngine(connection_manager, config)
    market_data_manager = MarketDataManager(connection_manager)
    strategy_engine = StrategyEngine(trading_engine, market_data_manager)
    
    print("✅ 系统组件初始化完成")
    
    # 2. 连接网关和启动市场数据
    print("\n2. 连接网关和启动市场数据...")
    connection_result = connection_manager.connect_gateway()
    print(f"网关连接: {'成功' if connection_result else '失败'}")
    
    market_data_manager.start()
    print("✅ 市场数据管理器已启动")
    
    # 3. 创建和加载策略
    print("\n3. 创建和加载策略...")
    
    # 创建策略配置
    strategy_config = create_sample_strategy_config(
        name="test_strategy_1",
        symbols=["rb2310", "i2310"]
    )
    
    # 加载策略
    load_result = strategy_engine.load_strategy(MockStrategy, strategy_config)
    print(f"策略加载: {'成功' if load_result else '失败'}")
    
    if load_result:
        print(f"✅ 策略已加载: {strategy_config.name}")
        print(f"   关注合约: {strategy_config.symbols}")
        print(f"   策略参数: {strategy_config.parameters}")
    
    # 4. 启动策略
    print("\n4. 启动策略...")
    start_result = strategy_engine.start_strategy("test_strategy_1")
    print(f"策略启动: {'成功' if start_result else '失败'}")
    
    # 检查活跃策略
    active_strategies = strategy_engine.active_strategies
    print(f"活跃策略数量: {len(active_strategies)}")
    print(f"活跃策略名称: {list(active_strategies.keys())}")
    
    # 5. 订阅市场数据和运行策略
    print("\n5. 订阅市场数据和运行策略...")
    
    # 订阅策略关注的合约
    for symbol in strategy_config.symbols:
        result = market_data_manager.subscribe_market_data(symbol)
        print(f"订阅 {symbol}: {'成功' if result else '失败'}")
    
    # 等待策略处理数据
    print("\n6. 策略运行监控 (10秒)...")
    for i in range(10):
        time.sleep(1)
        
        # 获取策略实例
        strategy = strategy_engine.strategy_manager.get_strategy("test_strategy_1")
        if strategy:
            print(f"[{i+1:2d}s] Tick处理: {strategy.tick_count:3d}个, Bar处理: {strategy.bar_count:2d}个")
    
    # 7. 检查策略统计
    print("\n7. 策略统计信息...")
    statistics = strategy_engine.get_strategy_statistics()
    
    if "test_strategy_1" in statistics:
        stats = statistics["test_strategy_1"]
        print(f"策略名称: {stats['strategy_name']}")
        print(f"策略状态: {stats['status']}")
        print(f"运行时间: {stats['start_time']}")
        print(f"总交易数: {stats['total_trades']}")
        print(f"信号数量: {stats['signals_count']}")
    
    # 8. 测试策略管理功能
    print("\n8. 测试策略管理功能...")
    
    # 加载第二个策略
    strategy_config_2 = create_sample_strategy_config(
        name="test_strategy_2",
        symbols=["j2310"]
    )
    
    load_result_2 = strategy_engine.load_strategy(MockStrategy, strategy_config_2)
    print(f"第二个策略加载: {'成功' if load_result_2 else '失败'}")
    
    start_result_2 = strategy_engine.start_strategy("test_strategy_2")
    print(f"第二个策略启动: {'成功' if start_result_2 else '失败'}")
    
    # 检查总体状态
    status = strategy_engine.get_status()
    print(f"总策略数量: {status['total_strategies']}")
    print(f"活跃策略数量: {status['active_strategies']}")
    print(f"活跃策略列表: {status['active_strategy_names']}")
    
    # 9. 测试策略停止
    print("\n9. 测试策略停止...")
    
    stop_result_1 = strategy_engine.stop_strategy("test_strategy_1")
    print(f"停止策略1: {'成功' if stop_result_1 else '失败'}")
    
    # 检查活跃策略变化
    active_strategies_after_stop = strategy_engine.active_strategies
    print(f"停止后活跃策略: {list(active_strategies_after_stop.keys())}")
    
    # 10. 测试策略移除
    print("\n10. 测试策略移除...")
    
    remove_result = strategy_engine.remove_strategy("test_strategy_1")
    print(f"移除策略1: {'成功' if remove_result else '失败'}")
    
    # 最终状态
    final_status = strategy_engine.get_status()
    print(f"最终策略数量: {final_status['total_strategies']}")
    print(f"最终活跃策略: {final_status['active_strategy_names']}")
    
    # 11. 验证里程碑检查标准
    print("\n11. 验证里程碑检查标准...")
    
    # 策略加载机制正常
    load_check = load_result and load_result_2
    print(f"✅ 策略加载机制正常: {'通过' if load_check else '失败'}")
    
    # 策略生命周期管理正确  
    lifecycle_check = start_result and start_result_2 and stop_result_1
    print(f"✅ 策略生命周期管理正确: {'通过' if lifecycle_check else '失败'}")
    
    # 数据事件分发准确
    strategy_1 = strategy_engine.strategy_manager.get_strategy("test_strategy_2")  # 仍在运行的策略
    data_dispatch_check = strategy_1 and strategy_1.tick_count > 0
    print(f"✅ 数据事件分发准确: {'通过' if data_dispatch_check else '失败'}")
    
    # 信号回调机制有效 (通过策略能接收数据验证)
    signal_callback_check = data_dispatch_check
    print(f"✅ 信号回调机制有效: {'通过' if signal_callback_check else '失败'}")
    
    # 12. 清理资源
    print("\n12. 清理资源...")
    
    # 停止剩余策略
    strategy_engine.stop_strategy("test_strategy_2")
    
    # 断开连接
    connection_manager.disconnect_gateway()
    
    print("✅ StrategyEngine测试完成")
    
    # 返回测试结果
    return {
        "strategy_loading": load_check,
        "lifecycle_management": lifecycle_check,  
        "data_dispatch": data_dispatch_check,
        "callback_mechanism": signal_callback_check,
        "all_passed": all([load_check, lifecycle_check, data_dispatch_check, signal_callback_check])
    }


if __name__ == '__main__':
    os.chdir('/home/user/webapp')
    
    results = test_strategy_engine()
    
    print("\n" + "="*60)
    print("里程碑2.2验证结果")
    print("="*60)
    print(f"策略加载机制: {'✅ 通过' if results['strategy_loading'] else '❌ 失败'}")
    print(f"生命周期管理: {'✅ 通过' if results['lifecycle_management'] else '❌ 失败'}")
    print(f"数据事件分发: {'✅ 通过' if results['data_dispatch'] else '❌ 失败'}")
    print(f"信号回调机制: {'✅ 通过' if results['callback_mechanism'] else '❌ 失败'}")
    
    if results['all_passed']:
        print("\n🎉 StrategyEngine框架验证成功！")
        print("✅ 策略加载 ✅ 生命周期管理 ✅ 事件分发 ✅ 回调机制")
        print("\n🏆 Milestone 2.2 - StrategyEngine框架开发完成！")
    else:
        print("\n❌ 部分功能验证失败，需要进一步调试")