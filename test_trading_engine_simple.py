#!/usr/bin/env python3
"""
简化版TradingEngine测试 - 快速验证核心功能
"""

import json
import time
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from core.trading_engine import TradingEngine, create_sample_trading_signal
from core.connection_manager import ConnectionManager
from core.data_types import TradingSignal, TradingSignalAction, Direction

def test_trading_engine():
    print("="*60)
    print("简化版TradingEngine测试")
    print("="*60)
    
    # 1. 加载配置和初始化
    print("\n1. 初始化TradingEngine...")
    with open('system_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    connection_manager = ConnectionManager(config)
    trading_engine = TradingEngine(connection_manager, config)
    
    print("✅ TradingEngine初始化完成")
    
    # 2. 连接网关
    print("\n2. 连接网关...")
    connection_result = connection_manager.connect_gateway()
    print(f"连接结果: {'成功' if connection_result else '失败'}")
    
    # 3. 测试订单管理功能
    print("\n3. 测试订单管理功能...")
    
    # 收集回调数据
    received_trades = []
    received_orders = []
    
    def trade_callback(trade):
        received_trades.append(trade)
        print(f"📈 成交回调: {trade.symbol} {trade.direction.value} {trade.volume}手@{trade.price:.2f}")
    
    trading_engine.register_trade_callback(trade_callback)
    
    # 4. 测试开多头交易
    print("\n4. 测试开多头交易...")
    long_signal = TradingSignal(
        symbol="rb2310",
        action=TradingSignalAction.OPEN_LONG,
        volume=2,
        price=0.0,  # 市价单
        timestamp=datetime.now(),
        strategy="test_strategy",
        reason="测试开多"
    )
    
    result = trading_engine.send_order(long_signal)
    print(f"开多结果: {'成功' if result.success else '失败'} - {result.message}")
    if result.success:
        print(f"订单ID: {result.orderid}")
    
    # 等待成交
    time.sleep(1)
    
    # 5. 检查持仓
    print("\n5. 检查持仓...")
    positions = trading_engine.get_all_positions()
    print(f"总持仓数量: {len(positions)}")
    
    for position in positions:
        print(f"持仓: {position.symbol} {position.direction.value} "
              f"{position.volume}手 均价:{position.price:.2f} 盈亏:{position.pnl:.2f}")
    
    # 6. 测试开空头交易
    print("\n6. 测试开空头交易...")
    short_signal = TradingSignal(
        symbol="i2310", 
        action=TradingSignalAction.OPEN_SHORT,
        volume=1,
        price=800.0,  # 限价单
        timestamp=datetime.now(),
        strategy="test_strategy",
        reason="测试开空"
    )
    
    result2 = trading_engine.send_order(short_signal)
    print(f"开空结果: {'成功' if result2.success else '失败'} - {result2.message}")
    
    # 等待成交
    time.sleep(1)
    
    # 7. 再次检查持仓
    print("\n7. 更新后的持仓...")
    positions = trading_engine.get_all_positions()
    print(f"总持仓数量: {len(positions)}")
    
    for position in positions:
        print(f"持仓: {position.symbol} {position.direction.value} "
              f"{position.volume}手 均价:{position.price:.2f} 盈亏:{position.pnl:.2f}")
    
    # 8. 测试平仓
    if len(positions) > 0:
        print("\n8. 测试部分平仓...")
        
        # 选择第一个持仓进行平仓
        pos = positions[0]
        if pos.direction == Direction.LONG:
            close_action = TradingSignalAction.CLOSE_LONG
        else:
            close_action = TradingSignalAction.CLOSE_SHORT
        
        close_signal = TradingSignal(
            symbol=pos.symbol,
            action=close_action,
            volume=1,
            price=0.0,
            timestamp=datetime.now(),
            strategy="test_strategy",
            reason="测试平仓"
        )
        
        result3 = trading_engine.send_order(close_signal)
        print(f"平仓结果: {'成功' if result3.success else '失败'} - {result3.message}")
        
        # 等待成交
        time.sleep(1)
    
    # 9. 最终状态检查
    print("\n9. 最终状态检查...")
    
    # 检查活跃订单
    active_orders = trading_engine.get_active_orders()
    print(f"活跃订单数量: {len(active_orders)}")
    
    # 检查最终持仓
    final_positions = trading_engine.get_all_positions()
    print(f"最终持仓数量: {len(final_positions)}")
    
    for position in final_positions:
        print(f"持仓: {position.symbol} {position.direction.value} "
              f"{position.volume}手 均价:{position.price:.2f} 盈亏:{position.pnl:.2f}")
    
    # 检查账户信息
    account = trading_engine.get_account_info()
    print(f"账户余额: {account.balance:,.2f}")
    print(f"可用资金: {account.available:,.2f}")
    
    # 检查成交记录
    print(f"成交记录数量: {len(received_trades)}")
    
    # 10. 引擎状态
    print("\n10. 引擎状态...")
    status = trading_engine.get_status()
    print(f"引擎状态: {status}")
    
    # 11. 清理
    print("\n11. 清理资源...")
    connection_manager.disconnect_gateway()
    
    print("✅ TradingEngine测试完成")
    
    # 返回测试结果
    return {
        "trades_count": len(received_trades),
        "positions_count": len(final_positions),
        "orders_successful": result.success and result2.success,
        "engine_ready": trading_engine.is_ready()
    }


if __name__ == '__main__':
    os.chdir('/home/user/webapp')
    
    results = test_trading_engine()
    
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)
    print(f"成交记录: {results['trades_count']} 条")
    print(f"最终持仓: {results['positions_count']} 个")
    print(f"订单执行: {'成功' if results['orders_successful'] else '失败'}")
    print(f"引擎状态: {'就绪' if results['engine_ready'] else '未就绪'}")
    
    if results['trades_count'] > 0 and results['orders_successful']:
        print("\n🎉 TradingEngine核心功能验证成功！")
        print("✅ 订单管理 ✅ 持仓管理 ✅ 交易执行")
    else:
        print("\n❌ 部分功能验证失败，需要进一步调试")