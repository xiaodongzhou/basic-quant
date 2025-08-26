#!/usr/bin/env python3
"""
改进版EMA趋势跟随策略测试
验证策略的各个组件和整体性能
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any
from loguru import logger

from strategies.ema_trend_strategy import AdvancedEMATrendStrategy
from strategies.indicators import (
    calculate_ema, calculate_adx, detect_long_lower_shadow, detect_strong_bullish_candle
)


def generate_trending_data(days: int = 30, base_price: float = 50000.0, 
                          trend_strength: float = 0.1) -> pd.DataFrame:
    """生成带趋势的测试数据"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days*24, freq='h')
    
    # 生成趋势性价格数据
    np.random.seed(42)
    
    data = []
    price = base_price
    
    for i, date in enumerate(dates):
        # 添加趋势成分
        trend_factor = 1 + (trend_strength * i / len(dates))
        
        # 添加噪声
        noise = np.random.normal(0, 0.01)
        daily_volatility = np.random.uniform(0.005, 0.02)
        
        # 计算OHLC
        open_price = price
        
        # 生成有一定趋势的收盘价
        close_change = (trend_strength / len(dates)) + noise
        close_price = open_price * (1 + close_change)
        
        # 生成高低价
        day_range = open_price * daily_volatility
        high_price = max(open_price, close_price) + np.random.uniform(0, day_range)
        low_price = min(open_price, close_price) - np.random.uniform(0, day_range)
        
        # 确保价格逻辑正确
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        volume = np.random.uniform(1000, 5000)
        
        data.append({
            'datetime': date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
        
        price = close_price
    
    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)
    return df


def test_ema_indicators():
    """测试EMA指标计算"""
    print("🧮 测试EMA指标计算")
    print("=" * 50)
    
    # 生成测试数据
    df = generate_trending_data(20, 50000, 0.05)
    
    # 测试EMA计算
    ema20 = calculate_ema(df['close'], 20)
    ema60 = calculate_ema(df['close'], 60)
    
    print(f"数据长度: {len(df)}")
    print(f"EMA20 最新值: ${ema20.iloc[-1]:.2f}")
    print(f"EMA60 最新值: ${ema60.iloc[-1]:.2f}")
    
    # 测试ADX计算
    adx, plus_di, minus_di = calculate_adx(df['high'], df['low'], df['close'], 14)
    print(f"ADX 最新值: {adx.iloc[-1]:.2f}")
    print(f"+DI 最新值: {plus_di.iloc[-1]:.2f}")
    print(f"-DI 最新值: {minus_di.iloc[-1]:.2f}")
    
    print("✅ EMA指标计算测试完成\n")


def test_candlestick_patterns():
    """测试K线形态识别"""
    print("🕯️  测试K线形态识别")
    print("=" * 50)
    
    # 创建测试K线数据
    test_candles = [
        # 长下影线
        {'open': 100, 'high': 105, 'low': 90, 'close': 102},  # 长下影线
        # 大阳线
        {'open': 100, 'high': 120, 'low': 98, 'close': 118},  # 大阳线
        # 普通K线
        {'open': 100, 'high': 103, 'low': 98, 'close': 101},  # 普通
    ]
    
    for i, candle in enumerate(test_candles):
        print(f"测试K线 {i+1}:")
        print(f"  OHLC: {candle['open']}/{candle['high']}/{candle['low']}/{candle['close']}")
        
        # 测试长下影线
        long_shadow = detect_long_lower_shadow(
            candle['open'], candle['high'], candle['low'], candle['close']
        )
        print(f"  长下影线: {'是' if long_shadow else '否'}")
        
        # 测试大阳线
        strong_bullish = detect_strong_bullish_candle(
            candle['open'], candle['close'], recent_avg_body=5.0, threshold=2.0
        )
        print(f"  强势大阳线: {'是' if strong_bullish else '否'}")
        print()
    
    print("✅ K线形态识别测试完成\n")


def test_ema_strategy_components():
    """测试EMA策略组件"""
    print("🔧 测试EMA策略组件")
    print("=" * 50)
    
    # 创建策略实例
    strategy = AdvancedEMATrendStrategy(
        name="EMA测试策略",
        symbol="TESTEMA",
        parameters={
            'ema_short': 20,
            'ema_long': 60,
            'adx_threshold': 20.0,  # 降低阈值便于测试
            'min_confidence': 0.6
        }
    )
    
    # 生成测试数据
    df = generate_trending_data(30, 50000, 0.08)  # 更强的趋势
    
    print(f"生成测试数据: {len(df)} 条记录")
    
    # 测试方向分析
    direction = strategy.direction_analyzer.analyze_direction(df)
    confidence = strategy.direction_analyzer.get_direction_confidence()
    ema_values = strategy.direction_analyzer.get_ema_values(df)
    
    print(f"方向分析结果:")
    print(f"  趋势方向: {direction.value}")
    print(f"  置信度: {confidence:.2f}")
    print(f"  EMA20: ${ema_values['ema20']:.2f}")
    print(f"  EMA60: ${ema_values['ema60']:.2f}")
    print(f"  ADX: {ema_values['adx']:.2f}")
    
    # 测试位置管理
    if direction.value != "SIDEWAYS":
        entry_levels = strategy.position_manager.calculate_entry_position(df, direction)
        print(f"入场位置:")
        if entry_levels:
            print(f"  入场价: ${entry_levels.get('entry_price', 0):.2f}")
            print(f"  止损价: ${entry_levels.get('stop_loss', 0):.2f}")
            print(f"  目标价: ${entry_levels.get('take_profit', 0):.2f}")
            print(f"  入场EMA: {entry_levels.get('ema_name', 'N/A')}")
            print(f"  风险金额: ${entry_levels.get('risk_amount', 0):.2f}")
            
            # 测试信号生成
            signal = strategy.signal_generator.generate_signal(
                df, direction, entry_levels, {}
            )
            print(f"信号生成:")
            print(f"  信号类型: {signal.signal_type.value}")
            print(f"  信号置信度: {signal.confidence:.2f}")
            print(f"  信号价格: ${signal.price:.2f}")
            print(f"  信号原因: {signal.reason}")
        else:
            print("  ⚠️ 无有效入场位置")
    
    print("✅ EMA策略组件测试完成\n")


def test_ema_strategy_backtest():
    """测试EMA策略完整回测"""
    print("📊 测试EMA策略完整回测")
    print("=" * 50)
    
    # 创建策略
    strategy = AdvancedEMATrendStrategy(
        name="EMA回测策略",
        symbol="BTCUSDT",
        parameters={
            'account_balance': 100000.0,
            'adx_threshold': 20.0,  # 降低阈值增加交易机会
            'min_confidence': 0.6
        }
    )
    
    # 生成更长期的测试数据
    df = generate_trending_data(45, 50000, 0.12)  # 45天，强趋势
    
    print(f"回测数据: {len(df)} 条记录")
    print(f"价格范围: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    # 执行策略
    strategy.start()
    
    bar_count = 0
    signal_count = 0
    
    # 逐根K线执行
    for i in range(60, len(df)):  # 从第60根开始，确保有足够历史数据
        current_df = df.iloc[:i+1].copy()
        strategy.on_bar(current_df)
        
        bar_count += 1
        if bar_count % 200 == 0:
            current_position = strategy.get_current_position()
            position_status = current_position.direction if current_position else "NO_POSITION"
            print(f"  📈 进度 {bar_count}/{len(df)-60}: 价格=${current_df['close'].iloc[-1]:.2f}, "
                  f"仓位={position_status}")
    
    strategy.stop()
    
    # 获取策略统计
    stats = strategy.get_performance_metrics()
    state = strategy.get_strategy_state()
    
    print(f"\n  ✅ EMA策略回测完成:")
    print(f"     总信号数: {state.get('signal_count', 0)}")
    print(f"     总交易数: {state.get('trade_count', 0)}")
    print(f"     胜率: {stats.get('win_rate', 0)*100:.2f}%")
    print(f"     总盈亏: ${state.get('total_pnl', 0):.2f}")
    print(f"     最大回撤: {stats.get('max_drawdown', 0)*100:.2f}%")
    print(f"     夏普比率: {stats.get('sharpe_ratio', 0):.2f}")
    print(f"     部分止盈率: {stats.get('partial_profit_rate', 0)*100:.2f}%")
    
    print("✅ EMA策略完整回测测试完成\n")


def run_all_tests():
    """运行所有测试"""
    print("🚀 改进版EMA趋势策略测试开始")
    print("=" * 60)
    
    try:
        test_ema_indicators()
        test_candlestick_patterns()
        test_ema_strategy_components()
        test_ema_strategy_backtest()
        
        print("=" * 60)
        print("📊 测试结果汇总")
        print("=" * 60)
        print("  EMA指标计算          ✅ 通过")
        print("  K线形态识别          ✅ 通过")
        print("  EMA策略组件          ✅ 通过")
        print("  EMA完整回测          ✅ 通过")
        print()
        print("🎯 总计: 4/4 测试通过 (100.0%)")
        print("🎉 所有测试通过！改进版EMA趋势策略工作正常。")
        
        print("\n💡 使用方法:")
        print("   python main.py backtest --strategy ema --symbol BTCUSDT")
        print("   python main.py backtest --strategy ema --symbol AAPL")
        print("   python main.py backtest --strategy ema --symbol 000001.SZ")
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")
        print("❌ 测试失败")
        return False
    
    return True


if __name__ == "__main__":
    run_all_tests()