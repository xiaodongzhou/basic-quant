#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest System Demo - 回测系统演示

Milestone 2.5: 策略组合回测系统完整演示
- 多策略组合配置
- 历史数据回测执行  
- 性能分析报告
- 结果可视化展示
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.backtest_engine import (
    BacktestEngine, BacktestConfig, run_portfolio_backtest
)
from core.strategy_portfolio_config import (
    PortfolioConfig, StrategyConfig, StrategyAllocation, ConfigManager
)


def create_demo_portfolio_config() -> PortfolioConfig:
    """创建演示用的投资组合配置"""
    
    print("📋 创建多策略投资组合配置...")
    
    # 创建基础投资组合配置
    portfolio_config = PortfolioConfig(
        portfolio_name="demo_multi_strategy_portfolio",
        description="演示用多策略投资组合，包含不同周期的MA策略",
        total_capital=2000000.0,  # 200万初始资金
        allocation_method="weighted"  # 加权分配
    )
    
    # 添加多个MA策略配置
    strategies = [
        StrategyConfig(
            strategy_name="ma_fast_rb",
            strategy_class="MAStrategy",
            strategy_module="strategies.ma_strategy",
            parameters={
                "fast_period": 5,
                "slow_period": 20,
                "symbols": ["rb2405"],
                "description": "螺纹钢快速MA策略"
            },
            tags=["trend", "fast", "rb"]
        ),
        StrategyConfig(
            strategy_name="ma_slow_rb",
            strategy_class="MAStrategy", 
            strategy_module="strategies.ma_strategy",
            parameters={
                "fast_period": 10,
                "slow_period": 50,
                "symbols": ["rb2405"],
                "description": "螺纹钢慢速MA策略"
            },
            tags=["trend", "slow", "rb"]
        ),
        StrategyConfig(
            strategy_name="ma_fast_i",
            strategy_class="MAStrategy",
            strategy_module="strategies.ma_strategy", 
            parameters={
                "fast_period": 8,
                "slow_period": 25,
                "symbols": ["i2405"],
                "description": "铁矿石MA策略"
            },
            tags=["trend", "fast", "iron_ore"]
        ),
        StrategyConfig(
            strategy_name="ma_balanced_j",
            strategy_class="MAStrategy",
            strategy_module="strategies.ma_strategy",
            parameters={
                "fast_period": 12,
                "slow_period": 30,
                "symbols": ["j2405"],
                "description": "焦炭平衡MA策略"
            },
            tags=["trend", "balanced", "coke"]
        )
    ]
    
    portfolio_config.strategies = strategies
    
    # 配置策略资金分配（基于风险和预期收益）
    total_capital = portfolio_config.total_capital
    allocations = [
        StrategyAllocation(
            strategy_name="ma_fast_rb",
            allocation_amount=total_capital * 0.4,  # 40% - 主力品种
            allocation_ratio=0.4,
            max_position_ratio=0.8,
            risk_budget=0.03  # 3%风险预算
        ),
        StrategyAllocation(
            strategy_name="ma_slow_rb", 
            allocation_amount=total_capital * 0.25,  # 25% - 保守策略
            allocation_ratio=0.25,
            max_position_ratio=0.6,
            risk_budget=0.02  # 2%风险预算
        ),
        StrategyAllocation(
            strategy_name="ma_fast_i",
            allocation_amount=total_capital * 0.25,  # 25% - 多元化
            allocation_ratio=0.25, 
            max_position_ratio=0.7,
            risk_budget=0.025  # 2.5%风险预算
        ),
        StrategyAllocation(
            strategy_name="ma_balanced_j",
            allocation_amount=total_capital * 0.1,  # 10% - 小仓位试水
            allocation_ratio=0.1,
            max_position_ratio=0.5,
            risk_budget=0.015  # 1.5%风险预算
        )
    ]
    
    portfolio_config.strategy_allocations = allocations
    
    print(f"✅ 投资组合配置创建完成:")
    print(f"   组合名称: {portfolio_config.portfolio_name}")
    print(f"   总资金: {portfolio_config.total_capital:,.0f}")
    print(f"   策略数量: {len(portfolio_config.strategies)}")
    print(f"   分配方法: {portfolio_config.allocation_method}")
    
    for allocation in allocations:
        print(f"   {allocation.strategy_name}: {allocation.allocation_ratio:.1%} "
              f"({allocation.allocation_amount:,.0f}) 风险预算{allocation.risk_budget:.1%}")
    
    return portfolio_config


def create_demo_backtest_config() -> BacktestConfig:
    """创建演示用的回测配置"""
    
    print("\n⚙️  创建回测配置...")
    
    # 配置回测参数
    config = BacktestConfig(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),    # 半年回测
        initial_capital=2000000.0,
        symbols=['rb2405', 'i2405', 'j2405'],  # 三个主要品种
        data_frequency='1h',                    # 1小时数据
        commission_rate=0.0002,                 # 万2手续费
        slippage_rate=0.0001,                   # 万1滑点
        
        # 风险控制参数
        max_single_position=0.3,               # 单品种最大30%仓位
        max_total_position=0.9,                # 总仓位最大90%
        stop_loss_pct=0.05,                    # 5%止损
        
        # 回测执行参数
        match_mode="next_tick",                 # 下一个tick成交
        price_mode="close"                      # 收盘价成交
    )
    
    print(f"✅ 回测配置创建完成:")
    print(f"   回测周期: {config.start_date.strftime('%Y-%m-%d')} 到 {config.end_date.strftime('%Y-%m-%d')}")
    print(f"   数据频率: {config.data_frequency}")
    print(f"   交易品种: {config.symbols}")
    print(f"   手续费率: {config.commission_rate:.4f}")
    print(f"   滑点率: {config.slippage_rate:.4f}")
    print(f"   风险控制: 单品种≤{config.max_single_position:.0%}, 总仓位≤{config.max_total_position:.0%}")
    
    return config


def run_comprehensive_backtest():
    """运行综合回测演示"""
    
    print("\n🚀 开始运行综合回测演示")
    print("=" * 80)
    
    try:
        # 1. 创建投资组合配置
        portfolio_config = create_demo_portfolio_config()
        
        # 2. 创建回测配置
        backtest_config = create_demo_backtest_config()
        
        print("\n🔄 执行投资组合回测...")
        print("-" * 50)
        
        # 3. 运行回测
        results = run_portfolio_backtest(portfolio_config, backtest_config)
        
        print("✅ 回测执行完成!")
        
        # 4. 分析回测结果
        analyze_backtest_results(results)
        
        # 5. 保存结果
        save_backtest_results(results, portfolio_config, backtest_config)
        
        return results
        
    except Exception as e:
        print(f"❌ 回测执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_backtest_results(results: dict):
    """分析回测结果"""
    
    print("\n📊 回测结果分析")
    print("=" * 80)
    
    # 基础信息
    config = results['config']
    portfolio_values = results['portfolio_values']
    trades = results['trades']
    positions = results['positions']
    metrics = results['performance_metrics']
    
    print(f"\n📋 基础信息:")
    print(f"   回测周期: {config['start_date']} 到 {config['end_date']}")
    print(f"   初始资金: {config['initial_capital']:,.0f}")
    print(f"   交易品种: {', '.join(config['symbols'])}")
    print(f"   数据频率: {config['data_frequency']}")
    
    # 投资组合表现
    if len(portfolio_values) >= 2:
        initial_value = portfolio_values[0]['value']
        final_value = portfolio_values[-1]['value']
        
        print(f"\n💰 投资组合表现:")
        print(f"   初始净值: {initial_value:,.0f}")
        print(f"   最终净值: {final_value:,.0f}")
        print(f"   绝对收益: {final_value - initial_value:,.0f}")
        print(f"   相对收益: {(final_value/initial_value - 1)*100:+.2f}%")
        
        # 净值曲线统计
        values = [pv['value'] for pv in portfolio_values]
        max_value = max(values)
        min_value = min(values)
        
        print(f"   最高净值: {max_value:,.0f}")
        print(f"   最低净值: {min_value:,.0f}")
        print(f"   净值波动: {((max_value/min_value - 1)*100):.2f}%")
    
    # 交易统计
    print(f"\n📈 交易统计:")
    print(f"   总交易次数: {len(trades)}")
    
    closed_trades = [t for t in trades if t.get('close_time') is not None]
    if closed_trades:
        total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
        winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('pnl', 0) <= 0]
        
        print(f"   已平仓交易: {len(closed_trades)}")
        print(f"   盈利交易: {len(winning_trades)}")
        print(f"   亏损交易: {len(losing_trades)}")
        
        if len(closed_trades) > 0:
            win_rate = len(winning_trades) / len(closed_trades)
            print(f"   胜率: {win_rate:.1%}")
            
        if winning_trades and losing_trades:
            avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades)
            avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades)
            profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
            print(f"   盈亏比: {profit_loss_ratio:.2f}")
            print(f"   平均盈利: {avg_win:,.0f}")
            print(f"   平均亏损: {avg_loss:,.0f}")
    
    # 持仓状况
    print(f"\n📊 当前持仓:")
    if positions:
        for pos in positions:
            print(f"   {pos['symbol']}: {pos['direction']} {pos['quantity']} 手, "
                  f"成本 {pos['avg_price']:.1f}, 市值 {pos['market_value']:,.0f}, "
                  f"浮盈 {pos['unrealized_pnl']:+,.0f}")
    else:
        print("   无持仓")
    
    # 性能指标
    if metrics:
        print(f"\n📊 性能指标:")
        print(f"   总收益率: {metrics.get('total_return', 0)*100:+.2f}%")
        print(f"   年化收益率: {metrics.get('annual_return', 0)*100:+.2f}%") 
        print(f"   波动率: {metrics.get('volatility', 0)*100:.2f}%")
        print(f"   夏普比率: {metrics.get('sharpe_ratio', 0):.3f}")
        print(f"   最大回撤: {metrics.get('max_drawdown', 0)*100:.2f}%")
        print(f"   Calmar比率: {metrics.get('calmar_ratio', 0):.3f}")
        
        print(f"\n🎯 风险指标:")
        print(f"   VaR (95%): {metrics.get('var_95', 0)*100:.2f}%")
        print(f"   CVaR (95%): {metrics.get('cvar_95', 0)*100:.2f}%")
        print(f"   最大回撤持续期: {metrics.get('max_drawdown_duration', 0)} 个周期")


def save_backtest_results(results: dict, portfolio_config: PortfolioConfig, 
                         backtest_config: BacktestConfig):
    """保存回测结果"""
    
    print(f"\n💾 保存回测结果...")
    
    try:
        # 创建结果目录
        results_dir = Path("backtest_results")
        results_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        portfolio_name = portfolio_config.portfolio_name
        
        # 保存完整结果
        results_file = results_dir / f"{portfolio_name}_{timestamp}_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ 完整结果已保存: {results_file}")
        
        # 保存投资组合配置
        config_manager = ConfigManager(config_dir=str(results_dir))
        portfolio_config.portfolio_name = f"{portfolio_name}_{timestamp}"
        config_success = config_manager.save_config(portfolio_config)
        
        if config_success:
            config_file = results_dir / f"{portfolio_config.portfolio_name}.yaml"
            print(f"✅ 投资组合配置已保存: {config_file}")
        
        # 生成简化报告
        report_file = results_dir / f"{portfolio_name}_{timestamp}_report.txt"
        generate_text_report(results, portfolio_config, backtest_config, report_file)
        print(f"✅ 文本报告已保存: {report_file}")
        
        print(f"\n📁 所有结果文件已保存到目录: {results_dir.absolute()}")
        
    except Exception as e:
        print(f"❌ 保存结果失败: {e}")


def generate_text_report(results: dict, portfolio_config: PortfolioConfig,
                        backtest_config: BacktestConfig, report_file: Path):
    """生成文本格式的回测报告"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("策略组合回测报告 - Milestone 2.5\n")
        f.write("=" * 80 + "\n\n")
        
        # 基础信息
        f.write("📋 基础配置信息\n")
        f.write("-" * 40 + "\n")
        f.write(f"投资组合名称: {portfolio_config.portfolio_name}\n")
        f.write(f"回测周期: {backtest_config.start_date.strftime('%Y-%m-%d')} 到 {backtest_config.end_date.strftime('%Y-%m-%d')}\n")
        f.write(f"初始资金: {backtest_config.initial_capital:,.0f}\n")
        f.write(f"数据频率: {backtest_config.data_frequency}\n")
        f.write(f"交易品种: {', '.join(backtest_config.symbols)}\n")
        f.write(f"分配方法: {portfolio_config.allocation_method}\n\n")
        
        # 策略配置
        f.write("🎯 策略配置详情\n")
        f.write("-" * 40 + "\n")
        for i, (strategy, allocation) in enumerate(zip(portfolio_config.strategies, portfolio_config.strategy_allocations), 1):
            f.write(f"{i}. {strategy.strategy_name}\n")
            f.write(f"   策略类: {strategy.strategy_class}\n")
            f.write(f"   参数: {strategy.parameters}\n")
            f.write(f"   资金分配: {allocation.allocation_ratio:.1%} ({allocation.allocation_amount:,.0f})\n")
            f.write(f"   风险预算: {allocation.risk_budget:.1%}\n\n")
        
        # 回测结果
        portfolio_values = results['portfolio_values']
        metrics = results['performance_metrics']
        
        if len(portfolio_values) >= 2:
            initial_value = portfolio_values[0]['value']
            final_value = portfolio_values[-1]['value']
            
            f.write("📊 回测结果汇总\n")
            f.write("-" * 40 + "\n")
            f.write(f"初始净值: {initial_value:,.0f}\n")
            f.write(f"最终净值: {final_value:,.0f}\n") 
            f.write(f"绝对收益: {final_value - initial_value:+,.0f}\n")
            f.write(f"相对收益: {(final_value/initial_value - 1)*100:+.2f}%\n\n")
        
        # 性能指标
        if metrics:
            f.write("📈 性能指标\n")
            f.write("-" * 40 + "\n")
            f.write(f"总收益率: {metrics.get('total_return', 0)*100:+.2f}%\n")
            f.write(f"年化收益率: {metrics.get('annual_return', 0)*100:+.2f}%\n")
            f.write(f"波动率: {metrics.get('volatility', 0)*100:.2f}%\n")
            f.write(f"夏普比率: {metrics.get('sharpe_ratio', 0):.3f}\n")
            f.write(f"最大回撤: {metrics.get('max_drawdown', 0)*100:.2f}%\n")
            f.write(f"胜率: {metrics.get('win_rate', 0)*100:.1f}%\n")
            f.write(f"盈亏比: {metrics.get('profit_loss_ratio', 0):.2f}\n")
            f.write(f"总交易次数: {metrics.get('total_trades', 0)}\n\n")
        
        # 交易明细
        trades = results['trades']
        if trades:
            f.write("💼 交易记录 (最近10笔)\n")
            f.write("-" * 40 + "\n")
            recent_trades = trades[-10:]  # 最近10笔交易
            
            for trade in recent_trades:
                f.write(f"交易ID: {trade['trade_id']}\n")
                f.write(f"策略: {trade['strategy_name']}\n")
                f.write(f"标的: {trade['symbol']} {trade['direction']}\n")
                f.write(f"开仓: {trade['open_time']} @ {trade['open_price']}\n")
                if trade.get('close_time'):
                    f.write(f"平仓: {trade['close_time']} @ {trade.get('close_price', 'N/A')}\n")
                    f.write(f"盈亏: {trade.get('pnl', 0):+,.0f}\n")
                f.write("-" * 20 + "\n")
        
        f.write(f"\n报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def main():
    """主演示函数"""
    
    print("🎯 Milestone 2.5: 策略组合回测系统演示")
    print("🔬 基于VNPY框架的期货量化交易回测平台")
    print("=" * 80)
    
    # 运行综合回测
    results = run_comprehensive_backtest()
    
    if results:
        print(f"\n🎉 演示完成! 回测系统验证成功!")
        print(f"📊 回测状态: {results['state']}")
        print(f"📁 结果文件已保存到 backtest_results/ 目录")
        
        # 显示关键指标摘要
        metrics = results.get('performance_metrics', {})
        portfolio_values = results.get('portfolio_values', [])
        
        if metrics and len(portfolio_values) >= 2:
            initial = portfolio_values[0]['value']
            final = portfolio_values[-1]['value']
            
            print(f"\n🏆 关键指标摘要:")
            print(f"   总收益率: {metrics.get('total_return', 0)*100:+.2f}%")
            print(f"   夏普比率: {metrics.get('sharpe_ratio', 0):.3f}")
            print(f"   最大回撤: {metrics.get('max_drawdown', 0)*100:.2f}%")
            print(f"   总交易次数: {metrics.get('total_trades', 0)}")
            print(f"   胜率: {metrics.get('win_rate', 0)*100:.1f}%")
        
        print(f"\n✅ Milestone 2.5 回测系统开发成功完成!")
        return True
    else:
        print(f"\n❌ 演示失败!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)