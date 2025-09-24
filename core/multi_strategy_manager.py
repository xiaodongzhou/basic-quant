#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi Strategy Manager - 多策略管理器

Milestone 2.4 核心模块 - 实现多策略组合管理功能
- 策略资金分配和隔离
- 统一风险控制
- 绩效监控和报告
- 动态策略管理
"""

import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import copy

from .strategy_engine import StrategyEngine, StrategyBase, StrategyStatus
from .data_types import BarData, TickData, TradeData, OrderData, PositionData
from .trading_engine import TradingEngine
from .market_data_manager import MarketDataManager


class StrategyAllocationMethod(Enum):
    """策略资金分配方式"""
    EQUAL = "equal"              # 等额分配
    WEIGHTED = "weighted"        # 权重分配
    RISK_PARITY = "risk_parity"  # 风险平价
    DYNAMIC = "dynamic"          # 动态分配


class RiskControlLevel(Enum):
    """风险控制级别"""
    STRATEGY = "strategy"        # 单策略级别
    GROUP = "group"             # 策略组级别  
    PORTFOLIO = "portfolio"     # 组合级别
    GLOBAL = "global"           # 全局级别


@dataclass
class StrategyAllocation:
    """策略资金分配配置"""
    strategy_name: str
    allocation_amount: float    # 分配金额
    allocation_ratio: float     # 分配比例
    max_position_ratio: float   # 最大仓位比例
    risk_budget: float          # 风险预算
    priority: int = 1           # 优先级
    active: bool = True         # 是否激活


@dataclass
class StrategyGroup:
    """策略组配置"""
    group_name: str
    strategies: List[str] = field(default_factory=list)
    max_correlation: float = 0.7    # 最大相关性
    max_group_risk: float = 0.3     # 组最大风险
    rebalance_frequency: str = "daily"  # 再平衡频率
    active: bool = True


@dataclass
class RiskLimit:
    """风险限制配置"""
    level: RiskControlLevel
    target: str                 # 目标(策略名/组名等)
    max_drawdown: float         # 最大回撤
    max_daily_loss: float       # 最大日损失
    max_position_size: float    # 最大持仓规模
    var_limit: float           # VaR限制
    active: bool = True


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    daily_pnl: List[float] = field(default_factory=list)
    monthly_returns: List[float] = field(default_factory=list)
    
    # 风险指标
    volatility: float = 0.0
    var_95: float = 0.0
    var_99: float = 0.0
    beta: float = 0.0
    
    # 时间戳
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    last_update: Optional[datetime] = None


@dataclass
class StrategyRunStatus:
    """策略运行状态"""
    strategy_name: str
    status: str
    allocated_capital: float
    used_capital: float
    current_positions: Dict[str, float]
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    risk_utilization: float     # 风险利用率
    last_signal_time: Optional[datetime] = None
    error_count: int = 0
    
    def capital_utilization(self) -> float:
        """资金利用率"""
        return self.used_capital / self.allocated_capital if self.allocated_capital > 0 else 0.0


class MultiStrategyManager:
    """多策略管理器"""
    
    def __init__(self, 
                 trading_engine: TradingEngine,
                 market_data_manager: MarketDataManager,
                 config: dict):
        
        self.trading_engine = trading_engine
        self.market_data_manager = market_data_manager
        self.config = config
        
        # 策略管理
        self.strategy_engines: Dict[str, StrategyEngine] = {}
        self.strategy_instances: Dict[str, StrategyBase] = {}
        self.strategy_allocations: Dict[str, StrategyAllocation] = {}
        self.strategy_groups: Dict[str, StrategyGroup] = {}
        
        # 风险控制
        self.risk_limits: Dict[str, RiskLimit] = {}
        self.risk_monitors: Dict[str, Any] = {}
        
        # 绩效监控
        self.performance_metrics: Dict[str, PerformanceMetrics] = {}
        self.portfolio_metrics: PerformanceMetrics = PerformanceMetrics()
        
        # 状态管理
        self.strategy_statuses: Dict[str, StrategyRunStatus] = {}
        self.manager_status = "inactive"
        self.start_time: Optional[datetime] = None
        
        # 资金管理
        self.total_capital = config.get('total_capital', 1000000.0)
        self.available_capital = self.total_capital
        self.allocation_method = StrategyAllocationMethod(config.get('allocation_method', 'equal'))
        
        # 线程管理
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="MultiStrategy")
        self.monitor_thread: Optional[threading.Thread] = None
        self.running = False
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 日志
        self.logger = logging.getLogger("MultiStrategyManager")
        self.logger.info("多策略管理器初始化完成")
    
    def add_strategy(self, 
                    strategy_name: str, 
                    strategy_class: type, 
                    strategy_config: dict,
                    allocation_config: Optional[dict] = None) -> bool:
        """添加策略到管理器"""
        try:
            with self._lock:
                self.logger.info(f"添加策略: {strategy_name}")
                
                # 创建策略引擎
                strategy_engine = StrategyEngine(
                    trading_engine=self.trading_engine,
                    market_data_manager=self.market_data_manager
                )
                
                # 创建策略实例
                strategy_instance = strategy_class(
                    strategy_name=strategy_name,
                    config=strategy_config,
                    trading_engine=self.trading_engine
                )
                
                # 注册策略到引擎
                strategy_engine.load_strategy(strategy_instance, strategy_config)
                
                # 保存引用
                self.strategy_engines[strategy_name] = strategy_engine
                self.strategy_instances[strategy_name] = strategy_instance
                
                # 配置资金分配
                if allocation_config:
                    allocation = StrategyAllocation(
                        strategy_name=strategy_name,
                        allocation_amount=allocation_config.get('amount', 0.0),
                        allocation_ratio=allocation_config.get('ratio', 0.0),
                        max_position_ratio=allocation_config.get('max_position_ratio', 0.8),
                        risk_budget=allocation_config.get('risk_budget', 0.02),
                        priority=allocation_config.get('priority', 1)
                    )
                    self.strategy_allocations[strategy_name] = allocation
                
                # 初始化状态
                self.strategy_statuses[strategy_name] = StrategyRunStatus(
                    strategy_name=strategy_name,
                    status="inactive",
                    allocated_capital=0.0,
                    used_capital=0.0,
                    current_positions={},
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    daily_pnl=0.0,
                    risk_utilization=0.0
                )
                
                # 初始化绩效指标
                self.performance_metrics[strategy_name] = PerformanceMetrics()
                
                self.logger.info(f"策略 {strategy_name} 添加成功")
                return True
                
        except Exception as e:
            self.logger.error(f"添加策略 {strategy_name} 失败: {e}")
            return False
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """移除策略"""
        try:
            with self._lock:
                if strategy_name not in self.strategy_engines:
                    self.logger.warning(f"策略 {strategy_name} 不存在")
                    return False
                
                # 停止策略
                self.stop_strategy(strategy_name)
                
                # 清理资源
                del self.strategy_engines[strategy_name]
                del self.strategy_instances[strategy_name]
                
                if strategy_name in self.strategy_allocations:
                    del self.strategy_allocations[strategy_name]
                if strategy_name in self.strategy_statuses:
                    del self.strategy_statuses[strategy_name]
                if strategy_name in self.performance_metrics:
                    del self.performance_metrics[strategy_name]
                
                self.logger.info(f"策略 {strategy_name} 移除成功")
                return True
                
        except Exception as e:
            self.logger.error(f"移除策略 {strategy_name} 失败: {e}")
            return False
    
    def create_strategy_group(self, group_config: dict) -> bool:
        """创建策略组"""
        try:
            group_name = group_config['group_name']
            strategies = group_config.get('strategies', [])
            
            # 验证策略是否存在
            for strategy_name in strategies:
                if strategy_name not in self.strategy_engines:
                    raise ValueError(f"策略 {strategy_name} 不存在")
            
            group = StrategyGroup(
                group_name=group_name,
                strategies=strategies,
                max_correlation=group_config.get('max_correlation', 0.7),
                max_group_risk=group_config.get('max_group_risk', 0.3),
                rebalance_frequency=group_config.get('rebalance_frequency', 'daily')
            )
            
            self.strategy_groups[group_name] = group
            self.logger.info(f"策略组 {group_name} 创建成功，包含策略: {strategies}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建策略组失败: {e}")
            return False
    
    def allocate_capital(self) -> bool:
        """分配资金给各策略"""
        try:
            with self._lock:
                if not self.strategy_allocations:
                    # 如果没有配置分配，使用等额分配
                    self._equal_allocation()
                else:
                    # 使用配置的分配方式
                    if self.allocation_method == StrategyAllocationMethod.EQUAL:
                        self._equal_allocation()
                    elif self.allocation_method == StrategyAllocationMethod.WEIGHTED:
                        self._weighted_allocation()
                    elif self.allocation_method == StrategyAllocationMethod.RISK_PARITY:
                        self._risk_parity_allocation()
                    elif self.allocation_method == StrategyAllocationMethod.DYNAMIC:
                        self._dynamic_allocation()
                
                # 更新策略状态中的分配资金
                for strategy_name, allocation in self.strategy_allocations.items():
                    if strategy_name in self.strategy_statuses:
                        self.strategy_statuses[strategy_name].allocated_capital = allocation.allocation_amount
                
                self.logger.info(f"资金分配完成，分配方式: {self.allocation_method.value}")
                return True
                
        except Exception as e:
            self.logger.error(f"资金分配失败: {e}")
            return False
    
    def _equal_allocation(self):
        """等额分配资金"""
        strategy_count = len(self.strategy_engines)
        if strategy_count == 0:
            return
        
        amount_per_strategy = self.total_capital / strategy_count
        
        for strategy_name in self.strategy_engines:
            if strategy_name not in self.strategy_allocations:
                self.strategy_allocations[strategy_name] = StrategyAllocation(
                    strategy_name=strategy_name,
                    allocation_amount=amount_per_strategy,
                    allocation_ratio=1.0 / strategy_count,
                    max_position_ratio=0.8,
                    risk_budget=0.02
                )
            else:
                self.strategy_allocations[strategy_name].allocation_amount = amount_per_strategy
                self.strategy_allocations[strategy_name].allocation_ratio = 1.0 / strategy_count
    
    def _weighted_allocation(self):
        """权重分配资金"""
        total_weight = sum(alloc.allocation_ratio for alloc in self.strategy_allocations.values())
        
        for allocation in self.strategy_allocations.values():
            normalized_weight = allocation.allocation_ratio / total_weight
            allocation.allocation_amount = self.total_capital * normalized_weight
    
    def _risk_parity_allocation(self):
        """风险平价分配资金"""
        # 简化实现：基于风险预算分配
        total_risk_budget = sum(alloc.risk_budget for alloc in self.strategy_allocations.values())
        
        for allocation in self.strategy_allocations.values():
            risk_weight = allocation.risk_budget / total_risk_budget
            allocation.allocation_amount = self.total_capital * risk_weight
    
    def _dynamic_allocation(self):
        """动态分配资金"""
        # 基于历史绩效和风险动态调整分配
        # 简化实现：基于夏普比率调整
        
        sharpe_ratios = {}
        for strategy_name, metrics in self.performance_metrics.items():
            if metrics.volatility > 0:
                sharpe_ratios[strategy_name] = metrics.sharpe_ratio
            else:
                sharpe_ratios[strategy_name] = 0.0
        
        total_sharpe = sum(max(0, s) for s in sharpe_ratios.values())
        if total_sharpe == 0:
            self._equal_allocation()
            return
        
        for strategy_name, allocation in self.strategy_allocations.items():
            weight = max(0, sharpe_ratios.get(strategy_name, 0)) / total_sharpe
            allocation.allocation_amount = self.total_capital * weight
    
    def start_all_strategies(self) -> bool:
        """启动所有策略"""
        try:
            self.logger.info("启动所有策略...")
            
            # 分配资金
            self.allocate_capital()
            
            # 启动策略
            success_count = 0
            for strategy_name in self.strategy_engines:
                if self.start_strategy(strategy_name):
                    success_count += 1
            
            # 启动监控线程
            if success_count > 0:
                self.running = True
                self.manager_status = "running"
                self.start_time = datetime.now()
                
                self.monitor_thread = threading.Thread(
                    target=self._monitoring_loop,
                    name="StrategyMonitor",
                    daemon=True
                )
                self.monitor_thread.start()
            
            self.logger.info(f"策略启动完成，成功启动 {success_count}/{len(self.strategy_engines)} 个策略")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"启动所有策略失败: {e}")
            return False
    
    def start_strategy(self, strategy_name: str) -> bool:
        """启动单个策略"""
        try:
            if strategy_name not in self.strategy_engines:
                self.logger.error(f"策略 {strategy_name} 不存在")
                return False
            
            # 检查资金分配
            if strategy_name not in self.strategy_allocations:
                self.logger.error(f"策略 {strategy_name} 未分配资金")
                return False
            
            # 启动策略引擎
            strategy_engine = self.strategy_engines[strategy_name]
            if strategy_engine.start_strategy(strategy_name):
                # 更新状态
                self.strategy_statuses[strategy_name].status = "running"
                
                self.logger.info(f"策略 {strategy_name} 启动成功")
                return True
            else:
                self.logger.error(f"策略 {strategy_name} 启动失败")
                return False
                
        except Exception as e:
            self.logger.error(f"启动策略 {strategy_name} 失败: {e}")
            return False
    
    def stop_strategy(self, strategy_name: str) -> bool:
        """停止单个策略"""
        try:
            if strategy_name not in self.strategy_engines:
                self.logger.error(f"策略 {strategy_name} 不存在")
                return False
            
            # 停止策略引擎
            strategy_engine = self.strategy_engines[strategy_name]
            if strategy_engine.stop_strategy(strategy_name):
                # 更新状态
                self.strategy_statuses[strategy_name].status = "stopped"
                
                self.logger.info(f"策略 {strategy_name} 停止成功")
                return True
            else:
                self.logger.error(f"策略 {strategy_name} 停止失败")
                return False
                
        except Exception as e:
            self.logger.error(f"停止策略 {strategy_name} 失败: {e}")
            return False
    
    def stop_all_strategies(self) -> bool:
        """停止所有策略"""
        try:
            self.logger.info("停止所有策略...")
            
            # 停止监控
            self.running = False
            
            # 停止策略
            success_count = 0
            for strategy_name in self.strategy_engines:
                if self.stop_strategy(strategy_name):
                    success_count += 1
            
            # 等待监控线程结束
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5.0)
            
            self.manager_status = "stopped"
            
            self.logger.info(f"策略停止完成，成功停止 {success_count}/{len(self.strategy_engines)} 个策略")
            return success_count == len(self.strategy_engines)
            
        except Exception as e:
            self.logger.error(f"停止所有策略失败: {e}")
            return False
    
    def _monitoring_loop(self):
        """监控循环"""
        self.logger.info("策略监控线程启动")
        
        while self.running:
            try:
                # 更新策略状态
                self._update_strategy_statuses()
                
                # 检查风险限制
                self._check_risk_limits()
                
                # 更新绩效指标
                self._update_performance_metrics()
                
                # 检查策略健康状态
                self._check_strategy_health()
                
                # 等待下次检查
                time.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                time.sleep(5.0)
        
        self.logger.info("策略监控线程停止")
    
    def _update_strategy_statuses(self):
        """更新策略状态"""
        with self._lock:
            for strategy_name, status in self.strategy_statuses.items():
                try:
                    # 获取策略实例
                    strategy = self.strategy_instances.get(strategy_name)
                    if not strategy:
                        continue
                    
                    # 更新持仓信息
                    status.current_positions = {}
                    status.unrealized_pnl = 0.0
                    
                    # 从策略获取持仓信息
                    if hasattr(strategy, 'positions'):
                        for symbol, position in strategy.positions.items():
                            if hasattr(position, 'volume') and position.volume > 0:
                                status.current_positions[symbol] = position.volume
                                if hasattr(position, 'unrealized_pnl'):
                                    status.unrealized_pnl += position.unrealized_pnl
                    
                    # 计算已用资金
                    status.used_capital = abs(status.unrealized_pnl)  # 简化计算
                    
                    # 计算风险利用率
                    if status.allocated_capital > 0:
                        status.risk_utilization = status.used_capital / status.allocated_capital
                    
                except Exception as e:
                    self.logger.error(f"更新策略 {strategy_name} 状态失败: {e}")
    
    def _check_risk_limits(self):
        """检查风险限制"""
        for limit_name, risk_limit in self.risk_limits.items():
            try:
                if not risk_limit.active:
                    continue
                
                # 检查不同级别的风险限制
                if risk_limit.level == RiskControlLevel.STRATEGY:
                    self._check_strategy_risk_limit(risk_limit)
                elif risk_limit.level == RiskControlLevel.GROUP:
                    self._check_group_risk_limit(risk_limit)
                elif risk_limit.level == RiskControlLevel.PORTFOLIO:
                    self._check_portfolio_risk_limit(risk_limit)
                
            except Exception as e:
                self.logger.error(f"检查风险限制 {limit_name} 失败: {e}")
    
    def _check_strategy_risk_limit(self, risk_limit: RiskLimit):
        """检查策略级风险限制"""
        strategy_name = risk_limit.target
        status = self.strategy_statuses.get(strategy_name)
        
        if not status:
            return
        
        # 检查最大回撤
        metrics = self.performance_metrics.get(strategy_name)
        if metrics and metrics.max_drawdown > risk_limit.max_drawdown:
            self.logger.warning(f"策略 {strategy_name} 超过最大回撤限制: {metrics.max_drawdown:.2%} > {risk_limit.max_drawdown:.2%}")
    
    def _check_group_risk_limit(self, risk_limit: RiskLimit):
        """检查策略组风险限制"""
        pass
    
    def _check_portfolio_risk_limit(self, risk_limit: RiskLimit):
        """检查组合级风险限制"""
        pass
    
    def _update_performance_metrics(self):
        """更新绩效指标"""
        for strategy_name, metrics in self.performance_metrics.items():
            try:
                # 获取策略状态
                status = self.strategy_statuses.get(strategy_name)
                if not status:
                    continue
                
                # 更新基本指标
                metrics.last_update = datetime.now()
                
                # 从策略获取更多绩效数据
                strategy = self.strategy_instances.get(strategy_name)
                if strategy and hasattr(strategy, 'total_trades'):
                    metrics.total_trades = strategy.total_trades
                
            except Exception as e:
                self.logger.error(f"更新策略 {strategy_name} 绩效指标失败: {e}")
    
    def _check_strategy_health(self):
        """检查策略健康状态"""
        for strategy_name, status in self.strategy_statuses.items():
            try:
                # 检查策略是否响应
                strategy_engine = self.strategy_engines.get(strategy_name)
                if not strategy_engine:
                    continue
                
                # 检查最后信号时间
                if status.last_signal_time:
                    time_since_signal = datetime.now() - status.last_signal_time
                    if time_since_signal > timedelta(minutes=30):  # 30分钟无信号
                        self.logger.warning(f"策略 {strategy_name} 长时间无信号")
                
            except Exception as e:
                self.logger.error(f"检查策略 {strategy_name} 健康状态失败: {e}")
    
    def get_portfolio_status(self) -> dict:
        """获取组合状态"""
        with self._lock:
            total_allocated = sum(s.allocated_capital for s in self.strategy_statuses.values())
            total_used = sum(s.used_capital for s in self.strategy_statuses.values())
            total_pnl = sum(s.unrealized_pnl + s.realized_pnl for s in self.strategy_statuses.values())
            
            return {
                'manager_status': self.manager_status,
                'total_capital': self.total_capital,
                'allocated_capital': total_allocated,
                'available_capital': self.total_capital - total_allocated,
                'used_capital': total_used,
                'total_pnl': total_pnl,
                'strategy_count': len(self.strategy_engines),
                'running_strategies': len([s for s in self.strategy_statuses.values() 
                                         if s.status == "running"]),
                'start_time': self.start_time,
                'uptime': (datetime.now() - self.start_time) if self.start_time else None
            }
    
    def get_strategy_summary(self) -> Dict[str, dict]:
        """获取策略汇总信息"""
        with self._lock:
            summary = {}
            
            for strategy_name in self.strategy_engines:
                status = self.strategy_statuses.get(strategy_name)
                allocation = self.strategy_allocations.get(strategy_name)
                metrics = self.performance_metrics.get(strategy_name)
                
                summary[strategy_name] = {
                    'status': status.status if status else 'unknown',
                    'allocated_capital': allocation.allocation_amount if allocation else 0.0,
                    'used_capital': status.used_capital if status else 0.0,
                    'unrealized_pnl': status.unrealized_pnl if status else 0.0,
                    'capital_utilization': status.capital_utilization() if status else 0.0,
                    'risk_utilization': status.risk_utilization if status else 0.0,
                    'total_trades': metrics.total_trades if metrics else 0,
                    'sharpe_ratio': metrics.sharpe_ratio if metrics else 0.0,
                    'max_drawdown': metrics.max_drawdown if metrics else 0.0
                }
            
            return summary
    
    def add_risk_limit(self, limit_name: str, risk_limit: RiskLimit) -> bool:
        """添加风险限制"""
        try:
            self.risk_limits[limit_name] = risk_limit
            self.logger.info(f"风险限制 {limit_name} 添加成功")
            return True
        except Exception as e:
            self.logger.error(f"添加风险限制 {limit_name} 失败: {e}")
            return False
    
    def export_performance_report(self, filepath: str) -> bool:
        """导出绩效报告"""
        try:
            report_data = {
                'portfolio_status': self.get_portfolio_status(),
                'strategy_summary': self.get_strategy_summary(),
                'performance_metrics': {
                    name: {
                        'total_return': metrics.total_return,
                        'sharpe_ratio': metrics.sharpe_ratio,
                        'max_drawdown': metrics.max_drawdown,
                        'total_trades': metrics.total_trades,
                        'win_rate': metrics.win_rate
                    }
                    for name, metrics in self.performance_metrics.items()
                },
                'generated_time': datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"绩效报告已导出到: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出绩效报告失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        try:
            # 停止所有策略
            self.stop_all_strategies()
            
            # 关闭线程池
            self.executor.shutdown(wait=True)
            
            self.logger.info("多策略管理器资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")