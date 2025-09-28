# 🚀 VN.PY 量化交易系统 v2.0

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/xiaodongzhou/basic-quant/releases/tag/v2.0.0)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen.svg)](https://5035-iqwt7pakk30j34exwvp41-6532622b.e2b.dev)

**专业的期货量化交易系统** - 基于VN.PY框架构建，集成真实市场数据、中式交易界面、动态合约选择等功能。

🌐 **在线演示**: https://5035-iqwt7pakk30j34exwvp41-6532622b.e2b.dev  
📚 **完整文档**: [项目结构说明](PROJECT_STRUCTURE_GUIDE.md) | [版本发布总结](V2_0_MAJOR_RELEASE_SUMMARY.md) | [发展路线图](NEXT_PHASE_ROADMAP.md)

## ✨ v2.0 核心功能亮点

### 🎯 **生产级功能** (v2.0 全新升级)
- 🔴 **中式蜡烛图**: 红涨绿跌，符合中国期货市场习惯
- 📊 **真实市场数据**: AKShare集成，替代模拟数据
- 🔄 **动态合约选择**: 智能主力合约识别，两级选择UI
- 📏 **智能Y轴缩放**: 品种自适应价格单位显示
- ⚡ **实时数据流**: WebSocket + AKShare实时推送
- 📈 **增强回测系统**: 多周期真实历史数据分析

### 📊 **支持品种** (13个主要期货)
- 🏭 **商品期货**: 螺纹钢、沪铜、沪铝、铁矿石、焦炭、焦煤、热卷  
- 🥇 **贵金属**: 沪镍、沪锌、沪锡、沪铅、沪银、沪金

### 🔧 **数据管理**
- **AKShare数据源**: 专业期货数据接口
- **多周期支持**: 5分钟、15分钟、30分钟、1小时、日线
- **实时推送**: WebSocket实时行情数据
- **智能映射**: 动态合约代码到数据源映射

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