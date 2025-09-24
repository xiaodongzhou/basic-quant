# 极简期货量化交易系统 - 概要设计

## 🏗️ 系统整体架构

### 架构原则
- **模块化设计**：每个模块职责单一，低耦合高内聚
- **VN.PY集成**：充分利用VN.PY框架的能力
- **Jupyter友好**：适配Notebook的交互特性
- **扩展性**：为后续功能扩展预留接口

### 系统分层架构

```
┌─────────────────────────────────────────┐
│           Jupyter Notebook Interface    │  ← 用户交互层
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐ │
│  │监控界面 │ │策略控制 │ │配置管理     │ │
│  └─────────┘ └─────────┘ └─────────────┘ │
├─────────────────────────────────────────┤
│              Business Logic Layer       │  ← 业务逻辑层
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐ │
│  │策略引擎 │ │交易管理 │ │风险控制     │ │
│  └─────────┘ └─────────┘ └─────────────┘ │
├─────────────────────────────────────────┤
│              Data Access Layer          │  ← 数据访问层
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐ │
│  │行情数据 │ │账户数据 │ │合约管理     │ │
│  └─────────┘ └─────────┘ └─────────────┘ │
├─────────────────────────────────────────┤
│              VN.PY Framework            │  ← VN.PY框架层
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐ │
│  │CTP网关  │ │事件引擎 │ │数据管理     │ │
│  └─────────┘ └─────────┘ └─────────────┘ │
└─────────────────────────────────────────┘
```

## 📦 核心模块设计

### 1. 连接管理模块 (ConnectionManager)
**职责**：管理与期货交易所的连接
```python
class ConnectionManager:
    - connect_gateway()      # 连接CTP网关
    - disconnect_gateway()   # 断开连接
    - get_connection_status() # 获取连接状态
    - handle_reconnection()  # 处理重连逻辑
```

**关键特性**：
- 支持模拟和实盘环境切换
- 自动重连机制
- 连接状态监控

### 2. 合约管理模块 (ContractManager)  
**职责**：管理数据合约与交易合约的映射
```python
class ContractManager:
    - register_data_contract()    # 注册数据合约
    - register_trade_contract()   # 注册交易合约
    - get_main_contract()        # 获取主力合约
    - get_weighted_contract()    # 获取加权合约
    - handle_contract_switch()   # 处理合约切换
```

**数据结构**：
```python
ContractMapping = {
    "symbol": "rb",  # 品种代码
    "data_contract": "rb_weighted",    # 数据合约
    "trade_contract": "rb2405",        # 交易合约
    "switch_date": "2024-04-15",       # 切换日期
}
```

### 3. 行情数据模块 (MarketDataManager)
**职责**：实时行情数据获取和处理
```python
class MarketDataManager:
    - subscribe_market_data()    # 订阅行情
    - get_tick_data()           # 获取tick数据
    - get_bar_data()            # 获取K线数据
    - calculate_indicators()     # 计算技术指标
```

**数据流设计**：
- 实时tick数据 → K线合成 → 技术指标计算 → 策略信号生成

### 4. 策略引擎模块 (StrategyEngine)
**职责**：策略逻辑执行和信号生成
```python
class StrategyEngine:
    - load_strategy()           # 加载策略
    - start_strategy()          # 启动策略
    - stop_strategy()           # 停止策略
    - on_tick()                # 处理tick数据
    - on_bar()                 # 处理K线数据
    - generate_signals()        # 生成交易信号
```

**策略信号定义**：
```python
TradingSignal = {
    "symbol": "rb2405",
    "direction": "LONG",        # LONG/SHORT
    "action": "OPEN",          # OPEN/CLOSE/ADD/REDUCE  
    "volume": 1,               # 交易数量
    "price_type": "MARKET",    # MARKET/LIMIT
    "price": 3500.0,          # 限价（市价单可为None）
}
```

### 5. 交易执行模块 (TradingEngine)
**职责**：订单管理和交易执行
```python
class TradingEngine:
    - send_order()             # 发送订单
    - cancel_order()           # 撤销订单
    - get_positions()          # 获取持仓
    - get_orders()             # 获取订单
    - calculate_pnl()          # 计算盈亏
```

**订单状态管理**：
- 订单提交 → 已报 → 部分成交 → 全部成交
- 异常处理：拒绝、撤销、超时

### 6. 账户管理模块 (AccountManager)
**职责**：账户信息和资金管理
```python
class AccountManager:
    - get_account_info()       # 获取账户信息
    - get_balance()           # 获取资金余额
    - get_positions()         # 获取持仓详情
    - calculate_total_pnl()    # 计算总盈亏
```

### 7. 监控显示模块 (MonitoringDisplay)
**职责**：Jupyter界面显示和交互
```python
class MonitoringDisplay:
    - show_positions_table()   # 显示持仓表格
    - show_pnl_summary()      # 显示盈亏汇总
    - show_strategy_status()   # 显示策略状态
    - update_display()        # 更新显示内容
```

**显示内容设计**：
```
持仓监控表格：
┌────────┬─────────┬─────────┬──────┬─────────┬─────────────┐
│ 品种   │ 合约    │ 方向    │ 数量 │ 开仓价  │ 浮动盈亏    │
├────────┼─────────┼─────────┼──────┼─────────┼─────────────┤
│ 螺纹钢 │ rb2405  │ 多头    │ 2    │ 3500.0  │ +150.0      │
│ 铁矿石 │ i2405   │ 空头    │ 1    │ 800.0   │ -80.0       │
└────────┴─────────┴─────────┴──────┴─────────┴─────────────┘
```

## 🔄 数据流设计

### 实时数据流
```
期货交易所 → VN.PY网关 → 行情数据模块 → 策略引擎 → 交易执行模块 → 订单反馈
     ↑                                                              ↓
     └─────────────────── 交易指令发送 ←─────────────────────────────┘
```

### 策略执行流程
```
1. 行情数据更新 → 2. 技术指标计算 → 3. 策略信号生成 → 4. 风险检查 → 5. 订单发送
                                                                      ↓
6. 监控界面更新 ← 5. 持仓更新 ← 4. 成交反馈 ← 3. 订单状态 ← 2. 交易所反馈
```

## 📊 技术架构选择

### 核心技术栈
- **VN.PY 3.x**: 量化交易框架
- **Python 3.8+**: 开发语言  
- **Jupyter Notebook**: 交互环境
- **Pandas**: 数据处理
- **NumPy**: 数值计算
- **asyncio**: 异步处理
- **threading**: 多线程支持

### VN.PY集成方案
```python
# VN.PY核心组件使用
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.gateway.ctp import CtpGateway
from vnpy.app.cta_strategy import CtaStrategyApp
```

### 异步处理设计
- **事件驱动**：基于VN.PY事件引擎
- **异步更新**：界面异步更新，不阻塞交易
- **线程安全**：多线程访问数据的安全机制

## 🔧 配置管理设计

### 配置文件结构
```python
# config.json
{
    "gateway": {
        "name": "CTP",
        "settings": {
            "用户名": "your_username",
            "密码": "your_password", 
            "经纪商代码": "9999",
            "交易服务器": "tcp://180.168.146.187:10130",
            "行情服务器": "tcp://180.168.146.187:10131"
        }
    },
    "contracts": {
        "rb": {
            "data_contract": "rb_weighted",
            "trade_contract": "rb2405"
        },
        "i": {
            "data_contract": "i_weighted", 
            "trade_contract": "i2405"
        }
    },
    "strategies": {
        "ma_strategy": {
            "class": "MAStrategy",
            "settings": {
                "fast_ma": 10,
                "slow_ma": 30
            }
        }
    }
}
```

## 🎯 模块接口设计

### 统一接口规范
所有模块遵循统一的接口设计模式：
```python
class BaseModule:
    def initialize(self, config): pass    # 初始化
    def start(self): pass                # 启动
    def stop(self): pass                 # 停止
    def get_status(self): pass           # 获取状态
    def on_event(self, event): pass      # 事件处理
```

### 模块间通信
- **事件驱动**：通过VN.PY事件引擎通信
- **回调机制**：关键状态变化通过回调通知
- **数据共享**：通过共享数据结构交换信息

## 📈 扩展性设计

### 策略扩展接口
```python
class BaseStrategy:
    def on_init(self): pass              # 策略初始化
    def on_start(self): pass             # 策略启动
    def on_stop(self): pass              # 策略停止
    def on_tick(self, tick): pass        # tick数据处理
    def on_bar(self, bar): pass          # K线数据处理
```

### 功能扩展预留
- **插件机制**：支持策略、指标、风控插件
- **数据源扩展**：支持多种数据源接入
- **交易接口扩展**：支持多种交易接口
- **监控界面扩展**：支持自定义监控面板

## ✅ 概要设计总结

**架构优势**：
- 模块化设计，便于开发和维护
- 基于VN.PY成熟框架，稳定可靠
- 数据合约与交易合约分离，灵活配置
- 事件驱动架构，响应及时
- 良好的扩展性，支持功能增强

**关键创新点**：
- 合约映射管理解决数据/交易分离需求
- Jupyter Notebook集成提供良好交互体验
- 多策略并行运行支持
- 实时监控界面设计

下一步将进入**功能设计**阶段，详细定义各模块的具体功能和接口。