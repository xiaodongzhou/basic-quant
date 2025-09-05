#!/usr/bin/env python3
"""
Machine Learning Adaptive SuperTrend (MLAS) - Python实现
精确复制AlgoAlpha Pine Script算法
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Tuple, Dict, List, Optional

class MLAdaptiveSuperTrend:
    """
    Machine Learning Adaptive SuperTrend指标 - Python实现
    基于Pine Script版本的精确转换
    """
    
    def __init__(self, 
                 atr_len: int = 10,
                 factor: float = 3.0,
                 training_data_period: int = 100,
                 high_vol_percentile: float = 0.75,
                 mid_vol_percentile: float = 0.5,
                 low_vol_percentile: float = 0.25):
        """
        初始化MLAS指标参数
        
        Args:
            atr_len: ATR计算周期 (对应Pine Script的atr_len)
            factor: SuperTrend倍数 (对应Pine Script的fact)
            training_data_period: K-Means训练数据长度 (对应training_data_period)
            high_vol_percentile: 高波动率百分位 (对应highvol)
            mid_vol_percentile: 中波动率百分位 (对应midvol)
            low_vol_percentile: 低波动率百分位 (对应lowvol)
        """
        self.atr_len = atr_len
        self.factor = factor
        self.training_data_period = training_data_period
        self.high_vol_percentile = high_vol_percentile
        self.mid_vol_percentile = mid_vol_percentile
        self.low_vol_percentile = low_vol_percentile
        
    def pine_supertrend(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                       factor: float, atr_values: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Pine Script SuperTrend函数的精确Python实现
        
        Args:
            high, low, close: OHLC价格序列
            factor: SuperTrend倍数
            atr_values: ATR值序列
            
        Returns:
            (supertrend, direction): SuperTrend值和方向
        """
        # 计算HL2 (src = hl2)
        hl2 = (high + low) / 2
        
        # 初始化输出序列
        supertrend = pd.Series(np.nan, index=close.index, name='supertrend')
        direction = pd.Series(np.nan, index=close.index, name='direction')
        upper_band = pd.Series(np.nan, index=close.index, name='upper_band')
        lower_band = pd.Series(np.nan, index=close.index, name='lower_band')
        
        for i in range(len(close)):
            if pd.isna(atr_values.iloc[i]):
                continue
                
            # 计算当前上下轨 
            curr_upper = hl2.iloc[i] + factor * atr_values.iloc[i]
            curr_lower = hl2.iloc[i] - factor * atr_values.iloc[i]
            
            # 上轨处理 (对应Pine Script upperBand逻辑)
            if i == 0:
                upper_band.iloc[i] = curr_upper
                lower_band.iloc[i] = curr_lower
            else:
                prev_upper = upper_band.iloc[i-1] if not pd.isna(upper_band.iloc[i-1]) else curr_upper
                prev_lower = lower_band.iloc[i-1] if not pd.isna(lower_band.iloc[i-1]) else curr_lower
                prev_close = close.iloc[i-1]
                
                # upperBand := upperBand < prevUpperBand or close[1] > prevUpperBand ? upperBand : prevUpperBand
                if curr_upper < prev_upper or prev_close > prev_upper:
                    upper_band.iloc[i] = curr_upper
                else:
                    upper_band.iloc[i] = prev_upper
                    
                # lowerBand := lowerBand > prevLowerBand or close[1] < prevLowerBand ? lowerBand : prevLowerBand  
                if curr_lower > prev_lower or prev_close < prev_lower:
                    lower_band.iloc[i] = curr_lower
                else:
                    lower_band.iloc[i] = prev_lower
            
            # 方向判断 (对应Pine Script _direction逻辑)
            if i == 0:
                direction.iloc[i] = 1  # 初始方向向上
            else:
                prev_supertrend = supertrend.iloc[i-1] if not pd.isna(supertrend.iloc[i-1]) else upper_band.iloc[i-1]
                prev_direction = direction.iloc[i-1] if not pd.isna(direction.iloc[i-1]) else 1
                
                # Pine Script逻辑转换
                if pd.isna(atr_values.iloc[i-1]) if i > 0 else True:
                    direction.iloc[i] = 1
                elif prev_supertrend == upper_band.iloc[i-1]:
                    # prevSuperTrend == prevUpperBand
                    direction.iloc[i] = -1 if close.iloc[i] > upper_band.iloc[i] else 1
                else:
                    # else条件 
                    direction.iloc[i] = 1 if close.iloc[i] < lower_band.iloc[i] else -1
            
            # SuperTrend值 (superTrend := _direction == -1 ? lowerBand : upperBand)
            if direction.iloc[i] == -1:
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
        
        return supertrend, direction
    
    def k_means_volatility_clustering(self, volatility: pd.Series, 
                                    training_period: int) -> Dict[str, pd.Series]:
        """
        K-Means波动率聚类算法 - 精确复制Pine Script实现
        
        Args:
            volatility: ATR波动率序列
            training_period: 训练数据期间长度
            
        Returns:
            包含聚类结果的字典
        """
        # 初始化输出
        cluster_assignments = pd.Series(np.nan, index=volatility.index, name='cluster')
        assigned_centroids = pd.Series(np.nan, index=volatility.index, name='assigned_centroid') 
        high_centroids = pd.Series(np.nan, index=volatility.index, name='high_centroid')
        mid_centroids = pd.Series(np.nan, index=volatility.index, name='mid_centroid')
        low_centroids = pd.Series(np.nan, index=volatility.index, name='low_centroid')
        
        for i in range(len(volatility)):
            # 检查是否有足够的训练数据 (对应 bar_index >= training_data_period-1)
            if i < training_period - 1 or pd.isna(volatility.iloc[i]) or volatility.iloc[i] <= 0:
                continue
                
            # 获取训练数据窗口
            train_start = max(0, i - training_period + 1)
            train_window = volatility.iloc[train_start:i+1]
            
            # 计算初始质心 (对应Pine Script的upper/lower/high_volatility等计算)
            upper = train_window.max()  # ta.highest(volatility, training_data_period)
            lower = train_window.min()  # ta.lowest(volatility, training_data_period) 
            
            # 初始质心猜测 (对应Pine Script的百分位计算)
            high_vol_init = lower + (upper - lower) * self.high_vol_percentile
            mid_vol_init = lower + (upper - lower) * self.mid_vol_percentile  
            low_vol_init = lower + (upper - lower) * self.low_vol_percentile
            
            # K-Means迭代 (对应Pine Script的while循环)
            # 初始化质心数组 (对应amean, bmean, cmean)
            high_centroid = high_vol_init
            mid_centroid = mid_vol_init
            low_centroid = low_vol_init
            
            prev_high_centroid = None
            prev_mid_centroid = None
            prev_low_centroid = None
            
            max_iterations = 100  # 防止无限循环
            iteration = 0
            
            # while循环条件检查 (对应Pine Script的复杂while条件)
            while (iteration < max_iterations and 
                   (prev_high_centroid != high_centroid or 
                    prev_mid_centroid != mid_centroid or
                    prev_low_centroid != low_centroid)):
                
                prev_high_centroid = high_centroid
                prev_mid_centroid = mid_centroid
                prev_low_centroid = low_centroid
                
                # 分配点到最近的质心 (对应Pine Script的for循环和距离计算)
                high_cluster = []  # 对应hv数组
                mid_cluster = []   # 对应mv数组  
                low_cluster = []   # 对应lv数组
                
                # 遍历训练窗口 (对应 for i = training_data_period-1 to 0)
                for j in range(len(train_window)):
                    vol_val = train_window.iloc[j]
                    
                    # 计算到各质心的距离 (对应_1, _2, _3计算)
                    dist_high = abs(vol_val - high_centroid)
                    dist_mid = abs(vol_val - mid_centroid) 
                    dist_low = abs(vol_val - low_centroid)
                    
                    # 分配到最近的质心 (对应Pine Script的if条件)
                    if dist_high < dist_mid and dist_high < dist_low:
                        high_cluster.append(vol_val)  # 对应hv.unshift(volatility[i])
                    elif dist_mid < dist_high and dist_mid < dist_low:
                        mid_cluster.append(vol_val)   # 对应mv.unshift(volatility[i])
                    elif dist_low < dist_high and dist_low < dist_mid:
                        low_cluster.append(vol_val)   # 对应lv.unshift(volatility[i])
                
                # 更新质心 (对应amean.unshift(hv.avg())等)
                high_centroid = np.mean(high_cluster) if high_cluster else high_centroid
                mid_centroid = np.mean(mid_cluster) if mid_cluster else mid_centroid
                low_centroid = np.mean(low_cluster) if low_cluster else low_centroid
                
                iteration += 1
            
            # 存储最终质心
            high_centroids.iloc[i] = high_centroid
            mid_centroids.iloc[i] = mid_centroid  
            low_centroids.iloc[i] = low_centroid
            
            # 分类当前点 (对应Pine Script的最终距离计算和cluster分配)
            current_vol = volatility.iloc[i]
            
            # 计算到各质心的距离 (对应vdist_a, vdist_b, vdist_c)
            dist_to_high = abs(current_vol - high_centroid)
            dist_to_mid = abs(current_vol - mid_centroid)
            dist_to_low = abs(current_vol - low_centroid)
            
            # 找到最小距离对应的集群 (对应distances.indexof(distances.min()))
            distances = [dist_to_high, dist_to_mid, dist_to_low]
            centroids = [high_centroid, mid_centroid, low_centroid]
            
            min_dist_idx = distances.index(min(distances))
            cluster_assignments.iloc[i] = min_dist_idx  # 0=high, 1=mid, 2=low
            
            # 分配对应的质心值 (对应assigned_centroid)
            assigned_centroids.iloc[i] = centroids[min_dist_idx]
        
        return {
            'cluster': cluster_assignments,
            'assigned_centroid': assigned_centroids,
            'high_centroid': high_centroids,
            'mid_centroid': mid_centroids,
            'low_centroid': low_centroids
        }
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算ML Adaptive SuperTrend指标 - 主函数
        
        Args:
            data: 包含OHLC数据的DataFrame
            
        Returns:
            包含所有计算结果的DataFrame
        """
        print("🔄 开始计算ML Adaptive SuperTrend...")
        
        # 输入数据验证
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            raise ValueError(f"缺少必要的数据列: {missing_cols}")
        
        result_data = data.copy()
        
        # 1. 计算ATR波动率 (对应Pine Script: volatility = ta.atr(atr_len))
        print("📊 计算ATR波动率...")
        volatility = ta.atr(high=data['high'], low=data['low'], 
                           close=data['close'], length=self.atr_len)
        result_data['volatility'] = volatility
        
        # 2. K-Means波动率聚类
        print("🤖 执行K-Means波动率聚类...")
        clustering_results = self.k_means_volatility_clustering(volatility, self.training_data_period)
        
        for key, series in clustering_results.items():
            result_data[key] = series
        
        # 3. 计算SuperTrend (对应Pine Script: [ST, dir] = pine_supertrend(fact, assigned_centroid))
        print("📈 计算自适应SuperTrend...")
        supertrend, direction = self.pine_supertrend(
            data['high'], data['low'], data['close'],
            self.factor, clustering_results['assigned_centroid']
        )
        
        result_data['supertrend'] = supertrend
        result_data['direction'] = direction
        
        # 4. 计算信号 (趋势变化)
        result_data['trend_signal'] = 0
        result_data.loc[result_data['direction'] == 1, 'trend_signal'] = 1   # 上升趋势
        result_data.loc[result_data['direction'] == -1, 'trend_signal'] = -1 # 下降趋势
        
        # 5. 检测趋势变化点 (对应Pine Script的crossover/crossunder)
        result_data['signal_change'] = result_data['trend_signal'].diff()
        
        print("✅ ML Adaptive SuperTrend计算完成")
        
        return result_data

def demo_mlas_calculation():
    """
    演示MLAS计算功能
    """
    import yfinance as yf
    
    print("🎯 ML Adaptive SuperTrend (MLAS) 演示")
    print("=" * 50)
    
    # 获取测试数据
    print("📊 获取QQQ测试数据...")
    ticker = yf.Ticker('QQQ')
    data = ticker.history(start='2023-01-01', end='2025-01-01', interval='1d')
    
    # 重命名列
    data = data.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low', 
        'Close': 'close', 'Volume': 'volume'
    })
    
    print(f"✅ 获取{len(data)}条数据 ({data.index[0].date()} 到 {data.index[-1].date()})")
    
    # 创建MLAS实例 (使用Pine Script默认参数)
    mlas = MLAdaptiveSuperTrend(
        atr_len=10,
        factor=3.0,
        training_data_period=100,
        high_vol_percentile=0.75,
        mid_vol_percentile=0.5,
        low_vol_percentile=0.25
    )
    
    # 计算指标
    results = mlas.calculate(data)
    
    # 性能统计
    print("\n📊 计算结果统计:")
    print(f"SuperTrend有效数据: {results['supertrend'].count()} / {len(results)}")
    print(f"聚类有效数据: {results['cluster'].count()} / {len(results)}")
    
    # 聚类分布
    cluster_counts = results['cluster'].value_counts().sort_index()
    cluster_labels = {0: '高波动率', 1: '中波动率', 2: '低波动率'}
    print("\n🎯 波动率聚类分布:")
    for cluster_id, count in cluster_counts.items():
        if not pd.isna(cluster_id):
            label = cluster_labels.get(int(cluster_id), f'未知({int(cluster_id)})')
            percentage = count / results['cluster'].count() * 100
            print(f"  {label}: {count}次 ({percentage:.1f}%)")
    
    # 趋势统计
    trend_counts = results['trend_signal'].value_counts()
    print("\n📈 趋势信号统计:")
    if 1 in trend_counts:
        print(f"  上升趋势: {trend_counts[1]}天 ({trend_counts[1]/len(results)*100:.1f}%)")
    if -1 in trend_counts:
        print(f"  下降趋势: {trend_counts[-1]}天 ({trend_counts[-1]/len(results)*100:.1f}%)")
    
    # 信号变化
    signal_changes = results[results['signal_change'] != 0]
    buy_signals = results[results['signal_change'] == 2]  # -1变为1
    sell_signals = results[results['signal_change'] == -2] # 1变为-1
    
    print(f"\n📡 交易信号:")
    print(f"  买入信号: {len(buy_signals)}次")
    print(f"  卖出信号: {len(sell_signals)}次")
    
    if len(buy_signals) > 0:
        print(f"  最近买入: {buy_signals.index[-1].date()}")
    if len(sell_signals) > 0:
        print(f"  最近卖出: {sell_signals.index[-1].date()}")
    
    # 当前状态
    print(f"\n📋 当前状态:")
    latest = results.iloc[-1]
    print(f"  当前价格: ${latest['close']:.2f}")
    if not pd.isna(latest['supertrend']):
        print(f"  SuperTrend: ${latest['supertrend']:.2f}")
    if not pd.isna(latest['cluster']):
        cluster_name = cluster_labels.get(int(latest['cluster']), '未知')
        print(f"  波动率级别: {cluster_name}")
    if not pd.isna(latest['trend_signal']):
        trend_name = '上升' if latest['trend_signal'] == 1 else '下降' if latest['trend_signal'] == -1 else '中性'
        print(f"  当前趋势: {trend_name}")
    
    # 保存结果
    output_file = 'mlas_results.csv'
    save_columns = ['close', 'volatility', 'supertrend', 'direction', 'cluster', 
                   'assigned_centroid', 'trend_signal', 'signal_change']
    results[save_columns].to_csv(output_file)
    print(f"\n💾 结果已保存到: {output_file}")
    
    return results

if __name__ == "__main__":
    # 运行演示
    results = demo_mlas_calculation()
    print("\n🎉 MLAS算法测试完成!")