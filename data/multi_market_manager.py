"""
统一多市场数据管理器
整合美股、美国期货、中国A股、中国商品期货的数据获取和管理
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
import pandas as pd
from loguru import logger

from .market_config import MarketType, DataSource, get_market_type_by_symbol, get_market_config
from .base_fetcher import BaseDataFetcher, BarData, TickerData, DataFetcherFactory
from .data_manager import DatabaseManager

# 导入所有数据获取器以触发注册
from .fetchers import us_stock_fetcher, china_stock_fetcher, us_futures_fetcher, china_futures_fetcher

class MultiMarketDataManager:
    """统一多市场数据管理器"""
    
    def __init__(self, db_path: str = None, **config):
        """
        初始化多市场数据管理器
        
        Args:
            db_path: 数据库路径
            **config: 各数据源的配置（如API密钥等）
        """
        self.db_manager = DatabaseManager(db_path)
        self.config = config
        self.fetchers = {}  # 缓存的数据获取器
        
        logger.info("多市场数据管理器初始化完成")
        logger.info(f"支持的市场组合: {DataFetcherFactory.get_supported_combinations()}")
    
    def _get_fetcher(self, market_type: MarketType, data_source: DataSource = None) -> BaseDataFetcher:
        """获取数据获取器实例"""
        if data_source is None:
            # 使用默认数据源
            market_config = get_market_config(market_type)
            if not market_config:
                raise ValueError(f"不支持的市场类型: {market_type}")
            data_source = market_config.default_source
        
        # 检查是否已缓存
        key = (market_type, data_source)
        if key in self.fetchers:
            return self.fetchers[key]
        
        # 创建新的获取器实例
        fetcher_config = {}
        
        # 根据数据源添加相应的配置
        if data_source == DataSource.ALPHA_VANTAGE:
            fetcher_config['api_key'] = self.config.get('alphavantage_api_key')
        elif data_source == DataSource.TUSHARE:
            fetcher_config['api_key'] = self.config.get('tushare_token')
        
        fetcher = DataFetcherFactory.create(market_type, data_source, **fetcher_config)
        self.fetchers[key] = fetcher
        
        return fetcher
    
    def auto_detect_market(self, symbol: str) -> Optional[MarketType]:
        """自动检测品种所属市场"""
        market_type = get_market_type_by_symbol(symbol)
        if market_type:
            logger.info(f"自动检测 {symbol} 属于 {market_type.value} 市场")
        else:
            logger.warning(f"无法自动检测 {symbol} 的市场类型")
        return market_type
    
    def get_unified_data(self, symbol: str, start_date: str, end_date: str,
                        interval: str = "1d", market_type: MarketType = None,
                        data_source: DataSource = None, force_update: bool = False) -> pd.DataFrame:
        """
        获取统一格式的历史数据
        
        Args:
            symbol: 品种代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD) 
            interval: 时间间隔
            market_type: 指定市场类型（None则自动检测）
            data_source: 指定数据源（None则使用默认）
            force_update: 是否强制更新
            
        Returns:
            pd.DataFrame: 统一格式的K线数据
        """
        try:
            # 自动检测市场类型
            if market_type is None:
                market_type = self.auto_detect_market(symbol)
                if market_type is None:
                    raise ValueError(f"无法确定 {symbol} 的市场类型，请手动指定")
            
            # 检查本地是否有缓存数据
            if not force_update:
                cached_data = self._load_cached_data(symbol, start_date, end_date, interval, market_type)
                if not cached_data.empty:
                    logger.info(f"使用本地缓存数据: {symbol}")
                    return cached_data
            
            # 获取数据获取器
            fetcher = self._get_fetcher(market_type, data_source)
            
            # 获取历史数据
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            
            logger.info(f"从 {fetcher.__class__.__name__} 获取 {symbol} 数据")
            bars = fetcher.fetch_bars(symbol, interval, start_dt, end_dt)
            
            if not bars:
                logger.warning(f"未获取到 {symbol} 的数据")
                return pd.DataFrame()
            
            # 保存到数据库
            self._save_bars_to_db(bars, market_type)
            
            # 转换为统一格式的DataFrame
            df = self._bars_to_dataframe(bars)
            
            logger.info(f"成功获取 {symbol} 共 {len(df)} 条数据")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_real_time_data(self, symbols: Union[str, List[str]], 
                          market_type: MarketType = None,
                          data_source: DataSource = None) -> Dict[str, TickerData]:
        """
        获取实时行情数据
        
        Args:
            symbols: 单个品种代码或品种列表
            market_type: 指定市场类型
            data_source: 指定数据源
            
        Returns:
            Dict[str, TickerData]: 实时行情数据字典
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        results = {}
        
        # 按市场类型分组
        market_groups = {}
        for symbol in symbols:
            if market_type is None:
                symbol_market = self.auto_detect_market(symbol)
            else:
                symbol_market = market_type
            
            if symbol_market is None:
                logger.warning(f"跳过未知市场类型的品种: {symbol}")
                continue
            
            if symbol_market not in market_groups:
                market_groups[symbol_market] = []
            market_groups[symbol_market].append(symbol)
        
        # 分市场获取数据
        for market, symbol_list in market_groups.items():
            try:
                fetcher = self._get_fetcher(market, data_source)
                
                for symbol in symbol_list:
                    ticker = fetcher.fetch_ticker(symbol)
                    if ticker:
                        results[symbol] = ticker
                    else:
                        logger.warning(f"获取 {symbol} 实时行情失败")
                        
            except Exception as e:
                logger.error(f"获取 {market.value} 市场实时数据失败: {e}")
        
        return results
    
    def get_symbols_by_market(self, market_type: MarketType, 
                             data_source: DataSource = None) -> List[str]:
        """
        获取指定市场的品种列表
        
        Args:
            market_type: 市场类型
            data_source: 数据源
            
        Returns:
            List[str]: 品种代码列表
        """
        try:
            fetcher = self._get_fetcher(market_type, data_source)
            symbols = fetcher.get_symbols()
            
            logger.info(f"获取 {market_type.value} 市场 {len(symbols)} 个品种")
            return symbols
            
        except Exception as e:
            logger.error(f"获取 {market_type.value} 市场品种列表失败: {e}")
            return []
    
    def search_symbols(self, keyword: str, market_types: List[MarketType] = None) -> Dict[MarketType, List[str]]:
        """
        搜索品种代码
        
        Args:
            keyword: 搜索关键词
            market_types: 指定搜索的市场类型列表
            
        Returns:
            Dict[MarketType, List[str]]: 按市场分类的搜索结果
        """
        if market_types is None:
            market_types = list(MarketType)
        
        results = {}
        keyword = keyword.upper()
        
        for market_type in market_types:
            try:
                symbols = self.get_symbols_by_market(market_type)
                matched = [s for s in symbols if keyword in s.upper()]
                
                if matched:
                    results[market_type] = matched
                    
            except Exception as e:
                logger.warning(f"搜索 {market_type.value} 市场时出错: {e}")
        
        return results
    
    def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览信息"""
        overview = {
            "supported_markets": {},
            "data_sources": {},
            "cached_symbols": self._get_cached_symbols_count()
        }
        
        # 统计支持的市场
        for market_type in MarketType:
            try:
                config = get_market_config(market_type)
                if config:
                    overview["supported_markets"][market_type.value] = {
                        "name": config.market_name,
                        "currency": config.currency,
                        "timezone": config.timezone,
                        "intervals": config.supported_intervals,
                        "sources": [ds.value for ds in config.data_sources]
                    }
            except:
                continue
        
        # 统计数据源
        for combination in DataFetcherFactory.get_supported_combinations():
            market, source = combination
            if source.value not in overview["data_sources"]:
                overview["data_sources"][source.value] = []
            overview["data_sources"][source.value].append(market.value)
        
        return overview
    
    def _load_cached_data(self, symbol: str, start_date: str, end_date: str,
                         interval: str, market_type: MarketType) -> pd.DataFrame:
        """从本地数据库加载缓存数据"""
        try:
            # 确定交易所名称
            if market_type == MarketType.CRYPTO:
                exchange = "BINANCE"
            else:
                fetcher = self._get_fetcher(market_type)
                exchange = fetcher.get_exchange_name()
            
            return self.db_manager.load_bars(symbol, exchange, start_date, end_date, interval)
            
        except Exception as e:
            logger.warning(f"加载缓存数据失败: {e}")
            return pd.DataFrame()
    
    def _save_bars_to_db(self, bars: List[BarData], market_type: MarketType):
        """保存K线数据到数据库"""
        try:
            bar_dicts = [bar.to_dict() for bar in bars]
            self.db_manager.save_bars(bar_dicts)
        except Exception as e:
            logger.error(f"保存数据到数据库失败: {e}")
    
    def _bars_to_dataframe(self, bars: List[BarData]) -> pd.DataFrame:
        """将BarData列表转换为统一格式的DataFrame"""
        if not bars:
            return pd.DataFrame()
        
        data = []
        for bar in bars:
            data.append({
                'datetime': bar.datetime,
                'open': bar.open_price,
                'high': bar.high_price,
                'low': bar.low_price,
                'close': bar.close_price,
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
    
    def _get_cached_symbols_count(self) -> Dict[str, int]:
        """统计缓存的品种数量"""
        try:
            query = """
                SELECT exchange, COUNT(DISTINCT symbol) as count
                FROM bar_data 
                GROUP BY exchange
            """
            
            cursor = self.db_manager.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            return {row[0]: row[1] for row in results}
            
        except Exception as e:
            logger.warning(f"统计缓存数据失败: {e}")
            return {}
    
    def export_unified_data(self, symbols: List[str], start_date: str, end_date: str,
                           output_path: str, interval: str = "1d", format: str = "csv"):
        """
        导出统一格式的多市场数据
        
        Args:
            symbols: 品种代码列表
            start_date: 开始日期
            end_date: 结束日期
            output_path: 输出路径
            interval: 时间间隔
            format: 输出格式 (csv, excel, parquet)
        """
        try:
            all_data = {}
            
            for symbol in symbols:
                df = self.get_unified_data(symbol, start_date, end_date, interval)
                if not df.empty:
                    all_data[symbol] = df
            
            if not all_data:
                logger.warning("没有数据可导出")
                return
            
            # 合并数据
            combined_df = pd.DataFrame()
            for symbol, df in all_data.items():
                df_copy = df.copy()
                df_copy['symbol'] = symbol
                combined_df = pd.concat([combined_df, df_copy])
            
            # 导出数据
            output_path = Path(output_path)
            
            if format.lower() == "csv":
                combined_df.to_csv(output_path)
            elif format.lower() == "excel":
                combined_df.to_excel(output_path)
            elif format.lower() == "parquet":
                combined_df.to_parquet(output_path)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            logger.info(f"成功导出 {len(symbols)} 个品种的数据到 {output_path}")
            
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
    
    def get_data_quality_report(self, symbol: str, start_date: str, end_date: str,
                               interval: str = "1d") -> Dict[str, Any]:
        """
        获取数据质量报告
        
        Args:
            symbol: 品种代码
            start_date: 开始日期
            end_date: 结束日期
            interval: 时间间隔
            
        Returns:
            Dict[str, Any]: 数据质量报告
        """
        try:
            df = self.get_unified_data(symbol, start_date, end_date, interval)
            
            if df.empty:
                return {"error": "无数据"}
            
            # 计算数据质量指标
            report = {
                "symbol": symbol,
                "period": f"{start_date} to {end_date}",
                "total_records": len(df),
                "missing_values": df.isnull().sum().to_dict(),
                "data_range": {
                    "start": str(df.index.min()),
                    "end": str(df.index.max()),
                },
                "price_statistics": {
                    "min_price": df['low'].min(),
                    "max_price": df['high'].max(),
                    "avg_volume": df['volume'].mean(),
                    "total_volume": df['volume'].sum()
                },
                "data_gaps": self._detect_data_gaps(df, interval),
                "anomalies": self._detect_price_anomalies(df)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成数据质量报告失败: {e}")
            return {"error": str(e)}
    
    def _detect_data_gaps(self, df: pd.DataFrame, interval: str) -> List[Dict]:
        """检测数据缺口"""
        gaps = []
        
        # 根据间隔类型计算期望的时间差
        interval_map = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "30m": timedelta(minutes=30),
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "1d": timedelta(days=1)
        }
        
        expected_delta = interval_map.get(interval, timedelta(days=1))
        
        for i in range(1, len(df)):
            actual_delta = df.index[i] - df.index[i-1]
            if actual_delta > expected_delta * 1.5:  # 允许50%的误差
                gaps.append({
                    "start": str(df.index[i-1]),
                    "end": str(df.index[i]),
                    "duration": str(actual_delta)
                })
        
        return gaps
    
    def _detect_price_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """检测价格异常"""
        anomalies = []
        
        # 计算价格变化率
        df_copy = df.copy()
        df_copy['price_change_pct'] = df_copy['close'].pct_change()
        
        # 检测异常大的价格变动
        threshold = df_copy['price_change_pct'].std() * 3  # 3倍标准差
        
        for idx, row in df_copy.iterrows():
            if abs(row['price_change_pct']) > threshold:
                anomalies.append({
                    "datetime": str(idx),
                    "price_change_pct": row['price_change_pct'],
                    "close_price": row['close'],
                    "type": "large_price_movement"
                })
        
        return anomalies
    
    def close(self):
        """关闭数据管理器"""
        self.db_manager.close()
        logger.info("多市场数据管理器已关闭")