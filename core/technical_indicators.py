#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Technical Indicators Module - 技术指标计算模块

提供常用技术指标的计算功能：
- MACD (Moving Average Convergence Divergence) - 移动平均收敛发散指标
- RSI (Relative Strength Index) - 相对强弱指标  
- KDJ - 随机指标
- Bollinger Bands - 布林带
- OBV (On Balance Volume) - 能量潮指标
- VRSI - 成交量相对强弱指标
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, Union
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """技术指标计算类"""
    
    @staticmethod
    def calculate_macd(data: pd.DataFrame, 
                      fast: int = 12, 
                      slow: int = 26, 
                      signal: int = 9,
                      price_col: str = 'close') -> Dict[str, pd.Series]:
        """
        计算MACD指标
        
        Args:
            data: 包含价格数据的DataFrame
            fast: 快速EMA周期，默认12
            slow: 慢速EMA周期，默认26
            signal: 信号线周期，默认9
            price_col: 用于计算的价格列名，默认'close'
            
        Returns:
            Dict包含: 'dif', 'dea', 'macd', 'histogram'
        """
        try:
            if price_col not in data.columns:
                logger.error(f"Price column '{price_col}' not found in data")
                return {}
                
            prices = data[price_col]
            
            # 计算快速和慢速EMA
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            
            # DIF线 (快线-慢线)
            dif = ema_fast - ema_slow
            
            # DEA线 (DIF的EMA)
            dea = dif.ewm(span=signal).mean()
            
            # MACD柱状图 (DIF-DEA)*2
            histogram = (dif - dea) * 2
            
            return {
                'dif': dif,
                'dea': dea,
                'macd': dif,  # DIF线通常被称为MACD线
                'histogram': histogram
            }
            
        except Exception as e:
            logger.error(f"MACD calculation error: {e}")
            return {}
    
    @staticmethod
    def calculate_rsi(data: pd.DataFrame,
                     period: int = 14,
                     price_col: str = 'close') -> pd.Series:
        """
        计算RSI指标
        
        Args:
            data: 包含价格数据的DataFrame
            period: RSI计算周期，默认14
            price_col: 用于计算的价格列名，默认'close'
            
        Returns:
            RSI值的Series
        """
        try:
            if price_col not in data.columns:
                logger.error(f"Price column '{price_col}' not found in data")
                return pd.Series()
                
            prices = data[price_col]
            
            # 计算价格变化
            delta = prices.diff()
            
            # 分离上涨和下跌
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # 计算平均增益和平均损失
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            # 计算相对强度
            rs = avg_gain / avg_loss
            
            # 计算RSI
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            return pd.Series()
    
    @staticmethod
    def calculate_kdj(data: pd.DataFrame,
                     k_period: int = 9,
                     d_period: int = 3,
                     j_period: int = 3,
                     high_col: str = 'high',
                     low_col: str = 'low',
                     close_col: str = 'close') -> Dict[str, pd.Series]:
        """
        计算KDJ指标
        
        Args:
            data: 包含OHLC数据的DataFrame
            k_period: K值计算周期，默认9
            d_period: D值计算周期，默认3
            j_period: J值计算周期，默认3
            high_col: 最高价列名，默认'high'
            low_col: 最低价列名，默认'low'
            close_col: 收盘价列名，默认'close'
            
        Returns:
            Dict包含: 'k', 'd', 'j'
        """
        try:
            required_cols = [high_col, low_col, close_col]
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                logger.error(f"Missing columns for KDJ: {missing_cols}")
                return {}
            
            high = data[high_col]
            low = data[low_col]
            close = data[close_col]
            
            # 计算最高价和最低价的滚动窗口
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            
            # 计算RSV (Raw Stochastic Value)
            rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
            
            # 计算K值 (RSV的移动平均)
            k = rsv.ewm(alpha=1/d_period).mean()
            
            # 计算D值 (K值的移动平均)
            d = k.ewm(alpha=1/d_period).mean()
            
            # 计算J值
            j = 3 * k - 2 * d
            
            return {
                'k': k,
                'd': d,
                'j': j
            }
            
        except Exception as e:
            logger.error(f"KDJ calculation error: {e}")
            return {}
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.DataFrame,
                                period: int = 20,
                                std_dev: float = 2.0,
                                price_col: str = 'close') -> Dict[str, pd.Series]:
        """
        计算布林带指标
        
        Args:
            data: 包含价格数据的DataFrame
            period: 移动平均周期，默认20
            std_dev: 标准差倍数，默认2.0
            price_col: 用于计算的价格列名，默认'close'
            
        Returns:
            Dict包含: 'upper', 'middle', 'lower', 'width', 'percent_b'
        """
        try:
            if price_col not in data.columns:
                logger.error(f"Price column '{price_col}' not found in data")
                return {}
                
            prices = data[price_col]
            
            # 计算中轨线 (移动平均)
            middle = prices.rolling(window=period).mean()
            
            # 计算标准差
            std = prices.rolling(window=period).std()
            
            # 计算上轨和下轨
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            
            # 计算带宽
            width = (upper - lower) / middle * 100
            
            # 计算%B (价格在布林带中的相对位置)
            percent_b = (prices - lower) / (upper - lower) * 100
            
            return {
                'upper': upper,
                'middle': middle,
                'lower': lower,
                'width': width,
                'percent_b': percent_b
            }
            
        except Exception as e:
            logger.error(f"Bollinger Bands calculation error: {e}")
            return {}
    
    @staticmethod
    def calculate_obv(data: pd.DataFrame,
                     price_col: str = 'close',
                     volume_col: str = 'volume') -> pd.Series:
        """
        计算OBV (能量潮) 指标
        
        Args:
            data: 包含价格和成交量数据的DataFrame
            price_col: 价格列名，默认'close'
            volume_col: 成交量列名，默认'volume'
            
        Returns:
            OBV值的Series
        """
        try:
            required_cols = [price_col, volume_col]
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                logger.error(f"Missing columns for OBV: {missing_cols}")
                return pd.Series()
            
            prices = data[price_col]
            volume = data[volume_col]
            
            # 计算价格变化方向
            price_change = prices.diff()
            
            # 根据价格变化方向调整成交量符号
            obv_volume = volume.copy()
            obv_volume[price_change < 0] = -volume[price_change < 0]
            obv_volume[price_change == 0] = 0
            
            # 计算累积成交量
            obv = obv_volume.cumsum()
            
            return obv
            
        except Exception as e:
            logger.error(f"OBV calculation error: {e}")
            return pd.Series()
    
    @staticmethod
    def calculate_vrsi(data: pd.DataFrame,
                      period: int = 14,
                      volume_col: str = 'volume') -> pd.Series:
        """
        计算VRSI (成交量相对强弱指标)
        
        Args:
            data: 包含成交量数据的DataFrame
            period: 计算周期，默认14
            volume_col: 成交量列名，默认'volume'
            
        Returns:
            VRSI值的Series
        """
        try:
            if volume_col not in data.columns:
                logger.error(f"Volume column '{volume_col}' not found in data")
                return pd.Series()
                
            volume = data[volume_col]
            
            # 计算成交量变化
            volume_change = volume.diff()
            
            # 分离成交量增长和减少
            volume_up = volume_change.where(volume_change > 0, 0)
            volume_down = -volume_change.where(volume_change < 0, 0)
            
            # 计算平均成交量增长和减少
            avg_volume_up = volume_up.rolling(window=period).mean()
            avg_volume_down = volume_down.rolling(window=period).mean()
            
            # 计算VRSI
            vrsi = 100 * avg_volume_up / (avg_volume_up + avg_volume_down)
            
            return vrsi
            
        except Exception as e:
            logger.error(f"VRSI calculation error: {e}")
            return pd.Series()
    
    @staticmethod
    def calculate_all_indicators(data: pd.DataFrame,
                               macd_params: Optional[Dict] = None,
                               rsi_params: Optional[Dict] = None,
                               kdj_params: Optional[Dict] = None,
                               bb_params: Optional[Dict] = None,
                               obv_params: Optional[Dict] = None,
                               vrsi_params: Optional[Dict] = None) -> Dict[str, Union[Dict, pd.Series]]:
        """
        一次性计算所有技术指标
        
        Args:
            data: 包含OHLCV数据的DataFrame
            macd_params: MACD参数字典
            rsi_params: RSI参数字典
            kdj_params: KDJ参数字典
            bb_params: 布林带参数字典
            obv_params: OBV参数字典
            vrsi_params: VRSI参数字典
            
        Returns:
            Dict包含所有计算的指标
        """
        try:
            results = {}
            
            # 设置默认参数
            macd_params = macd_params or {}
            rsi_params = rsi_params or {}
            kdj_params = kdj_params or {}
            bb_params = bb_params or {}
            obv_params = obv_params or {}
            vrsi_params = vrsi_params or {}
            
            # 计算各项指标
            results['macd'] = TechnicalIndicators.calculate_macd(data, **macd_params)
            results['rsi'] = TechnicalIndicators.calculate_rsi(data, **rsi_params)
            results['kdj'] = TechnicalIndicators.calculate_kdj(data, **kdj_params)
            results['bollinger'] = TechnicalIndicators.calculate_bollinger_bands(data, **bb_params)
            results['obv'] = TechnicalIndicators.calculate_obv(data, **obv_params)
            results['vrsi'] = TechnicalIndicators.calculate_vrsi(data, **vrsi_params)
            
            return results
            
        except Exception as e:
            logger.error(f"Calculate all indicators error: {e}")
            return {}

    @staticmethod
    def format_indicators_for_api(indicators: Dict, 
                                 data_length: int = None) -> Dict[str, Dict]:
        """
        格式化技术指标数据用于API响应
        
        Args:
            indicators: calculate_all_indicators返回的指标数据
            data_length: 数据长度限制
            
        Returns:
            格式化后的指标数据
        """
        try:
            formatted = {}
            
            # 格式化MACD
            if 'macd' in indicators and indicators['macd']:
                macd_data = indicators['macd']
                formatted['macd'] = {
                    'dif': macd_data.get('dif', pd.Series()).fillna(0).tail(data_length).tolist() if data_length else macd_data.get('dif', pd.Series()).fillna(0).tolist(),
                    'dea': macd_data.get('dea', pd.Series()).fillna(0).tail(data_length).tolist() if data_length else macd_data.get('dea', pd.Series()).fillna(0).tolist(),
                    'histogram': macd_data.get('histogram', pd.Series()).fillna(0).tail(data_length).tolist() if data_length else macd_data.get('histogram', pd.Series()).fillna(0).tolist()
                }
            
            # 格式化RSI
            if 'rsi' in indicators and len(indicators['rsi']) > 0:
                formatted['rsi'] = {
                    'values': indicators['rsi'].fillna(50).tail(data_length).tolist() if data_length else indicators['rsi'].fillna(50).tolist()
                }
            
            # 格式化KDJ
            if 'kdj' in indicators and indicators['kdj']:
                kdj_data = indicators['kdj']
                formatted['kdj'] = {
                    'k': kdj_data.get('k', pd.Series()).fillna(50).tail(data_length).tolist() if data_length else kdj_data.get('k', pd.Series()).fillna(50).tolist(),
                    'd': kdj_data.get('d', pd.Series()).fillna(50).tail(data_length).tolist() if data_length else kdj_data.get('d', pd.Series()).fillna(50).tolist(),
                    'j': kdj_data.get('j', pd.Series()).fillna(50).tail(data_length).tolist() if data_length else kdj_data.get('j', pd.Series()).fillna(50).tolist()
                }
            
            # 格式化布林带
            if 'bollinger' in indicators and indicators['bollinger']:
                bb_data = indicators['bollinger']
                formatted['bollinger'] = {
                    'upper': bb_data.get('upper', pd.Series()).fillna(0).tail(data_length).tolist() if data_length else bb_data.get('upper', pd.Series()).fillna(0).tolist(),
                    'middle': bb_data.get('middle', pd.Series()).fillna(0).tail(data_length).tolist() if data_length else bb_data.get('middle', pd.Series()).fillna(0).tolist(),
                    'lower': bb_data.get('lower', pd.Series()).fillna(0).tail(data_length).tolist() if data_length else bb_data.get('lower', pd.Series()).fillna(0).tolist(),
                    'width': bb_data.get('width', pd.Series()).fillna(0).tail(data_length).tolist() if data_length else bb_data.get('width', pd.Series()).fillna(0).tolist(),
                    'percent_b': bb_data.get('percent_b', pd.Series()).fillna(0).tail(data_length).tolist() if data_length else bb_data.get('percent_b', pd.Series()).fillna(0).tolist()
                }
            
            # 格式化OBV
            if 'obv' in indicators and len(indicators['obv']) > 0:
                formatted['obv'] = {
                    'values': indicators['obv'].fillna(0).tail(data_length).tolist() if data_length else indicators['obv'].fillna(0).tolist()
                }
            
            # 格式化VRSI
            if 'vrsi' in indicators and len(indicators['vrsi']) > 0:
                formatted['vrsi'] = {
                    'values': indicators['vrsi'].fillna(50).tail(data_length).tolist() if data_length else indicators['vrsi'].fillna(50).tolist()
                }
            
            return formatted
            
        except Exception as e:
            logger.error(f"Format indicators for API error: {e}")
            return {}

# 预设指标参数配置
DEFAULT_INDICATOR_PARAMS = {
    'macd': {'fast': 12, 'slow': 26, 'signal': 9},
    'rsi': {'period': 14},
    'kdj': {'k_period': 9, 'd_period': 3, 'j_period': 3},
    'bollinger': {'period': 20, 'std_dev': 2.0},
    'obv': {},
    'vrsi': {'period': 14}
}

# 指标阈值配置
INDICATOR_THRESHOLDS = {
    'rsi': {
        'oversold': 30,      # 超卖线
        'overbought': 70,    # 超买线
        'strong_oversold': 20,
        'strong_overbought': 80
    },
    'kdj': {
        'oversold': 20,
        'overbought': 80,
        'strong_oversold': 10,
        'strong_overbought': 90
    },
    'vrsi': {
        'oversold': 30,
        'overbought': 70
    }
}

def get_signal_analysis(indicators: Dict, thresholds: Dict = None) -> Dict[str, str]:
    """
    基于技术指标生成交易信号分析
    
    Args:
        indicators: 格式化后的技术指标数据
        thresholds: 自定义阈值，默认使用INDICATOR_THRESHOLDS
        
    Returns:
        各指标的信号分析结果
    """
    try:
        if thresholds is None:
            thresholds = INDICATOR_THRESHOLDS
        
        signals = {}
        
        # RSI信号分析
        if 'rsi' in indicators and indicators['rsi']['values']:
            current_rsi = indicators['rsi']['values'][-1]
            rsi_thresholds = thresholds.get('rsi', {})
            
            if current_rsi <= rsi_thresholds.get('strong_oversold', 20):
                signals['rsi'] = '强烈超卖，考虑买入'
            elif current_rsi <= rsi_thresholds.get('oversold', 30):
                signals['rsi'] = '超卖，可能反弹'
            elif current_rsi >= rsi_thresholds.get('strong_overbought', 80):
                signals['rsi'] = '强烈超买，考虑卖出'
            elif current_rsi >= rsi_thresholds.get('overbought', 70):
                signals['rsi'] = '超买，可能回调'
            else:
                signals['rsi'] = '正常区间'
        
        # KDJ信号分析
        if 'kdj' in indicators and indicators['kdj']['k']:
            current_k = indicators['kdj']['k'][-1]
            current_d = indicators['kdj']['d'][-1]
            kdj_thresholds = thresholds.get('kdj', {})
            
            if current_k <= kdj_thresholds.get('oversold', 20) and current_d <= kdj_thresholds.get('oversold', 20):
                signals['kdj'] = '超卖区域，关注金叉'
            elif current_k >= kdj_thresholds.get('overbought', 80) and current_d >= kdj_thresholds.get('overbought', 80):
                signals['kdj'] = '超买区域，关注死叉'
            elif current_k > current_d:
                signals['kdj'] = 'K线在D线上方，偏多'
            else:
                signals['kdj'] = 'K线在D线下方，偏空'
        
        # MACD信号分析
        if 'macd' in indicators and indicators['macd']['dif']:
            current_dif = indicators['macd']['dif'][-1]
            current_dea = indicators['macd']['dea'][-1]
            current_histogram = indicators['macd']['histogram'][-1]
            
            if current_dif > current_dea and current_histogram > 0:
                signals['macd'] = '金叉向上，多头趋势'
            elif current_dif < current_dea and current_histogram < 0:
                signals['macd'] = '死叉向下，空头趋势'
            elif current_histogram > 0:
                signals['macd'] = '多头动能'
            else:
                signals['macd'] = '空头动能'
        
        return signals
        
    except Exception as e:
        logger.error(f"Signal analysis error: {e}")
        return {}

if __name__ == "__main__":
    # 测试代码
    import matplotlib.pyplot as plt
    
    # 生成模拟数据进行测试
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    # 生成模拟价格数据
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # 生成模拟OHLCV数据
    test_data = pd.DataFrame({
        'date': dates,
        'open': np.array(prices) * np.random.uniform(0.98, 1.02, 100),
        'high': np.array(prices) * np.random.uniform(1.00, 1.05, 100),
        'low': np.array(prices) * np.random.uniform(0.95, 1.00, 100),
        'close': prices,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # 计算所有技术指标
    indicators = TechnicalIndicators.calculate_all_indicators(test_data)
    
    # 格式化指标数据
    formatted = TechnicalIndicators.format_indicators_for_api(indicators, 50)
    
    # 生成信号分析
    signals = get_signal_analysis(formatted)
    
    print("技术指标测试完成!")
    print("指标数据:", list(formatted.keys()))
    print("信号分析:", signals)