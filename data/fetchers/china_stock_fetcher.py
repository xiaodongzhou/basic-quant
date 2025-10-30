"""
中国A股数据获取器
支持AKShare和Tushare数据源
"""
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
from loguru import logger

from ..base_fetcher import BaseDataFetcher, BarData, TickerData, register_fetcher
from ..market_config import MarketType, DataSource

@register_fetcher(MarketType.CHINA_STOCK, DataSource.AKSHARE)
class AKShareChinaStockFetcher(BaseDataFetcher):
    """AKShare中国A股数据获取器"""
    
    def __init__(self, market_type: MarketType, data_source: DataSource, **kwargs):
        super().__init__(market_type, data_source, **kwargs)
        self.ak = None
        self._init_akshare()
    
    def _init_akshare(self):
        """初始化AKShare"""
        try:
            import akshare as ak
            self.ak = ak
            logger.info("AKShare初始化成功")
        except ImportError:
            logger.error("AKShare未安装，请运行: pip install akshare")
            raise ImportError("需要安装akshare包")
    
    def normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码"""
        symbol = symbol.upper()
        # 处理不同格式的股票代码
        if "." in symbol:
            code, exchange = symbol.split(".")
            return code
        return symbol
    
    def get_ak_symbol(self, symbol: str) -> str:
        """转换为AKShare格式的股票代码"""
        code = self.normalize_symbol(symbol)
        
        # A股代码通常是6位数字
        if len(code) == 6 and code.isdigit():
            return code
        
        # 处理其他格式
        return code
    
    def convert_interval(self, interval: str) -> str:
        """转换时间间隔格式"""
        interval_map = {
            "1m": "1",
            "5m": "5", 
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "1d": "daily"
        }
        return interval_map.get(interval, "daily")
    
    def infer_exchange(self, symbol: str) -> str:
        """推断交易所"""
        code = self.normalize_symbol(symbol)
        if not code.isdigit() or len(code) != 6:
            return "SH"
        
        # 根据代码前缀判断交易所
        if code.startswith(('60', '68', '11', '12', '13', '18')):
            return "SH"  # 上交所
        elif code.startswith(('00', '30', '12', '20')):
            return "SZ"  # 深交所
        else:
            return "SH"  # 默认上交所
    
    def fetch_bars(self, symbol: str, interval: str, start_time: datetime, 
                   end_time: datetime, **kwargs) -> List[BarData]:
        """获取历史K线数据"""
        try:
            ak_symbol = self.get_ak_symbol(symbol)
            ak_interval = self.convert_interval(interval)
            
            start_date = start_time.strftime("%Y%m%d")
            end_date = end_time.strftime("%Y%m%d")
            
            # 根据时间间隔选择不同的AKShare接口
            if ak_interval == "daily":
                # 日线数据
                df = self.ak.stock_zh_a_hist(
                    symbol=ak_symbol,
                    period="daily", 
                    start_date=start_date,
                    end_date=end_date,
                    adjust=""
                )
            else:
                # 分钟数据 (AKShare分钟数据功能有限)
                # 这里使用日线数据作为替代
                logger.warning(f"AKShare分钟数据支持有限，使用日线数据替代")
                df = self.ak.stock_zh_a_hist(
                    symbol=ak_symbol,
                    period="daily", 
                    start_date=start_date,
                    end_date=end_date,
                    adjust=""
                )
            
            if df is None or df.empty:
                logger.warning(f"AKShare未返回{symbol}的数据")
                return []
            
            # 数据预处理
            df.reset_index(drop=True, inplace=True)
            
            bars = []
            exchange = self.infer_exchange(symbol)
            
            for idx, row in df.iterrows():
                try:
                    # 处理日期格式
                    if '日期' in df.columns:
                        date_str = str(row['日期'])
                    else:
                        continue
                    
                    bar_time = pd.to_datetime(date_str).to_pydatetime()
                    
                    bar = BarData(
                        symbol=f"{ak_symbol}.{exchange}",
                        exchange=exchange,
                        datetime=bar_time,
                        interval=interval,
                        open_price=float(row.get('开盘', row.get('open', 0))),
                        high_price=float(row.get('最高', row.get('high', 0))),
                        low_price=float(row.get('最低', row.get('low', 0))),
                        close_price=float(row.get('收盘', row.get('close', 0))),
                        volume=float(row.get('成交量', row.get('volume', 0))),
                        turnover=float(row.get('成交额', row.get('amount', 0))),
                        open_interest=0.0
                    )
                    bars.append(bar)
                    
                except (ValueError, TypeError, KeyError) as e:
                    continue
            
            logger.info(f"AKShare获取{symbol} {len(bars)}条K线数据")
            return bars
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}历史数据")
            return []
    
    def fetch_ticker(self, symbol: str, **kwargs) -> Optional[TickerData]:
        """获取实时行情数据"""
        try:
            ak_symbol = self.get_ak_symbol(symbol)
            
            # 获取实时行情
            df = self.ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                logger.warning("AKShare未返回实时行情数据")
                return None
            
            # 查找指定股票
            stock_data = df[df['代码'] == ak_symbol]
            if stock_data.empty:
                logger.warning(f"未找到{symbol}的实时行情")
                return None
            
            row = stock_data.iloc[0]
            exchange = self.infer_exchange(symbol)
            
            ticker = TickerData(
                symbol=f"{ak_symbol}.{exchange}",
                exchange=exchange,
                price=float(row.get('最新价', 0)),
                change=float(row.get('涨跌额', 0)),
                change_percent=float(row.get('涨跌幅', 0)),
                volume=float(row.get('成交量', 0)),
                turnover=float(row.get('成交额', 0)),
                high=float(row.get('最高', 0)),
                low=float(row.get('最低', 0)),
                open=float(row.get('今开', 0)),
                prev_close=float(row.get('昨收', 0)),
                timestamp=datetime.now()
            )
            
            return ticker
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}实时行情")
            return None
    
    def get_symbols(self, **kwargs) -> List[str]:
        """获取可交易品种列表"""
        try:
            # 获取A股股票列表
            df = self.ak.stock_info_a_code_name()
            
            if df is None or df.empty:
                return []
            
            symbols = []
            for idx, row in df.iterrows():
                code = str(row.get('code', ''))
                if len(code) == 6 and code.isdigit():
                    exchange = self.infer_exchange(code)
                    symbols.append(f"{code}.{exchange}")
            
            logger.info(f"AKShare获取了{len(symbols)}个A股代码")
            return symbols[:100]  # 限制返回数量
            
        except Exception as e:
            self.handle_error(e, "获取股票列表")
            return []
    
    def handle_rate_limit(self):
        """处理API限制"""
        time.sleep(0.2)  # AKShare建议的延迟
    
    def get_exchange_name(self) -> str:
        """获取交易所名称"""
        return "CHINA_STOCK"

@register_fetcher(MarketType.CHINA_STOCK, DataSource.TUSHARE)
class TushareChinaStockFetcher(BaseDataFetcher):
    """Tushare中国A股数据获取器"""
    
    def __init__(self, market_type: MarketType, data_source: DataSource, **kwargs):
        super().__init__(market_type, data_source, **kwargs)
        self.ts = None
        self._init_tushare()
    
    def _init_tushare(self):
        """初始化Tushare"""
        try:
            import tushare as ts
            
            if not self.api_key:
                raise ValueError("Tushare需要API Token")
            
            ts.set_token(self.api_key)
            self.ts = ts.pro_api()
            logger.info("Tushare初始化成功")
            
        except ImportError:
            logger.error("Tushare未安装，请运行: pip install tushare")
            raise ImportError("需要安装tushare包")
    
    def normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码为Tushare格式"""
        symbol = symbol.upper()
        
        if "." in symbol:
            # 已经是完整格式
            return symbol
        elif len(symbol) == 6 and symbol.isdigit():
            # 推断交易所
            if symbol.startswith(('60', '68', '11', '12', '13', '18')):
                return f"{symbol}.SH"
            elif symbol.startswith(('00', '30', '12', '20')):
                return f"{symbol}.SZ"
            else:
                return f"{symbol}.SH"
        
        return symbol
    
    def convert_interval(self, interval: str) -> str:
        """转换时间间隔格式"""
        # Tushare主要支持日线和分钟线
        interval_map = {
            "1m": "1min",
            "5m": "5min", 
            "15m": "15min",
            "30m": "30min",
            "1h": "60min",
            "1d": "D"
        }
        return interval_map.get(interval, "D")
    
    def fetch_bars(self, symbol: str, interval: str, start_time: datetime, 
                   end_time: datetime, **kwargs) -> List[BarData]:
        """获取历史K线数据"""
        try:
            ts_symbol = self.normalize_symbol(symbol)
            ts_freq = self.convert_interval(interval)
            
            start_date = start_time.strftime("%Y%m%d")
            end_date = end_time.strftime("%Y%m%d")
            
            # 获取K线数据
            if ts_freq == "D":
                # 日线数据
                df = self.ts.daily(
                    ts_code=ts_symbol,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                # 分钟数据（需要更高级别的Tushare权限）
                logger.warning("Tushare分钟数据需要高级权限，使用日线数据")
                df = self.ts.daily(
                    ts_code=ts_symbol,
                    start_date=start_date,
                    end_date=end_date
                )
            
            if df is None or df.empty:
                logger.warning(f"Tushare未返回{symbol}的数据")
                return []
            
            bars = []
            
            for idx, row in df.iterrows():
                try:
                    bar_time = pd.to_datetime(row['trade_date']).to_pydatetime()
                    
                    bar = BarData(
                        symbol=ts_symbol,
                        exchange=ts_symbol.split('.')[1] if '.' in ts_symbol else 'SH',
                        datetime=bar_time,
                        interval=interval,
                        open_price=float(row['open']),
                        high_price=float(row['high']),
                        low_price=float(row['low']),
                        close_price=float(row['close']),
                        volume=float(row['vol']) * 100,  # Tushare成交量单位是手，需要乘以100
                        turnover=float(row['amount']) * 1000,  # 成交额单位转换
                        open_interest=0.0
                    )
                    bars.append(bar)
                    
                except (ValueError, TypeError, KeyError) as e:
                    continue
            
            # 按时间排序
            bars.sort(key=lambda x: x.datetime)
            
            logger.info(f"Tushare获取{symbol} {len(bars)}条K线数据")
            return bars
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}历史数据")
            return []
    
    def fetch_ticker(self, symbol: str, **kwargs) -> Optional[TickerData]:
        """获取实时行情数据"""
        try:
            ts_symbol = self.normalize_symbol(symbol)
            
            # 获取最新交易日的数据
            df = self.ts.daily(ts_code=ts_symbol, trade_date='')
            
            if df is None or df.empty:
                logger.warning(f"Tushare未返回{symbol}的最新数据")
                return None
            
            row = df.iloc[0]  # 最新一条记录
            
            # 计算涨跌额和涨跌幅（基于前一交易日）
            prev_df = self.ts.daily(ts_code=ts_symbol, limit=2)
            prev_close = 0
            if len(prev_df) >= 2:
                prev_close = float(prev_df.iloc[1]['close'])
            
            current_price = float(row['close'])
            change = current_price - prev_close if prev_close > 0 else 0
            change_percent = (change / prev_close * 100) if prev_close > 0 else 0
            
            ticker = TickerData(
                symbol=ts_symbol,
                exchange=ts_symbol.split('.')[1] if '.' in ts_symbol else 'SH',
                price=current_price,
                change=change,
                change_percent=change_percent,
                volume=float(row['vol']) * 100,
                turnover=float(row['amount']) * 1000,
                high=float(row['high']),
                low=float(row['low']),
                open=float(row['open']),
                prev_close=prev_close,
                timestamp=datetime.now()
            )
            
            return ticker
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}实时行情")
            return None
    
    def get_symbols(self, **kwargs) -> List[str]:
        """获取可交易品种列表"""
        try:
            # 获取股票基本信息
            df = self.ts.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
            
            if df is None or df.empty:
                return []
            
            symbols = df['ts_code'].tolist()
            logger.info(f"Tushare获取了{len(symbols)}个A股代码")
            
            return symbols[:100]  # 限制返回数量
            
        except Exception as e:
            self.handle_error(e, "获取股票列表")
            return []
    
    def handle_rate_limit(self):
        """处理API限制 - Tushare有调用频率限制"""
        time.sleep(0.5)  # 500ms延迟
    
    def get_exchange_name(self) -> str:
        """获取交易所名称"""
        return "CHINA_STOCK"