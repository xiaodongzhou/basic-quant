#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy Portfolio - 策略组合配置和管理

提供策略组合的配置加载、验证和管理功能
"""

import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import logging

from .multi_strategy_manager import (
    StrategyAllocation, StrategyGroup, RiskLimit, 
    StrategyAllocationMethod, RiskControlLevel
)


@dataclass
class PortfolioConfig:
    """组合配置"""
    name: str
    description: str
    total_capital: float
    allocation_method: str
    rebalance_frequency: str
    risk_tolerance: float
    
    strategies: List[dict]
    groups: List[dict] = None
    risk_limits: List[dict] = None
    
    # 高级配置
    max_correlation: float = 0.7
    max_portfolio_var: float = 0.05
    emergency_stop_loss: float = 0.1
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PortfolioConfig':
        """从字典创建"""
        return cls(**data)


class PortfolioConfigManager:
    """组合配置管理器"""
    
    def __init__(self, config_dir: str = "configs/portfolios"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("PortfolioConfigManager")
    
    def create_default_config(self) -> PortfolioConfig:
        """创建默认配置"""
        return PortfolioConfig(
            name="默认组合",
            description="基础多策略组合配置",
            total_capital=1000000.0,
            allocation_method="equal",
            rebalance_frequency="daily",
            risk_tolerance=0.02,
            strategies=[
                {
                    "name": "ma_strategy_1",
                    "class": "MAStrategy", 
                    "config": {
                        "fast_period": 5,
                        "slow_period": 20,
                        "trade_volume": 1,
                        "subscribed_symbols": ["rb2405"]
                    },
                    "allocation": {
                        "ratio": 0.5,
                        "max_position_ratio": 0.8,
                        "risk_budget": 0.02
                    }
                },
                {
                    "name": "ma_strategy_2", 
                    "class": "MAStrategy",
                    "config": {
                        "fast_period": 10,
                        "slow_period": 30,
                        "trade_volume": 1,
                        "subscribed_symbols": ["i2405"]
                    },
                    "allocation": {
                        "ratio": 0.5,
                        "max_position_ratio": 0.8,
                        "risk_budget": 0.02
                    }
                }
            ],
            groups=[
                {
                    "group_name": "ma_group",
                    "strategies": ["ma_strategy_1", "ma_strategy_2"],
                    "max_correlation": 0.7,
                    "max_group_risk": 0.3
                }
            ],
            risk_limits=[
                {
                    "level": "portfolio",
                    "target": "portfolio",
                    "max_drawdown": 0.15,
                    "max_daily_loss": 0.05,
                    "max_position_size": 0.8,
                    "var_limit": 0.05
                }
            ]
        )
    
    def save_config(self, config: PortfolioConfig, filename: str) -> bool:
        """保存配置"""
        try:
            filepath = self.config_dir / filename
            
            # 支持JSON和YAML格式
            if filename.endswith('.json'):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            elif filename.endswith('.yaml') or filename.endswith('.yml'):
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(config.to_dict(), f, default_flow_style=False, 
                             allow_unicode=True, indent=2)
            else:
                raise ValueError("不支持的文件格式，请使用.json或.yaml")
            
            self.logger.info(f"配置已保存到: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            return False
    
    def load_config(self, filename: str) -> Optional[PortfolioConfig]:
        """加载配置"""
        try:
            filepath = self.config_dir / filename
            
            if not filepath.exists():
                self.logger.error(f"配置文件不存在: {filepath}")
                return None
            
            # 根据文件扩展名选择解析器
            if filename.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif filename.endswith('.yaml') or filename.endswith('.yml'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            else:
                raise ValueError("不支持的文件格式")
            
            config = PortfolioConfig.from_dict(data)
            
            # 验证配置
            if self.validate_config(config):
                self.logger.info(f"配置加载成功: {filename}")
                return config
            else:
                self.logger.error(f"配置验证失败: {filename}")
                return None
                
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            return None
    
    def validate_config(self, config: PortfolioConfig) -> bool:
        """验证配置"""
        try:
            # 基本字段验证
            if not config.name or not config.strategies:
                self.logger.error("配置缺少必要字段")
                return False
            
            if config.total_capital <= 0:
                self.logger.error("总资本必须大于0")
                return False
            
            # 验证分配方法
            valid_methods = ['equal', 'weighted', 'risk_parity', 'dynamic']
            if config.allocation_method not in valid_methods:
                self.logger.error(f"无效的分配方法: {config.allocation_method}")
                return False
            
            # 验证策略配置
            strategy_names = []
            total_ratio = 0.0
            
            for strategy_config in config.strategies:
                if 'name' not in strategy_config or 'class' not in strategy_config:
                    self.logger.error("策略配置缺少名称或类型")
                    return False
                
                strategy_name = strategy_config['name']
                if strategy_name in strategy_names:
                    self.logger.error(f"重复的策略名称: {strategy_name}")
                    return False
                
                strategy_names.append(strategy_name)
                
                # 验证分配比例
                if 'allocation' in strategy_config:
                    ratio = strategy_config['allocation'].get('ratio', 0.0)
                    total_ratio += ratio
            
            # 如果使用权重分配，检查总比例
            if config.allocation_method == 'weighted' and abs(total_ratio - 1.0) > 0.001:
                self.logger.error(f"权重分配总比例不等于1.0: {total_ratio}")
                return False
            
            # 验证策略组配置
            if config.groups:
                for group_config in config.groups:
                    if 'group_name' not in group_config or 'strategies' not in group_config:
                        self.logger.error("策略组配置缺少必要字段")
                        return False
                    
                    # 检查组内策略是否存在
                    for strategy_name in group_config['strategies']:
                        if strategy_name not in strategy_names:
                            self.logger.error(f"策略组引用了不存在的策略: {strategy_name}")
                            return False
            
            # 验证风险限制配置
            if config.risk_limits:
                for risk_limit in config.risk_limits:
                    required_fields = ['level', 'target', 'max_drawdown']
                    if not all(field in risk_limit for field in required_fields):
                        self.logger.error("风险限制配置缺少必要字段")
                        return False
                    
                    # 验证风险控制级别
                    valid_levels = ['strategy', 'group', 'portfolio', 'global']
                    if risk_limit['level'] not in valid_levels:
                        self.logger.error(f"无效的风险控制级别: {risk_limit['level']}")
                        return False
            
            self.logger.info("配置验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"配置验证异常: {e}")
            return False
    
    def list_configs(self) -> List[str]:
        """列出所有配置文件"""
        try:
            configs = []
            for filepath in self.config_dir.glob("*.json"):
                configs.append(filepath.name)
            for filepath in self.config_dir.glob("*.yaml"):
                configs.append(filepath.name)
            for filepath in self.config_dir.glob("*.yml"):
                configs.append(filepath.name)
            
            return sorted(configs)
            
        except Exception as e:
            self.logger.error(f"列出配置文件失败: {e}")
            return []
    
    def delete_config(self, filename: str) -> bool:
        """删除配置文件"""
        try:
            filepath = self.config_dir / filename
            
            if filepath.exists():
                filepath.unlink()
                self.logger.info(f"配置文件已删除: {filename}")
                return True
            else:
                self.logger.warning(f"配置文件不存在: {filename}")
                return False
                
        except Exception as e:
            self.logger.error(f"删除配置文件失败: {e}")
            return False
    
    def create_sample_configs(self):
        """创建示例配置文件"""
        
        # 1. 简单均衡组合
        simple_config = PortfolioConfig(
            name="简单均衡组合",
            description="两个MA策略的简单组合",
            total_capital=500000.0,
            allocation_method="equal",
            rebalance_frequency="daily",
            risk_tolerance=0.02,
            strategies=[
                {
                    "name": "ma_short_term",
                    "class": "MAStrategy",
                    "config": {
                        "fast_period": 5,
                        "slow_period": 10,
                        "trade_volume": 1,
                        "subscribed_symbols": ["rb2405"]
                    },
                    "allocation": {
                        "ratio": 0.5,
                        "max_position_ratio": 0.9,
                        "risk_budget": 0.03
                    }
                },
                {
                    "name": "ma_long_term",
                    "class": "MAStrategy", 
                    "config": {
                        "fast_period": 20,
                        "slow_period": 50,
                        "trade_volume": 1,
                        "subscribed_symbols": ["i2405"]
                    },
                    "allocation": {
                        "ratio": 0.5,
                        "max_position_ratio": 0.9,
                        "risk_budget": 0.03
                    }
                }
            ]
        )
        
        # 2. 权重分配组合
        weighted_config = PortfolioConfig(
            name="权重分配组合",
            description="基于风险预算的权重分配",
            total_capital=1000000.0,
            allocation_method="weighted",
            rebalance_frequency="weekly",
            risk_tolerance=0.025,
            strategies=[
                {
                    "name": "aggressive_ma",
                    "class": "MAStrategy",
                    "config": {
                        "fast_period": 3,
                        "slow_period": 8,
                        "trade_volume": 2,
                        "subscribed_symbols": ["rb2405", "hc2405"]
                    },
                    "allocation": {
                        "ratio": 0.6,
                        "max_position_ratio": 0.8,
                        "risk_budget": 0.04
                    }
                },
                {
                    "name": "conservative_ma",
                    "class": "MAStrategy",
                    "config": {
                        "fast_period": 20,
                        "slow_period": 60,
                        "trade_volume": 1,
                        "subscribed_symbols": ["i2405"]
                    },
                    "allocation": {
                        "ratio": 0.4,
                        "max_position_ratio": 0.6,
                        "risk_budget": 0.015
                    }
                }
            ],
            groups=[
                {
                    "group_name": "ma_strategies",
                    "strategies": ["aggressive_ma", "conservative_ma"],
                    "max_correlation": 0.6,
                    "max_group_risk": 0.4
                }
            ],
            risk_limits=[
                {
                    "level": "strategy",
                    "target": "aggressive_ma",
                    "max_drawdown": 0.12,
                    "max_daily_loss": 0.04,
                    "max_position_size": 0.8,
                    "var_limit": 0.06
                },
                {
                    "level": "portfolio",
                    "target": "portfolio",
                    "max_drawdown": 0.10,
                    "max_daily_loss": 0.03,
                    "max_position_size": 0.9,
                    "var_limit": 0.04
                }
            ]
        )
        
        # 3. 多品种分散组合
        diversified_config = PortfolioConfig(
            name="多品种分散组合",
            description="跨品种的分散化投资组合",
            total_capital=2000000.0,
            allocation_method="risk_parity",
            rebalance_frequency="monthly",
            risk_tolerance=0.03,
            strategies=[
                {
                    "name": "steel_ma_strategy",
                    "class": "MAStrategy",
                    "config": {
                        "fast_period": 5,
                        "slow_period": 20,
                        "trade_volume": 1,
                        "subscribed_symbols": ["rb2405", "hc2405"]
                    },
                    "allocation": {
                        "risk_budget": 0.25
                    }
                },
                {
                    "name": "iron_ore_ma_strategy",
                    "class": "MAStrategy",
                    "config": {
                        "fast_period": 8,
                        "slow_period": 25,
                        "trade_volume": 1,
                        "subscribed_symbols": ["i2405"]
                    },
                    "allocation": {
                        "risk_budget": 0.25
                    }
                },
                {
                    "name": "coke_ma_strategy",
                    "class": "MAStrategy",
                    "config": {
                        "fast_period": 10,
                        "slow_period": 30,
                        "trade_volume": 1,
                        "subscribed_symbols": ["j2405"]
                    },
                    "allocation": {
                        "risk_budget": 0.25
                    }
                },
                {
                    "name": "coking_coal_ma_strategy",
                    "class": "MAStrategy",
                    "config": {
                        "fast_period": 12,
                        "slow_period": 35,
                        "trade_volume": 1,
                        "subscribed_symbols": ["jm2405"]
                    },
                    "allocation": {
                        "risk_budget": 0.25
                    }
                }
            ],
            groups=[
                {
                    "group_name": "steel_chain",
                    "strategies": ["steel_ma_strategy", "iron_ore_ma_strategy"],
                    "max_correlation": 0.8,
                    "max_group_risk": 0.5
                },
                {
                    "group_name": "coal_chain", 
                    "strategies": ["coke_ma_strategy", "coking_coal_ma_strategy"],
                    "max_correlation": 0.8,
                    "max_group_risk": 0.5
                }
            ]
        )
        
        # 保存示例配置
        configs = [
            (simple_config, "simple_balanced.json"),
            (weighted_config, "weighted_allocation.yaml"),
            (diversified_config, "diversified_portfolio.json")
        ]
        
        for config, filename in configs:
            self.save_config(config, filename)
        
        self.logger.info(f"已创建 {len(configs)} 个示例配置文件")