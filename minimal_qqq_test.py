"""
最简化QQQ回测 - 验证基本逻辑
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
from strategies.indicators import calculate_ema, calculate_atr, calculate_adx

def minimal_backtest():
    """最简化回测逻辑"""
    print("最简化QQQ EMA策略回测...")
    
    # 下载数据
    ticker = yf.Ticker("QQQ")
    data = ticker.history(start='2021-01-01', end='2025-08-01', interval='1d')
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    data.columns = ['open', 'high', 'low', 'close', 'volume']
    
    print(f"数据长度: {len(data)}")
    
    # 计算指标
    data['ema20'] = calculate_ema(data['close'], 20)
    data['ema60'] = calculate_ema(data['close'], 60)
    adx, plus_di, minus_di = calculate_adx(data['high'], data['low'], data['close'], 14)
    data['adx'] = adx
    
    # 简化的交易逻辑
    capital = 100000
    position = 0  # 0=空仓, 1=持仓
    entry_price = 0
    trades = []
    signals = []
    equity = []
    
    for i in range(70, len(data)):  # 从第70天开始确保指标稳定
        current_price = data['close'].iloc[i]
        current_date = data.index[i]
        ema20 = data['ema20'].iloc[i]
        ema60 = data['ema60'].iloc[i]
        adx_val = data['adx'].iloc[i]
        
        # 简单的趋势判断
        is_uptrend = (ema20 > ema60) and (adx_val > 20)
        
        # 买入信号：无持仓 + 上升趋势 + 价格上涨
        if position == 0 and is_uptrend and current_price > data['close'].iloc[i-1]:
            # 买入
            shares = int(capital / current_price)
            if shares > 0:
                position = 1
                entry_price = current_price
                capital -= shares * current_price
                
                trades.append({
                    'type': 'BUY',
                    'date': current_date,
                    'price': current_price,
                    'shares': shares
                })
                
                signals.append({
                    'date': current_date,
                    'price': current_price,
                    'signal': 'BUY'
                })
                
                print(f"{current_date.strftime('%Y-%m-%d')}: 买入 {shares} 股，价格 ${current_price:.2f}")
        
        # 卖出信号：有持仓 + (趋势转弱 或 价格跌破EMA20)
        elif position == 1 and (not is_uptrend or current_price < ema20 * 0.98):
            # 卖出
            sell_amount = shares * current_price
            capital += sell_amount
            profit = sell_amount - shares * entry_price
            
            trades.append({
                'type': 'SELL',
                'date': current_date,
                'price': current_price,
                'shares': shares,
                'profit': profit
            })
            
            signals.append({
                'date': current_date,
                'price': current_price,
                'signal': 'SELL'
            })
            
            print(f"{current_date.strftime('%Y-%m-%d')}: 卖出 {shares} 股，价格 ${current_price:.2f}，盈亏 ${profit:.2f}")
            
            position = 0
            shares = 0
            entry_price = 0
        
        # 计算当前权益
        current_equity = capital
        if position == 1:
            current_equity += shares * current_price
            
        equity.append({
            'date': current_date,
            'equity': current_equity
        })
    
    # 最终平仓
    if position == 1:
        final_price = data['close'].iloc[-1]
        final_amount = shares * final_price
        capital += final_amount
        profit = final_amount - shares * entry_price
        
        print(f"最终平仓: 卖出 {shares} 股，价格 ${final_price:.2f}，盈亏 ${profit:.2f}")
    
    # 计算结果
    total_trades = len([t for t in trades if t['type'] == 'BUY'])
    total_return = (capital - 100000) / 100000
    
    print(f"\n回测结果:")
    print(f"总交易次数: {total_trades}")
    print(f"初始资金: $100,000")
    print(f"最终资金: ${capital:,.2f}")
    print(f"总收益: ${capital - 100000:,.2f}")
    print(f"总收益率: {total_return:.2%}")
    
    # 绘制图表
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
    
    # 价格图
    ax1.plot(data.index, data['close'], label='QQQ Close', color='black', linewidth=1)
    ax1.plot(data.index, data['ema20'], label='EMA20', color='blue', alpha=0.8)
    ax1.plot(data.index, data['ema60'], label='EMA60', color='red', alpha=0.8)
    
    # 标注信号
    if signals:
        signals_df = pd.DataFrame(signals)
        buy_signals = signals_df[signals_df['signal'] == 'BUY']
        sell_signals = signals_df[signals_df['signal'] == 'SELL']
        
        if not buy_signals.empty:
            ax1.scatter(buy_signals['date'], buy_signals['price'],
                       marker='^', color='green', s=80, label='买入', zorder=5)
        if not sell_signals.empty:
            ax1.scatter(sell_signals['date'], sell_signals['price'],
                       marker='v', color='red', s=80, label='卖出', zorder=5)
    
    ax1.set_title('QQQ价格与EMA策略信号', fontsize=14)
    ax1.set_ylabel('价格 ($)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 权益曲线
    if equity:
        equity_df = pd.DataFrame(equity)
        ax2.plot(equity_df['date'], equity_df['equity'], color='blue', linewidth=2)
        ax2.axhline(y=100000, color='gray', linestyle='--', alpha=0.7, label='初始资金')
        
    ax2.set_title('权益曲线', fontsize=14)
    ax2.set_ylabel('权益 ($)')
    ax2.set_xlabel('日期')
    ax2.grid(True, alpha=0.3)
    
    # 设置日期格式
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig('/home/user/webapp/minimal_qqq_results.png', dpi=300, bbox_inches='tight')
    print("图表已保存至: minimal_qqq_results.png")
    
    plt.show()
    
    return data, trades, signals, equity

if __name__ == "__main__":
    data, trades, signals, equity = minimal_backtest()