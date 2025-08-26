"""
最终QQQ EMA策略完整回测分析
包含详细性能指标、可视化图表和交易分析
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

from strategies.indicators import calculate_ema, calculate_atr, calculate_adx

# 设置中文字体和图表样式
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('default')

class ComprehensiveQQQAnalysis:
    """QQQ策略综合分析类"""
    
    def __init__(self, start_date='2021-01-01', end_date='2025-08-01'):
        self.start_date = start_date
        self.end_date = end_date
        self.data = None
        self.trades = []
        self.signals = []
        self.equity_curve = []
        self.initial_capital = 100000
        
    def download_and_prepare_data(self):
        """下载并准备数据"""
        print(f"正在下载QQQ数据: {self.start_date} 至 {self.end_date}")
        
        ticker = yf.Ticker("QQQ")
        data = ticker.history(start=self.start_date, end=self.end_date, interval='1d')
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        data.columns = ['open', 'high', 'low', 'close', 'volume']
        
        print(f"成功下载 {len(data)} 条数据记录")
        print(f"数据时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
        
        # 计算技术指标
        print("正在计算技术指标...")
        data['ema20'] = calculate_ema(data['close'], 20)
        data['ema60'] = calculate_ema(data['close'], 60)
        data['atr'] = calculate_atr(data['high'], data['low'], data['close'], 14)
        
        adx, plus_di, minus_di = calculate_adx(data['high'], data['low'], data['close'], 14)
        data['adx'] = adx
        data['plus_di'] = plus_di
        data['minus_di'] = minus_di
        
        self.data = data
        return data
    
    def run_enhanced_backtest(self):
        """运行增强版回测"""
        print("开始运行增强版策略回测...")
        
        data = self.data
        capital = self.initial_capital
        position = 0  # 0=空仓, >0=持股数
        entry_price = 0
        entry_date = None
        
        for i in range(70, len(data)):  # 从第70天开始
            current_price = data['close'].iloc[i]
            current_date = data.index[i]
            ema20 = data['ema20'].iloc[i]
            ema60 = data['ema60'].iloc[i]
            adx_val = data['adx'].iloc[i]
            
            # 增强的趋势判断
            is_uptrend = (ema20 > ema60) and (adx_val > 20)
            ema20_rising = ema20 > data['ema20'].iloc[i-1]
            price_momentum = current_price > data['close'].iloc[i-1]
            
            # 买入条件：无持仓 + 强势上升趋势
            if (position == 0 and is_uptrend and ema20_rising and price_momentum and
                current_price > ema20):  # 价格在EMA20之上
                
                shares = int(capital * 0.95 / current_price)  # 使用95%资金
                if shares > 0:
                    position = shares
                    entry_price = current_price
                    entry_date = current_date
                    capital -= shares * current_price
                    
                    self.trades.append({
                        'type': 'BUY',
                        'date': current_date,
                        'price': current_price,
                        'shares': shares,
                        'capital_used': shares * current_price
                    })
                    
                    self.signals.append({
                        'date': current_date,
                        'price': current_price,
                        'signal': 'BUY'
                    })
            
            # 卖出条件：有持仓 + (趋势转弱 或 技术止损)
            elif position > 0:
                # 止损条件
                stop_loss_triggered = current_price < entry_price * 0.95  # 5%止损
                
                # 趋势转弱条件
                trend_weakening = (not is_uptrend or 
                                 current_price < ema20 * 0.98 or
                                 adx_val < 15)
                
                if stop_loss_triggered or trend_weakening:
                    sell_amount = position * current_price
                    capital += sell_amount
                    profit = sell_amount - position * entry_price
                    profit_pct = profit / (position * entry_price)
                    holding_days = (current_date - entry_date).days
                    
                    self.trades.append({
                        'type': 'SELL',
                        'date': current_date,
                        'price': current_price,
                        'shares': position,
                        'profit': profit,
                        'profit_pct': profit_pct,
                        'holding_days': holding_days,
                        'exit_reason': 'STOP_LOSS' if stop_loss_triggered else 'TREND_WEAK'
                    })
                    
                    self.signals.append({
                        'date': current_date,
                        'price': current_price,
                        'signal': 'SELL'
                    })
                    
                    position = 0
                    entry_price = 0
                    entry_date = None
            
            # 计算当前权益
            current_equity = capital
            if position > 0:
                current_equity += position * current_price
                
            self.equity_curve.append({
                'date': current_date,
                'equity': current_equity,
                'capital': capital,
                'position_value': position * current_price if position > 0 else 0
            })
        
        # 最终平仓
        if position > 0:
            final_price = data['close'].iloc[-1]
            final_amount = position * final_price
            capital += final_amount
            profit = final_amount - position * entry_price
            
            self.trades.append({
                'type': 'SELL',
                'date': data.index[-1],
                'price': final_price,
                'shares': position,
                'profit': profit,
                'profit_pct': profit / (position * entry_price),
                'holding_days': (data.index[-1] - entry_date).days,
                'exit_reason': 'FINAL_EXIT'
            })
        
        print(f"回测完成! 总交易次数: {len([t for t in self.trades if t['type'] == 'BUY'])}")
        return capital
    
    def calculate_performance_metrics(self):
        """计算详细性能指标"""
        equity_df = pd.DataFrame(self.equity_curve)
        buy_trades = [t for t in self.trades if t['type'] == 'BUY']
        sell_trades = [t for t in self.trades if t['type'] == 'SELL']
        
        # 基础指标
        total_trades = len(buy_trades)
        if total_trades == 0:
            return {}
        
        final_capital = equity_df['equity'].iloc[-1]
        total_return = (final_capital - self.initial_capital) / self.initial_capital
        
        # 交易分析
        profitable_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        losing_trades = [t for t in sell_trades if t.get('profit', 0) <= 0]
        
        win_rate = len(profitable_trades) / len(sell_trades) if sell_trades else 0
        
        avg_profit = np.mean([t['profit'] for t in profitable_trades]) if profitable_trades else 0
        avg_loss = np.mean([t['profit'] for t in losing_trades]) if losing_trades else 0
        
        profit_factor = abs(avg_profit / avg_loss) if avg_loss < 0 else float('inf')
        
        # 时间分析
        start_date = equity_df['date'].iloc[0]
        end_date = equity_df['date'].iloc[-1]
        total_days = (end_date - start_date).days
        years = total_days / 365.25
        
        annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # 风险指标
        daily_returns = equity_df['equity'].pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252)  # 年化波动率
        sharpe_ratio = (annual_return - 0.02) / volatility if volatility > 0 else 0  # 假设无风险利率2%
        
        # 最大回撤
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak']
        max_drawdown = equity_df['drawdown'].min()
        
        # 平均持仓时间
        avg_holding_days = np.mean([t.get('holding_days', 0) for t in sell_trades]) if sell_trades else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'volatility': volatility,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'avg_holding_days': avg_holding_days,
            'total_profit': sum([t.get('profit', 0) for t in sell_trades]),
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
        }
    
    def create_comprehensive_charts(self):
        """创建综合图表"""
        fig = plt.figure(figsize=(20, 16))
        
        # 创建网格布局
        gs = fig.add_gridspec(4, 2, height_ratios=[2, 1, 1, 1], hspace=0.3, wspace=0.3)
        
        data = self.data
        equity_df = pd.DataFrame(self.equity_curve)
        signals_df = pd.DataFrame(self.signals) if self.signals else pd.DataFrame()
        
        # 1. 主图：价格走势和交易信号
        ax1 = fig.add_subplot(gs[0, :])
        
        ax1.plot(data.index, data['close'], label='QQQ 收盘价', color='black', linewidth=1.5)
        ax1.plot(data.index, data['ema20'], label='EMA20', color='blue', alpha=0.8, linewidth=1.5)
        ax1.plot(data.index, data['ema60'], label='EMA60', color='red', alpha=0.8, linewidth=1.5)
        
        if not signals_df.empty:
            buy_signals = signals_df[signals_df['signal'] == 'BUY']
            sell_signals = signals_df[signals_df['signal'] == 'SELL']
            
            if not buy_signals.empty:
                ax1.scatter(buy_signals['date'], buy_signals['price'],
                           marker='^', color='green', s=100, label='买入信号', zorder=5)
            if not sell_signals.empty:
                ax1.scatter(sell_signals['date'], sell_signals['price'],
                           marker='v', color='red', s=100, label='卖出信号', zorder=5)
        
        ax1.set_title('QQQ价格走势与EMA趋势策略交易信号', fontsize=16, fontweight='bold', pad=20)
        ax1.set_ylabel('价格 ($)', fontsize=12)
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 2. 权益曲线
        ax2 = fig.add_subplot(gs[1, :])
        if not equity_df.empty:
            ax2.plot(equity_df['date'], equity_df['equity'], color='blue', linewidth=2, label='策略权益')
            ax2.axhline(y=self.initial_capital, color='gray', linestyle='--', alpha=0.7, label='初始资金')
            
            # 买入持有基准
            buy_hold_return = (data['close'] / data['close'].iloc[70]) * self.initial_capital
            ax2.plot(data.index[70:], buy_hold_return.iloc[70:], 
                    color='orange', linewidth=2, alpha=0.8, label='买入持有基准')
        
        ax2.set_title('权益曲线对比', fontsize=14, fontweight='bold')
        ax2.set_ylabel('权益 ($)', fontsize=12)
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 3. 回撤图
        ax3 = fig.add_subplot(gs[2, 0])
        if not equity_df.empty:
            equity_df_copy = equity_df.copy()
            equity_df_copy['peak'] = equity_df_copy['equity'].cummax()
            equity_df_copy['drawdown'] = (equity_df_copy['equity'] - equity_df_copy['peak']) / equity_df_copy['peak'] * 100
            
            ax3.fill_between(equity_df_copy['date'], equity_df_copy['drawdown'], 0,
                           color='red', alpha=0.3)
            ax3.plot(equity_df_copy['date'], equity_df_copy['drawdown'], color='red', linewidth=1)
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        ax3.set_title('策略回撤', fontsize=14, fontweight='bold')
        ax3.set_ylabel('回撤 (%)', fontsize=12)
        ax3.grid(True, alpha=0.3)
        
        # 4. ADX指标
        ax4 = fig.add_subplot(gs[2, 1])
        ax4.plot(data.index, data['adx'], color='purple', linewidth=1, label='ADX')
        ax4.axhline(y=20, color='red', linestyle='--', alpha=0.7, label='ADX=20')
        ax4.axhline(y=25, color='orange', linestyle='--', alpha=0.7, label='ADX=25')
        
        ax4.set_title('ADX趋势强度指标', fontsize=14, fontweight='bold')
        ax4.set_ylabel('ADX值', fontsize=12)
        ax4.legend(fontsize=10)
        ax4.grid(True, alpha=0.3)
        
        # 5. 月度收益热力图
        ax5 = fig.add_subplot(gs[3, :])
        if not equity_df.empty:
            # 计算月度收益
            equity_df_copy = equity_df.copy()
            equity_df_copy['year_month'] = equity_df_copy['date'].dt.to_period('M')
            monthly_returns = equity_df_copy.groupby('year_month')['equity'].agg(['first', 'last'])
            monthly_returns['return'] = (monthly_returns['last'] / monthly_returns['first'] - 1) * 100
            
            # 创建热力图数据
            monthly_returns.index = monthly_returns.index.astype(str)
            returns_data = monthly_returns['return'].values
            
            # 简单的颜色映射
            colors = ['red' if x < 0 else 'green' for x in returns_data]
            bars = ax5.bar(range(len(returns_data)), returns_data, color=colors, alpha=0.7)
            
            ax5.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            ax5.set_title('月度收益分布', fontsize=14, fontweight='bold')
            ax5.set_ylabel('月度收益 (%)', fontsize=12)
            ax5.set_xlabel('时间', fontsize=12)
            
            # 设置x轴标签（每6个月显示一次）
            tick_indices = range(0, len(monthly_returns), 6)
            ax5.set_xticks(tick_indices)
            ax5.set_xticklabels([monthly_returns.index[i] for i in tick_indices], rotation=45)
        
        ax5.grid(True, alpha=0.3)
        
        # 设置日期格式（对于时间序列图）
        for ax in [ax1, ax2, ax3, ax4]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.suptitle('QQQ EMA趋势策略 - 完整回测分析报告', fontsize=20, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        return fig
    
    def print_detailed_analysis(self, metrics):
        """打印详细分析报告"""
        print("\n" + "="*80)
        print("QQQ EMA趋势策略 - 详细回测分析报告")
        print("="*80)
        print(f"测试期间: {self.start_date} 至 {self.end_date}")
        print(f"初始资金: ${self.initial_capital:,}")
        
        if not self.equity_curve:
            print("无交易记录")
            return
        
        final_equity = self.equity_curve[-1]['equity']
        print(f"最终权益: ${final_equity:,.2f}")
        print(f"绝对收益: ${final_equity - self.initial_capital:,.2f}")
        
        print(f"\n📊 核心性能指标:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  年化收益率: {metrics['annual_return']:.2%}")
        print(f"  最大回撤: {metrics['max_drawdown']:.2%}")
        print(f"  夏普比率: {metrics['sharpe_ratio']:.3f}")
        print(f"  年化波动率: {metrics['volatility']:.2%}")
        
        print(f"\n📈 交易统计:")
        print(f"  总交易次数: {metrics['total_trades']}")
        print(f"  盈利交易: {metrics['profitable_trades']}")
        print(f"  亏损交易: {metrics['losing_trades']}")
        print(f"  胜率: {metrics['win_rate']:.2%}")
        print(f"  盈亏比: {metrics['profit_factor']:.2f}")
        print(f"  平均盈利: ${metrics['avg_profit']:.2f}")
        print(f"  平均亏损: ${metrics['avg_loss']:.2f}")
        print(f"  平均持仓天数: {metrics['avg_holding_days']:.1f}")
        
        # 基准对比
        if len(self.data) > 70:
            buy_hold_return = (self.data['close'].iloc[-1] / self.data['close'].iloc[70]) - 1
            excess_return = metrics['total_return'] - buy_hold_return
            
            print(f"\n📊 基准对比:")
            print(f"  策略收益率: {metrics['total_return']:.2%}")
            print(f"  买入持有收益率: {buy_hold_return:.2%}")
            print(f"  超额收益: {excess_return:.2%}")
        
        # 详细交易记录（最近10笔）
        sell_trades = [t for t in self.trades if t['type'] == 'SELL']
        if sell_trades:
            print(f"\n📝 最近10笔完整交易:")
            print("-" * 120)
            headers = ["买入日期", "卖出日期", "买入价", "卖出价", "持仓天数", "收益率", "盈亏金额", "退出原因"]
            print(f"{headers[0]:<12} {headers[1]:<12} {headers[2]:<8} {headers[3]:<8} {headers[4]:<8} {headers[5]:<8} {headers[6]:<12} {headers[7]}")
            print("-" * 120)
            
            # 找到对应的买入交易
            buy_trades = [t for t in self.trades if t['type'] == 'BUY']
            for i, sell_trade in enumerate(sell_trades[-10:]):
                if i < len(buy_trades):
                    buy_trade = buy_trades[-(10-i)]
                    print(f"{buy_trade['date'].strftime('%Y-%m-%d'):<12} "
                          f"{sell_trade['date'].strftime('%Y-%m-%d'):<12} "
                          f"${buy_trade['price']:<7.2f} "
                          f"${sell_trade['price']:<7.2f} "
                          f"{sell_trade.get('holding_days', 0):<8} "
                          f"{sell_trade.get('profit_pct', 0):<7.2%} "
                          f"${sell_trade.get('profit', 0):<11.2f} "
                          f"{sell_trade.get('exit_reason', 'N/A')}")
        
        print("="*80)
    
    def run_complete_analysis(self):
        """运行完整分析"""
        print("🚀 开始QQQ EMA趋势策略完整分析...")
        
        # 1. 准备数据
        self.download_and_prepare_data()
        
        # 2. 运行回测
        final_capital = self.run_enhanced_backtest()
        
        # 3. 计算指标
        metrics = self.calculate_performance_metrics()
        
        # 4. 生成图表
        print("📊 正在生成综合分析图表...")
        fig = self.create_comprehensive_charts()
        
        # 5. 保存图表
        plt.savefig('/home/user/webapp/comprehensive_qqq_analysis.png', 
                   dpi=300, bbox_inches='tight', facecolor='white')
        print("📈 图表已保存至: comprehensive_qqq_analysis.png")
        
        # 6. 打印报告
        self.print_detailed_analysis(metrics)
        
        plt.show()
        
        return {
            'data': self.data,
            'trades': self.trades,
            'signals': self.signals,
            'equity_curve': self.equity_curve,
            'metrics': metrics,
            'final_capital': final_capital
        }


def main():
    """主函数"""
    print("🎯 QQQ EMA趋势策略 - 综合回测分析系统")
    print("=" * 60)
    
    # 创建分析器
    analyzer = ComprehensiveQQQAnalysis(start_date='2021-01-01', end_date='2025-08-01')
    
    # 运行完整分析
    results = analyzer.run_complete_analysis()
    
    return analyzer, results


if __name__ == "__main__":
    analyzer, results = main()