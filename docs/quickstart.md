# 快速开始指南

## 🚀 第一次运行

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt
```

### 2. 配置环境

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件（可选）
nano .env
```

### 3. 运行示例

```bash
# 运行简单示例
python examples/simple_example.py

# 运行主程序帮助
python main.py --help
```

## 📊 基本使用

### 命令行模式

```bash
# 运行回测
python main.py backtest --strategy ma --symbol BTCUSDT --start 2023-01-01 --end 2023-12-31

# 启动实盘交易
python main.py live --gateway BINANCE

# 下载数据
python main.py data --symbol BTCUSDT --start 2023-01-01 --end 2023-12-31
```

### 编程模式

```python
from strategies.moving_average_strategy import MovingAverageStrategy

# 创建策略
strategy = MovingAverageStrategy(
    name="MA_Strategy",
    symbol="BTCUSDT",
    parameters={
        'fast_ma_period': 10,
        'slow_ma_period': 30
    }
)

# 启动策略
strategy.start()

# 添加数据（示例）
bar_data = {
    'datetime': datetime.now(),
    'open_price': 16500,
    'high_price': 16600,
    'low_price': 16400,
    'close_price': 16550,
    'volume': 100
}

strategy.add_bar(bar_data)
```

## 🔧 自定义策略

创建新策略文件：

```python
from strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def calculate_indicators(self):
        # 计算技术指标
        pass
    
    def on_bar(self, bar):
        # 处理K线数据
        if self.should_buy():
            self.buy(bar['close_price'], 1.0)
        elif self.should_sell():
            self.sell(bar['close_price'], 1.0)
```

## 📈 下一步

1. 阅读完整文档
2. 查看更多示例
3. 开发自己的策略
4. 配置实盘交易接口

更多详细信息请查看项目文档。