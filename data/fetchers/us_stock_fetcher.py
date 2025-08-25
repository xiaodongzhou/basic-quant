"""
美股数据获取器
支持Yahoo Finance和Alpha Vantage数据源
"""
import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
from loguru import logger

from ..base_fetcher import BaseDataFetcher, BarData, TickerData, register_fetcher
from ..market_config import MarketType, DataSource

@register_fetcher(MarketType.US_STOCK, DataSource.YAHOO_FINANCE)
class YahooFinanceUSStockFetcher(BaseDataFetcher):
    """Yahoo Finance美股数据获取器"""
    
    def __init__(self, market_type: MarketType, data_source: DataSource, **kwargs):
        super().__init__(market_type, data_source, **kwargs)
        self.base_url = "https://query1.finance.yahoo.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def convert_interval(self, interval: str) -> str:
        """转换时间间隔格式"""
        interval_map = {
            "1m": "1m",
            "5m": "5m", 
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "1d": "1d",
            "1w": "1wk",
            "1M": "1mo"
        }
        return interval_map.get(interval, "1d")
    
    def fetch_bars(self, symbol: str, interval: str, start_time: datetime, 
                   end_time: datetime, **kwargs) -> List[BarData]:
        """获取历史K线数据"""
        try:
            symbol = self.normalize_symbol(symbol)
            yahoo_interval = self.convert_interval(interval)
            
            # 转换为Unix时间戳
            start_ts = int(start_time.timestamp())
            end_ts = int(end_time.timestamp())
            
            url = f"{self.base_url}/v8/finance/chart/{symbol}"
            params = {
                "interval": yahoo_interval,
                "period1": start_ts,
                "period2": end_ts,
                "includePrePost": "true",
                "events": "div,splits"
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            chart_data = data.get("chart", {}).get("result", [])
            
            if not chart_data:
                logger.warning(f"Yahoo Finance未返回{symbol}的数据")
                return []
            
            result = chart_data[0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {}).get("quote", [{}])[0]
            
            bars = []
            for i, ts in enumerate(timestamps):
                try:
                    bar_time = datetime.fromtimestamp(ts)
                    
                    # 检查数据完整性
                    open_price = indicators.get("open", [None] * len(timestamps))[i]
                    high_price = indicators.get("high", [None] * len(timestamps))[i]
                    low_price = indicators.get("low", [None] * len(timestamps))[i]
                    close_price = indicators.get("close", [None] * len(timestamps))[i]
                    volume = indicators.get("volume", [None] * len(timestamps))[i]
                    
                    # 跳过无效数据
                    if any(x is None for x in [open_price, high_price, low_price, close_price]):
                        continue
                    
                    bar = BarData(
                        symbol=symbol,
                        exchange=self.get_exchange_name(),
                        datetime=bar_time,
                        interval=interval,
                        open_price=float(open_price),
                        high_price=float(high_price),
                        low_price=float(low_price),
                        close_price=float(close_price),
                        volume=float(volume or 0),
                        turnover=0.0,  # Yahoo Finance不提供成交额
                        open_interest=0.0
                    )
                    bars.append(bar)
                    
                except (ValueError, TypeError) as e:
                    continue
            
            logger.info(f"Yahoo Finance获取{symbol} {len(bars)}条K线数据")
            return bars
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}历史数据")
            return []
    
    def fetch_ticker(self, symbol: str, **kwargs) -> Optional[TickerData]:
        """获取实时行情数据"""
        try:
            symbol = self.normalize_symbol(symbol)
            
            url = f"{self.base_url}/v6/finance/quote"
            params = {"symbols": symbol}
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("quoteResponse", {}).get("result", [])
            
            if not results:
                logger.warning(f"Yahoo Finance未返回{symbol}的行情数据")
                return None
            
            quote = results[0]
            
            ticker = TickerData(
                symbol=symbol,
                exchange=self.get_exchange_name(),
                price=float(quote.get("regularMarketPrice", 0)),
                change=float(quote.get("regularMarketChange", 0)),
                change_percent=float(quote.get("regularMarketChangePercent", 0)),
                volume=float(quote.get("regularMarketVolume", 0)),
                high=float(quote.get("regularMarketDayHigh", 0)),
                low=float(quote.get("regularMarketDayLow", 0)),
                open=float(quote.get("regularMarketOpen", 0)),
                prev_close=float(quote.get("regularMarketPreviousClose", 0)),
                timestamp=datetime.now()
            )
            
            return ticker
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}实时行情")
            return None
    
    def get_symbols(self, **kwargs) -> List[str]:
        """获取可交易品种列表"""
        # Yahoo Finance没有直接的API获取所有美股列表
        # 这里返回一些常见的美股代码作为示例
        common_symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX",
            "BRKB", "V", "JPM", "JNJ", "WMT", "PG", "UNH", "HD", "MA", "DIS",
            "PYPL", "BAC", "ADBE", "CRM", "NFLX", "CMCSA", "PEP", "TMO", "ABBV"
        ]
        return common_symbols
    
    def get_exchange_name(self) -> str:
        """获取交易所名称"""
        return "NASDAQ"  # 简化处理

@register_fetcher(MarketType.US_STOCK, DataSource.ALPHA_VANTAGE)
class AlphaVantageUSStockFetcher(BaseDataFetcher):
    """Alpha Vantage美股数据获取器"""
    
    def __init__(self, market_type: MarketType, data_source: DataSource, **kwargs):
        super().__init__(market_type, data_source, **kwargs)
        self.base_url = "https://www.alphavantage.co"
        
        if not self.api_key:
            raise ValueError("Alpha Vantage需要API密钥")
    
    def convert_interval(self, interval: str) -> tuple:
        """转换时间间隔格式，返回(function, interval)"""
        if interval == "1d":
            return ("TIME_SERIES_DAILY", None)
        elif interval in ["1m", "5m", "15m", "30m", "1h"]:
            return ("TIME_SERIES_INTRADAY", interval)
        else:
            return ("TIME_SERIES_DAILY", None)
    
    def fetch_bars(self, symbol: str, interval: str, start_time: datetime, 
                   end_time: datetime, **kwargs) -> List[BarData]:
        """获取历史K线数据"""
        try:
            symbol = self.normalize_symbol(symbol)
            function, av_interval = self.convert_interval(interval)
            
            url = f"{self.base_url}/query"
            params = {
                "function": function,
                "symbol": symbol,
                "apikey": self.api_key,
                "outputsize": "full",
                "datatype": "json"
            }
            
            if av_interval:
                params["interval"] = av_interval
            
            # Alpha Vantage有严格的API限制，需要限速
            self.handle_rate_limit()
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查API错误
            if "Error Message" in data:
                logger.error(f"Alpha Vantage错误: {data['Error Message']}")
                return []
            
            if "Note" in data:
                logger.warning(f"Alpha Vantage限制: {data['Note']}")
                return []
            
            # 获取时间序列数据
            time_series_key = None
            for key in data.keys():
                if "Time Series" in key:
                    time_series_key = key
                    break
            
            if not time_series_key:
                logger.warning(f"Alpha Vantage未返回{symbol}的时间序列数据")
                return []
            
            time_series = data[time_series_key]
            bars = []
            
            for timestamp_str, price_data in time_series.items():
                bar_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S" if " " in timestamp_str else "%Y-%m-%d")
                
                # 过滤时间范围
                if bar_time < start_time or bar_time > end_time:
                    continue
                
                bar = BarData(
                    symbol=symbol,
                    exchange=self.get_exchange_name(),
                    datetime=bar_time,
                    interval=interval,
                    open_price=float(price_data["1. open"]),
                    high_price=float(price_data["2. high"]),
                    low_price=float(price_data["3. low"]),
                    close_price=float(price_data["4. close"]),
                    volume=float(price_data["5. volume"]),
                    turnover=0.0,
                    open_interest=0.0
                )
                bars.append(bar)
            
            # 按时间排序
            bars.sort(key=lambda x: x.datetime)
            
            logger.info(f"Alpha Vantage获取{symbol} {len(bars)}条K线数据")
            return bars
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}历史数据")
            return []
    
    def fetch_ticker(self, symbol: str, **kwargs) -> Optional[TickerData]:
        """获取实时行情数据"""
        try:
            symbol = self.normalize_symbol(symbol)
            
            url = f"{self.base_url}/query"
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            self.handle_rate_limit()
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "Error Message" in data:
                logger.error(f"Alpha Vantage错误: {data['Error Message']}")
                return None
            
            quote = data.get("Global Quote", {})
            if not quote:
                logger.warning(f"Alpha Vantage未返回{symbol}的行情数据")
                return None
            
            ticker = TickerData(
                symbol=symbol,
                exchange=self.get_exchange_name(),
                price=float(quote.get("05. price", 0)),
                change=float(quote.get("09. change", 0)),
                change_percent=float(quote.get("10. change percent", "0%").replace("%", "")),
                volume=float(quote.get("06. volume", 0)),
                high=float(quote.get("03. high", 0)),
                low=float(quote.get("04. low", 0)),
                open=float(quote.get("02. open", 0)),
                prev_close=float(quote.get("08. previous close", 0)),
                timestamp=datetime.now()
            )
            
            return ticker
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}实时行情")
            return None
    
    def get_symbols(self, **kwargs) -> List[str]:
        """获取可交易品种列表"""
        # Alpha Vantage没有获取所有股票列表的API
        # 返回常见美股代码
        return YahooFinanceUSStockFetcher(self.market_type, DataSource.YAHOO_FINANCE).get_symbols()
    
    def handle_rate_limit(self):
        """处理API限制 - Alpha Vantage限制5次/分钟"""
        time.sleep(12)  # 每次请求间隔12秒，确保不超过限制
    
    def get_exchange_name(self) -> str:
        """获取交易所名称"""
        return "NASDAQ"