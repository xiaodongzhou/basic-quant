#!/usr/bin/env python3
"""
MLAS可视化脚本 - 创建完整的分析图表
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from mlas_implementation import MLAdaptiveSuperTrend

def create_mlas_visualization(data, title="MLAS - Machine Learning Adaptive SuperTrend Analysis", last_days=252):
    """
    创建MLAS完整可视化分析图表
    """
    if data is None or len(data) == 0:
        print("❌ 无数据可绘制")
        return None
    
    # 选择最近的数据
    plot_data = data.tail(last_days) if len(data) > last_days else data
    
    # 创建子图 - 4行布局
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            'QQQ价格 + MLAS SuperTrend + 波动率聚类',
            'K-Means波动率聚类时序分布',
            'ATR波动率 + 聚类质心',
            '趋势信号变化'
        ),
        row_heights=[0.4, 0.2, 0.25, 0.15]
    )
    
    # 第一个子图：价格 + SuperTrend + 聚类着色
    # K线图
    fig.add_trace(
        go.Candlestick(
            x=plot_data.index,
            open=plot_data['open'],
            high=plot_data['high'],
            low=plot_data['low'],
            close=plot_data['close'],
            name='QQQ价格',
            increasing_line_color='green',
            decreasing_line_color='red'
        ),
        row=1, col=1
    )
    
    # MLAS SuperTrend线
    if 'supertrend' in plot_data.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_data.index,
                y=plot_data['supertrend'],
                mode='lines',
                name='MLAS SuperTrend',
                line=dict(color='blue', width=3)
            ),
            row=1, col=1
        )
    
    # 波动率聚类着色点
    if 'cluster' in plot_data.columns:
        cluster_colors = {0: 'red', 1: 'orange', 2: 'green'}  # 高中低波动率
        cluster_names = {0: '高波动率', 1: '中波动率', 2: '低波动率'}
        
        for cluster_id in [0, 1, 2]:
            cluster_data = plot_data[plot_data['cluster'] == cluster_id]
            if len(cluster_data) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=cluster_data.index,
                        y=cluster_data['close'],
                        mode='markers',
                        name=f'{cluster_names[cluster_id]} ({len(cluster_data)}点)',
                        marker=dict(
                            color=cluster_colors[cluster_id], 
                            size=6, 
                            opacity=0.7,
                            symbol='circle'
                        )
                    ),
                    row=1, col=1
                )
    
    # 趋势背景色
    if 'trend_signal' in plot_data.columns:
        for i in range(len(plot_data)-1):
            if not pd.isna(plot_data['trend_signal'].iloc[i]):
                color = 'rgba(0,255,0,0.05)' if plot_data['trend_signal'].iloc[i] == 1 else 'rgba(255,0,0,0.05)'
                fig.add_shape(
                    type="rect",
                    x0=plot_data.index[i],
                    y0=plot_data['low'].min() * 0.95,
                    x1=plot_data.index[i+1],
                    y1=plot_data['high'].max() * 1.05,
                    fillcolor=color,
                    line=dict(width=0),
                    row=1, col=1
                )
    
    # 第二个子图：聚类时序分布
    if 'cluster' in plot_data.columns:
        cluster_colors = {0: 'red', 1: 'orange', 2: 'green'}
        cluster_names = {0: '高波动率', 1: '中波动率', 2: '低波动率'}
        
        for cluster_id in [0, 1, 2]:
            cluster_points = plot_data[plot_data['cluster'] == cluster_id]
            if len(cluster_points) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=cluster_points.index,
                        y=[cluster_id] * len(cluster_points),
                        mode='markers',
                        name=f'{cluster_names[cluster_id]}聚类',
                        marker=dict(
                            color=cluster_colors[cluster_id], 
                            size=8, 
                            opacity=0.8,
                            symbol='square'
                        ),
                        showlegend=False
                    ),
                    row=2, col=1
                )
    
    # 第三个子图：ATR波动率 + 聚类质心
    if 'volatility' in plot_data.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_data.index,
                y=plot_data['volatility'],
                mode='lines',
                name='ATR波动率',
                line=dict(color='blue', width=1.5)
            ),
            row=3, col=1
        )
    
    # 聚类质心线 
    if 'assigned_centroid' in plot_data.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_data.index,
                y=plot_data['assigned_centroid'],
                mode='lines',
                name='分配的质心',
                line=dict(color='red', width=2, dash='dash')
            ),
            row=3, col=1
        )
    
    # 显示各个质心
    centroid_cols = ['high_centroid', 'mid_centroid', 'low_centroid']
    centroid_colors = ['red', 'orange', 'green']
    centroid_names = ['高波动率质心', '中波动率质心', '低波动率质心']
    
    for i, (col, color, name) in enumerate(zip(centroid_cols, centroid_colors, centroid_names)):
        if col in plot_data.columns:
            valid_data = plot_data[plot_data[col].notna()]
            if len(valid_data) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=valid_data.index,
                        y=valid_data[col],
                        mode='lines',
                        name=name,
                        line=dict(color=color, width=1, dash='dot'),
                        opacity=0.7
                    ),
                    row=3, col=1
                )
    
    # 第四个子图：趋势信号变化
    if 'trend_signal' in plot_data.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_data.index,
                y=plot_data['trend_signal'],
                mode='lines+markers',
                name='趋势信号',
                line=dict(color='purple', width=2),
                marker=dict(size=4)
            ),
            row=4, col=1
        )
        
        # 标记信号变化点
        if 'signal_change' in plot_data.columns:
            signal_changes = plot_data[plot_data['signal_change'] != 0]
            if len(signal_changes) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=signal_changes.index,
                        y=signal_changes['trend_signal'],
                        mode='markers',
                        name='信号变化',
                        marker=dict(
                            color='red',
                            size=10,
                            symbol='star'
                        )
                    ),
                    row=4, col=1
                )
    
    # 更新布局
    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            font=dict(size=16)
        ),
        height=900,
        showlegend=True,
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 更新x轴
    fig.update_xaxes(rangeslider_visible=False)
    
    # 更新y轴标签
    fig.update_yaxes(title_text="价格 ($)", row=1, col=1)
    fig.update_yaxes(title_text="聚类ID", row=2, col=1, tickvals=[0, 1, 2], ticktext=['高', '中', '低'])
    fig.update_yaxes(title_text="ATR波动率", row=3, col=1)
    fig.update_yaxes(title_text="信号", row=4, col=1, tickvals=[-1, 0, 1], ticktext=['下降', '中性', '上升'])
    
    return fig

def generate_mlas_report(data):
    """
    生成MLAS分析报告
    """
    print("📊 MLAS (Machine Learning Adaptive SuperTrend) 分析报告")
    print("=" * 60)
    
    # 基础统计
    print(f"📈 数据期间: {data.index[0].date()} 到 {data.index[-1].date()}")
    print(f"📊 总数据点: {len(data)}")
    
    if 'supertrend' in data.columns:
        print(f"📈 SuperTrend有效点: {data['supertrend'].count()}")
    
    # K-Means聚类分析
    if 'cluster' in data.columns:
        print(f"\n🤖 K-Means波动率聚类分析:")
        cluster_counts = data['cluster'].value_counts().sort_index()
        cluster_labels = {0: '高波动率', 1: '中波动率', 2: '低波动率'}
        
        total_clustered = data['cluster'].count()
        print(f"  聚类有效点: {total_clustered}")
        
        for cluster_id, count in cluster_counts.items():
            if not pd.isna(cluster_id):
                label = cluster_labels.get(int(cluster_id), f'未知({int(cluster_id)})')
                percentage = count / total_clustered * 100
                print(f"  {label}: {count}次 ({percentage:.1f}%)")
    
    # 趋势分析
    if 'trend_signal' in data.columns:
        print(f"\n📈 趋势信号分析:")
        trend_counts = data['trend_signal'].value_counts()
        
        for trend_val, count in trend_counts.items():
            trend_name = '上升' if trend_val == 1 else '下降' if trend_val == -1 else '中性'
            percentage = count / len(data) * 100
            print(f"  {trend_name}趋势: {count}天 ({percentage:.1f}%)")
    
    # 交易信号统计
    if 'signal_change' in data.columns:
        signal_changes = data[data['signal_change'] != 0]
        buy_signals = data[data['signal_change'] == 2]
        sell_signals = data[data['signal_change'] == -2]
        
        print(f"\n📡 交易信号统计:")
        print(f"  总信号变化: {len(signal_changes)}次")
        print(f"  买入信号: {len(buy_signals)}次")
        print(f"  卖出信号: {len(sell_signals)}次")
        
        if len(buy_signals) > 0:
            print(f"  最近买入: {buy_signals.index[-1].date()}")
        if len(sell_signals) > 0:
            print(f"  最近卖出: {sell_signals.index[-1].date()}")
    
    # 波动率质心统计
    if 'assigned_centroid' in data.columns:
        centroids = data['assigned_centroid'].dropna()
        if len(centroids) > 0:
            print(f"\n🎯 自适应质心统计:")
            print(f"  平均ATR质心: {centroids.mean():.3f}")
            print(f"  质心范围: {centroids.min():.3f} - {centroids.max():.3f}")
            print(f"  质心标准差: {centroids.std():.3f}")
    
    # 当前状态
    print(f"\n📋 当前市场状态:")
    latest = data.iloc[-1]
    print(f"  当前价格: ${latest['close']:.2f}")
    
    if 'supertrend' in data.columns and not pd.isna(latest['supertrend']):
        print(f"  MLAS SuperTrend: ${latest['supertrend']:.2f}")
        
    if 'cluster' in data.columns and not pd.isna(latest['cluster']):
        cluster_labels = {0: '高波动率', 1: '中波动率', 2: '低波动率'}
        cluster_name = cluster_labels.get(int(latest['cluster']), '未知')
        print(f"  波动率级别: {cluster_name}")
        
    if 'trend_signal' in data.columns and not pd.isna(latest['trend_signal']):
        trend_name = '上升' if latest['trend_signal'] == 1 else '下降' if latest['trend_signal'] == -1 else '中性'
        print(f"  当前趋势: {trend_name}")
        
    if 'volatility' in data.columns and not pd.isna(latest['volatility']):
        print(f"  当前ATR波动率: {latest['volatility']:.3f}")

def main():
    """
    主函数 - 创建完整的MLAS分析和可视化
    """
    print("🚀 MLAS (Machine Learning Adaptive SuperTrend) 完整分析")
    print("=" * 60)
    
    # 获取数据
    print("📊 获取QQQ数据...")
    ticker = yf.Ticker('QQQ')
    data = ticker.history(start='2023-01-01', end='2025-01-01', interval='1d')
    
    # 重命名列
    data = data.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low',
        'Close': 'close', 'Volume': 'volume'
    })
    
    print(f"✅ 获取{len(data)}条数据")
    
    # 创建MLAS实例并计算
    print("\n🤖 计算MLAS指标...")
    mlas = MLAdaptiveSuperTrend(
        atr_len=10,
        factor=3.0,
        training_data_period=100,
        high_vol_percentile=0.75,
        mid_vol_percentile=0.5,
        low_vol_percentile=0.25
    )
    
    results = mlas.calculate(data)
    print("✅ MLAS计算完成")
    
    # 生成分析报告
    print("\n" + "="*60)
    generate_mlas_report(results)
    print("="*60)
    
    # 创建可视化
    print("\n📊 生成可视化图表...")
    fig = create_mlas_visualization(results, "QQQ MLAS分析 - Pine Script精确Python实现", last_days=252)
    
    if fig is not None:
        # 保存为HTML
        html_file = 'mlas_analysis.html'
        fig.write_html(html_file)
        print(f"✅ 交互式图表已保存到: {html_file}")
        
        # 显示图表
        fig.show()
    
    # 保存数据
    csv_file = 'mlas_complete_results.csv'
    results.to_csv(csv_file)
    print(f"💾 完整数据已保存到: {csv_file}")
    
    print("\n🎉 MLAS完整分析完成!")
    return results, fig

if __name__ == "__main__":
    results, figure = main()