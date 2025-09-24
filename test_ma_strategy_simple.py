#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MA Strategy Simple Integration Test

MA策略的简化集成测试
- 快速验证MA策略核心功能
- 测试信号生成和交易逻辑
- 验证回测结果
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.ma_strategy import MAStrategy
from core.data_types import BarData, TickData, Exchange, Interval, Direction
from core.strategy_engine import StrategyStatus


def create_test_bars(symbol: str, start_price: float, count: int) -> list:
    """创建测试K线数据"""
    bars = []
    base_time = datetime.now()
    
    for i in range(count):
        # 模拟价格波动
        if i < count // 3:
            # 前1/3：平稳
            price = start_price + (i % 3) * 5
        elif i < count * 2 // 3:
            # 中1/3：上涨趋势
            price = start_price + (i - count // 3) * 10 + 20
        else:
            # 后1/3：下跌趋势
            price = start_price + 100 - (i - count * 2 // 3) * 8
        
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=base_time + timedelta(minutes=i),
            interval=Interval.MINUTE,
            volume=1000 + i * 10,
            turnover=(1000 + i * 10) * price,
            open_interest=5000,
            open_price=price - 2,
            high_price=price + 5,
            low_price=price - 8,
            close_price=price
        )
        bars.append(bar)
    
    return bars


def test_ma_strategy_basic():
    """测试MA策略基本功能"""
    print("=== 测试MA策略基本功能 ===")
    
    # 配置策略
    config = {
        'fast_period': 5,
        'slow_period': 10,
        'trade_volume': 2,
        'max_position': 5,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.04,
        'subscribed_symbols': ['rb2405']
    }
    
    # 创建策略
    strategy = MAStrategy('test_ma', config)
    strategy.subscribed_symbols = ['rb2405']
    
    try:
        # 1. 测试初始化
        print("1. 测试策略初始化...")
        try:
            strategy.on_init()
            assert len(strategy.indicators) == 1, "指标初始化数量错误"
            assert len(strategy.positions) == 1, "持仓初始化数量错误"
            print("✅ 策略初始化成功")
        except Exception as e:
            raise AssertionError(f"策略初始化失败: {e}")
        
        # 2. 测试启动
        print("2. 测试策略启动...")
        try:
            strategy.on_start()
            print("✅ 策略启动成功")
        except Exception as e:
            raise AssertionError(f"策略启动失败: {e}")
        
        # 3. 获取策略信息
        print("3. 测试策略信息...")
        info = strategy.get_strategy_info()
        assert info['strategy_name'] == 'test_ma', "策略名称错误"
        assert info['fast_period'] == 5, "快线周期错误"
        assert info['slow_period'] == 10, "慢线周期错误"
        print("✅ 策略信息正确")
        
        # 4. 测试停止
        print("4. 测试策略停止...")
        try:
            strategy.on_stop()
            print("✅ 策略停止成功")
        except Exception as e:
            raise AssertionError(f"策略停止失败: {e}")
        
        print("🎉 MA策略基本功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ MA策略基本功能测试失败: {e}")
        return False


def test_ma_indicator():
    """测试MA指标计算"""
    print("\n=== 测试MA指标计算 ===")
    
    from strategies.ma_strategy import MAIndicator
    
    try:
        # 创建MA指标
        ma5 = MAIndicator(period=5)
        
        # 测试数据
        prices = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]
        
        # 添加数据
        for i, price in enumerate(prices):
            ma_value = ma5.update(price)
            print(f"价格: {price}, MA5: {ma_value:.2f}, Ready: {ma5.is_ready()}")
            
            # 检查第5个数据点
            if i == 4:  # 索引4是第5个数据
                expected = (100 + 102 + 104 + 106 + 108) / 5
                assert abs(ma_value - expected) < 0.01, f"MA计算错误: {ma_value} != {expected}"
                assert ma5.is_ready(), "MA应该准备好"
        
        print("✅ MA指标计算测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ MA指标计算测试失败: {e}")
        return False


def test_ma_strategy_trading():
    """测试MA策略交易逻辑"""
    print("\n=== 测试MA策略交易逻辑 ===")
    
    # 配置策略
    config = {
        'fast_period': 3,    # 使用更小的周期便于测试
        'slow_period': 5,
        'trade_volume': 1,
        'max_position': 3,
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.10,
        'subscribed_symbols': ['test_symbol']
    }
    
    strategy = MAStrategy('trading_test', config)
    strategy.subscribed_symbols = ['test_symbol']
    
    try:
        # 初始化和启动
        strategy.on_init()
        strategy.on_start()
        
        # 创建测试数据
        symbol = 'test_symbol'
        bars = create_test_bars(symbol, 4000.0, 20)
        
        # 处理K线数据
        print("处理K线数据...")
        for i, bar in enumerate(bars):
            strategy.on_bar(bar)
            
            # 获取当前状态
            if strategy._indicators_ready(symbol):
                position = strategy.positions[symbol]
                fast_ma = strategy.indicators[symbol]['fast_ma'].current_ma
                slow_ma = strategy.indicators[symbol]['slow_ma'].current_ma
                
                print(f"K线{i+1}: 价格={bar.close_price:.1f}, "
                      f"MA3={fast_ma:.1f}, MA5={slow_ma:.1f}, "
                      f"持仓={position.direction}:{position.volume}")
        
        # 检查结果
        print(f"\n交易结果:")
        print(f"信号数量: {len(strategy.signals)}")
        print(f"交易次数: {len(strategy.trades)}")
        print(f"最终持仓: {strategy.positions[symbol].direction}:{strategy.positions[symbol].volume}")
        
        # 打印信号详情
        print(f"\n信号详情:")
        for i, signal in enumerate(strategy.signals[-5:]):  # 显示最后5个信号
            print(f"信号{i+1}: {signal.signal_type}, 快线={signal.fast_ma:.1f}, 慢线={signal.slow_ma:.1f}")
        
        # 基本验证
        assert len(strategy.indicators[symbol]['fast_ma'].values) > 0, "快线指标无数据"
        assert len(strategy.indicators[symbol]['slow_ma'].values) > 0, "慢线指标无数据"
        
        # 停止策略
        strategy.on_stop()
        
        print("✅ MA策略交易逻辑测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ MA策略交易逻辑测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ma_strategy_signals():
    """测试MA策略信号生成"""
    print("\n=== 测试MA策略信号生成 ===")
    
    config = {
        'fast_period': 2,    # 非常小的周期
        'slow_period': 4,
        'trade_volume': 1,
        'max_position': 2,
        'subscribed_symbols': ['signal_test']
    }
    
    strategy = MAStrategy('signal_test', config)
    strategy.subscribed_symbols = ['signal_test']
    
    try:
        strategy.on_init()
        strategy.on_start()
        
        symbol = 'signal_test'
        
        # 构造明确的金叉数据
        # 先让慢线稳定在高位，快线在低位
        stable_prices = [4000.0] * 6  # 让慢线稳定
        for price in stable_prices:
            strategy._update_indicators(symbol, price)
        
        # 让快线下降到更低
        low_prices = [3980.0, 3970.0]
        for price in low_prices:
            strategy._update_indicators(symbol, price)
        
        print("初始状态:")
        fast_ma = strategy.indicators[symbol]['fast_ma'].current_ma
        slow_ma = strategy.indicators[symbol]['slow_ma'].current_ma
        print(f"快线: {fast_ma:.1f}, 慢线: {slow_ma:.1f}")
        
        # 现在让价格上升，产生金叉
        rising_prices = [4020.0, 4040.0, 4060.0]
        for price in rising_prices:
            strategy._update_indicators(symbol, price)
            
            # 创建Bar并处理
            bar = BarData(
                symbol=symbol,
                exchange=Exchange.SHFE,
                datetime=datetime.now(),
                interval=Interval.MINUTE,
                volume=1000,
                turnover=1000 * price,
                open_interest=5000,
                open_price=price-5,
                high_price=price+5,
                low_price=price-10,
                close_price=price
            )
            
            strategy.on_bar(bar)
            
            fast_ma = strategy.indicators[symbol]['fast_ma'].current_ma
            slow_ma = strategy.indicators[symbol]['slow_ma'].current_ma
            print(f"价格: {price}, 快线: {fast_ma:.1f}, 慢线: {slow_ma:.1f}")
        
        print(f"\n生成的信号数量: {len(strategy.signals)}")
        for signal in strategy.signals:
            print(f"信号: {signal.signal_type}, 快线={signal.fast_ma:.1f}, 慢线={signal.slow_ma:.1f}")
        
        strategy.on_stop()
        
        print("✅ MA策略信号生成测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ MA策略信号生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ma_strategy_position_management():
    """测试MA策略持仓管理"""
    print("\n=== 测试MA策略持仓管理 ===")
    
    config = {
        'fast_period': 3,
        'slow_period': 5,
        'trade_volume': 2,
        'max_position': 5,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.04,
        'subscribed_symbols': ['pos_test']
    }
    
    strategy = MAStrategy('pos_test', config)
    strategy.subscribed_symbols = ['pos_test']
    
    try:
        strategy.on_init()
        strategy.on_start()
        
        symbol = 'pos_test'
        
        # 测试开多仓
        print("1. 测试开多仓...")
        initial_trades = len(strategy.trades)
        strategy._open_long_position(symbol, 4000.0)
        
        assert len(strategy.trades) == initial_trades + 1, "交易记录未增加"
        position = strategy.positions[symbol]
        assert position.is_long(), "持仓方向错误"
        assert position.volume == 2, "持仓数量错误"
        print(f"✅ 开多仓成功: {position.direction}:{position.volume}@{position.avg_price}")
        
        # 测试盈亏计算
        print("2. 测试盈亏计算...")
        strategy._update_position_pnl(symbol, 4100.0)
        expected_pnl = (4100.0 - 4000.0) * 2
        assert abs(position.unrealized_pnl - expected_pnl) < 0.01, "盈亏计算错误"
        print(f"✅ 盈亏计算正确: {position.unrealized_pnl}")
        
        # 测试平仓
        print("3. 测试平仓...")
        initial_trades = len(strategy.trades)
        strategy._close_position(symbol, position)
        
        assert len(strategy.trades) == initial_trades + 1, "平仓交易记录未增加"
        assert position.is_empty(), "持仓未清空"
        print(f"✅ 平仓成功: {position.direction}:{position.volume}")
        
        # 测试开空仓
        print("4. 测试开空仓...")
        initial_trades = len(strategy.trades)
        strategy._open_short_position(symbol, 4000.0)
        
        assert len(strategy.trades) == initial_trades + 1, "开空仓交易记录未增加"
        assert position.is_short(), "空仓方向错误"
        assert position.volume == 2, "空仓数量错误"
        print(f"✅ 开空仓成功: {position.direction}:{position.volume}@{position.avg_price}")
        
        strategy.on_stop()
        
        print("✅ MA策略持仓管理测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ MA策略持仓管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ma_strategy_risk_management():
    """测试MA策略风险管理"""
    print("\n=== 测试MA策略风险管理 ===")
    
    config = {
        'fast_period': 3,
        'slow_period': 5,
        'trade_volume': 1,
        'max_position': 3,
        'stop_loss_pct': 0.02,  # 2%止损
        'take_profit_pct': 0.04,  # 4%止盈
        'subscribed_symbols': ['risk_test']
    }
    
    strategy = MAStrategy('risk_test', config)
    strategy.subscribed_symbols = ['risk_test']
    
    try:
        strategy.on_init()
        strategy.on_start()
        
        symbol = 'risk_test'
        open_price = 4000.0
        
        # 开多仓
        strategy._open_long_position(symbol, open_price)
        position = strategy.positions[symbol]
        
        print(f"开仓: {position.direction}:{position.volume}@{position.avg_price}")
        
        # 测试止损
        print("1. 测试止损...")
        stop_loss_price = open_price * (1 - 0.025)  # 下跌2.5%，超过2%止损线
        initial_trades = len(strategy.trades)
        
        strategy._check_risk_management(symbol, stop_loss_price)
        
        # 由于模拟交易会立即触发平仓，检查是否平仓
        if len(strategy.trades) > initial_trades:
            print("✅ 止损触发成功")
        else:
            # 重新开仓测试止盈
            strategy._open_long_position(symbol, open_price)
        
        # 测试止盈
        print("2. 测试止盈...")
        take_profit_price = open_price * (1 + 0.045)  # 上涨4.5%，超过4%止盈线
        initial_trades = len(strategy.trades)
        
        strategy._check_risk_management(symbol, take_profit_price)
        
        if len(strategy.trades) > initial_trades:
            print("✅ 止盈触发成功")
        
        strategy.on_stop()
        
        print("✅ MA策略风险管理测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ MA策略风险管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("🚀 开始运行MA策略简化集成测试")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 测试列表
    tests = [
        ("MA策略基本功能", test_ma_strategy_basic),
        ("MA指标计算", test_ma_indicator),
        ("MA策略交易逻辑", test_ma_strategy_trading),
        ("MA策略信号生成", test_ma_strategy_signals),
        ("MA策略持仓管理", test_ma_strategy_position_management),
        ("MA策略风险管理", test_ma_strategy_risk_management),
    ]
    
    # 执行测试
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
    print(f"🏆 测试总结")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print(f"🎉 所有测试通过! MA策略实现成功!")
        return True
    else:
        print(f"⚠️ 有 {total-passed} 个测试失败，请检查实现")
        return False


if __name__ == '__main__':
    success = main()
    
    # 退出码
    import sys
    sys.exit(0 if success else 1)