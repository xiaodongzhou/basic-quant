"""
简化版QQQ策略测试脚本
直接实现EMA趋势策略的核心逻辑进行回测
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

# 导入指标计算模块
from strategies.indicators import calculate_ema, calculate_atr, calculate_adx

# 设置中文字体和图表样式
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('default')

class SimpleEMAStrategy:
    """简化版EMA趋势策略"""
    
    def __init__(self, ema_short=20, ema_long=60, adx_threshold=20.0, risk_per_trade=0.02):
        self.ema_short = ema_short
        self.ema_long = ema_long  
        self.adx_threshold = adx_threshold  # 降低ADX阈值
        self.risk_per_trade = risk_per_trade
        
    def analyze_trend(self, df: pd.DataFrame, idx: int) -> str:
        """分析趋势方向"""
        if idx < max(self.ema_long, 14):  # 确保有足够数据
            return "SIDEWAYS"
            
        ema20 = df['ema20'].iloc[idx]
        ema60 = df['ema60'].iloc[idx]
        adx = df['adx'].iloc[idx]
        
        # ADX过滤：只在强趋势时交易
        if pd.isna(adx) or adx < self.adx_threshold:
            return "SIDEWAYS"
            
        # EMA趋势判断
        if ema20 > ema60:
            return "UP"
        elif ema20 < ema60:
            return "DOWN" 
        else:
            return "SIDEWAYS"
    
    def check_entry_signal(self, df: pd.DataFrame, idx: int, trend: str) -> str:
        """检查入场信号 - 简化版本"""
        if trend == "SIDEWAYS" or idx < 5:
            return "NONE"
            
        current_price = df['close'].iloc[idx]
        prev_price = df['close'].iloc[idx-1]
        ema20 = df['ema20'].iloc[idx]
        ema20_prev = df['ema20'].iloc[idx-1]
        
        # 做多信号：上升趋势中的简单条件
        if trend == "UP":
            # 价格在EMA20上方且价格上涨
            if (current_price > ema20 and 
                current_price > prev_price and
                ema20 > ema20_prev):  # EMA20也在上涨
                return "LONG"
        
        # 做空信号：下降趋势中的简单条件  
        elif trend == "DOWN":
            # 价格在EMA20下方且价格下跌
            if (current_price < ema20 and
                current_price < prev_price and
                ema20 < ema20_prev):  # EMA20也在下跌
                return "SHORT"
                
        return "NONE"
    
    def check_exit_signal(self, df: pd.DataFrame, idx: int, position_direction: str, entry_price: float) -> bool:
        """检查出场信号"""
        if idx < 2:
            return False
            
        current_price = df['close'].iloc[idx]
        ema20_current = df['ema20'].iloc[idx]
        ema20_prev = df['ema20'].iloc[idx-1]
        
        # EMA20转向信号
        if position_direction == "LONG":
            # 多头出场：EMA20开始下降或价格跌破EMA20
            if (ema20_current < ema20_prev or 
                current_price < ema20_current * 0.98):  # 跌破EMA20的2%
                return True
        elif position_direction == "SHORT":
            # 空头出场：EMA20开始上升或价格突破EMA20  
            if (ema20_current > ema20_prev or
                current_price > ema20_current * 1.02):  # 突破EMA20的2%
                return True
                
        return False

def download_qqq_data(start_date='2021-01-01', end_date='2025-08-01'):
    """下载QQQ数据"""
    print(f"正在下载QQQ数据: {start_date} 到 {end_date}")
    
    ticker = yf.Ticker("QQQ")
    data = ticker.history(start=start_date, end=end_date, interval='1d')
    
    if data.empty:
        raise ValueError("未能获取到数据")
    
    # 处理列名
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    data.columns = ['open', 'high', 'low', 'close', 'volume']
    
    # 确保数据类型正确并删除空值
    for col in ['open', 'high', 'low', 'close', 'volume']:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    data = data.dropna()
    
    print(f"成功下载数据: {len(data)} 条记录")
    print(f"数据时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
    
    return data

def calculate_indicators(df):
    """计算技术指标"""
    print("正在计算技术指标...")
    
    # 计算EMA
    df['ema20'] = calculate_ema(df['close'], 20)
    df['ema60'] = calculate_ema(df['close'], 60)
    
    # 计算ATR
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)
    
    # 计算ADX
    adx, plus_di, minus_di = calculate_adx(df['high'], df['low'], df['close'], 14)
    df['adx'] = adx
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di
    
    print("技术指标计算完成")
    return df

def run_backtest(df, initial_capital=100000):
    """运行回测"""
    print("开始回测...")
    
    strategy = SimpleEMAStrategy()
    
    # 初始化回测变量
    capital = initial_capital
    position = None  # {'direction': 'LONG/SHORT', 'size': int, 'entry_price': float, 'entry_idx': int}
    trades = []
    equity_curve = []
    signals = []
    
    # 遍历数据
    for i in range(60, len(df)):  # 从第60根K线开始，确保指标完整
        current_price = df['close'].iloc[i]
        current_date = df.index[i]
        
        # 分析趋势
        trend = strategy.analyze_trend(df, i)
        
        # 当前无持仓时检查入场机会
        if position is None:
            entry_signal = strategy.check_entry_signal(df, i, trend)
            
            if entry_signal != "NONE":
                # 计算仓位大小
                atr_value = df['atr'].iloc[i]
                if pd.notna(atr_value) and atr_value > 0:
                    risk_amount = capital * strategy.risk_per_trade
                    stop_distance = 2 * atr_value  # 2倍ATR止损
                    position_size = risk_amount / stop_distance
                    shares = int(position_size / current_price)
                    
                    if shares > 0:
                        # 开仓
                        position = {
                            'direction': entry_signal,
                            'size': shares,
                            'entry_price': current_price,
                            'entry_idx': i,
                            'stop_loss': current_price - stop_distance if entry_signal == 'LONG' else current_price + stop_distance
                        }
                        
                        signals.append({
                            'date': current_date,
                            'price': current_price, 
                            'signal': 'BUY' if entry_signal == 'LONG' else 'SELL',
                            'type': 'ENTRY'
                        })
                        
                        print(f"{current_date.strftime('%Y-%m-%d')}: {'做多' if entry_signal == 'LONG' else '做空'} "
                              f"价格: {current_price:.2f}, 股数: {shares}")
        
        # 持仓时检查出场机会
        else:
            exit_signal = False
            exit_reason = ""
            
            # 检查策略出场信号
            if strategy.check_exit_signal(df, i, position['direction'], position['entry_price']):
                exit_signal = True
                exit_reason = "STRATEGY_EXIT"
            
            # 检查止损
            elif ((position['direction'] == 'LONG' and current_price <= position['stop_loss']) or
                  (position['direction'] == 'SHORT' and current_price >= position['stop_loss'])):
                exit_signal = True
                exit_reason = "STOP_LOSS"
            
            # 执行出场
            if exit_signal:
                # 计算盈亏
                if position['direction'] == 'LONG':
                    pnl = (current_price - position['entry_price']) * position['size']
                else:  # SHORT
                    pnl = (position['entry_price'] - current_price) * position['size']
                
                capital += pnl
                
                # 记录交易
                trades.append({
                    'entry_date': df.index[position['entry_idx']],
                    'exit_date': current_date,
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'size': position['size'],
                    'pnl': pnl,
                    'return': pnl / (position['size'] * position['entry_price']),
                    'exit_reason': exit_reason,
                    'days': i - position['entry_idx']
                })
                
                signals.append({
                    'date': current_date,
                    'price': current_price,
                    'signal': 'SELL' if position['direction'] == 'LONG' else 'BUY', 
                    'type': exit_reason
                })
                
                print(f"{current_date.strftime('%Y-%m-%d')}: {'平多' if position['direction'] == 'LONG' else '平空'} "
                      f"价格: {current_price:.2f}, 盈亏: {pnl:.2f} ({exit_reason})")
                
                position = None  # 重置持仓
        
        # 计算当前权益
        current_equity = capital
        if position is not None:
            if position['direction'] == 'LONG':
                unrealized_pnl = (current_price - position['entry_price']) * position['size']
            else:
                unrealized_pnl = (position['entry_price'] - current_price) * position['size']
            current_equity += unrealized_pnl
        
        equity_curve.append({
            'date': current_date,
            'equity': current_equity,
            'capital': capital
        })
    
    print(f"回测完成! 交易次数: {len(trades)}")
    
    return {
        'trades': trades,
        'equity_curve': equity_curve,
        'signals': signals,
        'initial_capital': initial_capital,
        'final_capital': capital
    }

def calculate_metrics(results):
    """计算绩效指标"""
    trades = results['trades']
    equity_curve = pd.DataFrame(results['equity_curve'])
    
    if len(trades) == 0:
        return {
            'total_trades': 0, 
            'total_return': 0.0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'annual_return': 0.0,
            'max_drawdown': 0.0,
            'total_pnl': 0.0,
            'avg_trade_pnl': 0.0,
            'avg_winning_trade': 0.0,
            'avg_losing_trade': 0.0,
            'profit_factor': 0.0,
            'avg_holding_days': 0.0,
        }
    
    # 基础统计
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t['pnl'] > 0])
    win_rate = winning_trades / total_trades
    
    total_pnl = sum(t['pnl'] for t in trades)
    total_return = total_pnl / results['initial_capital']
    
    # 计算最大回撤
    equity_curve['peak'] = equity_curve['equity'].cummax()
    equity_curve['drawdown'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak']
    max_drawdown = equity_curve['drawdown'].min()
    
    # 年化收益率
    start_date = equity_curve['date'].iloc[0]
    end_date = equity_curve['date'].iloc[-1] 
    days = (end_date - start_date).days
    years = days / 365.25
    annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
    
    # 其他指标
    avg_trade_pnl = total_pnl / total_trades
    avg_winning_trade = np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if winning_trades > 0 else 0
    avg_losing_trade = np.mean([t['pnl'] for t in trades if t['pnl'] < 0]) if winning_trades < total_trades else 0
    
    # 胜负比
    profit_factor = abs(avg_winning_trade * winning_trades / avg_losing_trade / (total_trades - winning_trades)) if avg_losing_trade < 0 else float('inf')
    
    # 平均持仓天数
    avg_holding_days = np.mean([t['days'] for t in trades])
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': total_trades - winning_trades,
        'win_rate': win_rate,
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'total_pnl': total_pnl,
        'avg_trade_pnl': avg_trade_pnl,
        'avg_winning_trade': avg_winning_trade,
        'avg_losing_trade': avg_losing_trade,
        'profit_factor': profit_factor,
        'avg_holding_days': avg_holding_days,
    }

def plot_results(df, results, figsize=(15, 12)):
    """绘制回测结果"""
    equity_curve = pd.DataFrame(results['equity_curve'])
    signals_df = pd.DataFrame(results['signals'])
    
    fig, axes = plt.subplots(3, 1, figsize=figsize)
    
    # 1. K线图和交易信号
    ax1 = axes[0]
    
    # 绘制价格和EMA
    ax1.plot(df.index, df['close'], label='QQQ Close', color='black', linewidth=1)
    ax1.plot(df.index, df['ema20'], label='EMA20', color='blue', alpha=0.8, linewidth=1)
    ax1.plot(df.index, df['ema60'], label='EMA60', color='red', alpha=0.8, linewidth=1)
    
    # 标注买卖点
    if not signals_df.empty:
        buy_signals = signals_df[signals_df['signal'] == 'BUY']
        sell_signals = signals_df[signals_df['signal'] == 'SELL']
        
        if not buy_signals.empty:
            ax1.scatter(buy_signals['date'], buy_signals['price'], 
                       marker='^', color='green', s=60, label='买入信号', zorder=5)
        
        if not sell_signals.empty:
            ax1.scatter(sell_signals['date'], sell_signals['price'],
                       marker='v', color='red', s=60, label='卖出信号', zorder=5)
    
    ax1.set_title('QQQ 价格走势与EMA趋势策略交易信号', fontsize=14, fontweight='bold')
    ax1.set_ylabel('价格 ($)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 2. 权益曲线
    ax2 = axes[1]
    if not equity_curve.empty:
        ax2.plot(equity_curve['date'], equity_curve['equity'], 
                 label='总权益', color='blue', linewidth=2)
        ax2.axhline(y=results['initial_capital'], 
                   color='gray', linestyle='--', alpha=0.7, label='初始资金')
    
    ax2.set_title('权益曲线', fontsize=14, fontweight='bold')
    ax2.set_ylabel('权益 ($)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 收益率曲线和回撤
    ax3 = axes[2]
    if not equity_curve.empty:
        returns = (equity_curve['equity'] / results['initial_capital'] - 1) * 100
        ax3.plot(equity_curve['date'], returns, 
                 label='累计收益率', color='green', linewidth=2)
        
        # 计算并显示回撤
        peak = equity_curve['equity'].cummax()
        drawdown = (equity_curve['equity'] - peak) / peak * 100
        ax3.fill_between(equity_curve['date'], drawdown, 0,
                        color='red', alpha=0.3, label='回撤')
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    ax3.set_title('收益率与回撤', fontsize=14, fontweight='bold')
    ax3.set_ylabel('百分比 (%)')
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

def print_performance_summary(results, metrics):
    """打印绩效总结"""
    print("\n" + "="*60)
    print("QQQ EMA趋势策略 - 回测结果总结") 
    print("="*60)
    print(f"初始资金: ${results['initial_capital']:,.2f}")
    print(f"最终资金: ${results['final_capital']:,.2f}")
    print(f"总盈亏: ${metrics['total_pnl']:,.2f}")
    print()
    print("交易统计:")
    print(f"  总交易次数: {metrics['total_trades']}")
    print(f"  盈利交易: {metrics['winning_trades']}")
    print(f"  亏损交易: {metrics['losing_trades']}")
    print(f"  胜率: {metrics['win_rate']:.2%}")
    print(f"  平均每笔盈亏: ${metrics['avg_trade_pnl']:,.2f}")
    print(f"  平均盈利交易: ${metrics['avg_winning_trade']:,.2f}")
    print(f"  平均亏损交易: ${metrics['avg_losing_trade']:,.2f}")
    print(f"  盈亏比: {metrics['profit_factor']:.2f}")
    print(f"  平均持仓天数: {metrics['avg_holding_days']:.1f}")
    print()
    print("收益指标:")
    print(f"  总收益率: {metrics['total_return']:.2%}")
    print(f"  年化收益率: {metrics['annual_return']:.2%}")
    print(f"  最大回撤: {metrics['max_drawdown']:.2%}")
    print("="*60)
    
    # 打印详细交易记录（最近10笔）
    if results['trades']:
        print("\n最近10笔交易:")
        print("-" * 100)
        print(f"{'入场日期':<12} {'出场日期':<12} {'方向':<6} {'入场价':<8} {'出场价':<8} {'盈亏':<10} {'收益率':<8} {'持仓天数':<6} {'出场原因'}")
        print("-" * 100)
        
        for trade in results['trades'][-10:]:
            print(f"{trade['entry_date'].strftime('%Y-%m-%d'):<12} "
                  f"{trade['exit_date'].strftime('%Y-%m-%d'):<12} "
                  f"{trade['direction']:<6} "
                  f"{trade['entry_price']:>8.2f} "
                  f"{trade['exit_price']:>8.2f} "
                  f"{trade['pnl']:>10.2f} "
                  f"{trade['return']:>7.2%} "
                  f"{trade['days']:>6} "
                  f"{trade['exit_reason']}")

def main():
    """主函数"""
    print("QQQ EMA趋势策略回测开始...")
    
    try:
        # 1. 下载数据
        df = download_qqq_data('2021-01-01', '2025-08-01')
        
        # 2. 计算指标
        df = calculate_indicators(df)
        
        # 3. 运行回测
        results = run_backtest(df, initial_capital=100000)
        
        # 4. 计算指标
        metrics = calculate_metrics(results)
        
        # 5. 打印结果
        print_performance_summary(results, metrics)
        
        # 6. 绘制图表
        print("\n正在生成图表...")
        fig = plot_results(df, results)
        
        # 保存图表
        plt.savefig('/home/user/webapp/simple_qqq_results.png', dpi=300, bbox_inches='tight')
        print("图表已保存至: simple_qqq_results.png")
        
        plt.show()
        
        return df, results, metrics
        
    except Exception as e:
        print(f"回测过程发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

if __name__ == "__main__":
    df, results, metrics = main()