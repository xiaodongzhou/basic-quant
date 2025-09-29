#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Demo Server - 项目验收演示服务器

提供交互式Web界面展示期货量化交易系统核心功能：
- 实时数据监控
- 策略执行展示  
- 回测结果可视化
- 配置管理界面
"""

import sys
import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any
import logging

# Web框架
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import pandas as pd
import numpy as np
import akshare as ak

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入核心模块
from core.backtest_engine import BacktestEngine, BacktestConfig, run_portfolio_backtest
from core.strategy_portfolio_config import PortfolioConfig, StrategyConfig, StrategyAllocation, ConfigManager
from core.multi_strategy_manager import StrategyAllocationMethod
from core.technical_indicators import TechnicalIndicators, DEFAULT_INDICATOR_PARAMS, get_signal_analysis
from core.strategy_library import strategy_library, format_signals_for_api, format_backtest_metrics_for_api
from core.data_types import TradingSignalAction

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 时区配置 - 东8区（北京时间）
BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    """获取东8区当前时间"""
    return datetime.now(BEIJING_TZ)

def beijing_time(dt=None):
    """转换为东8区时间"""
    if dt is None:
        return beijing_now()
    if dt.tzinfo is None:
        # 如果没有时区信息，假设为UTC时间
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BEIJING_TZ)

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局数据存储
demo_data = {
    'market_data': {},
    'strategies': {},
    'portfolio': {},
    'backtest_results': {},
    'positions': {},
    'trades': [],
    'system_status': 'ready'
}


class DemoDataGenerator:
    """演示数据生成器"""
    
    def __init__(self):
        self.symbols = ['rb2405', 'i2405', 'j2405', 'hc2405']
        self.base_prices = {'rb2405': 3500, 'i2405': 800, 'j2405': 2000, 'hc2405': 3200}
        self.current_prices = self.base_prices.copy()
        self.last_update = beijing_now()
        self.trade_counter = 0
        self.last_trade_time = datetime.now()
        
        # 初始化持仓数据
        self._init_positions()
        self._init_trades()
        
    def generate_market_tick(self):
        """生成模拟market tick数据"""
        
        now = datetime.now()
        ticks = {}
        
        for symbol in self.symbols:
            # 生成随机价格波动
            change_pct = np.random.normal(0, 0.002)  # 0.2%标准波动
            new_price = self.current_prices[symbol] * (1 + change_pct)
            
            # 确保价格在合理范围内
            base_price = self.base_prices[symbol]
            new_price = max(base_price * 0.8, min(base_price * 1.2, new_price))
            
            self.current_prices[symbol] = new_price
            
            # 生成完整tick数据
            tick = {
                'symbol': symbol,
                'timestamp': now.isoformat(),
                'last_price': round(new_price, 1),
                'volume': np.random.randint(100, 1000),
                'bid_price': round(new_price - np.random.uniform(0.5, 2.0), 1),
                'ask_price': round(new_price + np.random.uniform(0.5, 2.0), 1),
                'change': round((new_price / base_price - 1) * 100, 2),
                'turnover': round(new_price * np.random.randint(100, 1000), 0)
            }
            
            ticks[symbol] = tick
            
        return ticks
    
    def generate_strategy_status(self):
        """生成策略状态数据"""
        
        strategies = {
            'ma_fast_rb': {
                'name': 'MA快速-螺纹钢',
                'symbol': 'rb2405',
                'status': 'running',
                'position': np.random.randint(-5, 6),
                'pnl': np.random.uniform(-5000, 8000),
                'signals': ['golden_cross' if np.random.random() > 0.8 else 'hold'],
                'parameters': {'fast': 5, 'slow': 20},
                'allocated_capital': 800000
            },
            'ma_slow_rb': {
                'name': 'MA慢速-螺纹钢', 
                'symbol': 'rb2405',
                'status': 'running',
                'position': np.random.randint(-3, 4),
                'pnl': np.random.uniform(-3000, 5000),
                'signals': ['death_cross' if np.random.random() > 0.9 else 'hold'],
                'parameters': {'fast': 10, 'slow': 50},
                'allocated_capital': 500000
            },
            'ma_iron_ore': {
                'name': 'MA策略-铁矿石',
                'symbol': 'i2405', 
                'status': 'running',
                'position': np.random.randint(-4, 5),
                'pnl': np.random.uniform(-4000, 6000),
                'signals': ['buy' if np.random.random() > 0.85 else 'hold'],
                'parameters': {'fast': 8, 'slow': 25},
                'allocated_capital': 500000
            },
            'ma_coke': {
                'name': 'MA策略-焦炭',
                'symbol': 'j2405',
                'status': 'paused',
                'position': 0,
                'pnl': np.random.uniform(-2000, 3000),
                'signals': ['hold'],
                'parameters': {'fast': 12, 'slow': 30},
                'allocated_capital': 200000
            }
        }
        
        return strategies
    
    def _init_positions(self):
        """初始化持仓数据"""
        positions = {
            'rb2405_long': {
                'symbol': 'rb2405',
                'direction': 'long',
                'quantity': np.random.randint(8, 15),
                'avg_price': 3485.5,
                'current_price': self.current_prices['rb2405'],
                'market_value': 0,
                'unrealized_pnl': 0,
                'strategy': 'MA快速-螺纹钢',
                'open_time': (beijing_now() - timedelta(hours=2, minutes=15)).isoformat()
            },
            'i2405_long': {
                'symbol': 'i2405', 
                'direction': 'long',
                'quantity': np.random.randint(15, 25),
                'avg_price': 795.2,
                'current_price': self.current_prices['i2405'],
                'market_value': 0,
                'unrealized_pnl': 0,
                'strategy': 'MA策略-铁矿石',
                'open_time': (beijing_now() - timedelta(hours=1, minutes=45)).isoformat()
            },
            'j2405_short': {
                'symbol': 'j2405',
                'direction': 'short', 
                'quantity': np.random.randint(5, 12),
                'avg_price': 2015.8,
                'current_price': self.current_prices['j2405'],
                'market_value': 0,
                'unrealized_pnl': 0,
                'strategy': 'MA策略-焦炭',
                'open_time': (beijing_now() - timedelta(minutes=30)).isoformat()
            }
        }
        
        # 计算初始市值和盈亏
        for pos_id, pos in positions.items():
            self._update_position_pnl(pos)
            
        demo_data['positions'] = positions
    
    def _init_trades(self):
        """初始化成交记录"""
        trades = []
        base_time = beijing_now() - timedelta(hours=6)
        
        # 生成历史成交记录
        trade_data = [
            ('rb2405', 'long', 10, 3478.5, 3485.5, 'open', 'MA快速-螺纹钢'),
            ('rb2405', 'long', 5, 3462.2, 3475.8, 'close', 'MA慢速-螺纹钢'),
            ('i2405', 'long', 20, 792.5, 795.2, 'open', 'MA策略-铁矿石'),
            ('hc2405', 'short', 8, 3215.8, 3208.4, 'close', 'MA策略-热卷'),
            ('j2405', 'short', 6, 2018.9, 2015.8, 'open', 'MA策略-焦炭'),
            ('rb2405', 'long', 3, 3445.2, 3456.7, 'close', 'MA快速-螺纹钢'),
            ('i2405', 'short', 15, 798.1, 795.8, 'close', 'MA策略-铁矿石'),
            ('rb2405', 'short', 8, 3492.3, 3487.9, 'open', 'MA快速-螺纹钢'),
            ('j2405', 'long', 12, 2005.6, 2012.4, 'close', 'MA策略-焦炭'),
            ('hc2405', 'long', 6, 3198.7, 3205.2, 'open', 'MA策略-热卷'),
            ('rb2405', 'long', 9, 3455.8, 3461.3, 'close', 'MA慢速-螺纹钢'),
            ('i2405', 'long', 18, 789.4, 793.7, 'open', 'MA策略-铁矿石'),
            ('j2405', 'short', 7, 2021.5, 2018.2, 'close', 'MA策略-焦炭'),
            ('rb2405', 'short', 4, 3498.6, 3495.1, 'close', 'MA快速-螺纹钢'),
            ('hc2405', 'short', 11, 3212.9, 3209.5, 'close', 'MA策略-热卷'),
            ('i2405', 'short', 13, 801.3, 798.9, 'open', 'MA策略-铁矿石'),
            ('rb2405', 'long', 7, 3467.2, 3472.8, 'open', 'MA慢速-螺纹钢'),
            ('j2405', 'long', 9, 2014.7, 2019.3, 'close', 'MA策略-焦炭'),
            ('hc2405', 'long', 5, 3201.4, 3206.8, 'close', 'MA策略-热卷'),
            ('rb2405', 'short', 14, 3489.1, 3484.6, 'open', 'MA快速-螺纹钢'),
        ]
        
        for i, (symbol, direction, qty, open_price, close_price, action, strategy) in enumerate(trade_data):
            trade_time = base_time + timedelta(minutes=i*25)
            
            if action == 'close':
                pnl = (close_price - open_price) * qty if direction == 'long' else (open_price - close_price) * qty
            else:
                pnl = None
                
            trade = {
                'id': f'T{1000 + i}',
                'timestamp': trade_time.isoformat(),
                'symbol': symbol,
                'direction': direction,
                'action': action,
                'quantity': qty,
                'price': close_price if action == 'close' else open_price,
                'amount': (close_price if action == 'close' else open_price) * qty,
                'pnl': pnl,
                'commission': round(open_price * qty * 0.0002, 2),
                'strategy': strategy,
                'status': 'filled'
            }
            trades.append(trade)
        
        demo_data['trades'] = trades
        self.trade_counter = len(trades)
    
    def _update_position_pnl(self, position):
        """更新持仓盈亏"""
        current_price = self.current_prices[position['symbol']]
        position['current_price'] = current_price
        position['market_value'] = current_price * position['quantity']
        
        if position['direction'] == 'long':
            position['unrealized_pnl'] = (current_price - position['avg_price']) * position['quantity']
        else:
            position['unrealized_pnl'] = (position['avg_price'] - current_price) * position['quantity']
    
    def update_positions(self):
        """更新所有持仓数据"""
        positions = demo_data.get('positions', {})
        
        for pos_id, position in positions.items():
            self._update_position_pnl(position)
            
        return positions
    
    def generate_new_trade(self):
        """随机生成新的成交记录"""
        # 30%概率生成新交易
        if np.random.random() > 0.3:
            return None
            
        # 随机选择交易参数
        symbol = np.random.choice(self.symbols)
        direction = np.random.choice(['long', 'short'])
        action = np.random.choice(['open', 'close'], p=[0.6, 0.4])
        quantity = np.random.randint(3, 20)
        price = self.current_prices[symbol] + np.random.uniform(-5, 5)
        
        strategies = {
            'rb2405': 'MA快速-螺纹钢',
            'i2405': 'MA策略-铁矿石', 
            'j2405': 'MA策略-焦炭',
            'hc2405': 'MA策略-热卷'
        }
        
        self.trade_counter += 1
        
        # 计算盈亏（如果是平仓）
        pnl = None
        if action == 'close':
            # 模拟盈亏
            base_pnl = np.random.uniform(-200, 800) * quantity
            pnl = round(base_pnl, 2)
        
        trade = {
            'id': f'T{1000 + self.trade_counter}',
            'timestamp': beijing_now().isoformat(),
            'symbol': symbol,
            'direction': direction,
            'action': action, 
            'quantity': quantity,
            'price': round(price, 1),
            'amount': round(price * quantity, 2),
            'pnl': pnl,
            'commission': round(price * quantity * 0.0002, 2),
            'strategy': strategies[symbol],
            'status': 'filled'
        }
        
        # 添加到交易记录
        trades = demo_data.get('trades', [])
        trades.append(trade)
        
        # 保持最近50笔交易
        if len(trades) > 50:
            trades = trades[-50:]
        
        demo_data['trades'] = trades
        return trade


# 创建数据生成器
data_generator = DemoDataGenerator()


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/system/status')
def system_status():
    """获取系统状态"""
    
    status = {
        'timestamp': beijing_now().isoformat(),
        'system_status': demo_data['system_status'],
        'total_strategies': 4,
        'active_strategies': 3,
        'total_capital': 2000000,
        'used_capital': 1850000,
        'available_capital': 150000,
        'total_pnl': sum(s.get('pnl', 0) for s in demo_data.get('strategies', {}).values()),
        'daily_trades': np.random.randint(15, 45)
    }
    
    return jsonify(status)


@app.route('/api/market/data')
def market_data():
    """获取市场数据"""
    
    ticks = data_generator.generate_market_tick()
    demo_data['market_data'] = ticks
    
    return jsonify({
        'timestamp': beijing_now().isoformat(),
        'data': ticks
    })


@app.route('/api/strategies/status')
def strategies_status():
    """获取策略状态"""
    
    strategies = data_generator.generate_strategy_status()
    demo_data['strategies'] = strategies
    
    return jsonify({
        'timestamp': beijing_now().isoformat(),
        'strategies': strategies
    })


@app.route('/api/backtest/run', methods=['POST'])
def run_backtest_api():
    """运行回测API"""
    
    try:
        # 解析请求参数
        params = request.get_json()
        
        # 创建回测配置
        backtest_config = BacktestConfig(
            start_date=datetime.strptime(params.get('start_date', '2024-01-01'), '%Y-%m-%d'),
            end_date=datetime.strptime(params.get('end_date', '2024-03-31'), '%Y-%m-%d'),
            initial_capital=float(params.get('initial_capital', 1000000)),
            symbols=params.get('symbols', ['rb2405']),
            data_frequency=params.get('frequency', '1h')
        )
        
        # 创建投资组合配置
        portfolio_config = PortfolioConfig(
            portfolio_name="demo_backtest",
            total_capital=backtest_config.initial_capital,
            allocation_method="equal"
        )
        
        # 添加策略
        strategy = StrategyConfig(
            strategy_name="demo_ma",
            strategy_class="MAStrategy", 
            strategy_module="strategies.ma_strategy",
            parameters={
                "fast_period": params.get('fast_period', 5),
                "slow_period": params.get('slow_period', 20)
            }
        )
        portfolio_config.strategies = [strategy]
        
        # 添加分配
        allocation = StrategyAllocation(
            strategy_name="demo_ma",
            allocation_amount=backtest_config.initial_capital,
            allocation_ratio=1.0,
            max_position_ratio=0.8,
            risk_budget=0.02
        )
        portfolio_config.strategy_allocations = [allocation]
        
        # 运行回测
        results = run_portfolio_backtest(portfolio_config, backtest_config)
        
        # 保存结果
        demo_data['backtest_results'] = results
        
        return jsonify({
            'success': True,
            'message': '回测完成',
            'results': {
                'total_return': results.get('performance_metrics', {}).get('total_return', 0),
                'sharpe_ratio': results.get('performance_metrics', {}).get('sharpe_ratio', 0),
                'max_drawdown': results.get('performance_metrics', {}).get('max_drawdown', 0),
                'total_trades': results.get('performance_metrics', {}).get('total_trades', 0),
                'portfolio_values': results.get('portfolio_values', [])[-50:],  # 最后50个点
            }
        })
        
    except Exception as e:
        logger.error(f"回测执行失败: {e}")
        return jsonify({
            'success': False,
            'message': f'回测失败: {str(e)}'
        }), 500


@app.route('/api/backtest/chart_data')
def get_backtest_chart_data():
    """获取回测分析图表数据"""
    
    try:
        # 生成模拟的K线数据和交易信号
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 3, 31)
        
        # 生成时间序列（每小时）
        time_series = pd.date_range(start=start_date, end=end_date, freq='H')
        
        # 生成模拟K线数据
        np.random.seed(42)  # 固定随机种子保证一致性
        
        initial_price = 3500
        prices = []
        current_price = initial_price
        
        kline_data = []
        trade_signals = []
        portfolio_values = []
        
        # 策略状态
        position = 0  # 0: 空仓, 1: 多头, -1: 空头
        entry_price = 0
        initial_capital = 1000000
        current_capital = initial_capital
        
        # MA参数
        fast_ma = 5
        slow_ma = 20
        price_history = []
        
        for i, timestamp in enumerate(time_series):
            # 生成价格走势（模拟期货价格波动）
            if i == 0:
                price = initial_price
            else:
                # 添加趋势和随机波动
                trend = 0.001 if i < len(time_series) * 0.6 else -0.0005
                volatility = np.random.normal(0, 0.01)
                price = current_price * (1 + trend + volatility)
                price = max(price, initial_price * 0.8)  # 设置价格下限
                price = min(price, initial_price * 1.3)  # 设置价格上限
            
            current_price = price
            price_history.append(price)
            
            # 生成OHLC数据
            high = price * (1 + abs(np.random.normal(0, 0.005)))
            low = price * (1 - abs(np.random.normal(0, 0.005)))
            open_price = price + np.random.normal(0, price * 0.003)
            close_price = price
            
            kline_data.append({
                'timestamp': timestamp.isoformat(),
                'time': timestamp.strftime('%Y-%m-%d %H:%M'),
                'open': round(open_price, 1),
                'high': round(high, 1),
                'low': round(low, 1),
                'close': round(close_price, 1),
                'volume': np.random.randint(1000, 5000)
            })
            
            # 计算移动平均线
            if len(price_history) >= slow_ma:
                fast_ma_value = np.mean(price_history[-fast_ma:])
                slow_ma_value = np.mean(price_history[-slow_ma:])
                
                # 生成交易信号
                prev_fast = np.mean(price_history[-fast_ma-1:-1]) if len(price_history) > fast_ma else fast_ma_value
                prev_slow = np.mean(price_history[-slow_ma-1:-1]) if len(price_history) > slow_ma else slow_ma_value
                
                # 金叉开多仓
                if prev_fast <= prev_slow and fast_ma_value > slow_ma_value and position <= 0:
                    if position == -1:  # 先平空仓
                        pnl = (entry_price - close_price) * 10  # 10手
                        current_capital += pnl
                        trade_signals.append({
                            'timestamp': timestamp.isoformat(),
                            'time': timestamp.strftime('%Y-%m-%d %H:%M'),
                            'type': 'close_short',
                            'price': close_price,
                            'pnl': pnl
                        })
                    
                    # 开多仓
                    position = 1
                    entry_price = close_price
                    trade_signals.append({
                        'timestamp': timestamp.isoformat(),
                        'time': timestamp.strftime('%Y-%m-%d %H:%M'),
                        'type': 'open_long',
                        'price': close_price,
                        'pnl': 0
                    })
                
                # 死叉开空仓
                elif prev_fast >= prev_slow and fast_ma_value < slow_ma_value and position >= 0:
                    if position == 1:  # 先平多仓
                        pnl = (close_price - entry_price) * 10  # 10手
                        current_capital += pnl
                        trade_signals.append({
                            'timestamp': timestamp.isoformat(),
                            'time': timestamp.strftime('%Y-%m-%d %H:%M'),
                            'type': 'close_long',
                            'price': close_price,
                            'pnl': pnl
                        })
                    
                    # 开空仓
                    position = -1
                    entry_price = close_price
                    trade_signals.append({
                        'timestamp': timestamp.isoformat(),
                        'time': timestamp.strftime('%Y-%m-%d %H:%M'),
                        'type': 'open_short',
                        'price': close_price,
                        'pnl': 0
                    })
            
            # 计算当前组合价值
            unrealized_pnl = 0
            if position != 0:
                if position == 1:  # 多头
                    unrealized_pnl = (close_price - entry_price) * 10
                else:  # 空头
                    unrealized_pnl = (entry_price - close_price) * 10
            
            portfolio_value = current_capital + unrealized_pnl
            portfolio_values.append({
                'timestamp': timestamp.isoformat(),
                'time': timestamp.strftime('%Y-%m-%d %H:%M'),
                'value': portfolio_value,
                'return': (portfolio_value - initial_capital) / initial_capital * 100
            })
        
        # 计算性能指标
        returns = [pv['return'] for pv in portfolio_values]
        final_return = returns[-1] if returns else 0
        max_return = max(returns) if returns else 0
        min_return = min(returns) if returns else 0
        max_drawdown = max_return - min_return
        
        return jsonify({
            'timestamp': beijing_now().isoformat(),
            'kline_data': kline_data,
            'trade_signals': trade_signals,
            'portfolio_values': portfolio_values,
            'performance_metrics': {
                'total_return': final_return,
                'max_drawdown': max_drawdown,
                'total_trades': len([t for t in trade_signals if 'open' in t['type']]),
                'win_rate': 65.4,  # 模拟胜率
                'profit_trades': len([t for t in trade_signals if t.get('pnl', 0) > 0]),
                'loss_trades': len([t for t in trade_signals if t.get('pnl', 0) < 0])
            }
        })
        
    except Exception as e:
        logger.error(f"获取回测图表数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取数据失败: {str(e)}'
        }), 500


@app.route('/api/positions')
def get_positions():
    """获取实时持仓信息"""
    
    positions = data_generator.update_positions()
    
    # 格式化持仓数据
    formatted_positions = []
    total_market_value = 0
    total_unrealized_pnl = 0
    
    for pos_id, pos in positions.items():
        formatted_pos = {
            'id': pos_id,
            'symbol': pos['symbol'],
            'direction': pos['direction'],
            'quantity': pos['quantity'],
            'avg_price': pos['avg_price'],
            'current_price': pos['current_price'],
            'market_value': pos['market_value'],
            'unrealized_pnl': pos['unrealized_pnl'],
            'pnl_ratio': (pos['unrealized_pnl'] / (pos['avg_price'] * pos['quantity'])) * 100 if pos['quantity'] > 0 else 0,
            'strategy': pos['strategy'],
            'open_time': pos['open_time'].isoformat(),
            'hold_duration': str(beijing_now() - pos['open_time']).split('.')[0]
        }
        formatted_positions.append(formatted_pos)
        total_market_value += pos['market_value']
        total_unrealized_pnl += pos['unrealized_pnl']
    
    return jsonify({
        'timestamp': beijing_now().isoformat(),
        'current_datetime': beijing_now().strftime('%Y-%m-%d %H:%M:%S'),
        'positions': formatted_positions,
        'summary': {
            'total_positions': len(formatted_positions),
            'total_market_value': total_market_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'pnl_ratio': (total_unrealized_pnl / total_market_value) * 100 if total_market_value > 0 else 0
        }
    })


@app.route('/api/trades')
def get_trades():
    """获取成交记录"""
    
    # 获取分页参数
    page = int(request.args.get('page', 1))  # 页码，从1开始
    per_page = int(request.args.get('per_page', 10))  # 每页条数，默认10条
    
    # 可能生成新交易
    new_trade = data_generator.generate_new_trade()
    
    trades = demo_data.get('trades', [])
    total_trades = len(trades)
    
    # 计算分页
    total_pages = (total_trades + per_page - 1) // per_page  # 向上取整
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_trades)
    
    # 获取当前页的交易（倒序显示，最新的在前面）
    reversed_trades = list(reversed(trades))
    page_trades = reversed_trades[start_idx:end_idx]
    
    # 格式化交易数据
    formatted_trades = []
    for trade in page_trades:
        formatted_trade = {
            'id': trade['id'],
            'timestamp': trade['timestamp'].isoformat(),
            'time_str': trade['timestamp'].strftime('%H:%M:%S'),
            'datetime_str': trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'date_str': trade['timestamp'].strftime('%m-%d'),
            'symbol': trade['symbol'],
            'direction': trade['direction'],
            'action': trade['action'],
            'quantity': trade['quantity'],
            'price': trade['price'],
            'amount': trade['amount'],
            'pnl': trade['pnl'],
            'commission': trade['commission'],
            'strategy': trade['strategy'],
            'status': trade['status']
        }
        formatted_trades.append(formatted_trade)
    
    # 统计信息
    today_trades = [t for t in trades if t['timestamp'].date() == beijing_now().date()]
    today_pnl = sum(t.get('pnl', 0) for t in today_trades if t.get('pnl') is not None)
    total_commission = sum(t.get('commission', 0) for t in today_trades)
    
    return jsonify({
        'timestamp': beijing_now().isoformat(),
        'trades': formatted_trades,
        'pagination': {
            'current_page': page,
            'per_page': per_page,
            'total_trades': total_trades,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_page': page - 1 if page > 1 else None,
            'next_page': page + 1 if page < total_pages else None
        },
        'summary': {
            'today_trades': len(today_trades),
            'today_pnl': today_pnl,
            'total_commission': total_commission,
            'new_trade': new_trade
        }
    })


@app.route('/api/futures/kline_data')
def get_futures_kline_data():
    """获取期货K线数据 - 使用AKShare获取真实数据"""
    
    try:
        # 获取请求参数
        symbol = request.args.get('symbol', 'rb2405')  # 合约代码
        period = request.args.get('period', '1h')      # 周期
        limit = int(request.args.get('limit', 48))     # 数据条数
        
        # 动态映射合约代码到AKShare格式（基于品种识别）
        def get_akshare_symbol(contract_code):
            """根据合约代码获取对应的AKShare主力合约符号"""
            contract_lower = contract_code.lower()
            
            # 品种到AKShare主力合约的映射
            variety_to_akshare = {
                # 商品期货 - 黑色系
                'rb': 'RB0',    # 螺纹钢主力
                'i': 'I0',      # 铁矿石主力
                'j': 'J0',      # 焦炭主力
                'jm': 'JM0',    # 焦煤主力
                'hc': 'HC0',    # 热卷主力
                
                # 商品期货 - 有色金属
                'cu': 'CU0',    # 沪铜主力  
                'al': 'AL0',    # 沪铝主力
                'ni': 'NI0',    # 沪镍主力
                'zn': 'ZN0',    # 沪锌主力
                'sn': 'SN0',    # 沪锡主力
                'pb': 'PB0',    # 沪铅主力
                
                # 贵金属
                'ag': 'AG0',    # 沪银主力
                'au': 'AU0',    # 沪金主力
                
                # 股指期货 (新增)
                'if': 'IF0',    # 沪深300指数期货主力
                'ic': 'IC0',    # 中证500指数期货主力
                'ih': 'IH0',    # 上证50指数期货主力
                'im': 'IM0',    # 中证1000指数期货主力
                
                # 农产品期货 (新增)
                'a': 'A0',      # 大豆1号主力
                'b': 'B0',      # 大豆2号主力
                'c': 'C0',      # 玉米主力
                'm': 'M0',      # 豆粕主力
                'y': 'Y0',      # 豆油主力
                'p': 'P0',      # 棕榈油主力
                'sr': 'SR0',    # 白糖主力
                'cf': 'CF0',    # 棉花主力
                'rm': 'RM0',    # 菜粕主力
                'oi': 'OI0',    # 菜籽油主力
                
                # 能源化工 (新增) 
                'sc': 'SC0',    # 原油主力
                'pta': 'PTA0',  # PTA主力
                'ma': 'MA0',    # 甲醇主力
                'eg': 'EG0',    # 乙二醇主力
                'pp': 'PP0',    # 聚丙烯主力
                'v': 'V0',      # PVC主力
                'l': 'L0',      # 聚乙烯主力
                'bu': 'BU0',    # 沥青主力
                'fu': 'FU0',    # 燃料油主力
            }
            
            # 从合约代码中提取品种（字母部分）
            import re
            variety_match = re.match(r'^([a-zA-Z]+)', contract_code)
            if variety_match:
                variety = variety_match.group(1).lower()
                akshare_symbol = variety_to_akshare.get(variety, 'RB0')
                print(f"合约映射: {contract_code} -> 品种: {variety} -> AKShare: {akshare_symbol}")
                return akshare_symbol
            else:
                print(f"无法识别合约品种: {contract_code}，使用默认螺纹钢")
                return 'RB0'
        
        # 映射前端周期到AKShare格式
        period_map = {
            '5m': '5',
            '15m': '15', 
            '30m': '30',
            '1h': '60',
            '1d': 'daily'
        }
        
        akshare_symbol = get_akshare_symbol(symbol)
        akshare_period = period_map.get(period, '60')
        
        print(f"获取期货数据: symbol={symbol}({akshare_symbol}), period={period}({akshare_period}), limit={limit}")
        
        # 获取AKShare数据
        if period == '1d':
            # 日线数据使用不同的接口
            df = ak.futures_zh_daily_sina(symbol=akshare_symbol)
        else:
            # 分钟级数据
            df = ak.futures_zh_minute_sina(symbol=akshare_symbol, period=akshare_period)
        
        if df is None or len(df) == 0:
            raise Exception("未获取到数据")
            
        # 取最新的limit条数据
        df = df.tail(limit).copy()
        
        # 标准化数据格式
        kline_data = []
        for _, row in df.iterrows():
            # 确保时间格式正确
            if isinstance(row['datetime'], str):
                timestamp = pd.to_datetime(row['datetime'])
            else:
                timestamp = row['datetime']
                
            kline_item = {
                'timestamp': timestamp.isoformat(),
                'time': timestamp.strftime('%Y-%m-%d %H:%M'),
                'open': float(row['open']),
                'high': float(row['high']), 
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['volume']) if pd.notna(row['volume']) else 0
            }
            kline_data.append(kline_item)
        
        return jsonify({
            'success': True,
            'timestamp': beijing_now().isoformat(),
            'data': {
                'symbol': symbol,
                'period': period,
                'kline_data': kline_data,
                'data_source': 'akshare',
                'count': len(kline_data)
            }
        })
        
    except Exception as e:
        print(f"获取期货数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取期货数据失败: {str(e)}',
            'timestamp': beijing_now().isoformat()
        }), 500


@app.route('/api/backtest/historical_data')
def get_historical_data():
    """获取回测历史数据 - 使用AKShare获取真实历史数据"""
    
    try:
        # 获取请求参数
        symbol = request.args.get('symbol', 'rb2405')     # 合约代码
        period = request.args.get('period', '1h')         # 周期
        start_date = request.args.get('start_date')       # 开始日期 YYYY-MM-DD
        end_date = request.args.get('end_date')           # 结束日期 YYYY-MM-DD
        
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'message': '缺少必要的日期参数',
                'timestamp': beijing_now().isoformat()
            }), 400
        
        # 动态映射合约代码到AKShare格式（基于品种识别）
        def get_akshare_symbol(contract_code):
            """根据合约代码获取对应的AKShare主力合约符号"""
            contract_lower = contract_code.lower()
            
            # 品种到AKShare主力合约的映射
            variety_to_akshare = {
                # 商品期货 - 黑色系
                'rb': 'RB0',    # 螺纹钢主力
                'i': 'I0',      # 铁矿石主力
                'j': 'J0',      # 焦炭主力
                'jm': 'JM0',    # 焦煤主力
                'hc': 'HC0',    # 热卷主力
                
                # 商品期货 - 有色金属
                'cu': 'CU0',    # 沪铜主力  
                'al': 'AL0',    # 沪铝主力
                'ni': 'NI0',    # 沪镍主力
                'zn': 'ZN0',    # 沪锌主力
                'sn': 'SN0',    # 沪锡主力
                'pb': 'PB0',    # 沪铅主力
                
                # 贵金属
                'ag': 'AG0',    # 沪银主力
                'au': 'AU0',    # 沪金主力
                
                # 股指期货 (新增)
                'if': 'IF0',    # 沪深300指数期货主力
                'ic': 'IC0',    # 中证500指数期货主力
                'ih': 'IH0',    # 上证50指数期货主力
                'im': 'IM0',    # 中证1000指数期货主力
                
                # 农产品期货 (新增)
                'a': 'A0',      # 大豆1号主力
                'b': 'B0',      # 大豆2号主力
                'c': 'C0',      # 玉米主力
                'm': 'M0',      # 豆粕主力
                'y': 'Y0',      # 豆油主力
                'p': 'P0',      # 棕榈油主力
                'sr': 'SR0',    # 白糖主力
                'cf': 'CF0',    # 棉花主力
                'rm': 'RM0',    # 菜粕主力
                'oi': 'OI0',    # 菜籽油主力
                
                # 能源化工 (新增) 
                'sc': 'SC0',    # 原油主力
                'pta': 'PTA0',  # PTA主力
                'ma': 'MA0',    # 甲醇主力
                'eg': 'EG0',    # 乙二醇主力
                'pp': 'PP0',    # 聚丙烯主力
                'v': 'V0',      # PVC主力
                'l': 'L0',      # 聚乙烯主力
                'bu': 'BU0',    # 沥青主力
                'fu': 'FU0',    # 燃料油主力
            }
            
            # 从合约代码中提取品种（字母部分）
            import re
            variety_match = re.match(r'^([a-zA-Z]+)', contract_code)
            if variety_match:
                variety = variety_match.group(1).lower()
                akshare_symbol = variety_to_akshare.get(variety, 'RB0')
                print(f"历史数据合约映射: {contract_code} -> 品种: {variety} -> AKShare: {akshare_symbol}")
                return akshare_symbol
            else:
                print(f"无法识别合约品种: {contract_code}，使用默认螺纹钢")
                return 'RB0'
        
        # 映射前端周期到AKShare格式
        period_map = {
            '5m': '5',
            '15m': '15', 
            '30m': '30',
            '1h': '60',
            '1d': 'daily'
        }
        
        akshare_symbol = get_akshare_symbol(symbol)
        akshare_period = period_map.get(period, '60')
        
        print(f"获取历史数据: symbol={symbol}({akshare_symbol}), period={period}({akshare_period}), {start_date} to {end_date}")
        
        # 获取AKShare历史数据
        if period == '1d':
            # 日线数据使用不同的接口
            df = ak.futures_zh_daily_sina(symbol=akshare_symbol)
        else:
            # 分钟级数据
            df = ak.futures_zh_minute_sina(symbol=akshare_symbol, period=akshare_period)
        
        if df is None or len(df) == 0:
            raise Exception("未获取到历史数据")
        
        # 过滤日期范围
        df['datetime'] = pd.to_datetime(df['datetime'])
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)  # 包含结束日期
        
        df_filtered = df[(df['datetime'] >= start_dt) & (df['datetime'] < end_dt)].copy()
        
        if len(df_filtered) == 0:
            # 如果指定日期范围没有数据，使用最新的数据
            df_filtered = df.tail(100).copy()
            print(f"指定日期范围无数据，使用最新100条记录")
        
        # 标准化数据格式
        historical_data = []
        trade_signals = []  # 模拟交易信号
        portfolio_values = []  # 模拟组合价值
        
        initial_capital = 1000000
        current_capital = initial_capital
        position = 0  # 0: 空仓, 1: 多头, -1: 空头
        
        for i, (_, row) in enumerate(df_filtered.iterrows()):
            # 确保时间格式正确
            if isinstance(row['datetime'], str):
                timestamp = pd.to_datetime(row['datetime'])
            else:
                timestamp = row['datetime']
            
            # OHLC数据
            ohlc_item = {
                'timestamp': timestamp.isoformat(),
                'time': timestamp.strftime('%Y-%m-%d %H:%M'),
                'open': float(row['open']),
                'high': float(row['high']), 
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['volume']) if pd.notna(row['volume']) else 0
            }
            historical_data.append(ohlc_item)
            
            # 模拟简单MA交叉策略信号（每10个数据点一个信号用于演示）
            if i > 0 and i % 10 == 0:
                signal_type = 'buy' if i % 20 == 0 else 'sell'
                price = float(row['close'])
                
                signal = {
                    'timestamp': timestamp.isoformat(),
                    'time': timestamp.strftime('%Y-%m-%d %H:%M'),
                    'type': signal_type,
                    'price': price,
                    'volume': 1  # 1手
                }
                trade_signals.append(signal)
                
                # 更新持仓和资金（简化计算）
                if signal_type == 'buy' and position <= 0:
                    position = 1
                    current_capital -= price * 1  # 买入1手
                elif signal_type == 'sell' and position >= 0:
                    position = -1  
                    current_capital += price * 1  # 卖出1手
            
            # 组合价值
            portfolio_value = current_capital + (position * float(row['close']))
            portfolio_values.append({
                'timestamp': timestamp.isoformat(),
                'time': timestamp.strftime('%Y-%m-%d %H:%M'),
                'value': portfolio_value,
                'return_pct': ((portfolio_value - initial_capital) / initial_capital) * 100
            })
        
        return jsonify({
            'success': True,
            'timestamp': beijing_now().isoformat(),
            'data': {
                'symbol': symbol,
                'period': period,
                'start_date': start_date,
                'end_date': end_date,
                'kline_data': historical_data,
                'trade_signals': trade_signals,
                'portfolio_values': portfolio_values,
                'data_source': 'akshare_historical',
                'count': len(historical_data)
            }
        })
        
    except Exception as e:
        print(f"获取历史数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取历史数据失败: {str(e)}',
            'timestamp': beijing_now().isoformat()
        }), 500


@app.route('/api/futures/contracts')
def get_futures_contracts():
    """获取期货合约列表 - 支持动态合约选择"""
    
    try:
        variety = request.args.get('variety', '')  # 品种筛选，如'rb', 'cu', 'al'
        
        print(f"获取期货合约列表: variety={variety}")
        
        # 获取所有合约信息
        df = ak.futures_fees_info()
        
        if df is None or len(df) == 0:
            raise Exception("未获取到合约数据")
        
        # 品种映射配置
        variety_config = {
            # 商品期货 - 黑色系
            'rb': {'name': '螺纹钢', 'exchange': 'SHFE'},
            'i': {'name': '铁矿石', 'exchange': 'DCE'},
            'j': {'name': '焦炭', 'exchange': 'DCE'},
            'jm': {'name': '焦煤', 'exchange': 'DCE'},
            'hc': {'name': '热卷', 'exchange': 'SHFE'},
            
            # 商品期货 - 有色金属
            'cu': {'name': '沪铜', 'exchange': 'SHFE'},
            'al': {'name': '沪铝', 'exchange': 'SHFE'},
            'ni': {'name': '沪镍', 'exchange': 'SHFE'},
            'zn': {'name': '沪锌', 'exchange': 'SHFE'},
            'sn': {'name': '沪锡', 'exchange': 'SHFE'},
            'pb': {'name': '沪铅', 'exchange': 'SHFE'},
            
            # 贵金属
            'ag': {'name': '沪银', 'exchange': 'SHFE'},
            'au': {'name': '沪金', 'exchange': 'SHFE'},
            
            # 股指期货 (新增)
            'if': {'name': '沪深300', 'exchange': 'CFFEX'},
            'ic': {'name': '中证500', 'exchange': 'CFFEX'},
            'ih': {'name': '上证50', 'exchange': 'CFFEX'},
            'im': {'name': '中证1000', 'exchange': 'CFFEX'},
            
            # 农产品期货 (新增)
            'a': {'name': '大豆1号', 'exchange': 'DCE'},
            'b': {'name': '大豆2号', 'exchange': 'DCE'},
            'c': {'name': '玉米', 'exchange': 'DCE'},
            'm': {'name': '豆粕', 'exchange': 'DCE'},
            'y': {'name': '豆油', 'exchange': 'DCE'},
            'p': {'name': '棕榈油', 'exchange': 'DCE'},
            'sr': {'name': '白糖', 'exchange': 'CZCE'},
            'cf': {'name': '棉花', 'exchange': 'CZCE'},
            'rm': {'name': '菜粕', 'exchange': 'CZCE'},
            'oi': {'name': '菜籽油', 'exchange': 'CZCE'},
            
            # 能源化工 (新增)
            'sc': {'name': '原油', 'exchange': 'INE'},
            'pta': {'name': 'PTA', 'exchange': 'CZCE'},
            'ma': {'name': '甲醇', 'exchange': 'CZCE'},
            'eg': {'name': '乙二醇', 'exchange': 'DCE'},
            'pp': {'name': '聚丙烯', 'exchange': 'DCE'},
            'v': {'name': 'PVC', 'exchange': 'DCE'},
            'l': {'name': '聚乙烯', 'exchange': 'DCE'},
            'bu': {'name': '沥青', 'exchange': 'SHFE'},
            'fu': {'name': '燃料油', 'exchange': 'SHFE'}
        }
        
        if variety:
            # 获取指定品种的合约
            # 精确匹配品种代码，避免短代码被长代码误匹配
            import re
            variety_pattern = f"^{re.escape(variety.lower())}\\d"  # 品种代码后必须跟数字
            contracts_df = df[df['合约代码'].str.lower().str.match(variety_pattern, na=False)].copy()
            
            if len(contracts_df) == 0:
                return jsonify({
                    'success': False,
                    'message': f'未找到品种 {variety} 的合约',
                    'timestamp': beijing_now().isoformat()
                }), 404
            
            # 按持仓量排序，识别主力合约
            contracts_df = contracts_df.sort_values('持仓量', ascending=False)
            
            # 格式化合约列表
            contracts = []
            for i, (_, row) in enumerate(contracts_df.iterrows()):
                is_main = (i == 0)  # 持仓量最大的为主力合约
                
                contract_info = {
                    'code': row['合约代码'],
                    'name': row['合约名称'],
                    'is_main_contract': is_main,
                    'open_interest': int(row['持仓量']) if pd.notna(row['持仓量']) else 0,
                    'volume': int(row['成交量']) if pd.notna(row['成交量']) else 0,
                    'price': float(row['最新价']) if pd.notna(row['最新价']) else 0.0,
                    'exchange': row['交易所']
                }
                contracts.append(contract_info)
            
            variety_info = variety_config.get(variety.lower(), {'name': variety.upper(), 'exchange': 'Unknown'})
            
            return jsonify({
                'success': True,
                'timestamp': beijing_now().isoformat(),
                'data': {
                    'variety': variety.upper(),
                    'variety_name': variety_info['name'],
                    'exchange': variety_info['exchange'],
                    'contracts': contracts,
                    'main_contract': contracts[0]['code'] if contracts else None,
                    'total_count': len(contracts)
                }
            })
            
        else:
            # 返回所有支持的品种列表
            varieties = []
            # 按品种代码长度降序排序，避免短代码被长代码覆盖
            sorted_varieties = sorted(variety_config.items(), key=lambda x: len(x[0]), reverse=True)
            
            for var_code, var_info in sorted_varieties:
                # 检查是否有该品种的合约 - 精确匹配避免误识别
                import re
                variety_pattern = f"^{re.escape(var_code.lower())}\\d"
                var_contracts = df[df['合约代码'].str.lower().str.match(variety_pattern, na=False)]
                if len(var_contracts) > 0:
                    # 找到主力合约
                    main_contract = var_contracts.sort_values('持仓量', ascending=False).iloc[0]
                    
                    varieties.append({
                        'code': var_code.upper(),
                        'name': var_info['name'],
                        'exchange': var_info['exchange'],
                        'contract_count': len(var_contracts),
                        'main_contract': main_contract['合约代码'],
                        'main_price': float(main_contract['最新价']) if pd.notna(main_contract['最新价']) else 0.0,
                        'main_open_interest': int(main_contract['持仓量']) if pd.notna(main_contract['持仓量']) else 0
                    })
            
            return jsonify({
                'success': True,
                'timestamp': beijing_now().isoformat(),
                'data': {
                    'varieties': varieties,
                    'total_varieties': len(varieties)
                }
            })
        
    except Exception as e:
        print(f"获取合约列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取合约列表失败: {str(e)}',
            'timestamp': beijing_now().isoformat()
        }), 500


@app.route('/api/futures/technical_indicators')
def get_technical_indicators():
    """获取期货技术指标数据"""
    
    try:
        # 获取请求参数
        symbol = request.args.get('symbol', 'rb2405')
        period = request.args.get('period', '1h')
        limit = int(request.args.get('limit', 100))
        indicators = request.args.get('indicators', 'macd,rsi,kdj,bollinger').split(',')
        
        print(f"获取技术指标: symbol={symbol}, period={period}, limit={limit}, indicators={indicators}")
        
        # 动态映射合约代码到AKShare格式
        def get_akshare_symbol(contract_code):
            contract_lower = contract_code.lower()
            
            # 品种到AKShare主力合约的映射 (与get_futures_kline_data保持一致)
            variety_to_akshare = {
                # 商品期货 - 黑色系
                'rb': 'RB0', 'i': 'I0', 'j': 'J0', 'jm': 'JM0', 'hc': 'HC0',
                # 商品期货 - 有色金属  
                'cu': 'CU0', 'al': 'AL0', 'ni': 'NI0', 'zn': 'ZN0', 'sn': 'SN0', 'pb': 'PB0',
                # 贵金属
                'ag': 'AG0', 'au': 'AU0',
                # 股指期货
                'if': 'IF0', 'ic': 'IC0', 'ih': 'IH0', 'im': 'IM0', 
                # 农产品期货
                'a': 'A0', 'b': 'B0', 'c': 'C0', 'm': 'M0', 'y': 'Y0', 'p': 'P0',
                'sr': 'SR0', 'cf': 'CF0', 'ta': 'TA0', 'rm': 'RM0', 'oi': 'OI0',
                # 能源化工  
                'sc': 'SC0', 'pta': 'PTA0', 'ma': 'MA0', 'l': 'L0', 'v': 'V0',
                'pp': 'PP0', 'eg': 'EG0', 'eb': 'EB0', 'fu': 'FU0'
            }
            
            # 从合约代码中提取品种
            variety = None
            for v in sorted(variety_to_akshare.keys(), key=len, reverse=True):
                if contract_lower.startswith(v):
                    variety = v
                    break
            
            akshare_symbol = variety_to_akshare.get(variety, 'RB0')
            print(f"合约映射: {contract_code} -> {variety} -> {akshare_symbol}")
            return akshare_symbol
        
        # 直接调用K线数据API获取相同的价格数据，确保数据一致性
        try:
            # 内部调用K线数据API
            from flask import current_app
            with current_app.test_request_context(f'/api/futures/kline_data?symbol={symbol}&period={period}&limit={limit}'):
                kline_response = get_futures_kline_data()
                kline_data = kline_response.get_json()
                
                if not kline_data.get('success'):
                    raise Exception(f"获取K线数据失败: {kline_data.get('message', '未知错误')}")
                
                # 将K线数据转换为DataFrame供技术指标计算使用
                kline_items = kline_data['data']['kline_data']
                df_data = {
                    'open': [item['open'] for item in kline_items],
                    'high': [item['high'] for item in kline_items],
                    'low': [item['low'] for item in kline_items],
                    'close': [item['close'] for item in kline_items],
                    'volume': [item['volume'] for item in kline_items]
                }
                
                # 构建时间索引
                timestamps = [pd.to_datetime(item['timestamp']) for item in kline_items]
                df = pd.DataFrame(df_data, index=timestamps)
                
                print(f"✅ 使用K线API数据计算技术指标，数据点数: {len(df)}，时间范围: {df.index[0]} 到 {df.index[-1]}")
                
                # 记录数据源信息
                akshare_symbol = kline_data['data'].get('symbol', symbol)
            
            # 计算选择的技术指标
            indicator_results = {}
            
            # 准备指标参数
            params = DEFAULT_INDICATOR_PARAMS.copy()
            
            # 计算指标
            if 'macd' in indicators:
                macd_data = TechnicalIndicators.calculate_macd(df, **params['macd'])
                if macd_data:
                    indicator_results['macd'] = macd_data
            
            if 'rsi' in indicators:
                rsi_data = TechnicalIndicators.calculate_rsi(df, **params['rsi'])
                if len(rsi_data) > 0:
                    indicator_results['rsi'] = rsi_data
            
            if 'kdj' in indicators:
                kdj_data = TechnicalIndicators.calculate_kdj(df, **params['kdj'])
                if kdj_data:
                    indicator_results['kdj'] = kdj_data
            
            if 'bollinger' in indicators:
                bb_data = TechnicalIndicators.calculate_bollinger_bands(df, **params['bollinger'])
                if bb_data:
                    indicator_results['bollinger'] = bb_data
                    
            if 'obv' in indicators:
                obv_data = TechnicalIndicators.calculate_obv(df, **params['obv'])
                if len(obv_data) > 0:
                    indicator_results['obv'] = obv_data
                    
            if 'vrsi' in indicators:
                vrsi_data = TechnicalIndicators.calculate_vrsi(df, **params['vrsi'])
                if len(vrsi_data) > 0:
                    indicator_results['vrsi'] = vrsi_data
            
            # 格式化指标数据用于API响应
            formatted_indicators = TechnicalIndicators.format_indicators_for_api(
                indicator_results, data_length=limit
            )
            
            # 生成信号分析
            signals = get_signal_analysis(formatted_indicators)
            
            # 准备时间序列
            timestamps = [dt.strftime('%Y-%m-%d %H:%M:%S') for dt in df.index[-limit:]]
            
            # 准备价格数据
            price_data = {
                'timestamps': timestamps,
                'open': df['open'].tail(limit).tolist(),
                'high': df['high'].tail(limit).tolist(), 
                'low': df['low'].tail(limit).tolist(),
                'close': df['close'].tail(limit).tolist(),
                'volume': df['volume'].tail(limit).tolist()
            }
            
            response_data = {
                'success': True,
                'symbol': symbol,
                'akshare_symbol': akshare_symbol,
                'period': period,
                'data_count': len(timestamps),
                'price_data': price_data,
                'indicators': formatted_indicators,
                'signals': signals,
                'parameters': params,
                'timestamp': beijing_now().isoformat()
            }
            
            return jsonify(response_data)
            
        except Exception as ak_error:
            print(f"AKShare数据获取失败: {str(ak_error)}")
            # 不再使用模拟数据，直接返回错误
            return jsonify({
                'success': False,
                'message': f'无法获取真实数据: {str(ak_error)}',
                'error_type': 'akshare_data_fetch_failed',
                'timestamp': beijing_now().isoformat()
            }), 500
            
    except Exception as e:
        print(f"获取技术指标失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取技术指标失败: {str(e)}',
            'timestamp': beijing_now().isoformat()
        }), 500


# 模拟数据生成函数已删除 - 只使用真实数据


@app.route('/api/futures/supertrend')
def get_supertrend_data():
    """获取超级趋势指标数据"""
    
    try:
        # 获取请求参数
        symbol = request.args.get('symbol', 'rb2405')
        period = request.args.get('period', '1h')
        limit = int(request.args.get('limit', 100))
        atr_period = int(request.args.get('atr_period', 10))
        multiplier = float(request.args.get('multiplier', 3.0))
        
        print(f"获取SuperTrend数据: symbol={symbol}, period={period}, atr_period={atr_period}, multiplier={multiplier}")
        
        # 内部调用K线数据API获取基础数据
        from flask import current_app
        with current_app.test_request_context(f'/api/futures/kline_data?symbol={symbol}&period={period}&limit={limit}'):
            kline_response = get_futures_kline_data()
            kline_data = kline_response.get_json()
            
            if not kline_data.get('success'):
                raise Exception(f"获取K线数据失败: {kline_data.get('message', '未知错误')}")
            
            # 将K线数据转换为DataFrame
            kline_items = kline_data['data']['kline_data']
            df_data = {
                'open': [item['open'] for item in kline_items],
                'high': [item['high'] for item in kline_items],
                'low': [item['low'] for item in kline_items],
                'close': [item['close'] for item in kline_items],
                'volume': [item['volume'] for item in kline_items]
            }
            
            # 构建时间索引
            timestamps = [pd.to_datetime(item['timestamp']) for item in kline_items]
            df = pd.DataFrame(df_data, index=timestamps)
            
            print(f"✅ 使用K线数据计算SuperTrend，数据点数: {len(df)}")
        
        # 导入趋势分析器
        from core.trend_analyzers import SuperTrendAnalyzer
        
        # 创建SuperTrend分析器
        analyzer = SuperTrendAnalyzer(atr_period=atr_period, multiplier=multiplier)
        
        # 计算SuperTrend
        supertrend_result = analyzer.calculate(df)
        
        # 清理NaN值的辅助函数
        def clean_nan_values(data):
            """将NaN值转换为None以生成有效的JSON"""
            if isinstance(data, list):
                return [None if pd.isna(x) else x for x in data]
            return data
        
        # 准备返回数据 - 清理NaN值
        result_data = {
            'symbol': symbol,
            'period': period,
            'data_count': len(supertrend_result['supertrend_line']),
            'supertrend': {
                'line': clean_nan_values(supertrend_result['supertrend_line']),
                'upper_band': clean_nan_values(supertrend_result['supertrend_upper']),
                'lower_band': clean_nan_values(supertrend_result['supertrend_lower']),
                'trend_direction': clean_nan_values(supertrend_result['trend_direction']),
                'current_trend': supertrend_result['current_trend'],
                'trend_changes': supertrend_result['trend_changes'],
                'trend_strength': supertrend_result['trend_strength']
            },
            'timestamps': supertrend_result['timestamps'],
            'parameters': {
                'atr_period': atr_period,
                'multiplier': multiplier
            },
            'price_data': {
                'close': clean_nan_values(df['close'].tolist()),
                'high': clean_nan_values(df['high'].tolist()),
                'low': clean_nan_values(df['low'].tolist()),
                'open': clean_nan_values(df['open'].tolist())
            }
        }
        
        return jsonify({
            'success': True,
            'data': result_data,
            'timestamp': beijing_now().isoformat()
        })
        
    except Exception as e:
        print(f"获取SuperTrend数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取SuperTrend数据失败: {str(e)}',
            'timestamp': beijing_now().isoformat()
        }), 500


@app.route('/api/strategy_library/list')
def get_strategy_library():
    """获取策略库列表"""
    
    try:
        strategies = strategy_library.list_strategies()
        
        return jsonify({
            'success': True,
            'strategies': strategies,
            'total_count': len(strategies),
            'timestamp': beijing_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取策略库失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取策略库失败: {str(e)}',
            'timestamp': beijing_now().isoformat()
        }), 500


@app.route('/api/strategy_library/signals')
def get_strategy_signals():
    """获取策略交易信号"""
    
    try:
        # 获取请求参数
        strategy_id = request.args.get('strategy_id', 'turtle_trading')
        symbol = request.args.get('symbol', 'rb2405')
        period = request.args.get('period', '1h')
        limit = int(request.args.get('limit', 100))
        
        # 获取自定义参数（JSON格式）
        custom_params = request.args.get('parameters')
        parameters = None
        if custom_params:
            try:
                parameters = json.loads(custom_params)
            except json.JSONDecodeError:
                logger.warning(f"无效的参数JSON: {custom_params}")
        
        print(f"策略信号分析: strategy={strategy_id}, symbol={symbol}, period={period}")
        
        # 获取策略实例
        strategy = strategy_library.get_strategy(strategy_id, parameters)
        if not strategy:
            return jsonify({
                'success': False,
                'message': f'未找到策略: {strategy_id}',
                'timestamp': beijing_now().isoformat()
            }), 404
        
        # 获取历史数据（复用existing logic）
        def get_akshare_symbol(contract_code):
            contract_lower = contract_code.lower()
            variety_to_akshare = {
                'rb': 'RB0', 'i': 'I0', 'j': 'J0', 'jm': 'JM0', 'hc': 'HC0',
                'cu': 'CU0', 'al': 'AL0', 'ni': 'NI0', 'zn': 'ZN0', 'sn': 'SN0', 'pb': 'PB0',
                'ag': 'AG0', 'au': 'AU0',
                'if': 'IF0', 'ic': 'IC0', 'ih': 'IH0', 'im': 'IM0', 
                'a': 'A0', 'b': 'B0', 'c': 'C0', 'm': 'M0', 'y': 'Y0', 'p': 'P0',
                'sr': 'SR0', 'cf': 'CF0', 'ta': 'TA0', 'rm': 'RM0', 'oi': 'OI0',
                'sc': 'SC0', 'pta': 'PTA0', 'ma': 'MA0', 'l': 'L0', 'v': 'V0',
                'pp': 'PP0', 'eg': 'EG0', 'eb': 'EB0', 'fu': 'FU0'
            }
            
            variety = None
            for v in sorted(variety_to_akshare.keys(), key=len, reverse=True):
                if contract_lower.startswith(v):
                    variety = v
                    break
            
            return variety_to_akshare.get(variety, 'RB0')
        
        # 获取数据
        akshare_symbol = get_akshare_symbol(symbol)
        
        try:
            # 尝试获取真实数据
            df = ak.futures_zh_minute_sina(symbol=akshare_symbol, period=period)
            
            if df is None or len(df) == 0:
                raise Exception(f"未获取到{akshare_symbol}的数据")
            
            print(f"获取到{len(df)}条真实数据")
            
            # 限制数据量
            if len(df) > limit:
                df = df.tail(limit)
            
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            
            # 添加模拟成交量
            if 'volume' not in df.columns or df['volume'].isna().all():
                df['volume'] = np.random.randint(1000, 10000, len(df))
                
        except Exception as ak_error:
            print(f"AKShare数据获取失败: {str(ak_error)}")
            # 不再使用模拟数据，直接返回错误
            return jsonify({
                'success': False,
                'message': f'无法获取真实数据进行策略回测: {str(ak_error)}',
                'error_type': 'akshare_data_fetch_failed',
                'timestamp': beijing_now().isoformat()
            }), 500
        
        # 生成策略信号
        signals = strategy.generate_signals(df)
        formatted_signals = format_signals_for_api(signals)
        
        # 运行回测
        backtest_metrics = strategy.backtest(df)
        formatted_metrics = format_backtest_metrics_for_api(backtest_metrics)
        
        # 准备价格数据
        timestamps = [dt.strftime('%Y-%m-%d %H:%M:%S') for dt in df.index]
        price_data = {
            'timestamps': timestamps,
            'open': df['open'].tolist(),
            'high': df['high'].tolist(),
            'low': df['low'].tolist(),
            'close': df['close'].tolist(),
            'volume': df['volume'].tolist()
        }
        
        return jsonify({
            'success': True,
            'strategy_id': strategy_id,
            'strategy_name': strategy.name,
            'symbol': symbol,
            'akshare_symbol': akshare_symbol,
            'period': period,
            'data_count': len(df),
            'signals': formatted_signals,
            'signals_count': len(signals),
            'backtest_metrics': formatted_metrics,
            'price_data': price_data,
            'strategy_parameters': strategy.parameters,
            'timestamp': beijing_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"策略信号分析失败: {e}")
        return jsonify({
            'success': False,
            'message': f'策略信号分析失败: {str(e)}',
            'timestamp': beijing_now().isoformat()
        }), 500


@app.route('/api/strategy_library/backtest', methods=['POST'])
def run_strategy_backtest():
    """运行策略回测"""
    
    try:
        data = request.get_json()
        
        strategy_id = data.get('strategy_id', 'turtle_trading')
        symbol = data.get('symbol', 'rb2405')
        period = data.get('period', '1d')
        start_date = data.get('start_date', '2023-01-01')
        end_date = data.get('end_date', '2024-01-01')
        initial_capital = float(data.get('initial_capital', 100000))
        parameters = data.get('parameters')
        
        print(f"策略回测: {strategy_id}, {symbol}, {start_date} - {end_date}")
        
        # 获取策略实例
        strategy = strategy_library.get_strategy(strategy_id, parameters)
        if not strategy:
            return jsonify({
                'success': False,
                'message': f'未找到策略: {strategy_id}'
            }), 404
        
        # 获取真实历史数据进行回测
        try:
            # 动态映射合约代码到AKShare格式（与其他API保持一致）
            def get_akshare_symbol(contract_code):
                contract_lower = contract_code.lower()
                variety_to_akshare = {
                    'rb': 'RB0', 'cu': 'CU0', 'al': 'AL0', 'zn': 'ZN0', 'ni': 'NI0',
                    'ag': 'AG0', 'au': 'AU0', 'i': 'I0', 'j': 'J0', 'jm': 'JM0'
                }
                import re
                variety_match = re.match(r'^([a-zA-Z]+)', contract_code)
                if variety_match:
                    variety = variety_match.group(1).lower()
                    return variety_to_akshare.get(variety, 'RB0')
                return 'RB0'
            
            akshare_symbol = get_akshare_symbol(symbol)
            
            # 获取日线历史数据用于回测
            df = ak.futures_zh_daily_sina(symbol=akshare_symbol)
            if df is None or len(df) == 0:
                raise Exception(f"未获取到{akshare_symbol}的历史数据")
            
            # 按日期范围筛选
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df = df[(df.index >= start_dt) & (df.index <= end_dt)].copy()
            
            if len(df) == 0:
                raise Exception(f"指定日期范围{start_date}到{end_date}没有数据")
                
        except Exception as ak_error:
            print(f"获取真实历史数据失败: {str(ak_error)}")
            return jsonify({
                'success': False,
                'message': f'无法获取真实历史数据进行回测: {str(ak_error)}',
                'error_type': 'historical_data_fetch_failed',
                'timestamp': beijing_now().isoformat()
            }), 500
        
        # 运行回测
        metrics = strategy.backtest(df, initial_capital)
        formatted_metrics = format_backtest_metrics_for_api(metrics)
        
        # 生成信号用于图表显示
        signals = strategy.generate_signals(df)
        formatted_signals = format_signals_for_api(signals)
        
        # 计算权益曲线
        portfolio_values = []
        position = 0
        entry_price = 0
        cash = initial_capital
        
        signal_index = 0
        
        for i, (timestamp, row) in enumerate(df.iterrows()):
            current_price = row['close']
            
            # 处理信号
            if signal_index < len(signals) and timestamp >= signals[signal_index].timestamp:
                signal = signals[signal_index]
                
                if signal.action == TradingSignalAction.OPEN_LONG and position <= 0:
                    position = 1
                    entry_price = current_price
                elif signal.action == TradingSignalAction.OPEN_SHORT and position >= 0:
                    position = -1  
                    entry_price = current_price
                elif signal.action == TradingSignalAction.CLOSE_LONG or signal.action == TradingSignalAction.CLOSE_SHORT:
                    position = 0
                    entry_price = 0
                
                signal_index += 1
            
            # 计算组合价值
            if position > 0:
                portfolio_value = cash + (current_price - entry_price) * (initial_capital / entry_price)
            elif position < 0:
                portfolio_value = cash + (entry_price - current_price) * (initial_capital / entry_price)
            else:
                portfolio_value = cash
            
            portfolio_values.append(portfolio_value)
        
        # 准备图表数据
        chart_data = {
            'dates': [dt.strftime('%Y-%m-%d') for dt in df.index],
            'prices': df['close'].tolist(),
            'portfolio_values': portfolio_values
        }
        
        return jsonify({
            'success': True,
            'strategy_id': strategy_id,
            'strategy_name': strategy.name,
            'symbol': symbol,
            'backtest_period': f"{start_date} to {end_date}",
            'initial_capital': initial_capital,
            'metrics': formatted_metrics,
            'signals': formatted_signals,
            'chart_data': chart_data,
            'strategy_parameters': strategy.parameters,
            'timestamp': beijing_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"策略回测失败: {e}")
        return jsonify({
            'success': False,
            'message': f'策略回测失败: {str(e)}',
            'timestamp': beijing_now().isoformat()
        }), 500


@app.route('/api/strategy_library/compare')
def compare_strategies():
    """策略对比分析"""
    
    try:
        # 获取请求参数
        strategy_ids = request.args.get('strategies', 'turtle_trading,bollinger_bands,momentum').split(',')
        symbol = request.args.get('symbol', 'rb2405')
        period = request.args.get('period', '1d')
        days = int(request.args.get('days', 100))
        
        print(f"策略对比: {strategy_ids}, {symbol}, {days}天")
        
        # 获取真实数据进行策略对比
        try:
            # 使用与其他API一致的AKShare数据获取逻辑
            def get_akshare_symbol(contract_code):
                contract_lower = contract_code.lower()
                variety_to_akshare = {
                    'rb': 'RB0', 'cu': 'CU0', 'al': 'AL0', 'zn': 'ZN0', 'ni': 'NI0',
                    'ag': 'AG0', 'au': 'AU0', 'i': 'I0', 'j': 'J0', 'jm': 'JM0'
                }
                import re
                variety_match = re.match(r'^([a-zA-Z]+)', contract_code)
                if variety_match:
                    variety = variety_match.group(1).lower()
                    return variety_to_akshare.get(variety, 'RB0')
                return 'RB0'
            
            akshare_symbol = get_akshare_symbol(symbol)
            df = ak.futures_zh_daily_sina(symbol=akshare_symbol)
            
            if df is None or len(df) == 0:
                raise Exception(f"未获取到{akshare_symbol}的数据")
                
            # 取最新的days天数据
            df = df.tail(days).copy()
            dates = df.index
            
        except Exception as ak_error:
            print(f"获取真实数据失败: {str(ak_error)}")
            return jsonify({
                'success': False,
                'message': f'无法获取真实数据进行策略对比: {str(ak_error)}',
                'error_type': 'akshare_data_fetch_failed',
                'timestamp': beijing_now().isoformat()
            }), 500
        
        # 运行策略比较
        comparison_results = strategy_library.run_strategy_comparison(df, strategy_ids)
        
        # 格式化结果
        formatted_results = {}
        for strategy_id, metrics in comparison_results.items():
            if metrics:
                strategy = strategy_library.get_strategy(strategy_id)
                formatted_results[strategy_id] = {
                    'strategy_name': strategy.name if strategy else strategy_id,
                    'strategy_type': strategy.strategy_type.value if strategy else 'Unknown',
                    'metrics': format_backtest_metrics_for_api(metrics)
                }
            else:
                formatted_results[strategy_id] = {
                    'strategy_name': strategy_id,
                    'strategy_type': 'Unknown',
                    'metrics': None,
                    'error': '回测失败'
                }
        
        # 找出最佳策略
        best_strategy_id, best_metrics = strategy_library.get_best_strategy(df, strategy_ids)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'period': period,
            'test_days': days,
            'strategies_tested': len(strategy_ids),
            'comparison_results': formatted_results,
            'best_strategy': {
                'strategy_id': best_strategy_id,
                'metrics': format_backtest_metrics_for_api(best_metrics) if best_metrics else None
            },
            'timestamp': beijing_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"策略对比失败: {e}")
        return jsonify({
            'success': False,
            'message': f'策略对比失败: {str(e)}',
            'timestamp': beijing_now().isoformat()
        }), 500


@app.route('/api/portfolio/config')
def portfolio_config():
    """获取投资组合配置"""
    
    config = {
        'portfolio_name': 'Demo Multi-Strategy Portfolio',
        'total_capital': 2000000,
        'allocation_method': 'weighted',
        'strategies': [
            {
                'name': 'MA快速-螺纹钢',
                'symbol': 'rb2405',
                'allocation': 0.4,
                'capital': 800000,
                'parameters': {'fast': 5, 'slow': 20},
                'risk_budget': 0.03
            },
            {
                'name': 'MA慢速-螺纹钢',
                'symbol': 'rb2405', 
                'allocation': 0.25,
                'capital': 500000,
                'parameters': {'fast': 10, 'slow': 50},
                'risk_budget': 0.02
            },
            {
                'name': 'MA策略-铁矿石',
                'symbol': 'i2405',
                'allocation': 0.25, 
                'capital': 500000,
                'parameters': {'fast': 8, 'slow': 25},
                'risk_budget': 0.025
            },
            {
                'name': 'MA策略-焦炭',
                'symbol': 'j2405',
                'allocation': 0.1,
                'capital': 200000, 
                'parameters': {'fast': 12, 'slow': 30},
                'risk_budget': 0.015
            }
        ]
    }
    
    return jsonify(config)


@app.route('/static/<path:filename>')
def static_files(filename):
    """静态文件服务"""
    return send_from_directory('static', filename)


# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info('客户端已连接')
    emit('connected', {'message': '连接成功'})


@socketio.on('subscribe_market_data')
def handle_market_data_subscription():
    """订阅市场数据"""
    logger.info('客户端订阅市场数据')
    # 开始发送实时数据
    start_real_time_data()


def start_real_time_data():
    """开始发送实时数据"""
    
    def send_data():
        while True:
            # 发送市场数据
            market_ticks = data_generator.generate_market_tick()
            socketio.emit('market_data', {
                'timestamp': beijing_now().isoformat(),
                'data': market_ticks
            })
            
            # 发送策略状态
            strategy_status = data_generator.generate_strategy_status()
            socketio.emit('strategy_status', {
                'timestamp': beijing_now().isoformat(),
                'strategies': strategy_status
            })
            
            # 发送持仓数据
            positions = data_generator.update_positions()
            socketio.emit('positions_update', {
                'timestamp': beijing_now().isoformat(),
                'positions': positions
            })
            
            # 发送最新交易
            new_trade = data_generator.generate_new_trade()
            if new_trade:
                socketio.emit('new_trade', {
                    'timestamp': beijing_now().isoformat(),
                    'trade': new_trade
                })
            
            # 等待2秒
            socketio.sleep(2)
    
    # 启动后台任务
    socketio.start_background_task(send_data)


def create_demo_templates():
    """创建演示HTML模板"""
    
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # 创建主页面模板
    html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>期货量化交易系统 - 项目验收演示</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 0;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .dashboard { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .card:hover { transform: translateY(-2px); }
        .card h3 {
            color: #5a67d8;
            margin-bottom: 15px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background: #48bb78; }
        .status-paused { background: #ed8936; }
        .status-error { background: #f56565; }
        .metric { 
            display: flex; 
            justify-content: space-between; 
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #f7fafc;
        }
        .metric-value { font-weight: 600; }
        .positive { color: #38a169; }
        .negative { color: #e53e3e; }
        .btn {
            background: #5a67d8;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .btn:hover { background: #4c51bf; }
        .backtest-form { margin-top: 15px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
        .form-group input, .form-group select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
        }
        .loading { text-align: center; color: #718096; }
        #connection-status {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 8px 15px;
            border-radius: 20px;
            color: white;
            font-size: 12px;
        }
        .connected { background: #38a169; }
        .disconnected { background: #e53e3e; }
        
        /* 持仓和交易相关样式 */
        .position-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            background: #f8f9fa;
        }
        .position-info {
            flex: 1;
        }
        .position-pnl {
            text-align: right;
            font-weight: 600;
        }
        .direction-long {
            color: #e53e3e;
            background: #fed7d7;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
        }
        .direction-short {
            color: #38a169;
            background: #c6f6d5;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
        }
        .trade-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 10px;
            margin: 2px 0;
            border-bottom: 1px solid #f1f5f9;
            font-size: 13px;
        }
        .trade-item:last-child {
            border-bottom: none;
        }
        .trade-info {
            flex: 1;
        }
        .trade-pnl {
            text-align: right;
            font-weight: 600;
            font-size: 12px;
        }
        .action-open {
            color: #5a67d8;
            font-weight: 600;
        }
        .action-close {
            color: #ed8936;
            font-weight: 600;
        }
        .new-trade {
            animation: highlight 2s ease-in-out;
        }
        @keyframes highlight {
            0% { background: #fef5e7; }
            100% { background: transparent; }
        }
        .summary-box {
            background: #edf2f7;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 15px;
            text-align: center;
        }
        .summary-item {
            display: inline-block;
            margin: 0 10px;
            font-size: 14px;
        }
        .summary-label {
            color: #718096;
            font-size: 12px;
            display: block;
        }
        .summary-value {
            font-weight: 600;
            color: #2d3748;
        }
        .pagination-controls button {
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        .pagination-controls button:not(:disabled):hover {
            background: #e2e8f0 !important;
        }
        .pagination-controls button:disabled {
            opacity: 0.6;
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div id="connection-status" class="disconnected">未连接</div>
    
    <div class="header">
        <h1>🎯 期货量化交易系统</h1>
        <p>项目验收演示 - Milestone 2.1~2.5 核心功能展示</p>
    </div>
    
    <div class="container">
        <div class="dashboard">
            <!-- 系统状态 -->
            <div class="card">
                <h3>📊 系统状态</h3>
                <div id="system-status">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <!-- 市场数据 -->
            <div class="card">
                <h3>📈 实时行情</h3>
                <div id="market-data">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <!-- 策略状态 -->
            <div class="card">
                <h3>🎯 策略状态</h3>
                <div id="strategy-status">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <!-- 回测系统 -->
            <div class="card">
                <h3>🔬 回测系统</h3>
                <div class="backtest-form">
                    <div class="form-group">
                        <label>开始日期:</label>
                        <input type="date" id="start-date" value="2024-01-01">
                    </div>
                    <div class="form-group">
                        <label>结束日期:</label>
                        <input type="date" id="end-date" value="2024-03-31">
                    </div>
                    <div class="form-group">
                        <label>初始资金:</label>
                        <input type="number" id="initial-capital" value="1000000">
                    </div>
                    <div class="form-group">
                        <label>快均线周期:</label>
                        <input type="number" id="fast-period" value="5">
                    </div>
                    <div class="form-group">
                        <label>慢均线周期:</label>
                        <input type="number" id="slow-period" value="20">
                    </div>
                    <button class="btn" onclick="runBacktest()">运行回测</button>
                </div>
                <div id="backtest-results" style="margin-top: 20px;"></div>
            </div>
            
            <!-- 实时持仓 -->
            <div class="card">
                <h3>📊 实时持仓</h3>
                <div id="positions-data">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <!-- 成交记录 -->
            <div class="card">
                <h3>📋 成交记录</h3>
                <div id="trades-data">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <!-- 投资组合配置 -->
            <div class="card">
                <h3>⚖️ 投资组合配置</h3>
                <div id="portfolio-config">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <!-- 实时图表 -->
            <div class="card" style="grid-column: 1 / -1;">
                <h3>📊 实时监控图表</h3>
                <canvas id="priceChart" width="400" height="200"></canvas>
            </div>
            
            <!-- 回测分析图表 -->
            <div class="card" style="grid-column: 1 / -1;">
                <h3>📈 回测分析图表 - K线图与交易信号</h3>
                <div style="margin-bottom: 15px;">
                    <button class="btn" onclick="loadBacktestChart()" style="margin-right: 10px;">加载回测数据</button>
                    <span id="backtest-chart-status" style="color: #718096; font-size: 14px;">点击按钮加载回测分析图表</span>
                </div>
                <div style="position: relative; height: 500px; overflow: hidden;">
                    <canvas id="backtestChart" style="display: block; max-width: 100%; max-height: 100%;"></canvas>
                </div>
                <div id="backtest-metrics" style="margin-top: 15px; padding: 10px; background: #f7fafc; border-radius: 6px; display: none;">
                    <div style="display: flex; justify-content: space-around; text-align: center;">
                        <div>
                            <span style="display: block; font-size: 12px; color: #718096;">总收益率</span>
                            <span id="total-return" style="font-weight: 600; color: #2d3748;">-</span>
                        </div>
                        <div>
                            <span style="display: block; font-size: 12px; color: #718096;">最大回撤</span>
                            <span id="max-drawdown" style="font-weight: 600; color: #2d3748;">-</span>
                        </div>
                        <div>
                            <span style="display: block; font-size: 12px; color: #718096;">交易次数</span>
                            <span id="total-trades" style="font-weight: 600; color: #2d3748;">-</span>
                        </div>
                        <div>
                            <span style="display: block; font-size: 12px; color: #718096;">胜率</span>
                            <span id="win-rate" style="font-weight: 600; color: #2d3748;">-</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 初始化Socket.IO连接
        const socket = io();
        const connectionStatus = document.getElementById('connection-status');
        
        // 连接状态管理
        socket.on('connect', () => {
            connectionStatus.textContent = '已连接';
            connectionStatus.className = 'connected';
            console.log('已连接到服务器');
            socket.emit('subscribe_market_data');
        });
        
        socket.on('disconnect', () => {
            connectionStatus.textContent = '未连接';
            connectionStatus.className = 'disconnected';
        });
        
        // 初始化图表
        const ctx = document.getElementById('priceChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '螺纹钢价格',
                    data: [],
                    borderColor: '#5a67d8',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: false }
                }
            }
        });
        
        // 处理实时市场数据
        socket.on('market_data', (data) => {
            updateMarketData(data.data);
            
            // 更新图表
            if (data.data.rb2405) {
                const now = new Date().toLocaleTimeString();
                chart.data.labels.push(now);
                chart.data.datasets[0].data.push(data.data.rb2405.last_price);
                
                // 保持最后20个数据点
                if (chart.data.labels.length > 20) {
                    chart.data.labels.shift();
                    chart.data.datasets[0].data.shift();
                }
                
                chart.update('none');
            }
        });
        
        // 处理策略状态更新
        socket.on('strategy_status', (data) => {
            updateStrategyStatus(data.strategies);
        });
        
        // 处理持仓更新
        socket.on('positions_update', (data) => {
            updatePositions(data.positions);
        });
        
        // 处理新交易
        socket.on('new_trade', (data) => {
            addNewTrade(data.trade);
        });
        
        // 更新市场数据显示
        function updateMarketData(data) {
            const container = document.getElementById('market-data');
            let html = '';
            
            for (const [symbol, tick] of Object.entries(data)) {
                const changeClass = tick.change >= 0 ? 'positive' : 'negative';
                html += `
                    <div class="metric">
                        <span>${symbol}:</span>
                        <span class="metric-value ${changeClass}">
                            ${tick.last_price} (${tick.change >= 0 ? '+' : ''}${tick.change}%)
                        </span>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        // 更新策略状态显示
        function updateStrategyStatus(strategies) {
            const container = document.getElementById('strategy-status');
            let html = '';
            
            for (const [id, strategy] of Object.entries(strategies)) {
                const statusClass = strategy.status === 'running' ? 'status-running' : 
                                   strategy.status === 'paused' ? 'status-paused' : 'status-error';
                const pnlClass = strategy.pnl >= 0 ? 'positive' : 'negative';
                
                html += `
                    <div class="metric">
                        <span>
                            <span class="status-indicator ${statusClass}"></span>
                            ${strategy.name}
                        </span>
                        <span class="metric-value ${pnlClass}">
                            ${strategy.pnl.toFixed(0)}
                        </span>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        // 运行回测
        function runBacktest() {
            const params = {
                start_date: document.getElementById('start-date').value,
                end_date: document.getElementById('end-date').value,
                initial_capital: document.getElementById('initial-capital').value,
                fast_period: document.getElementById('fast-period').value,
                slow_period: document.getElementById('slow-period').value,
                symbols: ['rb2405']
            };
            
            document.getElementById('backtest-results').innerHTML = '<div class="loading">回测运行中...</div>';
            
            fetch('/api/backtest/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const results = data.results;
                    document.getElementById('backtest-results').innerHTML = `
                        <h4>回测结果:</h4>
                        <div class="metric">
                            <span>总收益率:</span>
                            <span class="metric-value ${results.total_return >= 0 ? 'positive' : 'negative'}">
                                ${(results.total_return * 100).toFixed(2)}%
                            </span>
                        </div>
                        <div class="metric">
                            <span>夏普比率:</span>
                            <span class="metric-value">${results.sharpe_ratio.toFixed(3)}</span>
                        </div>
                        <div class="metric">
                            <span>最大回撤:</span>
                            <span class="metric-value negative">${(results.max_drawdown * 100).toFixed(2)}%</span>
                        </div>
                        <div class="metric">
                            <span>交易次数:</span>
                            <span class="metric-value">${results.total_trades}</span>
                        </div>
                    `;
                } else {
                    document.getElementById('backtest-results').innerHTML = 
                        `<div style="color: #e53e3e;">回测失败: ${data.message}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('backtest-results').innerHTML = 
                    `<div style="color: #e53e3e;">请求失败: ${error}</div>`;
            });
        }
        
        // 加载初始数据
        function loadInitialData() {
            // 加载系统状态
            fetch('/api/system/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('system-status').innerHTML = `
                        <div class="metric">
                            <span>总资金:</span>
                            <span class="metric-value">${data.total_capital.toLocaleString()}</span>
                        </div>
                        <div class="metric">
                            <span>已用资金:</span>
                            <span class="metric-value">${data.used_capital.toLocaleString()}</span>
                        </div>
                        <div class="metric">
                            <span>活跃策略:</span>
                            <span class="metric-value">${data.active_strategies}/${data.total_strategies}</span>
                        </div>
                        <div class="metric">
                            <span>今日交易:</span>
                            <span class="metric-value">${data.daily_trades}</span>
                        </div>
                    `;
                });
            
            // 加载投资组合配置
            fetch('/api/portfolio/config')
                .then(response => response.json())
                .then(data => {
                    let html = `
                        <div class="metric">
                            <span>组合名称:</span>
                            <span class="metric-value">${data.portfolio_name}</span>
                        </div>
                        <div class="metric">
                            <span>总资金:</span>
                            <span class="metric-value">${data.total_capital.toLocaleString()}</span>
                        </div>
                    `;
                    
                    data.strategies.forEach(strategy => {
                        html += `
                            <div class="metric">
                                <span>${strategy.name}:</span>
                                <span class="metric-value">${(strategy.allocation * 100).toFixed(1)}%</span>
                            </div>
                        `;
                    });
                    
                    document.getElementById('portfolio-config').innerHTML = html;
                });
        }
        
        // 更新持仓显示
        function updatePositions(positionsData) {
            const container = document.getElementById('positions-data');
            let html = '';
            
            let totalMarketValue = 0;
            let totalUnrealizedPnl = 0;
            let positionCount = 0;
            
            // 显示当前时间
            const currentTime = positionsData.current_datetime || new Date().toLocaleString('zh-CN');
            html += `
                <div style="text-align: center; margin-bottom: 15px; padding: 8px; background: #f7fafc; border-radius: 6px; font-size: 13px; color: #4a5568;">
                    📅 当前时间：${currentTime}
                </div>
            `;
            
            const positions = positionsData.positions || positionsData;
            
            for (let i = 0; i < positions.length; i++) {
                const pos = positions[i];
                const directionClass = pos.direction === 'long' ? 'direction-long' : 'direction-short';
                const pnlClass = pos.unrealized_pnl >= 0 ? 'positive' : 'negative';
                const pnlRatio = ((pos.unrealized_pnl / (pos.avg_price * pos.quantity)) * 100);
                
                html += `
                    <div class="position-item">
                        <div class="position-info">
                            <div>
                                <strong>${pos.symbol}</strong>
                                <span class="${directionClass}">${pos.direction.toUpperCase()}</span>
                                <span style="margin-left: 8px; color: #718096;">x${pos.quantity}</span>
                            </div>
                            <div style="font-size: 12px; color: #718096; margin-top: 4px;">
                                均价: ${pos.avg_price} | 现价: ${pos.current_price} | ${pos.strategy}
                            </div>
                        </div>
                        <div class="position-pnl">
                            <div class="${pnlClass}">${pos.unrealized_pnl.toFixed(0)}</div>
                            <div style="font-size: 12px;" class="${pnlClass}">${pnlRatio >= 0 ? '+' : ''}${pnlRatio.toFixed(2)}%</div>
                        </div>
                    </div>
                `;
                
                totalMarketValue += pos.market_value;
                totalUnrealizedPnl += pos.unrealized_pnl;
                positionCount++;
            }
            
            // 添加汇总信息
            const totalPnlClass = totalUnrealizedPnl >= 0 ? 'positive' : 'negative';
            const summaryHtml = `
                <div class="summary-box">
                    <div class="summary-item">
                        <span class="summary-label">持仓数量</span>
                        <span class="summary-value">${positionCount}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">市值</span>
                        <span class="summary-value">${totalMarketValue.toFixed(0)}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">浮动盈亏</span>
                        <span class="summary-value ${totalPnlClass}">${totalUnrealizedPnl >= 0 ? '+' : ''}${totalUnrealizedPnl.toFixed(0)}</span>
                    </div>
                </div>
            `;
            
            container.innerHTML = summaryHtml + html;
        }
        
        // 全局分页状态
        let currentTradesPage = 1;
        const tradesPerPage = 10;
        
        // 更新交易记录
        function updateTrades(trades, pagination = null) {
            const container = document.getElementById('trades-data');
            let html = '';
            
            // 添加分页信息和控件
            if (pagination) {
                html += `
                    <div style="margin-bottom: 15px; padding: 8px; background: #f7fafc; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; font-size: 13px;">
                        <div style="color: #4a5568;">
                            📋 成交记录 (第${pagination.current_page}页/共${pagination.total_pages}页，总计${pagination.total_trades}笔)
                        </div>
                        <div class="pagination-controls">
                            <button onclick="loadTradesPage(${pagination.prev_page})" ${!pagination.has_prev ? 'disabled' : ''} 
                                    style="margin-right: 5px; padding: 4px 8px; font-size: 12px; border: 1px solid #cbd5e0; background: ${!pagination.has_prev ? '#f7fafc' : '#ffffff'}; cursor: ${!pagination.has_prev ? 'not-allowed' : 'pointer'};">
                                ← 上一页
                            </button>
                            <span style="margin: 0 10px; color: #718096;">${pagination.current_page} / ${pagination.total_pages}</span>
                            <button onclick="loadTradesPage(${pagination.next_page})" ${!pagination.has_next ? 'disabled' : ''} 
                                    style="margin-left: 5px; padding: 4px 8px; font-size: 12px; border: 1px solid #cbd5e0; background: ${!pagination.has_next ? '#f7fafc' : '#ffffff'}; cursor: ${!pagination.has_next ? 'not-allowed' : 'pointer'};">
                                下一页 →
                            </button>
                        </div>
                    </div>
                `;
            }
            
            trades.forEach(trade => {
                const actionClass = trade.action === 'open' ? 'action-open' : 'action-close';
                const directionClass = trade.direction === 'long' ? 'direction-long' : 'direction-short';
                const pnlHtml = trade.pnl !== null ? 
                    `<div class="trade-pnl ${trade.pnl >= 0 ? 'positive' : 'negative'}">${trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(0)}</div>` : 
                    '<div class="trade-pnl">-</div>';
                
                html += `
                    <div class="trade-item">
                        <div class="trade-info">
                            <div>
                                <span class="${actionClass}">${trade.action.toUpperCase()}</span>
                                <span class="${directionClass}">${trade.direction.toUpperCase()}</span>
                                <strong>${trade.symbol}</strong>
                                <span style="margin-left: 8px;">x${trade.quantity}</span>
                                <span style="color: #718096;">@${trade.price}</span>
                            </div>
                            <div style="font-size: 11px; color: #a0aec0;">
                                📅 ${trade.datetime_str} | ${trade.strategy}
                            </div>
                        </div>
                        ${pnlHtml}
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        // 添加新交易（带动画效果）
        function addNewTrade(trade) {
            const container = document.getElementById('trades-data');
            const actionClass = trade.action === 'open' ? 'action-open' : 'action-close';
            const directionClass = trade.direction === 'long' ? 'direction-long' : 'direction-short';
            const pnlHtml = trade.pnl !== null ? 
                `<div class="trade-pnl ${trade.pnl >= 0 ? 'positive' : 'negative'}">${trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(0)}</div>` : 
                '<div class="trade-pnl">-</div>';
            
            const newTradeHtml = `
                <div class="trade-item new-trade">
                    <div class="trade-info">
                        <div>
                            <span class="${actionClass}">${trade.action.toUpperCase()}</span>
                            <span class="${directionClass}">${trade.direction.toUpperCase()}</span>
                            <strong>${trade.symbol}</strong>
                            <span style="margin-left: 8px;">x${trade.quantity}</span>
                            <span style="color: #718096;">@${trade.price}</span>
                        </div>
                        <div style="font-size: 11px; color: #a0aec0;">
                            ${new Date(trade.timestamp).toLocaleTimeString()} | ${trade.strategy}
                        </div>
                    </div>
                    ${pnlHtml}
                </div>
            `;
            
            // 在顶部插入新交易
            container.insertAdjacentHTML('afterbegin', newTradeHtml);
            
            // 限制显示数量
            const tradeItems = container.querySelectorAll('.trade-item');
            if (tradeItems.length > 20) {
                tradeItems[tradeItems.length - 1].remove();
            }
        }
        
        // 加载指定页面的交易记录
        function loadTradesPage(page = 1) {
            if (!page) return; // 防止无效页码
            
            currentTradesPage = page;
            fetch(`/api/trades?page=${page}&per_page=${tradesPerPage}`)
                .then(response => response.json())
                .then(data => {
                    updateTrades(data.trades, data.pagination);
                })
                .catch(error => {
                    console.error('Error loading trades:', error);
                });
        }
        
        // 加载持仓和交易数据
        function loadPositionsAndTrades() {
            // 加载持仓数据
            fetch('/api/positions')
                .then(response => response.json())
                .then(data => {
                    updatePositions(data);
                });
            
            // 加载交易记录（第一页）
            loadTradesPage(1);
        }
        
        // 回测分析图表相关
        let backtestChart = null;
        
        function loadBacktestChart() {
            const statusElement = document.getElementById('backtest-chart-status');
            statusElement.textContent = '正在加载回测数据...';
            statusElement.style.color = '#5a67d8';
            
            fetch('/api/backtest/chart_data')
                .then(response => response.json())
                .then(data => {
                    createBacktestChart(data);
                    updateBacktestMetrics(data.performance_metrics);
                    statusElement.textContent = '回测数据加载完成';
                    statusElement.style.color = '#48bb78';
                })
                .catch(error => {
                    console.error('Error loading backtest chart:', error);
                    statusElement.textContent = '数据加载失败';
                    statusElement.style.color = '#f56565';
                });
        }
        
        function createBacktestChart(data) {
            const ctx = document.getElementById('backtestChart').getContext('2d');
            
            // 销毁现有图表
            if (backtestChart) {
                backtestChart.destroy();
            }
            
            // 简化数据处理，使用索引而不是时间
            const labels = data.kline_data.map((item, index) => {
                // 每50个数据点显示一个标签
                return index % 50 === 0 ? item.time.substring(5, 16) : '';
            });
            
            // 准备K线收盘价数据
            const priceData = data.kline_data.map(item => item.close);
            
            // 创建价格到索引的映射
            const timeToIndex = {};
            data.kline_data.forEach((item, index) => {
                timeToIndex[item.time] = index;
            });
            
            // 准备交易信号数据（转换为索引位置）
            const longEntries = data.trade_signals
                .filter(signal => signal.type === 'open_long')
                .map(signal => {
                    const index = timeToIndex[signal.time];
                    return index !== undefined ? { x: index, y: signal.price } : null;
                })
                .filter(item => item !== null);
                
            const longExits = data.trade_signals
                .filter(signal => signal.type === 'close_long')
                .map(signal => {
                    const index = timeToIndex[signal.time];
                    return index !== undefined ? { x: index, y: signal.price } : null;
                })
                .filter(item => item !== null);
                
            const shortEntries = data.trade_signals
                .filter(signal => signal.type === 'open_short')
                .map(signal => {
                    const index = timeToIndex[signal.time];
                    return index !== undefined ? { x: index, y: signal.price } : null;
                })
                .filter(item => item !== null);
                
            const shortExits = data.trade_signals
                .filter(signal => signal.type === 'close_short')
                .map(signal => {
                    const index = timeToIndex[signal.time];
                    return index !== undefined ? { x: index, y: signal.price } : null;
                })
                .filter(item => item !== null);
            
            // 准备收益曲线数据
            const returnData = data.portfolio_values.map(item => item.return);
            
            backtestChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        // K线收盘价
                        {
                            label: 'K线收盘价',
                            data: priceData,
                            borderColor: '#4299e1',
                            backgroundColor: 'rgba(66, 153, 225, 0.1)',
                            fill: false,
                            tension: 0.1,
                            yAxisID: 'price',
                            pointRadius: 0,
                            borderWidth: 1.5
                        },
                        // 多头开仓
                        {
                            label: '🔺 买入开仓',
                            data: longEntries,
                            backgroundColor: '#48bb78',
                            borderColor: '#48bb78',
                            pointRadius: 8,
                            pointStyle: 'triangle',
                            showLine: false,
                            yAxisID: 'price'
                        },
                        // 多头平仓
                        {
                            label: '⬜ 卖出平仓',
                            data: longExits,
                            backgroundColor: '#ed8936',
                            borderColor: '#ed8936',
                            pointRadius: 7,
                            pointStyle: 'rect',
                            showLine: false,
                            yAxisID: 'price'
                        },
                        // 空头开仓
                        {
                            label: '🔻 卖出开仓',
                            data: shortEntries,
                            backgroundColor: '#f56565',
                            borderColor: '#f56565',
                            pointRadius: 8,
                            pointStyle: 'triangle',
                            rotation: 180,
                            showLine: false,
                            yAxisID: 'price'
                        },
                        // 空头平仓
                        {
                            label: '✖️ 买入平仓',
                            data: shortExits,
                            backgroundColor: '#9f7aea',
                            borderColor: '#9f7aea',
                            pointRadius: 8,
                            pointStyle: 'crossRot',
                            showLine: false,
                            yAxisID: 'price'
                        },
                        // 收益曲线
                        {
                            label: '📈 收益曲线 (%)',
                            data: returnData,
                            borderColor: '#e53e3e',
                            backgroundColor: 'rgba(229, 62, 62, 0.1)',
                            fill: false,
                            tension: 0.1,
                            yAxisID: 'return',
                            borderWidth: 2,
                            pointRadius: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: '时间 (2024年1月-3月)'
                            },
                            ticks: {
                                maxTicksLimit: 10
                            }
                        },
                        price: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: '价格 (元/吨)'
                            },
                            grid: {
                                color: 'rgba(0,0,0,0.1)',
                            },
                        },
                        return: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: '收益率 (%)'
                            },
                            grid: {
                                drawOnChartArea: false,
                            },
                            ticks: {
                                callback: function(value) {
                                    return value.toFixed(1) + '%';
                                }
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: '📊 回测分析图表 - MA策略K线图与交易信号 (2024-01-01 至 2024-03-31)',
                            font: {
                                size: 16
                            }
                        },
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                padding: 20
                            }
                        },
                        tooltip: {
                            callbacks: {
                                title: function(context) {
                                    const index = context[0].dataIndex;
                                    return data.kline_data[index] ? data.kline_data[index].time : '';
                                },
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.dataset.yAxisID === 'return') {
                                        label += context.formattedValue + '%';
                                    } else {
                                        label += context.formattedValue;
                                    }
                                    return label;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        function updateBacktestMetrics(metrics) {
            document.getElementById('total-return').textContent = `${metrics.total_return.toFixed(2)}%`;
            document.getElementById('max-drawdown').textContent = `${metrics.max_drawdown.toFixed(2)}%`;
            document.getElementById('total-trades').textContent = metrics.total_trades;
            document.getElementById('win-rate').textContent = `${metrics.win_rate.toFixed(1)}%`;
            
            // 显示指标面板
            document.getElementById('backtest-metrics').style.display = 'block';
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', () => {
            loadInitialData();
            loadPositionsAndTrades();
            
            // 定时刷新持仓数据和当前页交易数据
            setInterval(() => {
                // 总是刷新持仓数据
                fetch('/api/positions')
                    .then(response => response.json())
                    .then(data => {
                        updatePositions(data);
                    });
                
                // 如果在第一页，自动刷新最新交易；否则保持用户当前查看的页面
                if (currentTradesPage === 1) {
                    loadTradesPage(1);
                }
            }, 5000);
        });
    </script>
</body>
</html>'''
    
    with open(templates_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info("演示HTML模板创建完成")


def main():
    """主函数"""
    
    print("🎯 期货量化交易系统 - 项目验收演示服务器")
    print("=" * 60)
    
    # 创建模板文件 (已有自定义模板，跳过)
    # create_demo_templates()
    
    # 启动服务器
    print("🚀 启动演示服务器...")
    print("📊 Web界面地址: http://localhost:5023")
    print("🔄 实时数据: WebSocket连接")
    print("💻 支持功能: 市场数据、策略状态、回测系统、配置管理")
    print("=" * 60)
    
    try:
        socketio.run(app, host='0.0.0.0', port=5023, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n👋 演示服务器已停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")


if __name__ == '__main__':
    main()