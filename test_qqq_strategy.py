"""
QQQ数据策略测试脚本
测试改进版EMA趋势策略在QQQ数据上的表现
包含equity curve、return curve和K线图标注
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import yfinance as yf
from typing import List, Tuple, Dict, Any
import warnings
warnings.filterwarnings('ignore')

# 导入策略相关模块
from strategies.ema_trend_strategy import AdvancedEMATrendStrategy
from strategies.three_principle_strategy import TrendDirection, SignalType, Position
from strategies.indicators import calculate_ema, calculate_atr, calculate_adx

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class QQQStrategyTester:
    """QQQ策略测试器"""
    
    def __init__(self, start_date: str = '2021-01-01', end_date: str = '2025-08-01'):
        self.start_date = start_date
        self.end_date = end_date
        self.data = None
        self.strategy = None
        self.backtest_results = None
        
    def download_data(self) -> pd.DataFrame:
        """下载QQQ历史数据"""
        print(f"正在下载QQQ数据: {self.start_date} 到 {self.end_date}")
        
        try:
            ticker = yf.Ticker("QQQ")
            data = ticker.history(start=self.start_date, end=self.end_date, interval='1d')
            
            if data.empty:
                raise ValueError("未能获取到数据")
            
            # 处理列名 - 检查实际返回的列
            print(f"原始数据列: {list(data.columns)}")
            
            # 重命名列以匹配策略期望的格式
            expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if len(data.columns) >= 5 and all(col in data.columns for col in expected_columns):
                # 如果包含期望的列，直接使用
                data = data[expected_columns].copy()
                data.columns = ['open', 'high', 'low', 'close', 'volume']
            else:
                # 如果列结构不同，尝试从现有列中提取
                available_cols = list(data.columns)
                data = data[available_cols[:5]].copy()  # 取前5列
                data.columns = ['open', 'high', 'low', 'close', 'volume']
            
            # 确保数据类型正确
            for col in ['open', 'high', 'low', 'close', 'volume']:
                data[col] = pd.to_numeric(data[col], errors='coerce')
            
            # 删除空值
            data = data.dropna()
            
            print(f"成功下载数据: {len(data)} 条记录")
            print(f"数据时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
            
            self.data = data
            return data
            
        except Exception as e:
            print(f"下载数据失败: {e}")
            raise
    
    def initialize_strategy(self, parameters: Dict[str, Any] = None) -> AdvancedEMATrendStrategy:
        """初始化策略"""
        default_params = {
            'ema_short': 20,
            'ema_long': 60,
            'adx_period': 14,
            'adx_threshold': 25.0,
            'lookback_candles': 4,
            'pullback_threshold': 0.5,
            'risk_reward_ratio': 2.0,
            'position_size': 0.02,
            'max_risk_per_trade': 0.01,
            'min_confidence': 0.7,
            'body_threshold': 1.5,
        }
        
        if parameters:
            default_params.update(parameters)
        
        self.strategy = AdvancedEMATrendStrategy(
            name="QQQ EMA趋势策略",
            symbol="QQQ",
            parameters=default_params
        )
        
        print("策略初始化完成")
        return self.strategy
    
    def run_backtest(self, initial_capital: float = 100000) -> Dict[str, Any]:
        """运行回测"""
        if self.data is None:
            raise ValueError("请先下载数据")
        
        if self.strategy is None:
            self.initialize_strategy()
        
        print("开始运行回测...")
        
        # 准备回测数据
        df = self.data.copy()
        
        # 计算技术指标
        df['ema20'] = calculate_ema(df['close'], 20)
        df['ema60'] = calculate_ema(df['close'], 60)
        df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)
        adx, plus_di, minus_di = calculate_adx(df['high'], df['low'], df['close'], 14)
        df['adx'] = adx
        df['plus_di'] = plus_di  
        df['minus_di'] = minus_di
        
        # 初始化回测变量
        capital = initial_capital
        # 创建一个简单的持仓对象来跟踪状态
        class SimplePosition:
            def __init__(self):
                self.size = 0
                self.entry_price = 0.0
                self.entry_time = None  
                self.stop_loss = 0.0
                self.direction = "NONE"
        
        position = SimplePosition()
        trades = []
        equity_curve = []
        signals = []
        
        # 遍历数据进行回测
        for i in range(max(60, len(df)//10), len(df)):  # 从第60根K线开始，确保指标计算完整
            current_data = df.iloc[:i+1].copy()
            current_price = current_data['close'].iloc[-1]
            current_date = current_data.index[-1]
            
            # 分析当前状态
            try:
                # 分析趋势方向
                direction = self.strategy.direction_analyzer.analyze_direction(current_data)
                
                # 生成交易信号
                signal = self.strategy.signal_generator.generate_signal(
                    current_data, direction, position
                )
                
                # 管理仓位
                if signal != SignalType.NO_SIGNAL and signal != SignalType.HOLD:
                    position_action = self.strategy.position_manager.manage_position(
                        current_data, signal, position
                    )
                    
                    # 执行交易
                    if position_action:
                        if signal in [SignalType.ENTRY_LONG, SignalType.ENTRY_SHORT]:
                            # 开仓
                            if position.size == 0:  # 确保没有持仓才开新仓
                                # 计算仓位大小
                                risk_amount = capital * self.strategy.parameters.get('max_risk_per_trade', 0.01)
                                atr_value = current_data['atr'].iloc[-1]
                                stop_distance = 2 * atr_value  # 2倍ATR作为止损距离
                                
                                if stop_distance > 0:
                                    position_size = risk_amount / stop_distance
                                    shares = int(position_size / current_price)
                                    
                                    if shares > 0:
                                        position.size = shares if signal == SignalType.ENTRY_LONG else -shares
                                        position.entry_price = current_price
                                        position.entry_time = current_date
                                        position.stop_loss = (current_price - stop_distance if signal == SignalType.ENTRY_LONG 
                                                            else current_price + stop_distance)
                                        
                                        signals.append({
                                            'date': current_date,
                                            'price': current_price,
                                            'signal': 'BUY' if signal == SignalType.ENTRY_LONG else 'SELL',
                                            'type': 'ENTRY'
                                        })
                                        
                                        print(f"{current_date.strftime('%Y-%m-%d')}: {'做多' if signal == SignalType.ENTRY_LONG else '做空'} "
                                              f"价格: {current_price:.2f}, 股数: {abs(shares)}")
                        
                        elif signal in [SignalType.EXIT_LONG, SignalType.EXIT_SHORT]:
                            # 平仓
                            if position.size != 0:
                                pnl = (current_price - position.entry_price) * position.size
                                capital += pnl
                                
                                trades.append({
                                    'entry_date': position.entry_time,
                                    'exit_date': current_date,
                                    'entry_price': position.entry_price,
                                    'exit_price': current_price,
                                    'size': position.size,
                                    'pnl': pnl,
                                    'return': pnl / (abs(position.size) * position.entry_price)
                                })
                                
                                signals.append({
                                    'date': current_date,
                                    'price': current_price,
                                    'signal': 'SELL' if position.size > 0 else 'BUY',
                                    'type': 'EXIT'
                                })
                                
                                print(f"{current_date.strftime('%Y-%m-%d')}: {'平多' if position.size > 0 else '平空'} "
                                      f"价格: {current_price:.2f}, 盈亏: {pnl:.2f}")
                                
                                # 重置持仓
                                position = SimplePosition()
                
                # 检查止损
                if position.size != 0:
                    if ((position.size > 0 and current_price <= position.stop_loss) or 
                        (position.size < 0 and current_price >= position.stop_loss)):
                        
                        # 执行止损
                        pnl = (current_price - position.entry_price) * position.size
                        capital += pnl
                        
                        trades.append({
                            'entry_date': position.entry_time,
                            'exit_date': current_date,
                            'entry_price': position.entry_price,
                            'exit_price': current_price,
                            'size': position.size,
                            'pnl': pnl,
                            'return': pnl / (abs(position.size) * position.entry_price),
                            'exit_reason': 'STOP_LOSS'
                        })
                        
                        signals.append({
                            'date': current_date,
                            'price': current_price,
                            'signal': 'SELL' if position.size > 0 else 'BUY',
                            'type': 'STOP_LOSS'
                        })
                        
                        print(f"{current_date.strftime('%Y-%m-%d')}: 止损 "
                              f"价格: {current_price:.2f}, 盈亏: {pnl:.2f}")
                        
                        # 重置持仓
                        position = SimplePosition()
                
                # 记录权益曲线
                market_value = 0
                if position.size != 0:
                    market_value = (current_price - position.entry_price) * position.size
                
                total_equity = capital + market_value
                equity_curve.append({
                    'date': current_date,
                    'equity': total_equity,
                    'capital': capital,
                    'unrealized_pnl': market_value
                })
                
            except Exception as e:
                # 如果某个时点出错，记录但继续
                print(f"回测第{i}根K线时出错: {e}")
                continue
        
        # 整理回测结果
        results = {
            'trades': trades,
            'equity_curve': equity_curve,
            'signals': signals,
            'initial_capital': initial_capital,
            'final_capital': capital,
            'data': df
        }
        
        self.backtest_results = results
        print(f"回测完成! 交易次数: {len(trades)}, 信号数量: {len(signals)}")
        return results
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """计算策略绩效指标"""
        if not self.backtest_results:
            raise ValueError("请先运行回测")
        
        trades = self.backtest_results['trades']
        equity_curve = pd.DataFrame(self.backtest_results['equity_curve'])
        
        if len(trades) == 0:
            return {'total_trades': 0, 'total_return': 0.0}
        
        # 基础指标
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        losing_trades = len([t for t in trades if t['pnl'] < 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in trades)
        total_return = total_pnl / self.backtest_results['initial_capital']
        
        # 计算最大回撤
        equity_curve['peak'] = equity_curve['equity'].cummax()
        equity_curve['drawdown'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak']
        max_drawdown = equity_curve['drawdown'].min()
        
        # 计算年化收益率
        start_date = equity_curve['date'].iloc[0]
        end_date = equity_curve['date'].iloc[-1]
        days = (end_date - start_date).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # 计算夏普比率
        if len(equity_curve) > 1:
            daily_returns = equity_curve['equity'].pct_change().dropna()
            sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        metrics = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_pnl': total_pnl,
            'avg_trade_pnl': total_pnl / total_trades if total_trades > 0 else 0,
        }
        
        return metrics
    
    def plot_results(self, figsize: Tuple[int, int] = (15, 12)):
        """绘制回测结果图表"""
        if not self.backtest_results:
            raise ValueError("请先运行回测")
        
        fig, axes = plt.subplots(3, 1, figsize=figsize)
        
        df = self.backtest_results['data']
        equity_curve = pd.DataFrame(self.backtest_results['equity_curve'])
        signals_df = pd.DataFrame(self.backtest_results['signals'])
        
        # 1. K线图和交易信号
        ax1 = axes[0]
        
        # 绘制价格线
        ax1.plot(df.index, df['close'], label='QQQ Close', color='black', linewidth=1)
        ax1.plot(df.index, df['ema20'], label='EMA20', color='blue', alpha=0.7)
        ax1.plot(df.index, df['ema60'], label='EMA60', color='red', alpha=0.7)
        
        # 标注买卖点
        if not signals_df.empty:
            buy_signals = signals_df[signals_df['signal'] == 'BUY']
            sell_signals = signals_df[signals_df['signal'] == 'SELL']
            
            if not buy_signals.empty:
                ax1.scatter(buy_signals['date'], buy_signals['price'], 
                           marker='^', color='green', s=100, label='买入信号', zorder=5)
            
            if not sell_signals.empty:
                ax1.scatter(sell_signals['date'], sell_signals['price'], 
                           marker='v', color='red', s=100, label='卖出信号', zorder=5)
        
        ax1.set_title('QQQ K线图 - EMA趋势策略交易信号', fontsize=14, fontweight='bold')
        ax1.set_ylabel('价格 ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 权益曲线
        ax2 = axes[1]
        if not equity_curve.empty:
            ax2.plot(equity_curve['date'], equity_curve['equity'], 
                     label='总权益', color='blue', linewidth=2)
            ax2.axhline(y=self.backtest_results['initial_capital'], 
                       color='gray', linestyle='--', alpha=0.7, label='初始资金')
        
        ax2.set_title('权益曲线', fontsize=14, fontweight='bold')
        ax2.set_ylabel('权益 ($)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 收益率曲线和回撤
        ax3 = axes[2]
        if not equity_curve.empty:
            returns = (equity_curve['equity'] / self.backtest_results['initial_capital'] - 1) * 100
            ax3.plot(equity_curve['date'], returns, 
                     label='累计收益率', color='green', linewidth=2)
            
            # 计算回撤
            peak = equity_curve['equity'].cummax()
            drawdown = (equity_curve['equity'] - peak) / peak * 100
            ax3.fill_between(equity_curve['date'], drawdown, 0, 
                           color='red', alpha=0.3, label='回撤')
        
        ax3.set_title('收益率与回撤', fontsize=14, fontweight='bold')
        ax3.set_ylabel('收益率 (%)')
        ax3.set_xlabel('日期')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 设置日期格式
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        return fig
    
    def print_performance_summary(self):
        """打印策略绩效总结"""
        if not self.backtest_results:
            print("请先运行回测")
            return
        
        metrics = self.calculate_performance_metrics()
        
        print("\n" + "="*60)
        print("QQQ EMA趋势策略 - 回测结果总结")
        print("="*60)
        print(f"测试周期: {self.start_date} 至 {self.end_date}")
        print(f"初始资金: ${self.backtest_results['initial_capital']:,.2f}")
        print(f"最终资金: ${self.backtest_results['final_capital']:,.2f}")
        print(f"总盈亏: ${metrics['total_pnl']:,.2f}")
        print()
        print("交易统计:")
        print(f"  总交易次数: {metrics['total_trades']}")
        print(f"  盈利交易: {metrics['winning_trades']}")
        print(f"  亏损交易: {metrics['losing_trades']}")
        print(f"  胜率: {metrics['win_rate']:.2%}")
        print(f"  平均每笔盈亏: ${metrics['avg_trade_pnl']:,.2f}")
        print()
        print("收益指标:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  年化收益率: {metrics['annual_return']:.2%}")
        print(f"  最大回撤: {metrics['max_drawdown']:.2%}")
        print(f"  夏普比率: {metrics['sharpe_ratio']:.3f}")
        print("="*60)


def main():
    """主函数 - 运行完整的QQQ策略测试"""
    # 创建测试器
    tester = QQQStrategyTester(start_date='2021-01-01', end_date='2025-08-01')
    
    try:
        # 1. 下载数据
        print("步骤1: 下载QQQ历史数据")
        tester.download_data()
        
        # 2. 初始化策略
        print("\n步骤2: 初始化EMA趋势策略")
        tester.initialize_strategy()
        
        # 3. 运行回测
        print("\n步骤3: 运行策略回测")
        results = tester.run_backtest(initial_capital=100000)
        
        # 4. 计算绩效指标
        print("\n步骤4: 计算绩效指标")
        metrics = tester.calculate_performance_metrics()
        
        # 5. 打印结果总结
        print("\n步骤5: 绩效总结")
        tester.print_performance_summary()
        
        # 6. 绘制图表
        print("\n步骤6: 生成可视化图表")
        fig = tester.plot_results()
        
        # 保存图表
        plt.savefig('/home/user/webapp/qqq_strategy_results.png', dpi=300, bbox_inches='tight')
        print("图表已保存至: qqq_strategy_results.png")
        
        plt.show()
        
        return tester, results, metrics
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


if __name__ == "__main__":
    # 运行完整测试
    tester, results, metrics = main()