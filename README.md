# VN.PY 量化交易系统

基于 VN.PY 框架构建的完整量化交易系统，支持策略开发、回测分析、风险控制和实盘交易。

## 🚀 主要特性

### 📊 数据管理
- **多数据源支持**: Binance、Yahoo Finance、CSV文件
- **数据存储**: SQLite、MongoDB、Redis缓存  
- **实时数据**: WebSocket实时行情推送
- **数据下载**: 自动下载和更新历史数据

### 🧠 策略框架
- **基础策略类**: 完整的策略开发框架
- **内置策略**:
  - 移动平均策略 (MA)
  - RSI策略
  - 布林带策略 (Bollinger Bands)
- **技术指标**: 内置常用技术指标计算
- **信号生成**: 自动化交易信号产生

### 📈 回测引擎
- **历史回测**: 基于历史数据的策略测试
- **性能分析**: 详细的收益、风险指标分析
- **可视化图表**: 权益曲线、回撤分析、收益分布
- **报告生成**: 完整的回测报告输出

### 🛡️ 风险管理
- **多层风险控制**: 
  - 最大持仓限制
  - 日亏损限制  
  - 回撤控制
  - 波动率监控
- **实时监控**: 风险指标实时计算
- **紧急停止**: 一键紧急停止功能

### 💼 实盘交易
- **交易接口**: 支持Binance、CTP等主流接口
- **订单管理**: 完整的订单生命周期管理
- **投资组合**: 多策略资金分配管理
- **实时监控**: 持仓、订单、账户信息监控

## 🏗️ 项目结构

```
webapp/
├── config/                 # 配置文件
├── data/                   # 数据管理
├── strategies/             # 策略模块
├── backtest/              # 回测模块
├── trading/               # 实盘交易
├── examples/              # 示例代码
├── docs/                  # 文档
├── main.py                # 主程序
└── requirements.txt       # 依赖包
```

## 🛠️ 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置环境
```bash
cp .env.example .env
# 编辑 .env 文件，配置API密钥
```

### 运行回测
```bash
python main.py backtest --strategy ma --symbol BTCUSDT --start 2023-01-01 --end 2023-12-31
```

### 启动实盘交易
```bash
python main.py live --gateway BINANCE
```

### 下载数据
```bash
python main.py data --symbol BTCUSDT --start 2023-01-01 --end 2023-12-31
```

## 📚 文档

- [安装指南](docs/installation.md)
- [快速开始](docs/quickstart.md)
- [策略开发](docs/strategy_guide.md)
- [API参考](docs/api.md)

## 🤝 贡献

欢迎贡献代码和提出建议！请查看贡献指南了解详情。

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## ⚠️ 免责声明

本软件仅供学习和研究使用，不构成投资建议。使用本软件进行实盘交易的任何损失由用户自行承担。

## 🙏 致谢

- [VN.PY](https://github.com/vnpy/vnpy) - 优秀的量化交易框架
- [CCXT](https://github.com/ccxt/ccxt) - 加密货币交易所API
- [Pandas](https://pandas.pydata.org/) - 数据分析库

---

如有问题或建议，请创建 Issue 或 Pull Request。