#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势分析器模块
实现可扩展的趋势分析框架
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Tuple, List
import logging

logger = logging.getLogger(__name__)


class TrendState(Enum):
    """趋势状态枚举"""
    BULLISH = "多头"      # 上涨趋势
    BEARISH = "空头"      # 下跌趋势
    SIDEWAYS = "震荡"     # 横盘震荡


class TrendAnalyzer(ABC):
    """趋势分析器基类 - 可扩展接口"""
    
    def __init__(self, name: str, parameters: Dict[str, Any]):
        self.name = name
        self.parameters = parameters
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算趋势指标
        
        Args:
            data: 包含OHLCV数据的DataFrame
            
        Returns:
            Dict包含趋势数据和状态信息
        """
        pass
    
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
    
    def get_minimum_periods(self) -> int:
        """获取计算所需的最小周期数"""
        return 20  # 默认最小周期


class SuperTrendAnalyzer(TrendAnalyzer):
    """超级趋势分析器 - 基于ATR的趋势跟踪指标"""
    
    def __init__(self, atr_period: int = 10, multiplier: float = 3.0):
        parameters = {
            'atr_period': atr_period,
            'multiplier': multiplier
        }
        super().__init__('SuperTrend', parameters)
        self.atr_period = atr_period
        self.multiplier = multiplier
    
    def get_minimum_periods(self) -> int:
        return max(20, self.atr_period + 10)
    
    def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算超级趋势指标
        
        Returns:
            Dict包含:
            - supertrend_upper: 上轨数据
            - supertrend_lower: 下轨数据  
            - trend_direction: 趋势方向 (1=多头, -1=空头)
            - active_line: 当前有效趋势线
            - trend_changes: 趋势转换点
        """
        if not self.validate_data(data):
            raise ValueError("数据验证失败")
        
        try:
            logger.info(f"计算SuperTrend指标: ATR周期={self.atr_period}, 倍数={self.multiplier}")
            
            # 自定义实现SuperTrend算法（无需pandas-ta）
            supertrend_line, trend_direction = self._calculate_supertrend_custom(data)
            
            if supertrend_line is None or len(supertrend_line) == 0:
                raise ValueError("SuperTrend计算失败")
            
            # 计算上轨和下轨
            upper_band, lower_band = self._calculate_bands(data, supertrend_line, trend_direction)
            
            # 检测趋势变换点
            trend_changes = self._detect_trend_changes(trend_direction)
            
            # 生成当前趋势状态
            current_trend = self._get_trend_state(trend_direction[-1] if len(trend_direction) > 0 else 0)
            
            result = {
                'supertrend_line': supertrend_line.tolist(),
                'supertrend_upper': upper_band.tolist(),
                'supertrend_lower': lower_band.tolist(),
                'trend_direction': trend_direction.tolist(),
                'trend_changes': trend_changes,
                'current_trend': current_trend,
                'timestamps': data.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'parameters': self.parameters,
                'trend_strength': abs(trend_direction[-1]) if len(trend_direction) > 0 else 0
            }
            
            logger.info(f"SuperTrend计算完成: 当前趋势={current_trend}, 数据点数={len(supertrend_line)}")
            return result
            
        except Exception as e:
            logger.error(f"SuperTrend计算错误: {e}")
            raise
    
    def _calculate_supertrend_custom(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        改进的SuperTrend计算实现 - 更准确的算法
        基于ATR和HL2的超级趋势指标
        """
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values
        n = len(close)
        
        # 计算ATR (Average True Range) - 使用更精确的算法
        atr = self._calculate_atr_improved(high, low, close)
        
        # 计算HL2 (High-Low Average)
        hl2 = (high + low) / 2
        
        # 计算基础上轨和下轨
        basic_upper = hl2 + (self.multiplier * atr)
        basic_lower = hl2 - (self.multiplier * atr)
        
        # 初始化最终上下轨
        final_upper = np.full(n, np.nan)
        final_lower = np.full(n, np.nan)
        
        # 初始化SuperTrend线和方向
        supertrend = np.full(n, np.nan)
        direction = np.full(n, 1.0)  # 1=多头, -1=空头
        
        # 从第一个有效ATR值开始计算
        # ATR在索引atr_period-1处开始有效，SuperTrend从atr_period开始
        start_idx = self.atr_period
        
        logger.info(f"SuperTrend计算: ATR周期={self.atr_period}, 开始索引={start_idx}, 数据长度={n}")
        logger.info(f"前{start_idx}个点将为NaN，SuperTrend从索引{start_idx}开始有效")
        
        if start_idx < n:
            # 计算修正后的上下轨
            for i in range(start_idx, n):
                # 上轨修正逻辑
                if i == start_idx:
                    final_upper[i] = basic_upper[i]
                else:
                    if basic_upper[i] < final_upper[i-1] or close[i-1] > final_upper[i-1]:
                        final_upper[i] = basic_upper[i]
                    else:
                        final_upper[i] = final_upper[i-1]
                
                # 下轨修正逻辑  
                if i == start_idx:
                    final_lower[i] = basic_lower[i]
                else:
                    if basic_lower[i] > final_lower[i-1] or close[i-1] < final_lower[i-1]:
                        final_lower[i] = basic_lower[i]
                    else:
                        final_lower[i] = final_lower[i-1]
            
            # 计算SuperTrend线和趋势方向
            for i in range(start_idx, n):
                if i == start_idx:
                    # 初始趋势判断
                    if close[i] <= final_lower[i]:
                        direction[i] = -1  # 空头
                        supertrend[i] = final_upper[i]
                    else:
                        direction[i] = 1   # 多头
                        supertrend[i] = final_lower[i]
                else:
                    # 趋势判断逻辑
                    prev_direction = direction[i-1]
                    
                    if prev_direction == 1:  # 之前是多头
                        if close[i] <= final_lower[i]:
                            direction[i] = -1  # 转为空头
                            supertrend[i] = final_upper[i]
                        else:
                            direction[i] = 1   # 保持多头
                            supertrend[i] = final_lower[i]
                    else:  # 之前是空头
                        if close[i] >= final_upper[i]:
                            direction[i] = 1   # 转为多头
                            supertrend[i] = final_lower[i]
                        else:
                            direction[i] = -1  # 保持空头
                            supertrend[i] = final_upper[i]
        
        return supertrend, direction
    
    def _calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """
        计算ATR (Average True Range) - 简单移动平均版本
        """
        n = len(close)
        tr = np.full(n, np.nan)
        
        # 计算True Range
        for i in range(1, n):
            hl = high[i] - low[i]  # High - Low
            hc = abs(high[i] - close[i-1])  # |High - Previous Close|
            lc = abs(low[i] - close[i-1])   # |Low - Previous Close|
            tr[i] = max(hl, hc, lc)
        
        # 计算ATR（简单移动平均）
        atr = np.full(n, np.nan)
        for i in range(self.atr_period, n):
            atr[i] = np.mean(tr[i-self.atr_period+1:i+1])
        
        return atr
    
    def _calculate_atr_improved(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """
        改进的ATR计算 - 使用指数移动平均（EMA）更接近标准实现
        """
        n = len(close)
        tr = np.full(n, np.nan)
        
        # 计算True Range
        tr[0] = high[0] - low[0]  # 第一个值
        for i in range(1, n):
            hl = high[i] - low[i]  # High - Low
            hc = abs(high[i] - close[i-1])  # |High - Previous Close|
            lc = abs(low[i] - close[i-1])   # |Low - Previous Close|
            tr[i] = max(hl, hc, lc)
        
        # 计算ATR - 使用指数移动平均
        atr = np.full(n, np.nan)
        alpha = 2.0 / (self.atr_period + 1)  # EMA平滑系数
        
        # 初始ATR值使用简单移动平均
        if n >= self.atr_period:
            atr[self.atr_period - 1] = np.mean(tr[:self.atr_period])
            
            # 后续值使用EMA
            for i in range(self.atr_period, n):
                atr[i] = alpha * tr[i] + (1 - alpha) * atr[i-1]
        
        return atr
    
    def _calculate_bands(self, data: pd.DataFrame, supertrend_line: np.ndarray, 
                        trend_direction: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算上轨和下轨数据
        在多头时显示下轨，在空头时显示上轨
        """
        n = len(supertrend_line)
        upper_band = np.full(n, np.nan)
        lower_band = np.full(n, np.nan)
        
        for i in range(n):
            if trend_direction[i] == 1:  # 多头趋势
                lower_band[i] = supertrend_line[i]  # 下轨作为支撑
            elif trend_direction[i] == -1:  # 空头趋势  
                upper_band[i] = supertrend_line[i]  # 上轨作为压力
        
        return upper_band, lower_band
    
    def _detect_trend_changes(self, trend_direction: np.ndarray) -> List[Dict]:
        """检测趋势转换点"""
        changes = []
        
        for i in range(1, len(trend_direction)):
            if trend_direction[i] != trend_direction[i-1]:
                change_type = "转多" if trend_direction[i] == 1 else "转空"
                changes.append({
                    'index': i,
                    'type': change_type,
                    'from_trend': self._get_trend_state(trend_direction[i-1]),
                    'to_trend': self._get_trend_state(trend_direction[i])
                })
        
        return changes
    
    def _get_trend_state(self, direction: float) -> str:
        """将数值方向转换为趋势状态"""
        if direction == 1:
            return TrendState.BULLISH.value
        elif direction == -1:
            return TrendState.BEARISH.value
        else:
            return TrendState.SIDEWAYS.value


class SuperTrendPandasAnalyzer(TrendAnalyzer):
    """基于pandas-ta库的SuperTrend分析器 - 作为对比参考"""
    
    def __init__(self, atr_period: int = 10, multiplier: float = 3.0):
        parameters = {
            'atr_period': atr_period,
            'multiplier': multiplier
        }
        super().__init__('SuperTrend_Pandas', parameters)
        self.atr_period = atr_period
        self.multiplier = multiplier
    
    def get_minimum_periods(self) -> int:
        return max(20, self.atr_period + 10)
    
    def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        使用pandas-ta库计算SuperTrend指标
        """
        if not self.validate_data(data):
            raise ValueError("数据验证失败")
        
        try:
            import pandas_ta as ta
            logger.info(f"使用pandas-ta计算SuperTrend: ATR周期={self.atr_period}, 倍数={self.multiplier}")
            
            # 使用pandas-ta计算SuperTrend
            # 注意: pandas-ta使用length作为ATR周期参数
            supertrend_data = ta.supertrend(
                high=data['high'], 
                low=data['low'], 
                close=data['close'], 
                length=self.atr_period, 
                multiplier=self.multiplier
            )
            
            if supertrend_data is None or supertrend_data.empty:
                raise ValueError("pandas-ta SuperTrend计算失败")
            
            # 解析pandas-ta的返回结果
            # 列名格式: SUPERT_{length}_{multiplier}, SUPERTd_{length}_{multiplier}, etc.
            col_suffix = f"{self.atr_period}_{self.multiplier}"
            
            # 获取各个列
            supertrend_line = supertrend_data[f'SUPERT_{col_suffix}'].values  # SuperTrend线值
            trend_direction = supertrend_data[f'SUPERTd_{col_suffix}'].values  # 趋势方向 (1=多头, -1=空头)
            supertrend_lower = supertrend_data[f'SUPERTl_{col_suffix}'].values  # 下轨
            supertrend_upper = supertrend_data[f'SUPERTs_{col_suffix}'].values  # 上轨
            
            # 处理NaN值和方向转换
            # pandas-ta的趋势方向: 1=多头, 0=空头，需要转换为1/-1格式
            trend_direction_adjusted = np.where(trend_direction == 1, 1, -1)
            
            # 检测趋势变化点
            trend_changes = self._detect_trend_changes(trend_direction_adjusted)
            
            # 生成当前趋势状态
            valid_directions = trend_direction_adjusted[~np.isnan(trend_direction_adjusted)]
            current_trend = self._get_trend_state(valid_directions[-1] if len(valid_directions) > 0 else 0)
            
            # 处理上下轨数据：pandas-ta可能返回的格式与我们的不同
            # 如果上下轨都是NaN，则使用SuperTrend线根据方向生成
            if np.all(np.isnan(supertrend_upper)) and np.all(np.isnan(supertrend_lower)):
                supertrend_upper, supertrend_lower = self._calculate_bands(data, supertrend_line, trend_direction_adjusted)
            
            result = {
                'supertrend_line': self._clean_nan_values(supertrend_line),
                'supertrend_upper': self._clean_nan_values(supertrend_upper),
                'supertrend_lower': self._clean_nan_values(supertrend_lower),
                'trend_direction': self._clean_nan_values(trend_direction_adjusted),
                'trend_changes': trend_changes,
                'current_trend': current_trend,
                'timestamps': data.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'parameters': self.parameters,
                'trend_strength': abs(valid_directions[-1]) if len(valid_directions) > 0 else 0,
                'source': 'pandas-ta'
            }
            
            logger.info(f"pandas-ta SuperTrend计算完成: 当前趋势={current_trend}, 数据点数={len(supertrend_line)}")
            return result
            
        except ImportError:
            raise ValueError("pandas-ta库未安装，无法使用SuperTrend_Pandas")
        except Exception as e:
            logger.error(f"pandas-ta SuperTrend计算错误: {e}")
            raise
    
    def _clean_nan_values(self, data: np.ndarray) -> List:
        """清理NaN值和numpy数据类型，转换为None/Python原生类型以适合JSON序列化"""
        result = []
        for x in data:
            if pd.isna(x):
                result.append(None)
            elif isinstance(x, (np.integer, np.int64, np.int32)):
                result.append(int(x))  # 转换numpy整数为Python int
            elif isinstance(x, (np.floating, np.float64, np.float32)):
                result.append(float(x))  # 转换numpy浮点数为Python float
            else:
                result.append(x)  # 其他类型保持不变
        return result
    
    def _calculate_bands(self, data: pd.DataFrame, supertrend_line: np.ndarray, 
                        trend_direction: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算上轨和下轨数据
        在多头时显示下轨，在空头时显示上轨
        """
        n = len(supertrend_line)
        upper_band = np.full(n, np.nan)
        lower_band = np.full(n, np.nan)
        
        for i in range(n):
            if not np.isnan(trend_direction[i]):
                if trend_direction[i] == 1:  # 多头趋势
                    lower_band[i] = supertrend_line[i]  # 下轨作为支撑
                elif trend_direction[i] == -1:  # 空头趋势  
                    upper_band[i] = supertrend_line[i]  # 上轨作为压力
        
        return upper_band, lower_band
    
    def _detect_trend_changes(self, trend_direction: np.ndarray) -> List[Dict]:
        """检测趋势转换点"""
        changes = []
        
        for i in range(1, len(trend_direction)):
            if not np.isnan(trend_direction[i]) and not np.isnan(trend_direction[i-1]):
                if trend_direction[i] != trend_direction[i-1]:
                    change_type = "转多" if trend_direction[i] == 1 else "转空"
                    changes.append({
                        'index': i,
                        'type': change_type,
                        'from_trend': self._get_trend_state(trend_direction[i-1]),
                        'to_trend': self._get_trend_state(trend_direction[i])
                    })
        
        return changes
    
    def _get_trend_state(self, direction: float) -> str:
        """将数值方向转换为趋势状态"""
        if direction == 1:
            return TrendState.BULLISH.value
        elif direction == -1:
            return TrendState.BEARISH.value
        else:
            return TrendState.SIDEWAYS.value


class TrendAnalyzerFactory:
    """趋势分析器工厂类 - 支持动态注册和创建"""
    
    _analyzers = {
        'supertrend': SuperTrendAnalyzer,
        'supertrend_pandas': SuperTrendPandasAnalyzer
    }
    
    @classmethod
    def _import_my_supertrend(cls):
        """动态导入MySuperTrend分析器"""
        try:
            from my_supertrend_analyzer import MySuperTrendAnalyzer
            return MySuperTrendAnalyzer
        except ImportError:
            logger.error("无法导入MySuperTrendAnalyzer")
            return None
    
    @classmethod
    def register(cls, name: str, analyzer_class):
        """注册新的趋势分析器"""
        cls._analyzers[name] = analyzer_class
        logger.info(f"注册趋势分析器: {name}")
    
    @classmethod
    def create(cls, name: str, **parameters):
        """创建趋势分析器实例"""
        if name == 'my_supertrend':
            # 动态导入MySuperTrend
            my_class = cls._import_my_supertrend()
            if my_class:
                return my_class(**parameters)
            else:
                raise ValueError("MySuperTrend分析器导入失败")
        
        if name not in cls._analyzers:
            raise ValueError(f"未知的趋势分析器: {name}")
        
        return cls._analyzers[name](**parameters)
    
    @classmethod
    def list_available(cls) -> List[str]:
        """列出所有可用的趋势分析器"""
        available = list(cls._analyzers.keys())
        # 添加MySuperTrend到可用列表
        available.append('my_supertrend')
        return available


# 使用示例
if __name__ == "__main__":
    # 测试超级趋势分析器
    import matplotlib.pyplot as plt
    
    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=100, freq='H')
    np.random.seed(42)
    
    price = 3500
    data_list = []
    
    for i in range(100):
        change = np.random.normal(0, 20)
        price += change
        high = price + abs(np.random.normal(0, 10))
        low = price - abs(np.random.normal(0, 10))
        open_price = price + np.random.normal(0, 5)
        volume = np.random.randint(1000, 5000)
        
        data_list.append({
            'open': open_price,
            'high': high,
            'low': low, 
            'close': price,
            'volume': volume
        })
    
    test_data = pd.DataFrame(data_list, index=dates)
    
    # 测试超级趋势分析器
    analyzer = SuperTrendAnalyzer(atr_period=10, multiplier=3.0)
    result = analyzer.calculate(test_data)
    
    print(f"SuperTrend测试完成:")
    print(f"当前趋势: {result['current_trend']}")
    print(f"趋势转换次数: {len(result['trend_changes'])}")
    print(f"数据点数: {len(result['supertrend_line'])}")