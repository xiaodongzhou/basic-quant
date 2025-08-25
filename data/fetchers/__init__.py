"""
数据获取器模块
包含所有市场的数据获取器实现
"""

# 导入所有数据获取器以触发注册装饰器
from . import us_stock_fetcher
from . import china_stock_fetcher  
from . import us_futures_fetcher
from . import china_futures_fetcher
from . import crypto_fetcher

__all__ = [
    'us_stock_fetcher',
    'china_stock_fetcher', 
    'us_futures_fetcher',
    'china_futures_fetcher',
    'crypto_fetcher'
]