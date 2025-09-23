# 极简期货量化交易系统 - 功能设计

## 📋 模块功能详细设计

### 1. 连接管理模块 (ConnectionManager)

#### 1.1 功能规格
**主要职责**：管理与期货交易所的连接，支持模拟和实盘环境

#### 1.2 接口定义
```python
class ConnectionManager:
    def __init__(self, config: dict):
        """初始化连接管理器"""
        
    def connect_gateway(self) -> bool:
        """
        连接CTP网关
        返回: True-连接成功, False-连接失败
        """
        
    def disconnect_gateway(self) -> bool:
        """断开网关连接"""
        
    def get_connection_status(self) -> dict:
        """
        获取连接状态
        返回: {
            'connected': bool,
            'login_time': datetime,
            'gateway_name': str,
            'error_msg': str
        }
        """
        
    def switch_environment(self, env_type: str) -> bool:
        """
        切换环境 (SIMULATION/LIVE)
        参数: env_type - 环境类型
        """
```

#### 1.3 核心逻辑伪代码
```
连接流程:
1. 加载配置信息 (服务器地址、用户名密码)
2. 初始化VN.PY主引擎和事件引擎
3. 添加CTP网关
4. 发起连接请求
5. 等待连接确认
6. 订阅账户和持仓信息
7. 返回连接状态

重连机制:
1. 监测连接状态
2. 如果断开，等待5秒后重试
3. 最多重试3次
4. 重连失败则通知用户
```

### 2. 合约管理模块 (ContractManager)

#### 2.1 功能规格
**主要职责**：管理数据合约与交易合约的映射，处理合约切换

#### 2.2 数据结构定义
```python
@dataclass
class ContractMapping:
    symbol: str              # 品种代码 (rb, i, j, etc.)
    data_contract: str       # 数据合约代码
    trade_contract: str      # 交易合约代码
    switch_date: date        # 下次切换日期
    is_main: bool           # 是否为主力合约
    
@dataclass
class ContractInfo:
    symbol: str              # 合约代码
    exchange: str           # 交易所
    product_type: str       # 产品类型
    size: int              # 合约乘数
    min_volume: int        # 最小交易量
    price_tick: float      # 最小变动价位
```

#### 2.3 接口定义
```python
class ContractManager:
    def register_contract_mapping(self, mapping: ContractMapping):
        """注册合约映射关系"""
        
    def get_data_contract(self, symbol: str) -> str:
        """获取指定品种的数据合约"""
        
    def get_trade_contract(self, symbol: str) -> str:
        """获取指定品种的交易合约"""
        
    def get_main_contracts(self) -> List[str]:
        """获取所有主力合约列表"""
        
    def check_contract_switch(self) -> List[ContractMapping]:
        """检查需要切换的合约"""
        
    def update_contract_mapping(self, symbol: str, new_contract: str):
        """更新合约映射"""
```

#### 2.4 核心逻辑
```
合约映射管理:
1. 维护 symbol -> (data_contract, trade_contract) 映射表
2. 支持动态更新映射关系
3. 处理合约到期切换逻辑

主力合约识别:
1. 基于成交量和持仓量判断主力合约
2. 定期更新主力合约信息
3. 提供合约切换预警

加权合约计算:
1. 按权重合成连续合约价格
2. 处理合约切换时的价格跳跃
3. 提供平滑的价格序列供策略使用
```

### 3. 行情数据模块 (MarketDataManager)

#### 3.1 功能规格
**主要职责**：实时行情数据获取、处理和技术指标计算

#### 3.2 数据结构定义
```python
@dataclass
class TickData:
    symbol: str
    datetime: datetime
    last_price: float
    volume: int
    open_interest: int
    bid_price_1: float
    bid_volume_1: int
    ask_price_1: float 
    ask_volume_1: int

@dataclass  
class BarData:
    symbol: str
    datetime: datetime
    interval: str           # 1m, 5m, 15m, 1h, 1d
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
```

#### 3.3 接口定义
```python
class MarketDataManager:
    def subscribe_market_data(self, symbols: List[str]):
        """订阅行情数据"""
        
    def unsubscribe_market_data(self, symbols: List[str]):
        """取消订阅行情数据"""
        
    def get_latest_tick(self, symbol: str) -> TickData:
        """获取最新tick数据"""
        
    def get_latest_bar(self, symbol: str, interval: str) -> BarData:
        """获取最新K线数据"""
        
    def calculate_ma(self, symbol: str, period: int) -> float:
        """计算移动平均线"""
        
    def calculate_rsi(self, symbol: str, period: int) -> float:
        """计算RSI指标"""
        
    def register_callback(self, callback_func):
        """注册行情数据回调函数"""
```

#### 3.4 核心逻辑
```
实时行情处理:
1. 接收VN.PY推送的tick数据
2. 合成不同周期的K线数据 (1分钟, 5分钟等)
3. 缓存历史数据用于指标计算
4. 触发策略引擎的数据更新事件

技术指标计算:
1. 维护滑动窗口数据
2. 实时计算常用技术指标 (MA, RSI, MACD等)
3. 支持自定义指标添加
4. 优化计算性能，避免重复计算
```

### 4. 策略引擎模块 (StrategyEngine)

#### 4.1 功能规格
**主要职责**：策略逻辑执行、信号生成和策略生命周期管理

#### 4.2 策略信号定义
```python
@dataclass
class TradingSignal:
    symbol: str             # 交易品种
    direction: str          # LONG/SHORT
    action: str            # OPEN/CLOSE/ADD/REDUCE
    volume: int            # 交易数量
    price_type: str        # MARKET/LIMIT  
    price: Optional[float] # 限价 (市价单为None)
    stop_loss: Optional[float]  # 止损价
    take_profit: Optional[float] # 止盈价
    strategy_name: str     # 策略名称
    timestamp: datetime    # 信号生成时间
```

#### 4.3 基础策略类定义
```python
class BaseStrategy:
    def __init__(self, strategy_name: str, symbols: List[str]):
        self.strategy_name = strategy_name
        self.symbols = symbols
        self.active = False
        
    def on_init(self):
        """策略初始化 - 加载历史数据，初始化指标"""
        pass
        
    def on_start(self):
        """策略启动 - 开始接收数据"""
        self.active = True
        
    def on_stop(self):
        """策略停止"""
        self.active = False
        
    def on_tick(self, tick: TickData):
        """处理tick数据"""
        if not self.active:
            return
        # 子类实现具体逻辑
        
    def on_bar(self, bar: BarData):
        """处理K线数据"""
        if not self.active:
            return
        # 子类实现具体逻辑
        
    def generate_signal(self, symbol: str, direction: str, action: str, volume: int) -> TradingSignal:
        """生成交易信号"""
        return TradingSignal(
            symbol=symbol,
            direction=direction,
            action=action,
            volume=volume,
            price_type="MARKET",
            price=None,
            strategy_name=self.strategy_name,
            timestamp=datetime.now()
        )
```

#### 4.4 趋势跟踪策略示例
```python
class MAStrategy(BaseStrategy):
    """移动平均趋势跟踪策略"""
    
    def __init__(self, strategy_name: str, symbols: List[str], 
                 fast_ma: int = 10, slow_ma: int = 30):
        super().__init__(strategy_name, symbols)
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.positions = {}  # 记录持仓状态
        
    def on_bar(self, bar: BarData):
        """K线数据处理"""
        if not self.active:
            return
            
        # 计算移动平均线
        fast_ma_value = self.calculate_ma(bar.symbol, self.fast_ma)
        slow_ma_value = self.calculate_ma(bar.symbol, self.slow_ma)
        
        if fast_ma_value is None or slow_ma_value is None:
            return
            
        current_pos = self.positions.get(bar.symbol, 0)
        
        # 生成交易信号
        if fast_ma_value > slow_ma_value and current_pos <= 0:
            # 金叉信号 - 开多仓或平空仓
            if current_pos < 0:
                # 先平空仓
                signal = self.generate_signal(bar.symbol, "SHORT", "CLOSE", abs(current_pos))
                self.send_signal(signal)
            # 开多仓
            signal = self.generate_signal(bar.symbol, "LONG", "OPEN", 1)
            self.send_signal(signal)
            
        elif fast_ma_value < slow_ma_value and current_pos >= 0:
            # 死叉信号 - 开空仓或平多仓
            if current_pos > 0:
                # 先平多仓
                signal = self.generate_signal(bar.symbol, "LONG", "CLOSE", current_pos)
                self.send_signal(signal)
            # 开空仓  
            signal = self.generate_signal(bar.symbol, "SHORT", "OPEN", 1)
            self.send_signal(signal)
```

#### 4.5 接口定义
```python
class StrategyEngine:
    def load_strategy(self, strategy_class, strategy_config: dict):
        """加载策略"""
        
    def start_strategy(self, strategy_name: str):
        """启动指定策略"""
        
    def stop_strategy(self, strategy_name: str):
        """停止指定策略"""
        
    def get_strategy_status(self) -> Dict[str, dict]:
        """获取所有策略状态"""
        
    def register_signal_callback(self, callback_func):
        """注册信号回调函数"""
```

### 5. 交易执行模块 (TradingEngine)

#### 5.1 功能规格
**主要职责**：订单管理、交易执行和持仓管理

#### 5.2 数据结构定义
```python
@dataclass
class OrderData:
    orderid: str           # 订单ID
    symbol: str           # 合约代码
    exchange: str         # 交易所
    direction: str        # LONG/SHORT
    offset: str          # OPEN/CLOSE
    type: str            # MARKET/LIMIT
    volume: int          # 委托数量
    traded: int          # 成交数量
    status: str          # 订单状态
    price: float         # 委托价格
    time: datetime       # 委托时间
    
@dataclass
class TradeData:
    tradeid: str         # 成交ID  
    orderid: str         # 订单ID
    symbol: str          # 合约代码
    direction: str       # 方向
    offset: str          # 开平
    volume: int          # 成交数量
    price: float         # 成交价格
    time: datetime       # 成交时间

@dataclass
class PositionData:
    symbol: str          # 合约代码
    direction: str       # LONG/SHORT
    volume: int          # 持仓数量
    yd_volume: int       # 昨仓数量
    frozen: int          # 冻结数量
    price: float         # 平均价格
    pnl: float          # 持仓盈亏
    percent: float      # 盈亏比例
```

#### 5.3 接口定义
```python
class TradingEngine:
    def send_order(self, signal: TradingSignal) -> str:
        """
        发送订单
        返回: 订单ID
        """
        
    def cancel_order(self, orderid: str) -> bool:
        """撤销订单"""
        
    def get_order(self, orderid: str) -> OrderData:
        """获取订单信息"""
        
    def get_all_orders(self) -> List[OrderData]:
        """获取所有订单"""
        
    def get_position(self, symbol: str) -> PositionData:
        """获取指定合约持仓"""
        
    def get_all_positions(self) -> List[PositionData]:
        """获取所有持仓"""
        
    def calculate_pnl(self, symbol: str = None) -> float:
        """计算盈亏 (不指定symbol则计算总盈亏)"""
```

#### 5.4 核心逻辑
```
订单管理流程:
1. 接收策略信号
2. 信号转换为订单参数
3. 风险检查 (资金、持仓限制等)
4. 发送订单到交易所
5. 跟踪订单状态变化
6. 处理成交回报
7. 更新持仓信息

持仓管理:
1. 实时更新持仓数量和均价
2. 计算浮动盈亏
3. 处理今仓昨仓分离
4. 支持锁仓模式
```

### 6. 账户管理模块 (AccountManager)

#### 6.1 功能规格
**主要职责**：账户信息管理、资金状况监控

#### 6.2 数据结构定义
```python
@dataclass
class AccountData:
    accountid: str       # 账户ID
    balance: float       # 账户余额
    frozen: float        # 冻结金额
    available: float     # 可用资金
    margin: float        # 占用保证金
    profit: float        # 持仓盈亏
    risk_ratio: float    # 风险度
```

#### 6.3 接口定义
```python
class AccountManager:
    def get_account_info(self) -> AccountData:
        """获取账户信息"""
        
    def get_available_margin(self) -> float:
        """获取可用保证金"""
        
    def calculate_margin_ratio(self) -> float:
        """计算保证金使用率"""
        
    def get_total_pnl(self) -> float:
        """获取总盈亏"""
        
    def check_margin_sufficient(self, required_margin: float) -> bool:
        """检查保证金是否充足"""
```

### 7. 监控显示模块 (MonitoringDisplay)

#### 7.1 功能规格
**主要职责**：Jupyter界面显示、实时数据展示

#### 7.2 接口定义
```python
class MonitoringDisplay:
    def show_positions_table(self):
        """显示持仓表格"""
        
    def show_account_summary(self):
        """显示账户摘要"""
        
    def show_strategy_status(self):
        """显示策略状态"""
        
    def show_recent_trades(self, count: int = 10):
        """显示最近成交"""
        
    def start_auto_refresh(self, interval: int = 3):
        """启动自动刷新"""
        
    def stop_auto_refresh(self):
        """停止自动刷新"""
```

#### 7.3 显示格式设计
```python
# 持仓监控表格
def format_positions_table(positions: List[PositionData]) -> str:
    """
    格式化持仓表格
    ┌────────┬─────────┬─────────┬──────┬─────────┬─────────────┐
    │ 品种   │ 合约    │ 方向    │ 数量 │ 开仓价  │ 浮动盈亏    │
    ├────────┼─────────┼─────────┼──────┼─────────┼─────────────┤
    │ 螺纹钢 │ rb2405  │ 多头    │ 2    │ 3500.0  │ +150.0      │
    │ 铁矿石 │ i2405   │ 空头    │ 1    │ 800.0   │ -80.0       │
    └────────┴─────────┴─────────┴──────┴─────────┴─────────────┘
    """
```

## 🔗 模块间接口协议

### 事件定义
```python
class EventType:
    TICK = "tick"                    # tick数据更新
    BAR = "bar"                     # K线数据更新  
    TRADE = "trade"                 # 成交事件
    ORDER = "order"                 # 订单状态更新
    POSITION = "position"           # 持仓更新
    ACCOUNT = "account"            # 账户更新
    STRATEGY_SIGNAL = "signal"      # 策略信号
    LOG = "log"                    # 日志事件
```

### 回调函数协议
```python
def on_tick_callback(tick: TickData):
    """tick数据回调"""
    pass
    
def on_signal_callback(signal: TradingSignal):
    """策略信号回调"""  
    pass
    
def on_trade_callback(trade: TradeData):
    """成交回调"""
    pass
```

## 📊 数据流图

```
行情数据流:
交易所 → VN.PY网关 → MarketDataManager → StrategyEngine → TradingSignal

交易执行流:
TradingSignal → TradingEngine → VN.PY网关 → 交易所 → TradeData

监控显示流:  
PositionData/AccountData → MonitoringDisplay → Jupyter界面
```

## ✅ 功能设计总结

完成了所有7个核心模块的详细功能设计：
- **明确的接口定义**：每个模块都有清晰的输入输出
- **完整的数据结构**：标准化的数据交换格式
- **详细的业务逻辑**：用伪代码描述核心算法
- **示例实现**：提供了MA策略的具体实现示例

下一步将进入**模块设计**阶段，为每个模块制定具体的实现方案和测试用例。