"""
极简期货量化交易系统 - 核心模块包
"""

from .connection_manager import ConnectionManager, ConnectionStatus, create_connection_manager
from .market_data_manager import MarketDataManager, create_market_data_manager
from .data_types import (
    TickData, BarData, ContractData, SubscribeRequest,
    MarketDataEvent, IndicatorValue, DataStatistics,
    Exchange, Direction, Interval,
    create_tick_data, create_bar_data
)

__all__ = [
    # 连接管理
    'ConnectionManager',
    'ConnectionStatus', 
    'create_connection_manager',
    
    # 行情数据管理
    'MarketDataManager',
    'create_market_data_manager',
    
    # 数据类型
    'TickData',
    'BarData', 
    'ContractData',
    'SubscribeRequest',
    'MarketDataEvent',
    'IndicatorValue',
    'DataStatistics',
    
    # 枚举类型
    'Exchange',
    'Direction',
    'Interval',
    
    # 工具函数
    'create_tick_data',
    'create_bar_data'
]