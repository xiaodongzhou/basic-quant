"""
数据管理器
统一管理数据的获取、存储和检索
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import pandas as pd
import numpy as np
import requests
from loguru import logger

from config.settings import DATA_PATHS


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DATA_PATHS.get("database", Path("data/database")) / "market_data.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # 创建K线数据表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bar_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                exchange TEXT NOT NULL,
                datetime TEXT NOT NULL,
                interval TEXT NOT NULL,
                open_price REAL NOT NULL,
                high_price REAL NOT NULL,
                low_price REAL NOT NULL,
                close_price REAL NOT NULL,
                volume REAL NOT NULL,
                turnover REAL DEFAULT 0,
                open_interest REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, exchange, datetime, interval)
            )
        """)
        
        self.conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")
    
    def save_bars(self, bars: List[Dict]):
        """保存K线数据"""
        try:
            cursor = self.conn.cursor()
            for bar in bars:
                cursor.execute("""
                    INSERT OR REPLACE INTO bar_data 
                    (symbol, exchange, datetime, interval, open_price, high_price, 
                     low_price, close_price, volume, turnover, open_interest)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bar.get("symbol", ""),
                    bar.get("exchange", ""),
                    bar.get("datetime", ""),
                    bar.get("interval", "1m"),
                    bar.get("open_price", 0),
                    bar.get("high_price", 0),
                    bar.get("low_price", 0),
                    bar.get("close_price", 0),
                    bar.get("volume", 0),
                    bar.get("turnover", 0),
                    bar.get("open_interest", 0)
                ))
            self.conn.commit()
            logger.info(f"保存了{len(bars)}条K线数据")
        except Exception as e:
            logger.error(f"保存K线数据失败: {e}")
    
    def load_bars(self, symbol: str, exchange: str, start_date: str, 
                  end_date: str, interval: str = "1m") -> pd.DataFrame:
        """加载K线数据"""
        try:
            query = """
                SELECT symbol, exchange, datetime, interval, open_price, high_price,
                       low_price, close_price, volume, turnover, open_interest
                FROM bar_data 
                WHERE symbol=? AND exchange=? AND interval=? 
                AND datetime BETWEEN ? AND ?
                ORDER BY datetime
            """
            df = pd.read_sql_query(
                query, self.conn, 
                params=(symbol, exchange, interval, start_date, end_date)
            )
            if not df.empty:
                df["datetime"] = pd.to_datetime(df["datetime"])
                df.set_index("datetime", inplace=True)
            logger.info(f"加载了{len(df)}条K线数据")
            return df
        except Exception as e:
            logger.error(f"加载K线数据失败: {e}")
            return pd.DataFrame()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


class BinanceDataFetcher:
    """币安数据获取器"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com"
        
    def fetch_klines(self, symbol: str, interval: str, start_time: datetime, 
                     end_time: datetime, limit: int = 1000) -> List[Dict]:
        """获取K线数据"""
        try:
            # 转换时间间隔格式
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "4h": "4h", "1d": "1d"
            }
            
            api_interval = interval_map.get(interval, "1m")
            start_ts = int(start_time.timestamp() * 1000)
            end_ts = int(end_time.timestamp() * 1000)
            
            url = f"{self.base_url}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": api_interval,
                "startTime": start_ts,
                "endTime": end_ts,
                "limit": limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            klines = response.json()
            bars = []
            
            for kline in klines:
                bar_time = datetime.fromtimestamp(kline[0] / 1000)
                bar = {
                    "symbol": symbol,
                    "exchange": "BINANCE",
                    "datetime": bar_time.isoformat(),
                    "interval": interval,
                    "open_price": float(kline[1]),
                    "high_price": float(kline[2]),
                    "low_price": float(kline[3]),
                    "close_price": float(kline[4]),
                    "volume": float(kline[5]),
                    "turnover": float(kline[7]),
                    "open_interest": 0.0
                }
                bars.append(bar)
            
            logger.info(f"从Binance获取了{len(bars)}条{symbol} {interval}数据")
            return bars
            
        except Exception as e:
            logger.error(f"从Binance获取K线数据失败: {e}")
            return []
    
    def fetch_ticker(self, symbol: str) -> Dict:
        """获取24小时价格变动统计"""
        try:
            url = f"{self.base_url}/api/v3/ticker/24hr"
            params = {"symbol": symbol}
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return {
                "symbol": symbol,
                "price": float(data["lastPrice"]),
                "change": float(data["priceChange"]),
                "change_percent": float(data["priceChangePercent"]),
                "volume": float(data["volume"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取{symbol}行情数据失败: {e}")
            return {}


class DataManager:
    """统一数据管理器"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.binance_fetcher = BinanceDataFetcher()
        logger.info("数据管理器初始化完成")
    
    def download_data(self, symbol: str, start_date: str, end_date: str, 
                     interval: str = "1m", exchange: str = "BINANCE", 
                     force_update: bool = False) -> pd.DataFrame:
        """下载历史数据"""
        try:
            # 检查本地是否已有数据
            if not force_update:
                existing_data = self.db_manager.load_bars(
                    symbol, exchange, start_date, end_date, interval
                )
                if not existing_data.empty:
                    logger.info(f"使用本地缓存数据: {symbol}")
                    return existing_data
            
            # 从外部数据源获取数据
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            
            logger.info(f"从{exchange}下载{symbol}数据: {start_date} 到 {end_date}")
            
            if exchange.upper() == "BINANCE":
                bar_data = self.binance_fetcher.fetch_klines(
                    symbol, interval, start_dt, end_dt
                )
            else:
                logger.error(f"不支持的交易所: {exchange}")
                return pd.DataFrame()
            
            if not bar_data:
                logger.warning(f"未获取到{symbol}的数据")
                return pd.DataFrame()
            
            # 保存到数据库
            self.db_manager.save_bars(bar_data)
            
            # 返回DataFrame格式
            df = pd.DataFrame(bar_data)
            df["datetime"] = pd.to_datetime(df["datetime"])
            df.set_index("datetime", inplace=True)
            
            logger.info(f"成功下载并保存{len(bar_data)}条{symbol}数据")
            return df
            
        except Exception as e:
            logger.error(f"下载历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_data(self, symbol: str, start_date: str, end_date: str, 
                interval: str = "1m", exchange: str = "BINANCE") -> pd.DataFrame:
        """获取历史数据"""
        return self.db_manager.load_bars(symbol, exchange, start_date, end_date, interval)
    
    def get_latest_price(self, symbol: str, exchange: str = "BINANCE") -> Dict:
        """获取最新价格"""
        if exchange.upper() == "BINANCE":
            return self.binance_fetcher.fetch_ticker(symbol)
        else:
            logger.error(f"不支持的交易所: {exchange}")
            return {}
    
    def get_symbols_list(self, exchange: str = "BINANCE") -> List[str]:
        """获取交易品种列表"""
        try:
            if exchange.upper() == "BINANCE":
                url = f"{self.binance_fetcher.base_url}/api/v3/exchangeInfo"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                symbols = [s["symbol"] for s in data["symbols"] if s["status"] == "TRADING"]
                logger.info(f"获取了{len(symbols)}个交易品种")
                return symbols
            else:
                logger.error(f"不支持的交易所: {exchange}")
                return []
        except Exception as e:
            logger.error(f"获取交易品种列表失败: {e}")
            return []
    
    def export_to_csv(self, symbol: str, start_date: str, end_date: str, 
                     file_path: str, interval: str = "1m", exchange: str = "BINANCE"):
        """导出数据到CSV"""
        try:
            df = self.get_data(symbol, start_date, end_date, interval, exchange)
            if not df.empty:
                df.to_csv(file_path)
                logger.info(f"数据已导出到{file_path}")
            else:
                logger.warning("没有数据可导出")
        except Exception as e:
            logger.error(f"导出CSV数据失败: {e}")
    
    def close(self):
        """关闭数据管理器"""
        self.db_manager.close()
        logger.info("数据管理器已关闭")