# ML Adaptive SuperTrend 指标实现

## 概述
本项目将Pine Script的Machine Learning Adaptive SuperTrend指标转换为Python实现，并使用QQQ数据进行测试和可视化。

## 功能特性
- 🔧 Pine Script到Python的精确转换
- 🤖 机器学习自适应参数调整
- 📊 完整的技术指标计算
- 📈 交互式K线图可视化
- 📋 详细的性能统计分析
- 💾 结果数据导出功能

## 项目结构
```
ml_supertrend/
├── ML_Adaptive_SuperTrend.ipynb  # 主要的Jupyter Notebook
├── requirements.txt              # 依赖包列表
├── README.md                     # 项目说明
└── [生成的输出文件]
    ├── QQQ_ML_SuperTrend_Results.csv   # 完整计算结果
    └── QQQ_ML_SuperTrend_Signals.csv   # 交易信号数据
```

## 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 启动Jupyter Notebook
```bash
cd /home/user/webapp/notebooks/ml_supertrend
jupyter notebook ML_Adaptive_SuperTrend.ipynb
```

### 2. 提供Pine Script代码
- 在Notebook的第2节中粘贴您的Pine Script源代码
- 运行后续单元格进行转换和分析

### 3. 查看结果
- 交互式图表显示价格和指标
- 详细的性能统计分析
- 导出的CSV数据文件

## 指标组件

### 核心算法
1. **ATR计算**: 平均真实波幅计算
2. **机器学习特征**: RSI, MACD, 布林带等技术指标
3. **自适应乘数**: 基于ML模型的动态参数调整
4. **SuperTrend计算**: 最终趋势指标生成

### 机器学习特性
- 特征工程：多种技术指标组合
- 随机森林模型：预测最优乘数
- 自适应调整：根据市场环境动态优化
- 风险控制：参数范围限制

### 可视化功能
- K线图 + SuperTrend叠加
- 趋势背景色显示
- 自适应乘数变化图
- ATR波动率分析图

## 数据说明
- **数据源**: Yahoo Finance (yfinance)
- **测试标的**: QQQ ETF
- **时间范围**: 2023-2025年
- **数据频率**: 日线数据

## 输出文件说明

### QQQ_ML_SuperTrend_Results.csv
包含完整的计算结果：
- 价格数据 (open, high, low, close, volume)
- SuperTrend指标 (supertrend, supertrend_upper, supertrend_lower)
- 趋势信号 (trend)
- 自适应参数 (adaptive_multiplier)
- ATR数值

### QQQ_ML_SuperTrend_Signals.csv
包含交易信号：
- 买入/卖出信号时间点
- 信号变化类型
- 当时的价格和指标值

## 性能指标
Notebook会自动计算并显示：
- 趋势准确性统计
- 交易信号次数
- 简单回测结果
- 胜率和平均收益

## 技术要求
- Python 3.8+
- pandas 2.0+
- numpy 1.20+
- 其他依赖见requirements.txt

## 注意事项
1. 确保提供有效的Pine Script源代码
2. 网络连接正常以获取股票数据
3. 计算可能需要一些时间，请耐心等待
4. 结果仅供学习和研究，不构成投资建议

## 下一步计划
- ✅ 基础框架完成
- ⏳ 等待Pine Script代码输入
- 📋 精确算法转换
- 🔧 参数优化调整
- 📊 结果验证分析

---
**免责声明**: 本项目仅供学习和研究使用，不构成任何投资建议。