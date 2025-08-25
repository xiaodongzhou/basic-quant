"""
中国商品期货数据获取器
支持AKShare数据源获取国内期货数据
"""
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
from loguru import logger

from ..base_fetcher import BaseDataFetcher, BarData, TickerData, register_fetcher
from ..market_config import MarketType, DataSource

@register_fetcher(MarketType.CHINA_FUTURES, DataSource.AKSHARE)
class AKShareChinaFuturesFetcher(BaseDataFetcher):
    """AKShare中国商品期货数据获取器"""
    
    def __init__(self, market_type: MarketType, data_source: DataSource, **kwargs):
        super().__init__(market_type, data_source, **kwargs)
        self.ak = None
        self._init_akshare()
        
        # 中国期货交易所映射
        self.exchange_map = {
            # 上海期货交易所 (SHFE)
            'cu': 'SHFE',   # 铜
            'al': 'SHFE',   # 铝
            'zn': 'SHFE',   # 锌
            'pb': 'SHFE',   # 铅
            'ni': 'SHFE',   # 镍
            'sn': 'SHFE',   # 锡
            'au': 'SHFE',   # 黄金
            'ag': 'SHFE',   # 白银
            'rb': 'SHFE',   # 螺纹钢
            'wr': 'SHFE',   # 线材
            'hc': 'SHFE',   # 热轧卷板
            'ss': 'SHFE',   # 不锈钢
            'fu': 'SHFE',   # 燃料油
            'bu': 'SHFE',   # 石油沥青
            'ru': 'SHFE',   # 天然橡胶
            'nr': 'SHFE',   # 20号胶
            'sp': 'SHFE',   # 纸浆
            
            # 大连商品交易所 (DCE)
            'c': 'DCE',     # 玉米
            'cs': 'DCE',    # 玉米淀粉
            's': 'DCE',     # 大豆1号
            'a': 'DCE',     # 豆一
            'm': 'DCE',     # 豆粕
            'y': 'DCE',     # 豆油
            'p': 'DCE',     # 棕榈油
            'v': 'DCE',     # PVC
            'l': 'DCE',     # 聚乙烯
            'pp': 'DCE',    # 聚丙烯
            'j': 'DCE',     # 焦炭
            'jm': 'DCE',    # 焦煤
            'i': 'DCE',     # 铁矿石
            'jd': 'DCE',    # 鸡蛋
            'fb': 'DCE',    # 纤维板
            'bb': 'DCE',    # 胶合板
            'pg': 'DCE',    # 液化石油气
            'eb': 'DCE',    # 苯乙烯
            'eg': 'DCE',    # 乙二醇
            'rr': 'DCE',    # 粳米
            'lh': 'DCE',    # 生猪
            
            # 郑州商品交易所 (CZCE)
            'TA': 'CZCE',   # PTA
            'MA': 'CZCE',   # 甲醇
            'FG': 'CZCE',   # 玻璃
            'OI': 'CZCE',   # 菜籽油
            'RM': 'CZCE',   # 菜籽粕
            'RS': 'CZCE',   # 菜籽
            'CF': 'CZCE',   # 棉花
            'CY': 'CZCE',   # 棉纱
            'SR': 'CZCE',   # 白糖
            'ZC': 'CZCE',   # 动力煤
            'JR': 'CZCE',   # 粳稻
            'LR': 'CZCE',   # 晚籼稻
            'WH': 'CZCE',   # 强麦
            'PM': 'CZCE',   # 普麦
            'RI': 'CZCE',   # 早籼稻
            'SF': 'CZCE',   # 硅铁
            'SM': 'CZCE',   # 锰硅
            'UR': 'CZCE',   # 尿素
            'SA': 'CZCE',   # 纯碱
            'PF': 'CZCE',   # 短纤
            'PK': 'CZCE',   # 花生
            'AP': 'CZCE',   # 苹果
            'CJ': 'CZCE',   # 红枣
            
            # 中国金融期货交易所 (CFFEX)
            'IF': 'CFFEX',  # 沪深300股指期货
            'IC': 'CFFEX',  # 中证500股指期货
            'IH': 'CFFEX',  # 上证50股指期货
            'T': 'CFFEX',   # 10年期国债期货
            'TF': 'CFFEX',  # 5年期国债期货
            'TS': 'CFFEX',  # 2年期国债期货
        }
    
    def _init_akshare(self):
        """初始化AKShare"""
        try:
            import akshare as ak
            self.ak = ak
            logger.info("AKShare期货模块初始化成功")
        except ImportError:
            logger.error("AKShare未安装，请运行: pip install akshare")
            raise ImportError("需要安装akshare包")
    
    def normalize_symbol(self, symbol: str) -> str:
        """标准化期货代码"""
        symbol = symbol.upper()
        
        # 移除可能的交易所后缀
        if '.' in symbol:
            symbol = symbol.split('.')[0]
        
        # 处理不同的代码格式
        # 例: rb2310 -> rb2310, RB2310 -> RB2310
        return symbol
    
    def get_base_symbol(self, symbol: str) -> str:
        """提取期货品种基础代码"""
        symbol = self.normalize_symbol(symbol)
        
        # 分离品种代码和合约月份
        base = ""
        for i, char in enumerate(symbol):
            if char.isdigit():
                base = symbol[:i]
                break
        
        return base.lower()
    
    def get_exchange_by_symbol(self, symbol: str) -> str:
        """根据期货代码获取交易所"""
        base_symbol = self.get_base_symbol(symbol)
        return self.exchange_map.get(base_symbol, 'UNKNOWN')
    
    def convert_interval(self, interval: str) -> str:
        """转换时间间隔格式"""
        # AKShare期货数据主要支持日线
        interval_map = {
            "1m": "1",
            "5m": "5", 
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "1d": "daily"
        }
        return interval_map.get(interval, "daily")
    
    def fetch_bars(self, symbol: str, interval: str, start_time: datetime, 
                   end_time: datetime, **kwargs) -> List[BarData]:
        """获取历史K线数据"""
        try:
            ak_symbol = self.normalize_symbol(symbol)
            ak_interval = self.convert_interval(interval)
            
            start_date = start_time.strftime("%Y%m%d")
            end_date = end_time.strftime("%Y%m%d")
            
            # 尝试获取期货历史数据
            try:
                # 使用AKShare的期货历史数据接口
                df = self.ak.futures_zh_daily_sina(symbol=ak_symbol)
                
                if df is None or df.empty:
                    logger.warning(f"AKShare未返回{symbol}的期货数据")
                    return []
                
                # 过滤时间范围
                df['date'] = pd.to_datetime(df['date'])
                mask = (df['date'] >= start_time) & (df['date'] <= end_time)
                df = df.loc[mask]
                
            except Exception as e:
                logger.warning(f"使用新浪期货接口失败，尝试其他接口: {e}")
                
                # 尝试使用主力合约数据
                try:
                    base_symbol = self.get_base_symbol(symbol)
                    df = self.ak.futures_main_sina(symbol=base_symbol)
                    
                    if df is None or df.empty:
                        return []
                        
                except Exception as e2:
                    logger.error(f"获取主力合约数据也失败: {e2}")
                    return []
            
            bars = []
            exchange = self.get_exchange_by_symbol(symbol)
            
            for idx, row in df.iterrows():
                try:
                    # 处理不同的日期列名
                    date_col = 'date' if 'date' in df.columns else 'datetime'
                    if date_col not in df.columns:
                        # 尝试其他可能的日期列名
                        date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
                        if date_cols:
                            date_col = date_cols[0]
                        else:
                            continue
                    
                    bar_time = pd.to_datetime(row[date_col]).to_pydatetime()
                    
                    # 处理价格数据（不同接口可能有不同的列名）
                    open_price = self._get_price_value(row, ['open', '开盘价', 'open_price'])
                    high_price = self._get_price_value(row, ['high', '最高价', 'high_price'])
                    low_price = self._get_price_value(row, ['low', '最低价', 'low_price'])
                    close_price = self._get_price_value(row, ['close', '收盘价', 'close_price'])
                    volume = self._get_price_value(row, ['volume', '成交量', 'vol'])
                    
                    if not all([open_price, high_price, low_price, close_price]):
                        continue
                    
                    bar = BarData(
                        symbol=ak_symbol,
                        exchange=exchange,
                        datetime=bar_time,
                        interval=interval,
                        open_price=float(open_price),
                        high_price=float(high_price),
                        low_price=float(low_price),
                        close_price=float(close_price),
                        volume=float(volume or 0),
                        turnover=0.0,  # 部分数据源可能不提供
                        open_interest=0.0  # 持仓量数据需要单独获取
                    )
                    bars.append(bar)
                    
                except (ValueError, TypeError, KeyError) as e:
                    continue
            
            logger.info(f"AKShare获取{symbol} {len(bars)}条期货K线数据")
            return bars
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}期货历史数据")
            return []
    
    def _get_price_value(self, row, possible_columns):
        """从可能的列名中获取价格数据"""
        for col in possible_columns:
            if col in row.index and pd.notna(row[col]):
                return row[col]
        return None
    
    def fetch_ticker(self, symbol: str, **kwargs) -> Optional[TickerData]:
        """获取实时行情数据"""
        try:
            ak_symbol = self.normalize_symbol(symbol)
            
            # 获取期货实时行情
            try:
                df = self.ak.futures_zh_spot()
                
                if df is None or df.empty:
                    logger.warning("AKShare未返回期货实时行情数据")
                    return None
                
                # 查找指定期货合约
                symbol_data = df[df['symbol'].str.contains(ak_symbol, case=False, na=False)]
                if symbol_data.empty:
                    # 尝试用基础品种代码搜索
                    base_symbol = self.get_base_symbol(symbol)
                    symbol_data = df[df['symbol'].str.contains(base_symbol, case=False, na=False)]
                    
                if symbol_data.empty:
                    logger.warning(f"未找到{symbol}的期货实时行情")
                    return None
                
                row = symbol_data.iloc[0]
                exchange = self.get_exchange_by_symbol(symbol)
                
                ticker = TickerData(
                    symbol=ak_symbol,
                    exchange=exchange,
                    price=float(row.get('current_price', row.get('price', 0))),
                    change=float(row.get('change', 0)),
                    change_percent=float(row.get('change_percent', 0)),
                    volume=float(row.get('volume', 0)),
                    high=float(row.get('high', 0)),
                    low=float(row.get('low', 0)),
                    open=float(row.get('open', 0)),
                    prev_close=float(row.get('pre_close', 0)),
                    timestamp=datetime.now()
                )
                
                return ticker
                
            except Exception as e:
                logger.warning(f"获取期货实时行情失败: {e}")
                return None
            
        except Exception as e:
            self.handle_error(e, f"获取{symbol}期货实时行情")
            return None
    
    def get_symbols(self, **kwargs) -> List[str]:
        """获取可交易品种列表"""
        try:
            # 获取期货品种列表
            symbols = []
            
            # 从交易所映射中构建常见合约代码
            current_year = datetime.now().year % 100  # 两位年份
            current_month = datetime.now().month
            
            for base_symbol, exchange in self.exchange_map.items():
                # 生成近几个月的合约
                for month_offset in range(0, 6):  # 当前月及后续5个月
                    target_month = current_month + month_offset
                    target_year = current_year
                    
                    if target_month > 12:
                        target_month -= 12
                        target_year += 1
                    
                    # 构建合约代码
                    if exchange == 'CZCE':
                        # 郑商所用大写字母
                        contract = f"{base_symbol.upper()}{target_year:02d}{target_month:02d}"
                    else:
                        # 其他交易所用小写字母
                        contract = f"{base_symbol.lower()}{target_year:02d}{target_month:02d}"
                    
                    symbols.append(contract)
            
            # 添加主力合约和连续合约
            main_contracts = []
            for base_symbol in self.exchange_map.keys():
                if base_symbol.isupper():  # CZCE
                    main_contracts.extend([f"{base_symbol}M", f"{base_symbol}0"])
                else:
                    main_contracts.extend([f"{base_symbol}m", f"{base_symbol}0"])
            
            all_symbols = symbols + main_contracts
            
            logger.info(f"生成了{len(all_symbols)}个中国期货合约代码")
            return all_symbols[:100]  # 限制返回数量
            
        except Exception as e:
            self.handle_error(e, "获取期货品种列表")
            return []
    
    def get_futures_info(self, symbol: str) -> Dict[str, Any]:
        """获取期货合约信息"""
        base_symbol = self.get_base_symbol(symbol)
        exchange = self.get_exchange_by_symbol(symbol)
        
        # 品种中文名映射
        name_map = {
            'cu': '铜', 'al': '铝', 'zn': '锌', 'pb': '铅', 'ni': '镍', 'sn': '锡',
            'au': '黄金', 'ag': '白银', 'rb': '螺纹钢', 'hc': '热轧卷板',
            'fu': '燃料油', 'bu': '沥青', 'ru': '橡胶', 'sp': '纸浆',
            'c': '玉米', 'a': '豆一', 'm': '豆粕', 'y': '豆油', 'p': '棕榈油',
            'v': 'PVC', 'l': '聚乙烯', 'pp': '聚丙烯', 'j': '焦炭', 'jm': '焦煤',
            'i': '铁矿石', 'jd': '鸡蛋', 'pg': '液化石油气',
            'TA': 'PTA', 'MA': '甲醇', 'FG': '玻璃', 'OI': '菜油', 'CF': '棉花',
            'SR': '白糖', 'ZC': '动力煤', 'UR': '尿素', 'SA': '纯碱',
            'IF': '沪深300', 'IC': '中证500', 'IH': '上证50', 'T': '10年国债'
        }
        
        return {
            "name": name_map.get(base_symbol, base_symbol),
            "base_symbol": base_symbol,
            "exchange": exchange,
            "category": self._get_category(base_symbol),
            "full_symbol": symbol
        }
    
    def _get_category(self, base_symbol: str) -> str:
        """获取期货品种分类"""
        categories = {
            "金属": ['cu', 'al', 'zn', 'pb', 'ni', 'sn', 'au', 'ag', 'rb', 'hc', 'ss'],
            "能源": ['fu', 'bu', 'ru', 'nr', 'sp', 'ma', 'pg', 'eb', 'eg', 'ZC', 'TA'],
            "农产品": ['c', 'cs', 's', 'a', 'm', 'y', 'p', 'jd', 'fb', 'bb', 'rr', 'lh',
                     'CF', 'CY', 'SR', 'JR', 'LR', 'WH', 'PM', 'RI', 'PK', 'AP', 'CJ'],
            "化工": ['v', 'l', 'pp', 'FG', 'OI', 'RM', 'RS', 'SF', 'SM', 'UR', 'SA', 'PF'],
            "金融": ['IF', 'IC', 'IH', 'T', 'TF', 'TS'],
            "黑色": ['j', 'jm', 'i', 'rb', 'hc', 'ss']
        }
        
        for category, symbols in categories.items():
            if base_symbol in symbols:
                return category
        
        return "其他"
    
    def handle_rate_limit(self):
        """处理API限制"""
        time.sleep(0.3)  # 300ms延迟
    
    def get_exchange_name(self) -> str:
        """获取交易所名称"""
        return "CHINA_FUTURES"