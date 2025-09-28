# 🚀 VN.PY 量化交易系统 v2.4.0

[![Version](https://img.shields.io/badge/version-2.4.0-blue.svg)](https://github.com/xiaodongzhou/basic-quant/releases/tag/v2.4.0)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen.svg)](https://5035-iqwt7pakk30j34exwvp41-6532622b.e2b.dev)

**专业的期货量化交易系统** - 基于VN.PY框架构建，集成32个期货品种、完整技术指标系统、专业策略库和智能回测引擎。

🌐 **在线演示**: https://5035-iqwt7pakk30j34exwvp41-6532622b.e2b.dev  
📚 **完整文档**: [项目结构说明](PROJECT_STRUCTURE_GUIDE.md) | [发展路线图](NEXT_PHASE_ROADMAP.md)

## ✨ v2.4.0 重大功能更新

### 🎯 **核心系统升级**
- 📊 **品种大扩展**: 13个 → **32个期货品种** (+146%增长)
- 📈 **完整技术指标系统**: **6大核心指标** (MACD/RSI/KDJ/布林带/OBV/VRSI)
- 🧠 **专业策略库**: **3大策略类型** + 回测引擎
- 🔴 **中式交易界面**: 红涨绿跌，符合中国期货市场习惯
- ⚡ **实时数据流**: WebSocket + AKShare + 模拟数据降级

### 📊 **支持的32个期货品种**

#### 🏭 **商品期货 - 黑色系** (5个)
- **螺纹钢(RB)** | **铁矿石(I)** | **焦炭(J)** | **焦煤(JM)** | **热卷(HC)**

#### ⚡ **有色金属** (6个)  
- **沪铜(CU)** | **沪铝(AL)** | **沪镍(NI)** | **沪锌(ZN)** | **沪锡(SN)** | **沪铅(PB)**

#### 🥇 **贵金属** (2个)
- **沪银(AG)** | **沪金(AU)**

#### 🏦 **股指期货** (4个) - ⭐ **新增**
- **沪深300(IF)** | **中证500(IC)** | **上证50(IH)** | **中证1000(IM)**

#### 🌾 **农产品期货** (10个) - ⭐ **新增**
- **大豆1号(A)** | **大豆2号(B)** | **玉米(C)** | **豆粕(M)** | **豆油(Y)**
- **棕榈油(P)** | **白糖(SR)** | **棉花(CF)** | **菜粕(RM)** | **菜籽油(OI)**

#### ⚡ **能源化工** (9个) - ⭐ **新增**
- **原油(SC)** | **PTA** | **甲醇(MA)** | **乙二醇(EG)** | **聚丙烯(PP)**
- **PVC(V)** | **聚乙烯(L)** | **沥青(BU)** | **燃料油(FU)**

### 📈 **完整技术指标系统**

#### 🎯 **6大核心指标** - ⭐ **新功能**
- **MACD** - 移动平均收敛发散指标 (DIF/DEA线 + 柱状图)
- **RSI** - 相对强弱指标 (超买超卖线 70/30)
- **KDJ** - 随机指标 (K/D/J三线)
- **布林带** - Bollinger Bands (上中下轨 + 价格线)
- **OBV** - 能量潮指标 (成交量分析)
- **VRSI** - 成交量相对强弱指标

#### 🔧 **技术特性**
- ✅ **实时计算**: 基于真实期货数据
- ✅ **参数化配置**: 支持自定义指标参数
- ✅ **智能信号**: 自动交易信号生成
- ✅ **图表可视化**: Chart.js专业图表
- ✅ **多指标切换**: 动态显示不同指标

### 🧠 **专业策略库系统**

#### 🎯 **3大策略类型** - ⭐ **新功能**

1. **🐢 海龟交易法则**
   - 唐奇安通道突破策略
   - 20日突破入场，10日突破出场
   - ATR动态止损系统
   - **适用**: 趋势明显的市场

2. **📊 布林带均值回归策略** 
   - 价格触及布林带极值 + RSI确认
   - 均值回归交易逻辑
   - **适用**: 震荡市场

3. **⚡ 动量策略**
   - 移动平均线交叉 + 价格动量
   - 趋势启动捕捉
   - **适用**: 趋势启动阶段

#### 🔧 **策略系统特性**
- ✅ **策略模板框架**: 可扩展的策略基类
- ✅ **自动参数优化**: 网格搜索最优参数  
- ✅ **完整回测引擎**: 13项回测指标
- ✅ **风险管理**: 动态止损止盈
- ✅ **策略对比**: 多策略性能比较

### 📊 **完整回测系统**

#### 🎯 **13项回测指标** - ⭐ **新功能**
- **总收益率** | **年化收益率** | **夏普比率** | **最大回撤**
- **胜率** | **盈亏比** | **总交易次数** | **盈利交易数** 
- **亏损交易数** | **平均交易时长** | **波动率** | **卡尔马比率**

#### 💻 **API接口系统**
- `GET /api/strategy_library/list` - 策略列表
- `GET /api/strategy_library/signals` - 策略信号
- `POST /api/strategy_library/backtest` - 策略回测
- `GET /api/strategy_library/compare` - 策略比较
- `GET /api/futures/technical_indicators` - 技术指标
- `GET /api/futures/contracts` - 期货合约

## 🏗️ 系统架构

### 💻 **技术栈**
```
后端技术栈:
├── Flask              # Web框架
├── SocketIO           # 实时数据推送
├── AKShare           # 期货数据源
├── Pandas + NumPy    # 数据分析
├── 策略库系统         # 量化策略
└── 技术指标引擎       # 指标计算

前端技术栈:
├── HTML5 + CSS3      # 现代化界面
├── Chart.js          # 专业图表
├── WebSocket         # 实时通信
└── 响应式设计         # 多设备适配
```

### 🗂️ **项目结构**
```
webapp/
├── core/                      # 核心模块
│   ├── strategy_library.py    # 策略库系统 ⭐ 新增
│   ├── technical_indicators.py # 技术指标引擎 ⭐ 新增
│   ├── backtest_engine.py     # 回测引擎
│   ├── data_types.py          # 数据结构
│   └── multi_strategy_manager.py # 多策略管理
├── templates/
│   └── index.html            # 前端界面
├── web_demo_server.py        # 主服务器
├── PROJECT_STRUCTURE_GUIDE.md # 项目文档
├── NEXT_PHASE_ROADMAP.md     # 发展路线
└── README.md                 # 项目说明
```

## 🛠️ 快速开始

### 1. **环境安装**
```bash
# 克隆项目
git clone https://github.com/xiaodongzhou/basic-quant.git
cd basic-quant

# 安装依赖
pip install flask flask-socketio pandas numpy akshare
```

### 2. **启动系统**
```bash
# 启动Web服务器
python web_demo_server.py

# 访问Web界面
# 本地: http://localhost:5035
# 在线: https://5035-iqwt7pakk30j34exwvp41-6532622b.e2b.dev
```

### 3. **使用功能**
- 🔴 **实时监控**: 查看32个期货品种实时行情
- 📊 **技术指标**: 使用6大技术指标分析
- 🧠 **策略测试**: 运行3大策略类型
- 📈 **回测分析**: 查看策略历史表现
- 🎯 **信号跟踪**: 获取实时交易信号

## 🚀 功能演示

### 📊 **品种扩展演示**
```bash
# 测试各类品种
curl "http://localhost:5035/api/futures/contracts?variety=if"   # 股指期货
curl "http://localhost:5035/api/futures/contracts?variety=a"    # 农产品  
curl "http://localhost:5035/api/futures/contracts?variety=sc"   # 能源化工
```

### 📈 **技术指标演示**
```bash
# 获取技术指标
curl "http://localhost:5035/api/futures/technical_indicators?symbol=rb2405&indicators=macd,rsi,kdj"
```

### 🧠 **策略库演示**
```bash
# 获取策略列表
curl "http://localhost:5035/api/strategy_library/list"

# 策略信号分析
curl "http://localhost:5035/api/strategy_library/signals?strategy_id=turtle_trading&symbol=rb2405"

# 策略对比
curl "http://localhost:5035/api/strategy_library/compare?strategies=turtle_trading,bollinger_bands,momentum"
```

## 🔧 开发指南

### 📊 **添加新技术指标**
```python
# 在 core/technical_indicators.py 中添加新指标
def calculate_custom_indicator(data, period=14):
    # 自定义指标计算逻辑
    pass
```

### 🧠 **开发新策略**
```python
# 继承策略模板基类
from core.strategy_library import StrategyTemplate

class CustomStrategy(StrategyTemplate):
    def generate_signals(self, data):
        # 自定义策略逻辑
        pass
```

### 📈 **扩展新品种**
```python
# 在 web_demo_server.py 中添加品种映射
variety_to_akshare = {
    'new_variety': 'NEW_SYMBOL0',  # 新品种映射
}

variety_config = {
    'new_variety': {'name': '新品种', 'exchange': 'EXCHANGE'},
}
```

## 📚 版本历史

### 🎉 **v2.4.0** (2025-09-28) - **完整版发布**
- ✅ **品种大扩展**: 32个期货品种全覆盖
- ✅ **技术指标系统**: 完整的6大指标
- ✅ **策略库系统**: 3大专业策略
- ✅ **回测引擎**: 13项性能指标
- ✅ **关键修复**: 品种识别算法优化

### 📈 **v2.3.x** (2025-09-28)
- v2.3.2: 前端技术指标图表功能
- v2.3.1: 品种识别算法修复  
- v2.3.0: 策略库系统实现

### 🔧 **v2.2.0** (2025-09-28)
- 技术指标计算引擎

### 🚀 **v2.1.0** (2025-09-28)  
- 品种扩展: 13→32个品种

### 🎯 **v2.0.0** (2024)
- 基础框架和核心功能

## 🤝 贡献指南

1. **Fork** 项目
2. **创建特性分支** (`git checkout -b feature/amazing-feature`)
3. **提交更改** (`git commit -m 'Add amazing feature'`)
4. **推送到分支** (`git push origin feature/amazing-feature`)  
5. **开启 Pull Request**

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## ⚠️ 免责声明

本软件仅供学习和研究使用，不构成投资建议。使用本软件进行实盘交易的任何损失由用户自行承担。

## 🙏 致谢

- [VN.PY](https://github.com/vnpy/vnpy) - 优秀的量化交易框架
- [AKShare](https://github.com/akfamily/akshare) - 专业的金融数据接口
- [Chart.js](https://www.chartjs.org/) - 强大的图表库
- [Flask](https://flask.palletsprojects.com/) - 轻量级Web框架

---

## 🚀 立即体验

🌐 **在线访问**: https://5035-iqwt7pakk30j34exwvp41-6532622b.e2b.dev

📧 如有问题或建议，请创建 **Issue** 或 **Pull Request**。

**⭐ 如果这个项目对您有帮助，请给个Star支持！**