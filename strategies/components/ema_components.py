"""
EMA趋势跟随策略专用组件
实现基于EMA20/EMA60 + ADX的改进版趋势跟随策略
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from loguru import logger

from ..three_principle_strategy import DirectionAnalyzer, PositionManager, SignalGenerator, TrendDirection, TradingSignal, SignalType, Position
from ..indicators import (
    calculate_ema, calculate_adx, calculate_average_range, calculate_recent_avg_body,
    is_ema_trending_up, is_ema_trending_down, check_price_pullback_to_ema,
    check_historical_position_above_ema, check_historical_position_below_ema,
    detect_long_lower_shadow, detect_long_upper_shadow, 
    detect_strong_bullish_candle, detect_strong_bearish_candle
)


class EMADirectionAnalyzer(DirectionAnalyzer):
    """基于EMA20/EMA60 + ADX的方向分析器"""
    
    def __init__(self, ema_short: int = 20, ema_long: int = 60, adx_period: int = 14, 
                 adx_threshold: float = 25.0, **kwargs):
        self.ema_short_period = ema_short
        self.ema_long_period = ema_long
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        
        self.direction_confidence = 0.0
        self.current_adx = 0.0
        self.ema20_direction = TrendDirection.UNKNOWN
        self.ema60_direction = TrendDirection.UNKNOWN
        
        logger.info(f"EMA方向分析器初始化: EMA{ema_short}/{ema_long}, ADX({adx_period})>{adx_threshold}")
    
    def analyze_direction(self, df: pd.DataFrame, **kwargs) -> TrendDirection:
        """基于EMA和ADX分析趋势方向"""
        if len(df) < max(self.ema_long_period, self.adx_period) + 10:
            self.direction_confidence = 0.0
            return TrendDirection.UNKNOWN
        
        try:
            # 计算EMA
            ema20 = calculate_ema(df['close'], self.ema_short_period)
            ema60 = calculate_ema(df['close'], self.ema_long_period)
            
            # 计算ADX
            adx, plus_di, minus_di = calculate_adx(df['high'], df['low'], df['close'], self.adx_period)
            self.current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0.0
            
            # 第一步：ADX过滤 - 趋势强度必须足够
            if self.current_adx <= self.adx_threshold:
                self.direction_confidence = 0.0
                self.ema20_direction = TrendDirection.SIDEWAYS
                self.ema60_direction = TrendDirection.SIDEWAYS
                logger.debug(f"ADX={self.current_adx:.2f} <= {self.adx_threshold}, 无趋势状态")
                return TrendDirection.SIDEWAYS
            
            # 第二步：判断EMA60主方向（多空分界线）
            ema60_is_up = is_ema_trending_up(ema60, lookback=3)
            ema60_is_down = is_ema_trending_down(ema60, lookback=3)
            
            if ema60_is_up:
                self.ema60_direction = TrendDirection.UP
                primary_direction = TrendDirection.UP
                logger.debug(f"EMA60向上，主趋势为多头")
            elif ema60_is_down:
                self.ema60_direction = TrendDirection.DOWN
                primary_direction = TrendDirection.DOWN
                logger.debug(f"EMA60向下，主趋势为空头")
            else:
                self.ema60_direction = TrendDirection.SIDEWAYS
                primary_direction = TrendDirection.SIDEWAYS
                logger.debug(f"EMA60方向不明确")
            
            # 第三步：检查EMA20交易趋势线方向
            ema20_is_up = is_ema_trending_up(ema20, lookback=3)
            ema20_is_down = is_ema_trending_down(ema20, lookback=3)
            
            if ema20_is_up:
                self.ema20_direction = TrendDirection.UP
            elif ema20_is_down:
                self.ema20_direction = TrendDirection.DOWN
            else:
                self.ema20_direction = TrendDirection.SIDEWAYS
            
            # 综合判断
            if primary_direction == TrendDirection.UP and self.ema20_direction == TrendDirection.UP:
                self.direction_confidence = 0.8 + (self.current_adx - self.adx_threshold) / 100.0
                final_direction = TrendDirection.UP
            elif primary_direction == TrendDirection.DOWN and self.ema20_direction == TrendDirection.DOWN:
                self.direction_confidence = 0.8 + (self.current_adx - self.adx_threshold) / 100.0
                final_direction = TrendDirection.DOWN
            else:
                self.direction_confidence = 0.3
                final_direction = TrendDirection.SIDEWAYS
            
            logger.debug(f"EMA方向分析: ADX={self.current_adx:.2f}, EMA20={self.ema20_direction.value}, "
                        f"EMA60={self.ema60_direction.value}, 最终={final_direction.value}, 置信度={self.direction_confidence:.2f}")
            
            return final_direction
            
        except Exception as e:
            logger.error(f"EMA方向分析失败: {e}")
            self.direction_confidence = 0.0
            return TrendDirection.UNKNOWN
    
    def get_direction_confidence(self) -> float:
        """获取方向判断置信度"""
        return self.direction_confidence
    
    def get_ema_values(self, df: pd.DataFrame) -> Dict[str, float]:
        """获取当前EMA值"""
        try:
            ema20 = calculate_ema(df['close'], self.ema_short_period)
            ema60 = calculate_ema(df['close'], self.ema_long_period)
            
            return {
                'ema20': ema20.iloc[-1] if len(ema20) > 0 else 0.0,
                'ema60': ema60.iloc[-1] if len(ema60) > 0 else 0.0,
                'adx': self.current_adx
            }
        except:
            return {'ema20': 0.0, 'ema60': 0.0, 'adx': 0.0}


class EMAPullbackPositionManager(PositionManager):
    """基于EMA回踩的位置管理器"""
    
    def __init__(self, lookback_candles: int = 4, pullback_threshold: float = 0.5,
                 risk_reward_ratio: float = 2.0, **kwargs):
        self.lookback_candles = lookback_candles
        self.pullback_threshold = pullback_threshold
        self.risk_reward_ratio = risk_reward_ratio
        
        logger.info(f"EMA回踩位置管理器初始化: 回看{lookback_candles}根K线, 阈值{pullback_threshold}")
    
    def calculate_entry_position(self, df: pd.DataFrame, direction: TrendDirection, **kwargs) -> Dict[str, float]:
        """计算基于EMA回踩的入场位置"""
        if len(df) < 60:  # 确保有足够数据计算EMA60
            return {}
        
        try:
            current_bar = df.iloc[-1]
            
            # 计算EMA值
            ema20 = calculate_ema(df['close'], 20)
            ema60 = calculate_ema(df['close'], 60)
            
            # 计算平均振幅
            avg_range = calculate_average_range(df['high'], df['low'], 5)
            
            positions = {}
            
            if direction == TrendDirection.UP:
                # 做多：检查回踩EMA20或EMA60
                ema20_pullback = check_price_pullback_to_ema(
                    current_bar['low'], ema20.iloc[-1], avg_range, self.pullback_threshold
                )
                ema60_pullback = check_price_pullback_to_ema(
                    current_bar['low'], ema60.iloc[-1], avg_range, self.pullback_threshold
                )
                
                if ema20_pullback:
                    entry_ema = ema20.iloc[-1]
                    ema_name = "EMA20"
                    # 历史位置验证：前4根K线收盘价都在EMA20上方
                    history_ok = check_historical_position_above_ema(df['close'], ema20, self.lookback_candles)
                elif ema60_pullback:
                    entry_ema = ema60.iloc[-1]
                    ema_name = "EMA60"
                    # 历史位置验证：前4根K线收盘价都在EMA60上方
                    history_ok = check_historical_position_above_ema(df['close'], ema60, self.lookback_candles)
                else:
                    return {}
                
                if not history_ok:
                    logger.debug(f"做多历史位置验证失败：前{self.lookback_candles}根K线未全部在{ema_name}上方")
                    return {}
                
                # 入场价格：当前收盘价
                entry_price = current_bar['close']
                
                # 止损：开仓K线及前两根K线的最低点
                stop_loss_bars = df.iloc[-3:] if len(df) >= 3 else df
                stop_loss = stop_loss_bars['low'].min()
                
                # 风险计算
                risk = entry_price - stop_loss
                if risk <= 0:
                    return {}
                
                # 目标价格
                take_profit = entry_price + (risk * self.risk_reward_ratio)
                
                positions = {
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_ema': entry_ema,
                    'ema_name': ema_name,
                    'risk_amount': risk,
                    'avg_range': avg_range
                }
                
            elif direction == TrendDirection.DOWN:
                # 做空：检查回踩EMA20或EMA60
                ema20_pullback = check_price_pullback_to_ema(
                    current_bar['high'], ema20.iloc[-1], avg_range, self.pullback_threshold
                )
                ema60_pullback = check_price_pullback_to_ema(
                    current_bar['high'], ema60.iloc[-1], avg_range, self.pullback_threshold
                )
                
                if ema20_pullback:
                    entry_ema = ema20.iloc[-1]
                    ema_name = "EMA20"
                    # 历史位置验证：前4根K线收盘价都在EMA20下方
                    history_ok = check_historical_position_below_ema(df['close'], ema20, self.lookback_candles)
                elif ema60_pullback:
                    entry_ema = ema60.iloc[-1]
                    ema_name = "EMA60"
                    # 历史位置验证：前4根K线收盘价都在EMA60下方
                    history_ok = check_historical_position_below_ema(df['close'], ema60, self.lookback_candles)
                else:
                    return {}
                
                if not history_ok:
                    logger.debug(f"做空历史位置验证失败：前{self.lookback_candles}根K线未全部在{ema_name}下方")
                    return {}
                
                # 入场价格：当前收盘价
                entry_price = current_bar['close']
                
                # 止损：开仓K线及前两根K线的最高点
                stop_loss_bars = df.iloc[-3:] if len(df) >= 3 else df
                stop_loss = stop_loss_bars['high'].max()
                
                # 风险计算
                risk = stop_loss - entry_price
                if risk <= 0:
                    return {}
                
                # 目标价格
                take_profit = entry_price - (risk * self.risk_reward_ratio)
                
                positions = {
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_ema': entry_ema,
                    'ema_name': ema_name,
                    'risk_amount': risk,
                    'avg_range': avg_range
                }
            
            logger.debug(f"EMA回踩位置计算完成: {positions}")
            return positions
            
        except Exception as e:
            logger.error(f"EMA回踩位置计算失败: {e}")
            return {}
    
    def calculate_exit_position(self, df: pd.DataFrame, position: Position, **kwargs) -> Dict[str, float]:
        """计算动态出场位置（阶段性止盈）"""
        try:
            current_price = df['close'].iloc[-1]
            positions = {}
            
            # 检查是否达到第一阶段止盈条件（1:2盈亏比）
            if position.direction == "LONG":
                profit = current_price - position.entry_price
                initial_risk = position.entry_price - position.stop_loss if hasattr(position, 'stop_loss') else 0
                
                if initial_risk > 0 and profit >= (initial_risk * self.risk_reward_ratio):
                    # 达到2倍风险收益比，设置保本止损
                    positions['break_even_stop'] = position.entry_price
                    positions['partial_profit_level'] = current_price
                    
            elif position.direction == "SHORT":
                profit = position.entry_price - current_price
                initial_risk = position.stop_loss - position.entry_price if hasattr(position, 'stop_loss') else 0
                
                if initial_risk > 0 and profit >= (initial_risk * self.risk_reward_ratio):
                    # 达到2倍风险收益比，设置保本止损
                    positions['break_even_stop'] = position.entry_price
                    positions['partial_profit_level'] = current_price
            
            return positions
            
        except Exception as e:
            logger.error(f"EMA动态出场位置计算失败: {e}")
            return {}


class EMAPatternSignalGenerator(SignalGenerator):
    """基于EMA策略和K线形态的信号生成器"""
    
    def __init__(self, min_confidence: float = 0.7, body_threshold: float = 1.5, **kwargs):
        self.min_confidence = min_confidence
        self.body_threshold = body_threshold
        
        logger.info(f"EMA形态信号生成器初始化: 最小置信度{min_confidence}, 实体阈值{body_threshold}")
    
    def generate_signal(self, df: pd.DataFrame, direction: TrendDirection, 
                       entry_levels: Dict[str, float], exit_levels: Dict[str, float],
                       current_position: Optional[Position] = None, **kwargs) -> TradingSignal:
        """基于K线形态生成交易信号"""
        
        if len(df) < 20:
            return TradingSignal(
                signal_type=SignalType.NO_SIGNAL,
                confidence=0.0,
                price=0.0,
                reason="数据不足"
            )
        
        try:
            current_bar = df.iloc[-1]
            
            # 计算近期平均实体大小
            recent_avg_body = calculate_recent_avg_body(df['open'], df['close'], 10)
            
            signal_type = SignalType.NO_SIGNAL
            confidence = 0.0
            reason = "无信号条件满足"
            
            # 如果已有持仓，检查出场条件
            if current_position is not None:
                exit_signal = self._check_exit_conditions(df, current_position, entry_levels)
                if exit_signal.signal_type != SignalType.NO_SIGNAL:
                    return exit_signal
            
            # 检查入场条件
            if not entry_levels:
                return TradingSignal(signal_type=signal_type, confidence=confidence, 
                                   price=current_bar['close'], reason=reason)
            
            if direction == TrendDirection.UP:
                # 做多信号检测
                signal_type, confidence, reason = self._check_bullish_patterns(
                    current_bar, recent_avg_body
                )
                
            elif direction == TrendDirection.DOWN:
                # 做空信号检测
                signal_type, confidence, reason = self._check_bearish_patterns(
                    current_bar, recent_avg_body
                )
            
            # 只有置信度足够高才发出信号
            if confidence < self.min_confidence:
                signal_type = SignalType.NO_SIGNAL
                confidence = 0.0
                reason = f"置信度{confidence:.2f}低于阈值{self.min_confidence}"
            
            return TradingSignal(
                signal_type=signal_type,
                confidence=confidence,
                price=current_bar['close'],
                reason=reason
            )
            
        except Exception as e:
            logger.error(f"EMA信号生成失败: {e}")
            return TradingSignal(
                signal_type=SignalType.NO_SIGNAL,
                confidence=0.0,
                price=0.0,
                reason=f"生成失败: {e}"
            )
    
    def _check_bullish_patterns(self, current_bar: pd.Series, recent_avg_body: float) -> tuple:
        """检查看涨形态"""
        open_price = current_bar['open']
        high_price = current_bar['high'] 
        low_price = current_bar['low']
        close_price = current_bar['close']
        
        # 检查长下影线
        has_long_lower_shadow = detect_long_lower_shadow(open_price, high_price, low_price, close_price)
        
        # 检查强势大阳线
        has_strong_bullish = detect_strong_bullish_candle(open_price, close_price, recent_avg_body, self.body_threshold)
        
        if has_long_lower_shadow:
            return (SignalType.ENTRY_LONG, 0.8, "长下影线买入信号")
        elif has_strong_bullish:
            return (SignalType.ENTRY_LONG, 0.85, "强势大阳线买入信号") 
        else:
            return (SignalType.NO_SIGNAL, 0.0, "无看涨形态")
    
    def _check_bearish_patterns(self, current_bar: pd.Series, recent_avg_body: float) -> tuple:
        """检查看跌形态"""
        open_price = current_bar['open']
        high_price = current_bar['high']
        low_price = current_bar['low'] 
        close_price = current_bar['close']
        
        # 检查长上影线
        has_long_upper_shadow = detect_long_upper_shadow(open_price, high_price, low_price, close_price)
        
        # 检查强势大阴线
        has_strong_bearish = detect_strong_bearish_candle(open_price, close_price, recent_avg_body, self.body_threshold)
        
        if has_long_upper_shadow:
            return (SignalType.ENTRY_SHORT, 0.8, "长上影线卖出信号")
        elif has_strong_bearish:
            return (SignalType.ENTRY_SHORT, 0.85, "强势大阴线卖出信号")
        else:
            return (SignalType.NO_SIGNAL, 0.0, "无看跌形态")
    
    def _check_exit_conditions(self, df: pd.DataFrame, position: Position, entry_levels: Dict[str, float]) -> TradingSignal:
        """检查出场条件"""
        try:
            current_price = df['close'].iloc[-1]
            
            # 检查EMA转向出场条件
            ema_name = entry_levels.get('ema_name', 'EMA20')
            
            if ema_name == 'EMA20':
                ema_series = calculate_ema(df['close'], 20)
            else:
                ema_series = calculate_ema(df['close'], 60)
            
            if position.direction == "LONG":
                # 多头持仓：EMA转向下时出场
                if is_ema_trending_down(ema_series, lookback=3):
                    return TradingSignal(
                        signal_type=SignalType.EXIT_LONG,
                        confidence=0.9,
                        price=current_price,
                        reason=f"{ema_name}转向下，趋势出场"
                    )
            elif position.direction == "SHORT":
                # 空头持仓：EMA转向上时出场
                if is_ema_trending_up(ema_series, lookback=3):
                    return TradingSignal(
                        signal_type=SignalType.EXIT_SHORT,
                        confidence=0.9,
                        price=current_price,
                        reason=f"{ema_name}转向上，趋势出场"
                    )
            
            return TradingSignal(SignalType.NO_SIGNAL, 0.0, 0.0, "持仓中，无出场信号")
            
        except Exception as e:
            logger.error(f"出场条件检查失败: {e}")
            return TradingSignal(SignalType.NO_SIGNAL, 0.0, 0.0, f"出场检查失败: {e}")