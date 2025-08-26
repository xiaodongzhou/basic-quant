"""
方向分析器实现
包含多种趋势方向判断算法
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import talib
from loguru import logger

from ..three_principle_strategy import DirectionAnalyzer, TrendDirection

class MovingAverageDirectionAnalyzer(DirectionAnalyzer):
    """基于移动平均线的方向分析器"""
    
    def __init__(self, short_period: int = 10, long_period: int = 30, 
                 filter_period: int = 5, **kwargs):
        self.short_period = short_period
        self.long_period = long_period
        self.filter_period = filter_period  # 过滤周期，避免频繁转换
        
        self.direction_confidence = 0.0
        self.last_direction = TrendDirection.UNKNOWN
        self.direction_counter = 0  # 方向持续计数
        
        logger.info(f"移动平均方向分析器初始化: 短期{short_period}, 长期{long_period}")
    
    def analyze_direction(self, df: pd.DataFrame, **kwargs) -> TrendDirection:
        """基于移动平均线分析方向"""
        if len(df) < self.long_period + 5:
            self.direction_confidence = 0.0
            return TrendDirection.UNKNOWN
        
        try:
            # 计算移动平均线
            short_ma = df['close'].rolling(window=self.short_period).mean()
            long_ma = df['close'].rolling(window=self.long_period).mean()
            
            # 获取最新值
            current_short = short_ma.iloc[-1]
            current_long = long_ma.iloc[-1]
            prev_short = short_ma.iloc[-2]
            prev_long = long_ma.iloc[-2]
            
            # 判断主趋势方向
            if current_short > current_long:
                if prev_short <= prev_long:
                    # 金叉
                    new_direction = TrendDirection.UP
                    self.direction_confidence = 0.8
                else:
                    # 持续多头
                    new_direction = TrendDirection.UP
                    # 根据MA斜率调整置信度
                    ma_slope = (current_short - prev_short) / prev_short
                    self.direction_confidence = min(0.9, 0.6 + abs(ma_slope) * 100)
                    
            elif current_short < current_long:
                if prev_short >= prev_long:
                    # 死叉
                    new_direction = TrendDirection.DOWN
                    self.direction_confidence = 0.8
                else:
                    # 持续空头
                    new_direction = TrendDirection.DOWN
                    # 根据MA斜率调整置信度
                    ma_slope = (current_short - prev_short) / prev_short
                    self.direction_confidence = min(0.9, 0.6 + abs(ma_slope) * 100)
            else:
                # MA接近，判断为横盘
                new_direction = TrendDirection.SIDEWAYS
                self.direction_confidence = 0.3
            
            # 方向过滤（避免频繁变化）
            if new_direction == self.last_direction:
                self.direction_counter += 1
            else:
                if self.direction_counter >= self.filter_period:
                    # 足够的确认，改变方向
                    self.last_direction = new_direction
                    self.direction_counter = 1
                else:
                    # 不足确认，保持原方向
                    new_direction = self.last_direction
                    self.direction_counter = 0
                    self.direction_confidence *= 0.8  # 降低置信度
            
            return new_direction
            
        except Exception as e:
            logger.error(f"移动平均方向分析失败: {e}")
            self.direction_confidence = 0.0
            return TrendDirection.UNKNOWN
    
    def get_direction_confidence(self) -> float:
        """获取方向置信度"""
        return self.direction_confidence

class TrendlineDirectionAnalyzer(DirectionAnalyzer):
    """基于趋势线的方向分析器"""
    
    def __init__(self, lookback_period: int = 20, min_touches: int = 2, 
                 slope_threshold: float = 0.001, **kwargs):
        self.lookback_period = lookback_period
        self.min_touches = min_touches
        self.slope_threshold = slope_threshold
        
        self.direction_confidence = 0.0
        self.support_line = None
        self.resistance_line = None
        
        logger.info(f"趋势线方向分析器初始化: 回看{lookback_period}期")
    
    def analyze_direction(self, df: pd.DataFrame, **kwargs) -> TrendDirection:
        """基于趋势线分析方向"""
        if len(df) < self.lookback_period + 5:
            self.direction_confidence = 0.0
            return TrendDirection.UNKNOWN
        
        try:
            recent_df = df.tail(self.lookback_period)
            current_price = df['close'].iloc[-1]
            
            # 计算支撑线和阻力线
            self.support_line = self._calculate_support_line(recent_df)
            self.resistance_line = self._calculate_resistance_line(recent_df)
            
            # 判断趋势方向
            if self.support_line and self.resistance_line:
                support_slope = self.support_line.get('slope', 0)
                resistance_slope = self.resistance_line.get('slope', 0)
                
                # 上升趋势：支撑线和阻力线都向上倾斜
                if (support_slope > self.slope_threshold and 
                    resistance_slope > self.slope_threshold):
                    self.direction_confidence = min(0.9, 0.6 + abs(support_slope) * 1000)
                    return TrendDirection.UP
                
                # 下降趋势：支撑线和阻力线都向下倾斜
                elif (support_slope < -self.slope_threshold and 
                      resistance_slope < -self.slope_threshold):
                    self.direction_confidence = min(0.9, 0.6 + abs(support_slope) * 1000)
                    return TrendDirection.DOWN
                
                # 横盘：斜率较小
                else:
                    self.direction_confidence = 0.4
                    return TrendDirection.SIDEWAYS
            
            # 单独分析当前趋势
            return self._analyze_price_momentum(recent_df)
            
        except Exception as e:
            logger.error(f"趋势线方向分析失败: {e}")
            self.direction_confidence = 0.0
            return TrendDirection.UNKNOWN
    
    def _calculate_support_line(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算支撑线"""
        lows = df['low'].values
        time_indices = np.arange(len(lows))
        
        # 找到局部最低点
        local_mins = []
        for i in range(1, len(lows) - 1):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                local_mins.append((i, lows[i]))
        
        if len(local_mins) < self.min_touches:
            return None
        
        # 使用最低的几个点拟合直线
        local_mins.sort(key=lambda x: x[1])  # 按价格排序
        selected_points = local_mins[:self.min_touches]
        
        if len(selected_points) >= 2:
            x_coords = [p[0] for p in selected_points]
            y_coords = [p[1] for p in selected_points]
            
            # 线性回归
            slope, intercept = np.polyfit(x_coords, y_coords, 1)
            
            return {
                'slope': slope,
                'intercept': intercept,
                'points': selected_points,
                'current_level': slope * (len(df) - 1) + intercept
            }
        
        return None
    
    def _calculate_resistance_line(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算阻力线"""
        highs = df['high'].values
        time_indices = np.arange(len(highs))
        
        # 找到局部最高点
        local_maxs = []
        for i in range(1, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                local_maxs.append((i, highs[i]))
        
        if len(local_maxs) < self.min_touches:
            return None
        
        # 使用最高的几个点拟合直线
        local_maxs.sort(key=lambda x: x[1], reverse=True)  # 按价格倒序
        selected_points = local_maxs[:self.min_touches]
        
        if len(selected_points) >= 2:
            x_coords = [p[0] for p in selected_points]
            y_coords = [p[1] for p in selected_points]
            
            # 线性回归
            slope, intercept = np.polyfit(x_coords, y_coords, 1)
            
            return {
                'slope': slope,
                'intercept': intercept,
                'points': selected_points,
                'current_level': slope * (len(df) - 1) + intercept
            }
        
        return None
    
    def _analyze_price_momentum(self, df: pd.DataFrame) -> TrendDirection:
        """分析价格动量"""
        if len(df) < 5:
            return TrendDirection.UNKNOWN
        
        # 计算价格变化率
        price_changes = df['close'].pct_change().dropna()
        
        # 统计上涨和下跌的次数
        up_count = sum(price_changes > 0)
        down_count = sum(price_changes < 0)
        
        # 计算平均涨跌幅
        avg_up = price_changes[price_changes > 0].mean() if up_count > 0 else 0
        avg_down = abs(price_changes[price_changes < 0].mean()) if down_count > 0 else 0
        
        # 综合判断
        if up_count > down_count and avg_up > avg_down:
            self.direction_confidence = 0.6
            return TrendDirection.UP
        elif down_count > up_count and avg_down > avg_up:
            self.direction_confidence = 0.6
            return TrendDirection.DOWN
        else:
            self.direction_confidence = 0.3
            return TrendDirection.SIDEWAYS
    
    def get_direction_confidence(self) -> float:
        """获取方向置信度"""
        return self.direction_confidence

class MultiIndicatorDirectionAnalyzer(DirectionAnalyzer):
    """多指标综合方向分析器"""
    
    def __init__(self, rsi_period: int = 14, macd_fast: int = 12, 
                 macd_slow: int = 26, macd_signal: int = 9, **kwargs):
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        
        self.direction_confidence = 0.0
        self.individual_signals = {}
        
        logger.info(f"多指标方向分析器初始化: RSI{rsi_period}, MACD({macd_fast},{macd_slow},{macd_signal})")
    
    def analyze_direction(self, df: pd.DataFrame, **kwargs) -> TrendDirection:
        """基于多个技术指标综合分析方向"""
        if len(df) < max(self.macd_slow, self.rsi_period) + 10:
            self.direction_confidence = 0.0
            return TrendDirection.UNKNOWN
        
        try:
            signals = []
            
            # 1. RSI分析
            rsi_signal = self._analyze_rsi(df)
            signals.append(rsi_signal)
            self.individual_signals['RSI'] = rsi_signal
            
            # 2. MACD分析  
            macd_signal = self._analyze_macd(df)
            signals.append(macd_signal)
            self.individual_signals['MACD'] = macd_signal
            
            # 3. 价格趋势分析
            price_signal = self._analyze_price_trend(df)
            signals.append(price_signal)
            self.individual_signals['PRICE'] = price_signal
            
            # 4. 成交量分析
            volume_signal = self._analyze_volume_trend(df)
            signals.append(volume_signal)
            self.individual_signals['VOLUME'] = volume_signal
            
            # 综合判断
            return self._combine_signals(signals)
            
        except Exception as e:
            logger.error(f"多指标方向分析失败: {e}")
            self.direction_confidence = 0.0
            return TrendDirection.UNKNOWN
    
    def _analyze_rsi(self, df: pd.DataFrame) -> Dict[str, Any]:
        """RSI分析"""
        # 简化的RSI计算
        price_changes = df['close'].diff()
        gains = price_changes.where(price_changes > 0, 0)
        losses = -price_changes.where(price_changes < 0, 0)
        
        avg_gains = gains.rolling(window=self.rsi_period).mean()
        avg_losses = losses.rolling(window=self.rsi_period).mean()
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else 50
        
        if current_rsi > 70:
            # 超买，可能下跌
            return {'direction': TrendDirection.DOWN, 'strength': 0.7}
        elif current_rsi < 30:
            # 超卖，可能上涨
            return {'direction': TrendDirection.UP, 'strength': 0.7}
        elif current_rsi > prev_rsi and current_rsi > 50:
            # RSI上升且在50以上
            return {'direction': TrendDirection.UP, 'strength': 0.5}
        elif current_rsi < prev_rsi and current_rsi < 50:
            # RSI下降且在50以下
            return {'direction': TrendDirection.DOWN, 'strength': 0.5}
        else:
            return {'direction': TrendDirection.SIDEWAYS, 'strength': 0.3}
    
    def _analyze_macd(self, df: pd.DataFrame) -> Dict[str, Any]:
        """MACD分析"""
        # 简化的MACD计算
        ema_fast = df['close'].ewm(span=self.macd_fast).mean()
        ema_slow = df['close'].ewm(span=self.macd_slow).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.macd_signal).mean()
        histogram = macd - signal
        
        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]
        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2] if len(histogram) > 1 else 0
        
        if current_macd > current_signal and current_hist > 0:
            # 金叉且柱状图为正
            return {'direction': TrendDirection.UP, 'strength': 0.8}
        elif current_macd < current_signal and current_hist < 0:
            # 死叉且柱状图为负
            return {'direction': TrendDirection.DOWN, 'strength': 0.8}
        elif current_hist > prev_hist and current_hist > 0:
            # 柱状图增长且为正
            return {'direction': TrendDirection.UP, 'strength': 0.6}
        elif current_hist < prev_hist and current_hist < 0:
            # 柱状图减少且为负
            return {'direction': TrendDirection.DOWN, 'strength': 0.6}
        else:
            return {'direction': TrendDirection.SIDEWAYS, 'strength': 0.3}
    
    def _analyze_price_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """价格趋势分析"""
        # 使用简单的价格动量
        lookback = 10
        if len(df) < lookback:
            return {'direction': TrendDirection.SIDEWAYS, 'strength': 0.1}
        
        recent_prices = df['close'].tail(lookback)
        price_change = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
        
        if price_change > 0.02:  # 2%以上涨幅
            return {'direction': TrendDirection.UP, 'strength': 0.6}
        elif price_change < -0.02:  # 2%以上跌幅
            return {'direction': TrendDirection.DOWN, 'strength': 0.6}
        else:
            return {'direction': TrendDirection.SIDEWAYS, 'strength': 0.4}
    
    def _analyze_volume_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """成交量趋势分析"""
        if 'volume' not in df.columns:
            return {'direction': TrendDirection.SIDEWAYS, 'strength': 0.1}
        
        # 计算成交量移动平均
        volume_ma = df['volume'].rolling(window=5).mean()
        current_volume = df['volume'].iloc[-1]
        avg_volume = volume_ma.iloc[-1]
        
        # 价格变化
        price_change = df['close'].pct_change().iloc[-1]
        
        if current_volume > avg_volume * 1.5:  # 放量
            if price_change > 0:
                return {'direction': TrendDirection.UP, 'strength': 0.7}
            elif price_change < 0:
                return {'direction': TrendDirection.DOWN, 'strength': 0.7}
        
        return {'direction': TrendDirection.SIDEWAYS, 'strength': 0.2}
    
    def _combine_signals(self, signals: List[Dict[str, Any]]) -> TrendDirection:
        """综合多个信号"""
        up_strength = 0
        down_strength = 0
        sideways_strength = 0
        
        for signal in signals:
            direction = signal['direction']
            strength = signal['strength']
            
            if direction == TrendDirection.UP:
                up_strength += strength
            elif direction == TrendDirection.DOWN:
                down_strength += strength
            else:
                sideways_strength += strength
        
        # 归一化强度
        total_strength = up_strength + down_strength + sideways_strength
        if total_strength > 0:
            up_strength /= total_strength
            down_strength /= total_strength
            sideways_strength /= total_strength
        
        # 确定最强方向
        max_strength = max(up_strength, down_strength, sideways_strength)
        self.direction_confidence = max_strength
        
        if max_strength == up_strength:
            return TrendDirection.UP
        elif max_strength == down_strength:
            return TrendDirection.DOWN
        else:
            return TrendDirection.SIDEWAYS
    
    def get_direction_confidence(self) -> float:
        """获取方向置信度"""
        return self.direction_confidence
    
    def get_individual_signals(self) -> Dict[str, Dict[str, Any]]:
        """获取各个指标的单独信号"""
        return self.individual_signals