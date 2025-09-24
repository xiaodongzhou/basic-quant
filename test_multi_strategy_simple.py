#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi Strategy System Simple Test

多策略系统的简化集成测试
- 测试多策略管理器基本功能
- 测试策略组合配置系统
- 验证资金分配和风险控制
- 测试策略组合部署
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import tempfile
import shutil

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.multi_strategy_manager import (
    MultiStrategyManager, StrategyAllocationMethod, 
    RiskControlLevel, RiskLimit
)
from core.strategy_portfolio_config import (
    ConfigManager, PortfolioDeployment, 
    PortfolioConfig, StrategyConfig
)
from core.trading_engine import TradingEngine
from core.market_data_manager import MarketDataManager
from strategies.ma_strategy import MAStrategy


def create_mock_engines():
    """创建模拟的交易引擎和市场数据管理器"""
    # 简化的模拟实现
    
    class MockTradingEngine:
        def __init__(self):
            self.orders = {}
            self.trades = {}
            self.positions = {}
            self.trade_callbacks = {}
            self.order_callbacks = {}
        
        def register_trade_callback(self, callback):
            """注册成交回调"""
            pass
        
        def register_order_callback(self, callback):
            """注册订单回调"""
            pass
        
        def send_order(self, order_request):
            """发送订单"""
            pass
    
    class MockMarketDataManager:
        def __init__(self):
            self.subscriptions = {}
            self.market_data = {}
            self.tick_callbacks = {}
            self.bar_callbacks = {}
        
        def register_tick_callback(self, callback):
            """注册tick回调"""
            pass
        
        def register_bar_callback(self, callback):
            """注册bar回调"""
            pass
        
        def subscribe_market_data(self, symbol, exchange=None):
            """订阅市场数据"""
            pass
    
    return MockTradingEngine(), MockMarketDataManager()


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
        
        print("✅ 多策略管理器创建成功")
        
        # 测试添加策略
        strategy_config = {
            'fast_period': 5,
            'slow_period': 20,
            'trade_volume': 1,
            'subscribed_symbols': ['rb2405']
        }
        
        success = manager.add_strategy(
            strategy_name='test_ma_strategy',
            strategy_class=MAStrategy,
            strategy_config=strategy_config,
            allocation_config={
                'amount': 500000.0,
                'ratio': 0.5,
                'max_position_ratio': 0.8,
                'risk_budget': 0.02
            }
        )
        
        assert success, "添加策略失败"
        print("✅ 策略添加成功")
        
        # 测试获取组合状态
        status = manager.get_portfolio_status()
        
        assert status['total_capital'] == 1000000.0, "总资金不正确"
        assert status['strategy_count'] == 1, "策略数量不正确"
        print("✅ 组合状态获取正确")
        
        # 测试资金分配
        success = manager.allocate_capital()
        assert success, "资金分配失败"
        print("✅ 资金分配成功")
        
        # 检查分配结果
        allocation = manager.strategy_allocations['test_ma_strategy']
        assert allocation.allocation_amount == 500000.0, "分配金额不正确"
        print("✅ 分配结果验证通过")
        
        # 测试策略组创建
        group_config = {
            'group_name': 'test_group',
            'strategies': ['test_ma_strategy'],
            'max_correlation': 0.7,
            'max_group_risk': 0.3
        }
        
        success = manager.create_strategy_group(group_config)
        assert success, "创建策略组失败"
        print("✅ 策略组创建成功")
        
        # 测试风险限制
        risk_limit = RiskLimit(
            level=RiskControlLevel.STRATEGY,
            target='test_ma_strategy',
            max_drawdown=0.1,
            max_daily_loss=0.05,
            max_position_size=0.3,
            var_limit=0.01
        )
        
        success = manager.add_risk_limit('test_risk_limit', risk_limit)
        assert success, "添加风险限制失败"
        print("✅ 风险限制添加成功")
        
        # 清理资源
        manager.cleanup()
        print("✅ 资源清理完成")
        
        print("🎉 多策略管理器基本功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 多策略管理器基本功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_portfolio_config_system():
    """测试策略组合配置系统"""
    print("\n=== 测试策略组合配置系统 ===")
    
    # 创建临时配置目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建配置管理器
        config_manager = ConfigManager(config_dir=temp_dir)
        
        print("✅ 配置管理器创建成功")
        
        # 创建投资组合配置
        config = config_manager.create_portfolio_config(
            portfolio_name="test_portfolio",
            total_capital=2000000.0,
            allocation_method="weighted"
        )
        
        assert config.portfolio_name == "test_portfolio", "组合名称不正确"
        assert config.total_capital == 2000000.0, "总资金不正确"
        print("✅ 投资组合配置创建成功")
        
        # 添加策略到组合
        success = config_manager.add_strategy_to_portfolio(
            config=config,
            strategy_name="ma_strategy_1",
            strategy_class="MAStrategy",
            strategy_module="strategies.ma_strategy",
            parameters={
                'fast_period': 5,
                'slow_period': 20,
                'subscribed_symbols': ['rb2405']
            },
            allocation_ratio=0.6
        )
        
        assert success, "添加策略到组合失败"
        assert len(config.strategies) == 1, "策略数量不正确"
        print("✅ 策略添加到组合成功")
        
        # 添加第二个策略
        success = config_manager.add_strategy_to_portfolio(
            config=config,
            strategy_name="ma_strategy_2",
            strategy_class="MAStrategy", 
            strategy_module="strategies.ma_strategy",
            parameters={
                'fast_period': 10,
                'slow_period': 30,
                'subscribed_symbols': ['i2405']
            },
            allocation_ratio=0.4
        )
        
        assert success, "添加第二个策略失败"
        assert len(config.strategies) == 2, "策略数量不正确"
        print("✅ 第二个策略添加成功")
        
        # 创建策略组
        success = config_manager.create_strategy_group(
            config=config,
            group_name="ma_group",
            strategy_names=["ma_strategy_1", "ma_strategy_2"],
            max_correlation=0.8
        )
        
        assert success, "创建策略组失败"
        assert len(config.strategy_groups) == 1, "策略组数量不正确"
        print("✅ 策略组创建成功")
        
        # 添加风险限制
        success = config_manager.add_risk_limit(
            config=config,
            limit_name="portfolio_limit",
            level="portfolio",
            target="test_portfolio",
            max_drawdown=0.15,
            max_daily_loss=0.03
        )
        
        assert success, "添加风险限制失败"
        assert len(config.risk_limits) == 1, "风险限制数量不正确"
        print("✅ 风险限制添加成功")
        
        # 保存配置
        success = config_manager.save_config(config, format="yaml")
        assert success, "保存配置失败"
        print("✅ 配置保存成功")
        
        # 加载配置
        loaded_config = config_manager.load_config("test_portfolio")
        assert loaded_config is not None, "加载配置失败"
        assert loaded_config.portfolio_name == "test_portfolio", "加载的配置名称不正确"
        assert len(loaded_config.strategies) == 2, "加载的策略数量不正确"
        print("✅ 配置加载成功")
        
        # 列出配置
        configs = config_manager.list_configs()
        assert "test_portfolio" in configs, "配置列表不正确"
        print("✅ 配置列表获取成功")
        
        print("🎉 策略组合配置系统测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 策略组合配置系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_config_template():
    """测试配置模板功能"""
    print("\n=== 测试配置模板功能 ===")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        config_manager = ConfigManager(config_dir=temp_dir)
        
        # 创建MA组合模板
        template_config = config_manager.create_template_config("ma_portfolio")
        
        assert template_config.portfolio_name == "ma_portfolio_template", "模板名称不正确"
        assert len(template_config.strategies) == 2, "模板策略数量不正确"
        assert len(template_config.strategy_groups) == 1, "模板策略组数量不正确"
        assert len(template_config.risk_limits) == 1, "模板风险限制数量不正确"
        print("✅ MA组合模板创建成功")
        
        # 保存模板
        success = config_manager.save_config(template_config, format="yaml")
        assert success, "保存模板失败"
        print("✅ 模板保存成功")
        
        # 验证模板内容
        strategy_names = [s.strategy_name for s in template_config.strategies]
        assert "ma_rb_5_20" in strategy_names, "模板策略名称不正确"
        assert "ma_i_10_30" in strategy_names, "模板策略名称不正确"
        
        group = template_config.strategy_groups[0]
        assert group.group_name == "ma_group", "模板策略组名称不正确"
        assert len(group.strategies) == 2, "模板策略组包含策略数量不正确"
        
        risk_limit = template_config.risk_limits[0]
        assert risk_limit.level == RiskControlLevel.PORTFOLIO, "模板风险限制级别不正确"
        print("✅ 模板内容验证通过")
        
        print("🎉 配置模板功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 配置模板功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_portfolio_deployment():
    """测试组合部署功能"""
    print("\n=== 测试组合部署功能 ===")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建配置管理器
        config_manager = ConfigManager(config_dir=temp_dir)
        
        # 创建并保存测试配置
        config = config_manager.create_template_config("ma_portfolio")
        config.portfolio_name = "deploy_test"
        config_manager.save_config(config)
        
        # 创建模拟引擎和管理器
        trading_engine, market_data_manager = create_mock_engines()
        manager_config = {
            'total_capital': 1000000.0,
            'allocation_method': 'equal'
        }
        
        multi_strategy_manager = MultiStrategyManager(
            trading_engine=trading_engine,
            market_data_manager=market_data_manager,
            config=manager_config
        )
        
        # 创建部署管理器
        deployment = PortfolioDeployment(config_manager)
        
        # 部署组合
        success = deployment.deploy_portfolio("deploy_test", multi_strategy_manager)
        assert success, "部署组合失败"
        print("✅ 组合部署成功")
        
        # 验证部署结果
        status = multi_strategy_manager.get_portfolio_status()
        assert status['strategy_count'] == 2, "部署的策略数量不正确"
        print("✅ 部署结果验证通过")
        
        # 验证策略组
        assert len(multi_strategy_manager.strategy_groups) == 1, "策略组数量不正确"
        group = list(multi_strategy_manager.strategy_groups.values())[0]
        assert len(group.strategies) == 2, "策略组包含策略数量不正确"
        print("✅ 策略组验证通过")
        
        # 验证风险限制
        assert len(multi_strategy_manager.risk_limits) == 1, "风险限制数量不正确"
        print("✅ 风险限制验证通过")
        
        # 清理资源
        multi_strategy_manager.cleanup()
        
        print("🎉 组合部署功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 组合部署功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_resource_allocation_methods():
    """测试不同的资金分配方式"""
    print("\n=== 测试资金分配方式 ===")
    
    try:
        trading_engine, market_data_manager = create_mock_engines()
        
        # 测试等额分配
        print("1. 测试等额分配...")
        config = {
            'total_capital': 1000000.0,
            'allocation_method': 'equal'
        }
        
        manager = MultiStrategyManager(
            trading_engine=trading_engine,
            market_data_manager=market_data_manager,
            config=config
        )
        
        # 添加两个策略
        for i in range(2):
            strategy_config = {
                'fast_period': 5 + i,
                'slow_period': 20 + i * 5,
                'subscribed_symbols': [f'test_symbol_{i}']
            }
            
            manager.add_strategy(
                strategy_name=f'strategy_{i}',
                strategy_class=MAStrategy,
                strategy_config=strategy_config
            )
        
        # 等额分配
        manager.allocation_method = StrategyAllocationMethod.EQUAL
        manager.allocate_capital()
        
        # 验证分配结果
        for i in range(2):
            allocation = manager.strategy_allocations[f'strategy_{i}']
            assert abs(allocation.allocation_amount - 500000.0) < 1.0, f"等额分配结果不正确: {allocation.allocation_amount}"
        
        print("✅ 等额分配验证通过")
        
        # 测试权重分配
        print("2. 测试权重分配...")
        
        # 设置权重
        manager.strategy_allocations['strategy_0'].allocation_ratio = 0.7
        manager.strategy_allocations['strategy_1'].allocation_ratio = 0.3
        
        manager.allocation_method = StrategyAllocationMethod.WEIGHTED
        manager.allocate_capital()
        
        # 验证权重分配结果
        alloc0 = manager.strategy_allocations['strategy_0']
        alloc1 = manager.strategy_allocations['strategy_1']
        
        assert abs(alloc0.allocation_amount - 700000.0) < 1.0, f"权重分配结果不正确: {alloc0.allocation_amount}"
        assert abs(alloc1.allocation_amount - 300000.0) < 1.0, f"权重分配结果不正确: {alloc1.allocation_amount}"
        
        print("✅ 权重分配验证通过")
        
        # 测试风险平价分配
        print("3. 测试风险平价分配...")
        
        # 设置风险预算
        manager.strategy_allocations['strategy_0'].risk_budget = 0.015
        manager.strategy_allocations['strategy_1'].risk_budget = 0.025
        
        manager.allocation_method = StrategyAllocationMethod.RISK_PARITY
        manager.allocate_capital()
        
        # 验证风险平价分配结果
        alloc0 = manager.strategy_allocations['strategy_0']
        alloc1 = manager.strategy_allocations['strategy_1']
        
        # 风险预算比例应该是 0.015/(0.015+0.025) = 0.375
        expected_0 = 1000000.0 * 0.375
        expected_1 = 1000000.0 * 0.625
        
        assert abs(alloc0.allocation_amount - expected_0) < 1.0, f"风险平价分配结果不正确: {alloc0.allocation_amount}"
        assert abs(alloc1.allocation_amount - expected_1) < 1.0, f"风险平价分配结果不正确: {alloc1.allocation_amount}"
        
        print("✅ 风险平价分配验证通过")
        
        manager.cleanup()
        
        print("🎉 资金分配方式测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 资金分配方式测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("🚀 开始运行多策略系统简化集成测试")
    
    # 配置日志
    logging.basicConfig(
        level=logging.WARNING,  # 降低日志级别减少输出
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    tests = [
        ("多策略管理器基本功能", test_multi_strategy_manager_basic),
        ("策略组合配置系统", test_portfolio_config_system),
        ("配置模板功能", test_config_template),
        ("组合部署功能", test_portfolio_deployment),
        ("资金分配方式", test_resource_allocation_methods),
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
    print(f"🏆 测试总结")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print(f"🎉 所有测试通过! 多策略系统Milestone 2.4基础功能验证成功!")
        return True
    else:
        print(f"⚠️ 有 {total-passed} 个测试失败")
        return False


if __name__ == '__main__':
    success = main()
    
    import sys
    sys.exit(0 if success else 1)