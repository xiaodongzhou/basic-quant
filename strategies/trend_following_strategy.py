"""
趋势跟踪策略
基于三原则框架的完整策略实现示例
结合移动平均方向分析 + ATR位置管理 + 价格行为信号生成
"""
import pandas as pd
import numpy as np
from typing import Dict, Any
from datetime import datetime
from loguru import logger

from .three_principle_strategy import ThreePrincipleStrategy, TrendDirection
from .components.direction_analyzers import MovingAverageDirectionAnalyzer, MultiIndicatorDirectionAnalyzer
from .components.position_managers import ATRPositionManager, SupportResistancePositionManager
from .components.signal_generators import PriceActionSignalGenerator, BreakoutSignalGenerator

class TrendFollowingStrategy(ThreePrincipleStrategy):
    """
    趋势跟踪策略
    - 方向：基于移动平均线和多技术指标判断趋势方向
    - 位置：使用ATR计算入场和出场位置
    - 信号：基于价格行为确认交易信号
    """
    
    def __init__(self, name: str = "趋势跟踪策略", symbol: str = "BTCUSDT", parameters: Dict[str, Any] = None):
        # 默认参数
        default_params = {
            # 方向分析参数
            'ma_short_period': 10,
            'ma_long_period': 30,
            'ma_filter_period': 3,
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            
            # 位置管理参数
            'atr_period': 14,
            'atr_entry_multiplier': 0.5,
            'atr_stop_multiplier': 2.0,
            'atr_target_multiplier': 4.0,
            
            # 信号生成参数
            'min_signal_confidence': 0.6,
            'price_tolerance': 0.002,
            'volume_confirmation': True,
            
            # 风险管理参数
            'max_position_size': 1.0,
            'risk_per_trade': 0.02,
            'account_balance': 100000,
            'volume': 1.0
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name, symbol, default_params)
        
        # 初始化三个组件
        self._setup_components()
        
        logger.info(f"趋势跟踪策略 {self.name} 初始化完成")
    
    def _setup_components(self):
        """设置策略的三个核心组件"""
        
        # 1. 方向分析器 - 使用多指标分析器
        direction_analyzer = MultiIndicatorDirectionAnalyzer(
            rsi_period=self.get_parameter('rsi_period'),
            macd_fast=self.get_parameter('macd_fast'),
            macd_slow=self.get_parameter('macd_slow'),
            macd_signal=self.get_parameter('macd_signal')
        )
        
        # 2. 位置管理器 - 使用ATR位置管理器
        position_manager = ATRPositionManager(
            atr_period=self.get_parameter('atr_period'),
            entry_atr_multiplier=self.get_parameter('atr_entry_multiplier'),
            stop_atr_multiplier=self.get_parameter('atr_stop_multiplier'),
            target_atr_multiplier=self.get_parameter('atr_target_multiplier')
        )
        
        # 3. 信号生成器 - 使用价格行为信号生成器
        signal_generator = PriceActionSignalGenerator(
            min_confidence=self.get_parameter('min_signal_confidence'),
            price_tolerance=self.get_parameter('price_tolerance'),
            volume_confirmation=self.get_parameter('volume_confirmation')
        )
        
        # 设置组件
        self.set_components(direction_analyzer, position_manager, signal_generator)
    
    def calculate_custom_indicators(self):
        """计算策略专用的技术指标"""
        if len(self.bar_df) < 30:
            return
        
        try:
            # 移动平均线
            short_period = self.get_parameter('ma_short_period')
            long_period = self.get_parameter('ma_long_period')
            
            self.indicators['ma_short'] = self.bar_df['close'].rolling(window=short_period).mean().tolist()
            self.indicators['ma_long'] = self.bar_df['close'].rolling(window=long_period).mean().tolist()
            
            # ATR
            atr_period = self.get_parameter('atr_period')
            if len(self.bar_df) >= atr_period:
                high = self.bar_df['high'].values
                low = self.bar_df['low'].values
                close = self.bar_df['close'].values
                
                # 计算真实范围
                tr1 = high - low
                tr2 = np.abs(high - np.roll(close, 1))
                tr3 = np.abs(low - np.roll(close, 1))
                
                tr = np.maximum(tr1, np.maximum(tr2, tr3))
                atr = pd.Series(tr).rolling(window=atr_period).mean().tolist()
                
                self.indicators['atr'] = atr
            
            # RSI (简化版本)
            rsi_period = self.get_parameter('rsi_period')
            if len(self.bar_df) >= rsi_period:
                price_changes = self.bar_df['close'].diff()
                gains = price_changes.where(price_changes > 0, 0)
                losses = -price_changes.where(price_changes < 0, 0)
                
                avg_gains = gains.rolling(window=rsi_period).mean()
                avg_losses = losses.rolling(window=rsi_period).mean()
                
                rs = avg_gains / avg_losses
                rsi = 100 - (100 / (1 + rs))
                
                self.indicators['rsi'] = rsi.tolist()
            
        except Exception as e:
            logger.error(f"自定义指标计算失败: {e}")

class BreakoutStrategy(ThreePrincipleStrategy):
    """
    突破策略
    - 方向：基于趋势线分析判断突破方向
    - 位置：使用支撑阻力位管理入场和出场
    - 信号：基于突破信号生成器
    """
    
    def __init__(self, name: str = "突破策略", symbol: str = "AAPL", parameters: Dict[str, Any] = None):
        # 默认参数
        default_params = {
            # 方向分析参数
            'trendline_lookback': 20,
            'min_touches': 2,
            'slope_threshold': 0.001,
            
            # 位置管理参数
            'sr_lookback_period': 20,
            'sr_min_touches': 2,
            'entry_buffer': 0.002,
            'exit_buffer': 0.003,
            
            # 信号生成参数
            'breakout_threshold': 0.003,
            'volume_multiplier': 1.5,
            'confirmation_periods': 2,
            
            # 风险管理参数
            'max_position_size': 1.0,
            'risk_per_trade': 0.015,
            'account_balance': 100000,
            'volume': 1.0
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name, symbol, default_params)
        
        # 初始化组件
        self._setup_breakout_components()
        
        logger.info(f"突破策略 {self.name} 初始化完成")
    
    def _setup_breakout_components(self):
        """设置突破策略的三个核心组件"""
        
        # 1. 方向分析器 - 使用趋势线分析器
        from .components.direction_analyzers import TrendlineDirectionAnalyzer
        
        direction_analyzer = TrendlineDirectionAnalyzer(
            lookback_period=self.get_parameter('trendline_lookback'),
            min_touches=self.get_parameter('min_touches'),
            slope_threshold=self.get_parameter('slope_threshold')
        )
        
        # 2. 位置管理器 - 使用支撑阻力位管理器
        position_manager = SupportResistancePositionManager(
            lookback_period=self.get_parameter('sr_lookback_period'),
            min_touches=self.get_parameter('sr_min_touches'),
            entry_buffer=self.get_parameter('entry_buffer'),
            exit_buffer=self.get_parameter('exit_buffer')
        )
        
        # 3. 信号生成器 - 使用突破信号生成器
        signal_generator = BreakoutSignalGenerator(
            breakout_threshold=self.get_parameter('breakout_threshold'),
            volume_multiplier=self.get_parameter('volume_multiplier'),
            confirmation_periods=self.get_parameter('confirmation_periods')
        )
        
        # 设置组件
        self.set_components(direction_analyzer, position_manager, signal_generator)
    
    def calculate_custom_indicators(self):
        """计算突破策略专用指标"""
        if len(self.bar_df) < 10:
            return
        
        try:
            # 计算支撑阻力位强度
            lookback = min(20, len(self.bar_df))
            recent_df = self.bar_df.tail(lookback)
            
            # 高低点统计
            highs = recent_df['high'].values
            lows = recent_df['low'].values
            
            self.indicators['recent_high'] = np.max(highs)
            self.indicators['recent_low'] = np.min(lows)
            self.indicators['price_range'] = self.indicators['recent_high'] - self.indicators['recent_low']
            
            # 波动率指标
            price_changes = self.bar_df['close'].pct_change()
            volatility = price_changes.rolling(window=10).std() * np.sqrt(252)  # 年化波动率
            self.indicators['volatility'] = volatility.tolist()
            
        except Exception as e:
            logger.error(f"突破策略指标计算失败: {e}")

class MeanReversionStrategy(ThreePrincipleStrategy):
    """
    均值回归策略
    - 方向：基于超买超卖判断反转方向
    - 位置：使用斐波那契回撤位
    - 信号：基于价格偏离均值的程度生成信号
    """
    
    def __init__(self, name: str = "均值回归策略", symbol: str = "000001.SZ", parameters: Dict[str, Any] = None):
        # 默认参数
        default_params = {
            # 方向分析参数
            'ma_period': 20,
            'bollinger_std': 2.0,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            
            # 位置管理参数
            'fib_swing_period': 20,
            'fib_levels': [0.236, 0.382, 0.5, 0.618, 0.786],
            
            # 信号生成参数
            'mean_reversion_threshold': 0.02,  # 2%偏离
            'min_confidence': 0.65,
            
            # 风险管理参数
            'max_position_size': 1.0,
            'risk_per_trade': 0.01,
            'account_balance': 100000,
            'volume': 1.0
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name, symbol, default_params)
        
        # 自定义信号生成器
        self._setup_mean_reversion_components()
        
        logger.info(f"均值回归策略 {self.name} 初始化完成")
    
    def _setup_mean_reversion_components(self):
        """设置均值回归策略组件"""
        
        # 1. 方向分析器 - 修改为反转逻辑的多指标分析器
        direction_analyzer = MultiIndicatorDirectionAnalyzer(
            rsi_period=self.get_parameter('rsi_period')
        )
        
        # 2. 位置管理器 - 使用斐波那契位置管理器
        from .components.position_managers import FibonacciPositionManager
        
        position_manager = FibonacciPositionManager(
            swing_period=self.get_parameter('fib_swing_period'),
            fib_levels=self.get_parameter('fib_levels')
        )
        
        # 3. 自定义均值回归信号生成器
        signal_generator = MeanReversionSignalGenerator(
            min_confidence=self.get_parameter('min_confidence'),
            mean_reversion_threshold=self.get_parameter('mean_reversion_threshold')
        )
        
        # 设置组件
        self.set_components(direction_analyzer, position_manager, signal_generator)
    
    def calculate_custom_indicators(self):
        """计算均值回归策略指标"""
        if len(self.bar_df) < 20:
            return
        
        try:
            ma_period = self.get_parameter('ma_period')
            bollinger_std = self.get_parameter('bollinger_std')
            
            # 布林带
            sma = self.bar_df['close'].rolling(window=ma_period).mean()
            std = self.bar_df['close'].rolling(window=ma_period).std()
            
            self.indicators['bollinger_upper'] = (sma + bollinger_std * std).tolist()
            self.indicators['bollinger_lower'] = (sma - bollinger_std * std).tolist()
            self.indicators['bollinger_middle'] = sma.tolist()
            
            # 价格偏离度
            current_price = self.bar_df['close'].iloc[-1]
            current_sma = sma.iloc[-1]
            
            self.indicators['price_deviation'] = (current_price - current_sma) / current_sma if current_sma > 0 else 0
            
        except Exception as e:
            logger.error(f"均值回归策略指标计算失败: {e}")

class MeanReversionSignalGenerator(PriceActionSignalGenerator):
    """均值回归信号生成器"""
    
    def __init__(self, min_confidence: float = 0.65, mean_reversion_threshold: float = 0.02, **kwargs):
        super().__init__(min_confidence, **kwargs)
        self.mean_reversion_threshold = mean_reversion_threshold
    
    def _analyze_price_action(self, df: pd.DataFrame, direction: TrendDirection, entry_price: float) -> float:
        """重写价格行为分析，适用于均值回归"""
        if len(df) < 20:
            return 0.0
        
        # 计算价格相对于移动平均线的偏离
        sma = df['close'].rolling(window=20).mean()
        current_price = df['close'].iloc[-1]
        current_sma = sma.iloc[-1]
        
        if current_sma <= 0:
            return 0.0
        
        price_deviation = (current_price - current_sma) / current_sma
        
        # 均值回归逻辑：价格偏离越大，回归概率越高
        if direction == TrendDirection.UP and price_deviation < -self.mean_reversion_threshold:
            # 价格低于均值，看涨回归
            return min(0.9, 0.5 + abs(price_deviation) * 10)
        elif direction == TrendDirection.DOWN and price_deviation > self.mean_reversion_threshold:
            # 价格高于均值，看跌回归
            return min(0.9, 0.5 + abs(price_deviation) * 10)
        
        return 0.3