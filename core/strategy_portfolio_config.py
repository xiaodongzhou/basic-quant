#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy Portfolio Configuration System - 策略组合配置系统

负责管理多策略组合的配置、验证和部署
- 策略组合配置管理
- 配置文件解析和验证
- 动态配置更新
- 配置模板管理
"""

import json
import yaml
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging
from pathlib import Path

from .multi_strategy_manager import (
    StrategyAllocation, StrategyGroup, RiskLimit, 
    StrategyAllocationMethod, RiskControlLevel
)


@dataclass
class StrategyConfig:
    """单个策略配置"""
    strategy_name: str
    strategy_class: str             # 策略类名
    strategy_module: str            # 策略模块路径
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class PortfolioConfig:
    """投资组合配置"""
    portfolio_name: str
    description: str = ""
    total_capital: float = 1000000.0
    allocation_method: str = "equal"
    
    # 策略配置
    strategies: List[StrategyConfig] = field(default_factory=list)
    strategy_allocations: List[StrategyAllocation] = field(default_factory=list)
    strategy_groups: List[StrategyGroup] = field(default_factory=list)
    risk_limits: List[RiskLimit] = field(default_factory=list)
    
    # 全局参数
    global_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 运行时配置
    auto_start: bool = True
    monitoring_enabled: bool = True
    reporting_enabled: bool = True
    
    # 元数据
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None
    version: str = "1.0.0"


class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_portfolio_config(config: PortfolioConfig) -> tuple[bool, List[str]]:
        """验证投资组合配置"""
        errors = []
        
        # 基本验证
        if not config.portfolio_name:
            errors.append("投资组合名称不能为空")
        
        if config.total_capital <= 0:
            errors.append("总资金必须大于0")
        
        if config.allocation_method not in ['equal', 'weighted', 'risk_parity', 'dynamic']:
            errors.append(f"不支持的资金分配方式: {config.allocation_method}")
        
        # 策略配置验证
        strategy_names = set()
        for strategy in config.strategies:
            if not strategy.strategy_name:
                errors.append("策略名称不能为空")
            
            if strategy.strategy_name in strategy_names:
                errors.append(f"策略名称重复: {strategy.strategy_name}")
            strategy_names.add(strategy.strategy_name)
            
            if not strategy.strategy_class:
                errors.append(f"策略 {strategy.strategy_name} 缺少策略类名")
        
        # 资金分配验证
        if config.strategy_allocations:
            total_allocation = sum(alloc.allocation_amount for alloc in config.strategy_allocations)
            if abs(total_allocation - config.total_capital) > 0.01:
                errors.append(f"资金分配总额 {total_allocation} 与总资金 {config.total_capital} 不匹配")
        
        # 策略组验证
        for group in config.strategy_groups:
            if not group.group_name:
                errors.append("策略组名称不能为空")
            
            for strategy_name in group.strategies:
                if strategy_name not in strategy_names:
                    errors.append(f"策略组 {group.group_name} 中的策略 {strategy_name} 不存在")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_strategy_config(config: StrategyConfig) -> tuple[bool, List[str]]:
        """验证策略配置"""
        errors = []
        
        if not config.strategy_name:
            errors.append("策略名称不能为空")
        
        if not config.strategy_class:
            errors.append("策略类名不能为空")
        
        if not config.strategy_module:
            errors.append("策略模块路径不能为空")
        
        return len(errors) == 0, errors


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("ConfigManager")
        self.validator = ConfigValidator()
        
        # 配置缓存
        self._config_cache: Dict[str, PortfolioConfig] = {}
        
    def create_portfolio_config(self, 
                              portfolio_name: str,
                              total_capital: float = 1000000.0,
                              allocation_method: str = "equal") -> PortfolioConfig:
        """创建新的投资组合配置"""
        
        config = PortfolioConfig(
            portfolio_name=portfolio_name,
            total_capital=total_capital,
            allocation_method=allocation_method,
            created_time=datetime.now(),
            updated_time=datetime.now()
        )
        
        self.logger.info(f"创建投资组合配置: {portfolio_name}")
        return config
    
    def add_strategy_to_portfolio(self,
                                config: PortfolioConfig,
                                strategy_name: str,
                                strategy_class: str,
                                strategy_module: str,
                                parameters: Optional[Dict[str, Any]] = None,
                                allocation_amount: Optional[float] = None,
                                allocation_ratio: Optional[float] = None,
                                risk_budget: Optional[float] = None) -> bool:
        """添加策略到投资组合"""
        
        try:
            # 创建策略配置
            strategy_config = StrategyConfig(
                strategy_name=strategy_name,
                strategy_class=strategy_class,
                strategy_module=strategy_module,
                parameters=parameters or {}
            )
            
            # 验证策略配置
            valid, errors = self.validator.validate_strategy_config(strategy_config)
            if not valid:
                self.logger.error(f"策略配置验证失败: {errors}")
                return False
            
            # 添加到配置
            config.strategies.append(strategy_config)
            
            # 如果指定了资金分配，创建分配配置
            if allocation_amount is not None or allocation_ratio is not None:
                allocation = StrategyAllocation(
                    strategy_name=strategy_name,
                    allocation_amount=allocation_amount or 0.0,
                    allocation_ratio=allocation_ratio or 0.0,
                    max_position_ratio=0.8,
                    risk_budget=risk_budget or 0.02
                )
                config.strategy_allocations.append(allocation)
            
            # 更新时间
            config.updated_time = datetime.now()
            
            self.logger.info(f"策略 {strategy_name} 添加到投资组合 {config.portfolio_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加策略失败: {e}")
            return False
    
    def create_strategy_group(self,
                            config: PortfolioConfig,
                            group_name: str,
                            strategy_names: List[str],
                            max_correlation: float = 0.7,
                            max_group_risk: float = 0.3) -> bool:
        """创建策略组"""
        
        try:
            # 验证策略是否存在
            existing_strategies = {s.strategy_name for s in config.strategies}
            for strategy_name in strategy_names:
                if strategy_name not in existing_strategies:
                    self.logger.error(f"策略 {strategy_name} 不存在于投资组合中")
                    return False
            
            # 创建策略组
            group = StrategyGroup(
                group_name=group_name,
                strategies=strategy_names,
                max_correlation=max_correlation,
                max_group_risk=max_group_risk
            )
            
            config.strategy_groups.append(group)
            config.updated_time = datetime.now()
            
            self.logger.info(f"策略组 {group_name} 创建成功")
            return True
            
        except Exception as e:
            self.logger.error(f"创建策略组失败: {e}")
            return False
    
    def add_risk_limit(self,
                      config: PortfolioConfig,
                      limit_name: str,
                      level: str,
                      target: str,
                      max_drawdown: float = 0.1,
                      max_daily_loss: float = 0.05,
                      max_position_size: float = 0.3) -> bool:
        """添加风险限制"""
        
        try:
            risk_limit = RiskLimit(
                level=RiskControlLevel(level),
                target=target,
                max_drawdown=max_drawdown,
                max_daily_loss=max_daily_loss,
                max_position_size=max_position_size,
                var_limit=0.01
            )
            
            config.risk_limits.append(risk_limit)
            config.updated_time = datetime.now()
            
            self.logger.info(f"风险限制 {limit_name} 添加成功")
            return True
            
        except Exception as e:
            self.logger.error(f"添加风险限制失败: {e}")
            return False
    
    def save_config(self, config: PortfolioConfig, format: str = "yaml") -> bool:
        """保存配置到文件"""
        
        try:
            filename = f"{config.portfolio_name}.{format}"
            filepath = self.config_dir / filename
            
            # 转换为字典
            config_dict = self._config_to_dict(config)
            
            # 保存文件
            if format.lower() == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2, ensure_ascii=False, default=str)
            elif format.lower() == "yaml":
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            else:
                raise ValueError(f"不支持的文件格式: {format}")
            
            # 更新缓存
            self._config_cache[config.portfolio_name] = config
            
            self.logger.info(f"配置已保存到: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            return False
    
    def load_config(self, portfolio_name: str) -> Optional[PortfolioConfig]:
        """从文件加载配置"""
        
        try:
            # 检查缓存
            if portfolio_name in self._config_cache:
                return self._config_cache[portfolio_name]
            
            # 尝试不同格式的文件
            for ext in ['yaml', 'yml', 'json']:
                filepath = self.config_dir / f"{portfolio_name}.{ext}"
                if filepath.exists():
                    return self._load_config_file(filepath)
            
            self.logger.warning(f"未找到投资组合配置文件: {portfolio_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            return None
    
    def _load_config_file(self, filepath: Path) -> Optional[PortfolioConfig]:
        """从文件加载配置"""
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                if filepath.suffix.lower() == '.json':
                    config_dict = json.load(f)
                else:  # yaml
                    config_dict = yaml.safe_load(f)
            
            # 转换为配置对象
            config = self._dict_to_config(config_dict)
            
            # 验证配置
            valid, errors = self.validator.validate_portfolio_config(config)
            if not valid:
                self.logger.error(f"配置验证失败: {errors}")
                return None
            
            # 更新缓存
            self._config_cache[config.portfolio_name] = config
            
            self.logger.info(f"配置加载成功: {filepath}")
            return config
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败 {filepath}: {e}")
            return None
    
    def _config_to_dict(self, config: PortfolioConfig) -> dict:
        """将配置对象转换为字典"""
        
        config_dict = asdict(config)
        
        # 处理特殊字段
        if config_dict.get('created_time'):
            config_dict['created_time'] = config.created_time.isoformat()
        if config_dict.get('updated_time'):
            config_dict['updated_time'] = config.updated_time.isoformat()
        
        # 处理枚举类型
        for allocation in config_dict.get('strategy_allocations', []):
            # allocation 已经是 dict，无需特殊处理
            pass
        
        for risk_limit in config_dict.get('risk_limits', []):
            if 'level' in risk_limit:
                risk_limit['level'] = risk_limit['level']  # 已经是字符串
        
        return config_dict
    
    def _dict_to_config(self, config_dict: dict) -> PortfolioConfig:
        """将字典转换为配置对象"""
        
        # 处理时间字段
        if config_dict.get('created_time'):
            config_dict['created_time'] = datetime.fromisoformat(config_dict['created_time'])
        if config_dict.get('updated_time'):
            config_dict['updated_time'] = datetime.fromisoformat(config_dict['updated_time'])
        
        # 处理策略配置
        strategies = []
        for strategy_dict in config_dict.get('strategies', []):
            strategies.append(StrategyConfig(**strategy_dict))
        config_dict['strategies'] = strategies
        
        # 处理资金分配
        allocations = []
        for alloc_dict in config_dict.get('strategy_allocations', []):
            allocations.append(StrategyAllocation(**alloc_dict))
        config_dict['strategy_allocations'] = allocations
        
        # 处理策略组
        groups = []
        for group_dict in config_dict.get('strategy_groups', []):
            groups.append(StrategyGroup(**group_dict))
        config_dict['strategy_groups'] = groups
        
        # 处理风险限制
        risk_limits = []
        for limit_dict in config_dict.get('risk_limits', []):
            if 'level' in limit_dict:
                limit_dict['level'] = RiskControlLevel(limit_dict['level'])
            risk_limits.append(RiskLimit(**limit_dict))
        config_dict['risk_limits'] = risk_limits
        
        return PortfolioConfig(**config_dict)
    
    def list_configs(self) -> List[str]:
        """列出所有配置文件"""
        
        configs = []
        for ext in ['yaml', 'yml', 'json']:
            for filepath in self.config_dir.glob(f"*.{ext}"):
                config_name = filepath.stem
                if config_name not in configs:
                    configs.append(config_name)
        
        return sorted(configs)
    
    def delete_config(self, portfolio_name: str) -> bool:
        """删除配置"""
        
        try:
            # 删除文件
            deleted = False
            for ext in ['yaml', 'yml', 'json']:
                filepath = self.config_dir / f"{portfolio_name}.{ext}"
                if filepath.exists():
                    filepath.unlink()
                    deleted = True
            
            # 从缓存中删除
            if portfolio_name in self._config_cache:
                del self._config_cache[portfolio_name]
            
            if deleted:
                self.logger.info(f"配置 {portfolio_name} 删除成功")
            else:
                self.logger.warning(f"配置文件不存在: {portfolio_name}")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"删除配置失败: {e}")
            return False
    
    def create_template_config(self, template_name: str) -> PortfolioConfig:
        """创建配置模板"""
        
        if template_name == "ma_portfolio":
            return self._create_ma_portfolio_template()
        elif template_name == "multi_strategy":
            return self._create_multi_strategy_template()
        else:
            return self.create_portfolio_config(f"{template_name}_portfolio")
    
    def _create_ma_portfolio_template(self) -> PortfolioConfig:
        """创建MA策略组合模板"""
        
        config = self.create_portfolio_config(
            portfolio_name="ma_portfolio_template",
            total_capital=1000000.0,
            allocation_method="equal"
        )
        
        # 添加MA策略
        self.add_strategy_to_portfolio(
            config=config,
            strategy_name="ma_rb_5_20",
            strategy_class="MAStrategy",
            strategy_module="strategies.ma_strategy",
            parameters={
                'fast_period': 5,
                'slow_period': 20,
                'trade_volume': 1,
                'max_position': 5,
                'subscribed_symbols': ['rb2405']
            },
            allocation_ratio=0.5
        )
        
        self.add_strategy_to_portfolio(
            config=config,
            strategy_name="ma_i_10_30",
            strategy_class="MAStrategy",
            strategy_module="strategies.ma_strategy",
            parameters={
                'fast_period': 10,
                'slow_period': 30,
                'trade_volume': 2,
                'max_position': 8,
                'subscribed_symbols': ['i2405']
            },
            allocation_ratio=0.5
        )
        
        # 创建策略组
        self.create_strategy_group(
            config=config,
            group_name="ma_group",
            strategy_names=["ma_rb_5_20", "ma_i_10_30"],
            max_correlation=0.6
        )
        
        # 添加风险限制
        self.add_risk_limit(
            config=config,
            limit_name="portfolio_risk",
            level="portfolio",
            target="ma_portfolio_template",
            max_drawdown=0.15,
            max_daily_loss=0.03
        )
        
        return config
    
    def _create_multi_strategy_template(self) -> PortfolioConfig:
        """创建多策略组合模板"""
        
        config = self.create_portfolio_config(
            portfolio_name="multi_strategy_template",
            total_capital=2000000.0,
            allocation_method="weighted"
        )
        
        # 设置全局参数
        config.global_parameters = {
            'risk_free_rate': 0.03,
            'benchmark': 'CSI300',
            'rebalance_frequency': 'monthly'
        }
        
        return config


class PortfolioDeployment:
    """组合部署管理"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = logging.getLogger("PortfolioDeployment")
    
    def deploy_portfolio(self, 
                        portfolio_name: str, 
                        multi_strategy_manager) -> bool:
        """部署投资组合"""
        
        try:
            # 加载配置
            config = self.config_manager.load_config(portfolio_name)
            if not config:
                self.logger.error(f"无法加载投资组合配置: {portfolio_name}")
                return False
            
            self.logger.info(f"开始部署投资组合: {portfolio_name}")
            
            # 设置总资金
            multi_strategy_manager.total_capital = config.total_capital
            multi_strategy_manager.allocation_method = StrategyAllocationMethod(config.allocation_method)
            
            # 添加策略
            for strategy_config in config.strategies:
                if not strategy_config.enabled:
                    continue
                
                # 动态导入策略类
                strategy_class = self._import_strategy_class(
                    strategy_config.strategy_module, 
                    strategy_config.strategy_class
                )
                
                if not strategy_class:
                    self.logger.error(f"无法导入策略类: {strategy_config.strategy_class}")
                    continue
                
                # 查找对应的资金分配
                allocation_config = None
                for alloc in config.strategy_allocations:
                    if alloc.strategy_name == strategy_config.strategy_name:
                        allocation_config = {
                            'amount': alloc.allocation_amount,
                            'ratio': alloc.allocation_ratio,
                            'max_position_ratio': alloc.max_position_ratio,
                            'risk_budget': alloc.risk_budget
                        }
                        break
                
                # 添加策略到管理器
                success = multi_strategy_manager.add_strategy(
                    strategy_name=strategy_config.strategy_name,
                    strategy_class=strategy_class,
                    strategy_config=strategy_config.parameters,
                    allocation_config=allocation_config
                )
                
                if success:
                    self.logger.info(f"策略 {strategy_config.strategy_name} 部署成功")
                else:
                    self.logger.error(f"策略 {strategy_config.strategy_name} 部署失败")
            
            # 创建策略组
            for group in config.strategy_groups:
                if group.active:
                    group_config = {
                        'group_name': group.group_name,
                        'strategies': group.strategies,
                        'max_correlation': group.max_correlation,
                        'max_group_risk': group.max_group_risk,
                        'rebalance_frequency': group.rebalance_frequency
                    }
                    
                    multi_strategy_manager.create_strategy_group(group_config)
            
            # 添加风险限制
            for risk_limit in config.risk_limits:
                if risk_limit.active:
                    multi_strategy_manager.add_risk_limit(
                        limit_name=f"{risk_limit.level.value}_{risk_limit.target}",
                        risk_limit=risk_limit
                    )
            
            self.logger.info(f"投资组合 {portfolio_name} 部署完成")
            return True
            
        except Exception as e:
            self.logger.error(f"部署投资组合失败: {e}")
            return False
    
    def _import_strategy_class(self, module_name: str, class_name: str):
        """动态导入策略类"""
        
        try:
            import importlib
            module = importlib.import_module(module_name)
            strategy_class = getattr(module, class_name)
            return strategy_class
            
        except Exception as e:
            self.logger.error(f"导入策略类失败 {module_name}.{class_name}: {e}")
            return None