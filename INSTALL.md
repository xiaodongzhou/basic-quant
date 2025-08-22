# 📦 量化交易系统安装指南

## 🚀 快速开始

### 1. 系统要求
- Python 3.8+ 
- pip 包管理器
- 8GB+ 内存推荐
- 网络连接（用于API调用）

### 2. 安装步骤

#### 方法一：最小依赖安装（推荐）
```bash
# 克隆项目
git clone https://github.com/xiaodongzhou/basic-quant.git
cd basic-quant

# 安装核心依赖（只安装必需的包）
pip install -r requirements-core.txt
```

#### 方法二：完整依赖安装
```bash
# 安装所有可选依赖（包括可视化、机器学习等）
pip install pandas numpy matplotlib seaborn plotly
pip install requests python-dotenv loguru
pip install python-dateutil pytz
```

### 3. 验证安装

```bash
# 运行完整系统演示
python demo_complete_system.py

# 查看命令行帮助
python main.py --help

# 测试数据管理
python main.py data --symbol BTCUSDT --start 2024-01-01 --end 2024-01-07
```

## 📋 依赖说明

### 核心依赖 (requirements-core.txt)
- **pandas**: 数据处理和分析
- **numpy**: 数值计算
- **matplotlib**: 基础图表绘制
- **requests**: HTTP API调用
- **python-dotenv**: 环境变量管理
- **loguru**: 日志系统
- **python-dateutil**: 时间处理
- **pytz**: 时区支持

### 可选依赖
- **seaborn**: 统计图表美化
- **plotly**: 交互式图表
- **websocket-client**: WebSocket连接
- **ccxt**: 多交易所API支持
- **scikit-learn**: 机器学习算法
- **aiohttp**: 异步HTTP客户端

### VN.PY 生态集成（可选）
如果需要与VN.PY生态系统集成，可安装：
```bash
pip install vnpy==3.9.2
pip install vnpy-binance==2025.6.17  # 最新版本
pip install vnpy-ctp==6.6.9
pip install vnpy-ctastrategy==1.0.25
```

## ⚠️ 常见问题

### 1. vnpy-binance版本错误
**错误**: `ERROR: Could not find a version that satisfies the requirement vnpy-binance==1.0.26`

**解决方案**: 
```bash
# 使用最新可用版本
pip install vnpy-binance==2025.6.17

# 或查看所有可用版本
pip index versions vnpy-binance
```

### 2. 网络连接问题
**错误**: Binance API返回451错误

**说明**: 这是正常的地理限制，系统会优雅处理此错误。可以：
- 使用演示模式查看功能
- 配置代理或VPN
- 使用其他数据源

### 3. 权限问题
**错误**: 无法创建数据库或日志文件

**解决方案**:
```bash
# 确保有写入权限
chmod +w .
mkdir -p data/database logs
```

## 🔧 配置

### 环境变量配置
创建 `.env` 文件：
```bash
# API配置
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# 数据库配置
DATABASE_PATH=data/database/market_data.db

# 日志配置
LOG_LEVEL=INFO
LOG_PATH=logs/
```

### 数据库配置
系统使用SQLite数据库，无需额外配置。首次运行时会自动创建数据库文件。

## 🎯 使用示例

### 基础用法
```bash
# 1. 数据下载（模拟）
python main.py data --symbol ETHUSDT --start 2024-01-01 --end 2024-01-31

# 2. 策略回测
python main.py backtest --strategy ma --capital 100000 --fast-ma 10 --slow-ma 30

# 3. 实盘交易模拟
python main.py live --strategy ma --capital 50000
```

### 高级用法
```bash
# 自定义参数回测
python main.py backtest \
  --symbol BTCUSDT \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --strategy ma \
  --capital 1000000 \
  --fast-ma 5 \
  --slow-ma 20 \
  --interval 1h

# 多品种实盘交易
python main.py live \
  --symbol ETHUSDT \
  --strategy ma \
  --capital 200000 \
  --gateway BINANCE
```

## 📊 系统架构

```
📦 量化交易系统
├── 📂 config/          # 配置管理
├── 📂 data/            # 数据管理
├── 📂 strategies/      # 策略实现
├── 📂 trading/         # 交易管理
├── 📂 examples/        # 使用示例
├── main.py            # 主程序入口
├── demo_complete_system.py    # 完整演示
├── requirements-core.txt      # 核心依赖
└── requirements.txt          # 完整依赖
```

## 🆘 获取帮助

1. **查看命令帮助**: `python main.py --help`
2. **运行演示程序**: `python demo_complete_system.py`
3. **查看日志文件**: `logs/` 目录
4. **检查数据库**: `data/database/market_data.db`

## 🎉 成功标志

安装成功后，您应该能看到：
- ✅ 演示程序正常运行
- ✅ 数据管理功能正常
- ✅ 策略回测计算正确
- ✅ 实盘交易模拟正常
- ✅ 日志文件正常生成