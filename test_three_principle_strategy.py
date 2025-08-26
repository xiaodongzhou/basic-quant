#!/usr/bin/env python3
"""
三原则策略测试脚本
测试方向-位置-信号三原则策略框架的完整功能
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from strategies.trend_following_strategy import TrendFollowingStrategy, BreakoutStrategy, MeanReversionStrategy
from strategies.three_principle_strategy import TrendDirection, SignalType, Position

def create_sample_data(symbol: str = "TESTUSDT", days: int = 100) -> pd.DataFrame:
    """创建测试数据"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days*24, freq='h')
    
    # 生成带趋势的价格数据 - 修复指数增长问题
    np.random.seed(42)
    base_price = 50000
    
    # 减少趋势和噪声的大小以避免指数爆炸
    total_trend = 0.2  # 总共20%的趋势
    trend_per_period = total_trend / len(dates)  # 每期的小幅趋势
    noise_std = 0.005  # 降低噪声标准差到0.5%
    
    # 生成更稳定的价格序列
    prices = [base_price]
    for i in range(1, len(dates)):
        # 小幅趋势 + 小幅随机变动
        change = trend_per_period + np.random.normal(0, noise_std)
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # 生成OHLCV数据
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        open_price = close * (1 + np.random.normal(0, 0.001))
        high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.005)))
        low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.005)))
        volume = np.random.uniform(1000, 5000)
        
        data.append({
            'datetime': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)
    
    return df

def test_trend_following_strategy():
    """测试趋势跟踪策略"""
    print("=" * 60)
    print("🔥 测试趋势跟踪策略")
    print("=" * 60)
    
    try:
        # 创建策略实例
        strategy = TrendFollowingStrategy(
            name="趋势跟踪测试",
            symbol="TESTUSDT",
            parameters={
                'ma_short_period': 5,
                'ma_long_period': 20,
                'atr_period': 10,
                'volume': 1.0,
                'account_balance': 100000
            }
        )
        
        # 生成测试数据
        df = create_sample_data("TESTUSDT", 30)
        print(f"  📊 生成测试数据: {len(df)} 条记录")
        
        # 启动策略
        strategy.start()
        
        # 逐条输入数据
        signal_count = 0
        for i, (timestamp, row) in enumerate(df.iterrows()):
            bar = {
                'datetime': timestamp,
                'open_price': row['open'],
                'high_price': row['high'],
                'low_price': row['low'], 
                'close_price': row['close'],
                'volume': row['volume']
            }
            
            strategy.add_bar(bar)
            
            # 每50个Bar输出一次状态
            if i > 0 and i % 50 == 0:
                status = strategy.get_strategy_status()
                print(f"  📈 进度 {i}/{len(df)}: 方向={status['current_direction']}, 仓位={status['position_status']}")
                
                if len(strategy.signals_history) > signal_count:
                    signal_count = len(strategy.signals_history)
                    latest_signal = strategy.signals_history[-1]
                    print(f"      🎯 新信号: {latest_signal.signal_type.value} @ {latest_signal.price:.2f}")
        
        # 输出最终结果
        final_status = strategy.get_strategy_status()
        print(f"\n  ✅ 策略测试完成:")
        print(f"     总信号数: {final_status['total_signals']}")
        print(f"     总交易数: {final_status['total_trades']}")
        print(f"     胜率: {final_status['win_rate']:.2%}")
        print(f"     总盈亏: ${final_status['total_pnl']:.2f}")
        print(f"     当前方向: {final_status['current_direction']}")
        
        # 显示交易记录
        if strategy.trades_history:
            print(f"\n  📋 交易记录:")
            for trade in strategy.trades_history[-3:]:  # 显示最后3笔交易
                print(f"     {trade['type']}: {trade.get('size', 0):.3f} @ ${trade['price']:.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"趋势跟踪策略测试失败: {e}")
        return False

def test_breakout_strategy():
    """测试突破策略"""
    print("\n" + "=" * 60)
    print("🚀 测试突破策略")
    print("=" * 60)
    
    try:
        # 创建突破策略实例
        strategy = BreakoutStrategy(
            name="突破测试",
            symbol="TESTSTOCK",
            parameters={
                'breakout_threshold': 0.005,  # 0.5%突破阈值
                'volume_multiplier': 1.3,
                'volume': 1.0,
                'account_balance': 100000
            }
        )
        
        # 生成震荡后突破的数据
        df = create_sample_data("TESTSTOCK", 20)
        
        # 在数据中间添加一些突破模式
        mid_point = len(df) // 2
        df.iloc[mid_point:mid_point+10, df.columns.get_loc('close')] *= 1.1  # 10%突破
        
        print(f"  📊 生成突破测试数据: {len(df)} 条记录")
        
        strategy.start()
        
        signal_count = 0
        for i, (timestamp, row) in enumerate(df.iterrows()):
            bar = {
                'datetime': timestamp,
                'open_price': row['open'],
                'high_price': row['high'],
                'low_price': row['low'],
                'close_price': row['close'],
                'volume': row['volume']
            }
            
            strategy.add_bar(bar)
            
            # 检查新信号
            if len(strategy.signals_history) > signal_count:
                signal_count = len(strategy.signals_history)
                latest_signal = strategy.signals_history[-1]
                print(f"  🎯 第{i}根K线 新信号: {latest_signal.signal_type.value} @ {latest_signal.price:.2f}")
                print(f"      原因: {latest_signal.reason}")
        
        # 输出结果
        final_status = strategy.get_strategy_status()
        print(f"\n  ✅ 突破策略测试完成:")
        print(f"     总信号数: {final_status['total_signals']}")
        print(f"     总交易数: {final_status['total_trades']}")
        print(f"     总盈亏: ${final_status['total_pnl']:.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"突破策略测试失败: {e}")
        return False

def test_mean_reversion_strategy():
    """测试均值回归策略"""
    print("\n" + "=" * 60)
    print("🔄 测试均值回归策略") 
    print("=" * 60)
    
    try:
        # 创建均值回归策略
        strategy = MeanReversionStrategy(
            name="均值回归测试",
            symbol="TESTSTOCK2",
            parameters={
                'ma_period': 15,
                'rsi_period': 10,
                'mean_reversion_threshold': 0.03,  # 3%偏离阈值
                'volume': 1.0,
                'account_balance': 100000
            }
        )
        
        # 生成均值回归数据（围绕均值震荡）
        dates = pd.date_range(start=datetime.now() - timedelta(days=20), periods=480, freq='h')
        base_price = 100
        
        # 生成均值回归模式的价格
        prices = []
        for i in range(len(dates)):
            # 使用正弦波 + 随机噪声模拟均值回归
            sine_wave = np.sin(i / 20) * 0.05  # 5%幅度的正弦波
            noise = np.random.normal(0, 0.01)   # 1%噪声
            price = base_price * (1 + sine_wave + noise)
            prices.append(price)
        
        # 构建DataFrame
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            open_price = close * (1 + np.random.normal(0, 0.001))
            high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.002)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.002)))
            volume = np.random.uniform(500, 2000)
            
            data.append({
                'datetime': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('datetime', inplace=True)
        
        print(f"  📊 生成均值回归数据: {len(df)} 条记录")
        
        strategy.start()
        
        deviation_alerts = 0
        for i, (timestamp, row) in enumerate(df.iterrows()):
            bar = {
                'datetime': timestamp,
                'open_price': row['open'],
                'high_price': row['high'],
                'low_price': row['low'],
                'close_price': row['close'],
                'volume': row['volume']
            }
            
            strategy.add_bar(bar)
            
            # 检查价格偏离情况
            if i > 20:  # 有足够数据后开始检查
                if 'price_deviation' in strategy.indicators:
                    deviation = strategy.indicators['price_deviation']
                    if abs(deviation) > 0.03 and deviation_alerts < 5:  # 只输出前5次
                        print(f"  ⚠️  价格偏离均值 {deviation:.2%} @ 第{i}根K线")
                        deviation_alerts += 1
        
        # 输出结果
        final_status = strategy.get_strategy_status()
        print(f"\n  ✅ 均值回归策略测试完成:")
        print(f"     总信号数: {final_status['total_signals']}")
        print(f"     总交易数: {final_status['total_trades']}")
        print(f"     总盈亏: ${final_status['total_pnl']:.2f}")
        
        # 显示布林带信息
        if 'bollinger_upper' in strategy.indicators and strategy.indicators['bollinger_upper']:
            upper = strategy.indicators['bollinger_upper'][-1]
            lower = strategy.indicators['bollinger_lower'][-1]
            middle = strategy.indicators['bollinger_middle'][-1]
            current_price = df['close'].iloc[-1]
            
            print(f"\n  📊 布林带状态:")
            print(f"     上轨: ${upper:.2f}")
            print(f"     中轨: ${middle:.2f}")
            print(f"     下轨: ${lower:.2f}")
            print(f"     当前价格: ${current_price:.2f}")
            
            if current_price > upper:
                print(f"     🔴 价格突破上轨（超买）")
            elif current_price < lower:
                print(f"     🟢 价格跌破下轨（超卖）")
            else:
                print(f"     ⚪ 价格在布林带内")
        
        return True
        
    except Exception as e:
        logger.error(f"均值回归策略测试失败: {e}")
        return False

def test_strategy_components():
    """测试策略组件的独立功能"""
    print("\n" + "=" * 60)
    print("🔧 测试策略组件")
    print("=" * 60)
    
    try:
        from strategies.components.direction_analyzers import MultiIndicatorDirectionAnalyzer
        from strategies.components.position_managers import ATRPositionManager
        from strategies.components.signal_generators import PriceActionSignalGenerator
        
        # 测试数据 - 使用更多数据以获得稳定的ATR计算
        df = create_sample_data("COMPONENTTEST", 30)
        
        # 1. 测试方向分析器
        print("  🧭 测试方向分析器...")
        direction_analyzer = MultiIndicatorDirectionAnalyzer(rsi_period=10)
        direction = direction_analyzer.analyze_direction(df)
        confidence = direction_analyzer.get_direction_confidence()
        
        print(f"     方向: {direction.value}, 置信度: {confidence:.2f}")
        
        # 2. 测试位置管理器
        print("  📍 测试位置管理器...")
        position_manager = ATRPositionManager(atr_period=10)
        entry_levels = position_manager.calculate_entry_position(df, direction)
        
        if entry_levels:
            print(f"     入场价: ${entry_levels.get('entry_price', 0):.2f}")
            print(f"     止损价: ${entry_levels.get('stop_loss', 0):.2f}")
            print(f"     目标价: ${entry_levels.get('take_profit', 0):.2f}")
        else:
            print("     ⚠️ 无法计算入场位置")
        
        # 3. 测试信号生成器
        print("  🎯 测试信号生成器...")
        signal_generator = PriceActionSignalGenerator(min_confidence=0.5)
        
        if entry_levels:
            signal = signal_generator.generate_signal(
                df=df,
                direction=direction,
                entry_levels=entry_levels,
                exit_levels={}
            )
            
            print(f"     信号类型: {signal.signal_type.value}")
            print(f"     信号置信度: {signal.confidence:.2f}")
            print(f"     信号原因: {signal.reason}")
        
        print("  ✅ 组件测试完成")
        return True
        
    except Exception as e:
        logger.error(f"组件测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 三原则策略框架测试开始")
    
    # 配置日志
    logger.add("logs/test_three_principle.log", rotation="1 day")
    Path("logs").mkdir(exist_ok=True)
    
    tests = [
        ("趋势跟踪策略", test_trend_following_strategy),
        ("突破策略", test_breakout_strategy),
        ("均值回归策略", test_mean_reversion_strategy),
        ("策略组件", test_strategy_components),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            
        except Exception as e:
            logger.error(f"{test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name:15} {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总计: {passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！三原则策略框架工作正常。")
        print("\n💡 使用方法:")
        print("   python main.py backtest --strategy trend --symbol BTCUSDT")
        print("   python main.py backtest --strategy breakout --symbol AAPL")
        print("   python main.py backtest --strategy meanrev --symbol 000001.SZ")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")

if __name__ == "__main__":
    main()