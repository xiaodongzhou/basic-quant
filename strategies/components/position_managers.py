"""
位置管理器实现
包含入场位、出场位的各种计算算法
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from loguru import logger

from ..three_principle_strategy import PositionManager, TrendDirection, Position

class SupportResistancePositionManager(PositionManager):
    """基于支撑阻力位的位置管理器"""
    
    def __init__(self, lookback_period: int = 20, min_touches: int = 2,
                 entry_buffer: float = 0.001, exit_buffer: float = 0.002, **kwargs):
        self.lookback_period = lookback_period
        self.min_touches = min_touches
        self.entry_buffer = entry_buffer    # 入场缓冲 0.1%
        self.exit_buffer = exit_buffer      # 出场缓冲 0.2%
        
        self.support_levels = []
        self.resistance_levels = []
        
        logger.info(f"支撑阻力位置管理器初始化: 回看{lookback_period}期")
    
    def calculate_entry_position(self, df: pd.DataFrame, direction: TrendDirection, **kwargs) -> Dict[str, float]:
        """计算入场位置"""
        if len(df) < self.lookback_period:
            return {}
        
        try:
            current_price = df['close'].iloc[-1]
            
            # 计算支撑阻力位
            self._calculate_support_resistance_levels(df)
            
            positions = {}
            
            if direction == TrendDirection.UP:
                # 上涨趋势：在支撑位附近入场
                entry_price = self._find_best_support_entry(current_price)
                if entry_price:
                    positions['entry_price'] = entry_price
                    positions['stop_loss'] = self._calculate_support_stop_loss(entry_price)
                    positions['take_profit'] = self._calculate_resistance_target(entry_price)
                    
            elif direction == TrendDirection.DOWN:
                # 下跌趋势：在阻力位附近入场
                entry_price = self._find_best_resistance_entry(current_price)
                if entry_price:
                    positions['entry_price'] = entry_price
                    positions['stop_loss'] = self._calculate_resistance_stop_loss(entry_price)
                    positions['take_profit'] = self._calculate_support_target(entry_price)
            
            return positions
            
        except Exception as e:
            logger.error(f"支撑阻力入场位置计算失败: {e}")
            return {}
    
    def calculate_exit_position(self, df: pd.DataFrame, position: Position, **kwargs) -> Dict[str, float]:
        """计算出场位置"""
        try:
            current_price = df['close'].iloc[-1]
            
            # 更新支撑阻力位
            self._calculate_support_resistance_levels(df)
            
            positions = {}
            
            if position.direction == "LONG":
                # 多头持仓的出场位
                positions['stop_loss'] = self._calculate_support_stop_loss(current_price)
                positions['take_profit'] = self._calculate_resistance_target(current_price)
                
                # 动态调整止损（保护利润）
                if current_price > position.entry_price * 1.02:  # 盈利2%以上
                    trailing_stop = current_price * (1 - self.exit_buffer)
                    positions['trailing_stop'] = max(trailing_stop, position.entry_price)
                    
            elif position.direction == "SHORT":
                # 空头持仓的出场位
                positions['stop_loss'] = self._calculate_resistance_stop_loss(current_price)
                positions['take_profit'] = self._calculate_support_target(current_price)
                
                # 动态调整止损（保护利润）
                if current_price < position.entry_price * 0.98:  # 盈利2%以上
                    trailing_stop = current_price * (1 + self.exit_buffer)
                    positions['trailing_stop'] = min(trailing_stop, position.entry_price)
            
            return positions
            
        except Exception as e:
            logger.error(f"支撑阻力出场位置计算失败: {e}")
            return {}
    
    def _calculate_support_resistance_levels(self, df: pd.DataFrame):
        """计算支撑阻力位"""
        recent_df = df.tail(self.lookback_period)
        
        # 找到局部高低点
        highs = recent_df['high'].values
        lows = recent_df['low'].values
        
        # 计算支撑位（局部最低点）
        support_points = []
        for i in range(1, len(lows) - 1):
            if lows[i] <= lows[i-1] and lows[i] <= lows[i+1]:
                support_points.append(lows[i])
        
        # 计算阻力位（局部最高点）
        resistance_points = []
        for i in range(1, len(highs) - 1):
            if highs[i] >= highs[i-1] and highs[i] >= highs[i+1]:
                resistance_points.append(highs[i])
        
        # 聚类相近的价位
        self.support_levels = self._cluster_levels(support_points)
        self.resistance_levels = self._cluster_levels(resistance_points)
    
    def _cluster_levels(self, price_points: list, cluster_threshold: float = 0.005) -> list:
        """聚类相近的价格水平"""
        if not price_points:
            return []
        
        price_points = sorted(price_points)
        clusters = []
        current_cluster = [price_points[0]]
        
        for price in price_points[1:]:
            if abs(price - current_cluster[-1]) / current_cluster[-1] <= cluster_threshold:
                current_cluster.append(price)
            else:
                # 新集群
                clusters.append(np.mean(current_cluster))
                current_cluster = [price]
        
        # 添加最后一个集群
        if current_cluster:
            clusters.append(np.mean(current_cluster))
        
        return clusters
    
    def _find_best_support_entry(self, current_price: float) -> Optional[float]:
        """找到最佳支撑位入场点"""
        if not self.support_levels:
            return None
        
        # 找到当前价格下方最近的支撑位
        valid_supports = [s for s in self.support_levels if s < current_price]
        if not valid_supports:
            return None
        
        best_support = max(valid_supports)  # 最近的支撑位
        
        # 加上缓冲，避免假突破
        return best_support * (1 + self.entry_buffer)
    
    def _find_best_resistance_entry(self, current_price: float) -> Optional[float]:
        """找到最佳阻力位入场点"""
        if not self.resistance_levels:
            return None
        
        # 找到当前价格上方最近的阻力位
        valid_resistances = [r for r in self.resistance_levels if r > current_price]
        if not valid_resistances:
            return None
        
        best_resistance = min(valid_resistances)  # 最近的阻力位
        
        # 减去缓冲，避免假突破
        return best_resistance * (1 - self.entry_buffer)
    
    def _calculate_support_stop_loss(self, entry_price: float) -> float:
        """计算基于支撑位的止损"""
        if not self.support_levels:
            return entry_price * 0.98  # 默认2%止损
        
        # 找到入场价下方的支撑位
        valid_supports = [s for s in self.support_levels if s < entry_price]
        if not valid_supports:
            return entry_price * 0.98
        
        nearest_support = max(valid_supports)
        return nearest_support * (1 - self.exit_buffer)
    
    def _calculate_resistance_stop_loss(self, entry_price: float) -> float:
        """计算基于阻力位的止损"""
        if not self.resistance_levels:
            return entry_price * 1.02  # 默认2%止损
        
        # 找到入场价上方的阻力位
        valid_resistances = [r for r in self.resistance_levels if r > entry_price]
        if not valid_resistances:
            return entry_price * 1.02
        
        nearest_resistance = min(valid_resistances)
        return nearest_resistance * (1 + self.exit_buffer)
    
    def _calculate_resistance_target(self, entry_price: float) -> Optional[float]:
        """计算基于阻力位的目标价"""
        if not self.resistance_levels:
            return None
        
        # 找到入场价上方的阻力位作为目标
        valid_resistances = [r for r in self.resistance_levels if r > entry_price]
        if not valid_resistances:
            return entry_price * 1.05  # 默认5%目标
        
        return min(valid_resistances) * (1 - self.exit_buffer)
    
    def _calculate_support_target(self, entry_price: float) -> Optional[float]:
        """计算基于支撑位的目标价"""
        if not self.support_levels:
            return None
        
        # 找到入场价下方的支撑位作为目标
        valid_supports = [s for s in self.support_levels if s < entry_price]
        if not valid_supports:
            return entry_price * 0.95  # 默认5%目标
        
        return max(valid_supports) * (1 + self.exit_buffer)

class ATRPositionManager(PositionManager):
    """基于ATR（平均真实范围）的位置管理器"""
    
    def __init__(self, atr_period: int = 14, entry_atr_multiplier: float = 0.5,
                 stop_atr_multiplier: float = 2.0, target_atr_multiplier: float = 3.0, **kwargs):
        self.atr_period = atr_period
        self.entry_atr_multiplier = entry_atr_multiplier   # 入场ATR倍数
        self.stop_atr_multiplier = stop_atr_multiplier     # 止损ATR倍数
        self.target_atr_multiplier = target_atr_multiplier # 目标ATR倍数
        
        logger.info(f"ATR位置管理器初始化: 周期{atr_period}, 入场{entry_atr_multiplier}x, 止损{stop_atr_multiplier}x, 目标{target_atr_multiplier}x")
    
    def calculate_entry_position(self, df: pd.DataFrame, direction: TrendDirection, **kwargs) -> Dict[str, float]:
        """基于ATR计算入场位置"""
        if len(df) < self.atr_period + 5:
            return {}
        
        try:
            current_price = df['close'].iloc[-1]
            # 简化的ATR计算
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            # 计算真实范围 - 修复第一行的问题
            tr1 = high - low
            prev_close = np.roll(close, 1)
            prev_close[0] = close[0]  # 第一行使用自己的收盘价，避免异常大的跳跃
            
            tr2 = np.abs(high - prev_close)
            tr3 = np.abs(low - prev_close)
            
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            atr = pd.Series(tr).rolling(window=self.atr_period).mean().values
            current_atr = atr[-1]
            
            # 确保ATR是有效数值并防止极端值
            if pd.isna(current_atr) or current_atr <= 0:
                current_atr = (high[-1] - low[-1])  # 使用当前bar的范围作为备选
            
            # 防止ATR过大导致极端的位置计算 - 限制ATR不超过价格的10%
            max_atr = current_price * 0.1
            if current_atr > max_atr:
                current_atr = max_atr
            
            positions = {}
            
            if direction == TrendDirection.UP:
                # 上涨趋势：在当前价格下方ATR距离处入场
                entry_price = current_price - (current_atr * self.entry_atr_multiplier)
                positions['entry_price'] = entry_price
                positions['stop_loss'] = entry_price - (current_atr * self.stop_atr_multiplier)
                positions['take_profit'] = entry_price + (current_atr * self.target_atr_multiplier)
                
            elif direction == TrendDirection.DOWN:
                # 下跌趋势：在当前价格上方ATR距离处入场
                entry_price = current_price + (current_atr * self.entry_atr_multiplier)
                positions['entry_price'] = entry_price
                positions['stop_loss'] = entry_price + (current_atr * self.stop_atr_multiplier)
                positions['take_profit'] = entry_price - (current_atr * self.target_atr_multiplier)
            
            # 添加ATR信息
            positions['atr_value'] = current_atr
            positions['atr_percentage'] = current_atr / current_price
            
            return positions
            
        except Exception as e:
            logger.error(f"ATR入场位置计算失败: {e}")
            return {}
    
    def calculate_exit_position(self, df: pd.DataFrame, position: Position, **kwargs) -> Dict[str, float]:
        """基于ATR计算出场位置"""
        try:
            current_price = df['close'].iloc[-1]
            # 简化的ATR计算
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            # 计算真实范围 - 修复第一行的问题
            tr1 = high - low
            prev_close = np.roll(close, 1)
            prev_close[0] = close[0]  # 第一行使用自己的收盘价，避免异常大的跳跃
            
            tr2 = np.abs(high - prev_close)
            tr3 = np.abs(low - prev_close)
            
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            atr = pd.Series(tr).rolling(window=self.atr_period).mean().values
            current_atr = atr[-1]
            
            # 确保ATR是有效数值并防止极端值
            if pd.isna(current_atr) or current_atr <= 0:
                current_atr = (high[-1] - low[-1])  # 使用当前bar的范围作为备选
            
            # 防止ATR过大导致极端的位置计算 - 限制ATR不超过价格的10%
            max_atr = current_price * 0.1
            if current_atr > max_atr:
                current_atr = max_atr
            
            positions = {}
            
            if position.direction == "LONG":
                # 多头持仓
                positions['stop_loss'] = current_price - (current_atr * self.stop_atr_multiplier)
                positions['take_profit'] = current_price + (current_atr * self.target_atr_multiplier)
                
                # 追踪止损
                if current_price > position.entry_price:
                    trailing_stop = current_price - (current_atr * self.stop_atr_multiplier)
                    positions['trailing_stop'] = max(trailing_stop, position.entry_price)
                    
            elif position.direction == "SHORT":
                # 空头持仓
                positions['stop_loss'] = current_price + (current_atr * self.stop_atr_multiplier)
                positions['take_profit'] = current_price - (current_atr * self.target_atr_multiplier)
                
                # 追踪止损
                if current_price < position.entry_price:
                    trailing_stop = current_price + (current_atr * self.stop_atr_multiplier)
                    positions['trailing_stop'] = min(trailing_stop, position.entry_price)
            
            positions['atr_value'] = current_atr
            
            return positions
            
        except Exception as e:
            logger.error(f"ATR出场位置计算失败: {e}")
            return {}

class FibonacciPositionManager(PositionManager):
    """基于斐波那契回撤的位置管理器"""
    
    def __init__(self, swing_period: int = 20, fib_levels: list = None, **kwargs):
        self.swing_period = swing_period
        self.fib_levels = fib_levels or [0.236, 0.382, 0.500, 0.618, 0.786]
        
        logger.info(f"斐波那契位置管理器初始化: 摆动周期{swing_period}")
    
    def calculate_entry_position(self, df: pd.DataFrame, direction: TrendDirection, **kwargs) -> Dict[str, float]:
        """基于斐波那契回撤计算入场位置"""
        if len(df) < self.swing_period + 5:
            return {}
        
        try:
            current_price = df['close'].iloc[-1]
            
            # 找到最近的高低点
            swing_high, swing_low = self._find_recent_swing_points(df)
            
            if swing_high is None or swing_low is None:
                return {}
            
            positions = {}
            
            if direction == TrendDirection.UP:
                # 上涨趋势：在回撤的斐波那契位入场
                fib_retracement_levels = self._calculate_fibonacci_retracements(swing_high, swing_low)
                
                # 选择合适的入场位（通常是38.2%或50%回撤）
                entry_levels = [fib_retracement_levels[0.382], fib_retracement_levels[0.500]]
                entry_price = max([level for level in entry_levels if level < current_price], default=None)
                
                if entry_price:
                    positions['entry_price'] = entry_price
                    positions['stop_loss'] = fib_retracement_levels[0.786]  # 78.6%回撤作为止损
                    positions['take_profit'] = swing_high * 1.01  # 突破前高
                    
            elif direction == TrendDirection.DOWN:
                # 下跌趋势：在反弹的斐波那契位入场
                fib_retracement_levels = self._calculate_fibonacci_retracements(swing_low, swing_high)
                
                # 选择合适的入场位
                entry_levels = [fib_retracement_levels[0.382], fib_retracement_levels[0.500]]
                entry_price = min([level for level in entry_levels if level > current_price], default=None)
                
                if entry_price:
                    positions['entry_price'] = entry_price
                    positions['stop_loss'] = fib_retracement_levels[0.786]  # 78.6%回撤作为止损
                    positions['take_profit'] = swing_low * 0.99  # 突破前低
            
            # 添加斐波那契级别信息
            if swing_high and swing_low:
                positions['fibonacci_levels'] = self._calculate_fibonacci_retracements(swing_high, swing_low)
            
            return positions
            
        except Exception as e:
            logger.error(f"斐波那契入场位置计算失败: {e}")
            return {}
    
    def calculate_exit_position(self, df: pd.DataFrame, position: Position, **kwargs) -> Dict[str, float]:
        """基于斐波那契计算出场位置"""
        try:
            # 找到入场后的新高低点
            swing_high, swing_low = self._find_recent_swing_points(df)
            
            if swing_high is None or swing_low is None:
                return {}
            
            positions = {}
            
            if position.direction == "LONG":
                # 基于新的摆动点计算斐波那契目标
                fib_extensions = self._calculate_fibonacci_extensions(
                    position.entry_price, swing_low, swing_high
                )
                
                positions['take_profit'] = fib_extensions.get(1.618, swing_high * 1.05)
                positions['stop_loss'] = swing_low * 0.99
                
            elif position.direction == "SHORT":
                # 基于新的摆动点计算斐波那契目标
                fib_extensions = self._calculate_fibonacci_extensions(
                    position.entry_price, swing_high, swing_low
                )
                
                positions['take_profit'] = fib_extensions.get(1.618, swing_low * 0.95)
                positions['stop_loss'] = swing_high * 1.01
            
            return positions
            
        except Exception as e:
            logger.error(f"斐波那契出场位置计算失败: {e}")
            return {}
    
    def _find_recent_swing_points(self, df: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
        """找到最近的摆动高低点"""
        recent_df = df.tail(self.swing_period)
        
        # 找到最高点和最低点
        swing_high = recent_df['high'].max()
        swing_low = recent_df['low'].min()
        
        return swing_high, swing_low
    
    def _calculate_fibonacci_retracements(self, high: float, low: float) -> Dict[float, float]:
        """计算斐波那契回撤位"""
        price_range = high - low
        
        retracements = {}
        for level in self.fib_levels:
            retracements[level] = high - (price_range * level)
        
        return retracements
    
    def _calculate_fibonacci_extensions(self, entry: float, swing_low: float, swing_high: float) -> Dict[float, float]:
        """计算斐波那契延伸位"""
        swing_range = abs(swing_high - swing_low)
        
        extension_levels = [1.0, 1.272, 1.414, 1.618, 2.0, 2.618]
        extensions = {}
        
        for level in extension_levels:
            if swing_high > swing_low:  # 上涨
                extensions[level] = swing_high + (swing_range * (level - 1))
            else:  # 下跌
                extensions[level] = swing_low - (swing_range * (level - 1))
        
        return extensions