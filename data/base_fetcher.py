"""
统一数据获取器基类
定义所有数据获取器的统一接口
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
import pandas as pd
from dataclasses import dataclass

from .market_config import MarketType, DataSource

@dataclass
class BarData:
    """K线数据标准格式"""
    symbol: str             # 品种代码
    exchange: str           # 交易所
    datetime: datetime      # 时间戳
    interval: str           # 时间间隔
    open_price: float       # 开盘价
    high_price: float       # 最高价
    low_price: float        # 最低价
    close_price: float      # 收盘价
    volume: float           # 成交量
    turnover: float = 0.0   # 成交额
    open_interest: float = 0.0  # 持仓量（期货用）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "datetime": self.datetime.isoformat(),
            "interval": self.interval,
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "close_price": self.close_price,
            "volume": self.volume,
            "turnover": self.turnover,
            "open_interest": self.open_interest
        }

@dataclass
class TickerData:
    """实时行情数据标准格式"""
    symbol: str             # 品种代码
    exchange: str           # 交易所
    price: float           # 当前价格
    change: float          # 涨跌额
    change_percent: float  # 涨跌幅(%)
    volume: float          # 成交量
    turnover: float = 0.0  # 成交额
    high: float = 0.0      # 最高价
    low: float = 0.0       # 最低价
    open: float = 0.0      # 开盘价
    prev_close: float = 0.0 # 昨收价
    timestamp: datetime = None  # 时间戳
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class BaseDataFetcher(ABC):
    """数据获取器抽象基类"""
    
    def __init__(self, market_type: MarketType, data_source: DataSource, **kwargs):
        self.market_type = market_type
        self.data_source = data_source
        self.config = kwargs
        self.api_key = kwargs.get('api_key', None)
        self.base_url = kwargs.get('base_url', '')
        
    @abstractmethod
    def fetch_bars(self, symbol: str, interval: str, start_time: datetime, 
                   end_time: datetime, **kwargs) -> List[BarData]:
        """
        获取历史K线数据
        
        Args:
            symbol: 品种代码
            interval: 时间间隔 (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            start_time: 开始时间
            end_time: 结束时间
            **kwargs: 其他参数
            
        Returns:
            List[BarData]: K线数据列表
        """
        pass
    
    @abstractmethod
    def fetch_ticker(self, symbol: str, **kwargs) -> Optional[TickerData]:
        """
        获取实时行情数据
        
        Args:
            symbol: 品种代码
            **kwargs: 其他参数
            
        Returns:
            TickerData: 实时行情数据
        """
        pass
    
    @abstractmethod
    def get_symbols(self, **kwargs) -> List[str]:
        """
        获取可交易品种列表
        
        Args:
            **kwargs: 其他参数
            
        Returns:
            List[str]: 品种代码列表
        """
        pass
    
    def validate_symbol(self, symbol: str) -> bool:
        """验证品种代码有效性"""
        symbols = self.get_symbols()
        return symbol in symbols if symbols else True
    
    def convert_interval(self, interval: str) -> str:
        """转换时间间隔格式（子类可重写）"""
        return interval
    
    def normalize_symbol(self, symbol: str) -> str:
        """标准化品种代码（子类可重写）"""
        return symbol.upper()
    
    def get_exchange_name(self) -> str:
        """获取交易所名称（子类可重写）"""
        return self.data_source.value.upper()
    
    def bars_to_dataframe(self, bars: List[BarData]) -> pd.DataFrame:
        """将BarData列表转换为DataFrame"""
        if not bars:
            return pd.DataFrame()
        
        data = []
        for bar in bars:
            data.append({
                'datetime': bar.datetime,
                'open_price': bar.open_price,
                'high_price': bar.high_price,
                'low_price': bar.low_price,
                'close_price': bar.close_price,
                'volume': bar.volume,
                'turnover': bar.turnover,
                'open_interest': bar.open_interest,
                'symbol': bar.symbol,
                'exchange': bar.exchange,
                'interval': bar.interval
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)
        
        return df
    
    def handle_rate_limit(self):
        """处理API限制（子类可重写）"""
        import time
        time.sleep(0.1)  # 默认100ms延迟
    
    def handle_error(self, error: Exception, operation: str):
        """统一错误处理"""
        from loguru import logger
        logger.error(f"{self.__class__.__name__} {operation} 失败: {error}")

class DataFetcherFactory:
    """数据获取器工厂类"""
    
    _fetchers = {}  # 注册的获取器类
    
    @classmethod
    def register(cls, market_type: MarketType, data_source: DataSource, fetcher_class):
        """注册数据获取器"""
        key = (market_type, data_source)
        cls._fetchers[key] = fetcher_class
    
    @classmethod
    def create(cls, market_type: MarketType, data_source: DataSource, **kwargs) -> BaseDataFetcher:
        """创建数据获取器实例"""
        key = (market_type, data_source)
        fetcher_class = cls._fetchers.get(key)
        
        if not fetcher_class:
            raise ValueError(f"不支持的市场类型和数据源组合: {market_type.value} + {data_source.value}")
        
        return fetcher_class(market_type, data_source, **kwargs)
    
    @classmethod
    def get_supported_combinations(cls) -> List[tuple]:
        """获取支持的市场类型和数据源组合"""
        return list(cls._fetchers.keys())

# 装饰器：用于注册数据获取器
def register_fetcher(market_type: MarketType, data_source: DataSource):
    """注册数据获取器的装饰器"""
    def decorator(fetcher_class):
        DataFetcherFactory.register(market_type, data_source, fetcher_class)
        return fetcher_class
    return decorator