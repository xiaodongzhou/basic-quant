"""
技术指标计算模块
包含EMA、ADX、ATR等常用技术指标的计算函数
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    计算指数移动平均线 (EMA)
    
    Args:
        data: 价格数据序列
        period: 计算周期
    
    Returns:
        EMA值序列
    """
    return data.ewm(span=period, adjust=False).mean()


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算平均方向指数 (ADX) 及相关指标
    
    Args:
        high: 最高价序列
        low: 最低价序列  
        close: 收盘价序列
        period: 计算周期，默认14
    
    Returns:
        Tuple[ADX, +DI, -DI]
    """
    # 计算真实范围 (True Range)
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # 计算方向性移动 (Directional Movement)
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    # 使用指数移动平均进行平滑（更稳定）
    alpha = 2.0 / (period + 1)
    
    # 计算平滑的TR和DM
    tr_smooth = pd.Series(tr).ewm(alpha=alpha, adjust=False).mean()
    plus_dm_smooth = pd.Series(plus_dm).ewm(alpha=alpha, adjust=False).mean()
    minus_dm_smooth = pd.Series(minus_dm).ewm(alpha=alpha, adjust=False).mean()
    
    # 计算方向性指标 (+DI, -DI)
    plus_di = 100 * (plus_dm_smooth / tr_smooth)
    minus_di = 100 * (minus_dm_smooth / tr_smooth)
    
    # 处理除零情况
    plus_di = plus_di.fillna(0)
    minus_di = minus_di.fillna(0)
    
    # 计算方向性移动指数 (DX)
    di_sum = plus_di + minus_di
    dx = np.where(di_sum > 0, 100 * np.abs(plus_di - minus_di) / di_sum, 0)
    
    # 计算平均方向指数 (ADX)
    adx = pd.Series(dx).ewm(alpha=alpha, adjust=False).mean()
    
    return adx, plus_di, minus_di


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    计算平均真实范围 (ATR)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 计算周期，默认14
    
    Returns:
        ATR值序列
    """
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    return pd.Series(tr).rolling(window=period).mean()


def is_ema_trending_up(ema_series: pd.Series, lookback: int = 3) -> bool:
    """
    判断EMA是否处于上升趋势
    
    Args:
        ema_series: EMA序列
        lookback: 回看周期数
    
    Returns:
        是否上升趋势
    """
    if len(ema_series) < lookback + 1:
        return False
    
    recent_values = ema_series.iloc[-lookback-1:]
    return recent_values.iloc[-1] > recent_values.iloc[0]


def is_ema_trending_down(ema_series: pd.Series, lookback: int = 3) -> bool:
    """
    判断EMA是否处于下降趋势
    
    Args:
        ema_series: EMA序列
        lookback: 回看周期数
    
    Returns:
        是否下降趋势
    """
    if len(ema_series) < lookback + 1:
        return False
    
    recent_values = ema_series.iloc[-lookback-1:]
    return recent_values.iloc[-1] < recent_values.iloc[0]


def calculate_average_range(high: pd.Series, low: pd.Series, period: int = 5) -> float:
    """
    计算前N根K线的平均振幅
    
    Args:
        high: 最高价序列
        low: 最低价序列
        period: 计算周期
    
    Returns:
        平均振幅值
    """
    if len(high) < period:
        return 0.0
    
    ranges = high.iloc[-period:] - low.iloc[-period:]
    return ranges.mean()


def detect_long_lower_shadow(open_price: float, high_price: float, low_price: float, close_price: float) -> bool:
    """
    检测长下影线
    判断条件：(开盘价 - 最低价) > (2 * |收盘价 - 开盘价|)
    
    Args:
        open_price: 开盘价
        high_price: 最高价
        low_price: 最低价
        close_price: 收盘价
    
    Returns:
        是否为长下影线
    """
    lower_shadow = open_price - low_price
    body_size = abs(close_price - open_price)
    
    return lower_shadow > (2 * body_size) and lower_shadow > 0


def detect_long_upper_shadow(open_price: float, high_price: float, low_price: float, close_price: float) -> bool:
    """
    检测长上影线
    判断条件：根据收盘价相对开盘价的位置选择不同计算方式
    
    Args:
        open_price: 开盘价
        high_price: 最高价
        low_price: 最低价
        close_price: 收盘价
    
    Returns:
        是否为长上影线
    """
    body_size = abs(close_price - open_price)
    
    if close_price >= open_price:
        # 阳线：(最高价 - 开盘价) > (2 * |收盘价 - 开盘价|)
        upper_shadow = high_price - open_price
    else:
        # 阴线：(最高价 - 收盘价) > (2 * |收盘价 - 开盘价|)
        upper_shadow = high_price - close_price
    
    return upper_shadow > (2 * body_size) and upper_shadow > 0


def detect_strong_bullish_candle(open_price: float, close_price: float, 
                                recent_avg_body: float, threshold: float = 1.5) -> bool:
    """
    检测强势大阳线
    
    Args:
        open_price: 开盘价
        close_price: 收盘价
        recent_avg_body: 近期K线平均实体大小
        threshold: 阈值倍数，默认1.5倍
    
    Returns:
        是否为强势大阳线
    """
    if close_price <= open_price:
        return False
    
    body_size = close_price - open_price
    return body_size > (recent_avg_body * threshold)


def detect_strong_bearish_candle(open_price: float, close_price: float, 
                                recent_avg_body: float, threshold: float = 1.5) -> bool:
    """
    检测强势大阴线
    
    Args:
        open_price: 开盘价
        close_price: 收盘价
        recent_avg_body: 近期K线平均实体大小
        threshold: 阈值倍数，默认1.5倍
    
    Returns:
        是否为强势大阴线
    """
    if close_price >= open_price:
        return False
    
    body_size = open_price - close_price
    return body_size > (recent_avg_body * threshold)


def calculate_recent_avg_body(open_series: pd.Series, close_series: pd.Series, period: int = 10) -> float:
    """
    计算近期K线平均实体大小
    
    Args:
        open_series: 开盘价序列
        close_series: 收盘价序列
        period: 计算周期
    
    Returns:
        平均实体大小
    """
    if len(open_series) < period:
        period = len(open_series)
    
    if period == 0:
        return 0.0
    
    recent_bodies = abs(close_series.iloc[-period:] - open_series.iloc[-period:])
    return recent_bodies.mean()


def check_price_pullback_to_ema(current_price: float, ema_value: float, 
                               avg_range: float, threshold: float = 0.5) -> bool:
    """
    检查价格是否回踩到EMA附近
    
    Args:
        current_price: 当前价格（最高价或最低价）
        ema_value: EMA值
        avg_range: 前5根K线平均振幅
        threshold: 阈值倍数，默认0.5
    
    Returns:
        是否回踩到EMA附近
    """
    distance = abs(current_price - ema_value)
    return distance < (avg_range * threshold)


def check_historical_position_above_ema(close_series: pd.Series, ema_series: pd.Series, 
                                       lookback: int = 4) -> bool:
    """
    检查历史位置是否在EMA上方（做多条件）
    
    Args:
        close_series: 收盘价序列
        ema_series: EMA序列
        lookback: 回看周期，默认4根K线
    
    Returns:
        是否满足历史位置条件
    """
    if len(close_series) < lookback or len(ema_series) < lookback:
        return False
    
    # 检查前4根K线的收盘价是否都在EMA上方
    for i in range(1, lookback + 1):
        if close_series.iloc[-1-i] <= ema_series.iloc[-1-i]:
            return False
    
    return True


def check_historical_position_below_ema(close_series: pd.Series, ema_series: pd.Series, 
                                       lookback: int = 4) -> bool:
    """
    检查历史位置是否在EMA下方（做空条件）
    
    Args:
        close_series: 收盘价序列
        ema_series: EMA序列
        lookback: 回看周期，默认4根K线
    
    Returns:
        是否满足历史位置条件
    """
    if len(close_series) < lookback or len(ema_series) < lookback:
        return False
    
    # 检查前4根K线的收盘价是否都在EMA下方
    for i in range(1, lookback + 1):
        if close_series.iloc[-1-i] >= ema_series.iloc[-1-i]:
            return False
    
    return True