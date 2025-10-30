#!/usr/bin/env python3
"""
多市场数据管理器使用演示
展示如何使用统一接口处理美股、期货、A股、商品期货的数据
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from data.multi_market_manager import MultiMarketDataManager
from data.market_config import MarketType, DataSource

def demo_unified_data_access():
    """演示统一数据访问"""
    print("=" * 80)
    print("🚀 多市场数据管理器演示")
    print("=" * 80)
    
    # 初始化多市场数据管理器
    manager = MultiMarketDataManager()
    
    print("📊 1. 市场概览")
    print("-" * 40)
    overview = manager.get_market_overview()
    
    print("支持的市场:")
    for market, info in overview["supported_markets"].items():
        print(f"  • {info['name']} ({market}) - {info['currency']}")
    
    print(f"\n支持的数据源: {', '.join(overview['data_sources'].keys())}")
    
    print("\n🔍 2. 品种代码自动识别")
    print("-" * 40)
    
    # 演示不同市场的品种识别
    test_symbols = {
        "AAPL": "苹果公司股票", 
        "TSLA": "特斯拉股票",
        "ES=F": "标普500期货",
        "GC=F": "黄金期货", 
        "000001.SZ": "平安银行",
        "600000.SH": "浦银行",
        "rb2310": "螺纹钢期货",
        "cu2309": "铜期货",
        "BTCUSDT": "比特币/USDT"
    }
    
    for symbol, description in test_symbols.items():
        market_type = manager.auto_detect_market(symbol)
        if market_type:
            print(f"  {symbol:12} ({description:12}) -> {market_type.value}")
    
    print("\n📈 3. 统一数据获取示例")
    print("-" * 40)
    
    # 演示获取美股数据（Yahoo Finance通常比较稳定）
    try:
        print("获取美股数据示例:")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        df = manager.get_unified_data(
            symbol="AAPL",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="1d",
            market_type=MarketType.US_STOCK
        )
        
        if not df.empty:
            print(f"  ✅ 获取AAPL数据成功: {len(df)}条记录")
            print(f"     时间范围: {df.index[0]} 到 {df.index[-1]}")
            print(f"     价格范围: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            print(f"     最新价格: ${df['close'].iloc[-1]:.2f}")
            
            # 显示数据格式
            print(f"     数据列: {list(df.columns)}")
            
    except Exception as e:
        print(f"  ❌ 美股数据获取失败: {e}")
        
    print("\n📋 4. 数据格式统一性")
    print("-" * 40)
    print("所有市场的数据都使用统一的格式:")
    print("  • datetime: 时间索引")
    print("  • open, high, low, close: OHLC价格数据")
    print("  • volume: 成交量")
    print("  • turnover: 成交额")
    print("  • open_interest: 持仓量（期货）")
    print("  • symbol, exchange, interval: 元数据")
    
    print("\n💡 5. 使用建议")
    print("-" * 40)
    print("✅ 推荐用法:")
    print("  • 让系统自动检测市场类型（大部分情况）")
    print("  • 使用默认数据源（已优化选择）")
    print("  • 批量处理多个品种时按市场分组")
    print("  • 使用数据质量报告检查数据完整性")
    
    print("\n⚠️  注意事项:")
    print("  • 某些数据源需要API密钥（如Alpha Vantage、Tushare）")
    print("  • 网络限制可能影响数据获取")
    print("  • 不同市场有不同的交易时间")
    print("  • 建议本地缓存常用数据")

def demo_code_examples():
    """演示代码使用例子"""
    print("\n" + "=" * 80)
    print("💻 代码使用示例")
    print("=" * 80)
    
    code_examples = [
        ("初始化管理器", """
from data.multi_market_manager import MultiMarketDataManager

# 基础初始化
manager = MultiMarketDataManager()

# 带API密钥的初始化
manager = MultiMarketDataManager(
    alphavantage_api_key="YOUR_API_KEY",
    tushare_token="YOUR_TOKEN"
)"""),
        
        ("获取历史数据", """
# 自动检测市场类型
df = manager.get_unified_data(
    symbol="AAPL",
    start_date="2023-01-01", 
    end_date="2023-12-31",
    interval="1d"
)

# 指定市场类型和数据源
df = manager.get_unified_data(
    symbol="000001.SZ",
    start_date="2023-01-01",
    end_date="2023-12-31", 
    interval="1d",
    market_type=MarketType.CHINA_STOCK,
    data_source=DataSource.AKSHARE
)"""),
        
        ("获取实时行情", """
# 单个品种
tickers = manager.get_real_time_data("AAPL")

# 多个品种（自动按市场分组）
symbols = ["AAPL", "TSLA", "BTCUSDT", "000001.SZ"]
tickers = manager.get_real_time_data(symbols)

for symbol, ticker in tickers.items():
    print(f"{symbol}: {ticker.price} ({ticker.change_percent:+.2f}%)")"""),
        
        ("搜索品种", """
# 搜索包含关键词的品种
results = manager.search_symbols("BTC")

# 指定市场搜索
results = manager.search_symbols(
    "000", 
    market_types=[MarketType.CHINA_STOCK]
)"""),
        
        ("数据质量检查", """
# 生成数据质量报告
report = manager.get_data_quality_report(
    symbol="AAPL",
    start_date="2023-01-01",
    end_date="2023-12-31"
)

print(f"总记录数: {report['total_records']}")
print(f"数据缺口: {len(report['data_gaps'])}")
print(f"价格异常: {len(report['anomalies'])}")"""),
        
        ("批量导出数据", """
# 导出多市场数据到文件
symbols = ["AAPL", "TSLA", "BTCUSDT", "000001.SZ"]

manager.export_unified_data(
    symbols=symbols,
    start_date="2023-01-01", 
    end_date="2023-12-31",
    output_path="multi_market_data.csv",
    format="csv"
)""")
    ]
    
    for title, code in code_examples:
        print(f"\n📝 {title}")
        print("-" * 40)
        print(code)

def demo_strategy_integration():
    """演示策略集成"""
    print("\n" + "=" * 80)
    print("🎯 与量化策略的集成")
    print("=" * 80)
    
    integration_example = """
# 在现有的量化系统中使用多市场数据管理器

# 1. 替换原有的数据管理器
from data.multi_market_manager import MultiMarketDataManager

class UnifiedQuantStrategy:
    def __init__(self):
        # 使用新的多市场数据管理器
        self.data_manager = MultiMarketDataManager()
    
    def get_data_for_backtest(self, symbol, start_date, end_date):
        # 自动处理不同市场的数据
        return self.data_manager.get_unified_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )
    
    def run_cross_market_strategy(self):
        # 跨市场策略示例
        symbols = [
            "AAPL",      # 美股
            "ES=F",      # 美国期货  
            "000001.SZ", # A股
            "rb2310",    # 中国期货
            "BTCUSDT"    # 加密货币
        ]
        
        all_data = {}
        for symbol in symbols:
            df = self.data_manager.get_unified_data(
                symbol=symbol,
                start_date="2023-01-01",
                end_date="2023-12-31"
            )
            
            if not df.empty:
                all_data[symbol] = df
        
        # 现在可以用统一格式处理所有市场的数据
        # 计算相关性、配对交易、跨市场套利等
        
        return all_data
"""
    
    print("集成示例:")
    print(integration_example)
    
    print("\n🔄 向后兼容")
    print("-" * 40)
    print("• 原有的DataManager仍然可用（加密货币数据）")
    print("• 策略代码可以逐步迁移到新的统一接口")
    print("• 数据库结构保持兼容")
    print("• 现有的回测和实盘交易框架无需修改")

def main():
    """主演示函数"""
    logger.add("logs/demo_multi_market.log", rotation="1 day")
    Path("logs").mkdir(exist_ok=True)
    
    try:
        demo_unified_data_access()
        demo_code_examples()
        demo_strategy_integration()
        
        print("\n" + "=" * 80)
        print("🎉 演示完成！")
        print("=" * 80)
        print("您现在已经了解了如何使用统一的多市场数据管理器。")
        print("这个系统可以让您的量化策略轻松处理全球多个市场的数据，")
        print("而无需为每个市场编写不同的数据处理代码。")
        print("\n下一步：")
        print("• 配置需要的API密钥")
        print("• 在您的策略中集成MultiMarketDataManager")
        print("• 测试跨市场的量化策略")
        
    except Exception as e:
        logger.error(f"演示过程中出错: {e}")
        print(f"❌ 演示失败: {e}")

if __name__ == "__main__":
    main()