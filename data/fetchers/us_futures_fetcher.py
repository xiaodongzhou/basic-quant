"""
美国期货数据获取器
主要支持Yahoo Finance数据源
"""
import requests
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
from loguru import logger

from ..base_fetcher import BaseDataFetcher, BarData, TickerData, register_fetcher
from ..market_config import MarketType, DataSource

@register_fetcher(MarketType.US_FUTURES, DataSource.YAHOO_FINANCE)
class YahooFinanceUSFuturesFetcher(BaseDataFetcher):
    """Yahoo Finance美国期货数据获取器"""
    
    def __init__(self, market_type: MarketType, data_source: DataSource, **kwargs):
        super().__init__(market_type, data_source, **kwargs)
        self.base_url = "https://query1.finance.yahoo.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 美国期货合约映射
        self.futures_map = {
            # 股指期货
            "ES": "ES=F",      # E-mini S&P 500
            "NQ": "NQ=F",      # E-mini NASDAQ 100
            "YM": "YM=F",      # E-mini Dow Jones
            "RTY": "RTY=F",    # E-mini Russell 2000
            
            # 商品期货
            "GC": "GC=F",      # 黄金
            "SI": "SI=F",      # 白银
            "CL": "CL=F",      # 原油WTI
            "BZ": "BZ=F",      # 布伦特原油
            "NG": "NG=F",      # 天然气
            
            # 农产品期货
            "ZC": "ZC=F",      # 玉米
            "ZS": "ZS=F",      # 大豆
            "ZW": "ZW=F",      # 小麦
            "KC": "KC=F",      # 咖啡
            "SB": "SB=F",      # 糖
            
            # 债券期货
            "ZN": "ZN=F",      # 10年期国债
            "ZB": "ZB=F",      # 30年期国债
            "ZF": "ZF=F",      # 5年期国债
            
            # 外汇期货
            "6E": "6E=F",      # 欧元
            "6J": "6J=F",      # 日元
            "6B": "6B=F",      # 英镑
        }
    
    def normalize_symbol(self, symbol: str) -> str:
        """标准化期货代码"""
        symbol = symbol.upper()
        
        # 如果已经是Yahoo格式，直接返回
        if symbol.endswith("=F"):
            return symbol
        
        # 查找映射
        base_symbol = symbol.replace("=F", "")
        if base_symbol in self.futures_map:
            return self.futures_map[base_symbol]
        
        # 如果没找到，尝试添加=F后缀
        return f"{base_symbol}=F"
    
    def convert_interval(self, interval: str) -> str:
        """转换时间间隔格式"""
        interval_map = {
            "1m": "1m",
            "5m": "5m", 
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1w": "1wk",
            "1M": "1mo"
        }
        return interval_map.get(interval, "1d")
    
    def fetch_bars(self, symbol: str, interval: str, start_time: datetime, 
                   end_time: datetime, **kwargs) -> List[BarData]:
        """获取历史K线数据"""
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            yahoo_interval = self.convert_interval(interval)
            
            # 转换为Unix时间戳
            start_ts = int(start_time.timestamp())
            end_ts = int(end_time.timestamp())
            
            url = f"{self.base_url}/v8/finance/chart/{yahoo_symbol}"
            params = {
                "interval": yahoo_interval,
                "period1": start_ts,
                "period2": end_ts,
                "includePrePost": "false",  # 期货一般不需要盘前盘后
                "events": "div,splits"
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            chart_data = data.get("chart", {}).get("result", [])
            
            if not chart_data:
                logger.warning(f"Yahoo Finance未返回{symbol}的期货数据")
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
                        symbol=yahoo_symbol,
                        exchange=self.get_exchange_name(),
                        datetime=bar_time,
                        interval=interval,
                        open_price=float(open_price),
                        high_price=float(high_price),
                        low_price=float(low_price),
                        close_price=float(close_price),
                        volume=float(volume or 0),
                        turnover=0.0,  # 期货通常不提供成交额
                        open_interest=0.0  # Yahoo Finance不提供持仓量
                    )
                    bars.append(bar)
                    
                except (ValueError, TypeError) as e:
                    continue
            
            logger.info(f"Yahoo Finance获取{symbol} {len(bars)}条期货K线数据")
            return bars
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}期货历史数据")
            return []
    
    def fetch_ticker(self, symbol: str, **kwargs) -> Optional[TickerData]:
        """获取实时行情数据"""
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            
            url = f"{self.base_url}/v6/finance/quote"
            params = {"symbols": yahoo_symbol}
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("quoteResponse", {}).get("result", [])
            
            if not results:
                logger.warning(f"Yahoo Finance未返回{symbol}的期货行情数据")
                return None
            
            quote = results[0]
            
            ticker = TickerData(
                symbol=yahoo_symbol,
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
            self.handle_error(e, f"获取{symbol}期货实时行情")
            return None
    
    def get_symbols(self, **kwargs) -> List[str]:
        """获取可交易品种列表"""
        # 返回支持的期货合约
        futures_symbols = list(self.futures_map.values())
        
        # 添加一些其他常见期货合约
        additional_futures = [
            "HE=F",    # 瘦肉猪
            "LE=F",    # 活牛
            "CC=F",    # 可可
            "CT=F",    # 棉花
            "LBS=F",   # 木材
            "PA=F",    # 钯金
            "PL=F",    # 铂金
            "HG=F",    # 铜
            "ZR=F",    # 糙米
            "ZO=F",    # 燕麦
        ]
        
        all_symbols = futures_symbols + additional_futures
        
        logger.info(f"返回{len(all_symbols)}个美国期货合约")
        return all_symbols
    
    def get_futures_info(self, symbol: str) -> Dict[str, Any]:
        """获取期货合约信息"""
        symbol_info = {
            "ES=F": {"name": "E-mini S&P 500", "category": "股指期货", "exchange": "CME"},
            "NQ=F": {"name": "E-mini NASDAQ 100", "category": "股指期货", "exchange": "CME"},
            "YM=F": {"name": "E-mini Dow Jones", "category": "股指期货", "exchange": "CBOT"},
            "GC=F": {"name": "黄金", "category": "贵金属", "exchange": "COMEX"},
            "SI=F": {"name": "白银", "category": "贵金属", "exchange": "COMEX"},
            "CL=F": {"name": "原油WTI", "category": "能源", "exchange": "NYMEX"},
            "NG=F": {"name": "天然气", "category": "能源", "exchange": "NYMEX"},
            "ZC=F": {"name": "玉米", "category": "农产品", "exchange": "CBOT"},
            "ZS=F": {"name": "大豆", "category": "农产品", "exchange": "CBOT"},
            "ZN=F": {"name": "10年期国债", "category": "利率", "exchange": "CBOT"},
        }
        
        return symbol_info.get(symbol, {"name": symbol, "category": "其他", "exchange": "未知"})
    
    def get_exchange_name(self) -> str:
        """获取交易所名称"""
        return "US_FUTURES"
    
    def handle_rate_limit(self):
        """处理API限制"""
        time.sleep(0.1)  # Yahoo Finance相对宽松