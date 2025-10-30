"""
信号生成器实现
根据方向和位置信息生成具体的交易信号
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from ..three_principle_strategy import (
    SignalGenerator, TrendDirection, SignalType, TradingSignal, Position
)

class PriceActionSignalGenerator(SignalGenerator):
    """基于价格行为的信号生成器"""
    
    def __init__(self, min_confidence: float = 0.6, price_tolerance: float = 0.001, 
                 volume_confirmation: bool = True, **kwargs):
        self.min_confidence = min_confidence        # 最小信号置信度
        self.price_tolerance = price_tolerance      # 价格容忍度 0.1%
        self.volume_confirmation = volume_confirmation  # 是否需要成交量确认
        
        logger.info(f"价格行为信号生成器初始化: 最小置信度{min_confidence}")
    
    def generate_signal(self, df: pd.DataFrame, direction: TrendDirection, 
                       entry_levels: Dict[str, float], exit_levels: Dict[str, float],
                       current_position: Optional[Position] = None, **kwargs) -> TradingSignal:
        """生成基于价格行为的交易信号"""
        
        if len(df) < 3:
            return self._create_no_signal(df)
        
        try:
            current_price = df['close'].iloc[-1]
            current_time = pd.to_datetime(df.index[-1]) if hasattr(df.index[-1], 'to_pydatetime') else datetime.now()
            
            # 如果有持仓，优先检查出场信号
            if current_position is not None:
                exit_signal = self._check_exit_signals(
                    df, current_position, exit_levels, current_price, current_time
                )
                if exit_signal.signal_type != SignalType.NO_SIGNAL:
                    return exit_signal
            
            # 检查入场信号
            if not entry_levels:
                return self._create_no_signal(df)
            
            entry_signal = self._check_entry_signals(
                df, direction, entry_levels, current_price, current_time
            )
            
            return entry_signal
            
        except Exception as e:
            logger.error(f"价格行为信号生成失败: {e}")
            return self._create_no_signal(df)
    
    def _check_exit_signals(self, df: pd.DataFrame, position: Position, 
                          exit_levels: Dict[str, float], current_price: float, 
                          current_time: datetime) -> TradingSignal:
        """检查出场信号"""
        
        # 止损检查
        if 'stop_loss' in exit_levels:
            if self._is_stop_loss_triggered(position, current_price, exit_levels['stop_loss']):
                return TradingSignal(
                    signal_type=SignalType.EXIT_LONG if position.direction == "LONG" else SignalType.EXIT_SHORT,
                    symbol=position.symbol,
                    price=current_price,
                    volume=position.size,
                    timestamp=current_time,
                    confidence=0.9,
                    reason="止损触发"
                )
        
        # 止盈检查
        if 'take_profit' in exit_levels:
            if self._is_take_profit_reached(position, current_price, exit_levels['take_profit']):
                return TradingSignal(
                    signal_type=SignalType.EXIT_LONG if position.direction == "LONG" else SignalType.EXIT_SHORT,
                    symbol=position.symbol,
                    price=current_price,
                    volume=position.size,
                    timestamp=current_time,
                    confidence=0.8,
                    reason="止盈触发"
                )
        
        # 追踪止损检查
        if 'trailing_stop' in exit_levels:
            if self._is_trailing_stop_triggered(position, current_price, exit_levels['trailing_stop']):
                return TradingSignal(
                    signal_type=SignalType.EXIT_LONG if position.direction == "LONG" else SignalType.EXIT_SHORT,
                    symbol=position.symbol,
                    price=current_price,
                    volume=position.size,
                    timestamp=current_time,
                    confidence=0.85,
                    reason="追踪止损触发"
                )
        
        # 趋势反转检查
        reversal_confidence = self._check_trend_reversal(df, position)
        if reversal_confidence > 0.7:
            return TradingSignal(
                signal_type=SignalType.EXIT_LONG if position.direction == "LONG" else SignalType.EXIT_SHORT,
                symbol=position.symbol,
                price=current_price,
                volume=position.size,
                timestamp=current_time,
                confidence=reversal_confidence,
                reason="趋势反转信号"
            )
        
        return self._create_no_signal(df)
    
    def _check_entry_signals(self, df: pd.DataFrame, direction: TrendDirection,
                           entry_levels: Dict[str, float], current_price: float,
                           current_time: datetime) -> TradingSignal:
        """检查入场信号"""
        
        entry_price = entry_levels.get('entry_price')
        if entry_price is None:
            return self._create_no_signal(df)
        
        # 价格触及入场位检查
        if not self._is_price_near_level(current_price, entry_price, self.price_tolerance):
            return self._create_no_signal(df)
        
        # 价格行为确认
        price_action_confidence = self._analyze_price_action(df, direction, entry_price)
        if price_action_confidence < self.min_confidence:
            return self._create_no_signal(df)
        
        # 成交量确认
        volume_confidence = 1.0
        if self.volume_confirmation and 'volume' in df.columns:
            volume_confidence = self._analyze_volume_confirmation(df, direction)
        
        # 综合置信度
        total_confidence = (price_action_confidence + volume_confidence) / 2
        
        if total_confidence < self.min_confidence:
            return self._create_no_signal(df)
        
        # 生成入场信号
        if direction == TrendDirection.UP:
            signal_type = SignalType.ENTRY_LONG
        elif direction == TrendDirection.DOWN:
            signal_type = SignalType.ENTRY_SHORT
        else:
            return self._create_no_signal(df)
        
        return TradingSignal(
            signal_type=signal_type,
            symbol=df.get('symbol', 'UNKNOWN'),
            price=entry_price,
            volume=1.0,  # 默认数量，实际由风险管理确定
            timestamp=current_time,
            confidence=total_confidence,
            stop_loss=entry_levels.get('stop_loss'),
            take_profit=entry_levels.get('take_profit'),
            reason=f"价格行为确认{direction.value}信号"
        )
    
    def _is_stop_loss_triggered(self, position: Position, current_price: float, 
                              stop_loss: float) -> bool:
        """检查是否触发止损"""
        if position.direction == "LONG":
            return current_price <= stop_loss
        elif position.direction == "SHORT":
            return current_price >= stop_loss
        return False
    
    def _is_take_profit_reached(self, position: Position, current_price: float,
                              take_profit: float) -> bool:
        """检查是否达到止盈"""
        if position.direction == "LONG":
            return current_price >= take_profit
        elif position.direction == "SHORT":
            return current_price <= take_profit
        return False
    
    def _is_trailing_stop_triggered(self, position: Position, current_price: float,
                                  trailing_stop: float) -> bool:
        """检查是否触发追踪止损"""
        return self._is_stop_loss_triggered(position, current_price, trailing_stop)
    
    def _is_price_near_level(self, current_price: float, target_price: float, 
                           tolerance: float) -> bool:
        """检查价格是否接近目标位"""
        return abs(current_price - target_price) / target_price <= tolerance
    
    def _analyze_price_action(self, df: pd.DataFrame, direction: TrendDirection,
                            entry_price: float) -> float:
        """分析价格行为模式"""
        if len(df) < 3:
            return 0.0
        
        # 获取最近几根K线
        recent_bars = df.tail(3)
        
        confidence = 0.5  # 基础置信度
        
        # 检查K线形态
        if direction == TrendDirection.UP:
            confidence += self._check_bullish_patterns(recent_bars)
        elif direction == TrendDirection.DOWN:
            confidence += self._check_bearish_patterns(recent_bars)
        
        # 检查价格动量
        momentum_score = self._calculate_momentum_score(df, direction)
        confidence += momentum_score * 0.3
        
        return min(confidence, 1.0)
    
    def _check_bullish_patterns(self, bars: pd.DataFrame) -> float:
        """检查看涨模式"""
        score = 0.0
        
        if len(bars) < 2:
            return score
        
        current = bars.iloc[-1]
        previous = bars.iloc[-2]
        
        # 阳线
        if current['close'] > current['open']:
            score += 0.2
        
        # 价格上涨
        if current['close'] > previous['close']:
            score += 0.2
        
        # 低点抬高
        if current['low'] > previous['low']:
            score += 0.1
        
        # 实体增大
        current_body = abs(current['close'] - current['open'])
        previous_body = abs(previous['close'] - previous['open'])
        if current_body > previous_body:
            score += 0.1
        
        return score
    
    def _check_bearish_patterns(self, bars: pd.DataFrame) -> float:
        """检查看跌模式"""
        score = 0.0
        
        if len(bars) < 2:
            return score
        
        current = bars.iloc[-1]
        previous = bars.iloc[-2]
        
        # 阴线
        if current['close'] < current['open']:
            score += 0.2
        
        # 价格下跌
        if current['close'] < previous['close']:
            score += 0.2
        
        # 高点降低
        if current['high'] < previous['high']:
            score += 0.1
        
        # 实体增大
        current_body = abs(current['close'] - current['open'])
        previous_body = abs(previous['close'] - previous['open'])
        if current_body > previous_body:
            score += 0.1
        
        return score
    
    def _calculate_momentum_score(self, df: pd.DataFrame, direction: TrendDirection) -> float:
        """计算动量评分"""
        if len(df) < 5:
            return 0.0
        
        # 计算价格变化率
        price_changes = df['close'].pct_change().tail(5)
        
        if direction == TrendDirection.UP:
            # 上涨动量：正收益率占比
            positive_changes = price_changes[price_changes > 0]
            return len(positive_changes) / len(price_changes)
        elif direction == TrendDirection.DOWN:
            # 下跌动量：负收益率占比
            negative_changes = price_changes[price_changes < 0]
            return len(negative_changes) / len(price_changes)
        
        return 0.0
    
    def _analyze_volume_confirmation(self, df: pd.DataFrame, direction: TrendDirection) -> float:
        """分析成交量确认"""
        if len(df) < 3:
            return 0.5
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].tail(5).mean()
        
        # 成交量放大
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        if volume_ratio > 1.5:  # 放量50%以上
            return 0.8
        elif volume_ratio > 1.2:  # 放量20%以上
            return 0.6
        else:
            return 0.4
    
    def _check_trend_reversal(self, df: pd.DataFrame, position: Position) -> float:
        """检查趋势反转信号"""
        if len(df) < 5:
            return 0.0
        
        # 简单的反转检测：连续相反方向的K线
        recent_bars = df.tail(3)
        
        if position.direction == "LONG":
            # 检查连续下跌
            consecutive_down = 0
            for i in range(len(recent_bars)):
                if recent_bars.iloc[i]['close'] < recent_bars.iloc[i]['open']:
                    consecutive_down += 1
                else:
                    break
            
            return consecutive_down / len(recent_bars)
        
        elif position.direction == "SHORT":
            # 检查连续上涨
            consecutive_up = 0
            for i in range(len(recent_bars)):
                if recent_bars.iloc[i]['close'] > recent_bars.iloc[i]['open']:
                    consecutive_up += 1
                else:
                    break
            
            return consecutive_up / len(recent_bars)
        
        return 0.0
    
    def _create_no_signal(self, df: pd.DataFrame) -> TradingSignal:
        """创建无信号"""
        current_time = pd.to_datetime(df.index[-1]) if len(df) > 0 else datetime.now()
        
        return TradingSignal(
            signal_type=SignalType.NO_SIGNAL,
            symbol="",
            price=0.0,
            volume=0.0,
            timestamp=current_time,
            confidence=0.0,
            reason="无信号条件满足"
        )

class BreakoutSignalGenerator(SignalGenerator):
    """基于突破的信号生成器"""
    
    def __init__(self, breakout_threshold: float = 0.002, volume_multiplier: float = 1.5,
                 confirmation_periods: int = 2, **kwargs):
        self.breakout_threshold = breakout_threshold    # 突破阈值 0.2%
        self.volume_multiplier = volume_multiplier      # 成交量倍数
        self.confirmation_periods = confirmation_periods # 确认周期
        
        logger.info(f"突破信号生成器初始化: 阈值{breakout_threshold*100}%, 成交量{volume_multiplier}x")
    
    def generate_signal(self, df: pd.DataFrame, direction: TrendDirection, 
                       entry_levels: Dict[str, float], exit_levels: Dict[str, float],
                       current_position: Optional[Position] = None, **kwargs) -> TradingSignal:
        """生成基于突破的交易信号"""
        
        if len(df) < 10:
            return self._create_no_signal()
        
        try:
            current_price = df['close'].iloc[-1]
            current_time = pd.to_datetime(df.index[-1]) if hasattr(df.index[-1], 'to_pydatetime') else datetime.now()
            
            # 如果有持仓，检查出场信号
            if current_position is not None:
                exit_signal = self._check_breakout_exit_signals(
                    df, current_position, current_price, current_time
                )
                if exit_signal.signal_type != SignalType.NO_SIGNAL:
                    return exit_signal
            
            # 检查突破入场信号
            if not entry_levels:
                return self._create_no_signal()
            
            breakout_signal = self._check_breakout_entry_signals(
                df, direction, entry_levels, current_price, current_time
            )
            
            return breakout_signal
            
        except Exception as e:
            logger.error(f"突破信号生成失败: {e}")
            return self._create_no_signal()
    
    def _check_breakout_entry_signals(self, df: pd.DataFrame, direction: TrendDirection,
                                    entry_levels: Dict[str, float], current_price: float,
                                    current_time: datetime) -> TradingSignal:
        """检查突破入场信号"""
        
        # 计算关键价位（阻力/支撑位）
        key_levels = self._identify_key_levels(df)
        
        if not key_levels:
            return self._create_no_signal()
        
        # 检查突破
        breakout_info = self._detect_breakout(df, key_levels, direction)
        
        if not breakout_info['is_breakout']:
            return self._create_no_signal()
        
        # 成交量确认
        volume_confirmed = self._confirm_breakout_volume(df)
        if not volume_confirmed:
            return self._create_no_signal()
        
        # 价格确认（避免假突破）
        price_confirmed = self._confirm_breakout_price(df, breakout_info, direction)
        confidence = 0.6 + (0.3 * price_confirmed)
        
        # 生成信号
        if direction == TrendDirection.UP:
            signal_type = SignalType.ENTRY_LONG
        elif direction == TrendDirection.DOWN:
            signal_type = SignalType.ENTRY_SHORT
        else:
            return self._create_no_signal()
        
        return TradingSignal(
            signal_type=signal_type,
            symbol=df.get('symbol', 'UNKNOWN'),
            price=current_price,
            volume=1.0,
            timestamp=current_time,
            confidence=confidence,
            stop_loss=entry_levels.get('stop_loss'),
            take_profit=entry_levels.get('take_profit'),
            reason=f"突破{breakout_info['level']:.2f}确认"
        )
    
    def _check_breakout_exit_signals(self, df: pd.DataFrame, position: Position,
                                   current_price: float, current_time: datetime) -> TradingSignal:
        """检查突破出场信号"""
        
        # 检查假突破回撤
        false_breakout = self._detect_false_breakout(df, position)
        
        if false_breakout > 0.7:
            return TradingSignal(
                signal_type=SignalType.EXIT_LONG if position.direction == "LONG" else SignalType.EXIT_SHORT,
                symbol=position.symbol,
                price=current_price,
                volume=position.size,
                timestamp=current_time,
                confidence=false_breakout,
                reason="假突破回撤"
            )
        
        return self._create_no_signal()
    
    def _identify_key_levels(self, df: pd.DataFrame) -> List[float]:
        """识别关键价格水平"""
        lookback = min(20, len(df))
        recent_df = df.tail(lookback)
        
        key_levels = []
        
        # 找到局部高低点
        for i in range(1, len(recent_df) - 1):
            current_high = recent_df.iloc[i]['high']
            current_low = recent_df.iloc[i]['low']
            
            prev_high = recent_df.iloc[i-1]['high']
            prev_low = recent_df.iloc[i-1]['low']
            
            next_high = recent_df.iloc[i+1]['high']
            next_low = recent_df.iloc[i+1]['low']
            
            # 局部最高点
            if current_high >= prev_high and current_high >= next_high:
                key_levels.append(current_high)
            
            # 局部最低点
            if current_low <= prev_low and current_low <= next_low:
                key_levels.append(current_low)
        
        # 去重并排序
        key_levels = sorted(list(set(key_levels)))
        
        return key_levels
    
    def _detect_breakout(self, df: pd.DataFrame, key_levels: List[float],
                        direction: TrendDirection) -> Dict[str, Any]:
        """检测突破"""
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        
        breakout_info = {'is_breakout': False, 'level': None, 'direction': None}
        
        for level in key_levels:
            # 向上突破
            if (direction == TrendDirection.UP and 
                prev_price <= level and 
                current_price > level * (1 + self.breakout_threshold)):
                
                breakout_info = {
                    'is_breakout': True,
                    'level': level,
                    'direction': 'UP',
                    'strength': (current_price - level) / level
                }
                break
            
            # 向下突破
            elif (direction == TrendDirection.DOWN and 
                  prev_price >= level and 
                  current_price < level * (1 - self.breakout_threshold)):
                
                breakout_info = {
                    'is_breakout': True,
                    'level': level,
                    'direction': 'DOWN',
                    'strength': (level - current_price) / level
                }
                break
        
        return breakout_info
    
    def _confirm_breakout_volume(self, df: pd.DataFrame) -> bool:
        """确认突破成交量"""
        if 'volume' not in df.columns:
            return True  # 没有成交量数据时默认通过
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].tail(10).mean()
        
        return current_volume > avg_volume * self.volume_multiplier
    
    def _confirm_breakout_price(self, df: pd.DataFrame, breakout_info: Dict[str, Any],
                              direction: TrendDirection) -> float:
        """确认突破价格动作"""
        if len(df) < self.confirmation_periods + 1:
            return 0.5
        
        confirmation_score = 0.0
        recent_bars = df.tail(self.confirmation_periods + 1)
        
        for i in range(1, len(recent_bars)):
            current_bar = recent_bars.iloc[i]
            
            if breakout_info['direction'] == 'UP':
                # 确认持续在突破位上方
                if current_bar['close'] > breakout_info['level']:
                    confirmation_score += 1.0 / self.confirmation_periods
            elif breakout_info['direction'] == 'DOWN':
                # 确认持续在突破位下方
                if current_bar['close'] < breakout_info['level']:
                    confirmation_score += 1.0 / self.confirmation_periods
        
        return confirmation_score
    
    def _detect_false_breakout(self, df: pd.DataFrame, position: Position) -> float:
        """检测假突破"""
        # 简单检测：价格是否快速回到入场价附近
        current_price = df['close'].iloc[-1]
        entry_price = position.entry_price
        
        if position.direction == "LONG":
            # 多头假突破：价格跌回入场价下方
            if current_price < entry_price * (1 - self.breakout_threshold):
                return 0.8
        elif position.direction == "SHORT":
            # 空头假突破：价格涨回入场价上方
            if current_price > entry_price * (1 + self.breakout_threshold):
                return 0.8
        
        return 0.0
    
    def _create_no_signal(self) -> TradingSignal:
        """创建无信号"""
        return TradingSignal(
            signal_type=SignalType.NO_SIGNAL,
            symbol="",
            price=0.0,
            volume=0.0,
            timestamp=datetime.now(),
            confidence=0.0,
            reason="无突破信号"
        )