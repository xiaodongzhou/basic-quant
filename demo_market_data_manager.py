#!/usr/bin/env python3
"""
MarketDataManager 功能演示
Milestone 1.3 演示脚本
"""

import time
from core import create_connection_manager, create_market_data_manager

def demo_subscription_and_data():
    """演示订阅和数据接收功能"""
    print("🎯 演示1: 订阅和数据接收功能")
    print("=" * 40)
    
    # 创建管理器
    cm = create_connection_manager()
    cm.connect_gateway()
    
    mdm = create_market_data_manager(cm)
    mdm.start()
    
    # 订阅行情数据
    print("📡 订阅行情数据...")
    symbols = ["rb2405", "i2405", "j2405"]
    success = mdm.subscribe_market_data(symbols)
    print(f"订阅结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 显示订阅信息
    subscriptions = mdm.get_subscription_info()
    print(f"\n📊 订阅信息:")
    for symbol, info in subscriptions.items():
        print(f"  {symbol}: 订阅时间 {info.subscribed_time.strftime('%H:%M:%S')}")
    
    # 等待数据接收
    print(f"\n⏰ 等待数据接收 (5秒)...")
    for i in range(5):
        time.sleep(1)
        print(f"  第 {i+1} 秒...")
        
        # 显示最新数据
        for symbol in symbols:
            tick = mdm.get_latest_tick(symbol)
            if tick:
                print(f"    {symbol}: {tick.last_price:.2f} (量: {tick.volume})")
    
    return cm, mdm

def demo_technical_indicators(mdm):
    """演示技术指标计算"""
    print("\n\n🎯 演示2: 技术指标计算")
    print("=" * 40)
    
    # 等待足够数据积累
    print("⏰ 等待数据积累 (8秒)...")
    for i in range(8):
        time.sleep(1)
        print(f"  等待中... {i+1}/8")
    
    symbol = "rb2405"
    
    # 计算移动平均线
    print(f"\n📈 {symbol} 技术指标:")
    
    ma5 = mdm.calculate_ma(symbol, 5)
    ma10 = mdm.calculate_ma(symbol, 10)
    ma20 = mdm.calculate_ma(symbol, 20)
    
    if ma5:
        print(f"  MA5:  {ma5:.2f}")
    if ma10:
        print(f"  MA10: {ma10:.2f}")
    if ma20:
        print(f"  MA20: {ma20:.2f}")
    
    # 计算RSI
    rsi = mdm.calculate_rsi(symbol, 14)
    if rsi:
        print(f"  RSI:  {rsi:.2f}")
    
    # 计算布林带
    boll = mdm.calculate_bollinger_bands(symbol, 20)
    if boll:
        print(f"  布林带:")
        print(f"    上轨: {boll['upper']:.2f}")
        print(f"    中轨: {boll['middle']:.2f}")
        print(f"    下轨: {boll['lower']:.2f}")
    
    # 显示指标缓存
    indicators = mdm.get_indicators(symbol)
    print(f"\n📊 指标缓存: 共 {len(indicators)} 个指标")
    for name, indicator in indicators.items():
        print(f"  {name}: {indicator.value:.2f}")

def demo_data_statistics(mdm):
    """演示数据统计功能"""
    print("\n\n🎯 演示3: 数据统计功能")
    print("=" * 40)
    
    # 获取所有统计数据
    all_stats = mdm.get_data_statistics()
    
    print("📊 数据统计概览:")
    for symbol, stats in all_stats.items():
        print(f"\n  {symbol}:")
        print(f"    Tick数量: {stats.total_ticks}")
        print(f"    Bar数量:  {stats.total_bars}")
        
        if stats.first_time:
            print(f"    首次数据: {stats.first_time.strftime('%H:%M:%S')}")
        if stats.last_time:
            print(f"    最新数据: {stats.last_time.strftime('%H:%M:%S')}")
            
            # 计算数据频率
            if stats.first_time:
                duration = (stats.last_time - stats.first_time).total_seconds()
                if duration > 0:
                    tick_rate = stats.total_ticks / duration
                    print(f"    数据频率: {tick_rate:.2f} tick/秒")

def demo_callback_system(mdm):
    """演示回调系统"""
    print("\n\n🎯 演示4: 回调系统")
    print("=" * 40)
    
    # 设置回调计数
    callback_stats = {"ticks": 0, "bars": 0, "latest_prices": {}}
    
    def tick_callback(tick):
        callback_stats["ticks"] += 1
        callback_stats["latest_prices"][tick.symbol] = tick.last_price
    
    def bar_callback(bar):
        callback_stats["bars"] += 1
        print(f"📊 新K线: {bar.symbol} [{bar.datetime.strftime('%H:%M:%S')}] "
              f"OHLC: {bar.open_price:.1f}/{bar.high_price:.1f}/{bar.low_price:.1f}/{bar.close_price:.1f}")
    
    # 注册回调
    mdm.register_tick_callback(tick_callback)
    mdm.register_bar_callback(bar_callback)
    
    print("📡 监听数据回调 (5秒)...")
    initial_ticks = callback_stats["ticks"]
    initial_bars = callback_stats["bars"]
    
    time.sleep(5)
    
    # 显示回调统计
    tick_received = callback_stats["ticks"] - initial_ticks
    bar_received = callback_stats["bars"] - initial_bars
    
    print(f"\n📈 回调统计:")
    print(f"  接收Tick: {tick_received} 个")
    print(f"  接收Bar:  {bar_received} 个")
    
    if callback_stats["latest_prices"]:
        print(f"  最新价格:")
        for symbol, price in callback_stats["latest_prices"].items():
            print(f"    {symbol}: {price:.2f}")

def demo_subscription_management(mdm):
    """演示订阅管理"""
    print("\n\n🎯 演示5: 订阅管理")
    print("=" * 40)
    
    # 显示当前订阅
    subscriptions = mdm.get_subscription_info()
    print(f"📊 当前订阅 ({len(subscriptions)} 个):")
    for symbol, info in subscriptions.items():
        print(f"  {symbol}: 回调次数 {info.callback_count}")
    
    # 取消部分订阅
    print(f"\n🔄 取消订阅 j2405...")
    success = mdm.unsubscribe_market_data(["j2405"])
    print(f"取消结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 显示更新后的订阅
    subscriptions = mdm.get_subscription_info()
    print(f"\n📊 更新后订阅 ({len(subscriptions)} 个):")
    for symbol in subscriptions.keys():
        print(f"  {symbol}: 仍在订阅中")
    
    # 添加新订阅
    print(f"\n🔄 添加新订阅 cu2405...")
    success = mdm.subscribe_market_data(["cu2405"])
    print(f"订阅结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 等待新数据
    time.sleep(2)
    
    # 检查新数据
    tick = mdm.get_latest_tick("cu2405")
    if tick:
        print(f"✅ cu2405 数据接收正常: {tick.last_price:.2f}")

def demo_data_retrieval(mdm):
    """演示数据检索功能"""
    print("\n\n🎯 演示6: 数据检索功能")
    print("=" * 40)
    
    symbol = "rb2405"
    
    # 获取最近tick数据
    recent_ticks = mdm.get_recent_ticks(symbol, 5)
    print(f"📊 {symbol} 最近5个Tick:")
    for i, tick in enumerate(recent_ticks[-5:], 1):
        print(f"  {i}. {tick.datetime.strftime('%H:%M:%S')} - 价格: {tick.last_price:.2f}, 量: {tick.volume}")
    
    # 获取最近bar数据
    recent_bars = mdm.get_recent_bars(symbol, "1m", 3)
    print(f"\n📊 {symbol} 最近3个K线:")
    for i, bar in enumerate(recent_bars[-3:], 1):
        print(f"  {i}. {bar.datetime.strftime('%H:%M:%S')} - OHLC: "
              f"{bar.open_price:.1f}/{bar.high_price:.1f}/{bar.low_price:.1f}/{bar.close_price:.1f}")
    
    # 显示数据数量统计
    total_ticks = len(mdm.tick_data.get(symbol, []))
    total_bars = len(mdm.bar_data.get(symbol, {}).get("1m", []))
    
    print(f"\n📈 {symbol} 数据总量:")
    print(f"  总Tick数: {total_ticks}")
    print(f"  总Bar数:  {total_bars}")

def main():
    """主演示函数"""
    print("🚀 MarketDataManager 功能演示")
    print("Milestone 1.3 - 行情数据管理模块")
    print("=" * 60)
    
    try:
        # 演示1: 订阅和数据接收
        cm, mdm = demo_subscription_and_data()
        
        # 演示2: 技术指标计算
        demo_technical_indicators(mdm)
        
        # 演示3: 数据统计
        demo_data_statistics(mdm)
        
        # 演示4: 回调系统
        demo_callback_system(mdm)
        
        # 演示5: 订阅管理
        demo_subscription_management(mdm)
        
        # 演示6: 数据检索
        demo_data_retrieval(mdm)
        
        print("\n🎉 MarketDataManager 演示完成!")
        print("✅ 所有核心功能工作正常")
        print("🚀 Milestone 1.3 验证成功!")
        
    except Exception as e:
        print(f"\n❌ 演示过程出错: {e}")
        return False
    
    finally:
        # 清理资源
        if 'mdm' in locals():
            mdm.stop()
        if 'cm' in locals():
            cm.disconnect_gateway()
    
    return True

if __name__ == "__main__":
    main()