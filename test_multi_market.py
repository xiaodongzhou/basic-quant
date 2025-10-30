#!/usr/bin/env python3
"""
多市场数据管理器测试脚本
测试美股、美国期货、中国A股、中国商品期货的数据获取功能
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

def test_market_overview():
    """测试市场概览功能"""
    print("=" * 60)
    print("🌍 测试市场概览功能")
    print("=" * 60)
    
    try:
        # 初始化多市场管理器
        manager = MultiMarketDataManager()
        
        # 获取市场概览
        overview = manager.get_market_overview()
        
        print("📊 支持的市场:")
        for market, info in overview["supported_markets"].items():
            print(f"  • {info['name']} ({market})")
            print(f"    货币: {info['currency']}, 时区: {info['timezone']}")
            print(f"    支持间隔: {', '.join(info['intervals'])}")
            print(f"    数据源: {', '.join(info['sources'])}")
            print()
        
        print("🔌 数据源支持:")
        for source, markets in overview["data_sources"].items():
            print(f"  • {source}: {', '.join(markets)}")
        
        print("💾 缓存数据:")
        for exchange, count in overview["cached_symbols"].items():
            print(f"  • {exchange}: {count} 个品种")
        
        return True
        
    except Exception as e:
        logger.error(f"市场概览测试失败: {e}")
        return False

def test_symbol_detection():
    """测试品种代码自动识别"""
    print("\n" + "=" * 60)
    print("🔍 测试品种代码自动识别")
    print("=" * 60)
    
    try:
        manager = MultiMarketDataManager()
        
        test_symbols = [
            "AAPL",          # 美股
            "TSLA",          # 美股  
            "ES=F",          # 美国期货
            "GC=F",          # 美国期货
            "000001.SZ",     # 中国A股
            "600000.SH",     # 中国A股
            "rb2310",        # 中国期货
            "cu2309",        # 中国期货
            "BTCUSDT",       # 加密货币
        ]
        
        for symbol in test_symbols:
            market_type = manager.auto_detect_market(symbol)
            if market_type:
                print(f"  ✅ {symbol:12} -> {market_type.value}")
            else:
                print(f"  ❌ {symbol:12} -> 未识别")
        
        return True
        
    except Exception as e:
        logger.error(f"品种识别测试失败: {e}")
        return False

def test_us_stock_data():
    """测试美股数据获取"""
    print("\n" + "=" * 60)
    print("🇺🇸 测试美股数据获取")
    print("=" * 60)
    
    try:
        manager = MultiMarketDataManager()
        
        # 测试获取苹果股票数据
        symbol = "AAPL"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        print(f"正在获取 {symbol} 最近30天的数据...")
        
        df = manager.get_unified_data(
            symbol=symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="1d",
            market_type=MarketType.US_STOCK,
            force_update=True
        )
        
        if not df.empty:
            print(f"  ✅ 成功获取 {len(df)} 条数据")
            print(f"  📊 数据范围: {df.index[0]} 到 {df.index[-1]}")
            print(f"  💰 价格范围: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            print(f"  📈 最新收盘价: ${df['close'].iloc[-1]:.2f}")
        else:
            print("  ❌ 未获取到数据")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"美股数据测试失败: {e}")
        return False

def test_crypto_data():
    """测试加密货币数据获取（使用现有的Binance接口）"""
    print("\n" + "=" * 60)
    print("₿ 测试加密货币数据获取")
    print("=" * 60)
    
    try:
        manager = MultiMarketDataManager()
        
        symbol = "BTCUSDT"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"正在获取 {symbol} 最近7天的数据...")
        
        df = manager.get_unified_data(
            symbol=symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="1d",
            market_type=MarketType.CRYPTO,
            force_update=True
        )
        
        if not df.empty:
            print(f"  ✅ 成功获取 {len(df)} 条数据")
            print(f"  📊 数据范围: {df.index[0]} 到 {df.index[-1]}")  
            print(f"  💰 价格范围: ${df['low'].min():,.2f} - ${df['high'].max():,.2f}")
            print(f"  📈 最新收盘价: ${df['close'].iloc[-1]:,.2f}")
        else:
            print("  ❌ 未获取到数据")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"加密货币数据测试失败: {e}")
        return False

def test_data_quality():
    """测试数据质量分析"""
    print("\n" + "=" * 60)
    print("📋 测试数据质量分析")
    print("=" * 60)
    
    try:
        manager = MultiMarketDataManager()
        
        # 使用已有的数据进行质量分析
        symbol = "BTCUSDT"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        print(f"正在分析 {symbol} 数据质量...")
        
        report = manager.get_data_quality_report(
            symbol=symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="1d"
        )
        
        if "error" not in report:
            print(f"  ✅ 数据质量分析完成")
            print(f"  📊 总记录数: {report['total_records']}")
            print(f"  📅 数据范围: {report['data_range']['start']} 到 {report['data_range']['end']}")
            print(f"  💰 价格统计:")
            stats = report['price_statistics']
            print(f"    最低价: ${stats['min_price']:,.2f}")
            print(f"    最高价: ${stats['max_price']:,.2f}")
            print(f"    平均成交量: {stats['avg_volume']:,.0f}")
            
            if report['data_gaps']:
                print(f"  ⚠️  发现 {len(report['data_gaps'])} 个数据缺口")
            else:
                print(f"  ✅ 数据连续性良好")
                
            if report['anomalies']:
                print(f"  ⚠️  发现 {len(report['anomalies'])} 个价格异常")
            else:
                print(f"  ✅ 价格数据正常")
        else:
            print(f"  ❌ 质量分析失败: {report['error']}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"数据质量测试失败: {e}")
        return False

def test_real_time_data():
    """测试实时行情获取"""
    print("\n" + "=" * 60)
    print("⚡ 测试实时行情获取")
    print("=" * 60)
    
    try:
        manager = MultiMarketDataManager()
        
        # 测试多个市场的实时行情
        symbols = ["AAPL", "BTCUSDT"]  # 只测试可用的数据源
        
        print("正在获取实时行情...")
        
        tickers = manager.get_real_time_data(symbols)
        
        for symbol, ticker in tickers.items():
            print(f"  📈 {symbol}:")
            print(f"    价格: {ticker.price:.2f}")
            print(f"    涨跌: {ticker.change:+.2f} ({ticker.change_percent:+.2f}%)")
            print(f"    成交量: {ticker.volume:,.0f}")
            print(f"    时间: {ticker.timestamp}")
        
        if not tickers:
            print("  ❌ 未获取到实时行情")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"实时行情测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始多市场数据管理器集成测试")
    
    # 配置日志
    logger.add("logs/test_multi_market.log", rotation="1 day")
    
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)
    
    tests = [
        ("市场概览", test_market_overview),
        ("品种识别", test_symbol_detection),
        ("美股数据", test_us_stock_data),
        ("加密货币数据", test_crypto_data),
        ("数据质量", test_data_quality),
        ("实时行情", test_real_time_data),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            
        except Exception as e:
            logger.error(f"{test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name:12} {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总计: {passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！多市场数据管理器工作正常。")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")

if __name__ == "__main__":
    main()