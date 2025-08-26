"""
改进版EMA趋势跟随策略
基于EMA20/EMA60 + ADX + K线形态的完整策略实现
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from loguru import logger

from .three_principle_strategy import ThreePrincipleStrategy, TrendDirection, Position
from .components.ema_components import EMADirectionAnalyzer, EMAPullbackPositionManager, EMAPatternSignalGenerator


class AdvancedEMATrendStrategy(ThreePrincipleStrategy):
    """改进版EMA趋势跟随策略
    
    核心特点：
    1. EMA20/EMA60双均线系统 + ADX趋势强度过滤
    2. 精确的回踩入场条件
    3. K线形态确认信号
    4. 阶段性止盈和动态止损管理
    """
    
    def __init__(self, name: str = "改进版EMA趋势策略", symbol: str = "", parameters: Dict[str, Any] = None):
        """初始化策略"""
        default_params = {
            # EMA参数
            'ema_short': 20,          # EMA20周期
            'ema_long': 60,           # EMA60周期
            
            # ADX参数
            'adx_period': 14,         # ADX计算周期
            'adx_threshold': 25.0,    # ADX阈值，大于此值才认为有趋势
            
            # 回踩参数
            'lookback_candles': 4,    # 历史位置验证K线数
            'pullback_threshold': 0.5, # 回踩阈值（相对于5根K线平均振幅）
            
            # 风险管理
            'risk_reward_ratio': 2.0,  # 风险收益比
            'position_size': 0.02,     # 每次交易的仓位大小（2%资金）
            'max_risk_per_trade': 0.01, # 每笔交易最大风险（1%资金）
            
            # 信号参数
            'min_confidence': 0.7,     # 最小信号置信度
            'body_threshold': 1.5,     # K线实体阈值倍数
            
            # 交易时段
            'trading_hours': None,     # 交易时段限制，None表示24小时
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name, symbol, default_params)
        
        # 创建策略组件
        self._create_strategy_components()
        
        # 风险管理状态
        self.partial_profit_taken = False  # 是否已获得部分利润
        self.break_even_activated = False  # 是否已激活保本止损
        
        logger.info(f"改进版EMA趋势策略 {name} 初始化完成")
    
    def _create_strategy_components(self):
        """创建策略的三原则组件"""
        # 方向分析器：EMA + ADX
        direction_analyzer = EMADirectionAnalyzer(
            ema_short=self.parameters['ema_short'],
            ema_long=self.parameters['ema_long'],
            adx_period=self.parameters['adx_period'],
            adx_threshold=self.parameters['adx_threshold']
        )
        
        # 位置管理器：EMA回踩
        position_manager = EMAPullbackPositionManager(
            lookback_candles=self.parameters['lookback_candles'],
            pullback_threshold=self.parameters['pullback_threshold'],
            risk_reward_ratio=self.parameters['risk_reward_ratio']
        )
        
        # 信号生成器：K线形态
        signal_generator = EMAPatternSignalGenerator(
            min_confidence=self.parameters['min_confidence'],
            body_threshold=self.parameters['body_threshold']
        )
        
        # 设置组件
        self.set_components(direction_analyzer, position_manager, signal_generator)
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, 
                              account_balance: float) -> float:
        """计算仓位大小（基于固定风险百分比）"""
        try:
            # 计算每股风险
            risk_per_share = abs(entry_price - stop_loss)
            if risk_per_share <= 0:
                return 0.0
            
            # 计算最大风险金额
            max_risk_amount = account_balance * self.parameters['max_risk_per_trade']
            
            # 计算基于风险的仓位大小
            position_size = max_risk_amount / risk_per_share
            
            # 限制最大仓位不超过账户资金的设定百分比
            max_position_value = account_balance * self.parameters['position_size']
            max_shares = max_position_value / entry_price
            
            # 取较小值
            final_position_size = min(position_size, max_shares)
            
            logger.debug(f"仓位计算: 入场价={entry_price:.2f}, 止损价={stop_loss:.2f}, "
                        f"风险={risk_per_share:.2f}, 仓位大小={final_position_size:.4f}")
            
            return final_position_size
            
        except Exception as e:
            logger.error(f"仓位计算失败: {e}")
            return 0.0
    
    def on_bar(self, df: pd.DataFrame):
        """K线数据更新处理"""
        try:
            # 调用基类的on_bar处理
            super().on_bar(df)
            
            # 获取当前状态信息
            current_bar = df.iloc[-1]
            current_price = current_bar['close']
            
            # 检查阶段性止盈条件
            if self.current_position and not self.partial_profit_taken:
                self._check_partial_profit_taking(df)
            
            # 记录关键指标
            if hasattr(self.direction_analyzer, 'get_ema_values'):
                ema_values = self.direction_analyzer.get_ema_values(df)
                logger.debug(f"EMA状态: EMA20={ema_values.get('ema20', 0):.2f}, "
                           f"EMA60={ema_values.get('ema60', 0):.2f}, ADX={ema_values.get('adx', 0):.2f}")
            
        except Exception as e:
            logger.error(f"K线处理失败: {e}")
    
    def _check_partial_profit_taking(self, df: pd.DataFrame):
        """检查部分止盈条件"""
        if not self.current_position:
            return
        
        try:
            current_price = df['close'].iloc[-1]
            entry_price = self.current_position.entry_price
            
            # 获取初始风险
            initial_risk = 0
            if hasattr(self.current_position, 'stop_loss') and self.current_position.stop_loss:
                if self.current_position.direction == "LONG":
                    initial_risk = entry_price - self.current_position.stop_loss
                else:
                    initial_risk = self.current_position.stop_loss - entry_price
            
            if initial_risk <= 0:
                return
            
            # 计算当前利润
            if self.current_position.direction == "LONG":
                current_profit = current_price - entry_price
            else:
                current_profit = entry_price - current_price
            
            # 检查是否达到2倍风险收益比
            target_profit = initial_risk * self.parameters['risk_reward_ratio']
            
            if current_profit >= target_profit and not self.partial_profit_taken:
                # 执行部分止盈
                self._execute_partial_profit(current_price, initial_risk)
                
                # 激活保本止损
                self._activate_break_even_stop()
                
        except Exception as e:
            logger.error(f"部分止盈检查失败: {e}")
    
    def _execute_partial_profit(self, current_price: float, initial_risk: float):
        """执行部分止盈"""
        try:
            # 平掉一半仓位
            partial_size = self.current_position.size * 0.5
            
            if self.current_position.direction == "LONG":
                pnl = (current_price - self.current_position.entry_price) * partial_size
            else:
                pnl = (self.current_position.entry_price - current_price) * partial_size
            
            # 更新仓位
            self.current_position.size -= partial_size
            self.total_pnl += pnl
            self.closed_pnl += pnl
            
            # 记录交易
            self.trade_count += 1
            if pnl > 0:
                self.winning_trades += 1
            
            self.partial_profit_taken = True
            
            logger.info(f"执行部分止盈: 平仓{partial_size:.4f}股，PNL: ${pnl:.2f}")
            
        except Exception as e:
            logger.error(f"部分止盈执行失败: {e}")
    
    def _activate_break_even_stop(self):
        """激活保本止损"""
        try:
            if self.current_position:
                # 将止损设置为入场价（保本）
                self.current_position.stop_loss = self.current_position.entry_price
                self.break_even_activated = True
                
                logger.info(f"激活保本止损: 止损价设为入场价 ${self.current_position.entry_price:.2f}")
                
        except Exception as e:
            logger.error(f"保本止损激活失败: {e}")
    
    def _reset_trade_state(self):
        """重置交易状态"""
        self.partial_profit_taken = False
        self.break_even_activated = False
    
    def _execute_entry_long(self, size: float, price: float):
        """执行做多入场（重写以添加状态重置）"""
        super()._execute_entry_long(size, price)
        self._reset_trade_state()
    
    def _execute_entry_short(self, size: float, price: float):
        """执行做空入场（重写以添加状态重置）"""
        super()._execute_entry_short(size, price)
        self._reset_trade_state()
    
    def _execute_exit(self, price: float, reason: str = ""):
        """执行出场（重写以添加状态重置）"""
        super()._execute_exit(price, reason)
        self._reset_trade_state()
    
    def get_strategy_state(self) -> Dict[str, Any]:
        """获取策略状态信息"""
        base_state = super().get_strategy_state()
        
        # 添加EMA策略特定状态
        ema_state = {
            'partial_profit_taken': self.partial_profit_taken,
            'break_even_activated': self.break_even_activated,
            'ema_short_period': self.parameters['ema_short'],
            'ema_long_period': self.parameters['ema_long'],
            'adx_threshold': self.parameters['adx_threshold'],
            'risk_reward_ratio': self.parameters['risk_reward_ratio']
        }
        
        base_state.update(ema_state)
        return base_state
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """获取策略性能指标"""
        base_metrics = super().get_performance_metrics()
        
        # 添加EMA策略特定指标
        try:
            if self.trade_count > 0:
                # 部分止盈率
                partial_profit_rate = 1.0 if self.partial_profit_taken else 0.0
                
                # 保本激活率
                break_even_rate = 1.0 if self.break_even_activated else 0.0
                
                ema_metrics = {
                    'partial_profit_rate': partial_profit_rate,
                    'break_even_activation_rate': break_even_rate,
                    'avg_risk_per_trade': abs(self.closed_pnl / self.trade_count) if self.trade_count > 0 else 0.0
                }
                
                base_metrics.update(ema_metrics)
                
        except Exception as e:
            logger.error(f"EMA性能指标计算失败: {e}")
        
        return base_metrics