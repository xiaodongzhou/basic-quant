#!/usr/bin/env python3
"""
数据类型定义模块
定义交易系统中使用的基础数据结构

基于VN.PY数据结构设计，保持兼容性
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class Exchange(Enum):
    """交易所枚举"""
    SHFE = "SHFE"      # 上海期货交易所
    DCE = "DCE"        # 大连商品交易所
    CZCE = "CZCE"      # 郑州商品交易所
    CFFEX = "CFFEX"    # 中国金融期货交易所
    INE = "INE"        # 上海国际能源交易中心

class Direction(Enum):
    """交易方向枚举"""
    LONG = "LONG"      # 多头
    SHORT = "SHORT"    # 空头

class Interval(Enum):
    """K线周期枚举"""
    TICK = "tick"      # Tick数据
    MINUTE = "1m"      # 1分钟
    MINUTE_5 = "5m"    # 5分钟
    MINUTE_15 = "15m"  # 15分钟
    HOUR = "1h"        # 1小时
    DAILY = "1d"       # 日线

@dataclass
class TickData:
    """
    Tick数据结构
    包含最基本的市场数据信息
    """
    symbol: str                    # 合约代码
    exchange: Exchange             # 交易所
    datetime: datetime             # 时间戳
    name: str                      # 合约名称
    volume: int                    # 成交量
    turnover: float               # 成交额
    open_interest: int            # 持仓量
    last_price: float             # 最新价
    
    # 价格限制
    limit_up: float = 0.0         # 涨停价
    limit_down: float = 0.0       # 跌停价
    
    # OHLC数据
    open_price: float = 0.0       # 开盘价
    high_price: float = 0.0       # 最高价
    low_price: float = 0.0        # 最低价
    pre_close: float = 0.0        # 昨收价
    
    # 买卖盘数据
    bid_price_1: float = 0.0      # 买一价
    bid_price_2: float = 0.0      # 买二价
    bid_price_3: float = 0.0      # 买三价
    bid_price_4: float = 0.0      # 买四价
    bid_price_5: float = 0.0      # 买五价
    
    ask_price_1: float = 0.0      # 卖一价
    ask_price_2: float = 0.0      # 卖二价
    ask_price_3: float = 0.0      # 卖三价
    ask_price_4: float = 0.0      # 卖四价
    ask_price_5: float = 0.0      # 卖五价
    
    bid_volume_1: int = 0         # 买一量
    bid_volume_2: int = 0         # 买二量
    bid_volume_3: int = 0         # 买三量
    bid_volume_4: int = 0         # 买四量
    bid_volume_5: int = 0         # 买五量
    
    ask_volume_1: int = 0         # 卖一量
    ask_volume_2: int = 0         # 卖二量
    ask_volume_3: int = 0         # 卖三量
    ask_volume_4: int = 0         # 卖四量
    ask_volume_5: int = 0         # 卖五量
    
    gateway_name: str = ""        # 网关名称
    localtime: Optional[datetime] = None  # 本地时间

@dataclass
class BarData:
    """
    K线数据结构
    包含OHLCV等标准K线信息
    """
    symbol: str                   # 合约代码
    exchange: Exchange            # 交易所
    datetime: datetime            # K线时间
    interval: Interval           # K线周期
    volume: int                  # 成交量
    turnover: float             # 成交额
    open_interest: int          # 持仓量
    
    # OHLC价格
    open_price: float           # 开盘价
    high_price: float          # 最高价
    low_price: float           # 最低价
    close_price: float         # 收盘价
    
    gateway_name: str = ""      # 网关名称

@dataclass
class ContractData:
    """
    合约数据结构
    包含合约的基本信息
    """
    symbol: str                 # 合约代码
    exchange: Exchange          # 交易所
    name: str                  # 合约名称
    product: str               # 产品代码
    size: int                  # 合约乘数
    pricetick: float          # 最小变动价位
    
    min_volume: int = 1        # 最小交易量
    stop_supported: bool = False  # 是否支持停止单
    net_position: bool = False   # 是否为净持仓
    history_data: bool = False   # 是否支持历史数据
    
    option_strike: float = 0.0    # 期权行权价
    option_underlying: str = ""   # 期权标的
    option_type: str = ""        # 期权类型
    option_expiry: datetime = None  # 期权到期日
    
    gateway_name: str = ""       # 网关名称

@dataclass 
class SubscribeRequest:
    """
    订阅请求数据结构
    用于订阅市场数据
    """
    symbol: str                 # 合约代码
    exchange: Exchange          # 交易所
    gateway_name: str = ""      # 网关名称

@dataclass
class HistoryRequest:
    """
    历史数据请求结构
    用于获取历史K线数据
    """
    symbol: str                 # 合约代码
    exchange: Exchange          # 交易所
    start: datetime            # 开始时间
    end: datetime              # 结束时间
    interval: Interval         # K线周期
    gateway_name: str = ""      # 网关名称

@dataclass
class MarketDataEvent:
    """
    市场数据事件结构
    用于事件驱动的数据分发
    """
    type: str                  # 事件类型 (tick/bar)
    data: Any                  # 数据内容 (TickData/BarData)
    timestamp: datetime        # 事件时间戳
    source: str = ""           # 数据源

# 技术指标相关数据结构
@dataclass
class IndicatorValue:
    """
    技术指标值结构
    """
    name: str                  # 指标名称
    value: float              # 指标数值
    timestamp: datetime       # 计算时间
    symbol: str              # 相关合约
    params: Dict[str, Any] = None  # 指标参数

@dataclass
class PricePoint:
    """
    价格点数据结构
    用于技术指标计算
    """
    timestamp: datetime       # 时间戳
    open: float              # 开盘价
    high: float              # 最高价
    low: float               # 最低价
    close: float             # 收盘价
    volume: int              # 成交量

# 交易相关枚举
class OrderType(Enum):
    """订单类型枚举"""
    LIMIT = "LIMIT"        # 限价单
    MARKET = "MARKET"      # 市价单
    STOP = "STOP"          # 停止单
    FAK = "FAK"            # Fill and Kill
    FOK = "FOK"            # Fill or Kill

class OrderStatus(Enum):
    """订单状态枚举"""
    SUBMITTING = "SUBMITTING"  # 提交中
    NOTTRADED = "NOTTRADED"    # 未成交
    PARTTRADED = "PARTTRADED"  # 部分成交
    ALLTRADED = "ALLTRADED"    # 全部成交
    CANCELLED = "CANCELLED"    # 已撤销
    REJECTED = "REJECTED"      # 拒绝

class Offset(Enum):
    """开平仓枚举"""
    NONE = "NONE"          # 不分开平仓
    OPEN = "OPEN"          # 开仓
    CLOSE = "CLOSE"        # 平仓
    CLOSETODAY = "CLOSETODAY"      # 平今
    CLOSEYESTERDAY = "CLOSEYESTERDAY"  # 平昨

class TradingSignalAction(Enum):
    """交易信号动作枚举"""
    OPEN_LONG = "OPEN_LONG"      # 开多
    OPEN_SHORT = "OPEN_SHORT"    # 开空
    CLOSE_LONG = "CLOSE_LONG"    # 平多
    CLOSE_SHORT = "CLOSE_SHORT"  # 平空

# 交易数据结构
@dataclass
class OrderRequest:
    """
    订单请求数据结构
    """
    symbol: str                   # 合约代码
    exchange: Exchange            # 交易所
    direction: Direction          # 交易方向
    type: OrderType              # 订单类型
    volume: int                  # 数量
    price: float = 0.0           # 价格
    offset: Offset = Offset.NONE # 开平仓
    reference: str = ""          # 订单备注
    gateway_name: str = ""       # 网关名称

@dataclass
class OrderData:
    """
    订单数据结构
    """
    orderid: str                 # 订单编号
    symbol: str                  # 合约代码
    exchange: Exchange           # 交易所
    direction: Direction         # 交易方向
    type: OrderType             # 订单类型
    volume: int                 # 总数量
    traded: int                 # 已成交数量
    status: OrderStatus         # 订单状态
    datetime: datetime          # 订单时间
    
    price: float = 0.0          # 委托价格
    offset: Offset = Offset.NONE # 开平仓
    reference: str = ""         # 订单备注
    gateway_name: str = ""      # 网关名称

@dataclass
class TradeData:
    """
    成交数据结构
    """
    tradeid: str                # 成交编号
    orderid: str               # 订单编号
    symbol: str                # 合约代码
    exchange: Exchange         # 交易所
    direction: Direction       # 交易方向
    volume: int               # 成交数量
    price: float              # 成交价格
    datetime: datetime        # 成交时间
    
    offset: Offset = Offset.NONE # 开平仓
    gateway_name: str = ""     # 网关名称

@dataclass
class PositionData:
    """
    持仓数据结构
    """
    symbol: str               # 合约代码
    exchange: Exchange        # 交易所
    direction: Direction      # 持仓方向
    volume: int              # 持仓数量
    frozen: int              # 冻结数量
    price: float             # 持仓均价
    pnl: float              # 持仓盈亏
    yd_volume: int = 0      # 昨仓数量
    gateway_name: str = ""   # 网关名称

@dataclass
class AccountData:
    """
    账户数据结构
    """
    accountid: str           # 账户编号
    balance: float          # 账户余额
    frozen: float           # 冻结资金
    available: float        # 可用资金
    
    # 期货相关
    pre_balance: float = 0.0      # 昨日余额
    commission: float = 0.0       # 手续费
    margin: float = 0.0          # 占用保证金
    close_profit: float = 0.0     # 平仓盈亏
    holding_profit: float = 0.0   # 持仓盈亏
    
    gateway_name: str = ""       # 网关名称

@dataclass
class TradingSignal:
    """
    交易信号数据结构
    """
    symbol: str                    # 合约代码
    action: TradingSignalAction    # 交易动作
    volume: int                   # 交易数量
    price: float = 0.0           # 期望价格 (0表示市价)
    timestamp: datetime = None    # 信号时间
    strategy: str = ""           # 策略名称
    reason: str = ""             # 信号原因

@dataclass
class TradingResult:
    """
    交易结果数据结构
    """
    success: bool               # 是否成功
    orderid: str = ""          # 订单编号
    message: str = ""          # 结果消息
    timestamp: datetime = None  # 处理时间

# 数据统计结构
@dataclass
class DataStatistics:
    """
    数据统计信息
    """
    symbol: str                    # 合约代码
    total_ticks: int = 0          # 总tick数
    total_bars: int = 0           # 总bar数
    first_time: Optional[datetime] = None   # 首个数据时间
    last_time: Optional[datetime] = None    # 最后数据时间
    update_count: int = 0         # 更新次数
    data_gaps: int = 0           # 数据缺口数
    
def create_tick_data(symbol: str, price: float, volume: int = 100, 
                    exchange: Exchange = Exchange.SHFE) -> TickData:
    """
    创建模拟Tick数据的便捷函数
    
    Args:
        symbol: 合约代码
        price: 价格
        volume: 成交量
        exchange: 交易所
        
    Returns:
        TickData: Tick数据对象
    """
    return TickData(
        symbol=symbol,
        exchange=exchange,
        datetime=datetime.now(),
        name=f"{symbol}合约",
        volume=volume,
        turnover=price * volume,
        open_interest=50000,
        last_price=price,
        limit_up=price * 1.1,
        limit_down=price * 0.9,
        open_price=price * 0.998,
        high_price=price * 1.002,
        low_price=price * 0.996,
        pre_close=price * 0.999,
        bid_price_1=price - 1,
        ask_price_1=price + 1,
        bid_volume_1=10,
        ask_volume_1=8,
        gateway_name="SIMULATION"
    )

def create_bar_data(symbol: str, open_p: float, high_p: float, 
                   low_p: float, close_p: float, volume: int = 1000,
                   interval: Interval = Interval.MINUTE,
                   exchange: Exchange = Exchange.SHFE) -> BarData:
    """
    创建模拟Bar数据的便捷函数
    
    Args:
        symbol: 合约代码
        open_p: 开盘价
        high_p: 最高价
        low_p: 最低价
        close_p: 收盘价
        volume: 成交量
        interval: K线周期
        exchange: 交易所
        
    Returns:
        BarData: Bar数据对象
    """
    return BarData(
        symbol=symbol,
        exchange=exchange,
        datetime=datetime.now(),
        interval=interval,
        volume=volume,
        turnover=close_p * volume,
        open_interest=50000,
        open_price=open_p,
        high_price=high_p,
        low_price=low_p,
        close_price=close_p,
        gateway_name="SIMULATION"
    )

# 数据转换函数
def tick_to_dict(tick: TickData) -> Dict:
    """将TickData转换为字典"""
    return {
        'symbol': tick.symbol,
        'datetime': tick.datetime.isoformat(),
        'last_price': tick.last_price,
        'volume': tick.volume,
        'bid_price_1': tick.bid_price_1,
        'ask_price_1': tick.ask_price_1,
        'bid_volume_1': tick.bid_volume_1,
        'ask_volume_1': tick.ask_volume_1
    }

def bar_to_dict(bar: BarData) -> Dict:
    """将BarData转换为字典"""
    return {
        'symbol': bar.symbol,
        'datetime': bar.datetime.isoformat(),
        'interval': bar.interval.value,
        'open': bar.open_price,
        'high': bar.high_price,
        'low': bar.low_price,
        'close': bar.close_price,
        'volume': bar.volume
    }

if __name__ == "__main__":
    """数据类型测试"""
    print("🧪 数据类型模块测试")
    print("=" * 40)
    
    # 测试创建Tick数据
    tick = create_tick_data("rb2405", 3500.0)
    print(f"✅ Tick数据: {tick.symbol} @ {tick.last_price}")
    
    # 测试创建Bar数据
    bar = create_bar_data("rb2405", 3480, 3520, 3470, 3500)
    print(f"✅ Bar数据: {bar.symbol} OHLC: {bar.open_price}/{bar.high_price}/{bar.low_price}/{bar.close_price}")
    
    # 测试数据转换
    tick_dict = tick_to_dict(tick)
    print(f"✅ Tick字典: {len(tick_dict)} 个字段")
    
    bar_dict = bar_to_dict(bar)
    print(f"✅ Bar字典: {len(bar_dict)} 个字段")
    
    print("\n✅ 数据类型模块测试完成")