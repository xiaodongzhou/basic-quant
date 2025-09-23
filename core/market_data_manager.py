#!/usr/bin/env python3
"""
MarketDataManager - 行情数据管理模块
实现行情数据订阅、处理和技术指标计算功能

Milestone 1.3 核心模块
"""

import threading
import time
import random
from datetime import datetime, timedelta
from collections import deque, defaultdict
from typing import Dict, List, Optional, Callable, Set, Deque
from dataclasses import dataclass

from .data_types import (
    TickData, BarData, ContractData, SubscribeRequest, 
    MarketDataEvent, IndicatorValue, DataStatistics,
    Exchange, Interval, create_tick_data, create_bar_data
)
from .connection_manager import ConnectionManager

@dataclass
class SubscriptionInfo:
    """订阅信息"""
    symbol: str
    exchange: Exchange
    subscribed_time: datetime
    callback_count: int = 0
    last_update: Optional[datetime] = None

class MarketDataManager:
    """
    行情数据管理器
    负责行情数据的订阅、接收、处理和分发
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        """
        初始化行情数据管理器
        
        Args:
            connection_manager: 连接管理器实例
        """
        self.connection_manager = connection_manager
        
        # 订阅管理
        self.subscriptions: Dict[str, SubscriptionInfo] = {}
        self.subscribed_symbols: Set[str] = set()
        
        # 数据缓存
        self.tick_data: Dict[str, Deque[TickData]] = defaultdict(lambda: deque(maxlen=1000))
        self.bar_data: Dict[str, Dict[str, Deque[BarData]]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=500))
        )
        
        # 回调管理
        self.tick_callbacks: List[Callable] = []
        self.bar_callbacks: List[Callable] = []
        
        # 数据统计
        self.statistics: Dict[str, DataStatistics] = {}
        
        # 技术指标缓存
        self.indicators: Dict[str, Dict[str, IndicatorValue]] = defaultdict(dict)
        
        # 模拟数据生成
        self.simulation_mode = connection_manager.simulation_mode
        self.simulation_threads: Dict[str, threading.Thread] = {}
        self.simulation_running: Dict[str, bool] = {}
        
        # 状态管理
        self.active = False
        self.data_lock = threading.Lock()
        
        print(f"✅ MarketDataManager初始化完成 (模拟模式: {self.simulation_mode})")
    
    def start(self):
        """启动行情数据管理器"""
        if not self.connection_manager.is_connected():
            raise RuntimeError("连接管理器未连接，无法启动行情数据管理器")
        
        self.active = True
        print("🚀 MarketDataManager启动成功")
    
    def stop(self):
        """停止行情数据管理器"""
        self.active = False
        
        # 停止所有模拟数据线程
        for symbol in list(self.simulation_running.keys()):
            self._stop_simulation(symbol)
        
        print("🛑 MarketDataManager已停止")
    
    def subscribe_market_data(self, symbols: List[str], exchange: Exchange = Exchange.SHFE) -> bool:
        """
        订阅行情数据
        
        Args:
            symbols: 合约代码列表
            exchange: 交易所
            
        Returns:
            bool: 订阅是否成功
        """
        if not self.active:
            print("❌ MarketDataManager未启动")
            return False
        
        success_count = 0
        
        for symbol in symbols:
            try:
                if symbol in self.subscribed_symbols:
                    print(f"⚠️ {symbol} 已订阅，跳过")
                    continue
                
                # 创建订阅信息
                subscription = SubscriptionInfo(
                    symbol=symbol,
                    exchange=exchange,
                    subscribed_time=datetime.now()
                )
                
                self.subscriptions[symbol] = subscription
                self.subscribed_symbols.add(symbol)
                
                # 初始化数据统计
                self.statistics[symbol] = DataStatistics(symbol=symbol)
                
                # 如果是模拟模式，启动模拟数据生成
                if self.simulation_mode:
                    self._start_simulation(symbol)
                else:
                    # TODO: 实际订阅VN.PY行情
                    pass
                
                success_count += 1
                print(f"✅ 订阅成功: {symbol}")
                
            except Exception as e:
                print(f"❌ 订阅失败 {symbol}: {e}")
        
        print(f"📊 订阅完成: {success_count}/{len(symbols)} 成功")
        return success_count == len(symbols)
    
    def unsubscribe_market_data(self, symbols: List[str]) -> bool:
        """
        取消订阅行情数据
        
        Args:
            symbols: 合约代码列表
            
        Returns:
            bool: 取消订阅是否成功
        """
        success_count = 0
        
        for symbol in symbols:
            try:
                if symbol not in self.subscribed_symbols:
                    print(f"⚠️ {symbol} 未订阅，跳过")
                    continue
                
                # 停止模拟数据生成
                if self.simulation_mode and symbol in self.simulation_running:
                    self._stop_simulation(symbol)
                
                # 移除订阅信息
                self.subscriptions.pop(symbol, None)
                self.subscribed_symbols.discard(symbol)
                
                success_count += 1
                print(f"✅ 取消订阅: {symbol}")
                
            except Exception as e:
                print(f"❌ 取消订阅失败 {symbol}: {e}")
        
        print(f"📊 取消订阅完成: {success_count}/{len(symbols)} 成功")
        return success_count == len(symbols)
    
    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """
        获取最新tick数据
        
        Args:
            symbol: 合约代码
            
        Returns:
            TickData: 最新tick数据，如果没有则返回None
        """
        with self.data_lock:
            tick_queue = self.tick_data.get(symbol)
            if tick_queue and len(tick_queue) > 0:
                return tick_queue[-1]
            return None
    
    def get_latest_bar(self, symbol: str, interval: str = "1m") -> Optional[BarData]:
        """
        获取最新bar数据
        
        Args:
            symbol: 合约代码
            interval: K线周期
            
        Returns:
            BarData: 最新bar数据，如果没有则返回None
        """
        with self.data_lock:
            symbol_bars = self.bar_data.get(symbol, {})
            bar_queue = symbol_bars.get(interval)
            if bar_queue and len(bar_queue) > 0:
                return bar_queue[-1]
            return None
    
    def get_recent_ticks(self, symbol: str, count: int = 10) -> List[TickData]:
        """
        获取最近的tick数据
        
        Args:
            symbol: 合约代码
            count: 数据数量
            
        Returns:
            List[TickData]: tick数据列表
        """
        with self.data_lock:
            tick_queue = self.tick_data.get(symbol, deque())
            return list(tick_queue)[-count:]
    
    def get_recent_bars(self, symbol: str, interval: str = "1m", count: int = 10) -> List[BarData]:
        """
        获取最近的bar数据
        
        Args:
            symbol: 合约代码
            interval: K线周期
            count: 数据数量
            
        Returns:
            List[BarData]: bar数据列表
        """
        with self.data_lock:
            symbol_bars = self.bar_data.get(symbol, {})
            bar_queue = symbol_bars.get(interval, deque())
            return list(bar_queue)[-count:]
    
    def calculate_ma(self, symbol: str, period: int, interval: str = "1m") -> Optional[float]:
        """
        计算移动平均线
        
        Args:
            symbol: 合约代码
            period: 周期
            interval: K线周期
            
        Returns:
            float: MA值，如果数据不足则返回None
        """
        bars = self.get_recent_bars(symbol, interval, period)
        
        if len(bars) < period:
            return None
        
        prices = [bar.close_price for bar in bars[-period:]]
        ma_value = sum(prices) / len(prices)
        
        # 缓存指标值
        indicator_key = f"MA{period}_{interval}"
        self.indicators[symbol][indicator_key] = IndicatorValue(
            name=indicator_key,
            value=ma_value,
            timestamp=datetime.now(),
            symbol=symbol,
            params={"period": period, "interval": interval}
        )
        
        return ma_value
    
    def calculate_rsi(self, symbol: str, period: int = 14, interval: str = "1m") -> Optional[float]:
        """
        计算RSI指标
        
        Args:
            symbol: 合约代码
            period: 周期
            interval: K线周期
            
        Returns:
            float: RSI值，如果数据不足则返回None
        """
        bars = self.get_recent_bars(symbol, interval, period + 1)
        
        if len(bars) < period + 1:
            return None
        
        # 计算价格变化
        price_changes = []
        for i in range(1, len(bars)):
            change = bars[i].close_price - bars[i-1].close_price
            price_changes.append(change)
        
        # 计算平均上涨和下跌
        gains = [change if change > 0 else 0 for change in price_changes[-period:]]
        losses = [-change if change < 0 else 0 for change in price_changes[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            rsi_value = 100
        else:
            rs = avg_gain / avg_loss
            rsi_value = 100 - (100 / (1 + rs))
        
        # 缓存指标值
        indicator_key = f"RSI{period}_{interval}"
        self.indicators[symbol][indicator_key] = IndicatorValue(
            name=indicator_key,
            value=rsi_value,
            timestamp=datetime.now(),
            symbol=symbol,
            params={"period": period, "interval": interval}
        )
        
        return rsi_value
    
    def calculate_bollinger_bands(self, symbol: str, period: int = 20, std_dev: float = 2.0, 
                                interval: str = "1m") -> Optional[Dict[str, float]]:
        """
        计算布林带指标
        
        Args:
            symbol: 合约代码
            period: 周期
            std_dev: 标准差倍数
            interval: K线周期
            
        Returns:
            Dict: 包含upper, middle, lower的字典，如果数据不足则返回None
        """
        bars = self.get_recent_bars(symbol, interval, period)
        
        if len(bars) < period:
            return None
        
        prices = [bar.close_price for bar in bars[-period:]]
        
        # 计算中线 (MA)
        middle = sum(prices) / len(prices)
        
        # 计算标准差
        variance = sum((price - middle) ** 2 for price in prices) / len(prices)
        std = variance ** 0.5
        
        # 计算上下轨
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        result = {
            "upper": upper,
            "middle": middle,
            "lower": lower
        }
        
        # 缓存指标值
        for band, value in result.items():
            indicator_key = f"BOLL_{band}_{period}_{interval}"
            self.indicators[symbol][indicator_key] = IndicatorValue(
                name=indicator_key,
                value=value,
                timestamp=datetime.now(),
                symbol=symbol,
                params={"period": period, "std_dev": std_dev, "interval": interval}
            )
        
        return result
    
    def register_tick_callback(self, callback: Callable[[TickData], None]):
        """
        注册tick数据回调函数
        
        Args:
            callback: 回调函数
        """
        self.tick_callbacks.append(callback)
        print(f"✅ Tick回调注册成功: {callback.__name__}")
    
    def register_bar_callback(self, callback: Callable[[BarData], None]):
        """
        注册bar数据回调函数
        
        Args:
            callback: 回调函数
        """
        self.bar_callbacks.append(callback)
        print(f"✅ Bar回调注册成功: {callback.__name__}")
    
    def get_subscription_info(self) -> Dict[str, SubscriptionInfo]:
        """获取订阅信息"""
        return self.subscriptions.copy()
    
    def get_data_statistics(self, symbol: str = None) -> Dict[str, DataStatistics]:
        """
        获取数据统计信息
        
        Args:
            symbol: 合约代码，如果为None则返回所有
            
        Returns:
            Dict: 数据统计信息
        """
        if symbol:
            return {symbol: self.statistics.get(symbol, DataStatistics(symbol))}
        return self.statistics.copy()
    
    def get_indicators(self, symbol: str) -> Dict[str, IndicatorValue]:
        """
        获取指标值
        
        Args:
            symbol: 合约代码
            
        Returns:
            Dict: 指标值字典
        """
        return self.indicators.get(symbol, {}).copy()
    
    def _start_simulation(self, symbol: str):
        """启动模拟数据生成"""
        if symbol in self.simulation_running:
            return
        
        self.simulation_running[symbol] = True
        
        def generate_simulation_data():
            """模拟数据生成线程"""
            base_price = 3500.0  # 基础价格
            current_price = base_price
            tick_count = 0
            
            print(f"🎯 开始生成 {symbol} 模拟数据")
            
            while self.simulation_running.get(symbol, False):
                try:
                    # 生成tick数据
                    price_change = random.uniform(-5, 5)  # 价格变动
                    current_price += price_change
                    current_price = max(current_price, base_price * 0.9)  # 最低价限制
                    current_price = min(current_price, base_price * 1.1)  # 最高价限制
                    
                    volume = random.randint(50, 200)
                    tick = create_tick_data(symbol, current_price, volume)
                    
                    # 存储tick数据
                    with self.data_lock:
                        self.tick_data[symbol].append(tick)
                        
                        # 更新统计
                        stats = self.statistics[symbol]
                        stats.total_ticks += 1
                        stats.last_time = tick.datetime
                        if stats.first_time is None:
                            stats.first_time = tick.datetime
                    
                    # 触发回调
                    self._trigger_tick_callbacks(tick)
                    
                    # 每10个tick生成一个bar
                    tick_count += 1
                    if tick_count >= 10:
                        self._generate_bar_from_ticks(symbol)
                        tick_count = 0
                    
                    time.sleep(0.5)  # 500ms间隔
                    
                except Exception as e:
                    print(f"❌ 模拟数据生成错误 {symbol}: {e}")
                    break
            
            print(f"🏁 停止生成 {symbol} 模拟数据")
        
        thread = threading.Thread(target=generate_simulation_data, daemon=True)
        thread.start()
        self.simulation_threads[symbol] = thread
    
    def _stop_simulation(self, symbol: str):
        """停止模拟数据生成"""
        if symbol in self.simulation_running:
            self.simulation_running[symbol] = False
            del self.simulation_running[symbol]
        
        if symbol in self.simulation_threads:
            del self.simulation_threads[symbol]
    
    def _generate_bar_from_ticks(self, symbol: str):
        """从tick数据生成bar数据"""
        with self.data_lock:
            ticks = list(self.tick_data[symbol])[-10:]  # 取最后10个tick
            
            if len(ticks) < 5:
                return
            
            # 计算OHLC
            open_price = ticks[0].last_price
            close_price = ticks[-1].last_price
            high_price = max(tick.last_price for tick in ticks)
            low_price = min(tick.last_price for tick in ticks)
            total_volume = sum(tick.volume for tick in ticks)
            
            # 创建bar数据
            bar = create_bar_data(
                symbol=symbol,
                open_p=open_price,
                high_p=high_price,
                low_p=low_price,
                close_p=close_price,
                volume=total_volume,
                interval=Interval.MINUTE
            )
            
            # 存储bar数据
            self.bar_data[symbol]["1m"].append(bar)
            
            # 更新统计
            stats = self.statistics[symbol]
            stats.total_bars += 1
        
        # 触发回调
        self._trigger_bar_callbacks(bar)
    
    def _trigger_tick_callbacks(self, tick: TickData):
        """触发tick回调"""
        for callback in self.tick_callbacks:
            try:
                callback(tick)
                
                # 更新订阅统计
                if tick.symbol in self.subscriptions:
                    self.subscriptions[tick.symbol].callback_count += 1
                    self.subscriptions[tick.symbol].last_update = tick.datetime
                    
            except Exception as e:
                print(f"⚠️ Tick回调执行失败: {e}")
    
    def _trigger_bar_callbacks(self, bar: BarData):
        """触发bar回调"""
        for callback in self.bar_callbacks:
            try:
                callback(bar)
            except Exception as e:
                print(f"⚠️ Bar回调执行失败: {e}")


def create_market_data_manager(connection_manager: ConnectionManager) -> MarketDataManager:
    """
    创建行情数据管理器的便捷函数
    
    Args:
        connection_manager: 连接管理器实例
        
    Returns:
        MarketDataManager: 行情数据管理器实例
    """
    return MarketDataManager(connection_manager)


if __name__ == "__main__":
    """模块测试代码"""
    print("=" * 50)
    print("MarketDataManager 模块测试")
    print("=" * 50)
    
    # 创建连接管理器和行情数据管理器
    from .connection_manager import create_connection_manager
    
    cm = create_connection_manager()
    cm.connect_gateway()
    
    mdm = create_market_data_manager(cm)
    mdm.start()
    
    # 测试订阅
    print("\n🧪 测试订阅功能...")
    success = mdm.subscribe_market_data(["rb2405", "i2405"])
    print(f"订阅结果: {success}")
    
    # 等待数据生成
    print("\n⏰ 等待数据生成...")
    time.sleep(3)
    
    # 检查数据
    print("\n📊 检查数据:")
    for symbol in ["rb2405", "i2405"]:
        tick = mdm.get_latest_tick(symbol)
        if tick:
            print(f"  {symbol} 最新价格: {tick.last_price}")
        
        bar = mdm.get_latest_bar(symbol)
        if bar:
            print(f"  {symbol} 最新K线: {bar.close_price}")
    
    # 测试技术指标
    print("\n📈 测试技术指标...")
    ma5 = mdm.calculate_ma("rb2405", 5)
    if ma5:
        print(f"  rb2405 MA5: {ma5:.2f}")
    
    # 停止测试
    mdm.stop()
    cm.disconnect_gateway()
    
    print("\n✅ MarketDataManager 测试完成")