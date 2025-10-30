# 统一多市场数据管理系统

## 🌍 概述

本系统是一个统一的多市场数据管理解决方案，支持**美股**、**美国期货**、**中国A股**和**中国商品期货**的数据获取和管理。通过统一的接口，您可以无缝处理不同市场的数据，而无需为每个市场编写不同的数据处理代码。

## ✨ 核心特性

### 🎯 统一接口
- **一套API处理所有市场**：无论是美股AAPL还是A股000001.SZ，使用相同的接口
- **自动市场识别**：根据品种代码自动识别所属市场
- **统一数据格式**：所有市场数据标准化为相同的DataFrame格式

### 🌐 多市场支持
- **美股市场**：Yahoo Finance、Alpha Vantage
- **美国期货**：Yahoo Finance（ES=F, GC=F等）
- **中国A股**：AKShare、Tushare
- **中国商品期货**：AKShare（螺纹钢、铜、黄金等）
- **加密货币**：Binance（向后兼容）

### 🔧 智能特性
- **自动缓存**：本地SQLite数据库缓存，避免重复请求
- **数据质量检查**：自动检测数据缺口和价格异常
- **灵活配置**：支持多种数据源和API密钥配置
- **批量处理**：支持多品种同时处理

## 🚀 快速开始

### 基础使用

```python
from data.multi_market_manager import MultiMarketDataManager

# 初始化管理器
manager = MultiMarketDataManager()

# 获取美股数据（自动识别市场）
aapl_data = manager.get_unified_data(
    symbol="AAPL",
    start_date="2023-01-01",
    end_date="2023-12-31",
    interval="1d"
)

# 获取A股数据
ping_an_data = manager.get_unified_data(
    symbol="000001.SZ", 
    start_date="2023-01-01",
    end_date="2023-12-31",
    interval="1d"
)

# 获取期货数据
gold_data = manager.get_unified_data(
    symbol="GC=F",  # 黄金期货
    start_date="2023-01-01", 
    end_date="2023-12-31",
    interval="1d"
)
```

### 高级配置

```python
# 带API密钥的初始化
manager = MultiMarketDataManager(
    alphavantage_api_key="YOUR_ALPHA_VANTAGE_KEY",
    tushare_token="YOUR_TUSHARE_TOKEN"
)

# 指定特定数据源
from data.market_config import MarketType, DataSource

df = manager.get_unified_data(
    symbol="000001.SZ",
    start_date="2023-01-01",
    end_date="2023-12-31", 
    market_type=MarketType.CHINA_STOCK,
    data_source=DataSource.AKSHARE
)
```

## 📊 支持的市场和数据源

| 市场 | 数据源 | 品种示例 | API密钥 |
|------|--------|----------|---------|
| 美股 | Yahoo Finance | AAPL, TSLA, MSFT | 不需要 |
| 美股 | Alpha Vantage | AAPL, TSLA, MSFT | 需要 |
| 美国期货 | Yahoo Finance | ES=F, GC=F, CL=F | 不需要 |
| 中国A股 | AKShare | 000001.SZ, 600000.SH | 不需要 |
| 中国A股 | Tushare | 000001.SZ, 600000.SH | 需要 |
| 中国期货 | AKShare | rb2310, cu2309, au2312 | 不需要 |
| 加密货币 | Binance | BTCUSDT, ETHUSDT | 不需要 |

## 🔍 品种代码格式

### 自动识别规则

系统可以自动识别以下格式的品种代码：

- **美股**：`AAPL`, `TSLA`, `MSFT`
- **美国期货**：`ES=F`, `GC=F`, `CL=F`
- **中国A股**：`000001.SZ`, `600000.SH`
- **中国期货**：`rb2310`, `cu2309`, `au2312`
- **加密货币**：`BTCUSDT`, `ETHUSDT`

## 📈 统一数据格式

所有市场的数据都标准化为相同格式：

```python
# DataFrame列结构
columns = [
    'open',          # 开盘价
    'high',          # 最高价
    'low',           # 最低价
    'close',         # 收盘价
    'volume',        # 成交量
    'turnover',      # 成交额
    'open_interest', # 持仓量（期货）
    'symbol',        # 品种代码
    'exchange',      # 交易所
    'interval'       # 时间间隔
]

# 时间索引：datetime
```

## 🎯 与量化策略集成

### 替换原有数据管理器

```python
# 旧代码
from data.data_manager import DataManager
data_manager = DataManager()

# 新代码 - 支持多市场
from data.multi_market_manager import MultiMarketDataManager
data_manager = MultiMarketDataManager()

# API保持兼容，但现在支持所有市场
```

### 跨市场策略示例

```python
class CrossMarketStrategy:
    def __init__(self):
        self.data_manager = MultiMarketDataManager()
    
    def run_global_pairs_trading(self):
        # 全球配对交易策略
        symbols = [
            "AAPL",      # 美股科技
            "000001.SZ", # A股金融  
            "GC=F",      # 黄金期货
            "cu2309",    # 铜期货
        ]
        
        # 获取所有数据（统一格式）
        data = {}
        for symbol in symbols:
            df = self.data_manager.get_unified_data(
                symbol=symbol,
                start_date="2023-01-01",
                end_date="2023-12-31"
            )
            if not df.empty:
                data[symbol] = df
        
        # 计算相关性矩阵
        prices = pd.DataFrame({
            symbol: df['close'] for symbol, df in data.items()
        })
        correlation = prices.corr()
        
        return correlation
```

## 🛠️ 安装依赖

### 核心依赖

```bash
pip install pandas numpy loguru requests
```

### 可选依赖（根据需要的数据源）

```bash
# 中国市场数据
pip install akshare tushare

# 美股高级数据（如需Alpha Vantage）
# 注册获取免费API密钥：https://www.alphavantage.co/
```

## 📖 API 参考

### MultiMarketDataManager

#### 初始化

```python
manager = MultiMarketDataManager(
    db_path=None,                    # 数据库路径
    alphavantage_api_key=None,       # Alpha Vantage API密钥
    tushare_token=None               # Tushare Token
)
```

#### 主要方法

##### get_unified_data()

获取统一格式的历史数据

```python
df = manager.get_unified_data(
    symbol: str,                     # 品种代码
    start_date: str,                 # 开始日期 YYYY-MM-DD
    end_date: str,                   # 结束日期 YYYY-MM-DD
    interval: str = "1d",            # 时间间隔
    market_type: MarketType = None,  # 市场类型（可选）
    data_source: DataSource = None,  # 数据源（可选）
    force_update: bool = False       # 强制更新
)
```

##### get_real_time_data()

获取实时行情数据

```python
tickers = manager.get_real_time_data(
    symbols: Union[str, List[str]],  # 品种代码或列表
    market_type: MarketType = None,  # 市场类型（可选）
    data_source: DataSource = None   # 数据源（可选）
)
```

##### search_symbols()

搜索品种代码

```python
results = manager.search_symbols(
    keyword: str,                    # 搜索关键词
    market_types: List[MarketType] = None  # 搜索的市场类型
)
```

##### get_data_quality_report()

获取数据质量报告

```python
report = manager.get_data_quality_report(
    symbol: str,                     # 品种代码
    start_date: str,                 # 开始日期
    end_date: str,                   # 结束日期
    interval: str = "1d"             # 时间间隔
)
```

##### export_unified_data()

导出统一格式数据

```python
manager.export_unified_data(
    symbols: List[str],              # 品种代码列表
    start_date: str,                 # 开始日期
    end_date: str,                   # 结束日期
    output_path: str,                # 输出路径
    interval: str = "1d",            # 时间间隔
    format: str = "csv"              # 输出格式 (csv, excel, parquet)
)
```

## 🧪 测试和验证

### 运行完整测试

```bash
python test_multi_market.py
```

### 运行演示

```bash
python demo_multi_market.py
```

### 测试特定功能

```python
from data.multi_market_manager import MultiMarketDataManager

# 测试市场识别
manager = MultiMarketDataManager()
print(manager.auto_detect_market("AAPL"))     # us_stock
print(manager.auto_detect_market("000001.SZ")) # china_stock

# 测试数据获取
df = manager.get_unified_data("AAPL", "2023-01-01", "2023-01-10")
print(df.head())
```

## 📁 项目结构

```
data/
├── multi_market_manager.py     # 统一多市场管理器
├── market_config.py            # 市场配置和枚举
├── base_fetcher.py            # 数据获取器基类
├── data_manager.py            # 原有数据管理器（兼容）
└── fetchers/
    ├── __init__.py
    ├── us_stock_fetcher.py     # 美股数据获取器
    ├── us_futures_fetcher.py   # 美国期货数据获取器
    ├── china_stock_fetcher.py  # 中国A股数据获取器
    ├── china_futures_fetcher.py # 中国期货数据获取器
    └── crypto_fetcher.py       # 加密货币数据获取器
```

## ⚠️ 注意事项

### API限制

- **Yahoo Finance**：相对宽松，但可能有地区限制
- **Alpha Vantage**：免费版每分钟5次请求
- **Tushare**：需要积分，不同接口有不同限制
- **AKShare**：相对宽松，但建议合理使用
- **Binance**：每分钟1200次请求

### 网络环境

- 某些API可能需要稳定的国际网络连接
- 建议配置重试机制和本地缓存
- 中国用户访问海外API可能需要代理

### 数据质量

- 不同数据源的数据质量可能有差异
- 建议使用数据质量报告功能检查
- 重要策略建议使用多个数据源交叉验证

## 🔄 向后兼容

- 原有的`DataManager`类仍然可用
- 现有的回测和实盘交易代码无需修改
- 数据库结构保持兼容
- 可以逐步迁移到新的统一接口

## 🤝 扩展开发

### 添加新的数据源

1. 创建新的获取器类继承`BaseDataFetcher`
2. 实现必要的抽象方法
3. 使用`@register_fetcher`装饰器注册
4. 在`market_config.py`中添加配置

```python
from data.base_fetcher import BaseDataFetcher, register_fetcher
from data.market_config import MarketType, DataSource

@register_fetcher(MarketType.NEW_MARKET, DataSource.NEW_SOURCE)
class NewDataFetcher(BaseDataFetcher):
    def fetch_bars(self, symbol, interval, start_time, end_time, **kwargs):
        # 实现数据获取逻辑
        pass
    
    def fetch_ticker(self, symbol, **kwargs):
        # 实现实时行情获取
        pass
    
    def get_symbols(self, **kwargs):
        # 实现品种列表获取
        pass
```

## 📞 支持和反馈

如果您在使用过程中遇到问题或有改进建议，请：

1. 查看日志文件了解详细错误信息
2. 检查网络连接和API密钥配置
3. 参考测试脚本和演示代码
4. 查看数据质量报告了解数据状态

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

---

🎉 **现在您可以用一套统一的接口处理全球多个市场的数据了！**