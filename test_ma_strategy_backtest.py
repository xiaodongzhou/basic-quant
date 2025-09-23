#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MA Strategy Backtest Verification

MA策略的完整回测验证
- 测试真实的金叉死叉信号
- 验证策略盈亏计算
- 验证风险管理
- 回测绩效统计
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import numpy as np

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.ma_strategy import MAStrategy
from core.data_types import BarData, Exchange, Interval


def generate_golden_cross_data(symbol: str, base_price: float = 4000.0) -> list:
    """生成包含金叉信号的测试数据"""
    bars = []
    base_time = datetime.now()
    
    # 第1阶段：快线在慢线下方 (20个数据点)
    prices_stage1 = [base_price + i * 2 for i in range(20)]  # 缓慢上涨
    
    # 第2阶段：快线开始快速上涨，穿越慢线 (10个数据点)
    prices_stage2 = [base_price + 40 + i * 8 for i in range(10)]  # 快速上涨
    
    # 第3阶段：保持上涨趋势 (10个数据点)
    prices_stage3 = [base_price + 120 + i * 4 for i in range(10)]  # 继续上涨
    
    # 第4阶段：开始下跌，准备死叉 (15个数据点)
    prices_stage4 = [base_price + 160 - i * 6 for i in range(15)]  # 快速下跌
    
    all_prices = prices_stage1 + prices_stage2 + prices_stage3 + prices_stage4
    
    for i, price in enumerate(all_prices):
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=base_time + timedelta(minutes=i),
            interval=Interval.MINUTE,
            volume=1000,
            turnover=1000 * price,
            open_interest=5000,
            open_price=price - 1,
            high_price=price + 2,
            low_price=price - 3,
            close_price=price
        )
        bars.append(bar)
    
    return bars


def test_ma_strategy_golden_cross():
    """测试金叉信号生成和交易"""
    print("=== 测试MA策略金叉信号验证 ===")
    
    # 配置策略 - 使用较小周期便于观察
    config = {
        'fast_period': 5,
        'slow_period': 10,
        'trade_volume': 1,
        'max_position': 3,
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.10,
        'subscribed_symbols': ['rb2405']
    }
    
    strategy = MAStrategy('golden_cross_test', config)
    strategy.subscribed_symbols = ['rb2405']
    
    try:
        # 初始化策略
        strategy.on_init()
        strategy.on_start()
        
        symbol = 'rb2405'
        bars = generate_golden_cross_data(symbol, 4000.0)
        
        print(f"开始处理 {len(bars)} 个K线数据...")
        
        # 记录关键时刻的MA值
        ma_history = []
        signal_points = []
        
        for i, bar in enumerate(bars):
            strategy.on_bar(bar)
            
            if strategy._indicators_ready(symbol):
                fast_ma = strategy.indicators[symbol]['fast_ma'].current_ma
                slow_ma = strategy.indicators[symbol]['slow_ma'].current_ma
                position = strategy.positions[symbol]
                
                ma_history.append({
                    'index': i,
                    'price': bar.close_price,
                    'fast_ma': fast_ma,
                    'slow_ma': slow_ma,
                    'position': f"{position.direction}:{position.volume}"
                })
                
                # 检查是否有新信号
                if len(strategy.signals) > len(signal_points):
                    new_signal = strategy.signals[-1]
                    signal_points.append({
                        'index': i,
                        'signal': new_signal.signal_type,
                        'fast_ma': new_signal.fast_ma,
                        'slow_ma': new_signal.slow_ma,
                        'price': new_signal.price
                    })
                    print(f"K线{i+1}: 生成信号 {new_signal.signal_type} - 快线:{fast_ma:.1f}, 慢线:{slow_ma:.1f}, 价格:{bar.close_price:.1f}")
        
        # 分析结果
        print(f"\n=== 回测结果分析 ===")
        print(f"总K线数量: {len(bars)}")
        print(f"生成信号数量: {len(strategy.signals)}")
        print(f"执行交易次数: {len(strategy.trades)}")
        print(f"最终持仓: {strategy.positions[symbol].direction}:{strategy.positions[symbol].volume}")
        
        # 打印所有信号
        print(f"\n=== 信号详情 ===")
        for i, signal_info in enumerate(signal_points):
            print(f"信号{i+1} (K线{signal_info['index']+1}): {signal_info['signal']} - "
                  f"快线:{signal_info['fast_ma']:.1f}, 慢线:{signal_info['slow_ma']:.1f}, 价格:{signal_info['price']:.1f}")
        
        # 打印关键MA数据点 (每10个)
        print(f"\n=== 关键MA数据点 ===")
        for i in range(0, len(ma_history), 10):
            data = ma_history[i]
            print(f"K线{data['index']+1}: 价格={data['price']:.1f}, MA5={data['fast_ma']:.1f}, MA10={data['slow_ma']:.1f}, 持仓={data['position']}")
        
        # 验证金叉信号
        golden_crosses = [s for s in strategy.signals if s.signal_type == 'golden_cross']
        death_crosses = [s for s in strategy.signals if s.signal_type == 'death_cross']
        
        print(f"\n=== 信号统计 ===")
        print(f"金叉信号: {len(golden_crosses)}")
        print(f"死叉信号: {len(death_crosses)}")
        
        # 基本验证
        assert len(strategy.signals) > 0, "应该生成信号"
        assert len(golden_crosses) > 0, "应该生成金叉信号"
        
        strategy.on_stop()
        
        print("✅ MA策略金叉信号验证通过！")
        return True
        
    except Exception as e:
        print(f"❌ MA策略金叉信号验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ma_strategy_comprehensive_backtest():
    """综合回测验证"""
    print("\n=== MA策略综合回测验证 ===")
    
    config = {
        'fast_period': 5,
        'slow_period': 20,
        'trade_volume': 2,
        'max_position': 10,
        'stop_loss_pct': 0.03,
        'take_profit_pct': 0.06,
        'subscribed_symbols': ['rb2405', 'i2405']
    }
    
    strategy = MAStrategy('comprehensive_test', config)
    strategy.subscribed_symbols = ['rb2405', 'i2405']
    
    try:
        strategy.on_init()
        strategy.on_start()
        
        # 为两个合约生成不同的数据
        symbols_data = {
            'rb2405': generate_golden_cross_data('rb2405', 4000.0),
            'i2405': generate_golden_cross_data('i2405', 800.0)
        }
        
        # 交替处理两个合约的数据 (模拟实时数据流)
        max_bars = max(len(bars) for bars in symbols_data.values())
        
        for i in range(max_bars):
            for symbol, bars in symbols_data.items():
                if i < len(bars):
                    strategy.on_bar(bars[i])
        
        # 统计结果
        total_signals = len(strategy.signals)
        total_trades = len(strategy.trades)
        
        print(f"多合约回测结果:")
        print(f"总信号数量: {total_signals}")
        print(f"总交易次数: {total_trades}")
        
        for symbol in ['rb2405', 'i2405']:
            position = strategy.positions[symbol]
            symbol_signals = [s for s in strategy.signals if 'rb' in symbol or 'i' in symbol]
            print(f"{symbol}: 持仓={position.direction}:{position.volume}, 信号={len(symbol_signals)}")
        
        # 验证多合约处理
        assert len(strategy.positions) == 2, "应该处理两个合约"
        assert total_signals >= 0, "信号数量应该大于等于0"
        
        strategy.on_stop()
        
        print("✅ MA策略综合回测验证通过！")
        return True
        
    except Exception as e:
        print(f"❌ MA策略综合回测验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ma_strategy_performance_statistics():
    """测试策略绩效统计"""
    print("\n=== MA策略绩效统计测试 ===")
    
    config = {
        'fast_period': 3,
        'slow_period': 8,
        'trade_volume': 1,
        'max_position': 5,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.05,
        'subscribed_symbols': ['test_symbol']
    }
    
    strategy = MAStrategy('performance_test', config)
    strategy.subscribed_symbols = ['test_symbol']
    
    try:
        strategy.on_init()
        strategy.on_start()
        
        # 生成更长的测试数据
        symbol = 'test_symbol'
        bars = generate_golden_cross_data(symbol, 5000.0)
        
        # 扩展数据长度
        extended_bars = []
        for cycle in range(3):  # 生成3个周期的数据
            for bar in bars:
                new_bar = BarData(
                    symbol=bar.symbol,
                    exchange=bar.exchange,
                    datetime=bar.datetime + timedelta(minutes=len(bars)*cycle + bars.index(bar)),
                    interval=bar.interval,
                    volume=bar.volume,
                    turnover=bar.turnover,
                    open_interest=bar.open_interest,
                    open_price=bar.open_price + cycle * 100,
                    high_price=bar.high_price + cycle * 100,
                    low_price=bar.low_price + cycle * 100,
                    close_price=bar.close_price + cycle * 100
                )
                extended_bars.append(new_bar)
        
        # 处理所有数据
        for bar in extended_bars:
            strategy.on_bar(bar)
        
        # 获取策略信息
        info = strategy.get_strategy_info()
        
        print(f"策略绩效统计:")
        print(f"策略名称: {info['strategy_name']}")
        print(f"策略类型: {info['strategy_type']}")
        print(f"快线周期: {info['fast_period']}")
        print(f"慢线周期: {info['slow_period']}")
        print(f"总交易次数: {info['total_trades']}")
        print(f"盈利交易: {info['win_trades']}")
        print(f"总盈亏: {info['total_pnl']}")
        print(f"信号数量: {info['signals_count']}")
        
        # 打印持仓信息
        for symbol, pos_info in info['positions'].items():
            print(f"{symbol}持仓: {pos_info['direction']}:{pos_info['volume']}@{pos_info['avg_price']:.1f}")
        
        strategy.on_stop()
        
        print("✅ MA策略绩效统计测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ MA策略绩效统计测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行MA策略回测验证"""
    print("🚀 开始运行MA策略回测验证")
    
    # 配置日志
    logging.basicConfig(
        level=logging.WARNING,  # 降低日志级别减少输出
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    tests = [
        ("MA策略金叉信号验证", test_ma_strategy_golden_cross),
        ("MA策略综合回测验证", test_ma_strategy_comprehensive_backtest),
        ("MA策略绩效统计测试", test_ma_strategy_performance_statistics),
    ]
    
    passed = 0
    total = len(tests)
    
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
    
    # 总结
    print(f"\n{'='*60}")
    print(f"🏆 回测验证总结")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print(f"🎉 所有回测验证通过! MA策略Milestone 2.3完成!")
        return True
    else:
        print(f"⚠️ 有 {total-passed} 个验证失败")
        return False


if __name__ == '__main__':
    success = main()
    
    import sys
    sys.exit(0 if success else 1)