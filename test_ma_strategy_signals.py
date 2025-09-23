#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MA Strategy Signals Test

专门测试MA策略信号生成的详细验证
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.ma_strategy import MAStrategy
from core.data_types import BarData, Exchange, Interval


def create_explicit_golden_cross_data(symbol: str) -> list:
    """创建明确的金叉信号数据"""
    bars = []
    base_time = datetime.now()
    
    # 构造明确的金叉场景
    # 快线周期5，慢线周期10
    
    # 第1阶段：让慢线保持高位，快线保持低位 (15个数据点)
    # 使用价格4000让MA10稳定在4000
    for i in range(15):
        price = 4000.0
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=base_time + timedelta(minutes=i),
            interval=Interval.MINUTE,
            volume=1000,
            turnover=1000 * price,
            open_interest=5000,
            open_price=price,
            high_price=price + 1,
            low_price=price - 1,
            close_price=price
        )
        bars.append(bar)
    
    # 第2阶段：快线价格快速上涨，穿越慢线 (10个数据点)
    # 让MA5快速上升超过MA10
    for i in range(10):
        price = 4000.0 + (i + 1) * 20  # 快速上涨
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=base_time + timedelta(minutes=15+i),
            interval=Interval.MINUTE,
            volume=1000,
            turnover=1000 * price,
            open_interest=5000,
            open_price=price - 5,
            high_price=price + 5,
            low_price=price - 10,
            close_price=price
        )
        bars.append(bar)
    
    # 第3阶段：保持高位一段时间 (5个数据点)
    for i in range(5):
        price = 4200.0 + i * 10
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=base_time + timedelta(minutes=25+i),
            interval=Interval.MINUTE,
            volume=1000,
            turnover=1000 * price,
            open_interest=5000,
            open_price=price - 5,
            high_price=price + 5,
            low_price=price - 10,
            close_price=price
        )
        bars.append(bar)
    
    # 第4阶段：快速下跌形成死叉 (10个数据点)
    for i in range(10):
        price = 4240.0 - (i + 1) * 25  # 快速下跌
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=base_time + timedelta(minutes=30+i),
            interval=Interval.MINUTE,
            volume=1000,
            turnover=1000 * price,
            open_interest=5000,
            open_price=price + 5,
            high_price=price + 10,
            low_price=price - 5,
            close_price=price
        )
        bars.append(bar)
    
    return bars


def test_explicit_golden_cross():
    """测试明确的金叉信号"""
    print("=== 测试明确的金叉信号生成 ===")
    
    config = {
        'fast_period': 5,
        'slow_period': 10,
        'trade_volume': 1,
        'max_position': 3,
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.10,
        'subscribed_symbols': ['test_symbol']
    }
    
    strategy = MAStrategy('explicit_golden_test', config)
    strategy.subscribed_symbols = ['test_symbol']
    
    # 配置更详细的日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        strategy.on_init()
        strategy.on_start()
        
        symbol = 'test_symbol'
        bars = create_explicit_golden_cross_data(symbol)
        
        print(f"开始处理 {len(bars)} 个K线数据...")
        
        # 详细记录每个K线的MA变化
        ma_records = []
        
        for i, bar in enumerate(bars):
            strategy.on_bar(bar)
            
            if strategy._indicators_ready(symbol):
                fast_ma = strategy.indicators[symbol]['fast_ma'].current_ma
                slow_ma = strategy.indicators[symbol]['slow_ma'].current_ma
                position = strategy.positions[symbol]
                
                ma_records.append({
                    'bar_num': i + 1,
                    'price': bar.close_price,
                    'fast_ma': fast_ma,
                    'slow_ma': slow_ma,
                    'diff': fast_ma - slow_ma,
                    'position': f"{position.direction}:{position.volume}",
                    'signals_count': len(strategy.signals)
                })
                
                # 如果有新信号，立即打印
                if i > 0 and len(strategy.signals) > ma_records[i-10 if i >= 10 else 0].get('signals_count', 0):
                    latest_signal = strategy.signals[-1]
                    print(f"🚨 K线{i+1}: {latest_signal.signal_type.upper()} - "
                          f"价格:{bar.close_price:.1f}, 快线:{fast_ma:.1f}, 慢线:{slow_ma:.1f}")
        
        # 打印详细的MA变化
        print(f"\n=== 详细MA变化记录 ===")
        for record in ma_records:
            cross_indicator = ""
            if record['diff'] > 0:
                cross_indicator = "快线在上"
            elif record['diff'] < 0:
                cross_indicator = "快线在下"
            else:
                cross_indicator = "快慢线相等"
            
            print(f"K{record['bar_num']:2d}: 价格={record['price']:6.1f}, "
                  f"MA5={record['fast_ma']:6.1f}, MA10={record['slow_ma']:6.1f}, "
                  f"差值={record['diff']:6.1f} ({cross_indicator}), "
                  f"持仓={record['position']:8s}, 信号数={record['signals_count']}")
        
        # 分析信号
        print(f"\n=== 信号分析 ===")
        print(f"总信号数量: {len(strategy.signals)}")
        
        golden_crosses = [s for s in strategy.signals if s.signal_type == 'golden_cross']
        death_crosses = [s for s in strategy.signals if s.signal_type == 'death_cross']
        
        print(f"金叉信号: {len(golden_crosses)}")
        print(f"死叉信号: {len(death_crosses)}")
        
        # 打印所有信号的详细信息
        for i, signal in enumerate(strategy.signals):
            print(f"信号{i+1}: {signal.signal_type} - "
                  f"时间:{signal.timestamp.strftime('%H:%M:%S')}, "
                  f"快线:{signal.fast_ma:.1f}, 慢线:{signal.slow_ma:.1f}, "
                  f"价格:{signal.price:.1f}")
        
        strategy.on_stop()
        
        # 验证结果
        has_golden_cross = len(golden_crosses) > 0
        has_death_cross = len(death_crosses) > 0
        
        print(f"\n=== 验证结果 ===")
        print(f"✅ 金叉信号: {'有' if has_golden_cross else '无'}")
        print(f"✅ 死叉信号: {'有' if has_death_cross else '无'}")
        
        # 期望至少有一个金叉信号
        if has_golden_cross:
            print("🎉 金叉信号生成测试通过！")
            return True
        else:
            print("⚠️ 未检测到预期的金叉信号")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_cross_detection():
    """简单的交叉检测测试"""
    print("\n=== 简单交叉检测测试 ===")
    
    config = {
        'fast_period': 2,  # 极简周期便于测试
        'slow_period': 4,
        'trade_volume': 1,
        'max_position': 2,
        'subscribed_symbols': ['simple_test']
    }
    
    strategy = MAStrategy('simple_cross_test', config)
    strategy.subscribed_symbols = ['simple_test']
    
    try:
        strategy.on_init()
        strategy.on_start()
        
        symbol = 'simple_test'
        base_time = datetime.now()
        
        # 手动构造明确的交叉场景
        test_prices = [
            100, 100, 100, 100,  # MA2=100, MA4=100
            100, 100,             # 保持相等
            110, 120,             # 快速上涨，MA2应该快速上升
            130, 140,             # 继续上涨
            90, 80,               # 快速下跌，应该形成死叉
            70, 60                # 继续下跌
        ]
        
        print(f"测试价格序列: {test_prices}")
        
        for i, price in enumerate(test_prices):
            bar = BarData(
                symbol=symbol,
                exchange=Exchange.SHFE,
                datetime=base_time + timedelta(minutes=i),
                interval=Interval.MINUTE,
                volume=1000,
                turnover=1000 * price,
                open_interest=5000,
                open_price=price,
                high_price=price + 1,
                low_price=price - 1,
                close_price=price
            )
            
            strategy.on_bar(bar)
            
            if strategy._indicators_ready(symbol):
                fast_ma = strategy.indicators[symbol]['fast_ma'].current_ma
                slow_ma = strategy.indicators[symbol]['slow_ma'].current_ma
                
                print(f"K{i+1:2d}: 价格={price:3d}, MA2={fast_ma:6.1f}, MA4={slow_ma:6.1f}, "
                      f"信号数={len(strategy.signals)}")
        
        print(f"\n生成的信号:")
        for signal in strategy.signals:
            print(f"- {signal.signal_type}: 快线={signal.fast_ma:.1f}, 慢线={signal.slow_ma:.1f}")
        
        strategy.on_stop()
        
        return len(strategy.signals) > 0
        
    except Exception as e:
        print(f"❌ 简单测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始MA策略信号生成专项测试")
    
    tests = [
        ("明确金叉信号测试", test_explicit_golden_cross),
        ("简单交叉检测测试", test_simple_cross_detection),
    ]
    
    passed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
    
    print(f"\n{'='*60}")
    print(f"🏆 专项测试总结: {passed}/{len(tests)} 通过")
    
    return passed == len(tests)


if __name__ == '__main__':
    success = main()
    
    import sys
    sys.exit(0 if success else 1)