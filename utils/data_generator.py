"""
数据生成工具
用于生成模拟的价格数据进行测试
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class DataGenerator:
    """数据生成器"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            np.random.seed(seed)
        
    def generate_random_walk(self, 
                           days: int = 100,
                           start_price: float = 100.0,
                           volatility: float = 0.02,
                           drift: float = 0.0001,
                           start_date: datetime = None) -> List[Dict]:
        """生成随机游走价格数据"""
        
        if start_date is None:
            start_date = datetime(2023, 1, 1)
        
        data = []
        current_price = start_price
        
        for i in range(days):
            # 几何布朗运动
            random_change = np.random.normal(drift, volatility)
            current_price *= (1 + random_change)
            
            # 生成OHLC数据
            intraday_volatility = volatility * 0.5
            high = current_price * (1 + abs(np.random.normal(0, intraday_volatility)))
            low = current_price * (1 - abs(np.random.normal(0, intraday_volatility)))
            open_price = current_price * (1 + np.random.normal(0, intraday_volatility * 0.3))
            
            # 确保OHLC逻辑正确
            high = max(high, current_price, open_price, low)
            low = min(low, current_price, open_price, high)
            
            bar = {
                'datetime': start_date + timedelta(days=i),
                'open_price': open_price,
                'high_price': high,
                'low_price': low,
                'close_price': current_price,
                'volume': np.random.randint(100, 2000)
            }
            
            data.append(bar)
        
        return data
    
    def generate_trending_data(self,
                             days: int = 100,
                             start_price: float = 100.0,
                             trend_strength: float = 0.01,
                             volatility: float = 0.02,
                             start_date: datetime = None) -> List[Dict]:
        """生成带趋势的价格数据"""
        
        if start_date is None:
            start_date = datetime(2023, 1, 1)
        
        data = []
        current_price = start_price
        
        for i in range(days):
            # 趋势 + 随机波动
            trend_change = trend_strength
            random_change = np.random.normal(0, volatility)
            total_change = trend_change + random_change
            
            current_price *= (1 + total_change)
            
            # 生成OHLC数据
            intraday_vol = volatility * 0.6
            high = current_price * (1 + abs(np.random.normal(0, intraday_vol)))
            low = current_price * (1 - abs(np.random.normal(0, intraday_vol)))
            open_price = current_price * (1 + np.random.normal(0, intraday_vol * 0.4))
            
            # 确保OHLC逻辑正确
            high = max(high, current_price, open_price)
            low = min(low, current_price, open_price)
            
            bar = {
                'datetime': start_date + timedelta(days=i),
                'open_price': open_price,
                'high_price': high,
                'low_price': low,
                'close_price': current_price,
                'volume': np.random.randint(500, 3000)
            }
            
            data.append(bar)
        
        return data
    
    def generate_oscillating_data(self,
                                days: int = 100,
                                start_price: float = 100.0,
                                oscillation_period: int = 20,
                                oscillation_amplitude: float = 0.1,
                                volatility: float = 0.01,
                                start_date: datetime = None) -> List[Dict]:
        """生成震荡价格数据"""
        
        if start_date is None:
            start_date = datetime(2023, 1, 1)
        
        data = []
        base_price = start_price
        
        for i in range(days):
            # 正弦波震荡 + 随机噪音
            oscillation = oscillation_amplitude * np.sin(2 * np.pi * i / oscillation_period)
            random_change = np.random.normal(0, volatility)
            
            current_price = base_price * (1 + oscillation + random_change)
            
            # 生成OHLC数据
            intraday_vol = volatility * 0.8
            high = current_price * (1 + abs(np.random.normal(0, intraday_vol)))
            low = current_price * (1 - abs(np.random.normal(0, intraday_vol)))
            open_price = current_price * (1 + np.random.normal(0, intraday_vol * 0.5))
            
            # 确保OHLC逻辑正确
            high = max(high, current_price, open_price)
            low = min(low, current_price, open_price)
            
            bar = {
                'datetime': start_date + timedelta(days=i),
                'open_price': open_price,
                'high_price': high,
                'low_price': low,
                'close_price': current_price,
                'volume': np.random.randint(200, 1500)
            }
            
            data.append(bar)
        
        return data
    
    def generate_mixed_scenario(self,
                              days: int = 300,
                              start_price: float = 100.0,
                              start_date: datetime = None) -> List[Dict]:
        """生成混合场景数据（趋势+震荡+随机）"""
        
        if start_date is None:
            start_date = datetime(2023, 1, 1)
        
        all_data = []
        current_date = start_date
        current_price = start_price
        
        # 第一阶段：上涨趋势 (1/3时间)
        trend_days = days // 3
        trend_data = self.generate_trending_data(
            days=trend_days,
            start_price=current_price,
            trend_strength=0.008,
            start_date=current_date
        )
        all_data.extend(trend_data)
        current_price = trend_data[-1]['close_price']
        current_date += timedelta(days=trend_days)
        
        # 第二阶段：震荡整理 (1/3时间)
        oscillation_days = days // 3
        oscillation_data = self.generate_oscillating_data(
            days=oscillation_days,
            start_price=current_price,
            oscillation_period=25,
            oscillation_amplitude=0.08,
            start_date=current_date
        )
        all_data.extend(oscillation_data)
        current_price = oscillation_data[-1]['close_price']
        current_date += timedelta(days=oscillation_days)
        
        # 第三阶段：随机游走 (剩余时间)
        remaining_days = days - trend_days - oscillation_days
        random_data = self.generate_random_walk(
            days=remaining_days,
            start_price=current_price,
            volatility=0.025,
            start_date=current_date
        )
        all_data.extend(random_data)
        
        return all_data
    
    def to_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """将数据转换为DataFrame"""
        df = pd.DataFrame(data)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        return df
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """保存数据到CSV文件"""
        df = self.to_dataframe(data)
        df.to_csv(filename)
        print(f"数据已保存到 {filename}")


# 便捷函数
def generate_test_data(scenario: str = "mixed", days: int = 200, **kwargs) -> List[Dict]:
    """生成测试数据的便捷函数"""
    generator = DataGenerator()
    
    if scenario == "random":
        return generator.generate_random_walk(days=days, **kwargs)
    elif scenario == "trend":
        return generator.generate_trending_data(days=days, **kwargs)
    elif scenario == "oscillation":
        return generator.generate_oscillating_data(days=days, **kwargs)
    elif scenario == "mixed":
        return generator.generate_mixed_scenario(days=days, **kwargs)
    else:
        raise ValueError(f"未知场景类型: {scenario}")


if __name__ == "__main__":
    # 测试数据生成器
    generator = DataGenerator(seed=42)
    
    # 生成不同类型的数据
    scenarios = ["random", "trend", "oscillation", "mixed"]
    
    for scenario in scenarios:
        print(f"生成{scenario}数据...")
        data = generate_test_data(scenario, days=100, start_price=16500)
        
        print(f"数据长度: {len(data)}")
        print(f"起始价格: {data[0]['close_price']:.2f}")
        print(f"结束价格: {data[-1]['close_price']:.2f}")
        print(f"价格变化: {(data[-1]['close_price'] / data[0]['close_price'] - 1) * 100:.2f}%")
        print("-" * 40)