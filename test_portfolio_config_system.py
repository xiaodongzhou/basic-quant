#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio Configuration System Test

专门测试投资组合配置系统的功能
- 配置创建和管理
- 配置验证
- 配置文件IO
- 配置模板
"""

import sys
import os
import tempfile
import shutil
from datetime import datetime
import copy

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.strategy_portfolio_config import (
    ConfigManager, PortfolioConfig, StrategyConfig,
    ConfigValidator, PortfolioDeployment
)
from core.multi_strategy_manager import (
    StrategyAllocation, StrategyGroup, RiskLimit,
    StrategyAllocationMethod, RiskControlLevel
)


def test_portfolio_config_creation():
    """测试投资组合配置创建"""
    print("=== 测试投资组合配置创建 ===")
    
    try:
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(config_dir=temp_dir)
        
        # 创建基础配置
        config = config_manager.create_portfolio_config(
            portfolio_name="test_config",
            total_capital=5000000.0,
            allocation_method="weighted"
        )
        
        assert config.portfolio_name == "test_config"
        assert config.total_capital == 5000000.0
        assert config.allocation_method == "weighted"
        assert config.created_time is not None
        print("✅ 基础配置创建成功")
        
        # 添加策略
        success = config_manager.add_strategy_to_portfolio(
            config=config,
            strategy_name="momentum_strategy",
            strategy_class="MomentumStrategy",
            strategy_module="strategies.momentum_strategy",
            parameters={
                'lookback_period': 20,
                'threshold': 0.02,
                'symbols': ['rb2405', 'hc2405']
            },
            allocation_ratio=0.4
        )
        
        assert success
        assert len(config.strategies) == 1
        strategy = config.strategies[0]
        assert strategy.strategy_name == "momentum_strategy"
        assert strategy.parameters['lookback_period'] == 20
        print("✅ 策略添加成功")
        
        # 添加第二个策略
        success = config_manager.add_strategy_to_portfolio(
            config=config,
            strategy_name="mean_reversion_strategy",
            strategy_class="MeanReversionStrategy", 
            strategy_module="strategies.mean_reversion_strategy",
            parameters={
                'window_size': 30,
                'z_threshold': 2.0,
                'symbols': ['i2405', 'j2405']
            },
            allocation_ratio=0.6
        )
        
        assert success
        assert len(config.strategies) == 2
        assert len(config.strategy_allocations) == 2
        print("✅ 多策略配置成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_strategy_groups():
    """测试策略组功能"""
    print("\n=== 测试策略组功能 ===")
    
    try:
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(config_dir=temp_dir)
        
        # 创建配置并添加策略
        config = config_manager.create_portfolio_config("group_test")
        
        # 添加3个策略
        strategies = [
            ("trend_follow_1", "TrendStrategy", {'period': 20}),
            ("trend_follow_2", "TrendStrategy", {'period': 50}), 
            ("contrarian_1", "ContrarianStrategy", {'threshold': 0.05})
        ]
        
        for name, cls, params in strategies:
            config_manager.add_strategy_to_portfolio(
                config=config,
                strategy_name=name,
                strategy_class=cls,
                strategy_module=f"strategies.{cls.lower()}",
                parameters=params
            )
        
        assert len(config.strategies) == 3
        print("✅ 多个策略添加成功")
        
        # 创建趋势策略组
        success = config_manager.create_strategy_group(
            config=config,
            group_name="trend_group",
            strategy_names=["trend_follow_1", "trend_follow_2"],
            max_correlation=0.8,
            max_group_risk=0.4
        )
        
        assert success
        assert len(config.strategy_groups) == 1
        group = config.strategy_groups[0]
        assert group.group_name == "trend_group"
        assert len(group.strategies) == 2
        assert "trend_follow_1" in group.strategies
        assert "trend_follow_2" in group.strategies
        print("✅ 趋势策略组创建成功")
        
        # 创建混合策略组
        success = config_manager.create_strategy_group(
            config=config,
            group_name="mixed_group", 
            strategy_names=["trend_follow_1", "contrarian_1"],
            max_correlation=0.5
        )
        
        assert success
        assert len(config.strategy_groups) == 2
        print("✅ 混合策略组创建成功")
        
        # 测试无效策略组创建
        success = config_manager.create_strategy_group(
            config=config,
            group_name="invalid_group",
            strategy_names=["nonexistent_strategy"],
            max_correlation=0.7
        )
        
        assert not success  # 应该失败
        assert len(config.strategy_groups) == 2  # 数量不变
        print("✅ 无效策略组正确拒绝")
        
        return True
        
    except Exception as e:
        print(f"❌ 策略组测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_risk_limits():
    """测试风险限制功能"""
    print("\n=== 测试风险限制功能 ===")
    
    try:
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(config_dir=temp_dir)
        
        config = config_manager.create_portfolio_config("risk_test")
        
        # 添加策略
        config_manager.add_strategy_to_portfolio(
            config=config,
            strategy_name="test_strategy",
            strategy_class="TestStrategy", 
            strategy_module="strategies.test_strategy",
            parameters={}
        )
        
        # 添加策略级风险限制
        success = config_manager.add_risk_limit(
            config=config,
            limit_name="strategy_risk",
            level="strategy",
            target="test_strategy",
            max_drawdown=0.1,
            max_daily_loss=0.03,
            max_position_size=0.5
        )
        
        assert success
        assert len(config.risk_limits) == 1
        
        risk_limit = config.risk_limits[0]
        assert risk_limit.level == RiskControlLevel.STRATEGY
        assert risk_limit.target == "test_strategy"
        assert risk_limit.max_drawdown == 0.1
        assert risk_limit.max_daily_loss == 0.03
        print("✅ 策略级风险限制添加成功")
        
        # 添加组合级风险限制
        success = config_manager.add_risk_limit(
            config=config,
            limit_name="portfolio_risk",
            level="portfolio", 
            target="risk_test",
            max_drawdown=0.15,
            max_daily_loss=0.05,
            max_position_size=0.8
        )
        
        assert success
        assert len(config.risk_limits) == 2
        
        portfolio_limit = config.risk_limits[1]
        assert portfolio_limit.level == RiskControlLevel.PORTFOLIO
        assert portfolio_limit.target == "risk_test"
        print("✅ 组合级风险限制添加成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 风险限制测试失败: {e}")
        return False
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_config_validation():
    """测试配置验证功能"""
    print("\n=== 测试配置验证功能 ===")
    
    try:
        validator = ConfigValidator()
        
        # 测试有效配置
        valid_config = PortfolioConfig(
            portfolio_name="valid_test",
            total_capital=1000000.0,
            allocation_method="equal"
        )
        
        valid_config.strategies.append(StrategyConfig(
            strategy_name="strategy1",
            strategy_class="TestStrategy",
            strategy_module="strategies.test"
        ))
        
        valid, errors = validator.validate_portfolio_config(valid_config)
        assert valid
        assert len(errors) == 0
        print("✅ 有效配置验证通过")
        
        # 测试无效配置 - 空名称
        invalid_config1 = PortfolioConfig(
            portfolio_name="",  # 空名称
            total_capital=1000000.0
        )
        
        valid, errors = validator.validate_portfolio_config(invalid_config1)
        assert not valid
        assert "投资组合名称不能为空" in errors
        print("✅ 空名称正确检测")
        
        # 测试无效配置 - 负资金
        invalid_config2 = PortfolioConfig(
            portfolio_name="test",
            total_capital=-100000.0  # 负数
        )
        
        valid, errors = validator.validate_portfolio_config(invalid_config2)
        assert not valid
        assert "总资金必须大于0" in errors
        print("✅ 负资金正确检测")
        
        # 测试策略名称重复
        invalid_config3 = PortfolioConfig(
            portfolio_name="duplicate_test",
            total_capital=1000000.0
        )
        
        # 添加重复名称的策略
        for i in range(2):
            invalid_config3.strategies.append(StrategyConfig(
                strategy_name="duplicate_strategy",  # 相同名称
                strategy_class="TestStrategy",
                strategy_module="strategies.test"
            ))
        
        valid, errors = validator.validate_portfolio_config(invalid_config3)
        assert not valid
        assert any("策略名称重复" in error for error in errors)
        print("✅ 重复策略名称正确检测")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置验证测试失败: {e}")
        return False


def test_config_file_io():
    """测试配置文件IO功能"""
    print("\n=== 测试配置文件IO功能 ===")
    
    try:
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(config_dir=temp_dir)
        
        # 创建复杂配置
        config = config_manager.create_portfolio_config(
            portfolio_name="io_test_config",
            total_capital=2000000.0,
            allocation_method="risk_parity"
        )
        
        # 添加策略
        strategies_data = [
            ("ma_fast", "MAStrategy", {"fast": 5, "slow": 20}),
            ("ma_slow", "MAStrategy", {"fast": 10, "slow": 50}),
            ("rsi_strategy", "RSIStrategy", {"period": 14, "threshold": [30, 70]})
        ]
        
        for name, cls, params in strategies_data:
            config_manager.add_strategy_to_portfolio(
                config=config,
                strategy_name=name,
                strategy_class=cls,
                strategy_module=f"strategies.{name}",
                parameters=params,
                allocation_ratio=1.0/len(strategies_data)
            )
        
        # 添加策略组和风险限制
        config_manager.create_strategy_group(
            config=config,
            group_name="ma_group",
            strategy_names=["ma_fast", "ma_slow"]
        )
        
        config_manager.add_risk_limit(
            config=config,
            limit_name="global_risk",
            level="portfolio",
            target="io_test_config",
            max_drawdown=0.2
        )
        
        print("✅ 复杂配置创建成功")
        
        # 保存为YAML格式
        success = config_manager.save_config(config, format="yaml")
        assert success
        print("✅ YAML格式保存成功")
        
        # 创建副本用于JSON保存，避免修改原配置对象
        json_config = copy.deepcopy(config)
        json_config.portfolio_name = "io_test_config_json"
        success = config_manager.save_config(json_config, format="json")
        assert success
        print("✅ JSON格式保存成功")
        
        # 加载YAML配置
        loaded_yaml = config_manager.load_config("io_test_config")
        assert loaded_yaml is not None
        assert loaded_yaml.portfolio_name == "io_test_config"
        assert loaded_yaml.total_capital == 2000000.0
        assert len(loaded_yaml.strategies) == 3
        assert len(loaded_yaml.strategy_groups) == 1
        assert len(loaded_yaml.risk_limits) == 1
        print("✅ YAML配置加载成功")
        
        # 加载JSON配置
        loaded_json = config_manager.load_config("io_test_config_json")
        assert loaded_json is not None
        assert loaded_json.portfolio_name == "io_test_config_json"
        assert len(loaded_json.strategies) == 3
        print("✅ JSON配置加载成功")
        
        # 验证数据一致性
        assert loaded_yaml.allocation_method == loaded_json.allocation_method
        assert len(loaded_yaml.strategies) == len(loaded_json.strategies)
        
        # 检查策略参数
        yaml_strategy = next(s for s in loaded_yaml.strategies if s.strategy_name == "rsi_strategy")
        json_strategy = next(s for s in loaded_json.strategies if s.strategy_name == "rsi_strategy")
        
        assert yaml_strategy.parameters["period"] == json_strategy.parameters["period"]
        assert yaml_strategy.parameters["threshold"] == json_strategy.parameters["threshold"]
        print("✅ 配置数据一致性验证通过")
        
        # 列出配置文件
        configs = config_manager.list_configs()
        assert "io_test_config" in configs
        assert "io_test_config_json" in configs
        print("✅ 配置列表功能正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置文件IO测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_config_templates():
    """测试配置模板功能"""
    print("\n=== 测试配置模板功能 ===")
    
    try:
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(config_dir=temp_dir)
        
        # 测试MA组合模板
        ma_template = config_manager.create_template_config("ma_portfolio")
        
        assert ma_template.portfolio_name == "ma_portfolio_template"
        assert ma_template.total_capital == 1000000.0
        assert len(ma_template.strategies) == 2
        assert len(ma_template.strategy_groups) == 1
        assert len(ma_template.risk_limits) == 1
        print("✅ MA组合模板创建成功")
        
        # 验证模板内容
        strategy_names = [s.strategy_name for s in ma_template.strategies]
        assert "ma_rb_5_20" in strategy_names
        assert "ma_i_10_30" in strategy_names
        
        # 检查策略参数
        rb_strategy = next(s for s in ma_template.strategies if s.strategy_name == "ma_rb_5_20")
        assert rb_strategy.strategy_class == "MAStrategy"
        assert rb_strategy.parameters["fast_period"] == 5
        assert rb_strategy.parameters["slow_period"] == 20
        assert "rb2405" in rb_strategy.parameters["subscribed_symbols"]
        print("✅ MA模板内容验证通过")
        
        # 验证策略组
        ma_group = ma_template.strategy_groups[0]
        assert ma_group.group_name == "ma_group"
        assert len(ma_group.strategies) == 2
        assert ma_group.max_correlation == 0.6
        print("✅ 策略组配置正确")
        
        # 验证风险限制
        risk_limit = ma_template.risk_limits[0]
        assert risk_limit.level == RiskControlLevel.PORTFOLIO
        assert risk_limit.max_drawdown == 0.15
        assert risk_limit.max_daily_loss == 0.03
        print("✅ 风险限制配置正确")
        
        # 保存模板
        success = config_manager.save_config(ma_template)
        assert success
        
        # 加载验证
        loaded_template = config_manager.load_config("ma_portfolio_template")
        assert loaded_template is not None
        assert len(loaded_template.strategies) == 2
        print("✅ 模板保存加载成功")
        
        # 测试多策略模板
        multi_template = config_manager.create_template_config("multi_strategy")
        
        assert multi_template.portfolio_name == "multi_strategy_template"
        assert multi_template.total_capital == 2000000.0
        assert multi_template.allocation_method == "weighted"
        assert "risk_free_rate" in multi_template.global_parameters
        print("✅ 多策略模板创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置模板测试失败: {e}")
        return False
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_allocation_config():
    """测试资金分配配置"""
    print("\n=== 测试资金分配配置 ===")
    
    try:
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(config_dir=temp_dir)
        
        # 创建配置
        config = config_manager.create_portfolio_config(
            portfolio_name="allocation_test",
            total_capital=3000000.0,
            allocation_method="weighted"
        )
        
        # 添加策略并指定分配
        strategies_config = [
            ("conservative", 0.5, 0.01),  # 50%分配，1%风险
            ("aggressive", 0.3, 0.03),    # 30%分配，3%风险
            ("speculative", 0.2, 0.05)   # 20%分配，5%风险
        ]
        
        total_ratio = sum(ratio for _, ratio, _ in strategies_config)
        
        for name, ratio, risk in strategies_config:
            config_manager.add_strategy_to_portfolio(
                config=config,
                strategy_name=name,
                strategy_class="GenericStrategy",
                strategy_module="strategies.generic",
                parameters={"risk_level": risk},
                allocation_ratio=ratio,
                risk_budget=risk
            )
        
        assert len(config.strategies) == 3
        assert len(config.strategy_allocations) == 3
        print("✅ 多策略分配配置成功")
        
        # 验证分配比例
        total_allocated_ratio = sum(alloc.allocation_ratio for alloc in config.strategy_allocations)
        assert abs(total_allocated_ratio - 1.0) < 0.001  # 应该等于1
        
        # 验证具体分配
        conservative_alloc = next(alloc for alloc in config.strategy_allocations 
                                if alloc.strategy_name == "conservative")
        assert conservative_alloc.allocation_ratio == 0.5
        assert conservative_alloc.risk_budget == 0.01
        print("✅ 分配比例验证正确")
        
        # 保存并重新加载验证
        config_manager.save_config(config)
        loaded_config = config_manager.load_config("allocation_test")
        
        assert loaded_config is not None
        assert len(loaded_config.strategy_allocations) == 3
        
        loaded_conservative = next(alloc for alloc in loaded_config.strategy_allocations 
                                 if alloc.strategy_name == "conservative")
        assert loaded_conservative.allocation_ratio == 0.5
        print("✅ 分配配置持久化成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 资金分配配置测试失败: {e}")
        return False
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """运行所有配置系统测试"""
    print("🚀 开始运行投资组合配置系统测试")
    
    tests = [
        ("投资组合配置创建", test_portfolio_config_creation),
        ("策略组功能", test_strategy_groups),
        ("风险限制功能", test_risk_limits),
        ("配置验证功能", test_config_validation),
        ("配置文件IO", test_config_file_io),
        ("配置模板功能", test_config_templates),
        ("资金分配配置", test_allocation_config),
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
    print(f"🏆 配置系统测试总结")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print(f"🎉 所有配置系统测试通过! Milestone 2.4核心功能验证成功!")
        return True
    else:
        print(f"⚠️ 有 {total-passed} 个测试失败")
        return False


if __name__ == '__main__':
    success = main()
    
    import sys
    sys.exit(0 if success else 1)