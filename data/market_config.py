"""
多市场配置文件
定义不同市场的配置参数、交易时间、交易规则等
"""
from datetime import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class MarketType(Enum):
    """市场类型枚举"""
    US_STOCK = "us_stock"           # 美股
    US_FUTURES = "us_futures"       # 美国期货
    CHINA_STOCK = "china_stock"     # 中国A股
    CHINA_FUTURES = "china_futures" # 中国商品期货
    CRYPTO = "crypto"               # 加密货币

class DataSource(Enum):
    """数据源枚举"""
    YAHOO_FINANCE = "yahoo"
    ALPHA_VANTAGE = "alphavantage"
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    BINANCE = "binance"
    IEX_CLOUD = "iex"
    QUANDL = "quandl"
    EASTMONEY = "eastmoney"

@dataclass
class TradingSession:
    """交易时段"""
    name: str
    start_time: time
    end_time: time
    timezone: str

@dataclass
class MarketConfig:
    """市场配置"""
    market_type: MarketType
    market_name: str
    currency: str
    timezone: str
    trading_sessions: List[TradingSession]
    supported_intervals: List[str]
    data_sources: List[DataSource]
    symbol_format: str  # 如：AAPL, 000001.SZ, BTCUSDT
    default_source: DataSource
    
# 市场配置字典
MARKET_CONFIGS = {
    MarketType.US_STOCK: MarketConfig(
        market_type=MarketType.US_STOCK,
        market_name="美股市场",
        currency="USD",
        timezone="America/New_York",
        trading_sessions=[
            TradingSession("盘前", time(4, 0), time(9, 30), "America/New_York"),
            TradingSession("正常", time(9, 30), time(16, 0), "America/New_York"),
            TradingSession("盘后", time(16, 0), time(20, 0), "America/New_York"),
        ],
        supported_intervals=["1m", "5m", "15m", "30m", "1h", "1d"],
        data_sources=[DataSource.YAHOO_FINANCE, DataSource.ALPHA_VANTAGE, DataSource.IEX_CLOUD],
        symbol_format="TICKER",  # 如: AAPL, MSFT, TSLA
        default_source=DataSource.YAHOO_FINANCE
    ),
    
    MarketType.US_FUTURES: MarketConfig(
        market_type=MarketType.US_FUTURES,
        market_name="美国期货市场",
        currency="USD",
        timezone="America/Chicago",
        trading_sessions=[
            TradingSession("电子盘", time(17, 0), time(16, 0), "America/Chicago"),  # 几乎24小时
        ],
        supported_intervals=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        data_sources=[DataSource.YAHOO_FINANCE, DataSource.QUANDL],
        symbol_format="CONTRACT_SYMBOL",  # 如: ES=F, NQ=F, GC=F
        default_source=DataSource.YAHOO_FINANCE
    ),
    
    MarketType.CHINA_STOCK: MarketConfig(
        market_type=MarketType.CHINA_STOCK,
        market_name="中国A股市场",
        currency="CNY",
        timezone="Asia/Shanghai",
        trading_sessions=[
            TradingSession("早盘", time(9, 30), time(11, 30), "Asia/Shanghai"),
            TradingSession("午盘", time(13, 0), time(15, 0), "Asia/Shanghai"),
        ],
        supported_intervals=["1m", "5m", "15m", "30m", "1h", "1d"],
        data_sources=[DataSource.TUSHARE, DataSource.AKSHARE, DataSource.EASTMONEY],
        symbol_format="CODE.EXCHANGE",  # 如: 000001.SZ, 600000.SH
        default_source=DataSource.AKSHARE
    ),
    
    MarketType.CHINA_FUTURES: MarketConfig(
        market_type=MarketType.CHINA_FUTURES,
        market_name="中国商品期货市场",
        currency="CNY",
        timezone="Asia/Shanghai",
        trading_sessions=[
            TradingSession("白盘", time(9, 0), time(15, 0), "Asia/Shanghai"),
            TradingSession("夜盘", time(21, 0), time(23, 30), "Asia/Shanghai"),
        ],
        supported_intervals=["1m", "5m", "15m", "30m", "1h", "1d"],
        data_sources=[DataSource.TUSHARE, DataSource.AKSHARE],
        symbol_format="CONTRACT_CODE",  # 如: rb2310, cu2309
        default_source=DataSource.AKSHARE
    ),
    
    MarketType.CRYPTO: MarketConfig(
        market_type=MarketType.CRYPTO,
        market_name="加密货币市场",
        currency="USDT",
        timezone="UTC",
        trading_sessions=[
            TradingSession("全天", time(0, 0), time(23, 59), "UTC"),
        ],
        supported_intervals=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        data_sources=[DataSource.BINANCE],
        symbol_format="CRYPTO_PAIR",  # 如: BTCUSDT, ETHUSDT
        default_source=DataSource.BINANCE
    )
}

# 数据源配置
DATA_SOURCE_CONFIGS = {
    DataSource.YAHOO_FINANCE: {
        "name": "Yahoo Finance",
        "api_key_required": False,
        "rate_limit": "2000/hour",
        "supported_markets": [MarketType.US_STOCK, MarketType.US_FUTURES],
        "base_url": "https://query1.finance.yahoo.com"
    },
    
    DataSource.ALPHA_VANTAGE: {
        "name": "Alpha Vantage",
        "api_key_required": True,
        "rate_limit": "5/minute",
        "supported_markets": [MarketType.US_STOCK],
        "base_url": "https://www.alphavantage.co"
    },
    
    DataSource.TUSHARE: {
        "name": "Tushare",
        "api_key_required": True,
        "rate_limit": "200/minute",
        "supported_markets": [MarketType.CHINA_STOCK, MarketType.CHINA_FUTURES],
        "base_url": "http://api.tushare.pro"
    },
    
    DataSource.AKSHARE: {
        "name": "AKShare",
        "api_key_required": False,
        "rate_limit": "flexible",
        "supported_markets": [MarketType.CHINA_STOCK, MarketType.CHINA_FUTURES],
        "base_url": "https://akshare.akfamily.xyz"
    },
    
    DataSource.BINANCE: {
        "name": "Binance",
        "api_key_required": False,
        "rate_limit": "1200/minute",
        "supported_markets": [MarketType.CRYPTO],
        "base_url": "https://api.binance.com"
    }
}

def get_market_config(market_type: MarketType) -> MarketConfig:
    """获取市场配置"""
    return MARKET_CONFIGS.get(market_type)

def get_supported_data_sources(market_type: MarketType) -> List[DataSource]:
    """获取市场支持的数据源"""
    config = get_market_config(market_type)
    return config.data_sources if config else []

def validate_symbol_format(symbol: str, market_type: MarketType) -> bool:
    """验证品种代码格式"""
    config = get_market_config(market_type)
    if not config:
        return False
    
    # 简单的格式验证逻辑，可以根据需要扩展
    if market_type == MarketType.US_STOCK:
        return symbol.isalpha() and len(symbol) <= 5
    elif market_type == MarketType.CHINA_STOCK:
        return "." in symbol and len(symbol.split(".")[0]) == 6
    elif market_type == MarketType.CRYPTO:
        return "USDT" in symbol or "BTC" in symbol
    else:
        return True  # 其他情况暂时返回True

def get_market_type_by_symbol(symbol: str) -> Optional[MarketType]:
    """根据品种代码推断市场类型"""
    symbol = symbol.upper()
    
    # 加密货币
    if any(pair in symbol for pair in ["USDT", "BTC", "ETH", "BNB"]):
        return MarketType.CRYPTO
    
    # 中国A股
    if "." in symbol and symbol.split(".")[1] in ["SH", "SZ"]:
        return MarketType.CHINA_STOCK
    
    # 美国期货
    if symbol.endswith("=F") or any(code in symbol for code in ["ES", "NQ", "GC", "CL"]):
        return MarketType.US_FUTURES
    
    # 中国期货（通常是字母+数字）
    if len(symbol) >= 4 and symbol[:2].isalpha() and symbol[2:].isdigit():
        return MarketType.CHINA_FUTURES
    
    # 默认认为是美股
    if symbol.isalpha():
        return MarketType.US_STOCK
    
    return None

# 常用品种代码示例
SYMBOL_EXAMPLES = {
    MarketType.US_STOCK: ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"],
    MarketType.US_FUTURES: ["ES=F", "NQ=F", "GC=F", "CL=F", "ZN=F"],
    MarketType.CHINA_STOCK: ["000001.SZ", "600000.SH", "000002.SZ", "600519.SH"],
    MarketType.CHINA_FUTURES: ["rb2310", "cu2309", "au2312", "ag2312"],
    MarketType.CRYPTO: ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
}