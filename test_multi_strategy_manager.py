#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi Strategy Manager Test

多策略管理系统的集成测试
- 测试多策略加载和管理
- 验证资金分配机制
- 测试风险控制功能  
- 验证绩效监控系统
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import time
import threading

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.multi_strategy_manager import (
    MultiStrategyManager, StrategyAllocation, StrategyGroup, 
    RiskLimit, StrategyAllocationMethod, RiskControlLevel
)
from core.strategy_portfolio import PortfolioConfigManager, PortfolioConfig
from strategies.ma_strategy import MAStrategy
from core.trading_engine import TradingEngine
from core.market_data_manager import MarketDataManager
from core.data_types import BarData, Exchange, Interval


def create_mock_engines():
    """创建模拟的交易和数据引擎"""
    # 创建模拟的连接管理器
    class MockConnectionManager:
        def __init__(self):
            self.simulation_mode = True
    
    # 创建模拟的TradingEngine
    trading_engine = TradingEngine({})
    
    # 创建模拟的MarketDataManager  
    market_data_manager = MarketDataManager(MockConnectionManager())
    
    return trading_engine, market_data_manager


def test_multi_strategy_manager_basic():
    """测试多策略管理器基本功能"""
    print("=== 测试多策略管理器基本功能 ===")
    
    try:
        # 创建模拟引擎
        trading_engine, market_data_manager = create_mock_engines()
        
        # 创建多策略管理器
        config = {
            'total_capital': 1000000.0,
            'allocation_method': 'equal'
        }
        
        manager = MultiStrategyManager(
            trading_engine=trading_engine,
            market_data_manager=market_data_manager,
            config=config
        )
        
        # 测试添加策略
        strategy1_config = {
            'fast_period': 5,
            'slow_period': 20,
            'trade_volume': 1,
            'subscribed_symbols': ['rb2405']
        }
        
        strategy2_config = {
            'fast_period': 10,
            'slow_period': 30,
            'trade_volume': 1,
            'subscribed_symbols': ['i2405']
        }
        
        # 添加第一个策略
        result1 = manager.add_strategy(
            strategy_name='ma_strategy_1',
            strategy_class=MAStrategy,
            strategy_config=strategy1_config,
            allocation_config={
                'ratio': 0.6,
                'max_position_ratio': 0.8,
                'risk_budget': 0.02
            }
        )
        
        # 添加第二个策略
        result2 = manager.add_strategy(
            strategy_name='ma_strategy_2',
            strategy_class=MAStrategy,
            strategy_config=strategy2_config,
            allocation_config={
                'ratio': 0.4,
                'max_position_ratio': 0.8,
                'risk_budget': 0.03
            }
        )
        
        assert result1, "添加策略1失败"
        assert result2, "添加策略2失败"
        
        # 测试资金分配
        allocation_result = manager.allocate_capital()
        assert allocation_result, "资金分配失败"
        
        # 检查分配结果
        portfolio_status = manager.get_portfolio_status()
        print(f"组合状态: {portfolio_status}")
        
        assert portfolio_status['total_capital'] == 1000000.0, "总资本不正确"
        assert portfolio_status['strategy_count'] == 2, "策略数量不正确"
        
        # 测试策略汇总
        strategy_summary = manager.get_strategy_summary()
        print(f"策略汇总: {strategy_summary}")
        
        assert 'ma_strategy_1' in strategy_summary, "策略1不在汇总中"
        assert 'ma_strategy_2' in strategy_summary, "策略2不在汇总中"
        
        # 清理
        manager.cleanup()
        
        print("✅ 多策略管理器基本功能测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 多策略管理器基本功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_capital_allocation_methods():
    """测试不同的资金分配方法"""
    print("\n=== 测试资金分配方法 ===")
    
    try:
        # 创建模拟引擎
        trading_engine, market_data_manager = create_mock_engines()
        
        # 测试等额分配
        config_equal = {
            'total_capital': 1000000.0,
            'allocation_method': 'equal'
        }
        
        manager = MultiStrategyManager(
            trading_engine=trading_engine,
            market_data_manager=market_data_manager,
            config=config_equal
        )
        
        # 添加策略
        for i in range(3):
            strategy_config = {
                'fast_period': 5 + i,
                'slow_period': 20 + i * 5,
                'trade_volume': 1,
                'subscribed_symbols': [f'test_{i}']
            }
            
            manager.add_strategy(
                strategy_name=f'strategy_{i}',
                strategy_class=MAStrategy,
                strategy_config=strategy_config
            )
        
        # 测试等额分配
        manager.allocate_capital()
        
        # 检查分配结果
        expected_amount = 1000000.0 / 3
        for strategy_name, allocation in manager.strategy_allocations.items():
            assert abs(allocation.allocation_amount - expected_amount) < 0.01, \
                f"等额分配不正确: {allocation.allocation_amount} != {expected_amount}"
        
        print("✅ 等额分配测试通过")
        
        # 测试权重分配
        manager.allocation_method = StrategyAllocationMethod.WEIGHTED
        
        # 设置权重
        weights = [0.5, 0.3, 0.2]
        for i, (strategy_name, allocation) in enumerate(manager.strategy_allocations.items()):
            allocation.allocation_ratio = weights[i]
        
        manager.allocate_capital()
        
        # 检查权重分配结果
        for i, (strategy_name, allocation) in enumerate(manager.strategy_allocations.items()):
            expected_amount = 1000000.0 * weights[i]
            assert abs(allocation.allocation_amount - expected_amount) < 0.01, \
                f"权重分配不正确: {allocation.allocation_amount} != {expected_amount}"
        
        print("✅ 权重分配测试通过")
        
        manager.cleanup()
        
        print("✅ 资金分配方法测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 资金分配方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_groups():
    """测试策略组功能"""
    print("\n=== 测试策略组功能 ===")
    
    try:
        # 创建模拟引擎
        trading_engine, market_data_manager = create_mock_engines()
        
        config = {
            'total_capital': 1000000.0,
            'allocation_method': 'equal'
        }
        
        manager = MultiStrategyManager(
            trading_engine=trading_engine,
            market_data_manager=market_data_manager,
            config=config
        )
        
        # 添加策略
        strategies = ['ma_short', 'ma_medium', 'ma_long']
        for strategy_name in strategies:
            strategy_config = {
                'fast_period': 5,
                'slow_period': 20,
                'trade_volume': 1,
                'subscribed_symbols': ['rb2405']
            }
            
            manager.add_strategy(
                strategy_name=strategy_name,
                strategy_class=MAStrategy,
                strategy_config=strategy_config
            )
        
        # 创建策略组
        group_config = {
            'group_name': 'ma_group',
            'strategies': strategies,
            'max_correlation': 0.7,
            'max_group_risk': 0.3,
            'rebalance_frequency': 'daily'
        }
        
        result = manager.create_strategy_group(group_config)
        assert result, "创建策略组失败"
        
        # 检查策略组
        assert 'ma_group' in manager.strategy_groups, "策略组未创建"
        
        group = manager.strategy_groups['ma_group']
        assert group.group_name == 'ma_group', "策略组名称不正确"
        assert len(group.strategies) == 3, "策略组包含的策略数量不正确"
        assert group.max_correlation == 0.7, "最大相关性设置不正确"
        
        # 测试添加不存在的策略到组
        invalid_group_config = {
            'group_name': 'invalid_group',
            'strategies': ['non_existent_strategy'],
        }
        
        result = manager.create_strategy_group(invalid_group_config)
        assert not result, "应该拒绝包含不存在策略的组"
        
        manager.cleanup()
        
        print("✅ 策略组功能测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 策略组功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_portfolio_config_manager():
    """测试组合配置管理器"""
    print("\n=== 测试组合配置管理器 ===")
    
    try:
        # 创建配置管理器
        config_manager = PortfolioConfigManager("test_configs")
        
        # 创建测试配置
        test_config = PortfolioConfig(
            name="测试组合",
            description="用于测试的组合配置",
            total_capital=500000.0,
            allocation_method="equal",
            rebalance_frequency="daily",
            risk_tolerance=0.02,
            strategies=[
                {
                    "name": "test_ma_strategy",
                    "class": "MAStrategy",
                    "config": {
                        "fast_period": 5,
                        "slow_period": 20,
                        "trade_volume": 1,
                        "subscribed_symbols": ["test_symbol"]
                    },
                    "allocation": {
                        "ratio": 1.0,
                        "max_position_ratio": 0.8,
                        "risk_budget": 0.02
                    }
                }
            ]
        )
        
        # 测试保存配置
        save_result = config_manager.save_config(test_config, "test_config.json")
        assert save_result, "保存配置失败"
        
        # 测试加载配置
        loaded_config = config_manager.load_config("test_config.json")
        assert loaded_config is not None, "加载配置失败"
        assert loaded_config.name == "测试组合", "配置名称不匹配"
        assert loaded_config.total_capital == 500000.0, "总资本不匹配"
        
        # 测试配置验证
        valid = config_manager.validate_config(loaded_config)
        assert valid, "配置验证失败"
        
        # 测试无效配置
        invalid_config = PortfolioConfig(
            name="",  # 空名称
            description="无效配置",
            total_capital=0.0,  # 无效资本
            allocation_method="invalid_method",  # 无效方法
            rebalance_frequency="daily",
            risk_tolerance=0.02,
            strategies=[]  # 空策略列表
        )
        
        invalid = not config_manager.validate_config(invalid_config)
        assert invalid, "应该拒绝无效配置"
        
        # 测试列出配置
        configs = config_manager.list_configs()
        assert "test_config.json" in configs, "配置文件未列出"
        
        # 测试删除配置
        delete_result = config_manager.delete_config("test_config.json")
        assert delete_result, "删除配置失败"
        
        print("✅ 组合配置管理器测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 组合配置管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_lifecycle():
    """测试策略生命周期管理"""
    print("\n=== 测试策略生命周期管理 ===")
    
    try:
        # 创建模拟引擎
        trading_engine, market_data_manager = create_mock_engines()
        
        config = {
            'total_capital': 500000.0,
            'allocation_method': 'equal'
        }
        
        manager = MultiStrategyManager(
            trading_engine=trading_engine,
            market_data_manager=market_data_manager,
            config=config
        )
        
        # 添加策略
        strategy_config = {
            'fast_period': 5,
            'slow_period': 20,
            'trade_volume': 1,
            'subscribed_symbols': ['rb2405']
        }
        
        manager.add_strategy(
            strategy_name='lifecycle_test_strategy',
            strategy_class=MAStrategy,
            strategy_config=strategy_config,
            allocation_config={
                'ratio': 1.0,
                'max_position_ratio': 0.8,
                'risk_budget': 0.02
            }
        )
        
        # 测试单个策略启动
        start_result = manager.start_strategy('lifecycle_test_strategy')
        assert start_result, "单个策略启动失败"
        
        # 检查策略状态
        status = manager.strategy_statuses.get('lifecycle_test_strategy')
        assert status is not None, "策略状态未创建"
        
        # 测试单个策略停止
        stop_result = manager.stop_strategy('lifecycle_test_strategy')
        assert stop_result, "单个策略停止失败"
        
        # 测试移除策略
        remove_result = manager.remove_strategy('lifecycle_test_strategy')
        assert remove_result, "移除策略失败"
        
        # 验证策略已移除
        assert 'lifecycle_test_strategy' not in manager.strategy_engines, "策略未完全移除"
        
        manager.cleanup()
        
        print("✅ 策略生命周期管理测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 策略生命周期管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_monitoring_system():
    """测试监控系统"""
    print("\n=== 测试监控系统 ===")
    
    try:
        # 创建模拟引擎
        trading_engine, market_data_manager = create_mock_engines()
        
        config = {
            'total_capital': 1000000.0,
            'allocation_method': 'equal'
        }
        
        manager = MultiStrategyManager(
            trading_engine=trading_engine,
            market_data_manager=market_data_manager,
            config=config
        )
        
        # 添加策略
        strategy_config = {
            'fast_period': 5,
            'slow_period': 20,
            'trade_volume': 1,
            'subscribed_symbols': ['rb2405']
        }
        
        manager.add_strategy(
            strategy_name='monitor_test_strategy',
            strategy_class=MAStrategy,
            strategy_config=strategy_config,
            allocation_config={
                'ratio': 1.0,
                'max_position_ratio': 0.8,
                'risk_budget': 0.02
            }
        )
        
        # 启动策略
        manager.start_strategy('monitor_test_strategy')
        
        # 启动监控系统
        manager.running = True
        monitor_thread = threading.Thread(
            target=manager._monitoring_loop,
            daemon=True
        )
        monitor_thread.start()
        
        # 让监控运行一小段时间
        time.sleep(2.0)
        
        # 停止监控
        manager.running = False
        monitor_thread.join(timeout=3.0)
        
        # 测试状态更新
        manager._update_strategy_statuses()
        
        # 测试绩效更新
        manager._update_performance_metrics()
        
        # 检查绩效指标
        metrics = manager.performance_metrics.get('monitor_test_strategy')
        assert metrics is not None, "绩效指标未创建"
        assert metrics.last_update is not None, "绩效指标未更新"
        
        # 测试报告导出
        report_path = "test_performance_report.json"
        export_result = manager.export_performance_report(report_path)
        assert export_result, "绩效报告导出失败"
        
        # 验证报告文件存在
        import os
        assert os.path.exists(report_path), "报告文件不存在"
        
        # 清理
        os.remove(report_path)
        manager.cleanup()
        
        print("✅ 监控系统测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 监控系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_comprehensive_integration():
    """综合集成测试"""
    print("\n=== 综合集成测试 ===")
    
    try:
        # 创建配置管理器
        config_manager = PortfolioConfigManager("integration_test_configs")
        
        # 创建示例配置
        config_manager.create_sample_configs()
        
        # 加载配置
        portfolio_config = config_manager.load_config("simple_balanced.json")
        assert portfolio_config is not None, "加载组合配置失败"
        
        # 创建多策略管理器
        manager_config = {
            'total_capital': portfolio_config.total_capital,
            'allocation_method': portfolio_config.allocation_method
        }
        
        # 创建模拟引擎
        trading_engine, market_data_manager = create_mock_engines()
        
        manager = MultiStrategyManager(
            trading_engine=trading_engine,
            market_data_manager=market_data_manager,
            config=manager_config
        )
        
        # 根据配置添加策略
        for strategy_config in portfolio_config.strategies:
            allocation_config = strategy_config.get('allocation', {})
            
            manager.add_strategy(
                strategy_name=strategy_config['name'],
                strategy_class=MAStrategy,  # 简化测试，都使用MA策略
                strategy_config=strategy_config['config'],
                allocation_config=allocation_config
            )
        
        # 创建策略组
        if portfolio_config.groups:
            for group_config in portfolio_config.groups:
                manager.create_strategy_group(group_config)
        
        # 启动所有策略
        start_result = manager.start_all_strategies()
        assert start_result, "启动所有策略失败"
        
        # 运行一段时间
        time.sleep(1.0)
        
        # 获取组合状态
        portfolio_status = manager.get_portfolio_status()
        print(f"组合运行状态: {portfolio_status}")
        
        # 获取策略汇总
        strategy_summary = manager.get_strategy_summary()
        print(f"策略汇总: {strategy_summary}")
        
        # 测试组合再平衡
        rebalance_result = manager.rebalance_portfolio()
        assert rebalance_result, "组合再平衡失败"
        
        # 停止所有策略
        stop_result = manager.stop_all_strategies()
        assert stop_result, "停止所有策略失败"
        
        # 清理
        manager.cleanup()
        
        # 清理测试配置文件
        import shutil
        shutil.rmtree("integration_test_configs", ignore_errors=True)
        
        print("✅ 综合集成测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 综合集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("🚀 开始运行多策略管理系统测试")
    
    # 配置日志
    logging.basicConfig(
        level=logging.WARNING,  # 降低日志级别减少输出
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    tests = [
        ("多策略管理器基本功能", test_multi_strategy_manager_basic),
        ("资金分配方法", test_capital_allocation_methods),
        ("策略组功能", test_strategy_groups),
        ("组合配置管理器", test_portfolio_config_manager),
        ("策略生命周期管理", test_strategy_lifecycle),
        ("监控系统", test_monitoring_system),
        ("综合集成测试", test_comprehensive_integration),
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
    print(f"🏆 多策略管理系统测试总结")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print(f"🎉 所有测试通过! Milestone 2.4 多策略管理系统实现成功!")
        return True
    else:
        print(f"⚠️ 有 {total-passed} 个测试失败")
        return False


if __name__ == '__main__':
    success = main()
    
    import sys
    sys.exit(0 if success else 1)