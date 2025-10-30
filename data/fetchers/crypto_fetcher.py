"""
加密货币数据获取器
使用现有的Binance数据获取器适配新的统一接口
"""
from datetime import datetime
from typing import List, Optional
from loguru import logger

from ..base_fetcher import BaseDataFetcher, BarData, TickerData, register_fetcher
from ..market_config import MarketType, DataSource
from ..data_manager import BinanceDataFetcher

@register_fetcher(MarketType.CRYPTO, DataSource.BINANCE)
class BinanceCryptoFetcher(BaseDataFetcher):
    """Binance加密货币数据获取器"""
    
    def __init__(self, market_type: MarketType, data_source: DataSource, **kwargs):
        super().__init__(market_type, data_source, **kwargs)
        self.binance_fetcher = BinanceDataFetcher()
    
    def fetch_bars(self, symbol: str, interval: str, start_time: datetime, 
                   end_time: datetime, **kwargs) -> List[BarData]:
        """获取历史K线数据"""
        try:
            # 使用现有的Binance获取器
            bar_dicts = self.binance_fetcher.fetch_klines(symbol, interval, start_time, end_time)
            
            # 转换为BarData格式
            bars = []
            for bar_dict in bar_dicts:
                bar = BarData(
                    symbol=bar_dict["symbol"],
                    exchange=bar_dict["exchange"],
                    datetime=datetime.fromisoformat(bar_dict["datetime"]),
                    interval=bar_dict["interval"],
                    open_price=bar_dict["open_price"],
                    high_price=bar_dict["high_price"],
                    low_price=bar_dict["low_price"],
                    close_price=bar_dict["close_price"],
                    volume=bar_dict["volume"],
                    turnover=bar_dict["turnover"],
                    open_interest=bar_dict["open_interest"]
                )
                bars.append(bar)
            
            logger.info(f"Binance获取{symbol} {len(bars)}条加密货币K线数据")
            return bars
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}加密货币历史数据")
            return []
    
    def fetch_ticker(self, symbol: str, **kwargs) -> Optional[TickerData]:
        """获取实时行情数据"""
        try:
            ticker_dict = self.binance_fetcher.fetch_ticker(symbol)
            
            if not ticker_dict:
                return None
            
            ticker = TickerData(
                symbol=ticker_dict["symbol"],
                exchange=self.get_exchange_name(),
                price=ticker_dict["price"],
                change=ticker_dict["change"],
                change_percent=ticker_dict["change_percent"],
                volume=ticker_dict["volume"],
                high=ticker_dict["high"],
                low=ticker_dict["low"],
                timestamp=datetime.fromisoformat(ticker_dict["timestamp"])
            )
            
            return ticker
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}加密货币实时行情")
            return None
    
    def get_symbols(self, **kwargs) -> List[str]:
        """获取可交易品种列表"""
        # 返回一些常见的加密货币交易对
        common_symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
            "SOLUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
            "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "UNIUSDT", "XLMUSDT"
        ]
        return common_symbols
    
    def get_exchange_name(self) -> str:
        """获取交易所名称"""
        return "BINANCE"