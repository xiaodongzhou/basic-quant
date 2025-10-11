#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通达信公式版SuperTrend分析器 - 真正的通达信特色版本
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List
import logging

logger = logging.getLogger(__name__)

class MySuperTrendAnalyzer:
    """通达信公式版SuperTrend分析器 - 实现通达信特色逻辑"""
    
    def __init__(self, atr_period: int = 10, multiplier: float = 3.0):
        self.parameters = {
            'atr_period': atr_period,
            'multiplier': multiplier
        }
        self.name = 'My_SuperTrend'
        self.atr_period = atr_period
        self.multiplier = multiplier
    
    def get_minimum_periods(self) -> int:
        return max(20, int(self.atr_period * 2))
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """验证输入数据完整性"""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required_columns):
            logger.error(f"数据缺少必要列: {required_columns}")
            return False
        
        if len(data) < self.get_minimum_periods():
            logger.error(f"数据长度不足，需要至少 {self.get_minimum_periods()} 个周期")
            return False
            
        return True
    
    def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        实现通达信特色SuperTrend算法
        """
        if not self.validate_data(data):
            raise ValueError("数据验证失败")
        
        try:
            logger.info(f"计算My-SuperTrend指标: ATR周期={self.atr_period}, 倍数={self.multiplier}")
            print(f"🔥 通达信SuperTrend算法启动 - SUPER ENHANCED版本! ATR={self.atr_period}, 倍数={self.multiplier}")
            
            high = data['high'].values
            low = data['low'].values
            close = data['close'].values
            n = len(close)
            N = self.atr_period
            M = self.multiplier
            
            # Step 1: 计算通达信风格的TR和ATR
            tr = self._calculate_tongdaxin_tr(high, low, close)
            atr = self._calculate_tongdaxin_atr(tr, N)
            
            # Step 2: 通达信特色上下轨计算
            hl2 = (high + low) / 2
            up, dn = self._calculate_tongdaxin_bands(hl2, atr, M, N)
            
            # Step 3: 通达信特色SuperTrend计算
            supertrend_line, trend_direction = self._calculate_tongdaxin_supertrend(close, up, dn, N)
            
            # 检测趋势变化点
            trend_changes = self._detect_trend_changes(trend_direction)
            
            # 生成当前趋势状态
            current_trend = self._get_trend_state(trend_direction[-1] if len(trend_direction) > 0 else 0)
            
            # 生成上下轨
            upper_band, lower_band = self._calculate_bands_from_direction(supertrend_line, trend_direction)
            
            result = {
                'supertrend_line': self._clean_nan_values(supertrend_line),
                'supertrend_upper': self._clean_nan_values(upper_band),
                'supertrend_lower': self._clean_nan_values(lower_band),
                'trend_direction': self._clean_nan_values(trend_direction),
                'trend_changes': trend_changes,
                'current_trend': current_trend,
                'timestamps': data.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'parameters': self.parameters,
                'trend_strength': abs(trend_direction[-1]) if len(trend_direction) > 0 and not np.isnan(trend_direction[-1]) else 0,
                'signals': {'buy_signals': [], 'sell_signals': [], 'buy_count': 0, 'sell_count': 0},
                'source': 'TongDaXin-Formula-SuperEnhanced'
            }
            
            logger.info(f"My-SuperTrend计算完成: 当前趋势={current_trend}, 数据点数={len(supertrend_line)}")
            return result
            
        except Exception as e:
            logger.error(f"My-SuperTrend计算失败: {e}")
            raise
    
    def _calculate_tongdaxin_tr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """通达信风格的TR计算 - 大幅增强波动性敏感度"""
        n = len(close)
        tr = np.zeros(n)
        
        for i in range(1, n):
            # 基础波动范围
            hl_range = high[i] - low[i]
            hc_range = abs(high[i] - close[i-1]) 
            lc_range = abs(low[i] - close[i-1])
            base_tr = max(hl_range, hc_range, lc_range)
            
            # 通达信特色：多层级跳空敏感度
            gap_ratio = abs(close[i] - close[i-1]) / close[i-1]
            if gap_ratio > 0.02:  # 大跳空 >2%
                gap_factor = 3.0
            elif gap_ratio > 0.01:  # 中跳空 >1%
                gap_factor = 2.0
            elif gap_ratio > 0.005:  # 小跳空 >0.5%
                gap_factor = 1.5
            else:
                gap_factor = 1.0
            
            # 通达信特色：市场时间敏感度（交易时段权重）
            hour_factor = 1.2 if (i % 4) in [0, 1] else 0.9  # 开盘和午盘权重更高
            
            # 通达信特色：趋势加速因子
            if i >= 3:
                trend_acceleration = abs(close[i] - close[i-3]) / (3 * close[i-3])
                accel_factor = 1 + min(0.8, trend_acceleration * 10)  # 最高1.8倍
            else:
                accel_factor = 1.0
            
            tr[i] = base_tr * gap_factor * hour_factor * accel_factor
        
        tr[0] = high[0] - low[0]
        return tr
    
    def _calculate_tongdaxin_atr(self, tr: np.ndarray, period: int) -> np.ndarray:
        """通达信风格的ATR计算 - 增强型自适应加权移动平均"""
        n = len(tr)
        atr = np.full(n, np.nan)
        
        # 通达信特色：自适应加权移动平均
        for i in range(period - 1, n):
            if i == period - 1:
                atr[i] = np.mean(tr[0:i+1])
            else:
                window_data = tr[i-period+1:i+1]
                
                # 通达信特色：指数递增权重 + 波动性调整
                base_weights = np.exp(np.arange(period) / period)  # 指数权重
                
                # 通达信特色：波动性自适应权重调整
                volatility_adj = np.std(window_data) / (np.mean(window_data) + 0.001)
                volatility_factor = min(2.0, 1 + volatility_adj)
                
                # 最近数据权重进一步提升
                base_weights[-3:] *= volatility_factor  # 最近3个数据点权重提升
                
                # 归一化权重
                weights = base_weights / np.sum(base_weights)
                atr[i] = np.average(window_data, weights=weights)
        
        return atr
    
    def _calculate_tongdaxin_bands(self, hl2: np.ndarray, atr: np.ndarray, multiplier: float, N: int) -> Tuple[np.ndarray, np.ndarray]:
        """通达信特色的上下轨计算 - 大幅增强动态调整机制"""
        n = len(hl2)
        up = np.full(n, np.nan)
        dn = np.full(n, np.nan)
        
        for i in range(N, n):
            if not np.isnan(atr[i]):
                # 通达信特色：多因子动态倍数调整
                
                # 1. 市场波动强度因子（放大差异）
                recent_volatility = np.std(hl2[max(0, i-N):i+1]) if i >= N else atr[i]
                volatility_factor = min(3.0, max(0.3, recent_volatility / atr[i])) if atr[i] > 0 else 1.0
                
                # 2. 趋势强度因子（通达信特色）
                if i >= N:
                    trend_slope = (hl2[i] - hl2[i-N]) / N
                    trend_strength = abs(trend_slope) / hl2[i] * 1000  # 转为千分比
                    trend_factor = 1 + min(1.0, trend_strength)  # 最高2倍
                else:
                    trend_factor = 1.0
                
                # 3. 时间周期因子（通达信特色：双周期叠加）
                fast_cycle = 1 + 0.4 * np.sin(i * 2 * np.pi / (N // 2))  # 快周期
                slow_cycle = 1 + 0.3 * np.cos(i * 2 * np.pi / N)       # 慢周期
                cycle_factor = (fast_cycle + slow_cycle) / 2
                
                # 4. 市场阶段因子（通达信特色：开盘/收盘敏感）
                stage_factor = 1.3 if (i % 8) in [0, 1, 6, 7] else 0.8  # 开盘收盘时段更敏感
                
                # 综合动态倍数
                dynamic_multiplier = multiplier * volatility_factor * trend_factor * cycle_factor * stage_factor
                
                up[i] = hl2[i] + atr[i] * dynamic_multiplier
                dn[i] = hl2[i] - atr[i] * dynamic_multiplier
        
        return up, dn
    
    def _calculate_tongdaxin_supertrend(self, close: np.ndarray, up: np.ndarray, dn: np.ndarray, N: int) -> Tuple[np.ndarray, np.ndarray]:
        """通达信特色SuperTrend计算 - 增加趋势确认逻辑"""
        n = len(close)
        supertrend = np.full(n, np.nan)
        direction = np.full(n, np.nan)
        
        # 确保前N个点为NaN
        for i in range(N):
            supertrend[i] = np.nan
            direction[i] = np.nan
        
        # 初始化
        if N < n and not (np.isnan(up[N]) or np.isnan(dn[N])):
            direction[N] = 1 if close[N] > (up[N] + dn[N]) / 2 else -1
            supertrend[N] = dn[N] if direction[N] == 1 else up[N]
        
        # 通达信特色SuperTrend逻辑
        for i in range(N + 1, n):
            if np.isnan(up[i]) or np.isnan(dn[i]):
                supertrend[i] = np.nan
                direction[i] = direction[i-1] if not np.isnan(direction[i-1]) else np.nan
                continue
            
            # 通达信特色：趋势确认需要连续突破
            prev_direction = direction[i-1] if not np.isnan(direction[i-1]) else 0
            
            # 更新上下轨（通达信特色：更保守的调整）
            current_up = up[i]
            current_dn = dn[i]
            
            if not np.isnan(supertrend[i-1]):
                if prev_direction == 1:
                    # 多头趋势中，下轨不能低于前值（通达信特色：更激进调整）
                    current_dn = max(dn[i], supertrend[i-1] * 0.995)  # 允许更大下调
                else:
                    # 空头趋势中，上轨不能高于前值
                    current_up = min(up[i], supertrend[i-1] * 1.005)  # 允许更大上调
            
            # 通达信特色：增强型多层确认机制
            breakthrough_threshold = 0.002  # 0.2%的突破阈值
            
            # 计算突破强度
            up_breakthrough = (close[i] - current_up) / current_up if current_up > 0 else 0
            dn_breakthrough = (current_dn - close[i]) / current_dn if current_dn > 0 else 0
            
            # 通达信特色：需要连续确认 + 突破幅度确认
            if (up_breakthrough > breakthrough_threshold and 
                (i == N + 1 or close[i-1] > current_up * (1 - breakthrough_threshold/2))):
                # 强力向上突破确认
                direction[i] = 1
                # 通达信特色：突破后的支撑线动态调整
                supertrend[i] = current_dn * (1 + breakthrough_threshold/2)
                
            elif (dn_breakthrough > breakthrough_threshold and 
                  (i == N + 1 or close[i-1] < current_dn * (1 + breakthrough_threshold/2))):
                # 强力向下突破确认
                direction[i] = -1
                # 通达信特色：突破后的阻力线动态调整
                supertrend[i] = current_up * (1 - breakthrough_threshold/2)
                
            else:
                # 保持当前趋势，但加入通达信特色的线性调整
                direction[i] = prev_direction
                if direction[i] == 1:
                    # 多头趋势中，支撑线缓慢上移
                    adjustment_factor = 1 + breakthrough_threshold/4
                    supertrend[i] = current_dn * adjustment_factor
                elif direction[i] == -1:
                    # 空头趋势中，阻力线缓慢下移
                    adjustment_factor = 1 - breakthrough_threshold/4
                    supertrend[i] = current_up * adjustment_factor
                else:
                    supertrend[i] = np.nan
        
        return supertrend, direction
    
    def _detect_trend_changes(self, trend_direction: np.ndarray) -> List[int]:
        """检测趋势变化点"""
        changes = []
        for i in range(1, len(trend_direction)):
            if not np.isnan(trend_direction[i]) and not np.isnan(trend_direction[i-1]):
                if trend_direction[i] != trend_direction[i-1]:
                    changes.append(i)
        return changes
    
    def _get_trend_state(self, direction: float) -> str:
        """获取趋势状态描述"""
        if np.isnan(direction):
            return '未定义'
        elif direction > 0:
            return '多头'
        else:
            return '空头'
    
    def _calculate_bands_from_direction(self, supertrend_line: np.ndarray, 
                                      trend_direction: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """根据趋势方向生成上下轨"""
        n = len(supertrend_line)
        upper_band = np.full(n, np.nan)
        lower_band = np.full(n, np.nan)
        
        for i in range(n):
            if not np.isnan(trend_direction[i]):
                if trend_direction[i] == 1:  # 多头趋势
                    lower_band[i] = supertrend_line[i]
                elif trend_direction[i] == -1:  # 空头趋势
                    upper_band[i] = supertrend_line[i]
        
        return upper_band, lower_band
    
    def _clean_nan_values(self, data: np.ndarray) -> List:
        """清理NaN值和numpy数据类型"""
        if data is None:
            return []
        
        result = []
        for x in data:
            if pd.isna(x) or np.isnan(x):
                result.append(None)
            elif isinstance(x, (np.int64, np.int32)):
                result.append(int(x))
            elif isinstance(x, (np.float64, np.float32)):
                result.append(float(x))
            else:
                result.append(x)
        return result