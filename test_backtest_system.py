#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest System Test Suite - 回测系统测试套件

测试Milestone 2.5回测系统的完整功能
- BacktestEngine核心功能
- 历史数据管理
- 多策略组合回测
- 性能分析和指标计算
- 结果导出和可视化
"""

import sys
import os
import tempfile
import shutil
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.backtest_engine import (
    BacktestEngine, BacktestConfig, HistoricalDataManager,
    MarketData, Trade, PositionInfo, PerformanceMetrics,
    BacktestState, run_portfolio_backtest
)
from core.strategy_portfolio_config import (
    PortfolioConfig, StrategyConfig, StrategyAllocation, ConfigManager
)
from core.multi_strategy_manager import StrategyAllocationMethod


def test_historical_data_manager():
    """测试历史数据管理器"""
    print("\n=== 测试历史数据管理器 ===")
    
    try:
        # 创建临时数据目录
        temp_dir = tempfile.mkdtemp()
        data_manager = HistoricalDataManager(data_dir=temp_dir)
        
        # 测试数据加载 (模拟数据)
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        symbols = ['rb2405', 'i2405', 'j2405']
        frequencies = ['1m', '5m', '1h', '1d']
        
        for symbol in symbols:
            for frequency in frequencies:
                data = data_manager.load_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency
                )
                
                assert len(data) > 0, f"数据为空: {symbol} {frequency}"
                assert 'open' in data.columns, "缺少open列"
                assert 'high' in data.columns, "缺少high列"
                assert 'low' in data.columns, "缺少low列"
                assert 'close' in data.columns, "缺少close列"
                assert 'volume' in data.columns, "缺少volume列"
                
                # 验证OHLC逻辑
                assert (data['high'] >= data['low']).all(), f"High < Low: {symbol} {frequency}"
                assert (data['high'] >= data['open']).all(), f"High < Open: {symbol} {frequency}"
                assert (data['high'] >= data['close']).all(), f"High < Close: {symbol} {frequency}"
                assert (data['low'] <= data['open']).all(), f"Low > Open: {symbol} {frequency}"
                assert (data['low'] <= data['close']).all(), f"Low > Close: {symbol} {frequency}"
                
                print(f"✅ {symbol} {frequency}: {len(data)} 条数据加载成功")
        
        # 测试数据缓存
        cached_data1 = data_manager.load_data('rb2405', start_date, end_date, '1h')
        cached_data2 = data_manager.load_data('rb2405', start_date, end_date, '1h')
        
        assert cached_data1 is cached_data2, "数据缓存机制失效"
        print("✅ 数据缓存机制验证成功")
        
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"❌ 历史数据管理器测试失败: {e}")
        return False


def test_backtest_config():
    """测试回测配置"""
    print("\n=== 测试回测配置 ===")
    
    try:
        # 基础配置
        config = BacktestConfig(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31),
            initial_capital=1000000.0,
            symbols=['rb2405', 'i2405'],
            data_frequency='1h',
            commission_rate=0.0002,
            slippage_rate=0.0001
        )
        
        assert config.initial_capital == 1000000.0
        assert len(config.symbols) == 2
        assert config.commission_rate == 0.0002
        assert config.data_frequency == '1h'
        print("✅ 基础配置创建成功")
        
        # 验证日期逻辑
        assert config.start_date < config.end_date, "开始日期必须早于结束日期"
        
        # 验证参数范围
        assert 0 <= config.commission_rate <= 0.01, "手续费率超出合理范围"
        assert 0 <= config.slippage_rate <= 0.01, "滑点率超出合理范围"
        assert config.initial_capital > 0, "初始资金必须为正数"
        
        print("✅ 配置参数验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 回测配置测试失败: {e}")
        return False


def test_market_data_structures():
    """测试市场数据结构"""
    print("\n=== 测试市场数据结构 ===")
    
    try:
        # 测试MarketData
        timestamp = datetime(2024, 1, 1, 9, 30)
        market_data = MarketData(
            symbol='rb2405',
            timestamp=timestamp,
            open=3500.0,
            high=3520.0,
            low=3490.0,
            close=3510.0,
            volume=1000,
            turnover=3505000.0
        )
        
        assert market_data.symbol == 'rb2405'
        assert market_data.timestamp == timestamp
        assert market_data.high >= market_data.low
        assert market_data.high >= market_data.open
        assert market_data.high >= market_data.close
        assert market_data.low <= market_data.open
        assert market_data.low <= market_data.close
        
        # 测试转换为字典
        data_dict = market_data.to_dict()
        assert isinstance(data_dict, dict)
        assert data_dict['symbol'] == 'rb2405'
        assert data_dict['close'] == 3510.0
        
        print("✅ MarketData结构验证成功")
        
        # 测试Trade
        trade = Trade(
            trade_id='test_001',
            strategy_name='ma_strategy',
            symbol='rb2405',
            direction='long',
            open_time=timestamp,
            open_price=3500.0,
            quantity=10
        )
        
        assert not trade.is_closed
        assert trade.pnl is None
        
        # 测试平仓
        close_time = timestamp + timedelta(hours=1)
        trade.close_trade(close_time, 3550.0, commission=7.0)
        
        assert trade.is_closed
        assert trade.close_time == close_time
        assert trade.close_price == 3550.0
        assert trade.pnl > 0  # 盈利交易
        
        print("✅ Trade结构验证成功")
        
        # 测试PositionInfo
        position = PositionInfo(
            symbol='rb2405',
            strategy_name='ma_strategy',
            direction='long',
            quantity=10,
            avg_price=3500.0
        )
        
        # 更新市值
        position.update_market_value(3550.0)
        assert position.market_value > 0
        assert position.unrealized_pnl > 0
        
        print("✅ PositionInfo结构验证成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 市场数据结构测试失败: {e}")
        return False


def test_backtest_engine_basic():
    """测试回测引擎基础功能"""
    print("\n=== 测试回测引擎基础功能 ===")
    
    try:
        # 创建回测配置
        config = BacktestConfig(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),  # 短期测试
            initial_capital=1000000.0,
            symbols=['rb2405'],
            data_frequency='1h',
            commission_rate=0.0002
        )
        
        # 创建回测引擎
        engine = BacktestEngine(config)
        
        assert engine.state == BacktestState.IDLE
        assert engine.config.initial_capital == 1000000.0
        assert len(engine.config.symbols) == 1
        
        print("✅ 回测引擎初始化成功")
        
        # 测试数据管理器
        assert engine.data_manager is not None
        
        # 加载测试数据
        data = engine.data_manager.load_data(
            symbol='rb2405',
            start_date=config.start_date,
            end_date=config.end_date,
            frequency=config.data_frequency
        )
        
        assert len(data) > 0, "测试数据为空"
        print(f"✅ 测试数据加载成功: {len(data)} 条记录")
        
        # 验证数据完整性
        assert 'open' in data.columns
        assert 'high' in data.columns
        assert 'low' in data.columns
        assert 'close' in data.columns
        assert 'volume' in data.columns
        
        # 验证价格逻辑
        assert (data['high'] >= data['low']).all()
        assert (data['high'] >= data['open']).all()
        assert (data['high'] >= data['close']).all()
        
        print("✅ 数据完整性验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 回测引擎基础功能测试失败: {e}")
        return False


def test_portfolio_backtest_integration():
    """测试投资组合回测集成功能"""
    print("\n=== 测试投资组合回测集成功能 ===")
    
    try:
        # 创建投资组合配置
        portfolio_config = PortfolioConfig(
            portfolio_name="test_portfolio",
            total_capital=1000000.0,
            allocation_method="equal"
        )
        
        # 添加策略配置
        strategies = [
            StrategyConfig(
                strategy_name="ma_fast",
                strategy_class="MAStrategy",
                strategy_module="strategies.ma_strategy",
                parameters={"fast_period": 5, "slow_period": 20}
            ),
            StrategyConfig(
                strategy_name="ma_slow",
                strategy_class="MAStrategy", 
                strategy_module="strategies.ma_strategy",
                parameters={"fast_period": 10, "slow_period": 50}
            )
        ]
        
        portfolio_config.strategies = strategies
        
        # 添加分配配置
        allocations = [
            StrategyAllocation(
                strategy_name="ma_fast",
                allocation_amount=600000.0,
                allocation_ratio=0.6,
                max_position_ratio=0.8,
                risk_budget=0.02
            ),
            StrategyAllocation(
                strategy_name="ma_slow",
                allocation_amount=400000.0,
                allocation_ratio=0.4,
                max_position_ratio=0.8,
                risk_budget=0.015
            )
        ]
        
        portfolio_config.strategy_allocations = allocations
        
        print("✅ 投资组合配置创建成功")
        
        # 创建回测配置
        backtest_config = BacktestConfig(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 15),  # 短期测试
            initial_capital=1000000.0,
            symbols=['rb2405', 'i2405'],
            data_frequency='1h',
            commission_rate=0.0002
        )
        
        print("✅ 回测配置创建成功")
        
        # 创建回测引擎
        engine = BacktestEngine(backtest_config)
        
        # 初始化投资组合
        init_success = engine.initialize_portfolio(portfolio_config)
        assert init_success, "投资组合初始化失败"
        
        assert engine.portfolio_manager is not None
        print("✅ 投资组合初始化成功")
        
        # 运行回测 (简化版本，不包括完整的策略逻辑)
        backtest_success = engine.run_backtest()
        assert backtest_success, "回测运行失败"
        
        assert engine.state == BacktestState.COMPLETED
        print("✅ 回测运行成功")
        
        # 验证回测结果
        results = engine.get_backtest_results()
        
        assert 'config' in results
        assert 'portfolio_values' in results
        assert 'trades' in results
        assert 'positions' in results
        assert 'performance_metrics' in results
        
        # 验证投资组合价值记录
        portfolio_values = results['portfolio_values']
        assert len(portfolio_values) > 0
        
        # 验证初始价值
        initial_value = portfolio_values[0]['value']
        assert initial_value == backtest_config.initial_capital
        
        print("✅ 回测结果验证成功")
        
        # 验证性能指标
        metrics = results['performance_metrics']
        assert 'total_return' in metrics
        assert 'annual_return' in metrics
        assert 'volatility' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        
        print("✅ 性能指标计算成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 投资组合回测集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance_metrics_calculation():
    """测试性能指标计算"""
    print("\n=== 测试性能指标计算 ===")
    
    try:
        # 创建模拟的投资组合价值序列
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        
        # 模拟价值变化 (包含上涨、下跌、震荡)
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, len(dates))  # 日均0.1%收益，2%波动
        
        initial_value = 1000000.0
        values = [initial_value]
        
        for r in returns[1:]:
            new_value = values[-1] * (1 + r)
            values.append(new_value)
        
        # 创建回测引擎进行性能分析
        config = BacktestConfig(
            start_date=dates[0].to_pydatetime(),
            end_date=dates[-1].to_pydatetime(),
            initial_capital=initial_value,
            symbols=['rb2405']
        )
        
        engine = BacktestEngine(config)
        
        # 手动设置投资组合价值
        engine.portfolio_values = [(date.to_pydatetime(), value) for date, value in zip(dates, values)]
        
        # 计算性能指标
        engine._calculate_performance_metrics()
        
        metrics = engine.performance_metrics
        assert metrics is not None
        
        # 验证基本指标
        assert isinstance(metrics.total_return, float)
        assert isinstance(metrics.annual_return, float)
        assert isinstance(metrics.volatility, float)
        assert isinstance(metrics.sharpe_ratio, float)
        assert isinstance(metrics.max_drawdown, float)
        
        # 验证指标合理性
        assert -1 <= metrics.total_return <= 10  # 合理的收益率范围
        assert 0 <= metrics.max_drawdown <= 1   # 回撤在0-100%之间
        assert metrics.volatility >= 0          # 波动率非负
        
        print(f"✅ 总收益率: {metrics.total_return:.2%}")
        print(f"✅ 年化收益率: {metrics.annual_return:.2%}")
        print(f"✅ 波动率: {metrics.volatility:.2%}")
        print(f"✅ 夏普比率: {metrics.sharpe_ratio:.3f}")
        print(f"✅ 最大回撤: {metrics.max_drawdown:.2%}")
        
        # 测试指标转换为字典
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert len(metrics_dict) > 10  # 应该有多个指标
        
        print("✅ 性能指标计算验证成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能指标计算测试失败: {e}")
        return False


def test_backtest_results_export():
    """测试回测结果导出"""
    print("\n=== 测试回测结果导出 ===")
    
    try:
        # 创建简单的回测配置
        config = BacktestConfig(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 5),
            initial_capital=1000000.0,
            symbols=['rb2405'],
            data_frequency='1h'
        )
        
        # 创建回测引擎
        engine = BacktestEngine(config)
        
        # 添加模拟数据
        test_time = datetime(2024, 1, 1, 10, 0)
        engine.portfolio_values = [
            (test_time, 1000000.0),
            (test_time + timedelta(hours=1), 1001000.0),
            (test_time + timedelta(hours=2), 999000.0)
        ]
        
        # 添加模拟交易
        trade = Trade(
            trade_id='test_001',
            strategy_name='test_strategy',
            symbol='rb2405',
            direction='long',
            open_time=test_time,
            open_price=3500.0,
            quantity=10
        )
        trade.close_trade(test_time + timedelta(hours=1), 3520.0, 7.0)
        engine.trades.append(trade)
        
        # 添加模拟持仓
        position = PositionInfo(
            symbol='rb2405',
            strategy_name='test_strategy',
            direction='long',
            quantity=5,
            avg_price=3510.0
        )
        position.update_market_value(3520.0)
        engine.positions['rb2405_long'] = position
        
        # 模拟性能指标
        engine.performance_metrics = PerformanceMetrics(
            total_return=0.001,
            annual_return=0.10,
            volatility=0.15,
            sharpe_ratio=0.67,
            max_drawdown=0.02,
            win_rate=0.6,
            total_trades=10
        )
        
        engine.state = BacktestState.COMPLETED
        
        # 获取回测结果
        results = engine.get_backtest_results()
        
        assert 'config' in results
        assert 'portfolio_values' in results
        assert 'trades' in results
        assert 'positions' in results  
        assert 'performance_metrics' in results
        assert 'state' in results
        
        # 验证配置信息
        config_info = results['config']
        assert config_info['initial_capital'] == 1000000.0
        assert config_info['symbols'] == ['rb2405']
        
        # 验证投资组合价值
        portfolio_values = results['portfolio_values']
        assert len(portfolio_values) == 3
        assert portfolio_values[0]['value'] == 1000000.0
        
        # 验证交易记录
        trades = results['trades']
        assert len(trades) == 1
        trade_data = trades[0]
        assert trade_data['symbol'] == 'rb2405'
        assert trade_data['direction'] == 'long'
        assert trade_data['pnl'] is not None
        
        # 验证持仓信息
        positions = results['positions']
        assert len(positions) == 1
        position_data = positions[0]
        assert position_data['symbol'] == 'rb2405'
        assert position_data['quantity'] == 5
        
        # 验证性能指标
        metrics = results['performance_metrics']
        assert metrics['total_return'] == 0.001
        assert metrics['annual_return'] == 0.10
        assert metrics['sharpe_ratio'] == 0.67
        
        print("✅ 回测结果数据结构验证成功")
        
        # 测试保存到文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.close()
        
        try:
            engine.save_results(temp_file.name)
            
            # 验证文件存在
            assert os.path.exists(temp_file.name)
            
            # 验证文件内容
            import json
            with open(temp_file.name, 'r', encoding='utf-8') as f:
                loaded_results = json.load(f)
            
            assert loaded_results['config']['initial_capital'] == 1000000.0
            assert len(loaded_results['portfolio_values']) == 3
            assert len(loaded_results['trades']) == 1
            
            print("✅ 回测结果文件导出验证成功")
            
        finally:
            os.unlink(temp_file.name)
        
        return True
        
    except Exception as e:
        print(f"❌ 回测结果导出测试失败: {e}")
        return False


def test_run_portfolio_backtest_convenience():
    """测试便捷函数run_portfolio_backtest"""
    print("\n=== 测试便捷函数run_portfolio_backtest ===")
    
    try:
        # 创建投资组合配置
        portfolio_config = PortfolioConfig(
            portfolio_name="convenience_test",
            total_capital=500000.0,
            allocation_method="equal"
        )
        
        # 添加策略
        strategy = StrategyConfig(
            strategy_name="test_ma",
            strategy_class="MAStrategy",
            strategy_module="strategies.ma_strategy",
            parameters={"fast_period": 5, "slow_period": 20}
        )
        portfolio_config.strategies = [strategy]
        
        # 添加分配
        allocation = StrategyAllocation(
            strategy_name="test_ma",
            allocation_amount=500000.0,
            allocation_ratio=1.0,
            max_position_ratio=0.8,
            risk_budget=0.02
        )
        portfolio_config.strategy_allocations = [allocation]
        
        # 创建回测配置
        backtest_config = BacktestConfig(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 3),  # 超短期测试
            initial_capital=500000.0,
            symbols=['rb2405'],
            data_frequency='1h'
        )
        
        # 运行回测
        results = run_portfolio_backtest(portfolio_config, backtest_config)
        
        assert isinstance(results, dict)
        assert 'config' in results
        assert 'portfolio_values' in results
        assert 'performance_metrics' in results
        assert results['state'] == 'completed'
        
        print("✅ 便捷函数运行成功")
        
        # 验证初始资金一致性
        assert results['config']['initial_capital'] == 500000.0
        
        # 验证有投资组合价值记录
        portfolio_values = results['portfolio_values']
        assert len(portfolio_values) > 0
        assert portfolio_values[0]['value'] == 500000.0
        
        print("✅ 便捷函数结果验证成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 便捷函数测试失败: {e}")
        return False


def main():
    """运行所有回测系统测试"""
    print("🚀 开始运行回测系统完整测试套件")
    print("=" * 60)
    
    tests = [
        ("历史数据管理器", test_historical_data_manager),
        ("回测配置", test_backtest_config),
        ("市场数据结构", test_market_data_structures),
        ("回测引擎基础功能", test_backtest_engine_basic),
        ("投资组合回测集成", test_portfolio_backtest_integration),
        ("性能指标计算", test_performance_metrics_calculation),
        ("回测结果导出", test_backtest_results_export),
        ("便捷函数", test_run_portfolio_backtest_convenience)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        try:
            if test_func():
                passed_tests += 1
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
        print("="*60)
    
    # 测试总结
    print(f"\n🏆 回测系统测试总结")
    print(f"通过: {passed_tests}/{total_tests}")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 所有回测系统测试通过! Milestone 2.5核心功能验证成功!")
        return True
    else:
        print(f"⚠️  有 {total_tests - passed_tests} 个测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)