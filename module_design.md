# 极简期货量化交易系统 - 模块设计

## 🛠️ 模块实现方案设计

### 1. 开发优先级规划

#### 第一阶段：核心基础（Week 1）
1. **ConnectionManager** - 连接管理模块
2. **MarketDataManager** - 行情数据模块  
3. **基础VN.PY集成** - 环境搭建

#### 第二阶段：交易核心（Week 2）
4. **TradingEngine** - 交易执行模块
5. **StrategyEngine** - 策略引擎模块
6. **简单策略实现** - MA策略

#### 第三阶段：管理监控（Week 3）
7. **AccountManager** - 账户管理模块
8. **MonitoringDisplay** - 监控界面
9. **ContractManager** - 合约管理模块

## 📋 详细实现方案

### 模块1: ConnectionManager (连接管理)

#### 1.1 实现要点
```python
# 文件: connection_manager.py
import logging
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.gateway.ctp import CtpGateway

class ConnectionManager:
    def __init__(self, config: dict):
        """
        初始化连接管理器
        config: {
            "gateway_name": "CTP",
            "settings": {
                "用户名": "simulation_user",
                "密码": "simulation_pass",
                "经纪商代码": "9999",
                "交易服务器": "tcp://180.168.146.187:10130",
                "行情服务器": "tcp://180.168.146.187:10131"
            }
        }
        """
        self.config = config
        self.event_engine = None
        self.main_engine = None
        self.gateway_name = config["gateway_name"]
        self.connected = False
        
    def connect_gateway(self) -> bool:
        """连接网关实现"""
        try:
            # 1. 初始化事件引擎
            self.event_engine = EventEngine()
            
            # 2. 初始化主引擎
            self.main_engine = MainEngine(self.event_engine)
            
            # 3. 添加CTP网关
            self.main_engine.add_gateway(CtpGateway)
            
            # 4. 连接网关
            self.main_engine.connect(self.config["settings"], self.gateway_name)
            
            # 5. 等待连接确认 (最多30秒)
            import time
            for i in range(30):
                time.sleep(1)
                if self._check_connection_status():
                    self.connected = True
                    logging.info("网关连接成功")
                    return True
                    
            logging.error("网关连接超时")
            return False
            
        except Exception as e:
            logging.error(f"连接失败: {e}")
            return False
```

#### 1.2 测试用例设计
```python
# 测试用例: test_connection_manager.py
class TestConnectionManager:
    
    def test_connect_simulation_success(self):
        """测试模拟环境连接成功"""
        config = {
            "gateway_name": "CTP",
            "settings": {...}  # 模拟环境配置
        }
        cm = ConnectionManager(config)
        result = cm.connect_gateway()
        assert result == True
        assert cm.connected == True
        
    def test_connect_invalid_config(self):
        """测试无效配置连接失败"""
        config = {"gateway_name": "INVALID"}
        cm = ConnectionManager(config)
        result = cm.connect_gateway()
        assert result == False
        
    def test_reconnection_mechanism(self):
        """测试重连机制"""
        # 模拟连接断开后的重连逻辑
        pass
```

### 模块2: MarketDataManager (行情数据)

#### 2.1 实现要点  
```python
# 文件: market_data_manager.py
import pandas as pd
from collections import deque
from typing import Dict, List, Callable
from dataclasses import dataclass

class MarketDataManager:
    def __init__(self, main_engine):
        self.main_engine = main_engine
        self.subscribed_symbols = set()
        self.tick_data = {}  # symbol -> deque of TickData
        self.bar_data = {}   # (symbol, interval) -> deque of BarData  
        self.callbacks = []  # 回调函数列表
        
    def subscribe_market_data(self, symbols: List[str]):
        """订阅行情数据"""
        for symbol in symbols:
            # 1. 通过VN.PY订阅行情
            contract = self._get_contract_info(symbol)
            if contract:
                self.main_engine.subscribe(contract, gateway_name="CTP")
                self.subscribed_symbols.add(symbol)
                
                # 2. 初始化数据缓存
                self.tick_data[symbol] = deque(maxlen=1000)  # 保留最近1000个tick
                self.bar_data[(symbol, "1m")] = deque(maxlen=500)  # 保留最近500根1分钟K线
                
        # 3. 注册事件处理
        self.main_engine.event_engine.register(EVENT_TICK, self._on_tick_event)
        
    def _on_tick_event(self, event):
        """处理tick事件"""
        tick = event.data
        symbol = tick.symbol
        
        # 1. 缓存tick数据
        if symbol in self.tick_data:
            self.tick_data[symbol].append(tick)
            
        # 2. 合成K线数据
        self._update_bar_data(tick)
        
        # 3. 触发回调
        for callback in self.callbacks:
            callback(tick)
            
    def calculate_ma(self, symbol: str, period: int) -> float:
        """计算移动平均线"""
        bars = self.bar_data.get((symbol, "1m"), deque())
        if len(bars) < period:
            return None
            
        prices = [bar.close_price for bar in list(bars)[-period:]]
        return sum(prices) / len(prices)
```

#### 2.2 测试用例设计
```python
class TestMarketDataManager:
    
    def test_subscribe_market_data(self):
        """测试行情订阅"""
        mdm = MarketDataManager(mock_main_engine)
        mdm.subscribe_market_data(["rb2405", "i2405"])
        assert "rb2405" in mdm.subscribed_symbols
        assert "i2405" in mdm.subscribed_symbols
        
    def test_calculate_ma(self):
        """测试移动平均计算"""
        # 准备测试数据
        test_bars = [BarData(close_price=i) for i in range(100, 110)]
        mdm.bar_data[("rb2405", "1m")] = deque(test_bars)
        
        # 测试MA计算
        ma5 = mdm.calculate_ma("rb2405", 5)
        expected = sum(range(105, 110)) / 5
        assert abs(ma5 - expected) < 0.01
        
    def test_tick_data_caching(self):
        """测试tick数据缓存"""
        # 模拟tick数据接收和缓存
        pass
```

### 模块3: TradingEngine (交易执行)

#### 3.1 实现要点
```python
# 文件: trading_engine.py
from typing import Dict, List
import uuid
from datetime import datetime

class TradingEngine:
    def __init__(self, main_engine):
        self.main_engine = main_engine
        self.orders = {}        # orderid -> OrderData
        self.trades = {}        # tradeid -> TradeData  
        self.positions = {}     # symbol -> PositionData
        
        # 注册事件处理
        self.main_engine.event_engine.register(EVENT_ORDER, self._on_order_event)
        self.main_engine.event_engine.register(EVENT_TRADE, self._on_trade_event)
        
    def send_order(self, signal: TradingSignal) -> str:
        """发送订单"""
        # 1. 生成订单ID
        orderid = f"order_{uuid.uuid4().hex[:8]}"
        
        # 2. 构建订单请求
        req = OrderRequest(
            symbol=signal.symbol,
            exchange=Exchange.SHFE,  # 根据品种确定交易所
            direction=Direction.LONG if signal.direction == "LONG" else Direction.SHORT,
            type=OrderType.MARKET if signal.price_type == "MARKET" else OrderType.LIMIT,
            volume=signal.volume,
            price=signal.price or 0,
            offset=Offset.OPEN if signal.action == "OPEN" else Offset.CLOSE,
            reference=f"{signal.strategy_name}_{orderid}"
        )
        
        # 3. 发送到交易所
        vt_orderid = self.main_engine.send_order(req, gateway_name="CTP")
        
        # 4. 记录订单信息
        order_data = OrderData(
            orderid=vt_orderid,
            symbol=signal.symbol,
            direction=signal.direction,
            volume=signal.volume,
            status="SUBMITTING",
            time=datetime.now()
        )
        self.orders[vt_orderid] = order_data
        
        return vt_orderid
        
    def _on_order_event(self, event):
        """处理订单状态更新"""
        order = event.data
        self.orders[order.vt_orderid] = order
        
    def _on_trade_event(self, event):
        """处理成交回报"""
        trade = event.data
        self.trades[trade.vt_tradeid] = trade
        
        # 更新持仓
        self._update_position(trade)
```

#### 3.2 测试用例设计
```python
class TestTradingEngine:
    
    def test_send_market_order(self):
        """测试市价单发送"""
        signal = TradingSignal(
            symbol="rb2405",
            direction="LONG",
            action="OPEN",
            volume=1,
            price_type="MARKET"
        )
        
        te = TradingEngine(mock_main_engine)
        orderid = te.send_order(signal)
        
        assert orderid is not None
        assert orderid in te.orders
        
    def test_position_update(self):
        """测试持仓更新"""
        # 模拟成交回报更新持仓
        pass
        
    def test_pnl_calculation(self):
        """测试盈亏计算"""
        # 测试持仓盈亏计算逻辑
        pass
```

### 模块4: StrategyEngine (策略引擎)

#### 4.1 实现要点
```python
# 文件: strategy_engine.py
from typing import Dict, Type
import importlib

class StrategyEngine:
    def __init__(self, market_data_manager, trading_engine):
        self.mdm = market_data_manager
        self.trading_engine = trading_engine
        self.strategies = {}  # strategy_name -> strategy_instance
        self.active_strategies = set()
        
        # 注册数据回调
        self.mdm.register_callback(self._on_tick_data)
        
    def load_strategy(self, strategy_class: Type[BaseStrategy], config: dict):
        """加载策略"""
        strategy_name = config["name"]
        symbols = config["symbols"]
        
        # 1. 创建策略实例
        strategy = strategy_class(strategy_name, symbols, **config.get("params", {}))
        
        # 2. 注册策略
        self.strategies[strategy_name] = strategy
        
        # 3. 策略初始化
        strategy.on_init()
        
        # 4. 设置信号回调
        strategy.set_signal_callback(self._on_strategy_signal)
        
    def start_strategy(self, strategy_name: str):
        """启动策略"""
        if strategy_name in self.strategies:
            strategy = self.strategies[strategy_name]
            strategy.on_start()
            self.active_strategies.add(strategy_name)
            
            # 订阅策略需要的行情数据
            self.mdm.subscribe_market_data(strategy.symbols)
            
    def _on_tick_data(self, tick: TickData):
        """处理tick数据"""
        for strategy_name in self.active_strategies:
            strategy = self.strategies[strategy_name]
            if tick.symbol in strategy.symbols:
                strategy.on_tick(tick)
                
    def _on_strategy_signal(self, signal: TradingSignal):
        """处理策略信号"""
        # 发送到交易引擎执行
        orderid = self.trading_engine.send_order(signal)
        logging.info(f"策略信号执行: {signal.strategy_name} -> {orderid}")
```

#### 4.2 MA策略完整实现
```python
# 文件: strategies/ma_strategy.py
class MAStrategy(BaseStrategy):
    def __init__(self, strategy_name: str, symbols: List[str], fast_ma: int = 10, slow_ma: int = 30):
        super().__init__(strategy_name, symbols)
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.positions = {symbol: 0 for symbol in symbols}  # 策略持仓记录
        self.last_signals = {symbol: None for symbol in symbols}  # 上次信号
        
    def on_bar(self, bar: BarData):
        """K线数据处理"""
        if not self.active:
            return
            
        symbol = bar.symbol
        
        # 1. 计算技术指标
        fast_ma = self.calculate_ma(symbol, self.fast_ma)
        slow_ma = self.calculate_ma(symbol, self.slow_ma)
        
        if fast_ma is None or slow_ma is None:
            return
            
        # 2. 判断信号
        current_signal = None
        if fast_ma > slow_ma:
            current_signal = "LONG"
        elif fast_ma < slow_ma:
            current_signal = "SHORT"
            
        # 3. 生成交易信号
        last_signal = self.last_signals[symbol]
        current_pos = self.positions[symbol]
        
        if current_signal != last_signal:
            # 信号发生变化
            if current_signal == "LONG" and current_pos <= 0:
                # 看多信号
                if current_pos < 0:
                    # 先平空仓
                    self.send_signal(self.create_signal(symbol, "SHORT", "CLOSE", abs(current_pos)))
                # 开多仓
                self.send_signal(self.create_signal(symbol, "LONG", "OPEN", 1))
                self.positions[symbol] = 1
                
            elif current_signal == "SHORT" and current_pos >= 0:
                # 看空信号  
                if current_pos > 0:
                    # 先平多仓
                    self.send_signal(self.create_signal(symbol, "LONG", "CLOSE", current_pos))
                # 开空仓
                self.send_signal(self.create_signal(symbol, "SHORT", "OPEN", 1))
                self.positions[symbol] = -1
                
            self.last_signals[symbol] = current_signal
```

#### 4.3 测试用例设计
```python
class TestStrategyEngine:
    
    def test_load_ma_strategy(self):
        """测试MA策略加载"""
        config = {
            "name": "ma_test",
            "symbols": ["rb2405"],
            "params": {"fast_ma": 5, "slow_ma": 20}
        }
        
        se = StrategyEngine(mock_mdm, mock_te)
        se.load_strategy(MAStrategy, config)
        
        assert "ma_test" in se.strategies
        
    def test_strategy_signal_generation(self):
        """测试策略信号生成"""
        # 准备测试数据: 创建金叉/死叉场景
        test_bars = create_crossover_test_data()
        
        # 测试策略响应
        strategy = MAStrategy("test", ["rb2405"], 5, 10)
        signals = []
        
        for bar in test_bars:
            signal = strategy.on_bar(bar)
            if signal:
                signals.append(signal)
                
        # 验证信号正确性
        assert len(signals) > 0
        assert signals[0].direction == "LONG"  # 金叉产生多头信号
```

### 模块5: MonitoringDisplay (监控显示)

#### 5.1 实现要点
```python
# 文件: monitoring_display.py
import pandas as pd
from IPython.display import display, clear_output
import time
import threading

class MonitoringDisplay:
    def __init__(self, trading_engine, account_manager, strategy_engine):
        self.te = trading_engine
        self.am = account_manager
        self.se = strategy_engine
        self.auto_refresh = False
        self.refresh_thread = None
        
    def show_positions_table(self):
        """显示持仓表格"""
        positions = self.te.get_all_positions()
        
        if not positions:
            print("当前无持仓")
            return
            
        # 构建表格数据
        data = []
        for pos in positions:
            current_price = self._get_current_price(pos.symbol)
            pnl = (current_price - pos.price) * pos.volume if current_price else 0
            
            data.append({
                "品种": self._get_symbol_name(pos.symbol),
                "合约": pos.symbol,
                "方向": "多头" if pos.direction == "LONG" else "空头",
                "数量": pos.volume,
                "开仓价": f"{pos.price:.2f}",
                "当前价": f"{current_price:.2f}" if current_price else "N/A",
                "浮动盈亏": f"{pnl:+.2f}"
            })
            
        df = pd.DataFrame(data)
        display(df)
        
    def show_account_summary(self):
        """显示账户摘要"""
        account = self.am.get_account_info()
        total_pnl = self.am.get_total_pnl()
        
        summary = {
            "账户余额": f"{account.balance:,.2f}",
            "可用资金": f"{account.available:,.2f}",
            "占用保证金": f"{account.margin:,.2f}",
            "浮动盈亏": f"{total_pnl:+,.2f}",
            "风险度": f"{account.risk_ratio:.2%}"
        }
        
        print("=== 账户信息 ===")
        for key, value in summary.items():
            print(f"{key}: {value}")
            
    def start_auto_refresh(self, interval: int = 3):
        """启动自动刷新"""
        self.auto_refresh = True
        
        def refresh_loop():
            while self.auto_refresh:
                clear_output(wait=True)
                print(f"=== 实时监控 - {time.strftime('%H:%M:%S')} ===")
                self.show_account_summary()
                print()
                self.show_positions_table()
                print()
                self.show_strategy_status()
                time.sleep(interval)
                
        self.refresh_thread = threading.Thread(target=refresh_loop)
        self.refresh_thread.start()
```

#### 5.2 测试用例设计
```python
class TestMonitoringDisplay:
    
    def test_positions_table_display(self):
        """测试持仓表格显示"""
        # 模拟持仓数据
        mock_positions = [
            PositionData(symbol="rb2405", direction="LONG", volume=2, price=3500.0),
            PositionData(symbol="i2405", direction="SHORT", volume=1, price=800.0)
        ]
        
        md = MonitoringDisplay(mock_te, mock_am, mock_se)
        # 测试表格生成和显示
        # (实际测试中需要验证输出格式)
        
    def test_account_summary_format(self):
        """测试账户摘要格式"""
        # 测试账户信息格式化显示
        pass
```

## 🧪 集成测试设计

### 端到端测试场景
```python
class TestFullSystemIntegration:
    
    def test_complete_trading_flow(self):
        """测试完整交易流程"""
        # 1. 初始化所有模块
        cm = ConnectionManager(test_config)
        assert cm.connect_gateway() == True
        
        mdm = MarketDataManager(cm.main_engine)
        te = TradingEngine(cm.main_engine)
        se = StrategyEngine(mdm, te)
        
        # 2. 加载策略
        strategy_config = {
            "name": "test_ma",
            "symbols": ["rb2405"],
            "params": {"fast_ma": 5, "slow_ma": 10}
        }
        se.load_strategy(MAStrategy, strategy_config)
        
        # 3. 启动策略
        se.start_strategy("test_ma")
        
        # 4. 模拟行情数据
        simulate_market_data(mdm, create_golden_cross_scenario())
        
        # 5. 验证交易执行
        time.sleep(5)  # 等待信号处理
        orders = te.get_all_orders()
        assert len(orders) > 0
        assert orders[0].direction == "LONG"
        
    def test_error_handling(self):
        """测试异常处理"""
        # 测试网络断线、无效合约等异常场景
        pass
```

## 📦 部署和打包设计

### Jupyter Notebook集成
```python
# 文件: quant_trading_system.py (主入口文件)
class QuantTradingSystem:
    """极简期货量化交易系统主类"""
    
    def __init__(self):
        self.connection_manager = None
        self.market_data_manager = None
        self.trading_engine = None
        self.strategy_engine = None
        self.account_manager = None
        self.monitoring_display = None
        self.initialized = False
        
    def initialize(self, config_file: str = "config.json"):
        """系统初始化"""
        # 1. 加载配置
        with open(config_file, 'r') as f:
            config = json.load(f)
            
        # 2. 初始化各模块
        self.connection_manager = ConnectionManager(config["gateway"])
        
        if self.connection_manager.connect_gateway():
            main_engine = self.connection_manager.main_engine
            
            self.market_data_manager = MarketDataManager(main_engine)
            self.trading_engine = TradingEngine(main_engine)
            self.strategy_engine = StrategyEngine(
                self.market_data_manager, 
                self.trading_engine
            )
            self.account_manager = AccountManager(main_engine)
            self.monitoring_display = MonitoringDisplay(
                self.trading_engine,
                self.account_manager, 
                self.strategy_engine
            )
            
            self.initialized = True
            print("✅ 系统初始化成功")
        else:
            print("❌ 系统初始化失败")
            
    def load_strategy(self, strategy_name: str, config: dict):
        """加载策略"""
        if not self.initialized:
            print("❌ 系统未初始化")
            return
            
        strategy_map = {
            "ma": MAStrategy,
            # 后续添加更多策略
        }
        
        if strategy_name in strategy_map:
            self.strategy_engine.load_strategy(strategy_map[strategy_name], config)
            print(f"✅ 策略 {config['name']} 加载成功")
        else:
            print(f"❌ 未知策略类型: {strategy_name}")
            
    def start_monitoring(self):
        """启动监控界面"""
        if self.initialized:
            self.monitoring_display.start_auto_refresh()
        else:
            print("❌ 系统未初始化")
```

### Jupyter使用示例
```python
# 在Jupyter Notebook中的使用方式
# Cell 1: 导入和初始化
from quant_trading_system import QuantTradingSystem

system = QuantTradingSystem()
system.initialize("config.json")

# Cell 2: 加载MA策略
strategy_config = {
    "name": "ma_rb",
    "symbols": ["rb2405"],
    "params": {"fast_ma": 10, "slow_ma": 30}
}
system.load_strategy("ma", strategy_config)

# Cell 3: 启动策略
system.strategy_engine.start_strategy("ma_rb")

# Cell 4: 启动监控
system.start_monitoring()
```

## ✅ 模块设计总结

**完成内容**：
- **5个核心模块的详细实现方案**
- **完整的测试用例设计** (单元测试 + 集成测试)
- **开发优先级规划** (3周迭代计划)
- **Jupyter集成方案** (用户友好的接口)
- **端到端测试场景** (验证完整流程)

**下一步行动**：
现在可以开始第一阶段的开发工作：
1. VN.PY环境搭建
2. ConnectionManager模块开发
3. MarketDataManager模块开发

请您确认这个模块设计方案，然后我们就可以开始实际的代码开发了！